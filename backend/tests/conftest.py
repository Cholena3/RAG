import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.middleware.auth import hash_password, create_access_token
from app.models.user import User


# ---------- DB fixtures ----------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------- App + client ----------

@pytest_asyncio.fixture
async def client():
    # Patch rate limiter redis and celery before importing app
    with patch("app.middleware.rate_limit.redis.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.incr = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[1, True])
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis_cls.return_value = mock_redis

        from app.main import app
        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()


# ---------- User helpers ----------

@pytest_asyncio.fixture
async def test_user():
    async with TestSession() as db:
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password=hash_password("testpass123"),
            full_name="Test User",
            role="user",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user():
    async with TestSession() as db:
        user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password=hash_password("adminpass123"),
            full_name="Admin User",
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest.fixture
def user_token(test_user):
    return create_access_token(str(test_user.id))


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(str(admin_user.id))


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
