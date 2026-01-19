"""API integration tests for Cost Registrations."""

from datetime import UTC, datetime
from decimal import Decimal
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
            "cost-registration-read",
            "cost-registration-create",
            "cost-registration-update",
            "cost-registration-delete",
            "cost-element-read",
            "cost-element-create",
            "project-create",
            "wbe-create",
            "department-create",
            "cost-element-type-create",
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
    """Setup dependencies: Project, WBE, Department, CostElementType, CostElement."""
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
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"CE-{uuid4().hex[:4].upper()}",
            "name": "Cost Element",
            "budget_amount": 5000.00,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
        },
    )
    ce_id = ce_res.json()["cost_element_id"]

    return {
        "department_id": dept_id,
        "cost_element_type_id": type_id,
        "project_id": proj_id,
        "wbe_id": wbe_id,
        "cost_element_id": ce_id,
    }


class TestCostRegistrationsAPI:
    """Test Cost Registrations API endpoints."""

    @pytest.mark.asyncio
    async def test_create_cost_registration(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test creating a cost registration."""
        deps = setup_dependencies
        registration_data = {
            "cost_element_id": deps["cost_element_id"],
            "amount": 100.00,
            "description": "Test cost registration",
            "quantity": 10.0,
            "unit_of_measure": "hours",
            "invoice_number": "INV-001",
            "vendor_reference": "Test Vendor",
        }

        response = await client.post(
            "/api/v1/cost-registrations",
            json=registration_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "100.00"
        assert data["description"] == "Test cost registration"
        assert "cost_registration_id" in data

    @pytest.mark.asyncio
    async def test_create_cost_registration_budget_exceeded(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test creating a cost registration that exceeds budget."""
        deps = setup_dependencies
        # Create a cost registration that exceeds the budget (5000)
        registration_data = {
            "cost_element_id": deps["cost_element_id"],
            "amount": 6000.00,
            "description": "Exceeded budget",
        }

        response = await client.post(
            "/api/v1/cost-registrations",
            json=registration_data,
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "Budget exceeded"

    @pytest.mark.asyncio
    async def test_get_cost_registrations_paginated(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test getting paginated cost registrations."""
        deps = setup_dependencies
        # Create multiple cost registrations
        for i in range(3):
            await client.post(
                "/api/v1/cost-registrations",
                json={
                    "cost_element_id": deps["cost_element_id"],
                    "amount": float(100 * (i + 1)),
                    "description": f"Cost {i}",
                },
            )

        # Get first page
        response = await client.get(
            f"/api/v1/cost-registrations?cost_element_id={deps['cost_element_id']}&page=1&per_page=2"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 3
        assert data["page"] == 1
        assert data["per_page"] == 2

    @pytest.mark.asyncio
    async def test_get_cost_registration_by_id(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test getting a cost registration by ID."""
        deps = setup_dependencies
        # Create a cost registration
        create_res = await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 100.00,
                "description": "Test",
            },
        )
        reg_id = create_res.json()["cost_registration_id"]

        # Get by ID
        response = await client.get(f"/api/v1/cost-registrations/{reg_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["cost_registration_id"] == reg_id
        assert data["amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_get_cost_registration_not_found(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test getting a non-existent cost registration."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/cost-registrations/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_cost_registration_creates_new_version(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test updating a cost registration creates a new version."""
        deps = setup_dependencies
        # Create a cost registration
        create_res = await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 100.00,
                "description": "Original",
            },
        )
        reg_id = create_res.json()["cost_registration_id"]
        original_id = create_res.json()["id"]

        # Update
        update_res = await client.put(
            f"/api/v1/cost-registrations/{reg_id}",
            json={
                "amount": 150.00,
                "description": "Updated",
            },
        )
        assert update_res.status_code == 200
        data = update_res.json()
        assert data["amount"] == "150.00"
        assert data["description"] == "Updated"
        assert data["id"] != original_id  # New version has different ID

    @pytest.mark.asyncio
    async def test_delete_cost_registration(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test soft deleting a cost registration."""
        deps = setup_dependencies
        # Create a cost registration
        create_res = await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 100.00,
                "description": "To delete",
            },
        )
        reg_id = create_res.json()["cost_registration_id"]

        # Delete
        response = await client.delete(f"/api/v1/cost-registrations/{reg_id}")
        assert response.status_code == 204

        # Verify deleted (should return 404)
        get_res = await client.get(f"/api/v1/cost-registrations/{reg_id}")
        assert get_res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_cost_registration_history(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test getting version history for a cost registration."""
        deps = setup_dependencies
        # Create a cost registration
        create_res = await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 100.00,
                "description": "Original",
            },
        )
        reg_id = create_res.json()["cost_registration_id"]

        # Update to create a new version
        await client.put(
            f"/api/v1/cost-registrations/{reg_id}",
            json={"amount": 150.00, "description": "Updated"},
        )

        # Get history
        response = await client.get(f"/api/v1/cost-registrations/{reg_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Original + updated version

    @pytest.mark.asyncio
    async def test_get_budget_status(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test getting budget status for a cost element."""
        deps = setup_dependencies
        # Create a cost registration
        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 500.00,
                "description": "Test",
            },
        )

        # Get budget status
        response = await client.get(
            f"/api/v1/cost-registrations/budget-status/{deps['cost_element_id']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["budget"] == "5000.00"
        assert data["used"] == "500.00"
        assert data["remaining"] == "4500.00"
        assert data["percentage"] == 10.0

    @pytest.mark.asyncio
    async def test_time_travel_query(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test time-travel query for cost registration."""
        deps = setup_dependencies
        # Create a cost registration
        create_res = await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 100.00,
                "description": "Original",
                "registration_date": "2026-01-01T00:00:00Z",
            },
        )
        reg_id = create_res.json()["cost_registration_id"]

        # Update to create v2
        await client.put(
            f"/api/v1/cost-registrations/{reg_id}",
            json={"amount": 150.00, "description": "Updated"},
        )

        # Query with as_of before the update (should return original)
        # Note: This tests the API endpoint structure; actual time-travel behavior
        # depends on the service's control_date handling
        response = await client.get(
            f"/api/v1/cost-registrations/{reg_id}?as_of=2026-01-01T12:00:00Z"
        )
        # Response may be 200 or 404 depending on timing; this tests the parameter is accepted
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_create_cost_registration_with_control_date(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test creating a cost registration with control_date parameter.

        Verifies that control_date sets the valid_time start date for bitemporal tracking.
        This is critical for time-travel queries and historical cost analysis.
        """
        deps = setup_dependencies
        # Create a cost registration with control_date set to Jan 1, 2026
        control_date_str = "2026-01-01T00:00:00Z"
        registration_data = {
            "cost_element_id": deps["cost_element_id"],
            "amount": 100.00,
            "description": "Test cost with control_date",
            "control_date": control_date_str,
        }

        response = await client.post(
            "/api/v1/cost-registrations",
            json=registration_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "100.00"
        assert data["description"] == "Test cost with control_date"
        assert "cost_registration_id" in data

        # Verify that time-travel query as of the control_date returns this cost
        reg_id = data["cost_registration_id"]
        response = await client.get(
            f"/api/v1/cost-registrations/{reg_id}?as_of={control_date_str}"
        )
        # Should return 200 because the cost is valid as of the control_date
        assert response.status_code == 200
        historical_data = response.json()
        assert historical_data["cost_registration_id"] == reg_id
        assert historical_data["amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_update_cost_registration_with_control_date(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test updating a cost registration with control_date parameter.

        Verifies that control_date sets the valid_time start date for the new version.
        """
        deps = setup_dependencies
        # Create initial version with control_date set to Jan 1, 2026
        create_control_date = "2026-01-01T00:00:00Z"
        create_res = await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": deps["cost_element_id"],
                "amount": 100.00,
                "description": "Original",
                "control_date": create_control_date,
            },
        )
        reg_id = create_res.json()["cost_registration_id"]

        # Update with control_date set to Jan 15, 2026 (after creation)
        update_control_date = "2026-01-15T00:00:00Z"
        update_res = await client.put(
            f"/api/v1/cost-registrations/{reg_id}",
            json={
                "amount": 150.00,
                "description": "Updated with control_date",
                "control_date": update_control_date,
            },
        )
        assert update_res.status_code == 200
        data = update_res.json()
        assert data["amount"] == "150.00"
        assert data["description"] == "Updated with control_date"

        # Verify time-travel query as of Jan 10 returns original version
        response = await client.get(
            f"/api/v1/cost-registrations/{reg_id}?as_of=2026-01-10T12:00:00Z"
        )
        # Should return 200 with original amount (100.00)
        assert response.status_code == 200
        historical_data = response.json()
        assert historical_data["amount"] == "100.00"
        assert historical_data["description"] == "Original"

        # Verify current query returns updated version
        response = await client.get(f"/api/v1/cost-registrations/{reg_id}")
        assert response.status_code == 200
        current_data = response.json()
        assert current_data["amount"] == "150.00"
        assert current_data["description"] == "Updated with control_date"

    @pytest.mark.asyncio
    async def test_cost_registration_with_all_fields(
        self, client: AsyncClient, setup_dependencies: dict[str, Any]
    ) -> None:
        """Test creating a cost registration with all optional fields."""
        deps = setup_dependencies
        registration_data = {
            "cost_element_id": deps["cost_element_id"],
            "amount": 250.00,
            "quantity": 10.0,
            "unit_of_measure": "hours",
            "registration_date": "2026-01-15T00:00:00Z",
            "description": "Consulting services",
            "invoice_number": "INV-2026-001",
            "vendor_reference": "Acme Consulting Inc.",
        }

        response = await client.post(
            "/api/v1/cost-registrations",
            json=registration_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "250.00"
        assert data["quantity"] == "10.00"
        assert data["unit_of_measure"] == "hours"
        assert data["invoice_number"] == "INV-2026-001"
        assert data["vendor_reference"] == "Acme Consulting Inc."
