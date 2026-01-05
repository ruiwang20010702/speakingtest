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


# ============================================
# Part 2 提交端点
# ============================================

class Part2SubmitRequest(BaseModel):
    """Part 2 提交请求"""
    audio_url: str  # OSS 音频 URL
    questions: list  # 12 道题目


class Part2SubmitResponse(BaseModel):
    """Part 2 提交响应"""
    success: bool
    task_id: Optional[str] = None
    message: str


@router.post(
    "/{test_id}/part2",
    response_model=Part2SubmitResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def submit_part2(
    test_id: int,
    request: Part2SubmitRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    提交 Part 2 录音进行异步评测。
    
    录音会被发送到消息队列，由后台 Worker 调用 Qwen API 评测。
    评测完成后可通过 GET /tests/{id} 查询结果。
    
    注意：这是异步操作，不会立即返回评分结果。
    """
    from src.use_cases.evaluate_part2 import SubmitPart2UseCase, SubmitPart2Request
    
    use_case = SubmitPart2UseCase(db)
    result = await use_case.execute(
        SubmitPart2Request(
            test_id=test_id,
            audio_url=request.audio_url,
            questions=request.questions
        )
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SubmitFailed", "message": result.message}
        )
    
    return Part2SubmitResponse(
        success=True,
        task_id=result.task_id,
        message=result.message
    )


# ============================================
# 完整报告端点
# ============================================

class TestItemResponse(BaseModel):
    """单题评分"""
    question_no: int
    score: int  # 0, 1, 2
    feedback: Optional[str] = None
    evidence: Optional[str] = None


class FullReportResponse(BaseModel):
    """完整测评报告"""
    test_id: int
    status: str
    student_name: Optional[str] = None
    level: str
    unit: str
    
    # 总分
    total_score: Optional[float] = None
    star_level: Optional[int] = None
    
    # Part 1
    part1_score: Optional[float] = None
    part1_fluency: Optional[float] = None
    part1_pronunciation: Optional[float] = None
    
    # Part 2
    part2_score: Optional[float] = None
    part2_transcript: Optional[str] = None
    part2_items: list[TestItemResponse] = []
    part2_suggestions: list[str] = []
    
    # 时间
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.get(
    "/{test_id}/report",
    response_model=FullReportResponse,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def get_full_report(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取完整测评报告。
    
    包含:
    - Part 1 分数（朗读评测）
    - Part 2 逐题评分 + 转写 + 建议
    - 总分和星级
    
    注意: 只有 status="completed" 时 Part 2 数据才完整。
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.adapters.repositories.models import TestModel, TestItemModel, StudentProfileModel
    
    # 查询测评记录（含逐题评分）
    stmt = (
        select(TestModel)
        .options(selectinload(TestModel.items))
        .where(TestModel.id == test_id)
    )
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "TestNotFound", "message": "测评记录不存在"}
        )
    
    # 获取学生姓名
    student_name = None
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile:
        student_name = profile.student_name
    
    # 解析 Part 1 详细分数
    part1_fluency = None
    part1_pronunciation = None
    if test.part1_raw_result:
        raw = test.part1_raw_result
        if isinstance(raw, dict):
            part1_fluency = raw.get("fluency_score")
            part1_pronunciation = raw.get("pronunciation_score")
    
    # 构建 Part 2 逐题响应
    part2_items = [
        TestItemResponse(
            question_no=item.question_no,
            score=item.score,
            feedback=item.feedback,
            evidence=item.evidence
        )
        for item in sorted(test.items, key=lambda x: x.question_no)
    ]
    
    # 解析建议（如果存储在 raw 中）
    part2_suggestions = []
    # 可以从 part2_raw_result 中提取 overall_suggestion
    
    return FullReportResponse(
        test_id=test.id,
        status=test.status,
        student_name=student_name,
        level=test.level,
        unit=test.unit,
        total_score=float(test.total_score) if test.total_score else None,
        star_level=test.star_level,
        part1_score=float(test.part1_score) if test.part1_score else None,
        part1_fluency=part1_fluency,
        part1_pronunciation=part1_pronunciation,
        part2_score=float(test.part2_score) if test.part2_score else None,
        part2_transcript=test.part2_transcript,
        part2_items=part2_items,
        part2_suggestions=part2_suggestions,
        created_at=test.created_at.isoformat() if test.created_at else None,
        completed_at=test.completed_at.isoformat() if test.completed_at else None
    )
