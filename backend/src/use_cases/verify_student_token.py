"""
Student Entry Token Use Case
Validates entry token and creates a session for the student.

Security:
- Tokens are single-use by default (STRICT_TOKEN_MODE)
- Once used, token cannot be reused even if test is incomplete
- This prevents link sharing/leakage abuse
- Set ENABLE_TOKEN_REENTRY=true for development/testing only
"""
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.timezone import now as china_now
from src.infrastructure.config import get_settings
from src.adapters.repositories.models import StudentEntryTokenModel, UserModel, StudentProfileModel, TestModel
from src.infrastructure.auth import create_access_token

logger = logging.getLogger(__name__)


@dataclass
class StudentSessionResponse:
    """Response for successful token verification."""
    access_token: str
    student_id: int
    student_name: str
    level: str
    unit: str
    test_id: Optional[int] = None


@dataclass
class TokenVerificationError:
    """Error response for token verification."""
    error: str
    message: str


class VerifyStudentEntryTokenUseCase:
    """
    Use case for verifying student entry token and creating a session.
    
    Security Flow:
    1. Find token in database
    2. Check if token is expired
    3. Check if token is already used (strict mode blocks reuse)
    4. Check if test is already completed
    5. Mark token as used (prevents future reuse)
    6. Create or find existing test record
    7. Generate JWT session token
    
    Note: In strict mode (default), a used token cannot be reused even
    if the test is incomplete. This prevents link sharing abuse.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def execute(self, token: str) -> StudentSessionResponse | TokenVerificationError:
        """
        Verify entry token and return session.
        
        Args:
            token: The entry token from URL
            
        Returns:
            StudentSessionResponse on success, TokenVerificationError on failure
        """
        # 1. Find token
        stmt = select(StudentEntryTokenModel).where(StudentEntryTokenModel.token == token)
        result = await self.db.execute(stmt)
        entry_token = result.scalar_one_or_none()

        if not entry_token:
            return TokenVerificationError(
                error="TokenNotFound",
                message="入口链接无效，请联系老师获取新链接"
            )

        # 2. Check if expired
        now = china_now()
        
        if entry_token.expires_at < now:
            return TokenVerificationError(
                error="TokenExpired",
                message="入口链接已过期，请联系老师获取新链接"
            )

        # 3. Check if token is already used (strict mode - default for production)
        # In strict mode, once a token is used, it cannot be reused
        # This prevents link sharing/leakage abuse
        allow_reentry = getattr(self.settings, 'ENABLE_TOKEN_REENTRY', False)
        
        if entry_token.is_used and not allow_reentry:
            logger.warning(f"Token reuse attempt blocked: token={token[:8]}..., student={entry_token.student_id}")
            return TokenVerificationError(
                error="TokenUsed",
                message="入口链接已使用，请联系老师获取新链接"
            )

        # 4. Check if test is already completed
        stmt = select(TestModel).where(
            TestModel.student_id == entry_token.student_id,
            TestModel.level == entry_token.level,
            TestModel.unit == entry_token.unit
        ).order_by(TestModel.created_at.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()

        if test and test.status == 'completed':
            return TokenVerificationError(
                error="TestCompleted",
                message="您已完成该测评，无法再次进入"
            )

        # 5. Get student info
        stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == entry_token.student_id)
        result = await self.db.execute(stmt)
        student_profile = result.scalar_one_or_none()

        if not student_profile:
            return TokenVerificationError(
                error="StudentNotFound",
                message="学生信息不存在，请联系老师"
            )

        # 6. Mark token as used (this is the security gate - prevents future reuse)
        if not entry_token.is_used:
            entry_token.is_used = True
            entry_token.used_at = now
            logger.info(f"Token marked as used: student={entry_token.student_id}, level={entry_token.level}")

        # 7. Create test if not exists
        if not test:
            test = TestModel(
                student_id=entry_token.student_id,
                level=entry_token.level,
                unit=entry_token.unit,
                status="pending"
            )
            self.db.add(test)
            await self.db.flush()

        # 8. Generate JWT (includes test_id for ownership verification)
        access_token = create_access_token(
            data={
                "sub": str(entry_token.student_id),
                "role": "student",
                "test_id": test.id
            }
        )

        await self.db.commit()

        return StudentSessionResponse(
            access_token=access_token,
            student_id=entry_token.student_id,
            student_name=student_profile.student_name,
            level=entry_token.level,
            unit=entry_token.unit,
            test_id=test.id
        )
