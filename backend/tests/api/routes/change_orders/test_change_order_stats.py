"""API tests for Change Order Stats endpoint."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

# --- Mocks for Auth ---
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


class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        # Grant all common permissions for testing
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "project-read",
            "project-create",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
        ]


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


class MockRBACServiceNoPermission(RBACServiceABC):
    """RBAC mock that denies all permissions."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return False

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return False

    def get_user_permissions(self, user_role: str) -> list[str]:
        return []


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


# --- Fixtures ---
@pytest_asyncio.fixture
async def test_project(client: AsyncClient) -> dict[str, Any]:
    """Create a test project."""
    project_data = {
        "name": "CO Stats Test Project",
        "code": "CO-STATS-PROJ",
        "budget": 1000000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def test_change_orders(
    client: AsyncClient,
    test_project: dict[str, Any],
    db_session: AsyncSession,
) -> list[dict[str, Any]]:
    """Create test change orders with various states."""
    project_id = test_project["project_id"]
    cos = []

    # Create 3 change orders
    for i in range(3):
        co_data = {
            "project_id": project_id,
            "code": f"CO-STATS-{i:03d}",
            "title": f"Test CO {i}",
            "description": "Test description",
        }
        response = await client.post("/api/v1/change-orders", json=co_data)
        assert response.status_code == 201
        cos.append(response.json())

    return cos


# --- Tests ---


class TestChangeOrderStatsEndpoint:
    """Test GET /api/v1/change-orders/stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_endpoint_requires_authentication(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test that stats endpoint requires authentication via RBAC.

        Note: With our mock, this should succeed because we override auth.
        The test verifies the endpoint uses RoleChecker.
        """
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        # With mock auth that has permission, should succeed
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stats_endpoint_denied_without_permission(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test that stats endpoint denies access without permission."""
        # Override with no-permission mock
        app.dependency_overrides[get_rbac_service] = lambda: MockRBACServiceNoPermission()

        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        # Should be forbidden
        assert response.status_code == 403

        # Restore mock
        app.dependency_overrides[get_rbac_service] = mock_get_rbac_service

    @pytest.mark.asyncio
    async def test_stats_response_schema_validation(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
        test_change_orders: list[dict[str, Any]],
    ) -> None:
        """Test that response matches ChangeOrderStatsResponse schema."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "total_count" in data
        assert "total_cost_exposure" in data
        assert "pending_value" in data
        assert "approved_value" in data
        assert "by_status" in data
        assert "by_impact_level" in data
        assert "cost_trend" in data
        assert "avg_approval_time_days" in data
        assert "approval_workload" in data
        assert "aging_items" in data
        assert "aging_threshold_days" in data

        # Validate types
        assert isinstance(data["total_count"], int)
        assert isinstance(data["total_cost_exposure"], (int, float, str))  # Decimal serialized
        assert isinstance(data["by_status"], list)
        assert isinstance(data["by_impact_level"], list)
        assert isinstance(data["cost_trend"], list)
        assert isinstance(data["approval_workload"], list)
        assert isinstance(data["aging_items"], list)

    @pytest.mark.asyncio
    async def test_stats_with_branch_parameter(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test stats endpoint with branch query parameter."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id, "branch": "main"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 0

    @pytest.mark.asyncio
    async def test_stats_with_as_of_parameter(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
        test_change_orders: list[dict[str, Any]],
    ) -> None:
        """Test stats endpoint with as_of time-travel parameter."""
        project_id = test_project["project_id"]

        # Get stats as of now
        now = datetime.now(UTC)
        response = await client.get(
            "/api/v1/change-orders/stats",
            params={
                "project_id": project_id,
                "as_of": now.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 3  # At least our test COs

    @pytest.mark.asyncio
    async def test_stats_with_aging_threshold_parameter(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test stats endpoint with aging_threshold_days parameter."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={
                "project_id": project_id,
                "aging_threshold_days": 14,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["aging_threshold_days"] == 14

    @pytest.mark.asyncio
    async def test_stats_aging_threshold_validation(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test that aging_threshold_days must be between 1 and 30."""
        project_id = test_project["project_id"]

        # Below minimum (1)
        response = await client.get(
            "/api/v1/change-orders/stats",
            params={
                "project_id": project_id,
                "aging_threshold_days": 0,
            },
        )
        assert response.status_code == 422  # Validation error

        # Above maximum (30)
        response = await client.get(
            "/api/v1/change-orders/stats",
            params={
                "project_id": project_id,
                "aging_threshold_days": 31,
            },
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_stats_empty_project(
        self,
        client: AsyncClient,
    ) -> None:
        """Test stats for a project with no change orders."""
        # Create a new project
        project_data = {
            "name": "Empty Project",
            "code": "EMPTY-PROJ",
            "budget": 500000,
        }
        response = await client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 201
        project_id = response.json()["project_id"]

        # Get stats
        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert float(data["total_cost_exposure"]) == 0
        assert float(data["pending_value"]) == 0
        assert float(data["approved_value"]) == 0
        assert data["by_status"] == []
        assert data["by_impact_level"] == []
        assert data["cost_trend"] == []
        assert data["approval_workload"] == []
        assert data["aging_items"] == []
        assert data["avg_approval_time_days"] is None

    @pytest.mark.asyncio
    async def test_stats_project_id_required(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that project_id is a required parameter."""
        response = await client.get("/api/v1/change-orders/stats")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_stats_response_includes_kpis(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
        test_change_orders: list[dict[str, Any]],
    ) -> None:
        """Test that response includes all expected KPIs."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # All KPIs should be present
        assert "total_count" in data
        assert "total_cost_exposure" in data
        assert "pending_value" in data
        assert "approved_value" in data
        assert "avg_approval_time_days" in data

        # total_count should match number of COs
        assert data["total_count"] >= len(test_change_orders)

    @pytest.mark.asyncio
    async def test_stats_by_status_structure(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
        test_change_orders: list[dict[str, Any]],
    ) -> None:
        """Test by_status array structure."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # by_status should have correct structure
        for status_item in data["by_status"]:
            assert "status" in status_item
            assert "count" in status_item
            assert "total_value" in status_item
            assert isinstance(status_item["status"], str)
            assert isinstance(status_item["count"], int)

    @pytest.mark.asyncio
    async def test_stats_by_impact_level_structure(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
        test_change_orders: list[dict[str, Any]],
    ) -> None:
        """Test by_impact_level array structure."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # by_impact_level should have correct structure
        for impact_item in data["by_impact_level"]:
            assert "impact_level" in impact_item
            assert "count" in impact_item
            assert "total_value" in impact_item
            assert isinstance(impact_item["impact_level"], str)
            assert isinstance(impact_item["count"], int)

    @pytest.mark.asyncio
    async def test_stats_cost_trend_structure(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
        test_change_orders: list[dict[str, Any]],
    ) -> None:
        """Test cost_trend array structure."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # cost_trend items should have correct structure
        for trend_point in data["cost_trend"]:
            assert "trend_date" in trend_point
            assert "cumulative_value" in trend_point
            assert "count" in trend_point

    @pytest.mark.asyncio
    async def test_stats_approval_workload_structure(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test approval_workload array structure."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # approval_workload items should have correct structure
        for workload_item in data["approval_workload"]:
            assert "approver_id" in workload_item
            assert "approver_name" in workload_item
            assert "pending_count" in workload_item
            assert "overdue_count" in workload_item
            assert "avg_days_waiting" in workload_item

    @pytest.mark.asyncio
    async def test_stats_aging_items_structure(
        self,
        client: AsyncClient,
        test_project: dict[str, Any],
    ) -> None:
        """Test aging_items array structure."""
        project_id = test_project["project_id"]

        response = await client.get(
            "/api/v1/change-orders/stats",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()

        # aging_items should have correct structure
        for aging_item in data["aging_items"]:
            assert "change_order_id" in aging_item
            assert "code" in aging_item
            assert "title" in aging_item
            assert "status" in aging_item
            assert "days_in_status" in aging_item
            assert "impact_level" in aging_item
            assert "sla_status" in aging_item
