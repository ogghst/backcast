"""API integration tests for Progress Entries."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

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
        return [
            "progress-entry-read",
            "progress-entry-create",
            "progress-entry-update",
            "progress-entry-delete",
            "cost-element-read",
            "cost-element-create",
        ]

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
        return "admin"


def mock_get_rbac_service() -> MockRBACService:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Any:
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def setup_cost_element(client: AsyncClient) -> dict[str, Any]:
    """Setup a cost element for testing progress entries."""
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept"},
    )
    dept_id = dept_res.json()["department_id"]

    # 2. Cost Element Type
    type_res = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": f"T-{uuid4().hex[:4].upper()}",
            "name": "Type",
            "department_id": dept_id,
        },
    )
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj", "budget": 10000},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": f"W-{uuid4().hex[:4].upper()}",
            "name": "WBE",
            "project_id": proj_id,
            "branch": "main",
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"CE-{uuid4().hex[:4].upper()}",
            "name": "Cost Element",
            "budget_amount": 100000,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
            "branch": "main",
        },
    )
    cost_element_id = ce_res.json()["cost_element_id"]

    return {
        "cost_element_id": cost_element_id,
        "dept_id": dept_id,
        "type_id": type_id,
        "project_id": proj_id,
        "wbe_id": wbe_id,
    }


class TestProgressEntriesAPI:
    """Test Progress Entries API endpoints."""

    @pytest.mark.asyncio
    async def test_create_progress_entry_success(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test POST /progress-entries creates a progress entry.

        Test ID: T-001, T-002
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": "Foundation complete",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["progress_percentage"] == "50.00"
        assert data["cost_element_id"] == str(cost_element_id)
        assert data["notes"] == "Foundation complete"
        assert "progress_entry_id" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_zero_percentage(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test POST /progress-entries with 0% progress.

        Test ID: T-001
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 0.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["progress_percentage"] == "0.00"

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_hundred_percentage(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test POST /progress-entries with 100% progress.

        Test ID: T-002
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 100.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["progress_percentage"] == "100.00"

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_negative_percentage_fails(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test POST /progress-entries with negative percentage returns 400.

        Test ID: T-003
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": -1.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )

        # Assert
        assert response.status_code == 422  # Pydantic validation returns 422

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_over_hundred_percentage_fails(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test POST /progress-entries with >100% returns 400.

        Test ID: T-004
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 101.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )

        # Assert
        assert response.status_code == 422  # Pydantic validation returns 422

    @pytest.mark.asyncio
    async def test_get_progress_entry_by_id(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /progress-entries/{id} returns progress entry."""
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        create_res = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )
        progress_entry_id = create_res.json()["progress_entry_id"]

        # Act
        response = await client.get(f"/api/v1/progress-entries/{progress_entry_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["progress_entry_id"] == progress_entry_id
        assert data["progress_percentage"] == "50.00"

    @pytest.mark.asyncio
    async def test_update_progress_entry_increase(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test PUT /progress-entries/{id} increases progress.

        Test ID: T-005
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        create_res = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )
        progress_entry_id = create_res.json()["progress_entry_id"]

        # Act
        response = await client.put(
            f"/api/v1/progress-entries/{progress_entry_id}",
            json={"progress_percentage": 75.0},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["progress_percentage"] == "75.00"

    @pytest.mark.asyncio
    async def test_update_progress_entry_decrease(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test PUT /progress-entries/{id} decreases progress.

        Test ID: T-006
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        create_res = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 75.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )
        progress_entry_id = create_res.json()["progress_entry_id"]

        # Act
        response = await client.put(
            f"/api/v1/progress-entries/{progress_entry_id}",
            json={
                "progress_percentage": 50.0,
                "notes": "Work undone - inspection failed",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["progress_percentage"] == "50.00"
        assert data["notes"] == "Work undone - inspection failed"

    @pytest.mark.asyncio
    async def test_delete_progress_entry(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test DELETE /progress-entries/{id} soft deletes entry."""
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        create_res = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )
        progress_entry_id = create_res.json()["progress_entry_id"]

        # Act
        response = await client.delete(f"/api/v1/progress-entries/{progress_entry_id}")

        # Assert
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_get_latest_progress(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /progress-entries/cost-element/{id}/latest.

        Test ID: T-008
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 25.0,
                "reported_date": datetime(2026, 1, 10, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )
        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )

        # Act
        response = await client.get(
            f"/api/v1/progress-entries/cost-element/{cost_element_id}/latest"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["progress_percentage"] == "50.00"

    @pytest.mark.asyncio
    async def test_get_progress_history(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /progress-entries/cost-element/{id}/history.

        Test ID: T-008
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 25.0,
                "reported_date": datetime(2026, 1, 10, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )
        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(cost_element_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
            },
        )

        # Act
        response = await client.get(
            f"/api/v1/progress-entries/cost-element/{cost_element_id}/history"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
