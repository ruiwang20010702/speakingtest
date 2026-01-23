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
from src.infrastructure.crm_service import fetch_crm_user_info, update_user_crm_info
from src.infrastructure.timezone import now as china_now


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
    RATE_LIMIT_SECONDS = 60  # 同一邮箱 1 分钟内只能发一次
    IP_RATE_LIMIT_COUNT = 10  # 同一 IP 10 分钟内最多发 10 次
    IP_RATE_LIMIT_WINDOW = 600  # 10 分钟窗口
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = get_email_service()
    
    async def execute(self, request: SendCodeRequest) -> SendCodeResponse:
        """执行发送验证码"""
        from src.infrastructure.config import get_settings
        settings = get_settings()
        
        # 1. 验证邮箱格式
        email = request.email.lower().strip()
        
        # 检查测试邮箱白名单（仅限 ENABLE_TEST_AUTH 模式）
        is_whitelisted = False
        if settings.ENABLE_TEST_AUTH and settings.TEST_EMAIL_WHITELIST:
            whitelist = [e.strip().lower() for e in settings.TEST_EMAIL_WHITELIST.split(",") if e.strip()]
            is_whitelisted = email in whitelist
        
        if not is_whitelisted and not email.endswith("@51talk.com"):
            return SendCodeResponse(
                success=False,
                message="仅支持 @51talk.com 邮箱登录"
            )
        
        # 2. 检查频率限制
        # 2a. 同一邮箱频率限制
        rate_limit_time = china_now() - timedelta(seconds=self.RATE_LIMIT_SECONDS)
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
        
        # 2b. 同一 IP 频率限制（防暴力攻击）
        if request.ip_address:
            from sqlalchemy import func
            ip_window = china_now() - timedelta(seconds=self.IP_RATE_LIMIT_WINDOW)
            ip_count_stmt = select(func.count(VerificationCodeModel.id)).where(
                and_(
                    VerificationCodeModel.ip_address == request.ip_address,
                    VerificationCodeModel.created_at > ip_window
                )
            )
            ip_count = (await self.db.execute(ip_count_stmt)).scalar() or 0
            
            if ip_count >= self.IP_RATE_LIMIT_COUNT:
                logger.warning(f"IP 频率限制触发: ip={request.ip_address}, count={ip_count}")
                return SendCodeResponse(
                    success=False,
                    message="请求过于频繁，请稍后再试"
                )
        
        # 3. 生成验证码
        code = self._generate_code()
        
        # 4. 保存到数据库
        expires_at = china_now() + timedelta(minutes=self.EXPIRE_MINUTES)
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
        from src.infrastructure.config import get_settings
        settings = get_settings()
        
        email = request.email.lower().strip()
        code = request.code.strip()
        
        # 1. 验证邮箱格式 - 检查测试邮箱白名单
        is_whitelisted = False
        if settings.ENABLE_TEST_AUTH and settings.TEST_EMAIL_WHITELIST:
            whitelist = [e.strip().lower() for e in settings.TEST_EMAIL_WHITELIST.split(",") if e.strip()]
            is_whitelisted = email in whitelist
        
        if not is_whitelisted and not email.endswith("@51talk.com"):
            return LoginResponse(
                success=False,
                error="InvalidEmail",
                message="仅支持 @51talk.com 邮箱登录"
            )
        
        # 2. 验证验证码
        # MAGIC CODE: Allow 888888 ONLY when ENABLE_TEST_AUTH=true (for stress testing)
        # This should NEVER be enabled in production!
        use_magic_code = settings.ENABLE_TEST_AUTH and code == "888888"
        
        if use_magic_code:
            logger.warning(f"[TEST MODE] Magic code bypass for {email} - ENABLE_TEST_AUTH is ON!")
            # Skip verification check, proceed to find/create user
            verification = None  # No verification record to mark as used
        else:
            now = china_now()
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
        
        # 从配置获取管理员邮箱列表（已在函数开头获取 settings）
        admin_emails = [e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]
        is_admin = email.lower() in admin_emails
        
        is_new_user = False
        if not user:
            # 创建新用户
            role = "admin" if is_admin else "teacher"
            user = UserModel(
                email=email,
                role=role,
                status=1
            )
            self.db.add(user)
            await self.db.flush()  # 获取 ID
            is_new_user = True
            logger.info(f"创建新用户: id={user.id}, email={email}, role={role}")
        elif is_admin and user.role != "admin":
            # Ensure admin role for configured admins
            user.role = "admin"
            logger.info(f"Updating user {email} to admin role")
        
        await self.db.commit()
        
        # 5. 同步 CRM 信息（新用户、CRM 信息为空、或超过 7 天未同步）
        display_name = user.ss_crm_name or email.split("@")[0]
        
        # 判断是否需要同步 CRM 信息
        CRM_SYNC_INTERVAL_DAYS = 7
        need_sync = is_new_user or not user.ss_crm_name
        
        if not need_sync and user.crm_synced_at:
            # 检查是否超过 7 天
            days_since_sync = (china_now() - user.crm_synced_at).days
            if days_since_sync >= CRM_SYNC_INTERVAL_DAYS:
                need_sync = True
                logger.info(f"CRM 信息已过期 ({days_since_sync} 天), 需要重新同步: user_id={user.id}")
        elif not need_sync and not user.crm_synced_at:
            # 有 CRM 信息但没有同步时间记录，需要同步
            need_sync = True
        
        if need_sync:
            try:
                crm_info = await fetch_crm_user_info(email)
                if crm_info:
                    await update_user_crm_info(self.db, user, crm_info)
                    display_name = crm_info.ss_crm_name or display_name
                    logger.info(f"已同步 CRM 信息: user_id={user.id}, crm_name={crm_info.ss_crm_name}")
                else:
                    # CRM 中不存在该用户，仍然记录同步时间以避免每次登录都尝试
                    logger.info(f"CRM 中未找到用户信息，跳过同步: user_id={user.id}, email={email}")
                # 无论成功还是失败，都更新同步时间戳
                user.crm_synced_at = china_now()
                await self.db.commit()
            except Exception as e:
                # CRM 同步失败不影响登录，但记录同步尝试时间
                user.crm_synced_at = china_now()
                await self.db.commit()
                logger.warning(f"CRM 信息同步失败（不影响登录）: {e}, user_id={user.id}")
        
        # 6. 生成 JWT Token
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role, "email": email}
        )
        
        logger.info(f"老师登录成功: user_id={user.id}, email={email}")
        
        return LoginResponse(
            success=True,
            access_token=access_token,
            user_id=user.id,
            role=user.role,
            name=display_name,
            message="登录成功"
        )
