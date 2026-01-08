"""
Teacher Auth Controller
基于 /api-design-principles 和 /fastapi-auth-patterns 设计
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.responses import ErrorResponse
from src.infrastructure.audit import log_audit
from src.use_cases.teacher_login import (
    SendVerificationCodeUseCase,
    TeacherLoginUseCase,
    SendCodeRequest,
    LoginRequest
)

router = APIRouter()


# ============================================
# 请求/响应 Schema
# ============================================

class SendCodeRequestSchema(BaseModel):
    """发送验证码请求"""
    email: str
    
    @validator("email")
    def validate_email(cls, v):
        v = v.lower().strip()
        if v == "704778107@qq.com":
            return v
        if not v.endswith("@51talk.com"):
            raise ValueError("仅支持 @51talk.com 邮箱")
        return v


class SendCodeResponseSchema(BaseModel):
    """发送验证码响应"""
    success: bool
    message: str


class LoginRequestSchema(BaseModel):
    """登录请求"""
    email: str
    code: str
    
    @validator("email")
    def validate_email(cls, v):
        return v.lower().strip()
    
    @validator("code")
    def validate_code(cls, v):
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("验证码必须是6位数字")
        return v


class LoginResponseSchema(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    name: str = "Teacher"


# ============================================
# API 端点
# ============================================

@router.post(
    "/send-code",
    response_model=SendCodeResponseSchema,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse}
    },
    summary="发送验证码",
    description="向指定邮箱发送6位登录验证码，仅支持 @51talk.com 邮箱"
)
async def send_verification_code(
    request: SendCodeRequestSchema,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    发送登录验证码到老师邮箱
    
    - 仅支持 @51talk.com 邮箱
    - 验证码5分钟内有效
    - 1分钟内只能发送一次
    """
    # 获取客户端IP
    client_ip = http_request.client.host if http_request.client else None
    
    use_case = SendVerificationCodeUseCase(db)
    result = await use_case.execute(
        SendCodeRequest(
            email=request.email,
            ip_address=client_ip
        )
    )
    
    if not result.success:
        # 区分不同错误类型
        if "频繁" in result.message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "TooManyRequests", "message": result.message}
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SendCodeFailed", "message": result.message}
        )
    
    return SendCodeResponseSchema(
        success=True,
        message=result.message
    )


@router.post(
    "/login",
    response_model=LoginResponseSchema,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    },
    summary="验证码登录",
    description="使用邮箱验证码登录，返回 JWT Token"
)
async def login_with_code(
    request: LoginRequestSchema,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    老师验证码登录
    
    - 验证码正确且未过期时，返回 JWT Token
    - 如果用户不存在，自动创建新用户
    """
    use_case = TeacherLoginUseCase(db)
    result = await use_case.execute(
        LoginRequest(
            email=request.email,
            code=request.code
        )
    )
    
    if not result.success:
        status_code = status.HTTP_400_BAD_REQUEST
        if result.error in ["CodeExpired", "CodeInvalid", "CodeUsed"]:
            status_code = status.HTTP_401_UNAUTHORIZED
        
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error, "message": result.message}
        )
    
    # Audit Log
    await log_audit(
        db=db,
        operator_id=result.user_id,
        action="LOGIN",
        target_type="user",
        target_id=result.user_id,
        details={"email": request.email, "role": result.role},
        request=http_request
    )
    
    return LoginResponseSchema(
        access_token=result.access_token,
        user_id=result.user_id,
        role=result.role,
        name=result.name or "Teacher"
    )
