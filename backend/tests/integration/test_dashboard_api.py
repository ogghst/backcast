"""Integration tests for Dashboard API endpoint."""

from collections.abc import AsyncGenerator
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.db.session import get_db
from app.main import app
from app.models.domain.user import User
from app.models.schemas.project import ProjectCreate
from app.models.schemas.wbe import WBECreate
from app.services.change_order_service import ChangeOrderService
from app.services.project import ProjectService
from app.services.wbe import WBEService

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
)


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
    return mock_admin_user


# Mock RBAC service that allows everything
class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "dashboard-read",
        ]


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with mocked auth."""

    def override_get_current_user():
        return mock_admin_user

    def override_get_current_active_user():
        return mock_admin_user

    def override_get_rbac_service():
        return MockRBACService()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[get_rbac_service] = override_get_rbac_service
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_dashboard_recent_activity_empty(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test dashboard endpoint with no data returns empty activities."""
    response = await client.get("/api/v1/dashboard/recent-activity")
    assert response.status_code == 200

    data = response.json()
    assert "last_edited_project" in data
    assert "recent_activity" in data
    assert data["last_edited_project"] is None
    assert data["recent_activity"]["projects"] == []
    assert data["recent_activity"]["wbes"] == []
    assert data["recent_activity"]["cost_elements"] == []
    assert data["recent_activity"]["change_orders"] == []


@pytest.mark.asyncio
async def test_get_dashboard_recent_activity_with_project(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test dashboard endpoint with a project returns project in activity."""
    # Create a project
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Test Project",
        code="TEST-001",
        budget=Decimal("100000.00"),
    )
    project = await project_service.create_project(
        project_in=project_in,
        actor_id=mock_admin_user.user_id,
    )
    await db_session.commit()

    # Get dashboard data
    response = await client.get("/api/v1/dashboard/recent-activity")
    assert response.status_code == 200

    data = response.json()
    assert data["last_edited_project"] is not None
    assert data["last_edited_project"]["project_id"] == str(project.project_id)
    assert data["last_edited_project"]["project_name"] == "Test Project"
    assert data["last_edited_project"]["project_code"] == "TEST-001"

    # Check metrics
    metrics = data["last_edited_project"]["metrics"]
    assert metrics["total_budget"] == "100000.00"
    assert metrics["total_wbes"] == 0
    assert metrics["total_cost_elements"] == 0
    assert metrics["active_change_orders"] == 0

    # Check recent activity
    assert len(data["recent_activity"]["projects"]) == 1
    project_activity = data["recent_activity"]["projects"][0]
    assert project_activity["entity_name"] == "Test Project"
    assert project_activity["entity_type"] == "project"
    assert project_activity["action"] in ["created", "updated"]


@pytest.mark.asyncio
async def test_get_dashboard_recent_activity_with_wbe(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test dashboard endpoint with WBE returns WBE in activity."""
    # Create project and WBE
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Test Project",
        code="TEST-001",
        budget=Decimal("100000.00"),
    )
    project = await project_service.create_project(
        project_in=project_in,
        actor_id=mock_admin_user.user_id,
    )

    wbe_service = WBEService(db_session)
    wbe_in = WBECreate(
        project_id=project.project_id,
        code="1.1",
        name="Test WBE",
        level=1,
    )
    await wbe_service.create_wbe(
        wbe_in=wbe_in,
        actor_id=mock_admin_user.user_id,
    )
    await db_session.commit()

    # Get dashboard data
    response = await client.get("/api/v1/dashboard/recent-activity")
    assert response.status_code == 200

    data = response.json()
    assert len(data["recent_activity"]["wbes"]) == 1
    wbe_activity = data["recent_activity"]["wbes"][0]
    assert wbe_activity["entity_name"] == "Test WBE"
    assert wbe_activity["entity_type"] == "wbe"
    assert wbe_activity["project_id"] == str(project.project_id)
    assert wbe_activity["project_name"] == "Test Project"


@pytest.mark.asyncio
async def test_get_dashboard_recent_activity_with_change_order(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test dashboard endpoint with change order returns it in activity."""
    # Create project
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Test Project",
        code="TEST-001",
        budget=Decimal("100000.00"),
    )
    project = await project_service.create_project(
        project_in=project_in,
        actor_id=mock_admin_user.user_id,
    )

    # Create change order
    co_service = ChangeOrderService(db_session)
    from app.models.schemas.change_order import ChangeOrderCreate

    co_in = ChangeOrderCreate(
        project_id=project.project_id,
        code="CO-2026-001",
        title="Test Change Order",
        description="Test change order description",
        justification="Testing",
        impact_level="LOW",
    )
    await co_service.create_change_order(
        change_order_in=co_in,
        actor_id=mock_admin_user.user_id,
    )
    await db_session.commit()

    # Get dashboard data
    response = await client.get("/api/v1/dashboard/recent-activity")
    assert response.status_code == 200

    data = response.json()
    assert len(data["recent_activity"]["change_orders"]) == 1
    co_activity = data["recent_activity"]["change_orders"][0]
    assert co_activity["entity_name"] == "Test Change Order"
    assert co_activity["entity_type"] == "change_order"
    assert co_activity["project_id"] == str(project.project_id)
    assert co_activity["project_name"] == "Test Project"


@pytest.mark.asyncio
async def test_get_dashboard_recent_activity_limit(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test dashboard endpoint respects activity_limit parameter."""
    # Create multiple projects
    project_service = ProjectService(db_session)

    for i in range(5):
        project_in = ProjectCreate(
            name=f"Test Project {i}",
            code=f"TEST-{i:03d}",
            budget=Decimal("100000.00"),
        )
        await project_service.create_project(
            project_in=project_in,
            actor_id=mock_admin_user.user_id,
        )

    await db_session.commit()

    # Get dashboard data with limit
    response = await client.get("/api/v1/dashboard/recent-activity?activity_limit=3")
    assert response.status_code == 200

    data = response.json()
    assert len(data["recent_activity"]["projects"]) == 3


@pytest.mark.asyncio
async def test_get_dashboard_project_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test dashboard endpoint calculates correct project metrics."""
    # Create project with WBEs
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Test Project",
        code="TEST-001",
        budget=Decimal("100000.00"),
    )
    project = await project_service.create_project(
        project_in=project_in,
        actor_id=mock_admin_user.user_id,
    )

    # Create WBEs
    wbe_service = WBEService(db_session)
    for i in range(3):
        wbe_in = WBECreate(
            project_id=project.project_id,
            code=f"1.{i}",
            name=f"Test WBE {i}",
            level=1,
        )
        await wbe_service.create_wbe(
            wbe_in=wbe_in,
            actor_id=mock_admin_user.user_id,
        )

    await db_session.commit()

    # Get dashboard data
    response = await client.get("/api/v1/dashboard/recent-activity")
    assert response.status_code == 200

    data = response.json()
    metrics = data["last_edited_project"]["metrics"]
    assert metrics["total_wbes"] == 3
    assert metrics["total_budget"] == "100000.00"
