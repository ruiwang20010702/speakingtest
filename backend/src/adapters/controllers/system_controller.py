"""
System Controller
Handles system-level endpoints like AI engine status checks.
"""
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from loguru import logger

from src.infrastructure.config import get_settings


router = APIRouter()
settings = get_settings()


class AIStatusResponse(BaseModel):
    """AI Engine status response."""
    status: str  # "online", "offline", "checking"
    model: str
    message: str


@router.get(
    "/ai-status",
    response_model=AIStatusResponse,
    summary="检查 AI 引擎状态",
    description="检查 Qwen-Omni AI 引擎是否可用。"
)
async def get_ai_status():
    """
    Check AI engine status.
    
    Performs a quick validation to check if the Qwen API is configured and reachable.
    """
    model_name = settings.QWEN_MODEL
    
    # Check if API key is configured
    if not settings.QWEN_API_KEY:
        return AIStatusResponse(
            status="offline",
            model=model_name,
            message="API Key 未配置"
        )
    
    # Try a quick API call to verify connectivity
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            timeout=5.0  # Quick timeout for status check
        )
        
        # Simple models list call to verify API is reachable
        # This is faster than making an actual completion request
        try:
            # Use asyncio.wait_for to enforce timeout
            await asyncio.wait_for(
                client.models.list(),
                timeout=3.0
            )
            
            return AIStatusResponse(
                status="online",
                model=model_name,
                message="运行中"
            )
        except asyncio.TimeoutError:
            logger.warning("AI status check timed out")
            return AIStatusResponse(
                status="offline",
                model=model_name,
                message="连接超时"
            )
            
    except ImportError:
        # OpenAI package not installed, check config only
        return AIStatusResponse(
            status="online",
            model=model_name,
            message="已配置"
        )
    except Exception as e:
        logger.error(f"AI status check failed: {e}")
        return AIStatusResponse(
            status="offline",
            model=model_name,
            message=f"连接失败"
        )
