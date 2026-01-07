"""
Teacher Login Use Cases
基于 /fastapi-auth-patterns 实现验证码登录
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Union
from dataclasses import dataclass

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import UserModel, VerificationCodeModel
from src.adapters.gateways.email_service import get_email_service
from src.infrastructure.auth import create_access_token


# ============================================
# 请求/响应数据类
# ============================================

@dataclass
class SendCodeRequest:
    """发送验证码请求"""
    email: str
    ip_address: Optional[str] = None


@dataclass
class SendCodeResponse:
    """发送验证码响应"""
    success: bool
    message: str


@dataclass
class LoginRequest:
    """登录请求"""
    email: str
    code: str


@dataclass
class LoginResponse:
    """登录响应"""
    success: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user_id: Optional[int] = None
    role: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


# ============================================
# 发送验证码用例
# ============================================

class SendVerificationCodeUseCase:
    """
    发送验证码用例
    
    流程:
    1. 验证邮箱格式（必须是 @51talk.com）
    2. 检查频率限制（1分钟内只能发一次）
    3. 生成6位验证码
    4. 保存到数据库（5分钟过期）
    5. 异步发送邮件
    """
    
    CODE_LENGTH = 6
    EXPIRE_MINUTES = 5
    RATE_LIMIT_SECONDS = 60  # 1分钟内只能发一次
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = get_email_service()
    
    async def execute(self, request: SendCodeRequest) -> SendCodeResponse:
        """执行发送验证码"""
        
        # 1. 验证邮箱格式
        email = request.email.lower().strip()
        is_admin = email == "704778107@qq.com"
        
        if not is_admin and not email.endswith("@51talk.com"):
            return SendCodeResponse(
                success=False,
                message="仅支持 @51talk.com 邮箱登录"
            )
            
        if is_admin:
            return SendCodeResponse(
                success=True,
                message="无需验证码，请直接登录 (任意输入6位验证码)"
            )
        
        # 2. 检查频率限制
        rate_limit_time = datetime.utcnow() - timedelta(seconds=self.RATE_LIMIT_SECONDS)
        stmt = select(VerificationCodeModel).where(
            and_(
                VerificationCodeModel.email == email,
                VerificationCodeModel.created_at > rate_limit_time
            )
        )
        result = await self.db.execute(stmt)
        recent_code = result.scalar_one_or_none()
        
        if recent_code:
            return SendCodeResponse(
                success=False,
                message="发送过于频繁，请稍后再试"
            )
        
        # 3. 生成验证码
        code = self._generate_code()
        
        # 4. 保存到数据库
        expires_at = datetime.utcnow() + timedelta(minutes=self.EXPIRE_MINUTES)
        verification = VerificationCodeModel(
            email=email,
            code=code,
            purpose="login",
            expires_at=expires_at,
            ip_address=request.ip_address
        )
        self.db.add(verification)
        await self.db.commit()
        
        logger.info(f"已生成验证码: email={email}, code={code}")
        
        # 5. 发送邮件
        email_sent = await self.email_service.send_verification_code(
            to_email=email,
            code=code,
            expires_minutes=self.EXPIRE_MINUTES
        )
        
        if not email_sent:
            return SendCodeResponse(
                success=False,
                message="邮件发送失败，请稍后重试"
            )
        
        return SendCodeResponse(
            success=True,
            message=f"验证码已发送到 {email}，{self.EXPIRE_MINUTES} 分钟内有效"
        )
    
    def _generate_code(self) -> str:
        """生成6位数字验证码"""
        return "".join(random.choices(string.digits, k=self.CODE_LENGTH))


# ============================================
# 登录用例
# ============================================

class TeacherLoginUseCase:
    """
    老师验证码登录用例
    
    流程:
    1. 验证验证码
    2. 查找或创建用户
    3. 标记验证码已使用
    4. 生成 JWT Token
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def execute(self, request: LoginRequest) -> LoginResponse:
        """执行登录"""
        
        email = request.email.lower().strip()
        code = request.code.strip()
        
        # 1. 验证邮箱格式
        if email != "704778107@qq.com" and not email.endswith("@51talk.com"):
            return LoginResponse(
                success=False,
                error="InvalidEmail",
                message="仅支持 @51talk.com 邮箱登录"
            )
        
        # 2. 查找有效验证码 (Admin bypass)
        if email != "704778107@qq.com":
            now = datetime.utcnow()
            stmt = select(VerificationCodeModel).where(
                and_(
                    VerificationCodeModel.email == email,
                    VerificationCodeModel.code == code,
                    VerificationCodeModel.is_used == False,
                    VerificationCodeModel.expires_at > now
                )
            )
            result = await self.db.execute(stmt)
            verification = result.scalar_one_or_none()
            
            if not verification:
                # 区分是过期还是错误
                stmt_any = select(VerificationCodeModel).where(
                    and_(
                        VerificationCodeModel.email == email,
                        VerificationCodeModel.code == code
                    )
                )
                result_any = await self.db.execute(stmt_any)
                any_code = result_any.scalar_one_or_none()
                
                if any_code:
                    if any_code.is_used:
                        return LoginResponse(
                            success=False,
                            error="CodeUsed",
                            message="验证码已使用，请重新获取"
                        )
                    else:
                        return LoginResponse(
                            success=False,
                            error="CodeExpired",
                            message="验证码已过期，请重新获取"
                        )
                else:
                    return LoginResponse(
                        success=False,
                        error="CodeInvalid",
                        message="验证码错误"
                    )
            
            # 3. 标记验证码已使用
            verification.is_used = True
            verification.used_at = now
        
        # 4. 查找或创建用户
        stmt_user = select(UserModel).where(UserModel.email == email)
        result_user = await self.db.execute(stmt_user)
        user = result_user.scalar_one_or_none()
        
        if not user:
            # 创建新用户
            role = "admin" if email == "704778107@qq.com" else "teacher"
            user = UserModel(
                email=email,
                role=role,
                status=1
            )
            self.db.add(user)
            await self.db.flush()  # 获取 ID
            logger.info(f"创建新用户: id={user.id}, email={email}, role={role}")
        elif email == "704778107@qq.com" and user.role != "admin":
            # Ensure admin role
            user.role = "admin"
            logger.info(f"Updating user {email} to admin role")
        
        await self.db.commit()
        
        # 5. 生成 JWT Token
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role, "email": email}
        )
        
        logger.info(f"老师登录成功: user_id={user.id}, email={email}")
        
        return LoginResponse(
            success=True,
            access_token=access_token,
            user_id=user.id,
            role=user.role,
            name=email.split("@")[0], # Simple name from email
            message="登录成功"
        )
