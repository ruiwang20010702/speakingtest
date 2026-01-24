"""
Test Controller
Handles test-related endpoints including Part 1 and Part 2 evaluation.

Security:
- All endpoints require authentication
- Ownership validation: users can only access their own tests
- Students: can only access tests where test.student_id == user_id
- Teachers: can only access tests of students they created
- Admins: can access all tests
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from src.infrastructure.database import get_db, get_db_readonly

logger = logging.getLogger(__name__)
from fastapi import Request
from src.infrastructure.auth import get_current_user_id, decode_token, oauth2_scheme, get_token_from_request
from src.infrastructure.responses import ErrorResponse
from src.adapters.gateways.oss_client import get_oss_client
from src.adapters.repositories.models import TestModel, StudentProfileModel
from src.use_cases.evaluate_part1 import (
    SubmitPart1UseCase,
    SubmitPart1Request,
)


async def verify_test_ownership(
    test_id: int,
    user_id: int,
    role: str,
    db: AsyncSession,
    load_full: bool = False
) -> TestModel:
    """
    Verify that the user has permission to access the test.
    
    - Students: can only access their own tests
    - Teachers: can only access tests of their students
    - Admins: can access all tests
    
    Args:
        load_full: If True, loads full TestModel. If False, only loads essential fields
                   for ownership check (performance optimization).
    
    Returns the test if authorized, raises HTTPException otherwise.
    """
    # Performance: Only select fields needed for ownership check
    if load_full:
        stmt = select(TestModel).where(TestModel.id == test_id)
    else:
        # Only select fields needed for ownership verification
        stmt = select(
            TestModel.id,
            TestModel.student_id,
            TestModel.status,
            TestModel.level,
            TestModel.unit
        ).where(TestModel.id == test_id)
    
    result = await db.execute(stmt)
    
    if load_full:
        test = result.scalar_one_or_none()
    else:
        row = result.first()
        if row:
            # Create a lightweight object for ownership check
            test = type('TestBasic', (), {
                'id': row.id,
                'student_id': row.student_id,
                'status': row.status,
                'level': row.level,
                'unit': row.unit
            })()
        else:
            test = None
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "TestNotFound", "message": "测评记录不存在"}
        )
    
    # Admin can access all
    if role == "admin":
        return test
    
    # Student can only access their own test
    if role == "student":
        if test.student_id != user_id:
            logger.warning(f"Student {user_id} tried to access test {test_id} (owner: {test.student_id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Forbidden", "message": "无权访问此测评"}
            )
        return test
    
    # Teacher can only access tests of their students
    if role == "teacher":
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == test.student_id,
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            logger.warning(f"Teacher {user_id} tried to access test {test_id} (student: {test.student_id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Forbidden", "message": "无权访问此测评（非您的学生）"}
            )
        return test
    
    # Unknown role - deny
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Forbidden", "message": "无权访问"}
    )


async def get_current_user_with_role(
    request: Request,
    auth_header: str = Depends(oauth2_scheme)
):
    """Get current user ID and role from token. Supports both Cookie and Authorization header."""
    token = get_token_from_request(request, auth_header)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    return {"user_id": token_data.user_id, "role": token_data.role}

router = APIRouter()


class Part1SubmitResponse(BaseModel):
    """Response for Part 1 async submission."""
    success: bool
    test_id: int
    task_id: Optional[str] = None
    message: str = "评测任务已提交"


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
    response_model=Part1SubmitResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def submit_part1(
    test_id: int,
    reference_text: str = Form(..., description="The text student should read"),
    audio: UploadFile = File(..., description="Audio file"),
    user: dict = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit Part 1 audio for evaluation (ASYNC).
    
    1. Upload audio to OSS
    2. Enqueue evaluation task
    3. Return immediately with task_id
    
    The evaluation runs in the background. Check test status for results.
    
    Security: Only the student who owns the test can submit audio.
    """
    # Verify ownership - students can only submit to their own tests
    await verify_test_ownership(test_id, user["user_id"], user["role"], db)
    
    # 1. Read audio data
    audio_data = await audio.read()
    
    if len(audio_data) < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "AudioTooShort", "message": "录音时间太短，请重试"}
        )
    
    # 2. Get extension
    extension = "mp3"
    if audio.filename:
        ext = audio.filename.split(".")[-1].lower()
        if ext in ["mp3", "wav", "m4a", "webm"]:
            extension = ext
    
    # 3. Upload to OSS first (this is fast, ~1-2s)
    oss_client = get_oss_client()
    oss_result = await oss_client.upload_audio(
        audio_data=audio_data,
        test_id=test_id,
        part="part1",
        extension=extension
    )
    
    if not oss_result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UploadFailed", "message": oss_result.error}
        )
    
    # 4. Enqueue evaluation task (立即返回)
    use_case = SubmitPart1UseCase(db)
    result = await use_case.execute(
        SubmitPart1Request(
            test_id=test_id,
            audio_url=oss_result.url,
            reference_text=reference_text
        )
    )
    
    if not result.success:
        logger.error(f"Part 1 提交失败: {result.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SubmitFailed", "message": result.message}
        )
    
    return Part1SubmitResponse(
        success=True,
        test_id=test_id,
        task_id=result.task_id,
        message="Part 1 评测任务已提交，正在后台处理"
    )


