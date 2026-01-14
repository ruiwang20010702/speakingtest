"""
Report Controller
Handles report viewing and sharing for teachers and parents.
"""
import json
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id, get_current_user_role
from src.infrastructure.timezone import now as china_now
from src.infrastructure.config import get_settings
from src.adapters.repositories.models import (
    TestModel, TestItemModel, StudentProfileModel, ReportShareTokenModel
)
from src.infrastructure.audit import log_audit

settings = get_settings()


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
    is_interpreted: bool = False  # 是否已生成报告解读


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
        StudentEntryTokenModel.expires_at > china_now()
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
            entry_url=f"{BASE_URL}/{token_map.get((t.level, t.unit))}" if t.status != 'completed' and (t.level, t.unit) in token_map else None,
            is_interpreted=t.interpretation_generated_at is not None
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
# Report Editing (Full Override)
# ============================================

class RadarScoreOverride(BaseModel):
    """五维雷达图分数覆盖"""
    fluency: Optional[float] = None          # 流利度 0-100
    pronunciation: Optional[float] = None    # 发音 0-100
    confidence: Optional[float] = None       # 自信度 0-100
    vocabulary: Optional[float] = None       # 词汇 0-100
    sentence: Optional[float] = None         # 整句输出 0-100


class Part1WordOverride(BaseModel):
    """Part1 单词覆盖"""
    text: str                                # 单词文本
    status: str                              # perfect / unclear / failed
    score: Optional[float] = None            # 分数 0-100


class Part2ItemOverride(BaseModel):
    """Part2 题目覆盖"""
    question_no: int                         # 题号
    score: int                               # 0/1/2
    feedback: Optional[str] = None           # 反馈
    evidence: Optional[str] = None           # 学生回答


class SuggestionOverride(BaseModel):
    """学习建议覆盖"""
    highlights: Optional[List[str]] = None   # 亮点
    weaknesses: Optional[List[str]] = None   # 短板
    suggestions: Optional[List[str]] = None  # 建议
    parent_script: Optional[str] = None      # 家长话术


class ReportOverrideRequest(BaseModel):
    """
    报告覆盖数据，所有字段可选。
    只传入需要覆盖的字段，未传入的字段保持原始数据。
    """
    # 基础信息
    student_name: Optional[str] = None
    level: Optional[str] = None
    unit: Optional[str] = None
    
    # 分数
    part1_score: Optional[float] = None
    part2_score: Optional[float] = None
    total_score: Optional[float] = None
    star_level: Optional[int] = None
    
    # 五维雷达图
    radar: Optional[RadarScoreOverride] = None
    
    # Part1 词汇详情
    part1_words: Optional[List[Part1WordOverride]] = None
    
    # Part2 对话详情
    part2_items: Optional[List[Part2ItemOverride]] = None
    
    # 学习建议
    suggestion: Optional[SuggestionOverride] = None


class UpdateReportResponse(BaseModel):
    """Response for report update."""
    success: bool
    message: str
    override_keys: List[str] = []  # 被覆盖的字段列表


class OriginalReportData(BaseModel):
    """Original AI-generated report data for editing initialization."""
    student_name: str
    level: str
    unit: str
    part1_score: Optional[float] = None
    part2_score: Optional[float] = None
    total_score: Optional[float] = None
    star_level: Optional[int] = None
    # 五维雷达原始数据
    radar: Optional[dict] = None
    # Part1 词汇原始数据
    part1_words: Optional[List[dict]] = None
    # Part2 题目原始数据
    part2_items: Optional[List[dict]] = None
    # 学习建议原始数据
    suggestion: Optional[dict] = None


class GetReportOverrideResponse(BaseModel):
    """Response for getting current override data."""
    has_override: bool
    override: Optional[dict] = None
    original: Optional[OriginalReportData] = None  # 原始数据用于初始化


