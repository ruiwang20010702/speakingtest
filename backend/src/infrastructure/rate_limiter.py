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
    def get_qwen_omni_limiter(cls) -> asyncio.Semaphore:
        """
        Get Qwen Omni (音频评测) API rate limiter.
        qwen3-omni-flash RPM=60, allow 5 concurrent requests.
        Used for Part 1/Part 2 audio evaluation.
        """
        if "qwen_omni" not in cls._instances:
            cls._instances["qwen_omni"] = asyncio.Semaphore(5)
        return cls._instances["qwen_omni"]

    @classmethod
    def get_qwen_plus_limiter(cls) -> asyncio.Semaphore:
        """
        Get Qwen Plus (文本分析) API rate limiter.
        qwen-plus RPM=600, allow 10 concurrent requests.
        Used for summary analysis, report interpretation, course selling.
        """
        if "qwen_plus" not in cls._instances:
            cls._instances["qwen_plus"] = asyncio.Semaphore(10)
        return cls._instances["qwen_plus"]

    @classmethod
    def get_qwen_limiter(cls) -> asyncio.Semaphore:
        """
        [Deprecated] Use get_qwen_omni_limiter() or get_qwen_plus_limiter() instead.
        Kept for backward compatibility, defaults to omni limiter.
        """
        return cls.get_qwen_omni_limiter()


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
