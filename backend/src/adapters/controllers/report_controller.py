"""
Report Controller
Handles report viewing and sharing for teachers and parents.
"""
import json
import secrets
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id, get_current_user_role
from src.infrastructure.timezone import now as china_now
from src.infrastructure.config import get_settings
from src.adapters.repositories.models import (
    TestModel, TestItemModel, StudentProfileModel, ReportShareTokenModel, TestRawDataModel
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
    interpretation_status: Optional[str] = None  # 报告解读状态: pending/generating/completed/failed
    failure_reason: Optional[str] = None  # 失败原因（当 status=failed 时）
    retry_count: int = 0  # 重试次数


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


class TestListResponse(BaseModel):
    """Paginated test list response."""
    items: List[TestSummary]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================
# Student Test History
# ============================================

@router.get(
    "/students/{student_id}/tests",
    response_model=TestListResponse,
    summary="获取学生测评历史",
    description="获取指定学生的所有测评记录列表，支持分页。"
)
async def get_student_tests(
    student_id: int,
    page: int = 1,
    page_size: int = 20,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Get test history for a specific student with pagination.
    
    - Teacher can only view their own students
    - Admin can view all students
    
    Args:
        student_id: Student user ID
        page: Page number (1-indexed), default 1
        page_size: Items per page, default 20, max 100
    """
    # Validate pagination params
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    
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
    
    # 1. Get total count (1 query)
    count_stmt = select(func.count(TestModel.id)).where(TestModel.student_id == student_id)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # 2. Get paginated tests (1 query)
    stmt = select(TestModel).where(
        TestModel.student_id == student_id
    ).order_by(TestModel.created_at.desc()).offset(offset).limit(page_size)
    
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

    # Use configured URL instead of hardcoded value
    BASE_URL = settings.FRONTEND_STUDENT_URL
    
    items = [
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
            is_interpreted=t.interpretation_generated_at is not None,
            interpretation_status=t.interpretation_status or "pending",
            failure_reason=t.failure_reason if t.status == 'failed' else None,
            retry_count=t.retry_count or 0
        )
        for t in tests
    ]
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return TestListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


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
    # Get test with items and raw_data (optimized: eager load large JSON from separate table)
    stmt = select(TestModel).options(
        selectinload(TestModel.items),
        selectinload(TestModel.raw_data)  # Load large JSON from separate table
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
    
    # Optimized: prefer raw_data table, fallback to main table
    raw_data = test.raw_data
    part1_raw_result = (raw_data.part1_raw_result if raw_data else None) or test.part1_raw_result
    
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
        part1_raw_result=part1_raw_result,
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
    # Get test with items and raw_data (optimized)
    stmt = select(TestModel).options(
        selectinload(TestModel.items),
        selectinload(TestModel.raw_data)  # Load large JSON from separate table
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
    
    # Optimized: prefer raw_data table, fallback to main table
    raw_data = test.raw_data
    part1_raw = (raw_data.part1_raw_result if raw_data else None) or test.part1_raw_result or {}
    part2_raw = (raw_data.part2_raw_result if raw_data else None) or test.part2_raw_result or {}
    
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
    if part2_raw and isinstance(part2_raw, dict):
        raw_items = part2_raw.get("items", [])
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
    
    # Extract suggestion from summary analysis (generated after test completion)
    original_suggestion = None
    if test.summary_generated_at:
        original_suggestion = {
            "highlights": json.loads(test.summary_highlights) if test.summary_highlights else [],
            "weaknesses": json.loads(test.summary_weaknesses) if test.summary_weaknesses else [],
            "suggestions": json.loads(test.summary_weekly_plan) if test.summary_weekly_plan else [],
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
    
    # Optimized: prefer raw_data.report_override, fallback to main table
    report_override = (raw_data.report_override if raw_data else None) or test.report_override
    
    return GetReportOverrideResponse(
        has_override=report_override is not None,
        override=report_override,
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
    
    # Get test with items and raw_data (optimized)
    stmt = select(TestModel).options(
        selectinload(TestModel.items),
        selectinload(TestModel.raw_data)  # Load large JSON from separate table
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
    
    # Optimized: prefer raw_data table, fallback to main table
    raw_data = test.raw_data
    part1_raw_result = (raw_data.part1_raw_result if raw_data else None) or test.part1_raw_result
    
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
        part1_raw_result=part1_raw_result,
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
    
    # Get test with items and raw_data (optimized: eager load large JSON)
    stmt = select(TestModel).options(
        selectinload(TestModel.items),
        selectinload(TestModel.raw_data)  # Load large JSON from separate table
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
    
    # Optimized: prefer raw_data table, fallback to main table
    raw_data_obj = test.raw_data
    
    # Get override data (prefer raw_data table)
    override = (raw_data_obj.report_override if raw_data_obj else None) or test.report_override or {}
    
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
    
    # Build suggestion dict for parent H5 (use override → summary_analysis → fallback)
    # 优先级: 手动覆盖 > 测评汇总分析 > 默认规则
    override_suggestion = override.get("suggestion")
    if override_suggestion:
        # 使用手动覆盖的内容
        interpretation = {
            "highlights": override_suggestion.get("highlights", []),
            "weaknesses": override_suggestion.get("weaknesses", []),
            "suggestions": override_suggestion.get("suggestions", [])
        }
    elif test.summary_generated_at:
        # 使用自动生成的测评汇总分析 (给家长看)
        interpretation = {
            "highlights": json.loads(test.summary_highlights) if test.summary_highlights else [],
            "weaknesses": json.loads(test.summary_weaknesses) if test.summary_weaknesses else [],
            "suggestions": json.loads(test.summary_weekly_plan) if test.summary_weekly_plan else []
        }
    else:
        # 没有生成过，使用 None 让 ParentReportService 生成默认建议
        interpretation = None
    
    # 获取 AI 生成的五维评语（用于雷达图 comment 和 tags）
    dimension_feedback = test.summary_dimension_feedback if hasattr(test, 'summary_dimension_feedback') else None
    
    # Apply radar override if available
    override_radar = override.get("radar")
    # Optimized: prefer raw_data table, fallback to main table
    part1_raw = (raw_data_obj.part1_raw_result if raw_data_obj else None) or test.part1_raw_result or {}
    part2_raw = (raw_data_obj.part2_raw_result if raw_data_obj else None) or test.part2_raw_result or {}
    
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
        interpretation=interpretation,
        dimension_feedback=dimension_feedback  # AI 生成的五维评语
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
    """Response for report interpretation (班主任演讲稿，按6页组织)."""
    pages: Dict[str, str]  # 每页一段演讲话术：cover/radar/vocab/dialogue/roadmap/badge
    full_script: str       # 完整演讲稿（约1500字，10分钟）


class InterpretationStatusResponse(BaseModel):
    """Response for interpretation generation status."""
    status: str  # pending/generating/completed/failed
    message: Optional[str] = None
    pages: Optional[Dict[str, str]] = None
    full_script: Optional[str] = None


@router.get(
    "/tests/{test_id}/interpretation",
    response_model=InterpretationResponse,
    summary="获取报告解读",
    description="获取已生成的报告解读（按6页组织）。如果尚未生成，返回 404。"
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
    
    # Check if interpretation exists (以 interpretation_pages 非空为准)
    if not test.interpretation_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解读尚未生成，请先调用 POST 接口生成解读"
        )
    
    # 解析 pages 数据（新格式：每页是字符串）
    pages_data = test.interpretation_pages if isinstance(test.interpretation_pages, dict) else {}
    
    # Return stored interpretation
    return InterpretationResponse(
        pages=pages_data,
        full_script=test.interpretation_parent_script or ""  # full_script 存储在 parent_script 字段
    )


@router.post(
    "/tests/{test_id}/interpretation",
    response_model=InterpretationStatusResponse,
    summary="生成报告解读（异步）",
    description="异步生成 AI 报告解读。立即返回状态，使用 GET 接口轮询结果。使用 force=true 可强制重新生成。"
)
async def generate_test_interpretation(
    test_id: int,
    force: bool = False,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    异步生成报告解读（班主任演讲稿）。
    
    返回状态:
    - generating: 正在生成中，请轮询 GET 接口
    - completed: 已完成，包含 pages 和 full_script
    - failed: 生成失败，可重试
    
    Query Parameters:
    - force: 是否强制重新生成（即使已存在解读）
    """
    import uuid
    from src.infrastructure.queue_service import InterpretationTask, enqueue_interpretation_task
    
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
    
    # Check current interpretation status
    if test.interpretation_status == "generating":
        return InterpretationStatusResponse(
            status="generating",
            message="报告解读正在生成中，请稍候..."
        )
    
    # If already completed and not forcing, return the result
    if test.interpretation_status == "completed" and test.interpretation_pages and not force:
        pages_data = test.interpretation_pages if isinstance(test.interpretation_pages, dict) else {}
        return InterpretationStatusResponse(
            status="completed",
            pages=pages_data,
            full_script=test.interpretation_parent_script or ""
        )
    
    # If failed, allow retry (will re-enqueue)
    if test.interpretation_status == "failed" and not force:
        # Check retry count
        if (test.interpretation_retry_count or 0) >= 3:
            return InterpretationStatusResponse(
                status="failed",
                message="生成失败次数过多，请联系管理员"
            )
    
    if force:
        logger.info(f"强制重新生成报告解读: test_id={test_id}")
        # Reset retry count on force
        test.interpretation_retry_count = 0
    
    # Get student name
    stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
    result = await db.execute(stmt)
    student_profile = result.scalar_one_or_none()
    student_name = student_profile.student_name if student_profile else "学生"
    
    # ========== 应用 report_override 数据（如果有修改）==========
    override = test.report_override or {}
    
    # 基础字段覆盖
    final_student_name = override.get("student_name") or student_name
    final_level = override.get("level") or test.level
    final_total_score = override.get("total_score") if override.get("total_score") is not None else (float(test.total_score) if test.total_score else 0)
    final_star_level = override.get("star_level") if override.get("star_level") is not None else (test.star_level or 1)
    final_part1_score = override.get("part1_score") if override.get("part1_score") is not None else (float(test.part1_score) if test.part1_score else 0)
    final_part2_score = override.get("part2_score") if override.get("part2_score") is not None else (float(test.part2_score) if test.part2_score else None)
    
    # Part 1 词汇详情覆盖
    part1_details = test.part1_raw_result or {}
    override_part1_words = override.get("part1_words")
    if override_part1_words:
        part1_details = {"words": override_part1_words}
    
    # Part 2 问答项覆盖
    override_part2_items = override.get("part2_items")
    if override_part2_items:
        final_part2_items = [
            {"question_no": item.get("question_no"), "score": item.get("score"), "evidence": item.get("evidence")}
            for item in override_part2_items
        ]
    elif test.items:
        final_part2_items = [
            {"question_no": item.question_no, "score": item.score, "evidence": item.evidence}
            for item in test.items
        ]
    else:
        final_part2_items = []
    
    # 雷达图数据覆盖
    override_radar = override.get("radar")
    radar_data = []
    if override_radar:
        radar_data = [
            {"name": "流利度", "value": override_radar.get("fluency", 0)},
            {"name": "发音", "value": override_radar.get("pronunciation", 0)},
            {"name": "自信度", "value": override_radar.get("confidence", 0)},
            {"name": "词汇", "value": override_radar.get("vocabulary", 0)},
            {"name": "整句输出", "value": override_radar.get("sentence", 0)},
        ]
    
    logger.info(f"入队报告解读任务: test_id={test_id}, student={final_student_name}")
    
    # Create and enqueue task
    task = InterpretationTask(
        task_id=str(uuid.uuid4()),
        test_id=test_id,
        student_name=final_student_name,
        level=final_level,
        total_score=final_total_score,
        part1_score=final_part1_score,
        part2_score=final_part2_score if final_part2_score is not None else 0,
        star_level=final_star_level,
        part1_details=part1_details,
        part2_items=final_part2_items,
        radar_data=radar_data,
    )
    
    # Update status to generating
    test.interpretation_status = "generating"
    await db.commit()
    
    # Enqueue the task
    try:
        await enqueue_interpretation_task(task)
    except Exception as e:
        logger.error(f"入队报告解读任务失败: {e}")
        # Revert status
        test.interpretation_status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务入队失败，请稍后重试"
        )
    
    return InterpretationStatusResponse(
        status="generating",
        message="报告解读已开始生成，请稍候轮询结果..."
    )


@router.get(
    "/tests/{test_id}/interpretation/status",
    response_model=InterpretationStatusResponse,
    summary="查询报告解读状态",
    description="查询报告解读的生成状态，用于前端轮询。"
)
async def get_interpretation_status(
    test_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    查询报告解读生成状态。
    
    返回状态:
    - generating: 正在生成中
    - completed: 已完成，包含 pages 和 full_script
    - failed: 生成失败
    - null/pending: 尚未开始
    """
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
    
    status_value = test.interpretation_status or "pending"
    
    if status_value == "completed" and test.interpretation_pages:
        pages_data = test.interpretation_pages if isinstance(test.interpretation_pages, dict) else {}
        return InterpretationStatusResponse(
            status="completed",
            pages=pages_data,
            full_script=test.interpretation_parent_script or ""
        )
    elif status_value == "failed":
        retry_count = test.interpretation_retry_count or 0
        if retry_count >= 3:
            return InterpretationStatusResponse(
                status="failed",
                message="生成失败次数过多，请联系管理员"
            )
        return InterpretationStatusResponse(
            status="failed",
            message="生成失败，请重试"
        )
    elif status_value == "generating":
        return InterpretationStatusResponse(
            status="generating",
            message="报告解读正在生成中..."
        )
    else:
        return InterpretationStatusResponse(
            status="pending",
            message="尚未开始生成"
        )
