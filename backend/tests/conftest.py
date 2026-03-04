"""pytest configuration and shared fixtures.

Database strategy
-----------------
Tests use the DATABASE_URL from environment (identical to the CI Postgres
service declared in .github/workflows/backend.yml).  The session-scoped
``engine`` fixture creates all tables before the suite runs and drops them
after — providing a clean slate without spinning up a separate test DB.

Each test gets its own session that is rolled back at teardown, so tests
are fully isolated and leave no persistent state.

Async
-----
All fixtures and tests are async (pytest-asyncio asyncio_mode = "auto").
The ASGI app is exercised through httpx.AsyncClient with ASGITransport,
which exercises the full middleware stack without a live TCP connection.
"""

import os

# Set required env vars before any app module is imported so that
# pydantic-settings can construct Settings() without a .env file.
# These values are safe for testing only — never use them in production.
os.environ.setdefault(
    "ENCRYPTION_KEY",
    # Valid Fernet key (base64-encoded 32 bytes of zeroes) for test isolation.
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
)

from collections.abc import AsyncGenerator

import pytest
from app.config import settings
from app.dependencies import get_db
from app.main import app
from app.models.base import Base
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Session-scoped engine: create all tables once, drop after suite."""
    test_engine = create_async_engine(settings.database_url, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture()
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session; rolled back after each test."""
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired to the FastAPI app with a test DB session.

    Use this fixture for tests that exercise DB-dependent endpoints (e.g.
    /ready).  Requires DATABASE_URL to be reachable (available in CI).
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with no DB dependency override.

    Use this fixture for endpoints that do not touch the database (e.g.
    /live).  Safe to run without a PostgreSQL instance.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
