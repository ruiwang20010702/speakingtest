#!/usr/bin/env python3
"""
审计日志归档脚本

将超过保留期的审计日志从 audit_logs 移动到 audit_logs_archive 表。
支持两种模式：
1. 使用 PostgreSQL 存储函数（推荐，性能更好）
2. 使用 Python 批量处理（兼容其他数据库）

使用方法：
    # 预览模式
    python scripts/archive_audit_logs.py --dry-run
    
    # 归档 90 天前的日志
    python scripts/archive_audit_logs.py --days 90
    
    # 使用 PostgreSQL 函数（推荐）
    python scripts/archive_audit_logs.py --days 90 --use-pg-function
    
    # Python 批量处理（兼容模式）
    python scripts/archive_audit_logs.py --days 90 --batch-size 1000

建议：
- 生产环境使用 cron 定时执行（如每周一次）
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

from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.timezone import now as china_now
from src.adapters.repositories.models import AuditLogModel, AuditLogArchiveModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AuditLogArchiver:
    """审计日志归档器"""
    
    def __init__(
        self,
        dry_run: bool = True,
        retention_days: int = 90,
        batch_size: int = 1000,
        use_pg_function: bool = False
    ):
        self.dry_run = dry_run
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.use_pg_function = use_pg_function
    
    async def count_to_archive(self, db: AsyncSession) -> int:
        """统计待归档的日志数量"""
        cutoff = china_now() - timedelta(days=self.retention_days)
        stmt = select(func.count(AuditLogModel.id)).where(
            AuditLogModel.created_at < cutoff
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
    
    async def archive_with_pg_function(self, db: AsyncSession) -> int:
        """使用 PostgreSQL 存储函数归档（推荐）"""
        if self.dry_run:
            count = await self.count_to_archive(db)
            logger.info(f"[DRY RUN] 将归档 {count} 条审计日志 (保留 {self.retention_days} 天)")
            return count
        
        # 调用 PostgreSQL 函数
        result = await db.execute(
            text("SELECT archive_old_audit_logs(:days)"),
            {"days": self.retention_days}
        )
        archived_count = result.scalar() or 0
        await db.commit()
        
        logger.info(f"已归档 {archived_count} 条审计日志")
        return archived_count
    
    async def archive_with_python(self, db: AsyncSession) -> int:
        """使用 Python 批量处理归档（兼容模式）"""
        cutoff = china_now() - timedelta(days=self.retention_days)
        total_archived = 0
        
        if self.dry_run:
            count = await self.count_to_archive(db)
            logger.info(f"[DRY RUN] 将归档 {count} 条审计日志 (保留 {self.retention_days} 天)")
            return count
        
        while True:
            # 分批查询待归档的记录
            stmt = select(AuditLogModel).where(
                AuditLogModel.created_at < cutoff
            ).limit(self.batch_size)
            
            result = await db.execute(stmt)
            logs = result.scalars().all()
            
            if not logs:
                break
            
            # 插入到归档表
            archive_records = [
                AuditLogArchiveModel(
                    original_id=log.id,
                    operator_id=log.operator_id,
                    action=log.action,
                    target_type=log.target_type,
                    target_id=log.target_id,
                    client_ip=log.client_ip,
                    user_agent=log.user_agent,
                    details=log.details,
                    created_at=log.created_at
                )
                for log in logs
            ]
            db.add_all(archive_records)
            
            # 删除原记录
            ids_to_delete = [log.id for log in logs]
            delete_stmt = delete(AuditLogModel).where(
                AuditLogModel.id.in_(ids_to_delete)
            )
            await db.execute(delete_stmt)
            
            await db.commit()
            
            batch_count = len(logs)
            total_archived += batch_count
            logger.info(f"已归档 {batch_count} 条记录 (累计: {total_archived})")
            
            # 如果本批次不足 batch_size，说明已处理完
            if batch_count < self.batch_size:
                break
        
        logger.info(f"归档完成，共归档 {total_archived} 条审计日志")
        return total_archived
    
    async def run(self):
        """执行归档"""
        mode = "[DRY RUN] " if self.dry_run else ""
        method = "PostgreSQL 函数" if self.use_pg_function else "Python 批量处理"
        
        logger.info(f"{mode}开始归档审计日志...")
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
        main_count = await db.execute(select(func.count(AuditLogModel.id)))
        main_total = main_count.scalar() or 0
        
        # 归档表统计
        archive_count = await db.execute(select(func.count(AuditLogArchiveModel.id)))
        archive_total = archive_count.scalar() or 0
        
        # 最早记录
        oldest_main = await db.execute(
            select(func.min(AuditLogModel.created_at))
        )
        oldest_archive = await db.execute(
            select(func.min(AuditLogArchiveModel.created_at))
        )
        
        print("\n审计日志统计:")
        print(f"  - audit_logs (主表): {main_total} 条")
        print(f"  - audit_logs_archive (归档): {archive_total} 条")
        print(f"  - 主表最早记录: {oldest_main.scalar()}")
        print(f"  - 归档最早记录: {oldest_archive.scalar()}")


def main():
    parser = argparse.ArgumentParser(
        description="归档审计日志到 audit_logs_archive 表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 预览模式
    python scripts/archive_audit_logs.py --dry-run
    
    # 归档 90 天前的日志（使用 PostgreSQL 函数）
    python scripts/archive_audit_logs.py --days 90 --use-pg-function
    
    # 查看统计信息
    python scripts/archive_audit_logs.py --stats
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
        default=1000,
        help="Python 模式下的批量大小（默认 1000）"
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
    
    archiver = AuditLogArchiver(
        dry_run=args.dry_run,
        retention_days=args.days,
        batch_size=args.batch_size,
        use_pg_function=args.use_pg_function
    )
    
    asyncio.run(archiver.run())


if __name__ == "__main__":
    main()
