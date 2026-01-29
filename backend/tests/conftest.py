"""Pytest configuration and fixtures for tests.

Provides database fixtures and test utilities.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any, cast

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
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = str(
    settings.DATABASE_URL
)  # .rsplit("/", 1)[0] + "/backcast_evs_test"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> Generator[None, None, None]:
    """Apply alembic migrations to the test database."""
    # Override settings to point to test DB
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = cast(Any, TEST_DATABASE_URL)
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    # Ensure ASYNC_DATABASE_URI is recomputed or patches env.py's source
    # But env.py imports settings. If settings is already imported, we need to ensure the property reflects the change.
    # If ASYNC_DATABASE_URI is a property, it should work. If it's a field, it won't.

    # Ensure clean slate - Nuclear option via subprocess to avoid loop/driver issues
    import subprocess
    import sys

    wipe_script = os.path.join(os.path.dirname(__file__), "wipe_db.py")

    # Get path to alembic.ini (parent directory of tests/)
    tests_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(tests_dir)
    alembic_ini = os.path.join(project_root, "alembic.ini")
    alembic_cfg = Config(alembic_ini)

    # Set script_location to absolute path
    alembic_cfg.set_main_option(
        "script_location", os.path.join(project_root, "alembic")
    )

    # Use .venv Python explicitly to ensure dependencies are available
    # When running via uv run, sys.executable may not have access to project packages
    venv_python = os.path.join(project_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        # Fallback to sys.executable if .venv doesn't exist
        venv_python = sys.executable

    env = os.environ.copy()
    env["WIPE_DATABASE_URL"] = TEST_DATABASE_URL

    try:
        subprocess.run(
            [venv_python, wipe_script],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"DB Wipe Failed: {e.stdout} {e.stderr}")
        # Don't raise - try to continue with migrations

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    # Verify critical tables were created
    # This ensures migrations executed successfully before running tests
    from sqlalchemy.ext.asyncio import create_async_engine

    async def verify_tables():
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        try:
            async with engine.connect() as conn:
                # List of critical tables that must exist after migrations
                required_tables = [
                    "users",
                    "departments",
                    "projects",
                    "wbes",
                    "cost_element_types",
                    "cost_elements",
                    "cost_registrations",
                    "progress_entries",  # Critical: Added in this iteration
                    "schedule_baselines",
                    "branches",
                    "change_orders",
                    "change_order_audit_log",
                    "forecasts",
                ]

                for table_name in required_tables:
                    result = await conn.execute(
                        text(
                            f"SELECT EXISTS (SELECT FROM information_schema.tables "
                            f"WHERE table_schema = 'public' AND table_name = '{table_name}')"
                        )
                    )
                    exists = result.scalar_one()
                    if not exists:
                        raise RuntimeError(
                            f"Critical table '{table_name}' not found after migrations! "
                            f"Migration may have failed silently."
                        )
        finally:
            await engine.dispose()

    # Run the async verification in the sync fixture
    asyncio.run(verify_tables())

    yield

    # Clean up (downgrade)
    # try:
    #     command.downgrade(alembic_cfg, "base")
    # except Exception:
    #     pass
    # finally:
    settings.DATABASE_URL = original_url


@pytest_asyncio.fixture(scope="function")
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
                        "TRUNCATE TABLE cost_elements, cost_element_types, wbes, projects, departments, users, cost_registrations, progress_entries, schedule_baselines, branches, change_orders, change_order_audit_log, forecasts RESTART IDENTITY CASCADE"
                    )
                )
                await session.commit()
            except Exception as e:
                # Tables might not exist yet (first test run), fail fast
                print(f"Error truncating tables: {e}")
                await session.rollback()
                raise RuntimeError(
                    f"Database tables do not exist. Migration may have failed. "
                    f"Error: {e}"
                )

            yield session

        # Rollback the transaction after the test completes
        await trans.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async client for tests."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides = {}
