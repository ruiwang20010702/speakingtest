"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.infrastructure.config import get_settings
from src.infrastructure.database import engine, Base
from src.infrastructure.logging import setup_logging, RequestLoggingMiddleware

settings = get_settings()

# Initialize logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    - Startup: Initialize database tables
    - Shutdown: Close connections
    """
    # Startup
    logger.info("Application starting up...")
    async with engine.begin() as conn:
        # Create tables if they don't exist (dev only; use Alembic in prod)
        # await conn.run_sync(Base.metadata.create_all)
        pass

    yield

    # Shutdown
    logger.info("Application shutting down...")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="口语测评系统 API",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestLoggingMiddleware)  # Request logging with correlation ID
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


# Import and include routers
from src.adapters.controllers.student_controller import router as student_router
from src.adapters.controllers.test_controller import router as test_router
# from src.adapters.controllers.report_controller import router as report_router

app.include_router(student_router, prefix="/api/v1/students", tags=["Students"])
app.include_router(test_router, prefix="/api/v1/tests", tags=["Tests"])
# app.include_router(report_router, prefix="/api/v1/reports", tags=["Reports"])
