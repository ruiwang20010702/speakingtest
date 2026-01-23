"""
Student Entry Controller
Handles student entry token verification and session creation.
支持 httpOnly Cookie 认证（更安全）
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db, get_db_readonly
from src.infrastructure.responses import ErrorResponse
from src.infrastructure.audit import log_audit
from src.infrastructure.auth import set_auth_cookie
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
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify student entry token and get session.
    
    This is the first endpoint a student calls after clicking
    the entry link from their teacher.
    
    Returns a JWT token for subsequent API calls.
    同时设置 httpOnly Cookie（浏览器自动携带，更安全）
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

    # 设置 httpOnly Cookie（浏览器端更安全）
    set_auth_cookie(response, result.access_token)

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
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.adapters.repositories.models import StudentProfileModel, UserModel
from src.infrastructure.auth import get_current_user_id, get_current_user_role, require_teacher
from src.infrastructure.responses import PaginatedResponse


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
    ss_name: Optional[str] = None       # New
    ss_sm_name: Optional[str] = None    # New
    ss_dept4_name: Optional[str] = None # New
    ss_group: Optional[str] = None      # New
    is_upgrade: int = 0                 # New


class StudentListResponse(BaseModel):
    """Paginated student list response."""
    items: List[StudentResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.get(
    "",
    response_model=StudentListResponse,
    summary="获取学生列表",
    description="获取名下学生列表。Admin 可查看所有学生，老师只能查看自己名下的学生。支持分页。"
)
async def list_students(
    page: int = 1,
    page_size: int = 50,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db_readonly)  # 只读操作，无需 commit
):
    """
    Get student list with RBAC and pagination.
    
    - **Admin**: Returns all students, including teacher info.
    - **Teacher**: Returns only students belonging to the current teacher.
    
    Args:
        page: Page number (1-indexed), default 1
        page_size: Items per page, default 50, max 100
    """
    # Validate pagination params
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    
    # Base filter for RBAC
    base_filter = []
    if role != "admin":
        base_filter.append(StudentProfileModel.teacher_id == user_id)
    
    # 1. Get total count (1 query)
    count_stmt = select(func.count(StudentProfileModel.user_id))
    if base_filter:
        count_stmt = count_stmt.where(*base_filter)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # 2. Get paginated students (1 query)
    stmt = select(StudentProfileModel).options(
        selectinload(StudentProfileModel.user).selectinload(UserModel.student_profile)
    )
    if base_filter:
        stmt = stmt.where(*base_filter)
    stmt = stmt.order_by(StudentProfileModel.user_id).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    students = result.scalars().all()
    
    # Build response
    response_items = []
    
    # Pre-fetch teacher names if admin (optimization, 1 query)
    teacher_map = {}
    if role == "admin" and students:
        teacher_ids = {s.teacher_id for s in students if s.teacher_id}
        if teacher_ids:
            t_stmt = select(UserModel).where(UserModel.id.in_(teacher_ids))
            t_result = await db.execute(t_stmt)
            teachers = t_result.scalars().all()
            teacher_map = {t.id: t.email for t in teachers}

    for s in students:
        teacher_name = None
        if role == "admin":
            # Prefer ss_crm_name if available, otherwise fallback to teacher map
            if s.ss_crm_name:
                teacher_name = s.ss_crm_name
            else:
                teacher_name = teacher_map.get(s.teacher_id, f"Teacher {s.teacher_id}")
            
        response_items.append(StudentResponse(
            user_id=s.user_id,
            external_user_id=s.external_user_id,
            student_name=s.student_name,
            cur_age=s.cur_age,
            cur_grade=s.cur_grade,
            cur_level_desc=s.cur_level_desc,
            main_last_buy_unit_name=s.main_last_buy_unit_name,
            teacher_id=s.teacher_id,
            teacher_name=teacher_name,
            ss_crm_name=s.ss_crm_name,
            ss_name=s.ss_name,
            ss_sm_name=s.ss_sm_name,
            ss_dept4_name=s.ss_dept4_name,
            ss_group=s.ss_group,
            is_upgrade=s.is_upgrade
        ))
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return StudentListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


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
        target_id=request.student_id,  # Use request.student_id since response doesn't have it
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


# ============================================
# Batch Token Generation
# ============================================

class BatchTokenRequest(BaseModel):
    """Batch token generation request."""
    student_ids: List[int]
    level: str = "L1"
    unit: str = "Unit 1"


class BatchTokenItem(BaseModel):
    """Single token in batch response."""
    student_id: int
    student_name: Optional[str] = None
    success: bool
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    entry_url: Optional[str] = None
    message: str


class BatchTokenResponse(BaseModel):
    """Batch token generation response."""
    total: int
    success_count: int
    failed_count: int
    items: List[BatchTokenItem]


@router.post(
    "/batch-tokens",
    response_model=BatchTokenResponse,
    summary="批量生成学生测评 Token",
    description="为多个学生批量生成一次性测评入口链接。"
)
async def batch_generate_tokens(
    request: BatchTokenRequest,
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch generate entry tokens for multiple students.
    
    - Requires teacher login
    - Only generates tokens for students belonging to the teacher
    
    Optimized: Uses batch query to load all students at once (1 query instead of N).
    """
    items = []
    success_count = 0
    use_case = GenerateStudentTokenUseCase(db)
    
    # Batch query: load all requested students belonging to the teacher (1 query instead of N)
    student_map: dict = {}
    if request.student_ids:
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id.in_(request.student_ids),
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        for student in result.scalars().all():
            student_map[student.user_id] = student
    
    for student_id in request.student_ids:
        # Lookup from pre-loaded map (no additional query)
        student = student_map.get(student_id)
        
        if not student:
            items.append(BatchTokenItem(
                student_id=student_id,
                success=False,
                message="Student not found or not authorized"
            ))
            continue
        
        try:
            token_result = await use_case.execute(
                GenerateTokenRequest(
                    student_id=student_id,
                    teacher_id=user_id,
                    level=request.level,
                    unit=request.unit
                )
            )
            
            if token_result.success:
                items.append(BatchTokenItem(
                    student_id=student_id,
                    student_name=student.student_name,
                    success=True,
                    token=token_result.token,
                    expires_at=token_result.expires_at,
                    entry_url=token_result.entry_url,
                    message="Token generated"
                ))
                success_count += 1
            else:
                items.append(BatchTokenItem(
                    student_id=student_id,
                    student_name=student.student_name,
                    success=False,
                    message=token_result.message
                ))
        except Exception as e:
            items.append(BatchTokenItem(
                student_id=student_id,
                student_name=student.student_name if student else None,
                success=False,
                message=str(e)
            ))
    
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="BATCH_GENERATE_TOKEN",
        target_type="students",
        target_id=None,
        details={
            "student_ids": request.student_ids,
            "level": request.level,
            "unit": request.unit,
            "success_count": success_count
        },
        request=http_request
    )
    
    return BatchTokenResponse(
        total=len(request.student_ids),
        success_count=success_count,
        failed_count=len(request.student_ids) - success_count,
        items=items
    )


