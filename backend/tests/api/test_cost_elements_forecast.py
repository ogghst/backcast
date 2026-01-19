"""Integration tests for Cost Element Forecast 1:1 relationship API endpoints.

Tests from: docs/03-project-plan/iterations/2026-01-18-one-forecast-per-cost-element/01-plan.md
"""

from datetime import datetime, timedelta
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
from app.models.domain.cost_element import CostElement
from app.models.domain.forecast import Forecast
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
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-delete",
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "forecast-delete",
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
    """Setup dependencies: Project, WBE, Department, CostElementType."""
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
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj", "budget": 100},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": f"W-{uuid4().hex[:4].upper()}",
            "name": "WBE",
            "project_id": proj_id,
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    return {
        "department_id": dept_id,
        "cost_element_type_id": type_id,
        "project_id": proj_id,
        "wbe_id": wbe_id,
    }


@pytest.mark.asyncio
class TestCostElementForecastAPI:
    """Test forecast endpoints nested under cost elements."""

    async def test_get_forecast_via_cost_element(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """T-F-003: Get forecast via cost element endpoint.

        Verify that GET /cost-elements/{id}/forecast returns the forecast
        with cost element details included.
        """
        # Create a cost element (auto-creates default forecast)
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Get the forecast
        response = await client.get(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert response.status_code == 200
        data = response.json()

        # Verify forecast data
        assert "eac_amount" in data
        assert data["eac_amount"] == "100000.00"
        assert data["basis_of_estimate"] == "Initial forecast"
        assert "forecast_id" in data

        # Verify cost element details are included
        assert data["cost_element_id"] == cost_element_id
        assert "cost_element_code" in data
        assert "cost_element_name" in data
        assert data["cost_element_budget_amount"] == "100000.00"

    async def test_update_forecast_via_cost_element(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """T-F-003: Update forecast via cost element endpoint.

        Verify that PUT /cost-elements/{id}/forecast updates the forecast
        and returns the updated forecast.
        """
        # Create a cost element
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Update the forecast
        update_data = {
            "eac_amount": "120000.00",
            "basis_of_estimate": "Updated forecast after review",
        }
        response = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/forecast",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify updated values
        assert data["eac_amount"] == "120000.00"
        assert data["basis_of_estimate"] == "Updated forecast after review"
        assert data["cost_element_id"] == cost_element_id

    async def test_delete_forecast_via_cost_element(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test deleting forecast via cost element endpoint.

        Verify that DELETE /cost-elements/{id}/forecast soft deletes the forecast.
        """
        # Create a cost element
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Delete the forecast
        response = await client.delete(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert response.status_code == 204

        # Verify forecast is deleted
        get_response = await client.get(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert get_response.status_code == 404

    async def test_delete_cost_element_cascades_to_forecast(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """T-F-004: Verify cascade delete from cost element to forecast.

        When a cost element is soft deleted, its forecast should also be soft deleted.
        """
        # Create a cost element
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Verify forecast exists
        get_before = await client.get(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert get_before.status_code == 200

        # Delete the cost element
        del_response = await client.delete(f"/api/v1/cost-elements/{cost_element_id}")
        assert del_response.status_code == 204

        # Verify forecast is also deleted (cascade)
        get_after = await client.get(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert get_after.status_code == 404

    async def test_create_new_forecast_when_none_exists(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test creating a new forecast when cost element has none.

        Verify PUT /cost-elements/{id}/forecast creates forecast if none exists.
        """
        # Create a cost element
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Delete the auto-created forecast
        delete_response = await client.delete(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert delete_response.status_code == 204

        # Verify no forecast exists
        get_response = await client.get(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert get_response.status_code == 404

        # Create a new forecast via PUT
        create_data = {
            "eac_amount": "95000.00",
            "basis_of_estimate": "New forecast created",
        }
        response = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/forecast",
            json=create_data,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["eac_amount"] == "95000.00"
        assert data["basis_of_estimate"] == "New forecast created"
        assert data["cost_element_id"] == cost_element_id

    @pytest.mark.skip(reason="Branch creation endpoint not implemented yet")
    async def test_branch_isolation(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """T-F-006: Verify forecasts are isolated across branches.

        Changes in a change order branch should not affect main branch.
        """
        # Create a cost element in main branch
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Get forecast in main branch
        main_response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/forecast"
        )
        assert main_response.status_code == 200
        main_eac = main_response.json()["eac_amount"]
        assert main_eac == "100000.00"

        # Create a change order branch
        branch_res = await client.post(
            f"/api/v1/cost-elements/{cost_element_id}/branches",
            json={"branch_name": "co-test-branch"},
        )
        assert branch_res.status_code == 200

        # Update forecast in change order branch
        update_res = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/forecast",
            params={"branch": "co-testbranch"},
            json={"eac_amount": "150000.00", "basis_of_estimate": "CO scenario"},
        )
        assert update_res.status_code == 200

        # Verify forecast in CO branch has new value
        co_response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/forecast",
            params={"branch": "co-testbranch"},
        )
        assert co_response.status_code == 200
        assert co_response.json()["eac_amount"] == "150000.00"

        # Verify main branch forecast is unchanged
        main_again = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/forecast"
        )
        assert main_again.status_code == 200
        assert main_again.json()["eac_amount"] == "100000.00"


@pytest.mark.asyncio
class TestForecastZombieCheck:
    """Test that soft-deleted forecasts respect time travel boundaries.

    Following the Zombie Check TDD pattern from temporal-query-reference.md.
    """

    async def test_forecast_zombie_check(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Verify deleted forecasts respect time travel boundaries.

        Pattern: Create -> Delete -> Query Past

        1. Create forecast at T1
        2. Delete forecast at T3
        3. Query at T2 (before deletion) - should return forecast
        4. Query at T4 (after deletion) - should NOT return forecast
        """
        # Create a cost element (T1)
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": "100000.00",
                "wbe_id": setup_dependencies["wbe_id"],
                "cost_element_type_id": setup_dependencies["cost_element_type_id"],
            },
        )
        assert ce_res.status_code == 201
        cost_element_id = ce_res.json()["cost_element_id"]

        # Delete the forecast (T3)
        del_response = await client.delete(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert del_response.status_code == 204

        # Query current time (T4 - after deletion) - should NOT return
        current_response = await client.get(f"/api/v1/cost-elements/{cost_element_id}/forecast")
        assert current_response.status_code == 404, "Forecast should NOT be visible after deletion"
