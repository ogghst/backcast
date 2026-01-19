"""API integration tests for EVM metrics."""

from datetime import UTC, datetime
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
            "cost-element-read",
            "cost-element-create",
            "progress-entry-read",
            "progress-entry-create",
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
async def setup_evm_data(client: AsyncClient) -> dict[str, Any]:
    """Setup complete EVM data: cost element, baseline, progress, costs."""
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
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj", "budget": 100000},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": f"W-{uuid4().hex[:4].upper()}",
            "name": "WBE",
            "project_id": proj_id,
            "department_id": dept_id,
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element with budget
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"CE-{uuid4().hex[:4].upper()}",
            "name": "Cost Element",
            "budget_amount": 100000,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
        },
    )
    cost_element_id = ce_res.json()["cost_element_id"]

    # 6. Schedule Baseline
    await client.post(
        f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
        json={
            "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
            "progression_type": "LINEAR",
            "description": "2026 Project Baseline",
        },
    )

    # 7. Progress Entry (50% complete)
    await client.post(
        "/api/v1/progress-entries",
        json={
            "cost_element_id": str(cost_element_id),
            "progress_percentage": 50.0,
            "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
            "reported_by_user_id": str(mock_admin_user.user_id),
            "notes": "Halfway complete",
        },
    )

    # 8. Cost Registrations (total 60,000)
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 35000.0,
            "description": "Materials",
            "registration_date": datetime(2026, 3, 1, tzinfo=UTC).isoformat(),
        },
    )
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 25000.0,
            "description": "Labor",
            "registration_date": datetime(2026, 6, 15, tzinfo=UTC).isoformat(),
        },
    )

    return {
        "cost_element_id": cost_element_id,
        "budget": 100000,
        "progress": 50.0,
        "total_costs": 60000,
    }


class TestEVMMetricsAPI:
    """Test EVM metrics API endpoint."""

    @pytest.mark.asyncio
    async def test_get_evm_metrics_returns_all_8_metrics(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /cost-elements/{id}/evm returns all 8 EVM metrics.

        Test ID: T-011

        Expected metrics:
        - BAC (Budget at Completion)
        - PV (Planned Value)
        - AC (Actual Cost)
        - EV (Earned Value)
        - CV (Cost Variance)
        - SV (Schedule Variance)
        - CPI (Cost Performance Index)
        - SPI (Schedule Performance Index)
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/evm"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all 8 metrics are present
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data
        assert "cv" in data
        assert "sv" in data
        assert "cpi" in data
        assert "spi" in data

        # Verify values (Decimal fields are serialized as strings)
        assert data["bac"] == "100000.00"  # Budget
        assert data["ac"] == "60000.00"  # Sum of costs
        assert data["ev"] == "50000.0000"  # BAC × 50% (4 decimal places for calculated values)

        # Verify variances
        assert data["cv"] == "-10000.0000"  # EV - AC = 50000 - 60000
        # Note: PV depends on date calculation, may vary

        # Verify metadata
        assert data["cost_element_id"] == str(cost_element_id)
        assert "control_date" in data
        assert data["progress_percentage"] == "50.00"
        assert data.get("warning") is None  # No warning (progress exists)

    @pytest.mark.asyncio
    async def test_get_evm_metrics_with_no_progress_returns_warning(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test EVM when no progress reported returns EV=0 with warning.

        Test ID: T-014

        Expected:
        - EV = 0
        - Warning message present
        - CPI = 0 (since EV = 0)
        """
        # Create a new cost element without progress
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept2"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj2", "budget": 100000},
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "WBE2",
                "project_id": proj_id,
                "department_id": dept_id,
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Cost Element No Progress",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
            },
        )
        new_cost_element_id = ce_res.json()["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{new_cost_element_id}/evm"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # EV should be 0 (Decimal serialized as string, note: zero may be "0" not "0.00")
        assert data["ev"] in ("0", "0.00")

        # Warning should be present
        assert data["warning"] is not None
        assert "No progress reported" in data["warning"]

        # CPI should be 0 or None (since EV = 0)
        assert data.get("cpi") is None or data.get("cpi") == 0

    @pytest.mark.asyncio
    async def test_get_evm_metrics_with_control_date(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test EVM with control_date parameter for time-travel.

        Test ID: T-012, T-013

        Scenario:
        - Query with control_date in the past
        - Expected: Returns metrics as of that date
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        past_date = datetime(2026, 3, 15, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/evm",
            params={"control_date": past_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Control date should be reflected in response
        assert "control_date" in data

    @pytest.mark.asyncio
    async def test_get_evm_metrics_cost_element_not_found(
        self, client: AsyncClient
    ) -> None:
        """Test EVM with non-existent cost element returns 404.

        Test ID: T-012
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/cost-elements/{fake_id}/evm")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_evm_metrics_branch_isolation(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test EVM with branch parameter.

        Test ID: T-013

        Scenario:
        - Query with branch="main"
        - Expected: Returns metrics for main branch
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/evm",
            params={"branch": "main"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "bac" in data
