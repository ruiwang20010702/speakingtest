"""
Student Entry Token Use Case
Validates entry token and creates a session for the student.

安全策略（2026-01-31 更新）：
- 改为基于「音频提交状态」判断，而非「token 是否使用」
- 核心目的：保证学生能够完成测试（网络断开、误关闭页面等情况可重新进入）
- Token 未过期 + Part1/Part2 音频未全部提交 → 允许进入
- Token 未过期 + Part1/Part2 音频已全部提交 → 拒绝进入（正在评测中）
- Token 未过期 + 测试已完成 → 拒绝进入
- Token 已过期 → 拒绝进入

判断标准：test.part1_audio_url AND test.part2_audio_url 都存在时，拒绝进入

旧策略（已注释）：
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
    
    验证流程（2026-01-31 更新）：
    1. 查找 token
    2. 检查 token 是否过期
    3. [已移除] 不再检查 token 是否已使用
    4. 检查测试是否已完成（已完成则拒绝进入）
    5. 检查是否已提交所有音频（Part1 + Part2 都提交则拒绝进入）
    6. 获取学生信息
    7. [已移除] 不再在进入时标记 token
    8. 创建或获取测试记录
    9. 生成 JWT session token
    
    设计目的：保证学生能够完成测试
    - 学生可以在音频未全部提交前多次进入（网络断开、误关闭等情况）
    - Part1 + Part2 音频都提交后无法再进入（正在评测中）
    - 测试完成后无法再进入
    - Token 过期后无法进入
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

        # 3. [已注释] 不再检查 token 是否已使用，改为依赖测试完成状态判断
        # 目的：保证学生能够完成测试（网络断开、误关闭页面等情况可重新进入）
        # 
        # === 旧逻辑（严格模式）===
        # allow_reentry = getattr(self.settings, 'ENABLE_TOKEN_REENTRY', False)
        # 
        # if entry_token.is_used and not allow_reentry:
        #     logger.warning(f"Token reuse attempt blocked: token={token[:8]}..., student={entry_token.student_id}")
        #     return TokenVerificationError(
        #         error="TokenUsed",
        #         message="入口链接已使用，请联系老师获取新链接"
        #     )
        # === 旧逻辑结束 ===

        # 4. Check if test audio has been submitted (Part1 + Part2 音频都已上传)
        stmt = select(TestModel).where(
            TestModel.student_id == entry_token.student_id,
            TestModel.level == entry_token.level,
            TestModel.unit == entry_token.unit
        ).order_by(TestModel.created_at.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()

        # 检查是否已完成测评（状态为 completed）
        if test and test.status == 'completed':
             return TokenVerificationError(
                error="TestCompleted",
                message="您已完成该测评，无法再次进入"
            )
        
        # 检查是否已提交所有音频（Part1 + Part2 音频 URL 都已保存）
        # 即使评测还在进行中，只要音频都提交了就不允许再进入
        if test and test.part1_audio_url and test.part2_audio_url:
            logger.info(f"Audio already submitted, blocking re-entry: student={entry_token.student_id}, test_id={test.id}")
            return TokenVerificationError(
                error="AudioSubmitted",
                message="您已提交测评录音，正在评测中，请耐心等待结果"
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

        # 6. [已注释] 不再在进入时标记 token 为已使用
        # 改为依赖测试完成状态判断，允许学生在测试未完成前重复进入
        #
        # === 旧逻辑（进入即标记）===
        # if not entry_token.is_used:
        #     entry_token.is_used = True
        #     entry_token.used_at = now
        #     logger.info(f"Token marked as used: student={entry_token.student_id}, level={entry_token.level}")
        # === 旧逻辑结束 ===
        
        # 新逻辑：记录进入日志，但不标记 token
        logger.info(f"Student entered: student={entry_token.student_id}, level={entry_token.level}, unit={entry_token.unit}")

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
