"""
Rate Limiting Middleware

Provides simple in-memory rate limiting with standard response headers.
For production, consider using Redis-based rate limiting.
"""
import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.infrastructure.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    Adds the following headers to all responses:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests in current window
    - X-RateLimit-Reset: Unix timestamp when the window resets
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        # {client_key: [(timestamp1, timestamp2, ...)]}
        self.request_counts: dict = defaultdict(list)
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Try to get user ID from state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def _cleanup_old_requests(self, client_key: str, current_time: float):
        """Remove requests outside the current window."""
        cutoff = current_time - self.window_seconds
        self.request_counts[client_key] = [
            ts for ts in self.request_counts[client_key] if ts > cutoff
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        current_time = time.time()
        client_key = self._get_client_key(request)
        
        # Clean up old requests
        self._cleanup_old_requests(client_key, current_time)
        
        # Calculate remaining requests
        request_count = len(self.request_counts[client_key])
        remaining = max(0, self.requests_per_minute - request_count)
        reset_time = int(current_time + self.window_seconds)
        
        # Check if rate limited
        if request_count >= self.requests_per_minute:
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
        
        # Record this request
        self.request_counts[client_key].append(current_time)
        remaining = max(0, self.requests_per_minute - len(self.request_counts[client_key]))
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
