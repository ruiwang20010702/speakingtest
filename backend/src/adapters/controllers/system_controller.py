"""
System Controller
Handles system-level endpoints like AI engine status checks.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from src.infrastructure.config import get_settings


router = APIRouter()
settings = get_settings()


class AIStatusResponse(BaseModel):
    """AI Engine status response."""
    status: str  # "online", "offline"
    model: str
    message: str


@router.get(
    "/ai-status",
    response_model=AIStatusResponse,
    summary="检查 AI 引擎配置状态",
    description="检查 Qwen-Omni AI 引擎是否已配置（不验证连接，减少 API 调用）。"
)
async def get_ai_status():
    """
    Check AI engine configuration status.
    
    Only checks if the API key is configured, does NOT make external API calls.
    This keeps the endpoint fast and avoids unnecessary API usage.
    """
    model_name = settings.QWEN_MODEL
    
    # Only check if API key is configured (no external API call)
    if settings.QWEN_API_KEY:
        return AIStatusResponse(
            status="online",
            model=model_name,
            message="已配置"
        )
    else:
        return AIStatusResponse(
            status="offline",
            model=model_name,
            message="API Key 未配置"
        )
