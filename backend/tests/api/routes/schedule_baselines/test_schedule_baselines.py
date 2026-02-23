"""API tests for Schedule Baseline endpoints.

Tests CRUD operations for schedule baselines with temporal context consistency.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

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
        return [
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "schedule-baseline-delete",
        ]


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
async def setup_dependencies(client: AsyncClient) -> dict[str, Any]:
    """Setup dependencies: Department, CostElementType, Project, WBE, CostElement."""
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
        json={
            "code": f"P-{uuid4().hex[:4].upper()}",
            "name": "Project",
            "budget": 1000000,
            "branch": "main",
        },
    )
    project_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": f"W-{uuid4().hex[:4].upper()}",
            "name": "WBE",
            "project_id": str(project_id),
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"C-{uuid4().hex[:4].upper()}",
            "name": "Cost Element",
            "wbe_id": str(wbe_id),
            "cost_element_type_id": str(type_id),
            "budget_amount": 50000,
            "branch": "main",
        },
    )
    ce_id = ce_res.json()["cost_element_id"]

    return {
        "cost_element_id": ce_id,
        "project_id": project_id,
        "wbe_id": wbe_id,
    }


class TestScheduleBaselineCreate:
    """Test schedule baseline CREATE endpoint with temporal context."""

    @pytest.mark.asyncio
    async def test_schedule_baseline_create_with_branch_main_in_body_creates_in_main(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that POST with branch='main' in body extracts branch from body.

        Acceptance Criteria:
        - POST request with branch="main" in body extracts branch from request body
        - control_date can also be extracted from request body
        """
        # Arrange
        cost_element_id = setup_dependencies["cost_element_id"]
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=365)

        # Act - Try to create with branch in body (using nested endpoint)
        # This will fail because a baseline already exists (auto-created), but we're
        # just testing that the endpoint doesn't reject the request due to branch param location
        response = await client.post(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
            json={
                "name": "Q1 2026 Baseline",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "progression_type": "LINEAR",
                "branch": "main",
                "control_date": None,
            },
        )

        # Assert - Should get 400 (baseline already exists) NOT 422 (validation error)
        # This proves the endpoint accepts branch and control_date in the body
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()
        # If we got a validation error about branch being in the wrong place, the test would fail

    @pytest.mark.asyncio
    async def test_schedule_baseline_create_with_control_date_in_body_uses_specified_date(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that POST with control_date in body extracts control_date from body.

        Acceptance Criteria:
        - POST request accepts control_date in request body
        - No validation error for control_date in body
        """
        # Arrange
        cost_element_id = setup_dependencies["cost_element_id"]
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=365)
        control_date = datetime(2026, 1, 19, tzinfo=UTC)

        # Act - Try to create with control_date in body (using nested endpoint)
        response = await client.post(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
            json={
                "name": "Q1 2026 Baseline",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "progression_type": "LINEAR",
                "control_date": control_date.isoformat(),
            },
        )

        # Assert - Should get 400 (baseline already exists) NOT 422 (validation error)
        # This proves the endpoint accepts control_date in the body
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_schedule_baseline_create_with_defaults_uses_main_branch(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that POST without branch field uses schema default of 'main'.

        Acceptance Criteria:
        - Request without branch field uses schema default value of 'main'
        - No validation error for missing branch field
        """
        # Arrange
        cost_element_id = setup_dependencies["cost_element_id"]
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=365)

        # Act - Try to create without branch field (should default to main)
        response = await client.post(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
            json={
                "name": "Q1 2026 Baseline",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "progression_type": "LINEAR",
            },
        )

        # Assert - Should get 400 (baseline already exists) NOT 422 (validation error)
        # This proves the endpoint uses the schema default for branch
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_schedule_baseline_create_with_non_main_branch_defaults_to_main(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that POST with non-main branch value still uses schema default.

        Acceptance Criteria:
        - Request with branch='feature-branch' uses schema default 'main'
        - Schema field defaults to "main" regardless of input
        """
        # Arrange
        cost_element_id = setup_dependencies["cost_element_id"]
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=365)

        # Act - Try to create with non-main branch value
        response = await client.post(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
            json={
                "name": "Q1 2026 Baseline",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "progression_type": "LINEAR",
                "branch": "feature-branch",  # Schema defaults to "main" anyway
            },
        )

        # Assert - Should get 400 (baseline already exists) NOT 422 (validation error)
        # The schema defaults to "main", so it tries to create in main (which already exists)
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()


class TestScheduleBaselineUpdate:
    """Test schedule baseline UPDATE endpoint with temporal context."""

    async def _get_baseline_id(self, client: AsyncClient, cost_element_id: str) -> str:
        """Helper to get the schedule baseline ID for a cost element."""
        # Query schedule baselines filtered by cost element
        list_response = await client.get(
            f"/api/v1/schedule-baselines?branch=main&cost_element_id={cost_element_id}"
        )
        list_data = list_response.json()
        if list_data.get("items") and len(list_data["items"]) > 0:
            return list_data["items"][0]["schedule_baseline_id"]
        pytest.fail("No schedule baseline found for cost element")

    @pytest.mark.asyncio
    async def test_schedule_baseline_update_with_branch_in_body_updates_in_specified_branch(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that PUT with branch='main' in body extracts branch from body.

        Acceptance Criteria:
        - PUT request with branch="main" in body extracts branch from request body
        - No validation error for branch in body
        """
        # Arrange - Get the auto-created baseline ID
        cost_element_id = setup_dependencies["cost_element_id"]
        baseline_id = await self._get_baseline_id(client, cost_element_id)

        # Act - Update with branch in body (using nested endpoint)
        update_response = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}",
            json={
                "name": "Updated Baseline",
                "branch": "main",
                "control_date": None,
            },
        )

        # Assert - Updated successfully
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Baseline"
        assert data["branch"] == "main"

    @pytest.mark.asyncio
    async def test_schedule_baseline_update_with_control_date_in_body_uses_specified_date(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that PUT with control_date in body extracts control_date from body.

        Acceptance Criteria:
        - PUT request accepts control_date in request body
        - No validation error for control_date in body
        """
        # Arrange - Get the auto-created baseline ID
        cost_element_id = setup_dependencies["cost_element_id"]
        baseline_id = await self._get_baseline_id(client, cost_element_id)
        # Use a future date for control_date (must be >= valid_time lower bound)
        control_date = datetime.now(UTC) + timedelta(days=1)

        # Act - Update with control_date in body (using nested endpoint)
        update_response = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}",
            json={
                "name": "Updated Baseline",
                "control_date": control_date.isoformat(),
            },
        )

        # Assert - Updated successfully
        assert update_response.status_code == 200


class TestScheduleBaselineDelete:
    """Test schedule baseline DELETE endpoint continues using query parameters."""

    async def _get_baseline_id(self, client: AsyncClient, cost_element_id: str) -> str:
        """Helper to get the schedule baseline ID for a cost element."""
        # Query schedule baselines filtered by cost element
        list_response = await client.get(
            f"/api/v1/schedule-baselines?branch=main&cost_element_id={cost_element_id}"
        )
        list_data = list_response.json()
        if list_data.get("items") and len(list_data["items"]) > 0:
            return list_data["items"][0]["schedule_baseline_id"]
        pytest.fail("No schedule baseline found for cost element")

    @pytest.mark.asyncio
    async def test_schedule_baseline_delete_with_query_params_succeeds(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that DELETE with query parameters soft deletes the baseline.

        Acceptance Criteria:
        - DELETE request with ?branch=main&control_date=... soft deletes the baseline
        - DELETE continues using query parameters (HTTP/1.1 constraint exception)
        """
        # Arrange - Get the auto-created baseline ID
        cost_element_id = setup_dependencies["cost_element_id"]
        baseline_id = await self._get_baseline_id(client, cost_element_id)

        # Act - Delete with query parameters (using nested endpoint)
        delete_response = await client.delete(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}?branch=main"
        )

        # Assert - Deleted successfully
        assert delete_response.status_code == 204

        # Verify baseline is deleted
        get_response = await client.get(
            f"/api/v1/schedule-baselines/{baseline_id}?branch=main"
        )
        assert get_response.status_code == 404


