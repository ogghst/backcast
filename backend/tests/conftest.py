"""Pytest configuration and fixtures for tests.

Provides database fixtures, mock user fixtures, and entity creation helpers.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

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
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.db.session import get_db
from app.main import app
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.cost_element import CostElementCreate
from app.models.schemas.cost_element_type import CostElementTypeCreate
from app.models.schemas.department import DepartmentCreate
from app.models.schemas.project import ProjectCreate
from app.models.schemas.wbe import WBECreate
from app.services.cost_element_service import CostElementService
from app.services.cost_element_type_service import CostElementTypeService
from app.services.department import DepartmentService
from app.services.project import ProjectService
from app.services.wbe import WBEService

_orig_url = str(settings.DATABASE_URL)
TEST_DATABASE_URL = _orig_url if _orig_url.endswith("_test") else _orig_url + "_test"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture(scope="session")
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
    # Set the database URLs for wipe script
    env["WIPE_DATABASE_URL"] = TEST_DATABASE_URL
    env["ORIGINAL_DATABASE_URL"] = str(original_url)
    # Also set DATABASE_URL for wipe script fallback
    env["DATABASE_URL"] = TEST_DATABASE_URL

    try:
        result = subprocess.run(
            [venv_python, wipe_script],
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,  # Add timeout to prevent hanging
        )
        print(f"DB Wipe output: {result.stdout}")
    except subprocess.TimeoutExpired as e:
        print("DB Wipe timed out after 60 seconds")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        # Don't raise - try to continue with migrations
    except subprocess.CalledProcessError as e:
        print(f"DB Wipe Failed: {e.stdout} {e.stderr}")
        # Don't raise - try to continue with migrations

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    # Verify critical tables were created
    # This ensures migrations executed successfully before running tests
    from sqlalchemy.ext.asyncio import create_async_engine

    async def verify_tables() -> None:
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
                    "ai_providers",
                    "ai_provider_configs",
                    "ai_models",
                    "ai_assistant_configs",
                    "ai_conversation_sessions",
                    "ai_conversation_messages",
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
async def db_engine(apply_migrations) -> AsyncGenerator[AsyncEngine, None]:
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
                # Check which tables exist using information_schema
                result = await session.execute(
                    text("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_type = 'BASE TABLE'
                    """)
                )
                existing_tables = {row[0] for row in result}

                # List of tables to truncate in dependency order (child tables first)
                tables_to_truncate = [
                    "ai_conversation_messages",
                    "ai_conversation_sessions",
                    "ai_assistant_configs",
                    "ai_models",
                    "ai_provider_configs",
                    "ai_providers",
                    "cost_registrations",
                    "progress_entries",
                    "cost_elements",
                    "change_order_audit_log",
                    "change_orders",
                    "branches",
                    "forecasts",
                    "wbes",
                    "cost_element_types",
                    "projects",
                    "departments",
                    "users",
                    "schedule_baselines",  # May not exist in newer migrations
                ]

                # Build TRUNCATE statement for tables that exist
                truncate_parts = []
                for table in tables_to_truncate:
                    if table in existing_tables:
                        truncate_parts.append(f'"{table}"')

                if truncate_parts:
                    truncate_sql = f"TRUNCATE TABLE {', '.join(truncate_parts)} RESTART IDENTITY CASCADE"
                    await session.execute(text(truncate_sql))
                    await session.commit()
            except Exception as e:
                # Tables might not exist yet (first test run), fail fast
                print(f"Error truncating tables: {e}")
                await session.rollback()
                raise RuntimeError(
                    f"Database tables do not exist. Migration may have failed. "
                    f"Error: {e}"
                ) from e

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


# =============================================================================
# Mock User Fixtures
# =============================================================================


