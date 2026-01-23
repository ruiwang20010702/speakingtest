"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.infrastructure.config import get_settings
from src.infrastructure.database import engine, Base
from src.infrastructure.logging import setup_logging, RequestLoggingMiddleware
from src.infrastructure.rate_limit import RateLimitMiddleware

settings = get_settings()

# Initialize logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    - Startup: Initialize database tables, security checks
    - Shutdown: Close connections
    """
    # Startup
    logger.info("Application starting up...")
    
    # Security check: Reject default JWT secret in production
    DEFAULT_JWT_SECRET = "your-secret-key-change-in-production"
    if settings.JWT_SECRET_KEY == DEFAULT_JWT_SECRET and not settings.DEBUG:
        logger.critical("SECURITY ERROR: JWT_SECRET_KEY is using default value in production!")
        logger.critical("Please set a secure JWT_SECRET_KEY in your environment variables.")
        raise RuntimeError("Cannot start application with default JWT_SECRET_KEY in production")
    elif settings.JWT_SECRET_KEY == DEFAULT_JWT_SECRET:
        logger.warning("WARNING: Using default JWT_SECRET_KEY. This is only acceptable in development.")
    
    # Database health check
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified successfully")
    except Exception as e:
        logger.critical(f"Database connection failed: {e}")
        raise RuntimeError(f"Cannot start application: Database connection failed - {e}")

    yield

    # Shutdown
    logger.info("Application shutting down...")
    
    # 关闭全局 HTTP 客户端
    from src.infrastructure.http_client import close_http_client
    await close_http_client()
    
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="口语测评系统 API",
    lifespan=lifespan,
)

# CORS 配置：生产环境必须显式配置 CORS_ORIGINS 环境变量
def _get_cors_origins() -> list:
    """
    获取 CORS 允许的域名列表
    
    Security:
    - 生产环境必须显式配置 CORS_ORIGINS
    - 不再回退到 "*"，防止任意域跨站调用
    - 使用 Cookie 认证时，不能使用通配符 "*"
    """
    if settings.CORS_ORIGINS:
        # 从环境变量解析（逗号分隔）
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
        logger.info(f"CORS origins configured: {origins}")
        return origins
    elif settings.DEBUG:
        # 开发环境：使用常见的本地开发地址
        # 注意：使用 Cookie (credentials) 时不能用通配符 "*"
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:3002",
            "http://localhost:5173",  # Vite 默认端口
            "http://localhost:5174",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]
        logger.warning(f"DEBUG mode: CORS allowing development origins: {dev_origins}")
        return dev_origins
    else:
        # 生产环境：从前端 URL 配置中提取，但不允许空配置
        origins = []
        from urllib.parse import urlparse
        
        if settings.FRONTEND_STUDENT_URL:
            parsed = urlparse(settings.FRONTEND_STUDENT_URL)
            if parsed.scheme and parsed.netloc:
                origins.append(f"{parsed.scheme}://{parsed.netloc}")
        if settings.FRONTEND_PARENT_URL:
            parsed = urlparse(settings.FRONTEND_PARENT_URL)
            if parsed.scheme and parsed.netloc:
                origins.append(f"{parsed.scheme}://{parsed.netloc}")
        if settings.FRONTEND_TEACHER_URL:
            parsed = urlparse(settings.FRONTEND_TEACHER_URL)
            if parsed.scheme and parsed.netloc:
                origins.append(f"{parsed.scheme}://{parsed.netloc}")
        
        if not origins:
            # 生产环境没有配置任何 CORS 域名，这是安全风险
            logger.critical("SECURITY WARNING: No CORS_ORIGINS configured in production!")
            logger.critical("API will reject all cross-origin requests. Set CORS_ORIGINS env variable.")
            # 返回空列表而非 "*"，这将导致所有跨域请求被拒绝
            # 这比允许所有域名更安全
            return []
        
        logger.info(f"CORS origins derived from frontend URLs: {origins}")
        return origins

# Middleware (order matters: first added = last executed)
app.add_middleware(RequestLoggingMiddleware)  # Request logging with correlation ID
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)  # Rate limiting
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check with dependency status.
    Returns status of: database, redis, rabbitmq, oss
    """
    from sqlalchemy import text
    import aio_pika
    
    health = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "dependencies": {}
    }
    
    # Database check
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health["dependencies"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["dependencies"]["database"] = {"status": "unhealthy", "error": str(e)[:100]}
        health["status"] = "degraded"
    
    # RabbitMQ check
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL, timeout=5)
        await connection.close()
        health["dependencies"]["rabbitmq"] = {"status": "healthy"}
    except Exception as e:
        health["dependencies"]["rabbitmq"] = {"status": "unhealthy", "error": str(e)[:100]}
        health["status"] = "degraded"
    
    # OSS check (just verify credentials are configured)
    if settings.OSS_ACCESS_KEY_ID and settings.OSS_BUCKET_NAME:
        health["dependencies"]["oss"] = {"status": "configured"}
    else:
        health["dependencies"]["oss"] = {"status": "not_configured"}
    
    return health


# Import and include routers
from src.adapters.controllers.student_controller import router as student_router
from src.adapters.controllers.test_controller import router as test_router
from src.adapters.controllers.upload_controller import router as upload_router
from src.adapters.controllers.teacher_auth_controller import router as teacher_auth_router
from src.adapters.controllers.report_controller import router as report_router
from src.adapters.controllers.question_controller import router as question_router

app.include_router(teacher_auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(student_router, prefix="/api/v1/students", tags=["Students"])
app.include_router(test_router, prefix="/api/v1/tests", tags=["Tests"])
app.include_router(upload_router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(report_router, prefix="/api/v1", tags=["Reports"])
app.include_router(question_router, prefix="/api/v1/questions", tags=["Questions"])

from src.adapters.controllers.admin_controller import router as admin_router
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])

from src.adapters.controllers.system_controller import router as system_router
app.include_router(system_router, prefix="/api/v1/system", tags=["System"])