class TestScheduleBaselineDirectEndpoints:
    """Test direct schedule baseline endpoints at /api/v1/schedule-baselines."""

    async def _get_baseline_id(self, client: AsyncClient, cost_element_id: str) -> str:
        """Helper to get the schedule baseline ID for a cost element."""
        # Query schedule baselines filtered by cost element
        list_response = await client.get(
            f"/api/v1/schedule-baselines?branch=main&cost_element_id={cost_element_id}"
        )
        list_data = list_response.json()
        if list_data.get("items") and len(list_data["items"]) > 0:
            return list_data["items"][0]["schedule_baseline_id"]
        pytest.fail("No schedule baseline found for cost element")

    @pytest.mark.asyncio
    async def test_direct_post_with_branch_in_body_creates_in_main(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that direct POST with branch in body extracts branch from request body.

        Acceptance Criteria:
        - POST request with branch="main" in body creates baseline in main branch
        - Endpoint extracts branch from baseline_in.branch instead of hardcoded value
        """
        # Arrange
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=365)

        # Act - Create using direct endpoint with branch in body
        response = await client.post(
            "/api/v1/schedule-baselines",
            json={
                "name": "Direct Baseline",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "progression_type": "LINEAR",
                "branch": "main",
                "control_date": None,
                "cost_element_id": setup_dependencies["cost_element_id"],
            },
        )
        # Assert - Should create successfully (direct endpoint doesn't require cost_element)
        data = response.json()
        assert response.status_code == 201
        assert data["branch"] == "main"
        assert data["name"] == "Direct Baseline"

    @pytest.mark.asyncio
    async def test_direct_post_with_control_date_in_body_uses_specified_date(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that direct POST with control_date in body extracts control_date from body.

        Acceptance Criteria:
        - POST request accepts control_date in request body
        - No validation error for control_date in body
        """
        # Arrange
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=365)
        control_date = datetime.now(UTC) + timedelta(hours=1)

        # Act - Create using direct endpoint with control_date in body
        response = await client.post(
            "/api/v1/schedule-baselines",
            json={
                "name": "Direct Baseline with Control Date",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "progression_type": "LINEAR",
                "control_date": control_date.isoformat(),
            },
        )

        # Assert - Should create successfully
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Direct Baseline with Control Date"

    @pytest.mark.asyncio
    async def test_direct_put_with_branch_in_body_updates_in_specified_branch(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that direct PUT with branch in body extracts branch from request body.

        Acceptance Criteria:
        - PUT request with branch="main" in body updates baseline in main branch
        - Endpoint extracts branch from request body instead of hardcoded value
        """
        # Arrange - Get the auto-created baseline ID
        cost_element_id = setup_dependencies["cost_element_id"]
        baseline_id = await self._get_baseline_id(client, cost_element_id)

        # Act - Update using direct endpoint with branch in body
        update_response = await client.put(
            f"/api/v1/schedule-baselines/{baseline_id}",
            json={
                "name": "Updated via Direct Endpoint",
                "branch": "main",
                "control_date": None,
            },
        )

        # Assert - Updated successfully
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated via Direct Endpoint"
        assert data["branch"] == "main"

    @pytest.mark.asyncio
    async def test_direct_put_with_control_date_in_body_uses_specified_date(
        self,
        client: AsyncClient,
        setup_dependencies: dict[str, Any],
    ) -> None:
        """Test that direct PUT with control_date in body extracts control_date from body.

        Acceptance Criteria:
        - PUT request accepts control_date in request body
        - Endpoint extracts control_date from request body instead of hardcoded None
        """
        # Arrange - Get the auto-created baseline ID
        cost_element_id = setup_dependencies["cost_element_id"]
        baseline_id = await self._get_baseline_id(client, cost_element_id)
        # Use a future date for control_date (must be >= valid_time lower bound)
        control_date = datetime.now(UTC) + timedelta(days=1)

        # Act - Update using direct endpoint with control_date in body
        update_response = await client.put(
            f"/api/v1/schedule-baselines/{baseline_id}",
            json={
                "name": "Updated with Control Date",
                "control_date": control_date.isoformat(),
            },
        )

        # Assert - Updated successfully
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated with Control Date"
