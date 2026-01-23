"""
Test Raw Data Repository
Handles operations for the test_raw_data table (large JSON storage).

Performance Note:
- Use this repository for reading/writing raw evaluation data
- The tests table has a trigger that auto-syncs to test_raw_data
- For list/stats queries, use tests table (compact, no large JSON)
- For detail views, join with test_raw_data or query directly here
"""
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import TestRawDataModel


class TestRawDataRepository:
    """Repository for test_raw_data table operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_test_id(self, test_id: int) -> Optional[TestRawDataModel]:
        """Get raw data by test ID."""
        stmt = select(TestRawDataModel).where(TestRawDataModel.test_id == test_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_part1_raw_result(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get Part1 raw result only."""
        stmt = select(TestRawDataModel.part1_raw_result).where(
            TestRawDataModel.test_id == test_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_part2_raw_result(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get Part2 raw result only."""
        stmt = select(TestRawDataModel.part2_raw_result).where(
            TestRawDataModel.test_id == test_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_interpretation(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get interpretation data."""
        stmt = select(
            TestRawDataModel.interpretation_pages,
            TestRawDataModel.interpretation_parent_script
        ).where(TestRawDataModel.test_id == test_id)
        result = await self.db.execute(stmt)
        row = result.first()
        if row:
            return {
                "pages": row.interpretation_pages,
                "parent_script": row.interpretation_parent_script
            }
        return None
    
    async def get_report_override(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get report override data."""
        stmt = select(TestRawDataModel.report_override).where(
            TestRawDataModel.test_id == test_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_tokens_used(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get tokens usage statistics."""
        stmt = select(TestRawDataModel.tokens_used).where(
            TestRawDataModel.test_id == test_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert(
        self,
        test_id: int,
        part1_raw_result: Optional[Dict] = None,
        part2_raw_result: Optional[Dict] = None,
        tokens_used: Optional[Dict] = None,
        interpretation_pages: Optional[Dict] = None,
        interpretation_parent_script: Optional[str] = None,
        report_override: Optional[Dict] = None
    ) -> TestRawDataModel:
        """
        Insert or update raw data for a test.
        
        Note: The tests table trigger usually handles this automatically.
        Use this method only for direct raw_data operations.
        """
        existing = await self.get_by_test_id(test_id)
        
        if existing:
            # Update existing record
            update_data = {}
            if part1_raw_result is not None:
                update_data["part1_raw_result"] = part1_raw_result
            if part2_raw_result is not None:
                update_data["part2_raw_result"] = part2_raw_result
            if tokens_used is not None:
                update_data["tokens_used"] = tokens_used
            if interpretation_pages is not None:
                update_data["interpretation_pages"] = interpretation_pages
            if interpretation_parent_script is not None:
                update_data["interpretation_parent_script"] = interpretation_parent_script
            if report_override is not None:
                update_data["report_override"] = report_override
            
            if update_data:
                stmt = update(TestRawDataModel).where(
                    TestRawDataModel.test_id == test_id
                ).values(**update_data)
                await self.db.execute(stmt)
                
            return await self.get_by_test_id(test_id)
        else:
            # Insert new record
            raw_data = TestRawDataModel(
                test_id=test_id,
                part1_raw_result=part1_raw_result,
                part2_raw_result=part2_raw_result,
                tokens_used=tokens_used or {},
                interpretation_pages=interpretation_pages,
                interpretation_parent_script=interpretation_parent_script,
                report_override=report_override
            )
            self.db.add(raw_data)
            await self.db.flush()
            return raw_data
    
    async def update_part1_raw_result(self, test_id: int, raw_result: Dict[str, Any]):
        """Update Part1 raw result."""
        await self.upsert(test_id, part1_raw_result=raw_result)
    
    async def update_part2_raw_result(self, test_id: int, raw_result: Dict[str, Any]):
        """Update Part2 raw result."""
        await self.upsert(test_id, part2_raw_result=raw_result)
    
    async def update_interpretation(
        self,
        test_id: int,
        pages: Optional[Dict] = None,
        parent_script: Optional[str] = None
    ):
        """Update interpretation data."""
        await self.upsert(
            test_id,
            interpretation_pages=pages,
            interpretation_parent_script=parent_script
        )
    
    async def update_report_override(self, test_id: int, override: Dict[str, Any]):
        """Update report override."""
        await self.upsert(test_id, report_override=override)
    
    async def add_tokens_used(self, test_id: int, tokens: Dict[str, int]):
        """Add to tokens used statistics (merge with existing)."""
        existing = await self.get_tokens_used(test_id) or {}
        
        # Merge token counts
        for key, value in tokens.items():
            existing[key] = existing.get(key, 0) + value
        
        await self.upsert(test_id, tokens_used=existing)
