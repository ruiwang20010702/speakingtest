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

        NOTE:
        - 这是当前线上实际使用的 Qwen 文本模型限流器；
        - 所有 qwen-plus 相关调用都应该通过该 Semaphore 做并发控制；
        - 具体并发上限由这里的常量（目前为 10）控制，如需调整请修改此处。
        """
        if "qwen_plus" not in cls._instances:
            cls._instances["qwen_plus"] = asyncio.Semaphore(10)
        return cls._instances["qwen_plus"]

    @classmethod
    def get_qwen_limiter(cls) -> asyncio.Semaphore:
        """
        [LEGACY / COMPAT ONLY]

        旧版统一 Qwen 限流入口，目前项目代码中**已不再主动使用**。

        - 新代码请直接使用：
          - `get_qwen_omni_limiter()` 控制音频评测并发（Part1 / Part2）
          - `get_qwen_plus_limiter()` 控制文本分析并发（汇总分析 / 报告解读等）
        - 仅保留给历史代码或外部脚本做兼容使用，默认返回 omni 限流器。
        - 如需删除，请先全局搜索确认没有外部依赖。
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
    [LEGACY HELPER]

    旧版 Qwen 限流封装，目前项目主流程中**没有引用**。

    历史行为：
    - 使用 `get_qwen_limiter()` 获取统一的 Qwen Semaphore；
    - 每次调用后强制 `sleep(1.0)`，相当于最多 1 QPS。

    当前推荐做法：
    - 对音频评测：直接使用 `RateLimiter.get_qwen_omni_limiter()` 并在调用处 `async with`。
    - 对文本分析：直接使用 `RateLimiter.get_qwen_plus_limiter()` 并在调用处 `async with`。

    如果没有兼容性需求，可以考虑后续删除该 helper。
    """
    semaphore = RateLimiter.get_qwen_limiter()
    async with semaphore:
        result = await coro
        await asyncio.sleep(1.0)  # Enforce 1 req/sec
        return result
