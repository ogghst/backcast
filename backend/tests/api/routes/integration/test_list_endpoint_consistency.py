"""API tests for list endpoint parameter consistency.

Tests that all versioned entity list endpoints support branch, mode, and as_of parameters.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

# Mock user for authentication
mock_admin_user = User(
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
    return mock_admin_user


class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["*"]
    
    async def has_project_access(
        self,
        user_id,
        user_role: str,
        project_id,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id, user_role: str):
        return []

    async def get_project_role(self, user_id, project_id):
        return "admin"


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestScheduleBaselinesListEndpoint:
    """Tests for /api/v1/schedule-baselines list endpoint."""

    async def test_list_accepts_mode_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts mode parameter."""
        response = await client.get(
            "/api/v1/schedule-baselines?mode=merged&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_isolated_mode(self, client: AsyncClient):
        """Test that list endpoint accepts isolated mode."""
        response = await client.get(
            "/api/v1/schedule-baselines?mode=isolated&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_as_of_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts as_of parameter."""
        as_of = datetime.now(tz=UTC).isoformat()
        response = await client.get(
            "/api/v1/schedule-baselines",
            params={"as_of": as_of, "page": 1, "per_page": 20},
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_rejects_invalid_mode(self, client: AsyncClient):
        """Test that list endpoint rejects invalid mode values."""
        response = await client.get(
            "/api/v1/schedule-baselines?mode=invalid&page=1&per_page=20"
        )
        # Should raise 422 validation error
        assert response.status_code == 422

    async def test_list_all_parameters_together(self, client: AsyncClient):
        """Test that list endpoint accepts all parameters together."""
        as_of = datetime.now(tz=UTC).isoformat()
        response = await client.get(
            "/api/v1/schedule-baselines",
            params={
                "branch": "main",
                "mode": "merged",
                "as_of": as_of,
                "page": 1,
                "per_page": 20,
            },
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestChangeOrdersListEndpoint:
    """Tests for /api/v1/change-orders list endpoint."""

    async def test_list_accepts_mode_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts mode parameter."""
        project_id = uuid4()
        response = await client.get(
            f"/api/v1/change-orders?project_id={project_id}&mode=merged&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_isolated_mode(self, client: AsyncClient):
        """Test that list endpoint accepts isolated mode."""
        project_id = uuid4()
        response = await client.get(
            f"/api/v1/change-orders?project_id={project_id}&mode=isolated&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_rejects_invalid_mode(self, client: AsyncClient):
        """Test that list endpoint rejects invalid mode values."""
        project_id = uuid4()
        response = await client.get(
            f"/api/v1/change-orders?project_id={project_id}&mode=invalid&page=1&per_page=20"
        )
        # Should raise 422 validation error
        assert response.status_code == 422


@pytest.mark.asyncio
class TestProgressEntriesListEndpoint:
    """Tests for /api/v1/progress-entries list endpoint."""

    async def test_list_accepts_branch_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts branch parameter."""
        response = await client.get(
            "/api/v1/progress-entries?branch=main&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_mode_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts mode parameter."""
        response = await client.get(
            "/api/v1/progress-entries?branch=main&mode=merged&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_isolated_mode(self, client: AsyncClient):
        """Test that list endpoint accepts isolated mode."""
        response = await client.get(
            "/api/v1/progress-entries?branch=main&mode=isolated&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_rejects_invalid_mode(self, client: AsyncClient):
        """Test that list endpoint rejects invalid mode values."""
        response = await client.get(
            "/api/v1/progress-entries?branch=main&mode=invalid&page=1&per_page=20"
        )
        # Should raise 422 validation error
        assert response.status_code == 422


@pytest.mark.asyncio
class TestCostRegistrationsListEndpoint:
    """Tests for /api/v1/cost-registrations list endpoint."""

    async def test_list_accepts_branch_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts branch parameter."""
        response = await client.get(
            "/api/v1/cost-registrations?branch=main&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_mode_parameter(self, client: AsyncClient):
        """Test that list endpoint accepts mode parameter."""
        response = await client.get(
            "/api/v1/cost-registrations?branch=main&mode=merged&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_accepts_isolated_mode(self, client: AsyncClient):
        """Test that list endpoint accepts isolated mode."""
        response = await client.get(
            "/api/v1/cost-registrations?branch=main&mode=isolated&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_rejects_invalid_mode(self, client: AsyncClient):
        """Test that list endpoint rejects invalid mode values."""
        response = await client.get(
            "/api/v1/cost-registrations?branch=main&mode=invalid&page=1&per_page=20"
        )
        # Should raise 422 validation error
        assert response.status_code == 422


@pytest.mark.asyncio
class TestCostElementsListEndpoint:
    """Tests for /api/v1/cost-elements list endpoint (existing compliance)."""

    async def test_list_has_mode_parameter(self, client: AsyncClient):
        """Test that cost elements list endpoint has mode parameter (existing)."""
        response = await client.get(
            "/api/v1/cost-elements?mode=merged&page=1&per_page=20"
        )
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestWBEsListEndpoint:
    """Tests for /api/v1/wbes list endpoint (existing compliance)."""

    async def test_list_has_mode_parameter(self, client: AsyncClient):
        """Test that WBEs list endpoint has mode parameter (existing)."""
        response = await client.get("/api/v1/wbes?mode=merged&page=1&per_page=20")
        # Should not raise 422 validation error
        assert response.status_code in [200, 401, 403, 404]
