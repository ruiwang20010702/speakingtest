---
description: Implement structured logging with Loguru or standard logging for Python applications.
---

# Python Logging Patterns

Implement structured, production-ready logging for Python applications using Loguru or the standard library.

## When to Use This Skill

- Setting up application logging
- Implementing structured (JSON) logging for log aggregation
- Configuring log rotation and retention
- Adding request tracing and correlation IDs
- Debugging production issues

## Core Concepts

### 1. Log Levels

| Level | Use Case |
| :--- | :--- |
| `DEBUG` | Detailed diagnostic info (dev only) |
| `INFO` | General operational events |
| `WARNING` | Unexpected but recoverable situations |
| `ERROR` | Errors that need attention |
| `CRITICAL` | System-breaking failures |

### 2. Structured Logging

Output logs as JSON for easy parsing by log aggregators (ELK, CloudWatch, etc.).

## Logging Patterns

### Pattern 1: Loguru Setup (Recommended)

Loguru is simpler and more powerful than stdlib logging.

```python
import sys
from loguru import logger

def setup_logging(log_level: str = "INFO", json_logs: bool = False):
    """
    Configure Loguru logger.
    - Console output with colors (dev)
    - JSON output for production
    - File rotation
    """
    # Remove default handler
    logger.remove()
    
    # Console handler
    if json_logs:
        logger.add(
            sys.stdout,
            format="{message}",
            serialize=True,  # JSON output
            level=log_level,
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True,
        )
    
    # File handler with rotation
    logger.add(
        "logs/app.log",
        rotation="100 MB",
        retention="7 days",
        compression="gz",
        level=log_level,
        serialize=json_logs,
    )
    
    return logger
```

### Pattern 2: Request Logging Middleware (FastAPI)

```python
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with timing and correlation ID.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        request_id = str(uuid.uuid4())[:8]
        
        # Add to request state for downstream access
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host,
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response

# Usage in FastAPI
# app.add_middleware(RequestLoggingMiddleware)
```

### Pattern 3: Context-Aware Logging

```python
from contextvars import ContextVar
from loguru import logger

# Context variable for request-scoped data
request_context: ContextVar[dict] = ContextVar("request_context", default={})

def get_context_logger():
    """Get logger with current request context."""
    context = request_context.get()
    return logger.bind(**context)

# Usage
def set_request_context(request_id: str, user_id: int = None):
    """Set context for current request."""
    ctx = {"request_id": request_id}
    if user_id:
        ctx["user_id"] = user_id
    request_context.set(ctx)

# In your code:
# set_request_context("abc123", user_id=42)
# log = get_context_logger()
# log.info("User performed action")  # Automatically includes request_id and user_id
```

### Pattern 4: Exception Logging

```python
from loguru import logger

@logger.catch(reraise=True)
async def risky_operation():
    """
    Any exception here is automatically logged with full traceback.
    """
    result = 1 / 0  # This will be logged automatically
    return result

# Or manually:
try:
    await risky_operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    raise
```

### Pattern 5: Standard Library Logging (Alternative)

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON output."""
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        
        return json.dumps(log_record)

def setup_stdlib_logging(log_level: str = "INFO"):
    """Configure standard library logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        handlers=[handler],
    )
    
    return logging.getLogger(__name__)
```

## Log Aggregation Integration

### For ELK Stack / CloudWatch / Datadog

1. Use JSON format (`serialize=True` in Loguru)
2. Include standard fields: `timestamp`, `level`, `message`, `service`
3. Add correlation IDs for request tracing

### Sample JSON Log Output

```json
{
  "timestamp": "2026-01-05T15:00:00.000Z",
  "level": "INFO",
  "message": "Request completed",
  "service": "speaking-test",
  "request_id": "abc12345",
  "method": "POST",
  "path": "/api/v1/tests",
  "status_code": 201,
  "duration_ms": 123.45,
  "user_id": 42
}
```

## Best Practices

1. **Don't log sensitive data**: Never log passwords, tokens, or PII.
2. **Use structured logging**: JSON is easier to search and aggregate.
3. **Include context**: Request ID, user ID, trace ID.
4. **Set appropriate levels**: Use DEBUG only in dev.
5. **Rotate logs**: Prevent disk space exhaustion.

## Checklist

- [ ] Log level configurable via environment?
- [ ] Request ID included in all logs?
- [ ] Sensitive data excluded from logs?
- [ ] Log rotation configured?
- [ ] JSON format for production?
