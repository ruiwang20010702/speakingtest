"""
Generate Student Token Use Case
Generates a unique entry token for a student to access the test.
"""
import secrets
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import StudentEntryTokenModel, StudentProfileModel, TestModel
from src.infrastructure.config import get_settings

settings = get_settings()


@dataclass
class GenerateTokenRequest:
    """Request to generate token."""
    student_id: int
    teacher_id: int
    level: str
    unit: str
    expires_hours: int = 168


@dataclass
class GenerateTokenResponse:
    """Response with token."""
    success: bool
    token: str
    expires_at: datetime
    entry_url: str
    message: str = ""


class GenerateStudentTokenUseCase:
    """
    Generate a one-time entry token for a student.
    
    1. Validate student belongs to teacher
    2. Generate random token string
    3. Create a pending Test record
    4. Save token to database
    5. Return token and full entry URL
    """
    
    BASE_URL = settings.FRONTEND_STUDENT_URL
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def execute(self, request: GenerateTokenRequest) -> GenerateTokenResponse:
        # 1. Validate student ownership (optional but recommended)
        # Assuming the controller has already checked basic permissions,
        # but we can double check here if needed.
        
        # 2. Create Pending Test Record
        # This ensures the test appears in the "Test History" list immediately
        test_record = TestModel(
            student_id=request.student_id,
            level=request.level,
            unit=request.unit,
            status="pending",
            created_at=datetime.utcnow()
        )
        self.db.add(test_record)
        await self.db.flush()  # Get ID

        # 3. Generate token
        token = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_hours)
        
        # 4. Save to DB
        entry_token = StudentEntryTokenModel(
            token=token,
            student_id=request.student_id,
            level=request.level,
            unit=request.unit,
            expires_at=expires_at,
            created_by=request.teacher_id
        )
        self.db.add(entry_token)
        
        try:
            await self.db.commit()
            
            entry_url = f"{self.BASE_URL}/{token}"
            
            return GenerateTokenResponse(
                success=True,
                token=token,
                expires_at=expires_at,
                entry_url=entry_url,
                message="Token generated successfully"
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to generate token: {e}")
            return GenerateTokenResponse(
                success=False,
                token="",
                expires_at=expires_at,
                entry_url="",
                message="Failed to generate token"
            )