@router.get(
    "/tests/{test_id}/report/override",
    response_model=GetReportOverrideResponse,
    summary="获取报告覆盖数据",
    description="获取当前报告的手动编辑覆盖数据和原始数据。"
)
async def get_report_override(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """Get current report override data and original data for editing."""
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
    
    # Extract original radar data from part1/part2 raw results
    part1_raw = test.part1_raw_result or {}
    part2_raw = test.part2_raw_result or {}
    
    original_radar = {
        "fluency": part2_raw.get("fluency_score") or part1_raw.get("fluency_score") or 0,
        "pronunciation": part2_raw.get("pronunciation_score") or part1_raw.get("pronunciation_score") or 0,
        "confidence": part2_raw.get("confidence_score") or 0,
        "vocabulary": part2_raw.get("vocabulary_score") or part1_raw.get("accuracy_score") or 0,
        "sentence": part2_raw.get("sentence_score") or part1_raw.get("integrity_score") or 0,
    }
    
    # Extract Part1 words from part1_raw_result
    original_part1_words = []
    if part1_raw.get("details"):
        for detail in part1_raw["details"]:
            word_score = detail.get("score", 0)
            status = "perfect" if word_score >= 80 else ("unclear" if word_score >= 50 else "failed")
            original_part1_words.append({
                "text": detail.get("content", ""),
                "status": status,
                "score": word_score
            })
    
    # Extract Part2 items from test.items, with fallback to part2_raw_result
    original_part2_items = []
    
    # Build lookup from part2_raw_result for fallback
    raw_items_lookup = {}
    if test.part2_raw_result and isinstance(test.part2_raw_result, dict):
        raw_items = test.part2_raw_result.get("items", [])
        for raw_item in raw_items:
            raw_items_lookup[raw_item.get("no")] = raw_item
    
    for item in test.items:
        feedback = item.feedback or ""
        evidence = item.evidence or ""
        
        # Fallback to raw result if database fields are empty (legacy data)
        if not feedback or not evidence:
            raw_item = raw_items_lookup.get(item.question_no, {})
            if not feedback:
                feedback = raw_item.get("feedback", "")
            if not evidence:
                evidence = raw_item.get("transcript", "")
        
        original_part2_items.append({
            "question_no": item.question_no,
            "score": item.score,
            "feedback": feedback,
            "evidence": evidence
        })
    
    # Extract suggestion from interpretation
    original_suggestion = None
    if test.interpretation_generated_at:
        original_suggestion = {
            "highlights": json.loads(test.interpretation_highlights) if test.interpretation_highlights else [],
            "weaknesses": json.loads(test.interpretation_weaknesses) if test.interpretation_weaknesses else [],
            "suggestions": json.loads(test.interpretation_suggestions) if test.interpretation_suggestions else [],
            "parent_script": test.interpretation_parent_script or ""
        }
    
    original = OriginalReportData(
        student_name=student_name,
        level=test.level,
        unit=test.unit,
        part1_score=float(test.part1_score) if test.part1_score else None,
        part2_score=float(test.part2_score) if test.part2_score else None,
        total_score=float(test.total_score) if test.total_score else None,
        star_level=test.star_level,
        radar=original_radar,
        part1_words=original_part1_words if original_part1_words else None,
        part2_items=original_part2_items if original_part2_items else None,
        suggestion=original_suggestion
    )
    
    return GetReportOverrideResponse(
        has_override=test.report_override is not None,
        override=test.report_override,
        original=original
    )


@router.patch(
    "/tests/{test_id}/report",
    response_model=UpdateReportResponse,
    summary="编辑报告内容",
    description="教师编辑测评报告的所有字段，数据存入 report_override。"
)
async def update_report(
    test_id: int,
    request: ReportOverrideRequest,
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Update report by saving override data.
    
    - All edits are stored in report_override JSON column
    - Original data is preserved in separate columns
    - Supports partial updates (only override specified fields)
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
                detail="Not authorized to edit this report"
            )
    
    # Validate scores
    if request.part1_score is not None and not 0 <= request.part1_score <= 100:
        raise HTTPException(status_code=400, detail="part1_score must be 0-100")
    if request.part2_score is not None and not 0 <= request.part2_score <= 100:
        raise HTTPException(status_code=400, detail="part2_score must be 0-100")
    if request.total_score is not None and not 0 <= request.total_score <= 100:
        raise HTTPException(status_code=400, detail="total_score must be 0-100")
    if request.star_level is not None and not 1 <= request.star_level <= 5:
        raise HTTPException(status_code=400, detail="star_level must be 1-5")
    
    # Build override dict (only include non-None fields)
    override_data = {}
    override_keys = []
    
    # Convert request to dict, excluding None values
    request_dict = request.model_dump(exclude_none=True)
    
    # Merge with existing override
    existing_override = test.report_override or {}
    
    for key, value in request_dict.items():
        if value is not None:
            # Handle nested objects
            if isinstance(value, dict):
                # For nested dicts like radar, suggestion, merge them
                existing_nested = existing_override.get(key, {})
                if isinstance(existing_nested, dict):
                    existing_nested.update(value)
                    override_data[key] = existing_nested
                else:
                    override_data[key] = value
            elif isinstance(value, list):
                # For lists like part1_words, part2_items, replace entirely
                override_data[key] = value
            else:
                override_data[key] = value
            override_keys.append(key)
    
    if not override_keys:
        return UpdateReportResponse(
            success=True, 
            message="No changes provided",
            override_keys=[]
        )
    
    # Merge with existing override (preserve fields not in this request)
    final_override = {**existing_override, **override_data}
    
    # Save to report_override column
    test.report_override = final_override
    await db.commit()
    
    # Audit log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="UPDATE_REPORT_OVERRIDE",
        target_type="test",
        target_id=test_id,
        details={"override_keys": override_keys, "override_data": override_data},
        request=http_request
    )
    
    return UpdateReportResponse(
        success=True,
        message=f"Report override saved ({len(override_keys)} field(s))",
        override_keys=override_keys
    )


