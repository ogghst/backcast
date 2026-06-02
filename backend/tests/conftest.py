"""Test suite configuration and shared fixtures.

Uses the running dev database (PostgreSQL) with real async sessions.
RBAC is bypassed via dependency override + monkey-patching to allow all
permission checks.  Test data is created via factory functions in factories.py.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    ProjectRoleChecker,
    RoleChecker,
    UserIdentity,
    get_current_user,
)
from app.core.security import create_access_token
from app.db.session import engine, get_db
from app.main import app

# ---------------------------------------------------------------------------
# Bypass RBAC: override get_current_user and monkey-patch RoleChecker.__call__
# ---------------------------------------------------------------------------

# Use a fixed test user ID that matches an existing seeded user (admin).
TEST_USER_ID = UUID("e03556f3-4385-5d68-a685-af307fc8af5c")  # admin@backcast.org


async def _override_get_current_user() -> UserIdentity:
    """Return a fixed test user identity, bypassing JWT validation."""
    return UserIdentity(user_id=TEST_USER_ID)


async def _bypass_role_checker(
    self: RoleChecker,
    current_user: Annotated[UserIdentity, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserIdentity:
    """Bypass all RoleChecker permission checks."""
    return current_user


async def _bypass_project_role_checker(
    self: ProjectRoleChecker,
    project_id: UUID,
    current_user: Annotated[UserIdentity, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserIdentity:
    """Bypass all ProjectRoleChecker permission checks."""
    return current_user


# Override get_current_user so JWT validation is skipped.
app.dependency_overrides[get_current_user] = _override_get_current_user

# Monkey-patch __call__ on both checker classes so that ANY instance
# (including Depends(RoleChecker(required_permission="..."))) always allows access.
RoleChecker.__call__ = _bypass_role_checker  # type: ignore[assignment]
ProjectRoleChecker.__call__ = _bypass_project_role_checker  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_pool() -> AsyncGenerator[None, None]:
    """Dispose the global engine pool before each test.

    pytest-asyncio creates a new event loop per test function.  The
    asyncpg connections in the global engine pool are bound to the
    previous loop and become stale, causing "Future attached to a
    different loop" errors.  Disposing the pool before each test forces
    fresh connections on the new loop.
    """
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests.

    Uses a real database session with a COMMIT at the end so that test
    data is visible to subsequent assertions.  Cleanup is handled by
    individual tests or by the session closing.
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session
        await session.commit()
        await session.close()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient wired to the FastAPI app.

    The client carries a valid JWT Authorization header for the test user.
    """
    token = create_access_token(subject=str(TEST_USER_ID))
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver/api/v1",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c


@pytest_asyncio.fixture
def actor_id() -> UUID:
    """Return the test user ID (actor for create/update operations)."""
    return TEST_USER_ID


@pytest_asyncio.fixture
def now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(tz=UTC)
