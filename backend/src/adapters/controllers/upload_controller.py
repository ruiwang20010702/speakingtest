"""
文件上传控制器
处理音频文件上传到 OSS
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.infrastructure.database import get_db
from src.infrastructure.auth import get_current_user_id
from src.infrastructure.responses import ErrorResponse
from src.adapters.gateways.oss_client import get_oss_client

router = APIRouter()


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    url: Optional[str] = None
    key: Optional[str] = None
    message: str = ""


@router.post(
    "/audio",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse}
    }
)
async def upload_audio(
    test_id: int = Form(..., description="测评 ID"),
    part: str = Form(..., description="部分 (part1/part2)"),
    audio: UploadFile = File(..., description="音频文件"),
    user_id: int = Depends(get_current_user_id)
):
    """
    上传音频文件到 OSS。
    
    前端录音完成后调用此接口上传音频，获取 URL 后再调用评测接口。
    
    支持格式: mp3, wav, m4a, webm
    最大大小: 20MB
    """
    # 验证文件类型
    allowed_extensions = ["mp3", "wav", "m4a", "webm", "pcm"]
    
    # 获取扩展名
    extension = "mp3"
    if audio.filename:
        ext = audio.filename.split(".")[-1].lower()
        if ext in allowed_extensions:
            extension = ext
    
    # 读取文件内容
    audio_data = await audio.read()
    
    # 验证大小 (20MB)
    max_size = 20 * 1024 * 1024
    if len(audio_data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "FileTooLarge", "message": "文件过大，最大支持 20MB"}
        )
    
    # 验证 part 参数
    if part not in ("part1", "part2"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "InvalidPart", "message": "part 必须是 part1 或 part2"}
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
