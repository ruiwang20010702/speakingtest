"""
Student Entry Controller
Handles student entry token verification and session creation.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.responses import ErrorResponse
from src.infrastructure.audit import log_audit
from src.use_cases.verify_student_token import (
    VerifyStudentEntryTokenUseCase,
    StudentSessionResponse,
    TokenVerificationError
)

router = APIRouter()


class EntryRequest(BaseModel):
    """Request body for token verification."""
    token: str


class EntryResponse(BaseModel):
    """Response for successful entry."""
    access_token: str
    token_type: str = "bearer"
    student_id: int
    student_name: str
    level: str
    unit: str
    test_id: int


@router.post(
    "/entry",
    response_model=EntryResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def verify_entry_token(
    request: EntryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify student entry token and get session.
    
    This is the first endpoint a student calls after clicking
    the entry link from their teacher.
    
    Returns a JWT token for subsequent API calls.
    """
    use_case = VerifyStudentEntryTokenUseCase(db)
    result = await use_case.execute(request.token)

    if isinstance(result, TokenVerificationError):
        status_code = status.HTTP_404_NOT_FOUND
        if result.error == "TokenExpired" or result.error == "TokenUsed":
            status_code = status.HTTP_400_BAD_REQUEST
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": result.error,
                "message": result.message
            }
        )

    return EntryResponse(
        access_token=result.access_token,
        student_id=result.student_id,
        student_name=result.student_name,
        level=result.level,
        unit=result.unit,
        test_id=result.test_id
    )


# ============================================
# Student Management (Teacher/Admin)
# ============================================

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.adapters.repositories.models import StudentProfileModel, UserModel
from src.infrastructure.auth import get_current_user_id, get_current_user_role, require_teacher


class StudentResponse(BaseModel):
    """Student profile response."""
    user_id: int
    external_user_id: Optional[str] = None
    student_name: str
    cur_age: Optional[int] = None
    cur_grade: Optional[str] = None
    cur_level_desc: Optional[str] = None
    main_last_buy_unit_name: Optional[str] = None
    teacher_id: int
    teacher_name: Optional[str] = None  # For admin view
    ss_crm_name: Optional[str] = None   # CRM account name

@router.get(
    "",
    response_model=List[StudentResponse],
    summary="获取学生列表",
    description="获取名下学生列表。Admin 可查看所有学生，老师只能查看自己名下的学生。"
)
async def list_students(
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Get student list with RBAC.
    
    - **Admin**: Returns all students, including teacher info.
    - **Teacher**: Returns only students belonging to the current teacher.
    """
    # Base query with teacher relationship loaded
    stmt = select(StudentProfileModel).options(
        selectinload(StudentProfileModel.user).selectinload(UserModel.student_profile)
    )
    
    # RBAC Filter
    if role != "admin":
        stmt = stmt.where(StudentProfileModel.teacher_id == user_id)
    
    # Execute query
    result = await db.execute(stmt)
    students = result.scalars().all()
    
    # Build response
    response = []
    
    # Pre-fetch teacher names if admin (optimization)
    teacher_map = {}
    if role == "admin":
        teacher_ids = {s.teacher_id for s in students}
        if teacher_ids:
            t_stmt = select(UserModel).where(UserModel.id.in_(teacher_ids))
            t_result = await db.execute(t_stmt)
            teachers = t_result.scalars().all()
            # Note: UserModel doesn't have a name field yet, using email or ID
            teacher_map = {t.id: t.email for t in teachers}

    for s in students:
        teacher_name = None
        if role == "admin":
            # Prefer ss_crm_name if available, otherwise fallback to teacher map
            if s.ss_crm_name:
                teacher_name = s.ss_crm_name
            else:
                teacher_name = teacher_map.get(s.teacher_id, f"Teacher {s.teacher_id}")
            
        response.append(StudentResponse(
            user_id=s.user_id,
            external_user_id=s.external_user_id,
            student_name=s.student_name,
            cur_age=s.cur_age,
            cur_grade=s.cur_grade,
            cur_level_desc=s.cur_level_desc,
            main_last_buy_unit_name=s.main_last_buy_unit_name,
            teacher_id=s.teacher_id,
            teacher_name=teacher_name,
            ss_crm_name=s.ss_crm_name
        ))
        
    return response


# ============================================
# Student Import
# ============================================

from src.use_cases.import_student import ImportStudentUseCase, ImportStudentRequest

class ImportRequest(BaseModel):
    """Import student request."""
    student_id: int


class ImportResponse(BaseModel):
    """Import student response."""
    success: bool
    student_name: Optional[str] = None
    message: str
    is_new: bool


@router.post(
    "/import",
    response_model=ImportResponse,
    summary="导入学生 (CRM)",
    description="通过学生 ID 从 CRM 导入学生信息。需提供学生 ID，系统会自动关联当前登录的老师。"
)
async def import_student(
    request: ImportRequest,
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Import student from CRM.
    
    1. Teacher provides student_id
    2. Backend fetches data from CRM using teacher's email + student_id
    3. Saves/Updates student profile
    """
    # Get current teacher's email (we need to query it)
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    teacher = result.scalar_one()
    
    if not teacher.email:
        raise HTTPException(status_code=400, detail="Teacher email not found")

    use_case = ImportStudentUseCase(db)
    result = await use_case.execute(
        ImportStudentRequest(
            teacher_id=user_id,
            teacher_email=teacher.email,
            student_id=request.student_id
        )
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ImportFailed", "message": result.message}
        )
        
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="IMPORT_STUDENT",
        target_type="student",
        target_id=result.student_id,  # Assuming result has student_id, let me check ImportStudentResponse
        details={"student_id": request.student_id, "is_new": result.is_new},
        request=http_request
    )
        
    return ImportResponse(
        success=True,
        student_name=result.student_name,
        message=result.message,
        is_new=result.is_new
    )


# ============================================
# Student Token Generation
# ============================================

from src.use_cases.generate_student_token import GenerateStudentTokenUseCase, GenerateTokenRequest

class GenerateTokenResponseSchema(BaseModel):
    """Generate token response."""
    success: bool
    token: str
    expires_at: datetime
    entry_url: str
    message: str


@router.post(
    "/{student_id}/token",
    response_model=GenerateTokenResponseSchema,
    summary="生成学生测评 Token",
    description="为指定学生生成一次性测评入口链接。学生扫码或访问链接即可直接进入测评。"
)
async def generate_student_token(
    student_id: int,
    http_request: Request,
    level: str = "L1",
    unit: str = "Unit 1",
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate entry token for student.
    
    - Requires teacher login
    - Validates student belongs to teacher
    """
    # Validate ownership
    stmt = select(StudentProfileModel).where(
        StudentProfileModel.user_id == student_id,
        StudentProfileModel.teacher_id == user_id
    )
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or not authorized"
        )
        
    use_case = GenerateStudentTokenUseCase(db)
    result = await use_case.execute(
        GenerateTokenRequest(
            student_id=student_id,
            teacher_id=user_id,
            level=level,
            unit=unit
        )
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message
        )
        
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="GENERATE_TOKEN",
        target_type="student_token",
        target_id=student_id,
        details={"level": level, "unit": unit, "token": result.token},
        request=http_request
    )
        
    return GenerateTokenResponseSchema(
        success=True,
        token=result.token,
        expires_at=result.expires_at,
        entry_url=result.entry_url,
        message=result.message
    )