@router.get(
    "/{test_id}",
    response_model=TestStatusResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def get_test_status(
    test_id: int,
    user: dict = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db_readonly)  # 只读操作，无需 commit
):
    """
    Get current test status and scores.
    
    Security: Users can only view tests they own or (for teachers) their students' tests.
    """
    # Verify ownership - load full test object to access score fields
    test = await verify_test_ownership(test_id, user["user_id"], user["role"], db, load_full=True)
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
    # questions 参数现在是可选的，默认从 DB 加载
    questions: Optional[list] = None  # 可选：覆盖默认题目


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
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def submit_part2(
    test_id: int,
    request: Part2SubmitRequest,
    user: dict = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """
    提交 Part 2 录音进行异步评测。
    
    题目会根据 Test 的 Level/Unit 自动从题库加载。
    录音会被发送到消息队列，由后台 Worker 调用 Qwen API 评测。
    评测完成后可通过 GET /tests/{id} 查询结果。
    
    注意：这是异步操作，不会立即返回评分结果。
    
    Security: Only the student who owns the test can submit audio.
    """
    from sqlalchemy import select, and_
    from src.adapters.repositories.models import QuestionModel
    from src.use_cases.evaluate_part2 import SubmitPart2UseCase, SubmitPart2Request
    
    # Verify ownership - students can only submit to their own tests
    test = await verify_test_ownership(test_id, user["user_id"], user["role"], db)
    
    # 2. 确定题目来源
    questions = request.questions
    if not questions:
        # 从数据库加载题目
        stmt = select(QuestionModel).where(
            and_(
                QuestionModel.level == test.level,
                QuestionModel.unit == test.unit,
                QuestionModel.is_active == True
            )
        ).order_by(QuestionModel.question_no)
        
        result = await db.execute(stmt)
        db_questions = result.scalars().all()
        
        if not db_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "NoQuestions", "message": f"题库中没有 {test.level} - {test.unit} 的题目，请先添加"}
            )
        
        questions = [
            {
                "no": q.question_no,
                "question": q.question,
                "reference_answer": q.reference_answer or "无"
            }
            for q in db_questions
        ]
    
    # 3. 提交评测任务
    use_case = SubmitPart2UseCase(db)
    result = await use_case.execute(
        SubmitPart2Request(
            test_id=test_id,
            audio_url=request.audio_url,
            questions=questions
        )
    )
    
    if not result.success:
        logger.error(f"Part 2 提交失败: {result.message}")
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
    part1_accuracy: Optional[float] = None
    part1_fluency: Optional[float] = None
    part1_pronunciation: Optional[float] = None
    part1_integrity: Optional[float] = None
    part1_overall_suggestion: list[str] = []
    
    # Part 2
    part2_score: Optional[float] = None
    part2_fluency: Optional[float] = None
    part2_pronunciation: Optional[float] = None
    part2_confidence: Optional[float] = None
    part2_vocabulary: Optional[float] = None
    part2_sentence: Optional[float] = None
    part2_transcript: Optional[str] = None
    part2_items: list[TestItemResponse] = []
    part2_overall_suggestion: list[str] = []
    
    # 时间
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.get(
    "/{test_id}/report",
    response_model=FullReportResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def get_full_report(
    test_id: int,
    user: dict = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db_readonly)  # 只读操作，无需 commit
):
    """
    获取完整测评报告。
    
    包含:
    - Part 1 分数（朗读评测）
    - Part 2 逐题评分 + 转写 + 建议
    - 总分和星级
    
    注意: 只有 status="completed" 时 Part 2 数据才完整。
    
    Security: Users can only view reports for tests they own or (for teachers) their students' tests.
    """
    from sqlalchemy.orm import selectinload
    from src.adapters.repositories.models import TestItemModel, TestRawDataModel
    
    # Verify ownership first
    await verify_test_ownership(test_id, user["user_id"], user["role"], db)
    
    # 查询测评记录（含逐题评分）- 优化：eager load raw_data 避免 N+1
    stmt = (
        select(TestModel)
        .options(
            selectinload(TestModel.items),
            selectinload(TestModel.raw_data)  # 加载大 JSON 分离表
        )
        .where(TestModel.id == test_id)
    )
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    # 获取学生姓名
    student_name = None
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile:
        student_name = profile.student_name
    
    # 优化：优先从 raw_data 分离表读取大 JSON，fallback 到主表
    # 注意：test.raw_data 是列表（backref 默认行为），取第一个元素
    raw_data = test.raw_data[0] if test.raw_data else None
    part1_raw = (raw_data.part1_raw_result if raw_data else None) or test.part1_raw_result
    part2_raw = (raw_data.part2_raw_result if raw_data else None) or test.part2_raw_result
    
    # 解析 Part 1 详细分数
    part1_accuracy = None
    part1_fluency = None
    part1_pronunciation = None
    part1_integrity = None
    part1_overall_suggestion = []
    if part1_raw and isinstance(part1_raw, dict):
        part1_accuracy = part1_raw.get("accuracy_score")
        part1_fluency = part1_raw.get("fluency_score")
        part1_pronunciation = part1_raw.get("pronunciation_score")
        part1_integrity = part1_raw.get("integrity_score")
        part1_overall_suggestion = part1_raw.get("part1_overall_suggestion", [])
    
    # 解析 Part 2 详细分数
    part2_fluency = None
    part2_pronunciation = None
    part2_confidence = None
    part2_vocabulary = None
    part2_sentence = None
    part2_overall_suggestion = []
    
    if part2_raw and isinstance(part2_raw, dict):
        part2_fluency = part2_raw.get("fluency_score")
        part2_pronunciation = part2_raw.get("pronunciation_score")
        part2_confidence = part2_raw.get("confidence_score")
        part2_vocabulary = part2_raw.get("vocabulary_score")
        part2_sentence = part2_raw.get("sentence_score")
        part2_overall_suggestion = part2_raw.get("part2_overall_suggestion", [])
    
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
    
    return FullReportResponse(
        test_id=test.id,
        status=test.status,
        student_name=student_name,
        level=test.level,
        unit=test.unit,
        total_score=float(test.total_score) if test.total_score else None,
        star_level=test.star_level,
        part1_score=float(test.part1_score) if test.part1_score else None,
        part1_accuracy=part1_accuracy,
        part1_fluency=part1_fluency,
        part1_pronunciation=part1_pronunciation,
        part1_integrity=part1_integrity,
        part1_overall_suggestion=part1_overall_suggestion,
        part2_score=float(test.part2_score) if test.part2_score else None,
        part2_fluency=part2_fluency,
        part2_pronunciation=part2_pronunciation,
        part2_confidence=part2_confidence,
        part2_vocabulary=part2_vocabulary,
        part2_sentence=part2_sentence,
        part2_transcript=test.part2_transcript,
        part2_items=part2_items,
        part2_overall_suggestion=part2_overall_suggestion,
        created_at=test.created_at.isoformat() if test.created_at else None,
        completed_at=test.completed_at.isoformat() if test.completed_at else None
    )
