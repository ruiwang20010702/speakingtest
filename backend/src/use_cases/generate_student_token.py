"""
Generate Student Token Use Case
Generates a unique entry token for a student to access the test.

Security:
- Rate limiting: Max 5 tokens per student per hour
- Rate limiting: Max 20 tokens per teacher per hour
- Prevents abuse and token flooding
"""
import secrets
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.infrastructure.timezone import now as china_now
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
    
    Security:
    - Rate limit per student: 5 tokens per hour
    - Rate limit per teacher: 20 tokens per hour
    
    Flow:
    1. Check rate limits
    2. Validate student belongs to teacher
    3. Generate random token string
    4. Create a pending Test record
    5. Save token to database
    6. Return token and full entry URL
    """
    
    BASE_URL = settings.FRONTEND_STUDENT_URL
    
    # Rate limit settings
    STUDENT_RATE_LIMIT = 5      # Max tokens per student per hour
    TEACHER_RATE_LIMIT = 20     # Max tokens per teacher per hour
    RATE_LIMIT_WINDOW = 3600    # 1 hour in seconds
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def _check_rate_limits(self, student_id: int, teacher_id: int) -> tuple[bool, str]:
        """
        Check rate limits for token generation.
        
        Returns:
            (is_allowed, error_message)
        """
        window_start = china_now() - timedelta(seconds=self.RATE_LIMIT_WINDOW)
        
        # 1. Check student rate limit
        student_count_stmt = select(func.count(StudentEntryTokenModel.id)).where(
            and_(
                StudentEntryTokenModel.student_id == student_id,
                StudentEntryTokenModel.created_at > window_start
            )
        )
        student_count = (await self.db.execute(student_count_stmt)).scalar() or 0
        
        if student_count >= self.STUDENT_RATE_LIMIT:
            logger.warning(f"Token rate limit exceeded for student: student_id={student_id}, count={student_count}")
            return False, f"该学生1小时内已生成{student_count}个链接，请稍后再试"
        
        # 2. Check teacher rate limit
        teacher_count_stmt = select(func.count(StudentEntryTokenModel.id)).where(
            and_(
                StudentEntryTokenModel.created_by == teacher_id,
                StudentEntryTokenModel.created_at > window_start
            )
        )
        teacher_count = (await self.db.execute(teacher_count_stmt)).scalar() or 0
        
        if teacher_count >= self.TEACHER_RATE_LIMIT:
            logger.warning(f"Token rate limit exceeded for teacher: teacher_id={teacher_id}, count={teacher_count}")
            return False, f"您1小时内已生成{teacher_count}个链接，请稍后再试"
        
        return True, ""
    
    async def execute(self, request: GenerateTokenRequest) -> GenerateTokenResponse:
        # 1. Check rate limits (security)
        is_allowed, error_msg = await self._check_rate_limits(request.student_id, request.teacher_id)
        if not is_allowed:
            return GenerateTokenResponse(
                success=False,
                token="",
                expires_at=china_now(),
                entry_url="",
                message=error_msg
            )
        
        # 2. Create Pending Test Record
        # This ensures the test appears in the "Test History" list immediately
        test_record = TestModel(
            student_id=request.student_id,
            level=request.level,
            unit=request.unit,
            status="pending",
            created_at=china_now()
        )
        self.db.add(test_record)
        await self.db.flush()  # Get ID

        # 3. Generate token
        token = secrets.token_urlsafe(16)
        expires_at = china_now() + timedelta(hours=request.expires_hours)
        
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
