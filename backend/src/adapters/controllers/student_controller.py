"""
Student Entry Controller
Handles student entry token verification and session creation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.responses import ErrorResponse
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
