"""
Part 1 Evaluation Use Case
Orchestrates the speech evaluation flow for Part 1 (reading).
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import TestModel
from src.adapters.gateways.xunfei_client import XunfeiGateway, XunfeiEvaluationResult


@dataclass
class Part1EvaluationRequest:
    """Request for Part 1 evaluation."""
    test_id: int
    reference_text: str
    audio_data: bytes


@dataclass
class Part1EvaluationResponse:
    """Response from Part 1 evaluation."""
    success: bool
    test_id: int
    score: Optional[float] = None
    fluency_score: Optional[float] = None
    pronunciation_score: Optional[float] = None
    error: Optional[str] = None


class EvaluatePart1UseCase:
    """
    Use case for evaluating Part 1 reading.
    
    Flow:
    1. Validate test exists and is in correct state
    2. Call Xunfei API for evaluation
    3. Parse and store scores
    4. Update test status
    """

    def __init__(self, db: AsyncSession, xunfei_gateway: XunfeiGateway):
        self.db = db
        self.xunfei = xunfei_gateway

    async def execute(self, request: Part1EvaluationRequest) -> Part1EvaluationResponse:
        """
        Execute Part 1 evaluation.
        
        Args:
            request: Part1EvaluationRequest with test_id, text, and audio
            
        Returns:
            Part1EvaluationResponse with scores or error
        """
        # 1. Find test
        stmt = select(TestModel).where(TestModel.id == request.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()

        if not test:
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error="Test not found"
            )

        # 2. Check test state
        if test.status not in ("pending", "part1_done"):
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error=f"Invalid test status: {test.status}"
            )

        logger.info(f"Starting Part 1 evaluation for test {request.test_id}")

        # 3. Call Xunfei API
        try:
            xunfei_result = await self.xunfei.evaluate_reading_sync(
                reference_text=request.reference_text,
                audio_data=request.audio_data
            )
        except Exception as e:
            logger.exception(f"Xunfei API error: {e}")
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error=f"Evaluation service error: {str(e)}"
            )

        # 4. Handle result
        if not xunfei_result.success:
            test.failure_reason = xunfei_result.error_message
            test.retry_count += 1
            await self.db.commit()
            
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error=xunfei_result.error_message
            )

        # 5. Store scores
        test.part1_score = xunfei_result.total_score
        test.part1_raw_result = xunfei_result.to_dict()
        test.status = "part1_done"
        test.updated_at = datetime.utcnow()

        await self.db.commit()
        
        logger.info(f"Part 1 completed for test {request.test_id}, score: {xunfei_result.total_score}")

        return Part1EvaluationResponse(
            success=True,
            test_id=request.test_id,
            score=xunfei_result.total_score,
            fluency_score=xunfei_result.fluency_score,
            pronunciation_score=xunfei_result.pronunciation_score
        )