class MockRBACService(RBACServiceABC):
    """Mock RBAC service that allows everything for testing."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        # Return all possible permissions for testing
        return [
            "user-read",
            "user-create",
            "user-update",
            "user-delete",
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "wbe-read",
            "wbe-create",
            "wbe-update",
            "wbe-delete",
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-delete",
            "department-read",
            "department-create",
            "department-update",
            "department-delete",
            "cost-element-type-read",
            "cost-element-type-create",
            "cost-element-type-update",
            "cost-element-type-delete",
        ]

    # Project-level RBAC methods (mocked - allow all)
    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        return None


def _create_mock_user(
    user_id: UUID | None = None,
    email: str = "test@example.com",
    is_active: bool = True,
    role: str = "viewer",
    full_name: str = "Test User",
    hashed_password: str = "hash",
) -> User:
    """Helper function to create mock user instances.

    Args:
        user_id: Optional UUID for the user. Defaults to random UUID.
        email: User email address.
        is_active: Whether the user is active.
        role: User role (admin, project_manager, viewer).
        full_name: User's full name.
        hashed_password: Hashed password.

    Returns:
        A User instance with the provided attributes.
    """
    return User(
        id=uuid4(),
        user_id=user_id or uuid4(),
        email=email,
        is_active=is_active,
        role=role,
        full_name=full_name,
        hashed_password=hashed_password,
        created_by=uuid4(),
    )


@pytest.fixture
def mock_admin_user() -> User:
    """Mock admin user for authentication testing.

    Returns:
        User instance with admin role.
    """
    return _create_mock_user(
        email="admin@example.com",
        role="admin",
        full_name="Admin User",
    )


@pytest.fixture
def mock_project_manager_user() -> User:
    """Mock project manager user for authentication testing.

    Returns:
        User instance with project_manager role.
    """
    return _create_mock_user(
        email="pm@example.com",
        role="project_manager",
        full_name="Project Manager User",
    )


@pytest.fixture
def mock_viewer_user() -> User:
    """Mock viewer user for authentication testing.

    Returns:
        User instance with viewer role.
    """
    return _create_mock_user(
        email="viewer@example.com",
        role="viewer",
        full_name="Viewer User",
    )


@pytest.fixture
def mock_rbac_service() -> MockRBACService:
    """Mock RBAC service that grants all permissions.

    Returns:
        MockRBACService instance.
    """
    return MockRBACService()


@pytest.fixture
def mock_rbac_service_no_ai() -> MockRBACService:
    """Mock RBAC service that denies AI chat permissions.

    Returns:
        MockRBACService instance without ai-chat permission.
    """
    class NoAIRBACService(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            # Deny ai-chat permission specifically
            if required_permission == "ai-chat":
                return False
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            # Return all permissions except ai-chat
            return [
                "user-read",
                "user-create",
                "user-update",
                "user-delete",
                "project-read",
                "project-create",
                "project-update",
                "project-delete",
                "wbe-read",
                "wbe-create",
                "wbe-update",
                "wbe-delete",
                "cost-element-read",
                "cost-element-create",
                "cost-element-update",
                "cost-element-delete",
                "department-read",
                "department-create",
                "department-update",
                "department-delete",
                "cost-element-type-read",
                "cost-element-type-create",
                "cost-element-type-update",
                "cost-element-type-delete",
            ]

        # Project-level RBAC methods (mocked - allow all)
        async def has_project_access(
            self,
            user_id: UUID,
            user_role: str,
            project_id: UUID,
            required_permission: str,
        ) -> bool:
            return True

        async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
            return []

        async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
            return None

    return NoAIRBACService()


# =============================================================================
# Auth Override Fixture
# =============================================================================


@pytest.fixture
def override_auth(
    mock_admin_user: User,
    mock_rbac_service: MockRBACService,
) -> Generator[None, None, None]:
    """Override authentication and RBAC dependencies for API tests.

    This fixture automatically overrides the authentication and RBAC
    dependencies for all tests in the module it's used in.

    Usage:
        @pytest.fixture(autouse=True)
        def override_auth_dependencies(override_auth):
            pass

    Or use autouse directly in the test file:
        @pytest.fixture(autouse=True)
        def override_auth(override_auth: None):
            ...
    """
    from app.api.dependencies.auth import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user
    app.dependency_overrides[get_rbac_service] = lambda: mock_rbac_service
    yield
    app.dependency_overrides = {}


# =============================================================================
# Entity Creation Helper Fixtures (Database-based)
# =============================================================================


@pytest_asyncio.fixture
async def test_department(db_session: AsyncSession) -> Department:
    """Create a test department in the database.

    Returns:
        Department instance with code 'ENG' and name 'Engineering'.
    """
    service = DepartmentService(db_session)
    dept_in = DepartmentCreate(
        name="Engineering",
        code="ENG",
        is_active=True,
    )
    return await service.create_department(dept_in, actor_id=uuid4())


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession) -> Project:
    """Create a test project in the database.

    Returns:
        Project instance with code 'TEST-PROJ' and name 'Test Project'.
    """
    service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Test Project",
        code="TEST-PROJ",
        budget=Decimal("100000.00"),
        status="Active",
    )
    return await service.create_project(project_in, actor_id=uuid4())


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user in the database.

    Returns:
        User instance with admin role.
    """
    from app.services.user import UserService

    service = UserService(db_session)
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="admin@test.com",
        full_name="Admin User",
        role="admin",
        is_active=True,
        hashed_password="hash",
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a regular test user in the database.

    Returns:
        User instance with viewer role.
    """
    from app.services.user import UserService

    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="user@test.com",
        full_name="Test User",
        role="viewer",
        is_active=True,
        hashed_password="hash",
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_wbe(db_session: AsyncSession, test_project: Project) -> WBE:
    """Create a test WBE in the database.

    Args:
        db_session: Database session.
        test_project: Parent project fixture.

    Returns:
        WBE instance linked to the test project.
    """
    service = WBEService(db_session)
    wbe_in = WBECreate(
        project_id=test_project.project_id,
        code="1.0",
        name="Test WBE",
        level=1,
    )
    return await service.create_wbe(wbe_in, actor_id=uuid4())


@pytest_asyncio.fixture
async def test_cost_element_type(
    db_session: AsyncSession,
    test_department: Department,
) -> CostElementType:
    """Create a test cost element type in the database.

    Args:
        db_session: Database session.
        test_department: Parent department fixture.

    Returns:
        CostElementType instance linked to the test department.
    """
    service = CostElementTypeService(db_session)
    type_in = CostElementTypeCreate(
        code="TEST-TYPE",
        name="Test Cost Element Type",
        description="A test cost element type",
        department_id=test_department.department_id,
    )
    return await service.create(type_in, actor_id=uuid4())


@pytest_asyncio.fixture
async def test_cost_element(
    db_session: AsyncSession,
    test_wbe: WBE,
    test_cost_element_type: CostElementType,
) -> CostElement:
    """Create a test cost element in the database.

    Args:
        db_session: Database session.
        test_wbe: Parent WBE fixture.
        test_cost_element_type: Cost element type fixture.

    Returns:
        CostElement instance linked to the test WBE and type.
    """
    service = CostElementService(db_session)
    element_in = CostElementCreate(
        code="TEST-CE",
        name="Test Cost Element",
        wbe_id=test_wbe.wbe_id,
        cost_element_type_id=test_cost_element_type.cost_element_type_id,
        budget_amount=Decimal("10000.00"),
        branch="main",
    )
    return await service.create_cost_element(element_in, actor_id=uuid4())


# =============================================================================
# Entity Hierarchy Fixture (Complete dependency chain)
# =============================================================================


@pytest_asyncio.fixture
async def test_entity_hierarchy(
    db_session: AsyncSession,
) -> dict[str, Any]:
    """Create a complete entity hierarchy for testing.

    Creates:
    1. Department
    2. Cost Element Type (linked to Department)
    3. Project
    4. WBE (linked to Project)
    5. Cost Element (linked to WBE and Cost Element Type)

    Returns:
        Dictionary containing all created entities with keys:
        - 'department': Department instance
        - 'cost_element_type': CostElementType instance
        - 'project': Project instance
        - 'wbe': WBE instance
        - 'cost_element': CostElement instance
    """
    # Create Department
    dept_service = DepartmentService(db_session)
    dept_in = DepartmentCreate(
        name="Mechanical",
        code="MECH",
        is_active=True,
        description="Mechanical Engineering Department",
    )
    department = await dept_service.create_department(dept_in, actor_id=uuid4())

    # Create Cost Element Type
    type_service = CostElementTypeService(db_session)
    type_in = CostElementTypeCreate(
        code="MECH-INST",
        name="Mechanical Installation",
        description="Mechanical installation work",
        department_id=department.department_id,
    )
    cost_element_type = await type_service.create(type_in, actor_id=uuid4())

    # Create Project
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Project Alpha",
        code="PROJ-A",
        budget=Decimal("1000000.00"),
        status="Active",
        description="Test project for automated testing",
    )
    project = await project_service.create_project(project_in, actor_id=uuid4())

    # Create WBE
    wbe_service = WBEService(db_session)
    wbe_in = WBECreate(
        project_id=project.project_id,
        code="1.1",
        name="Site Preparation",
        level=1,
        description="Site preparation phase",
    )
    wbe = await wbe_service.create_wbe(wbe_in, actor_id=uuid4())

    # Create Cost Element
    element_service = CostElementService(db_session)
    element_in = CostElementCreate(
        code="CE-001",
        name="Mechanical Work Phase 1",
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        budget_amount=Decimal("50000.00"),
        description="Phase 1 mechanical installation",
        branch="main",
    )
    cost_element = await element_service.create_cost_element(
        element_in, actor_id=uuid4()
    )

    return {
        "department": department,
        "cost_element_type": cost_element_type,
        "project": project,
        "wbe": wbe,
        "cost_element": cost_element,
    }


# =============================================================================
# API Entity Creation Helpers (HTTP-based)
# =============================================================================


@pytest_asyncio.fixture
async def api_test_department(client: AsyncClient) -> dict[str, Any]:
    """Create a test department via API.

    Returns:
        Dictionary containing the department response data.
    """
    response = await client.post(
        "/api/v1/departments",
        json={
            "code": f"API-DEPT-{uuid4().hex[:6].upper()}",
            "name": "API Test Department",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@pytest_asyncio.fixture
async def api_test_project(client: AsyncClient) -> dict[str, Any]:
    """Create a test project via API.

    Returns:
        Dictionary containing the project response data.
    """
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "API Test Project",
            "code": f"API-PROJ-{uuid4().hex[:6].upper()}",
            "budget": 100000,
            "status": "Active",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@pytest_asyncio.fixture
async def api_test_wbe(
    client: AsyncClient,
    api_test_project: dict[str, Any],
) -> dict[str, Any]:
    """Create a test WBE via API.

    Args:
        client: AsyncClient fixture.
        api_test_project: Parent project fixture.

    Returns:
        Dictionary containing the WBE response data.
    """
    response = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": api_test_project["project_id"],
            "code": f"API-WBE-{uuid4().hex[:6].upper()}",
            "name": "API Test WBE",
            "level": 1,
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@pytest_asyncio.fixture
async def api_test_cost_element_type(
    client: AsyncClient,
    api_test_department: dict[str, Any],
) -> dict[str, Any]:
    """Create a test cost element type via API.

    Args:
        client: AsyncClient fixture.
        api_test_department: Parent department fixture.

    Returns:
        Dictionary containing the cost element type response data.
    """
    response = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": f"API-TYPE-{uuid4().hex[:6].upper()}",
            "name": "API Test Cost Element Type",
            "department_id": api_test_department["department_id"],
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@pytest_asyncio.fixture
async def api_test_cost_element(
    client: AsyncClient,
    api_test_wbe: dict[str, Any],
    api_test_cost_element_type: dict[str, Any],
) -> dict[str, Any]:
    """Create a test cost element via API.

    Args:
        client: AsyncClient fixture.
        api_test_wbe: Parent WBE fixture.
        api_test_cost_element_type: Cost element type fixture.

    Returns:
        Dictionary containing the cost element response data.
    """
    response = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"API-CE-{uuid4().hex[:6].upper()}",
            "name": "API Test Cost Element",
            "wbe_id": api_test_wbe["wbe_id"],
            "cost_element_type_id": api_test_cost_element_type["cost_element_type_id"],
            "budget_amount": 10000.00,
            "branch": "main",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@pytest_asyncio.fixture
async def api_test_entity_hierarchy(client: AsyncClient) -> dict[str, dict[str, Any]]:
    """Create a complete entity hierarchy via API for testing.

    Creates all entities in order via HTTP endpoints:
    1. Department
    2. Cost Element Type (linked to Department)
    3. Project
    4. WBE (linked to Project)
    5. Cost Element (linked to WBE and Cost Element Type)

    Returns:
        Dictionary containing all created entity responses with keys:
        - 'department': Department response dict
        - 'cost_element_type': CostElementType response dict
        - 'project': Project response dict
        - 'wbe': WBE response dict
        - 'cost_element': CostElement response dict
    """
    # Create Department
    dept_response = await client.post(
        "/api/v1/departments",
        json={
            "code": f"HIER-DEPT-{uuid4().hex[:6].upper()}",
            "name": "Hierarchy Department",
            "is_active": True,
        },
    )
    assert dept_response.status_code == 201
    department = dept_response.json()

    # Create Cost Element Type
    type_response = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": f"HIER-TYPE-{uuid4().hex[:6].upper()}",
            "name": "Hierarchy Cost Element Type",
            "department_id": department["department_id"],
        },
    )
    assert type_response.status_code == 201
    cost_element_type = type_response.json()

    # Create Project
    project_response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Hierarchy Project",
            "code": f"HIER-PROJ-{uuid4().hex[:6].upper()}",
            "budget": 1000000,
            "status": "Active",
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()

    # Create WBE
    wbe_response = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": project["project_id"],
            "code": f"HIER-WBE-{uuid4().hex[:6].upper()}",
            "name": "Hierarchy WBE",
            "level": 1,
        },
    )
    assert wbe_response.status_code == 201
    wbe = wbe_response.json()

    # Create Cost Element
    element_response = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"HIER-CE-{uuid4().hex[:6].upper()}",
            "name": "Hierarchy Cost Element",
            "wbe_id": wbe["wbe_id"],
            "cost_element_type_id": cost_element_type["cost_element_type_id"],
            "budget_amount": 50000.00,
            "branch": "main",
        },
    )
    assert element_response.status_code == 201
    cost_element = element_response.json()

    return {
        "department": department,
        "cost_element_type": cost_element_type,
        "project": project,
        "wbe": wbe,
        "cost_element": cost_element,
    }


# =============================================================================
# AI Configuration Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_ai_provider(db_session: AsyncSession) -> Any:
    """Create a test AI provider in the database.

    Returns:
        AIProvider instance with OpenAI configuration.
    """
    from app.models.domain.ai import AIProvider

    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="OpenAI Test",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()
    await db_session.refresh(provider)
    return provider


@pytest_asyncio.fixture
async def test_ai_model(
    db_session: AsyncSession,
    test_ai_provider: Any,
) -> Any:
    """Create a test AI model in the database.

    Args:
        db_session: Database session.
        test_ai_provider: Parent provider fixture.

    Returns:
        AIModel instance for GPT-4.
    """
    from app.models.domain.ai import AIModel

    model = AIModel(
        id=str(uuid4()),
        provider_id=str(test_ai_provider.id),
        model_id="gpt-4",
        display_name="GPT-4 Test",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def test_ai_assistant(
    db_session: AsyncSession,
    test_ai_model: Any,
) -> Any:
    """Create an active test AI assistant configuration.

    Args:
        db_session: Database session.
        test_ai_model: Parent model fixture.

    Returns:
        AIAssistantConfig instance with test configuration.
    """
    from app.models.domain.ai import AIAssistantConfig

    config = AIAssistantConfig(
        id=str(uuid4()),
        name="Test Assistant",
        description="A test assistant for WebSocket tests",
        model_id=str(test_ai_model.id),
        system_prompt="You are a helpful test assistant.",
        temperature=0.0,
        max_tokens=1000,
        allowed_tools=["list_projects"],
        is_active=True,
    )
    db_session.add(config)
    await db_session.flush()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def inactive_ai_assistant(
    db_session: AsyncSession,
    test_ai_model: Any,
) -> Any:
    """Create an inactive test AI assistant configuration.

    Args:
        db_session: Database session.
        test_ai_model: Parent model fixture.

    Returns:
        AIAssistantConfig instance with is_active=False.
    """
    from app.models.domain.ai import AIAssistantConfig

    config = AIAssistantConfig(
        id=str(uuid4()),
        name="Inactive Assistant",
        description="An inactive test assistant",
        model_id=str(test_ai_model.id),
        system_prompt="You are a helpful test assistant.",
        temperature=0.0,
        max_tokens=1000,
        allowed_tools=["list_projects"],
        is_active=False,  # Inactive
    )
    db_session.add(config)
    await db_session.flush()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def test_ai_provider_with_config(
    db_session: AsyncSession,
    test_ai_provider: Any,
) -> Any:
    """Create a test AI provider with encrypted API key configuration.

    Args:
        db_session: Database session.
        test_ai_provider: Parent provider fixture.

    Returns:
        AIProvider instance with associated config.
    """
    from app.models.domain.ai import AIProviderConfig

    # Add encrypted API key config
    config = AIProviderConfig(
        id=str(uuid4()),
        provider_id=str(test_ai_provider.id),
        key="api_key",
        value="gsk_test_encrypted_api_key_value_that_is_long_enough",  # Mock encrypted value
        is_encrypted=True,
    )
    db_session.add(config)
    await db_session.flush()

    return test_ai_provider
