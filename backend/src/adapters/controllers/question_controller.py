"""
Question Controller
Handles question bank CRUD operations for different levels and units.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id, get_current_user_role
from src.adapters.repositories.models import QuestionModel


router = APIRouter()


# ============================================
# Request/Response Schemas
# ============================================

class QuestionCreate(BaseModel):
    """Create a new question."""
    level: str
    unit: str
    question_no: int
    question: str
    reference_answer: Optional[str] = None


class QuestionUpdate(BaseModel):
    """Update an existing question."""
    question: Optional[str] = None
    reference_answer: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    """Question response."""
    id: int
    level: str
    unit: str
    question_no: int
    question: str
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
            question=q.question,
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
    ).order_by(QuestionModel.question_no)
    
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
            question=q.question,
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
