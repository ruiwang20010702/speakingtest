#!/usr/bin/env python3
"""
测评记录归档脚本

将超过保留期的已完成测评从 tests 表归档到 tests_archive 表。

归档范围：
- tests 表中 status='completed' 且 completed_at < N 天前的记录
- 关联的 test_items 记录
- 关联的 test_raw_data 记录（大 JSON 字段）

使用方法：
    # 预览模式（不实际归档）
    python scripts/archive_old_tests.py --dry-run
    
    # 归档 90 天前的测评（默认）
    python scripts/archive_old_tests.py --days 90
    
    # 使用 PostgreSQL 函数（推荐，性能更好）
    python scripts/archive_old_tests.py --days 90 --use-pg-function
    
    # Python 批量处理（兼容模式）
    python scripts/archive_old_tests.py --days 90 --batch-size 100

建议：
- 生产环境使用 cron 定时执行（如每月 1 号凌晨 5 点）
- 首次执行建议使用 --dry-run 预览
- PostgreSQL 环境推荐使用 --use-pg-function
"""
import argparse
import asyncio
import logging
import sys
from datetime import timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.timezone import now as china_now
from src.adapters.repositories.models import (
    TestModel, TestItemModel, TestArchiveModel, TestItemArchiveModel, TestRawDataModel
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestArchiver:
    """测评记录归档器"""
    
    def __init__(
        self,
        dry_run: bool = True,
        retention_days: int = 90,
        batch_size: int = 100,
        use_pg_function: bool = False
    ):
        self.dry_run = dry_run
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.use_pg_function = use_pg_function
    
    async def count_to_archive(self, db: AsyncSession) -> int:
        """统计待归档的测评数量"""
        cutoff = china_now() - timedelta(days=self.retention_days)
        stmt = select(func.count(TestModel.id)).where(
            TestModel.status == "completed",
            TestModel.completed_at < cutoff
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
    
    async def archive_with_pg_function(self, db: AsyncSession) -> tuple:
        """使用 PostgreSQL 存储函数归档（推荐）"""
        if self.dry_run:
            count = await self.count_to_archive(db)
            logger.info(f"[DRY RUN] 将归档 {count} 条测评记录 (保留 {self.retention_days} 天)")
            return count, 0
        
        # 调用 PostgreSQL 函数
        result = await db.execute(
            text("SELECT * FROM archive_old_tests(:days)"),
            {"days": self.retention_days}
        )
        row = result.fetchone()
        await db.commit()
        
        archived_tests = row[0] if row else 0
        archived_items = row[1] if row else 0
        
        logger.info(f"已归档 {archived_tests} 条测评记录，{archived_items} 条题目记录")
        return archived_tests, archived_items
    
    async def archive_with_python(self, db: AsyncSession) -> tuple:
        """使用 Python 批量处理归档（兼容模式）"""
        cutoff = china_now() - timedelta(days=self.retention_days)
        total_tests = 0
        total_items = 0
        
        if self.dry_run:
            count = await self.count_to_archive(db)
            logger.info(f"[DRY RUN] 将归档 {count} 条测评记录 (保留 {self.retention_days} 天)")
            return count, 0
        
        while True:
            # 分批查询待归档的测评
            stmt = select(TestModel).options(
                selectinload(TestModel.items),
                selectinload(TestModel.raw_data)
            ).where(
                TestModel.status == "completed",
                TestModel.completed_at < cutoff
            ).limit(self.batch_size)
            
            result = await db.execute(stmt)
            tests = result.scalars().all()
            
            if not tests:
                break
            
            for test in tests:
                # 获取 raw_data
                raw_data = test.raw_data
                
                # 创建归档记录
                archive = TestArchiveModel(
                    original_id=test.id,
                    student_id=test.student_id,
                    level=test.level,
                    unit=test.unit,
                    status=test.status,
                    total_score=test.total_score,
                    part1_score=test.part1_score,
                    part2_score=test.part2_score,
                    star_level=test.star_level,
                    part2_transcript=test.part2_transcript,
                    part2_audio_url=test.part2_audio_url,
                    part1_audio_url=test.part1_audio_url,
                    failure_reason=test.failure_reason,
                    retry_count=test.retry_count,
                    cost=test.cost,
                    # 大 JSON 字段优先从 raw_data 获取
                    part1_raw_result=(raw_data.part1_raw_result if raw_data else None) or test.part1_raw_result,
                    part2_raw_result=(raw_data.part2_raw_result if raw_data else None) or test.part2_raw_result,
                    tokens_used=(raw_data.tokens_used if raw_data else None) or test.tokens_used,
                    summary_highlights=(raw_data.summary_highlights if raw_data else None) or test.summary_highlights,
                    summary_weaknesses=(raw_data.summary_weaknesses if raw_data else None) or test.summary_weaknesses,
                    summary_weekly_plan=(raw_data.summary_weekly_plan if raw_data else None) or test.summary_weekly_plan,
                    summary_dimension_feedback=(raw_data.summary_dimension_feedback if raw_data else None) or test.summary_dimension_feedback,
                    summary_generated_at=test.summary_generated_at,
                    interpretation_pages=(raw_data.interpretation_pages if raw_data else None) or test.interpretation_pages,
                    interpretation_parent_script=(raw_data.interpretation_parent_script if raw_data else None) or test.interpretation_parent_script,
                    interpretation_generated_at=test.interpretation_generated_at,
                    report_override=(raw_data.report_override if raw_data else None) or test.report_override,
                    created_at=test.created_at,
                    updated_at=test.updated_at,
                    completed_at=test.completed_at
                )
                db.add(archive)
                await db.flush()  # 获取 archive.id
                
                # 归档 test_items
                for item in test.items:
                    item_archive = TestItemArchiveModel(
                        original_id=item.id,
                        test_archive_id=archive.id,
                        original_test_id=test.id,
                        question_no=item.question_no,
                        score=item.score,
                        feedback=item.feedback,
                        evidence=item.evidence,
                        created_at=item.created_at
                    )
                    db.add(item_archive)
                    total_items += 1
                
                # 删除 raw_data
                if raw_data:
                    await db.delete(raw_data)
                
                # 删除 test_items (cascade 会自动删除)
                # 删除 test
                await db.delete(test)
                
                total_tests += 1
            
            await db.commit()
            logger.info(f"已归档 {len(tests)} 条记录 (累计: {total_tests})")
            
            # 如果本批次不足 batch_size，说明已处理完
            if len(tests) < self.batch_size:
                break
        
        logger.info(f"归档完成，共归档 {total_tests} 条测评记录，{total_items} 条题目记录")
        return total_tests, total_items
    
    async def run(self):
        """执行归档"""
        mode = "[DRY RUN] " if self.dry_run else ""
        method = "PostgreSQL 函数" if self.use_pg_function else "Python 批量处理"
        
        logger.info(f"{mode}开始归档测评记录...")
        logger.info(f"  - 保留天数: {self.retention_days}")
        logger.info(f"  - 归档方式: {method}")
        
        async with AsyncSessionLocal() as db:
            if self.use_pg_function:
                return await self.archive_with_pg_function(db)
            else:
                return await self.archive_with_python(db)


async def get_archive_stats():
    """获取归档统计信息"""
    async with AsyncSessionLocal() as db:
        # 主表统计
        main_count = await db.execute(select(func.count(TestModel.id)))
        main_total = main_count.scalar() or 0
        
        # 归档表统计
        archive_count = await db.execute(select(func.count(TestArchiveModel.id)))
        archive_total = archive_count.scalar() or 0
        
        # 最早记录
        oldest_main = await db.execute(
            select(func.min(TestModel.created_at))
        )
        oldest_archive = await db.execute(
            select(func.min(TestArchiveModel.created_at))
        )
        
        # 已完成的测评数量
        completed_count = await db.execute(
            select(func.count(TestModel.id)).where(TestModel.status == "completed")
        )
        completed_total = completed_count.scalar() or 0
        
        print("\n测评记录统计:")
        print(f"  - tests (主表): {main_total} 条 (已完成: {completed_total})")
        print(f"  - tests_archive (归档): {archive_total} 条")
        print(f"  - 主表最早记录: {oldest_main.scalar()}")
        print(f"  - 归档最早记录: {oldest_archive.scalar()}")


def main():
    parser = argparse.ArgumentParser(
        description="归档历史测评记录到 tests_archive 表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 预览模式
    python scripts/archive_old_tests.py --dry-run
    
    # 归档 90 天前的测评（使用 PostgreSQL 函数）
    python scripts/archive_old_tests.py --days 90 --use-pg-function
    
    # 查看统计信息
    python scripts/archive_old_tests.py --stats
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际归档"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="保留天数（默认 90）"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Python 模式下的批量大小（默认 100）"
    )
    
    parser.add_argument(
        "--use-pg-function",
        action="store_true",
        help="使用 PostgreSQL 存储函数（推荐）"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示归档统计信息"
    )
    
    args = parser.parse_args()
    
    if args.stats:
        asyncio.run(get_archive_stats())
        return
    
    archiver = TestArchiver(
        dry_run=args.dry_run,
        retention_days=args.days,
        batch_size=args.batch_size,
        use_pg_function=args.use_pg_function
    )
    
    asyncio.run(archiver.run())


if __name__ == "__main__":
    main()
