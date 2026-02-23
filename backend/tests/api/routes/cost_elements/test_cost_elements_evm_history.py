"""API integration tests for EVM history (Time Series)."""

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
            "schedule-baseline-create",
            "cost-registration-create",
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
    """Setup complete EVM data."""
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
            "branch": "main",
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

    return {
        "cost_element_id": cost_element_id,
        "budget": 100000,
    }


class TestEVMHistoryAPI:
    """Test EVM history API endpoint."""

    @pytest.mark.asyncio
    async def test_get_evm_history_endpoint(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /cost-elements/{id}/evm-history returns 200 OK.

        Test ID: T-003 (from Plan)
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        control_date = datetime(2026, 6, 15, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/evm-history",
            params={
                "granularity": "week",
                "control_date": control_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert data["granularity"] == "week"
        assert isinstance(data["points"], list)
        assert len(data["points"]) > 0
        assert "pv" in data["points"][0]
        assert "ev" in data["points"][0]
        assert "ac" in data["points"][0]
