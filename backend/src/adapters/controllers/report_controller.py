"""
Report Controller
Handles report viewing and sharing for teachers and parents.
"""
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id, get_current_user_role
from src.adapters.repositories.models import (
    TestModel, TestItemModel, StudentProfileModel, ReportShareTokenModel
)


router = APIRouter()


# ============================================
# Response Schemas
# ============================================

class TestSummary(BaseModel):
    """Summary of a test for list view."""
    id: int
    level: str
    unit: str
    status: str
    total_score: Optional[float] = None
    part1_score: Optional[float] = None
    part2_score: Optional[float] = None
    star_level: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    entry_url: Optional[str] = None


class TestItemDetail(BaseModel):
    """Detail of a single test item (Part 2 question)."""
    question_no: int
    score: int
    feedback: Optional[str] = None
    evidence: Optional[str] = None


class TestReportDetail(BaseModel):
    """Full test report detail."""
    id: int
    student_id: int
    student_name: str
    level: str
    unit: str
    status: str
    total_score: Optional[float] = None
    part1_score: Optional[float] = None
    part2_score: Optional[float] = None
    star_level: Optional[int] = None
    part1_audio_url: Optional[str] = None
    part2_audio_url: Optional[str] = None
    part2_transcript: Optional[str] = None
    part1_raw_result: Optional[dict] = None
    items: List[TestItemDetail] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
    entry_url: Optional[str] = None


class ShareLinkResponse(BaseModel):
    """Response for share link generation."""
    token: str
    share_url: str
    message: str


# ============================================
# Student Test History
# ============================================

@router.get(
    "/students/{student_id}/tests",
    response_model=List[TestSummary],
    summary="获取学生测评历史",
    description="获取指定学生的所有测评记录列表。"
)
async def get_student_tests(
    student_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Get test history for a specific student.
    
    - Teacher can only view their own students
    - Admin can view all students
    """
    # Verify ownership (RBAC)
    if role != "admin":
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == student_id,
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this student's tests"
            )
    
    # Get tests
    stmt = select(TestModel).where(
        TestModel.student_id == student_id
    ).order_by(TestModel.created_at.desc())
    
    result = await db.execute(stmt)
    tests = result.scalars().all()

    # Get active tokens for this student to populate entry_url for pending tests
    from src.adapters.repositories.models import StudentEntryTokenModel
    token_stmt = select(StudentEntryTokenModel).where(
        StudentEntryTokenModel.student_id == student_id,
        StudentEntryTokenModel.expires_at > datetime.utcnow()
    ).order_by(StudentEntryTokenModel.created_at.desc())
    
    token_result = await db.execute(token_stmt)
    tokens = token_result.scalars().all()
    
    # Map (level, unit) -> token
    token_map = {}
    for t in tokens:
        key = (t.level, t.unit)
        if key not in token_map:
            token_map[key] = t.token

    # Base URL for student H5 (TODO: Move to config)
    BASE_URL = "http://localhost:3001/s"
    
    return [
        TestSummary(
            id=t.id,
            level=t.level,
            unit=t.unit,
            status=t.status,
            total_score=float(t.total_score) if t.total_score else None,
            part1_score=float(t.part1_score) if t.part1_score else None,
            part2_score=float(t.part2_score) if t.part2_score else None,
            star_level=t.star_level,
            created_at=t.created_at,
            completed_at=t.completed_at,
            entry_url=f"{BASE_URL}/{token_map.get((t.level, t.unit))}" if t.status != 'completed' and (t.level, t.unit) in token_map else None
        )
        for t in tests
    ]


# ============================================
# Test Report Detail
# ============================================

@router.get(
    "/tests/{test_id}",
    response_model=TestReportDetail,
    summary="获取测评报告详情",
    description="获取完整的测评报告，包括 Part1 和 Part2 的详细评分。"
)
async def get_test_report(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full test report detail.
    
    Includes:
    - Overall scores
    - Part 1 raw result (word-level scores)
    - Part 2 items (question-by-question)
    - Audio URLs for playback
    """
    # Get test with items
    stmt = select(TestModel).options(
        selectinload(TestModel.items)
    ).where(TestModel.id == test_id)
    
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # RBAC check
    if role != "admin":
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == test.student_id,
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this test"
            )
    
    # Get student name
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    student_profile = result.scalar_one_or_none()
    student_name = student_profile.student_name if student_profile else "Unknown"
    
    return TestReportDetail(
        id=test.id,
        student_id=test.student_id,
        student_name=student_name,
        level=test.level,
        unit=test.unit,
        status=test.status,
        total_score=float(test.total_score) if test.total_score else None,
        part1_score=float(test.part1_score) if test.part1_score else None,
        part2_score=float(test.part2_score) if test.part2_score else None,
        star_level=test.star_level,
        part1_audio_url=test.part1_audio_url,
        part2_audio_url=test.part2_audio_url,
        part2_transcript=test.part2_transcript,
        part1_raw_result=test.part1_raw_result,
        items=[
            TestItemDetail(
                question_no=item.question_no,
                score=item.score,
                feedback=item.feedback,
                evidence=item.evidence
            )
            for item in sorted(test.items, key=lambda x: x.question_no)
        ],
        created_at=test.created_at,
        completed_at=test.completed_at
    )


