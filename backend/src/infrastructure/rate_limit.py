"""
Rate Limiting Middleware

Provides Redis-based rate limiting for production (multi-instance safe).
Falls back to in-memory limiting for development when Redis is unavailable.

Security:
- Uses sliding window algorithm for accurate rate limiting
- Redis-based for production (works across multiple instances)
- Memory-bounded in fallback mode (max 10000 keys with LRU eviction)
"""
import time
import logging
from collections import OrderedDict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.infrastructure.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global Redis client (lazy initialized)
_redis_client = None
_redis_available = None


async def _get_redis():
    """Get or create Redis client with connection pooling."""
    global _redis_client, _redis_available
    
    if _redis_available is False:
        return None
    
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            await _redis_client.ping()
            _redis_available = True
            logger.info("Redis rate limiting enabled")
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting, using in-memory fallback: {e}")
            _redis_available = False
            _redis_client = None
            return None
    
    return _redis_client


class LRUDict(OrderedDict):
    """LRU dictionary with max size to prevent memory exhaustion."""
    
    def __init__(self, max_size: int = 10000):
        super().__init__()
        self.max_size = max_size
    
    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            oldest = next(iter(self))
            del self[oldest]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with Redis support.
    
    Features:
    - Redis-based for production (multi-instance safe)
    - In-memory fallback with LRU eviction
    - Sliding window algorithm
    - Standard rate limit headers
    
    Headers added to all responses:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests in current window
    - X-RateLimit-Reset: Unix timestamp when the window resets
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        # Memory-bounded fallback storage with LRU eviction
        self._fallback_counts: LRUDict = LRUDict(max_size=10000)
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Try to get user ID from state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"ratelimit:user:{user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ratelimit:ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ratelimit:ip:{client_host}"
    
    async def _check_rate_limit_redis(self, client_key: str, current_time: float) -> tuple[int, int]:
        """
        Check rate limit using Redis sliding window.
        Returns (request_count, remaining).
        """
        redis = await _get_redis()
        if not redis:
            return await self._check_rate_limit_memory(client_key, current_time)
        
        try:
            pipe = redis.pipeline()
            cutoff = current_time - self.window_seconds
            
            # Remove old entries and add new one atomically
            pipe.zremrangebyscore(client_key, 0, cutoff)
            pipe.zadd(client_key, {str(current_time): current_time})
            pipe.zcard(client_key)
            pipe.expire(client_key, self.window_seconds + 1)
            
            results = await pipe.execute()
            request_count = results[2]
            remaining = max(0, self.requests_per_minute - request_count)
            
            return request_count, remaining
        except Exception as e:
            logger.warning(f"Redis rate limit error, falling back to memory: {e}")
            return await self._check_rate_limit_memory(client_key, current_time)
    
    async def _check_rate_limit_memory(self, client_key: str, current_time: float) -> tuple[int, int]:
        """
        Check rate limit using in-memory sliding window (fallback).
        Memory-bounded with LRU eviction.
        """
        cutoff = current_time - self.window_seconds
        
        # Get existing timestamps and filter old ones
        timestamps = self._fallback_counts.get(client_key, [])
        timestamps = [ts for ts in timestamps if ts > cutoff]
        
        # Add current timestamp
        timestamps.append(current_time)
        self._fallback_counts[client_key] = timestamps
        
        request_count = len(timestamps)
        remaining = max(0, self.requests_per_minute - request_count)
        
        return request_count, remaining
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/health/detailed", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        current_time = time.time()
        client_key = self._get_client_key(request)
        reset_time = int(current_time + self.window_seconds)
        
        # Check rate limit (Redis or memory fallback)
        request_count, remaining = await self._check_rate_limit_redis(client_key, current_time)
        
        # Check if rate limited (use > instead of >= since we already added the request)
        if request_count > self.requests_per_minute:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too Many Requests",
                    "message": f"Rate limit exceeded. Try again in {self.window_seconds} seconds."
                }
            )
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            response.headers["Retry-After"] = str(self.window_seconds)
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
