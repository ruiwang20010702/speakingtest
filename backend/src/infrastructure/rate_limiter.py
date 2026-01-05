"""
Rate Limiter Utilities
Implements Semaphore-based rate limiting for external APIs.
Based on /async-python-patterns Pattern 9.
"""
import asyncio
from typing import Dict
from src.infrastructure.config import get_settings

settings = get_settings()


class RateLimiter:
    """
    Singleton rate limiter for external API calls.
    Uses asyncio.Semaphore for concurrency control.
    """
    _instances: Dict[str, asyncio.Semaphore] = {}

    @classmethod
    def get_xunfei_limiter(cls) -> asyncio.Semaphore:
        """
        Get Xunfei API rate limiter.
        Limits to XUNFEI_MAX_CONCURRENT (default 50) concurrent connections.
        """
        if "xunfei" not in cls._instances:
            cls._instances["xunfei"] = asyncio.Semaphore(settings.XUNFEI_MAX_CONCURRENT)
        return cls._instances["xunfei"]

    @classmethod
    def get_qwen_limiter(cls) -> asyncio.Semaphore:
        """
        Get Qwen API rate limiter.
        Limits to 1 request per second (60 RPM).
        Note: This is a simple semaphore; for true RPM limiting,
        use a token bucket or sliding window in production.
        """
        if "qwen" not in cls._instances:
            # Allow only 1 concurrent request to self-throttle
            cls._instances["qwen"] = asyncio.Semaphore(1)
        return cls._instances["qwen"]


async def with_xunfei_limit(coro):
    """
    Execute coroutine with Xunfei rate limiting.
    Usage:
        result = await with_xunfei_limit(xunfei_api_call())
    """
    semaphore = RateLimiter.get_xunfei_limiter()
    async with semaphore:
        return await coro


async def with_qwen_limit(coro):
    """
    Execute coroutine with Qwen rate limiting.
    Adds a 1-second delay after each call to respect 60 RPM.
    """
    semaphore = RateLimiter.get_qwen_limiter()
    async with semaphore:
        result = await coro
        await asyncio.sleep(1.0)  # Enforce 1 req/sec
        return result