# ============================================
# Share Link Generation
# ============================================

@router.post(
    "/tests/{test_id}/share",
    response_model=ShareLinkResponse,
    summary="生成家长分享链接",
    description="为指定测评生成永久有效的家长查看链接。"
)
async def generate_share_link(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a share link for parents.
    
    - Link is permanent (no expiry)
    - Multiple calls return new tokens
    """
    # Get test
    stmt = select(TestModel).where(TestModel.id == test_id)
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # RBAC check
    if role != "admin":
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == test.student_id,
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
    
    # Generate token
    token = secrets.token_urlsafe(16)
    
    share = ReportShareTokenModel(
        token=token,
        test_id=test_id,
        expires_at=None,  # Permanent
        created_by=user_id
    )
    db.add(share)
    await db.commit()
    
    # TODO: Move base URL to config
    share_url = f"http://localhost:3000/p/{token}"
    
    return ShareLinkResponse(
        token=token,
        share_url=share_url,
        message="分享链接已生成"
    )


# ============================================
# Parent View (No Auth Required)
# ============================================

@router.get(
    "/reports/{token}",
    response_model=TestReportDetail,
    summary="家长查看报告",
    description="通过分享链接查看测评报告，无需登录。"
)
async def view_report_by_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    View report via share token.
    
    - No authentication required
    - Token must be valid (not revoked, not expired)
    """
    # Find share token
    stmt = select(ReportShareTokenModel).where(
        ReportShareTokenModel.token == token,
        ReportShareTokenModel.is_revoked == False
    )
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="链接无效或已过期"
        )
    
    # Increment view count
    share.view_count += 1
    await db.commit()
    
    # Check expiry (if set)
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="链接已过期"
        )
    
    # Get test with items
    stmt = select(TestModel).options(
        selectinload(TestModel.items)
    ).where(TestModel.id == share.test_id)
    
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在"
        )
    
    # Get student name
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    student_profile = result.scalar_one_or_none()
    student_name = student_profile.student_name if student_profile else "Unknown"
    
    return TestReportDetail(
        id=test.id,
        student_id=test.student_id,
        student_name=student_name,
        level=test.level,
        unit=test.unit,
        status=test.status,
        total_score=float(test.total_score) if test.total_score else None,
        part1_score=float(test.part1_score) if test.part1_score else None,
        part2_score=float(test.part2_score) if test.part2_score else None,
        star_level=test.star_level,
        part1_audio_url=test.part1_audio_url,
        part2_audio_url=test.part2_audio_url,
        part2_transcript=test.part2_transcript,
        part1_raw_result=test.part1_raw_result,
        items=[
            TestItemDetail(
                question_no=item.question_no,
                score=item.score,
                feedback=item.feedback,
                evidence=item.evidence
            )
            for item in sorted(test.items, key=lambda x: x.question_no)
        ],
        created_at=test.created_at,
        completed_at=test.completed_at
    )


# ============================================
# Report Interpretation (AI解读版)
# ============================================

from src.use_cases.report_interpretation import ReportInterpretationService


class InterpretationResponse(BaseModel):
    """Response for report interpretation."""
    highlights: List[str]
    weaknesses: List[str]
    evidence: List[str]
    suggestions: List[str]
    parent_script: str


@router.get(
    "/tests/{test_id}/interpretation",
    response_model=InterpretationResponse,
    summary="获取报告解读版",
    description="获取 AI 生成的报告解读，包含亮点、短板、证据和家长沟通话术。"
)
async def get_test_interpretation(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-generated interpretation for a test.
    
    Generates:
    - Highlights (亮点)
    - Weaknesses (短板)
    - Evidence points (证据点)
    - Suggestions (行动建议)
    - Parent communication script (家长沟通话术)
    """
    # Get test with items
    stmt = select(TestModel).options(
        selectinload(TestModel.items)
    ).where(TestModel.id == test_id)
    
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # RBAC check
    if role != "admin":
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == test.student_id,
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
    
    # Get student name
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    student_profile = result.scalar_one_or_none()
    student_name = student_profile.student_name if student_profile else "学生"
    
    # Generate interpretation
    service = ReportInterpretationService()
    interpretation = service.generate(
        student_name=student_name,
        level=test.level,
        total_score=float(test.total_score) if test.total_score else 0,
        part1_score=float(test.part1_score) if test.part1_score else 0,
        part2_score=float(test.part2_score) if test.part2_score else None,
        star_level=test.star_level or 1,
        part1_details=test.part1_raw_result,
        part2_items=[
            {"question_no": item.question_no, "score": item.score, "evidence": item.evidence}
            for item in test.items
        ] if test.items else None
    )
    
    return InterpretationResponse(
        highlights=interpretation.highlights,
        weaknesses=interpretation.weaknesses,
        evidence=interpretation.evidence,
        suggestions=interpretation.suggestions,
        parent_script=interpretation.parent_script
    )
