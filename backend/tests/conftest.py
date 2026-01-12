"""
Test Configuration and Fixtures

Provides shared fixtures for testing FastAPI endpoints.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# ============================================
# Event Loop Configuration
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============================================
# Database Fixtures
# ============================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create test database engine."""
    from src.adapters.repositories.models import Base
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client with test database."""
    from src.infrastructure.main import app
    from src.infrastructure.database import get_db
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ============================================
# User Fixtures
# ============================================

@pytest.fixture
async def teacher_user(test_db: AsyncSession):
    """Create a teacher user for testing."""
    from src.adapters.repositories.models import UserModel
    
    user = UserModel(
        email="teacher@51talk.com",
        role="teacher",
        status=1
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db: AsyncSession):
    """Create an admin user for testing."""
    from src.adapters.repositories.models import UserModel
    
    user = UserModel(
        email="admin@51talk.com",
        role="admin",
        status=1
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def student_user(test_db: AsyncSession):
    """Create a student user for testing."""
    from src.adapters.repositories.models import UserModel
    
    user = UserModel(
        role="student",
        status=1
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def student_profile(test_db: AsyncSession, teacher_user, student_user):
    """Create a student profile for testing."""
    from src.adapters.repositories.models import StudentProfileModel
    
    profile = StudentProfileModel(
        user_id=student_user.id,
        student_name="Test Student",
        external_source="test",
        external_user_id="12345",
        teacher_id=teacher_user.id,
        ss_email_addr=teacher_user.email
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)
    return profile


# ============================================
# Test Data Fixtures
# ============================================

@pytest.fixture
def sample_csv_content() -> str:
    """Sample CSV content for import testing."""
    return """student_id,student_name,cur_age,cur_grade
10001,张小明,10,四年级
10002,李小红,9,三年级"""


@pytest.fixture
def invalid_csv_content() -> str:
    """Invalid CSV content missing required columns."""
    return """name,age
张小明,10"""


# ============================================
# Auth Mock Fixtures
# ============================================

@pytest.fixture
def auth_teacher(teacher_user):
    """Override auth dependencies for teacher."""
    from src.infrastructure.main import app
    from src.infrastructure.auth import get_current_user_id, get_current_user_role
    
    app.dependency_overrides[get_current_user_id] = lambda: teacher_user.id
    app.dependency_overrides[get_current_user_role] = lambda: "teacher"
    yield
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_current_user_role, None)


@pytest.fixture
def auth_admin(admin_user):
    """Override auth dependencies for admin."""
    from src.infrastructure.main import app
    from src.infrastructure.auth import get_current_user_id, get_current_user_role, require_admin
    
    app.dependency_overrides[get_current_user_id] = lambda: admin_user.id
    app.dependency_overrides[get_current_user_role] = lambda: "admin"
    app.dependency_overrides[require_admin] = lambda: admin_user.id
    yield
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_current_user_role, None)
    app.dependency_overrides.pop(require_admin, None)