# ============================================
# Token Revocation
# ============================================

from src.adapters.repositories.models import StudentEntryTokenModel


class RevokeTokenResponse(BaseModel):
    """Token revocation response."""
    success: bool
    revoked_count: int
    message: str


@router.post(
    "/{student_id}/revoke-token",
    response_model=RevokeTokenResponse,
    summary="撤回学生入口 Token",
    description="撤回指定学生的所有未使用入口 Token，使其无法进入测评。"
)
async def revoke_student_token(
    student_id: int,
    http_request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke all unused entry tokens for a student.
    
    - Requires teacher login
    - Only affects tokens created by this teacher
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
    
    # Find and revoke all unused tokens
    from sqlalchemy import update
    stmt = (
        update(StudentEntryTokenModel)
        .where(
            StudentEntryTokenModel.student_id == student_id,
            StudentEntryTokenModel.is_used == False,
            StudentEntryTokenModel.created_by == user_id
        )
        .values(is_used=True, used_at=datetime.utcnow())
    )
    result = await db.execute(stmt)
    await db.commit()
    
    revoked_count = result.rowcount
    
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="REVOKE_TOKEN",
        target_type="student",
        target_id=student_id,
        details={"revoked_count": revoked_count},
        request=http_request
    )
    
    return RevokeTokenResponse(
        success=True,
        revoked_count=revoked_count,
        message=f"Revoked {revoked_count} token(s)"
    )


# ============================================
# CSV Import
# ============================================

from fastapi import UploadFile, File
from src.use_cases.csv_import import CSVImportUseCase, CSVImportResult
from src.adapters.repositories.models import UserModel


class CSVImportResponse(BaseModel):
    """CSV import response."""
    success: bool
    total_rows: int
    imported_count: int
    updated_count: int
    failed_count: int
    errors: List[str]


@router.post(
    "/import-csv",
    response_model=CSVImportResponse,
    summary="CSV 批量导入学生",
    description="通过 CSV 文件批量导入学生。CSV 必须包含 student_id 和 student_name 列。"
)
async def import_students_csv(
    http_request: Request,
    file: UploadFile = File(..., description="CSV 文件"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Import students from CSV file.
    
    Required columns: student_id, student_name
    Optional columns: cur_age, cur_grade, cur_level_desc
    """
    # Get teacher email
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher email not found"
        )
    
    # Read CSV content
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
    except UnicodeDecodeError:
        # Try GBK encoding for Chinese files
        csv_content = content.decode('gbk')
    
    use_case = CSVImportUseCase(db)
    result = await use_case.execute(
        csv_content=csv_content,
        teacher_id=user_id,
        teacher_email=user.email
    )
    
    # Audit Log
    await log_audit(
        db=db,
        operator_id=user_id,
        action="CSV_IMPORT",
        target_type="students",
        target_id=None,
        details={
            "total_rows": result.total_rows,
            "imported_count": result.imported_count,
            "updated_count": result.updated_count,
            "failed_count": result.failed_count
        },
        request=http_request
    )
    
    return CSVImportResponse(
        success=result.success,
        total_rows=result.total_rows,
        imported_count=result.imported_count,
        updated_count=result.updated_count,
        failed_count=result.failed_count,
        errors=result.errors
    )


