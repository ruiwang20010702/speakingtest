"""
Logging Configuration (Loguru)
Based on /python-logging-patterns workflow.
"""
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.config import get_settings

settings = get_settings()

# Context variable for request-scoped data
request_context: ContextVar[dict] = ContextVar("request_context", default={})


def setup_logging():
    """
    Configure Loguru logger.
    - Human-readable colored output for console
    - Detailed traceback for errors
    """
    # Remove default handler
    logger.remove()
    
    # Determine log level
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    
    # Human-readable format for all levels
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,  # Show full traceback on errors
        diagnose=True,   # Show variable values in traceback
    )
    
    logger.info(f"Logging configured: level={log_level}")
    return logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with timing and correlation ID.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        request_id = str(uuid.uuid4())[:8]
        
        # Add to request state for downstream access
        request.state.request_id = request_id
        
        # Set context for this request
        request_context.set({"request_id": request_id})
        
        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed: {response.status_code} in {duration_ms:.2f}ms",
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


def get_context_logger():
    """Get logger with current request context."""
    context = request_context.get()
    return logger.bind(**context)


def set_user_context(user_id: Optional[int]):
    """Add user ID to current request context."""
    context = request_context.get()
    context["user_id"] = user_id
    request_context.set(context)
