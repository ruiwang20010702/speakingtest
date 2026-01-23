"""
Test Archive Repository

查询历史归档测评数据的仓库。
支持从 tests_archive 和 test_items_archive 表查询归档数据。
"""
from typing import Optional, List, Tuple
from datetime import datetime

from sqlalchemy import select, func, or_, union_all, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.adapters.repositories.models import (
    TestModel, TestItemModel, TestArchiveModel, TestItemArchiveModel,
    StudentProfileModel, TestRawDataModel
)


class TestArchiveRepository:
    """测评归档数据仓库"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_test_by_id(
        self, 
        test_id: int, 
        include_archived: bool = True
    ) -> Optional[dict]:
        """
        根据 ID 查询测评（自动检查归档表）
        
        Args:
            test_id: 测评 ID
            include_archived: 是否查询归档表
            
        Returns:
            测评数据字典，包含 is_archived 标识
        """
        # 1. 先从主表查询
        stmt = select(TestModel).options(
            selectinload(TestModel.items),
            selectinload(TestModel.raw_data)
        ).where(TestModel.id == test_id)
        
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()
        
        if test:
            return self._test_to_dict(test, is_archived=False)
        
        # 2. 主表没有，查询归档表
        if include_archived:
            stmt = select(TestArchiveModel).options(
                selectinload(TestArchiveModel.items)
            ).where(TestArchiveModel.original_id == test_id)
            
            result = await self.db.execute(stmt)
            archive = result.scalar_one_or_none()
            
            if archive:
                return self._archive_to_dict(archive)
        
        return None
    
    async def get_student_tests_with_archive(
        self,
        student_id: int,
        include_archived: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[dict], int]:
        """
        查询学生测评列表（包含归档）
        
        Args:
            student_id: 学生 ID
            include_archived: 是否包含归档数据
            page: 页码（1-indexed）
            page_size: 每页数量
            
        Returns:
            (测评列表, 总数)
        """
        offset = (page - 1) * page_size
        
        if not include_archived:
            # 只查询主表
            count_stmt = select(func.count(TestModel.id)).where(
                TestModel.student_id == student_id
            )
            total = (await self.db.execute(count_stmt)).scalar() or 0
            
            stmt = select(TestModel).where(
                TestModel.student_id == student_id
            ).order_by(TestModel.created_at.desc()).offset(offset).limit(page_size)
            
            result = await self.db.execute(stmt)
            tests = result.scalars().all()
            
            return [self._test_to_dict(t, is_archived=False) for t in tests], total
        
        # 包含归档数据 - 使用两次查询合并结果
        # 1. 统计总数
        main_count = select(func.count(TestModel.id)).where(
            TestModel.student_id == student_id
        )
        archive_count = select(func.count(TestArchiveModel.id)).where(
            TestArchiveModel.student_id == student_id
        )
        
        main_total = (await self.db.execute(main_count)).scalar() or 0
        archive_total = (await self.db.execute(archive_count)).scalar() or 0
        total = main_total + archive_total
        
        # 2. 分页查询 - 先查主表，不够再查归档表
        results = []
        
        if offset < main_total:
            # 需要从主表获取数据
            main_limit = min(page_size, main_total - offset)
            stmt = select(TestModel).where(
                TestModel.student_id == student_id
            ).order_by(TestModel.created_at.desc()).offset(offset).limit(main_limit)
            
            result = await self.db.execute(stmt)
            tests = result.scalars().all()
            results.extend([self._test_to_dict(t, is_archived=False) for t in tests])
        
        # 如果主表数据不够，从归档表补充
        remaining = page_size - len(results)
        if remaining > 0:
            archive_offset = max(0, offset - main_total)
            stmt = select(TestArchiveModel).where(
                TestArchiveModel.student_id == student_id
            ).order_by(TestArchiveModel.created_at.desc()).offset(archive_offset).limit(remaining)
            
            result = await self.db.execute(stmt)
            archives = result.scalars().all()
            results.extend([self._archive_to_dict(a) for a in archives])
        
        return results, total
    
    async def get_archived_test_for_share(
        self, 
        original_test_id: int
    ) -> Optional[dict]:
        """
        为分享链接查询归档测评
        
        当 report_share_tokens 引用的 test_id 已归档时使用
        """
        stmt = select(TestArchiveModel).options(
            selectinload(TestArchiveModel.items)
        ).where(TestArchiveModel.original_id == original_test_id)
        
        result = await self.db.execute(stmt)
        archive = result.scalar_one_or_none()
        
        if archive:
            return self._archive_to_dict(archive)
        return None
    
    def _test_to_dict(self, test: TestModel, is_archived: bool = False) -> dict:
        """将 TestModel 转换为字典"""
        raw_data = test.raw_data if hasattr(test, 'raw_data') else None
        
        return {
            "id": test.id,
            "student_id": test.student_id,
            "level": test.level,
            "unit": test.unit,
            "status": test.status,
            "total_score": float(test.total_score) if test.total_score else None,
            "part1_score": float(test.part1_score) if test.part1_score else None,
            "part2_score": float(test.part2_score) if test.part2_score else None,
            "star_level": test.star_level,
            "part1_audio_url": test.part1_audio_url,
            "part2_audio_url": test.part2_audio_url,
            "part2_transcript": test.part2_transcript,
            "failure_reason": test.failure_reason,
            "retry_count": test.retry_count,
            # 大 JSON 字段优先从 raw_data 获取
            "part1_raw_result": (raw_data.part1_raw_result if raw_data else None) or test.part1_raw_result,
            "part2_raw_result": (raw_data.part2_raw_result if raw_data else None) or test.part2_raw_result,
            "tokens_used": (raw_data.tokens_used if raw_data else None) or test.tokens_used,
            "summary_highlights": (raw_data.summary_highlights if raw_data else None) or test.summary_highlights,
            "summary_weaknesses": (raw_data.summary_weaknesses if raw_data else None) or test.summary_weaknesses,
            "summary_weekly_plan": (raw_data.summary_weekly_plan if raw_data else None) or test.summary_weekly_plan,
            "summary_dimension_feedback": (raw_data.summary_dimension_feedback if raw_data else None) or test.summary_dimension_feedback,
            "summary_generated_at": test.summary_generated_at,
            "interpretation_pages": (raw_data.interpretation_pages if raw_data else None) or test.interpretation_pages,
            "interpretation_parent_script": (raw_data.interpretation_parent_script if raw_data else None) or test.interpretation_parent_script,
            "interpretation_generated_at": test.interpretation_generated_at,
            "interpretation_status": test.interpretation_status,
            "report_override": (raw_data.report_override if raw_data else None) or test.report_override,
            "created_at": test.created_at,
            "updated_at": test.updated_at,
            "completed_at": test.completed_at,
            "items": [
                {
                    "id": item.id,
                    "question_no": item.question_no,
                    "score": item.score,
                    "feedback": item.feedback,
                    "evidence": item.evidence,
                    "created_at": item.created_at
                }
                for item in (test.items or [])
            ],
            "is_archived": is_archived
        }
    
    def _archive_to_dict(self, archive: TestArchiveModel) -> dict:
        """将 TestArchiveModel 转换为字典"""
        return {
            "id": archive.original_id,  # 使用原始 ID，保持兼容
            "student_id": archive.student_id,
            "level": archive.level,
            "unit": archive.unit,
            "status": archive.status,
            "total_score": float(archive.total_score) if archive.total_score else None,
            "part1_score": float(archive.part1_score) if archive.part1_score else None,
            "part2_score": float(archive.part2_score) if archive.part2_score else None,
            "star_level": archive.star_level,
            "part1_audio_url": archive.part1_audio_url,
            "part2_audio_url": archive.part2_audio_url,
            "part2_transcript": archive.part2_transcript,
            "failure_reason": archive.failure_reason,
            "retry_count": archive.retry_count,
            # 归档表直接存储大 JSON
            "part1_raw_result": archive.part1_raw_result,
            "part2_raw_result": archive.part2_raw_result,
            "tokens_used": archive.tokens_used,
            "summary_highlights": archive.summary_highlights,
            "summary_weaknesses": archive.summary_weaknesses,
            "summary_weekly_plan": archive.summary_weekly_plan,
            "summary_dimension_feedback": archive.summary_dimension_feedback,
            "summary_generated_at": archive.summary_generated_at,
            "interpretation_pages": archive.interpretation_pages,
            "interpretation_parent_script": archive.interpretation_parent_script,
            "interpretation_generated_at": archive.interpretation_generated_at,
            "interpretation_status": None,  # 归档后不再更新
            "report_override": archive.report_override,
            "created_at": archive.created_at,
            "updated_at": archive.updated_at,
            "completed_at": archive.completed_at,
            "items": [
                {
                    "id": item.original_id,
                    "question_no": item.question_no,
                    "score": item.score,
                    "feedback": item.feedback,
                    "evidence": item.evidence,
                    "created_at": item.created_at
                }
                for item in (archive.items or [])
            ],
            "is_archived": True,
            "archived_at": archive.archived_at
        }