@router.delete(
    "/tests/{test_id}/report/override",
    response_model=UpdateReportResponse,
    summary="重置报告覆盖",
    description="清除报告的手动编辑内容，恢复为AI原始数据。"
)
async def reset_report_override(
    test_id: int,
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """Reset report override to original AI-generated data."""
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
    
    # Clear override
    test.report_override = None
    await db.commit()
    
    # Audit log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="RESET_REPORT_OVERRIDE",
        target_type="test",
        target_id=test_id,
        details={},
        request=http_request
    )
    
    return UpdateReportResponse(
        success=True,
        message="Report override cleared, restored to AI original data",
        override_keys=[]
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
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a share link for parents.
    
    - Link is permanent (no expiry)
    - Idempotent: returns existing valid token if available
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
    
    # Check for existing valid token (idempotent)
    stmt = select(ReportShareTokenModel).where(
        ReportShareTokenModel.test_id == test_id,
        ReportShareTokenModel.is_revoked == False
    ).order_by(ReportShareTokenModel.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    existing_share = result.scalar_one_or_none()
    
    if existing_share:
        # Reuse existing token
        share_url = f"{settings.FRONTEND_PARENT_URL}/p/{existing_share.token}"
        return ShareLinkResponse(
            token=existing_share.token,
            share_url=share_url,
            message="已有分享链接"
        )
    
    # Generate new token
    token = secrets.token_urlsafe(16)
    
    share = ReportShareTokenModel(
        token=token,
        test_id=test_id,
        expires_at=None,  # Permanent
        created_by=user_id
    )
    db.add(share)
    await db.commit()
    
    share_url = f"{settings.FRONTEND_PARENT_URL}/p/{token}"
    
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="SHARE_REPORT",
        target_type="test",
        target_id=test_id,
        details={"token": token},
        request=http_request
    )
    
    return ShareLinkResponse(
        token=token,
        share_url=share_url,
        message="分享链接已生成"
    )


# ============================================
# Share Link Revocation
# ============================================

class RevokeShareResponse(BaseModel):
    """Share link revocation response."""
    success: bool
    revoked_count: int
    message: str


@router.post(
    "/tests/{test_id}/revoke-share",
    response_model=RevokeShareResponse,
    summary="撤回家长分享链接",
    description="撤回指定测评的所有分享链接，使家长无法查看报告。"
)
async def revoke_share_link(
    test_id: int,
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke all share links for a test.
    
    - Requires teacher login or admin role
    - Sets is_revoked=True for all share tokens
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
    
    # Revoke all share tokens for this test
    from sqlalchemy import update
    stmt = (
        update(ReportShareTokenModel)
        .where(
            ReportShareTokenModel.test_id == test_id,
            ReportShareTokenModel.is_revoked == False
        )
        .values(is_revoked=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    
    revoked_count = result.rowcount
    
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="REVOKE_SHARE",
        target_type="test",
        target_id=test_id,
        details={"revoked_count": revoked_count},
        request=http_request
    )
    
    return RevokeShareResponse(
        success=True,
        revoked_count=revoked_count,
        message=f"Revoked {revoked_count} share link(s)"
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
    if share.expires_at and share.expires_at < china_now():
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
# Parent H5 Report (Fused Data)
# ============================================

from src.use_cases.parent_report import ParentReportService, RadarDimension, WordStatus, DialogueSample


class RadarDimensionResponse(BaseModel):
    """Single radar dimension response."""
    subject: str
    score: float
    fullMark: int = 100
    icon: str
    comment: str
    tags: List[str]


class WordStatusResponse(BaseModel):
    """Word status response."""
    text: str
    status: str  # 'perfect', 'unclear', 'failed'


class DialogueSampleResponse(BaseModel):
    """Dialogue sample response."""
    question_no: int
    question: str
    answer: str
    score: str
    feedback: str


class Part1DetailResponse(BaseModel):
    """Part 1 detail response."""
    score: float
    words: List[WordStatusResponse]


class Part2DetailResponse(BaseModel):
    """Part 2 detail response."""
    score: float
    best_sample: Optional[DialogueSampleResponse] = None
    weak_sample: Optional[DialogueSampleResponse] = None


class SuggestionResponse(BaseModel):
    """Suggestion response."""
    highlights: List[str]
    weaknesses: List[str]
    plan: List[str]


class StudentInfoResponse(BaseModel):
    """Student info response."""
    name: str
    level: str


class OverallScoreResponse(BaseModel):
    """Overall score response."""
    total_score: float
    star_level: int


class ParentReportResponse(BaseModel):
    """Complete parent H5 report response."""
    student: StudentInfoResponse
    overall: OverallScoreResponse
    radar: List[RadarDimensionResponse]
    part1: Part1DetailResponse
    part2: Part2DetailResponse
    suggestion: SuggestionResponse


@router.get(
    "/reports/{token}/h5",
    response_model=ParentReportResponse,
    summary="家长端 H5 报告",
    description="获取家长端 H5 所需的完整报告数据，包含融合后的五维图谱。"
)
async def get_parent_h5_report(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete report data for parent H5.
    
    Features:
    - No authentication required (uses share token)
    - Fused 5-dimension radar chart (Part 1 + Part 2)
    - Word-level Part 1 detail
    - Best/Weak samples for Part 2
    - Learning suggestions
    
    All scores are 0-100 scale.
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
    
    # Check expiry (if set)
    if share.expires_at and share.expires_at < china_now():
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
    
    # Get student profile
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    student_profile = result.scalar_one_or_none()
    student_name = student_profile.student_name if student_profile else "学生"
    
    # Get override data
    override = test.report_override or {}
    
    # Apply overrides to base data
    final_student_name = override.get("student_name") or student_name
    final_level = override.get("level") or test.level
    final_total_score = override.get("total_score") if override.get("total_score") is not None else (float(test.total_score) if test.total_score else 0)
    final_star_level = override.get("star_level") if override.get("star_level") is not None else (test.star_level or 1)
    final_part1_score = override.get("part1_score") if override.get("part1_score") is not None else (float(test.part1_score) if test.part1_score else 0)
    final_part2_score = override.get("part2_score") if override.get("part2_score") is not None else (float(test.part2_score) if test.part2_score else 0)
    
    # Get questions for Part 2 items (to fill in question text)
    from src.adapters.repositories.models import QuestionModel
    questions_stmt = select(QuestionModel).where(
        QuestionModel.level == test.level,
        QuestionModel.unit == test.unit,
        QuestionModel.part == 2
    )
    questions_result = await db.execute(questions_stmt)
    questions = {q.question_no: q.question for q in questions_result.scalars().all()}
    
    # Build test items with question text (use override if available)
    test_items = []
    override_part2_items = override.get("part2_items")
    if override_part2_items:
        # Use override items
        for item in override_part2_items:
            test_items.append({
                "question_no": item.get("question_no"),
                "question": questions.get(item.get("question_no"), f"Question {item.get('question_no')}"),
                "score": item.get("score"),
                "feedback": item.get("feedback"),
                "evidence": item.get("evidence")
            })
    else:
        # Use original items
        for item in test.items:
            test_items.append({
                "question_no": item.question_no,
                "question": questions.get(item.question_no, f"Question {item.question_no}"),
                "score": item.score,
                "feedback": item.feedback,
                "evidence": item.evidence
            })
    
    # Build interpretation dict (use override suggestion if available)
    override_suggestion = override.get("suggestion")
    if override_suggestion:
        interpretation = {
            "highlights": override_suggestion.get("highlights", []),
            "weaknesses": override_suggestion.get("weaknesses", []),
            "suggestions": override_suggestion.get("suggestions", [])
        }
    elif test.interpretation_generated_at:
        interpretation = {
            "highlights": json.loads(test.interpretation_highlights) if test.interpretation_highlights else [],
            "weaknesses": json.loads(test.interpretation_weaknesses) if test.interpretation_weaknesses else [],
            "suggestions": json.loads(test.interpretation_suggestions) if test.interpretation_suggestions else []
        }
    else:
        interpretation = None
    
    # Apply radar override if available
    override_radar = override.get("radar")
    part1_raw = test.part1_raw_result or {}
    part2_raw = test.part2_raw_result or {}
    
    if override_radar:
        # Override radar scores in part1/part2 raw for fusion
        if override_radar.get("fluency") is not None:
            part1_raw["fluency_score"] = override_radar["fluency"]
            part2_raw["fluency_score"] = override_radar["fluency"]
        if override_radar.get("pronunciation") is not None:
            part1_raw["pronunciation_score"] = override_radar["pronunciation"]
            part2_raw["pronunciation_score"] = override_radar["pronunciation"]
        if override_radar.get("confidence") is not None:
            part2_raw["confidence_score"] = override_radar["confidence"]
        if override_radar.get("vocabulary") is not None:
            part1_raw["accuracy_score"] = override_radar["vocabulary"]
            part2_raw["vocabulary_score"] = override_radar["vocabulary"]
        if override_radar.get("sentence") is not None:
            part1_raw["integrity_score"] = override_radar["sentence"]
            part2_raw["sentence_score"] = override_radar["sentence"]
    
    # Apply Part1 words override if available
    override_part1_words = override.get("part1_words")
    if override_part1_words:
        # Store in part1_raw for the service to use
        part1_raw["override_words"] = override_part1_words
    
    # Generate report using service
    service = ParentReportService()
    report = service.generate_report(
        student_name=final_student_name,
        level=final_level,
        total_score=final_total_score,
        star_level=final_star_level,
        part1_score=final_part1_score,
        part2_score=final_part2_score,
        part1_raw=part1_raw,
        part2_raw=part2_raw,
        part2_transcript=test.part2_transcript or "",
        test_items=test_items,
        interpretation=interpretation
    )
    
    await db.commit()
    
    # Convert to response
    return ParentReportResponse(
        student=StudentInfoResponse(name=report.student.name, level=report.student.level),
        overall=OverallScoreResponse(
            total_score=report.overall.total_score,
            star_level=report.overall.star_level
        ),
        radar=[
            RadarDimensionResponse(
                subject=dim.subject,
                score=dim.score,
                fullMark=dim.fullMark,
                icon=dim.icon,
                comment=dim.comment,
                tags=dim.tags
            )
            for dim in report.radar
        ],
        part1=Part1DetailResponse(
            score=report.part1.score,
            words=[
                WordStatusResponse(text=w.text, status=w.status)
                for w in report.part1.words
            ]
        ),
        part2=Part2DetailResponse(
            score=report.part2.score,
            best_sample=DialogueSampleResponse(
                question_no=report.part2.best_sample.question_no,
                question=report.part2.best_sample.question,
                answer=report.part2.best_sample.answer,
                score=report.part2.best_sample.score,
                feedback=report.part2.best_sample.feedback
            ) if report.part2.best_sample else None,
            weak_sample=DialogueSampleResponse(
                question_no=report.part2.weak_sample.question_no,
                question=report.part2.weak_sample.question,
                answer=report.part2.weak_sample.answer,
                score=report.part2.weak_sample.score,
                feedback=report.part2.weak_sample.feedback
            ) if report.part2.weak_sample else None
        ),
        suggestion=SuggestionResponse(
            highlights=report.suggestion.highlights,
            weaknesses=report.suggestion.weaknesses,
            plan=report.suggestion.plan
        )
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
    summary="获取报告解读",
    description="获取已生成的报告解读。如果尚未生成，返回 404。"
)
async def get_test_interpretation(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stored interpretation for a test.
    Returns 404 if not yet generated.
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
    
    # Check if interpretation exists
    if not test.interpretation_generated_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解读尚未生成，请先调用 POST 接口生成解读"
        )
    
    # Return stored interpretation
    return InterpretationResponse(
        highlights=json.loads(test.interpretation_highlights) if test.interpretation_highlights else [],
        weaknesses=json.loads(test.interpretation_weaknesses) if test.interpretation_weaknesses else [],
        evidence=json.loads(test.interpretation_evidence) if test.interpretation_evidence else [],
        suggestions=json.loads(test.interpretation_suggestions) if test.interpretation_suggestions else [],
        parent_script=test.interpretation_parent_script or ""
    )


@router.post(
    "/tests/{test_id}/interpretation",
    response_model=InterpretationResponse,
    summary="生成报告解读",
    description="生成 AI 报告解读并存储到数据库，包含亮点、短板、证据和家长沟通话术。"
)
async def generate_test_interpretation(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and store AI interpretation for a test.
    
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
    
    # Check test status
    if test.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已完成的测评才能生成解读"
        )
    
    # Check if already generated (return existing)
    if test.interpretation_generated_at:
        return InterpretationResponse(
            highlights=json.loads(test.interpretation_highlights) if test.interpretation_highlights else [],
            weaknesses=json.loads(test.interpretation_weaknesses) if test.interpretation_weaknesses else [],
            evidence=json.loads(test.interpretation_evidence) if test.interpretation_evidence else [],
            suggestions=json.loads(test.interpretation_suggestions) if test.interpretation_suggestions else [],
            parent_script=test.interpretation_parent_script or ""
            )
    
    # Get student name
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    student_profile = result.scalar_one_or_none()
    student_name = student_profile.student_name if student_profile else "学生"
    
    # Generate interpretation
    from src.adapters.gateways.qwen_client import QwenOmniGateway
    qwen_gateway = QwenOmniGateway()
    service = ReportInterpretationService(qwen_gateway)
    
    interpretation = await service.generate(
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
    
    # Store interpretation to database
    test.interpretation_highlights = json.dumps(interpretation.highlights, ensure_ascii=False)
    test.interpretation_weaknesses = json.dumps(interpretation.weaknesses, ensure_ascii=False)
    test.interpretation_evidence = json.dumps(interpretation.evidence, ensure_ascii=False)
    test.interpretation_suggestions = json.dumps(interpretation.suggestions, ensure_ascii=False)
    test.interpretation_parent_script = interpretation.parent_script
    test.interpretation_generated_at = china_now()
    
    await db.commit()
    
    return InterpretationResponse(
        highlights=interpretation.highlights,
        weaknesses=interpretation.weaknesses,
        evidence=interpretation.evidence,
        suggestions=interpretation.suggestions,
        parent_script=interpretation.parent_script
    )
