"""Pytest configuration and fixtures for tests.

Provides database fixtures and test utilities.
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import settings
from app.main import app

# Test database URL
# Replace database name with backend_evs_test
# We assume the default URL points to the main DB
TEST_DATABASE_URL = str(settings.DATABASE_URL).rsplit("/", 1)[0] + "/backcast_evs_test"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """Apply alembic migrations to the test database."""
    # Override settings to point to test DB
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = TEST_DATABASE_URL
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    alembic_cfg = Config("alembic.ini")

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    yield

    # Clean up (downgrade)
    try:
        command.downgrade(alembic_cfg, "base")
    except Exception:
        pass
    finally:
        settings.DATABASE_URL = original_url


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False, poolclass=NullPool, pool_pre_ping=True
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests with transaction rollback."""
    async with db_engine.connect() as conn:
        trans = await conn.begin()

        # Bind session to the connection with the active transaction
        async_session_maker = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            # We must ensure that the session doesn't close the connection
        )

        async with async_session_maker() as session:
            # Clean up all test data before the test (if tables exist)
            try:
                await session.execute(
                    text(
                        "TRUNCATE TABLE wbes, projects, departments, users RESTART IDENTITY CASCADE"
                    )
                )
                await session.commit()
            except Exception:
                # Tables might not exist yet (first test run), that's okay
                await session.rollback()

            yield session

        # Rollback the transaction after the test completes
        await trans.rollback()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async client for tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
