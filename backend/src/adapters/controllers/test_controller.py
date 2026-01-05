"""
Test Controller
Handles test-related endpoints including Part 1 and Part 2 evaluation.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id
from src.infrastructure.responses import ErrorResponse
from src.adapters.gateways.xunfei_client import XunfeiGateway
from src.use_cases.evaluate_part1 import (
    EvaluatePart1UseCase,
    Part1EvaluationRequest,
    Part1EvaluationResponse
)

router = APIRouter()


class Part1ScoreResponse(BaseModel):
    """Response for Part 1 score."""
    success: bool
    test_id: int
    score: Optional[float] = None
    fluency_score: Optional[float] = None
    pronunciation_score: Optional[float] = None
    message: str = "Evaluation completed"


class TestStatusResponse(BaseModel):
    """Response for test status check."""
    test_id: int
    status: str
    part1_score: Optional[float] = None
    part2_score: Optional[float] = None
    total_score: Optional[float] = None
    star_level: Optional[int] = None


@router.post(
    "/{test_id}/part1",
    response_model=Part1ScoreResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def submit_part1(
    test_id: int,
    reference_text: str = Form(..., description="The text student should read"),
    audio: UploadFile = File(..., description="Audio file (PCM 16kHz 16bit)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit Part 1 audio for evaluation.
    
    The audio is sent to Xunfei for real-time evaluation.
    Returns immediately with the score.
    """
    # Read audio data
    audio_data = await audio.read()
    
    if len(audio_data) < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "AudioTooShort", "message": "录音时间太短，请重试"}
        )
    
    # Create use case and execute
    xunfei_gateway = XunfeiGateway()
    use_case = EvaluatePart1UseCase(db, xunfei_gateway)
    
    result = await use_case.execute(
        Part1EvaluationRequest(
            test_id=test_id,
            reference_text=reference_text,
            audio_data=audio_data
        )
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "EvaluationFailed", "message": result.error}
        )
    
    return Part1ScoreResponse(
        success=True,
        test_id=result.test_id,
        score=result.score,
        fluency_score=result.fluency_score,
        pronunciation_score=result.pronunciation_score,
        message="Part 1 评分完成"
    )


@router.get(
    "/{test_id}",
    response_model=TestStatusResponse
)
async def get_test_status(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current test status and scores.
    """
    from sqlalchemy import select
    from src.adapters.repositories.models import TestModel
    
    stmt = select(TestModel).where(TestModel.id == test_id)
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "TestNotFound", "message": "测评记录不存在"}
        )
    
    return TestStatusResponse(
        test_id=test.id,
        status=test.status,
        part1_score=float(test.part1_score) if test.part1_score else None,
        part2_score=float(test.part2_score) if test.part2_score else None,
        total_score=float(test.total_score) if test.total_score else None,
        star_level=test.star_level
    )
