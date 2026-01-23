#!/usr/bin/env python3
"""
数据清理脚本

定期清理过期/无用数据，避免表膨胀影响性能。

清理范围：
1. verification_codes - 过期/已用验证码（保留 7 天）
2. student_entry_tokens - 过期入口 token（保留 30 天）
3. report_share_tokens - 过期+已撤销分享（保留 90 天）
4. audit_logs - 历史审计日志（保留 365 天，可选）

使用方法：
    # 预览模式（不实际删除）
    python scripts/cleanup_expired_data.py --dry-run
    
    # 实际执行
    python scripts/cleanup_expired_data.py
    
    # 只清理指定表
    python scripts/cleanup_expired_data.py --tables verification_codes,student_entry_tokens
    
    # 自定义保留天数
    python scripts/cleanup_expired_data.py --verification-days 3 --entry-days 14

建议：
- 生产环境使用 cron 定时执行（如每天凌晨 3 点）
- 首次执行建议使用 --dry-run 预览
- 大表清理建议分批进行，避免长时间锁表
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

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.timezone import now as china_now
from src.adapters.repositories.models import (
    VerificationCodeModel,
    StudentEntryTokenModel,
    ReportShareTokenModel,
    AuditLogModel,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清理器"""
    
    def __init__(
        self,
        dry_run: bool = True,
        verification_days: int = 7,
        entry_days: int = 30,
        share_days: int = 90,
        audit_days: int = 365,
        batch_size: int = 1000,
    ):
        self.dry_run = dry_run
        self.verification_days = verification_days
        self.entry_days = entry_days
        self.share_days = share_days
        self.audit_days = audit_days
        self.batch_size = batch_size
        self.stats = {}
    
    async def cleanup_verification_codes(self, db: AsyncSession) -> int:
        """
        清理过期/已用验证码
        
        规则：
        - is_used = true 且 used_at < N 天前
        - expires_at < 当前时间
        """
        cutoff = china_now() - timedelta(days=self.verification_days)
        
        # 统计待删除数量
        count_stmt = select(func.count(VerificationCodeModel.id)).where(
            (VerificationCodeModel.is_used == True) | 
            (VerificationCodeModel.expires_at < china_now())
        ).where(VerificationCodeModel.created_at < cutoff)
        
        count = (await db.execute(count_stmt)).scalar() or 0
        
        if self.dry_run:
            logger.info(f"[DRY RUN] verification_codes: 将删除 {count} 条记录")
            return count
        
        # 实际删除
        delete_stmt = delete(VerificationCodeModel).where(
            (VerificationCodeModel.is_used == True) | 
            (VerificationCodeModel.expires_at < china_now())
        ).where(VerificationCodeModel.created_at < cutoff)
        
        result = await db.execute(delete_stmt)
        await db.commit()
        
        deleted = result.rowcount
        logger.info(f"verification_codes: 已删除 {deleted} 条记录")
        return deleted
    
    async def cleanup_student_entry_tokens(self, db: AsyncSession) -> int:
        """
        清理过期入口 token
        
        规则：
        - expires_at < N 天前
        - is_used = true 且 used_at < N 天前
        """
        cutoff = china_now() - timedelta(days=self.entry_days)
        
        # 统计待删除数量
        count_stmt = select(func.count(StudentEntryTokenModel.id)).where(
            (StudentEntryTokenModel.expires_at < cutoff) |
            (
                (StudentEntryTokenModel.is_used == True) & 
                (StudentEntryTokenModel.used_at < cutoff)
            )
        )
        
        count = (await db.execute(count_stmt)).scalar() or 0
        
        if self.dry_run:
            logger.info(f"[DRY RUN] student_entry_tokens: 将删除 {count} 条记录")
            return count
        
        # 实际删除
        delete_stmt = delete(StudentEntryTokenModel).where(
            (StudentEntryTokenModel.expires_at < cutoff) |
            (
                (StudentEntryTokenModel.is_used == True) & 
                (StudentEntryTokenModel.used_at < cutoff)
            )
        )
        
        result = await db.execute(delete_stmt)
        await db.commit()
        
        deleted = result.rowcount
        logger.info(f"student_entry_tokens: 已删除 {deleted} 条记录")
        return deleted
    
    async def cleanup_report_share_tokens(self, db: AsyncSession) -> int:
        """
        清理过期/已撤销分享
        
        规则：
        - is_revoked = true 且 created_at < N 天前
        - expires_at < N 天前
        """
        cutoff = china_now() - timedelta(days=self.share_days)
        
        # 统计待删除数量
        count_stmt = select(func.count(ReportShareTokenModel.id)).where(
            (
                (ReportShareTokenModel.is_revoked == True) & 
                (ReportShareTokenModel.created_at < cutoff)
            ) |
            (
                (ReportShareTokenModel.expires_at != None) & 
                (ReportShareTokenModel.expires_at < cutoff)
            )
        )
        
        count = (await db.execute(count_stmt)).scalar() or 0
        
        if self.dry_run:
            logger.info(f"[DRY RUN] report_share_tokens: 将删除 {count} 条记录")
            return count
        
        # 实际删除
        delete_stmt = delete(ReportShareTokenModel).where(
            (
                (ReportShareTokenModel.is_revoked == True) & 
                (ReportShareTokenModel.created_at < cutoff)
            ) |
            (
                (ReportShareTokenModel.expires_at != None) & 
                (ReportShareTokenModel.expires_at < cutoff)
            )
        )
        
        result = await db.execute(delete_stmt)
        await db.commit()
        
        deleted = result.rowcount
        logger.info(f"report_share_tokens: 已删除 {deleted} 条记录")
        return deleted
    
    async def cleanup_audit_logs(self, db: AsyncSession) -> int:
        """
        清理历史审计日志（可选，谨慎使用）
        
        规则：
        - created_at < N 天前
        
        注意：
        - 审计日志通常需要长期保留，建议归档而非删除
        - 此功能默认不启用，需要显式传入 --cleanup-audit 参数
        """
        cutoff = china_now() - timedelta(days=self.audit_days)
        
        # 统计待删除数量
        count_stmt = select(func.count(AuditLogModel.id)).where(
            AuditLogModel.created_at < cutoff
        )
        
        count = (await db.execute(count_stmt)).scalar() or 0
        
        if self.dry_run:
            logger.info(f"[DRY RUN] audit_logs: 将删除 {count} 条记录 (保留 {self.audit_days} 天)")
            return count
        
        # 实际删除
        delete_stmt = delete(AuditLogModel).where(
            AuditLogModel.created_at < cutoff
        )
        
        result = await db.execute(delete_stmt)
        await db.commit()
        
        deleted = result.rowcount
        logger.info(f"audit_logs: 已删除 {deleted} 条记录")
        return deleted
    
    async def run(self, tables: list = None, cleanup_audit: bool = False):
        """
        执行清理
        
        Args:
            tables: 要清理的表列表，None 表示全部
            cleanup_audit: 是否清理审计日志（谨慎）
        """
        all_tables = [
            "verification_codes",
            "student_entry_tokens",
            "report_share_tokens",
        ]
        
        if cleanup_audit:
            all_tables.append("audit_logs")
        
        if tables:
            tables = [t.strip() for t in tables if t.strip() in all_tables]
        else:
            tables = all_tables
        
        if not tables:
            logger.error("没有指定有效的表名")
            return
        
        mode = "[DRY RUN] " if self.dry_run else ""
        logger.info(f"{mode}开始清理数据...")
        logger.info(f"  - 待清理表: {', '.join(tables)}")
        logger.info(f"  - 保留策略: verification={self.verification_days}天, "
                   f"entry={self.entry_days}天, share={self.share_days}天")
        
        async with AsyncSessionLocal() as db:
            total = 0
            
            if "verification_codes" in tables:
                total += await self.cleanup_verification_codes(db)
            
            if "student_entry_tokens" in tables:
                total += await self.cleanup_student_entry_tokens(db)
            
            if "report_share_tokens" in tables:
                total += await self.cleanup_report_share_tokens(db)
            
            if "audit_logs" in tables and cleanup_audit:
                total += await self.cleanup_audit_logs(db)
        
        logger.info(f"{mode}清理完成，共处理 {total} 条记录")


