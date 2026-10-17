"""Pytest configuration and shared fixtures for backend tests."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch, MagicMock

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.models import Base, Translation, UsageRecord


# ─── Environment ─────────────────────────────────────────────────────────────
# Set environment variables before importing app modules so Settings picks them up.
import os

TEST_JWT_SECRET = "test-jwt-secret-for-rosetta-unit-tests"
TEST_USER_ID = str(uuid.uuid4())

_test_settings = {
    "ENVIRONMENT": "testing",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJvbGUiOiJhbm9uIn0.fake_signature",
    "SUPABASE_SERVICE_ROLE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJvbGUiOiJzZXJ2aWNlX3JvbGUifQ.fake_signature",
    "SUPABASE_JWT_SECRET": TEST_JWT_SECRET,
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "GEMINI_API_KEY": "test-gemini-key",
    "GEMINI_MODEL": "gemini-test",
    "CORS_ORIGINS": "http://localhost:5173",
    "RATE_LIMIT_PER_MINUTE": "100",
    "MONTHLY_TRANSLATION_LIMIT": "100",
    "MAX_SOURCE_CODE_LENGTH": "10000",
    "LOG_LEVEL": "WARNING",
}

for _k, _v in _test_settings.items():
    os.environ.setdefault(_k, _v)



@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _make_test_token(
    user_id: str = TEST_USER_ID,
    expired: bool = False,
) -> str:
    """Create a valid or expired JWT for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iat": now - timedelta(minutes=5),
        "exp": now + (timedelta(hours=-1) if expired else timedelta(hours=1)),
        "role": "authenticated",
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return valid Authorization headers."""
    token = _make_test_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_auth_headers() -> dict[str, str]:
    """Return expired Authorization headers."""
    token = _make_test_token(expired=True)
    return {"Authorization": f"Bearer {token}"}


# ─── Database ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory SQLite async engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession) -> AsyncSession:
    """Seed the test database with a sample translation."""
    translation = Translation(
        id=uuid.uuid4(),
        user_id=uuid.UUID(TEST_USER_ID),
        source_language="python",
        target_language="typescript",
        source_code='print("hello")',
        translated_code='console.log("hello");',
        explanation=None,
        detected_language=None,
        model_used="gemini-test",
        tokens_used=50,
    )
    db_session.add(translation)

    # Add a usage record for the current month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage = UsageRecord(
        user_id=uuid.UUID(TEST_USER_ID),
        month=month_start,
        translation_count=1,
        tokens_consumed=50,
    )
    db_session.add(usage)
    await db_session.commit()
    return db_session


# ─── Mock Gemini ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_gemini():
    """Mock the Gemini client for translation/detection tests."""
    mock = AsyncMock()
    mock.translate_code = AsyncMock(return_value={
        "translated_code": 'console.log("hello");',
        "explanation": None,
        "model_used": "gemini-test",
        "tokens_used": 50,
    })
    mock.detect_language = AsyncMock(return_value="python")
    return mock


# ─── HTTP Client ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, mock_gemini) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client wired to the test app with overridden deps."""
    # Patch settings at the module level before importing the app
    with patch.dict("os.environ", _test_settings):
        # Re-import to pick up test settings
        from app.core.config import Settings

        # Create a test settings instance
        test_settings = Settings(**{k: v for k, v in _test_settings.items()})

        with patch("app.core.config.settings", test_settings):
            # Patch the supabase clients to avoid real connections
            mock_supabase = MagicMock()
            with patch("app.api.v1.routes.auth.supabase", mock_supabase), \
                 patch("app.api.v1.routes.account.supabase_admin", mock_supabase), \
                 patch("app.services.translation_service.gemini_client", mock_gemini):

                from app.main import create_app
                from app.core.database import get_db_session

                app = create_app()

                async def override_get_db():
                    yield db_session

                app.dependency_overrides[get_db_session] = override_get_db

                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as ac:
                    yield ac

                app.dependency_overrides.clear()
