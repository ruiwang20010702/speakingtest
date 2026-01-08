"""
Student Entry Token Use Case
Validates entry token and creates a session for the student.
"""
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.repositories.models import StudentEntryTokenModel, UserModel, StudentProfileModel, TestModel
from src.infrastructure.auth import create_access_token


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
    
    Flow:
    1. Find token in database
    2. Check if token is valid (not expired, not used)
    3. Mark token as used
    4. Create or find existing test record
    5. Generate JWT session token
    """

    def __init__(self, db: AsyncSession):
        self.db = db

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
        # Ensure current time is timezone-aware (UTC) to match database
        now = datetime.now(timezone.utc)
        
        if entry_token.expires_at < now:
            return TokenVerificationError(
                error="TokenExpired",
                message="入口链接已过期，请联系老师获取新链接"
            )

        # 3. Check if test is already completed
        # We allow re-entry if the test is not completed, even if token was used before.
        
        # Find latest test first to check status
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

        # 4. Get student info
        stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == entry_token.student_id)
        result = await self.db.execute(stmt)
        student_profile = result.scalar_one_or_none()

        if not student_profile:
            return TokenVerificationError(
                error="StudentNotFound",
                message="学生信息不存在，请联系老师"
            )

        # 5. Mark token as used (track usage, but don't block re-entry)
        if not entry_token.is_used:
            entry_token.is_used = True
            entry_token.used_at = datetime.utcnow()

        # 6. Create test if not exists (should exist from generation, but safe fallback)
        if not test:
            # Create new test
            test = TestModel(
                student_id=entry_token.student_id,
                level=entry_token.level,
                unit=entry_token.unit,
                status="pending"
            )
            self.db.add(test)
            await self.db.flush()  # Get the ID

        # 7. Generate JWT
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