def main():
    parser = argparse.ArgumentParser(
        description="清理过期/无用数据，避免表膨胀",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 预览模式
    python scripts/cleanup_expired_data.py --dry-run
    
    # 实际执行
    python scripts/cleanup_expired_data.py
    
    # 只清理指定表
    python scripts/cleanup_expired_data.py --tables verification_codes,student_entry_tokens
    
    # 清理审计日志（谨慎）
    python scripts/cleanup_expired_data.py --cleanup-audit --audit-days 180
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际删除数据"
    )
    
    parser.add_argument(
        "--tables",
        type=str,
        default=None,
        help="要清理的表（逗号分隔），默认全部"
    )
    
    parser.add_argument(
        "--verification-days",
        type=int,
        default=7,
        help="验证码保留天数（默认 7）"
    )
    
    parser.add_argument(
        "--entry-days",
        type=int,
        default=30,
        help="入口 token 保留天数（默认 30）"
    )
    
    parser.add_argument(
        "--share-days",
        type=int,
        default=90,
        help="分享 token 保留天数（默认 90）"
    )
    
    parser.add_argument(
        "--cleanup-audit",
        action="store_true",
        help="是否清理审计日志（谨慎使用）"
    )
    
    parser.add_argument(
        "--audit-days",
        type=int,
        default=365,
        help="审计日志保留天数（默认 365）"
    )
    
    args = parser.parse_args()
    
    tables = args.tables.split(",") if args.tables else None
    
    cleaner = DataCleaner(
        dry_run=args.dry_run,
        verification_days=args.verification_days,
        entry_days=args.entry_days,
        share_days=args.share_days,
        audit_days=args.audit_days,
    )
    
    asyncio.run(cleaner.run(tables=tables, cleanup_audit=args.cleanup_audit))


if __name__ == "__main__":
    main()
