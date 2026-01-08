"""
Question Controller
Handles question bank CRUD operations for different levels and units.
"""
from typing import List, Optional
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id, get_current_user_role
from src.adapters.repositories.models import QuestionModel
from src.adapters.gateways.oss_client import get_oss_client


router = APIRouter()


# ============================================
# Request/Response Schemas
# ============================================

class QuestionCreate(BaseModel):
    """Create a new question."""
    level: str
    unit: str
    part: int = 2  # 1=Word Reading, 2=Q&A
    question_no: int
    question: str
    translation: Optional[str] = None  # Chinese translation (Part 1)
    image_url: Optional[str] = None  # Image URL (Part 1)
    reference_answer: Optional[str] = None


class QuestionUpdate(BaseModel):
    """Update an existing question."""
    question: Optional[str] = None
    translation: Optional[str] = None
    image_url: Optional[str] = None
    reference_answer: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    """Question response."""
    id: int
    level: str
    unit: str
    part: int
    question_no: int
    question: str
    translation: Optional[str] = None
    image_url: Optional[str] = None
    reference_answer: Optional[str] = None
    is_active: bool


class QuestionBatchCreate(BaseModel):
    """Batch create questions for a level/unit."""
    level: str
    unit: str
    questions: List[dict]  # [{"question_no": 1, "question": "...", "reference_answer": "..."}]


# ============================================
# CRUD Endpoints
# ============================================

@router.get(
    "",
    response_model=List[QuestionResponse],
    summary="获取题目列表",
    description="按 Level 和 Unit 获取题目列表。"
)
async def list_questions(
    level: Optional[str] = None,
    unit: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List questions, optionally filtered by level and unit.
    """
    stmt = select(QuestionModel).where(QuestionModel.is_active == True)
    
    if level:
        stmt = stmt.where(QuestionModel.level == level)
    if unit:
        stmt = stmt.where(QuestionModel.unit == unit)
    
    stmt = stmt.order_by(QuestionModel.level, QuestionModel.unit, QuestionModel.question_no)
    
    result = await db.execute(stmt)
    questions = result.scalars().all()
    
    return [
        QuestionResponse(
            id=q.id,
            level=q.level,
            unit=q.unit,
            question_no=q.question_no,
            part=q.part,
            question=q.question,
            translation=q.translation,
            image_url=q.image_url,
            reference_answer=q.reference_answer,
            is_active=q.is_active
        )
        for q in questions
    ]


@router.get(
    "/{level}/{unit}",
    response_model=List[QuestionResponse],
    summary="获取指定 Level/Unit 的题目",
    description="获取指定 Level 和 Unit 的所有题目（12 道）。"
)
async def get_questions_by_level_unit(
    level: str,
    unit: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all questions for a specific level and unit.
    This is the main endpoint used by Part 2 evaluation.
    """
    stmt = select(QuestionModel).where(
        and_(
            QuestionModel.level == level,
            QuestionModel.unit == unit,
            QuestionModel.is_active == True
        )
    ).order_by(QuestionModel.part, QuestionModel.question_no)
    
    result = await db.execute(stmt)
    questions = result.scalars().all()
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No questions found for {level} - {unit}"
        )
    
    return [
        QuestionResponse(
            id=q.id,
            level=q.level,
            unit=q.unit,
            question_no=q.question_no,
            part=q.part,
            question=q.question,
            translation=q.translation,
            image_url=q.image_url,
            reference_answer=q.reference_answer,
            is_active=q.is_active
        )
        for q in questions
    ]


@router.post(
    "",
    response_model=QuestionResponse,
    summary="创建题目",
    description="创建单个题目。"
)
async def create_question(
    request: QuestionCreate,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a single question.
    Requires admin role.
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create questions"
        )
    
    question = QuestionModel(
        level=request.level,
        unit=request.unit,
        question_no=request.question_no,
        question=request.question,
        reference_answer=request.reference_answer
    )
    db.add(question)
    
    try:
        await db.commit()
        await db.refresh(question)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question already exists or invalid data: {str(e)}"
        )
    
    return QuestionResponse(
        id=question.id,
        level=question.level,
        unit=question.unit,
        question_no=question.question_no,
        part=question.part,
        question=question.question,
        reference_answer=question.reference_answer,
        is_active=question.is_active
    )


@router.post(
    "/batch",
    response_model=dict,
    summary="批量创建题目",
    description="为指定 Level/Unit 批量创建 12 道题目。"
)
async def batch_create_questions(
    request: QuestionBatchCreate,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch create questions for a level/unit.
    Requires admin role.
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create questions"
        )
    
    created_count = 0
    for q_data in request.questions:
        question = QuestionModel(
            level=request.level,
            unit=request.unit,
            question_no=q_data.get("question_no"),
            question=q_data.get("question"),
            reference_answer=q_data.get("reference_answer")
        )
        db.add(question)
        created_count += 1
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create questions: {str(e)}"
        )
    
    return {"success": True, "created": created_count, "message": f"Created {created_count} questions for {request.level} - {request.unit}"}


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="更新题目",
    description="更新指定题目的内容或状态。"
)
async def update_question(
    question_id: int,
    request: QuestionUpdate,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a question.
    Requires admin role.
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can update questions"
        )
    
    stmt = select(QuestionModel).where(QuestionModel.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    if request.question is not None:
        question.question = request.question
    if request.reference_answer is not None:
        question.reference_answer = request.reference_answer
    if request.is_active is not None:
        question.is_active = request.is_active
    
    await db.commit()
    
    return QuestionResponse(
        id=question.id,
        level=question.level,
        unit=question.unit,
        question_no=question.question_no,
        part=question.part,
        question=question.question,
        reference_answer=question.reference_answer,
        is_active=question.is_active
    )


@router.delete(
    "/{question_id}",
    summary="删除题目",
    description="软删除指定题目（设置 is_active=False）。"
)
async def delete_question(
    question_id: int,
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a question.
    Requires admin role.
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete questions"
        )
    
    stmt = select(QuestionModel).where(QuestionModel.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    question.is_active = False
    await db.commit()
    
    return {"success": True, "message": "Question deleted"}


# ============================================
# Image Upload Endpoint
# ============================================

@router.post(
    "/{question_id}/image",
    summary="上传题目图片",
    description="上传题目图片到 OSS 并更新 image_url。仅 Admin 可操作。"
)
async def upload_question_image(
    question_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image for a question.
    - Uploads to OSS: questions/{level}/{filename}
    - Updates question.image_url in database
    - Returns the new URL
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can upload images"
        )
    
    # Fetch question
    stmt = select(QuestionModel).where(QuestionModel.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {allowed_types}"
        )
    
    # Read file content
    content = await file.read()
    
    # Generate OSS key
    now = datetime.utcnow()
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    unique_id = str(uuid.uuid4())[:8]
    oss_key = f"questions/{question.level}/{question_id}_{unique_id}.{ext}"
    
    # Upload to OSS
    oss_client = get_oss_client()
    try:
        upload_result = oss_client.bucket.put_object(oss_key, content)
        
        if upload_result.status != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to OSS"
            )
        
        # Generate URL
        image_url = f"https://{oss_client.bucket_name}.{oss_client.endpoint.replace('https://', '')}/{oss_key}"
        
        # Update database
        question.image_url = image_url
        await db.commit()
        
        return {
            "success": True,
            "image_url": image_url,
            "message": "Image uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
