"""
Database Configuration (Async PostgreSQL)
Uses SQLAlchemy 2.0 async engine with asyncpg driver.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from src.infrastructure.config import get_settings

settings = get_settings()

# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    # 连接池超时设置（秒）
    pool_pre_ping=True,   # 连接前先 ping，自动重连断开的连接
    pool_recycle=3600,    # 连接回收时间（1小时），避免长时间连接超时
    pool_timeout=30,      # 获取连接超时 30 秒（避免网关 60s 超时）
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Alias for backward compatibility
async_session_factory = AsyncSessionLocal

# Base class for ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database session (with auto-commit).
    
    Usage in FastAPI for write operations:
        @router.post("/users")
        async def create_user(db: AsyncSession = Depends(get_db)):
            ...
    
    Note: For read-only operations, use get_db_readonly() for better performance.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for read-only database session (no auto-commit).
    
    Performance optimization: Avoids unnecessary commit on GET requests.
    Use this for pure read operations (SELECT queries).
    
    Usage in FastAPI:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db_readonly)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # No commit for read-only operations
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
