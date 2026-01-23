"""
文件上传控制器
处理音频文件上传到 OSS

Security:
- All uploads require authentication
- Users can only upload to tests they own
- Students: can only upload to tests where test.student_id == user_id
- Teachers/Admins: can upload to their students' tests

Performance:
- Concurrent upload limit (prevents memory exhaustion under high load)
- Configurable via UPLOAD_MAX_CONCURRENT environment variable
"""
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from src.infrastructure.database import get_db
from src.infrastructure.auth import decode_token, oauth2_scheme
from src.infrastructure.responses import ErrorResponse
from src.infrastructure.config import get_settings
from src.adapters.gateways.oss_client import get_oss_client
from src.adapters.repositories.models import TestModel, StudentProfileModel

logger = logging.getLogger(__name__)
settings = get_settings()

# Global semaphore for limiting concurrent uploads
# Prevents memory exhaustion when many users upload simultaneously
_upload_semaphore: Optional[asyncio.Semaphore] = None


def get_upload_semaphore() -> asyncio.Semaphore:
    """Get the upload semaphore (lazy initialized)."""
    global _upload_semaphore
    if _upload_semaphore is None:
        _upload_semaphore = asyncio.Semaphore(settings.UPLOAD_MAX_CONCURRENT)
        logger.info(f"Upload semaphore initialized: max_concurrent={settings.UPLOAD_MAX_CONCURRENT}")
    return _upload_semaphore

router = APIRouter()


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    url: Optional[str] = None
    key: Optional[str] = None
    message: str = ""


async def get_current_user_with_role(token: str = Depends(oauth2_scheme)):
    """Get current user ID and role from token."""
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    return {"user_id": token_data.user_id, "role": token_data.role}


async def verify_upload_permission(
    test_id: int,
    user_id: int,
    role: str,
    db: AsyncSession
) -> TestModel:
    """
    Verify that the user has permission to upload audio to this test.
    
    - Students: can only upload to their own tests
    - Teachers: can only upload to tests of their students  
    - Admins: can upload to any test
    
    Returns the test if authorized, raises HTTPException otherwise.
    """
    stmt = select(TestModel).where(TestModel.id == test_id)
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "TestNotFound", "message": "测评记录不存在"}
        )
    
    # Admin can upload to any test
    if role == "admin":
        return test
    
    # Student can only upload to their own test
    if role == "student":
        if test.student_id != user_id:
            logger.warning(f"Student {user_id} tried to upload to test {test_id} (owner: {test.student_id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Forbidden", "message": "无权上传到此测评"}
            )
        return test
    
    # Teacher can upload to their students' tests
    if role == "teacher":
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == test.student_id,
            StudentProfileModel.teacher_id == user_id
        )
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            logger.warning(f"Teacher {user_id} tried to upload to test {test_id} (student: {test.student_id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Forbidden", "message": "无权上传到此测评（非您的学生）"}
            )
        return test
    
    # Unknown role - deny
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Forbidden", "message": "无权上传"}
    )


@router.post(
    "/audio",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse}
    }
)
async def upload_audio(
    test_id: int = Form(..., description="测评 ID"),
    part: str = Form(..., description="部分 (part1/part2)"),
    audio: UploadFile = File(..., description="音频文件"),
    user: dict = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """
    上传音频文件到 OSS。
    
    前端录音完成后调用此接口上传音频，获取 URL 后再调用评测接口。
    
    支持格式: mp3, wav, m4a, webm, pcm
    最大大小: 可配置 (默认 20MB)
    
    Security: Users can only upload to tests they own.
    Performance: Concurrent uploads limited to prevent memory exhaustion.
    """
    # Verify ownership before allowing upload
    await verify_upload_permission(test_id, user["user_id"], user["role"], db)
    
    # 验证文件类型
    allowed_extensions = ["mp3", "wav", "m4a", "webm", "pcm"]
    
    # 获取扩展名
    extension = "mp3"
    if audio.filename:
        ext = audio.filename.split(".")[-1].lower()
        if ext in allowed_extensions:
            extension = ext
    
    # 验证 part 参数（在读取文件前验证，避免不必要的 IO）
    if part not in ("part1", "part2"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "InvalidPart", "message": "part 必须是 part1 或 part2"}
        )
    
    # 使用并发限制信号量（防止内存爆炸）
    semaphore = get_upload_semaphore()
    
    # Try to acquire semaphore with timeout
    try:
        # Wait up to 30 seconds for upload slot
        acquired = await asyncio.wait_for(semaphore.acquire(), timeout=30.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "ServerBusy",
                "message": "服务器繁忙，请稍后重试"
            }
        )
    
    try:
        # 读取文件内容（在信号量保护下）
        audio_data = await audio.read()
        
        # 验证大小
        max_size = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
        if len(audio_data) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "FileTooLarge",
                    "message": f"文件过大，最大支持 {settings.UPLOAD_MAX_SIZE_MB}MB"
                }
        )
    
    # 上传到 OSS
    oss_client = get_oss_client()
    result = await oss_client.upload_audio(
        audio_data=audio_data,
        test_id=test_id,
        part=part,
        extension=extension
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UploadFailed", "message": result.error}
        )
    
    return UploadResponse(
        success=True,
        url=result.url,
        key=result.key,
        message="上传成功"
    )
    finally:
        # Always release semaphore
        semaphore.release()
