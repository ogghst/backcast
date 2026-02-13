"""API integration tests for Cost Aggregation endpoints."""

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
            "cost-registration-read",
            "cost-registration-create",
            "cost-element-read",
            "cost-element-create",
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
async def setup_cost_element(client: AsyncClient) -> dict[str, Any]:
    """Setup a cost element with cost registrations for testing."""
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
            "department_id": dept_id,
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

    # 6. Create cost registrations across different dates
    # Day 1: 5000
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 5000.0,
            "description": "Day 1 cost",
            "registration_date": datetime(2026, 1, 10, tzinfo=UTC).isoformat(),
        },
    )

    # Day 5: 7000
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 7000.0,
            "description": "Day 5 cost",
            "registration_date": datetime(2026, 1, 14, tzinfo=UTC).isoformat(),
        },
    )

    # Day 10: 3000
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 3000.0,
            "description": "Day 10 cost",
            "registration_date": datetime(2026, 1, 19, tzinfo=UTC).isoformat(),
        },
    )

    return {"cost_element_id": cost_element_id}


class TestCostAggregationAPI:
    """Test cost aggregation API endpoints."""

    @pytest.mark.asyncio
    async def test_get_aggregated_costs_daily(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /cost-registrations/aggregated with period=daily.

        Test ID: T-015

        Expected: One row per day with sum of costs
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 31, tzinfo=UTC)

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/aggregated",
            params={
                "cost_element_id": str(cost_element_id),
                "period": "daily",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3  # 3 days with costs

        # Verify structure
        for item in data:
            assert "period_start" in item
            assert "total_amount" in item

    @pytest.mark.asyncio
    async def test_get_aggregated_costs_weekly(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /cost-registrations/aggregated with period=weekly.

        Test ID: T-016

        Expected: One row per week (Monday start) with sum
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 31, tzinfo=UTC)

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/aggregated",
            params={
                "cost_element_id": str(cost_element_id),
                "period": "weekly",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All dates are in January 2026, should be in same week or adjacent weeks

    @pytest.mark.asyncio
    async def test_get_aggregated_costs_monthly(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /cost-registrations/aggregated with period=monthly.

        Test ID: T-017

        Expected: One row per month (1st start) with sum
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 31, tzinfo=UTC)

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/aggregated",
            params={
                "cost_element_id": str(cost_element_id),
                "period": "monthly",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1  # All in January

    @pytest.mark.asyncio
    async def test_get_aggregated_costs_with_time_travel(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test cost aggregation with as_of parameter.

        Test ID: T-018

        Scenario:
        - Query with as_of in the past
        - Expected: Only include costs as of that date
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 31, tzinfo=UTC)
        as_of_date = datetime(2026, 1, 15, tzinfo=UTC)  # Before Day 10 cost

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/aggregated",
            params={
                "cost_element_id": str(cost_element_id),
                "period": "daily",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "as_of": as_of_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        # Should only have costs from Day 1 and Day 5 (not Day 10)

    @pytest.mark.asyncio
    async def test_get_aggregated_costs_invalid_period(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test cost aggregation with invalid period returns 422."""
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/aggregated",
            params={
                "cost_element_id": str(cost_element_id),
                "period": "invalid",  # Invalid period
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            },
        )

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_cumulative_costs(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test GET /cost-registrations/cumulative endpoint.

        Expected: Time series with running cumulative totals
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 31, tzinfo=UTC)

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/cumulative",
            params={
                "cost_element_id": str(cost_element_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Verify structure
        for item in data:
            assert "registration_date" in item
            assert "amount" in item
            assert "cumulative_amount" in item

        # Verify cumulative sums
        if len(data) >= 2:
            # First item
            assert data[0]["cumulative_amount"] >= data[0]["amount"]
            # Subsequent items should have increasing cumulative totals
            for i in range(1, len(data)):
                assert data[i]["cumulative_amount"] >= data[i - 1]["cumulative_amount"]

    @pytest.mark.asyncio
    async def test_get_aggregated_costs_empty_result(
        self, client: AsyncClient, setup_cost_element: dict[str, Any]
    ) -> None:
        """Test cost aggregation with date range containing no costs.

        Expected: Empty list
        """
        # Arrange
        cost_element_id = setup_cost_element["cost_element_id"]
        start_date = datetime(2026, 2, 1, tzinfo=UTC)  # February (no costs)
        end_date = datetime(2026, 2, 28, tzinfo=UTC)

        # Act
        response = await client.get(
            "/api/v1/cost-registrations/aggregated",
            params={
                "cost_element_id": str(cost_element_id),
                "period": "daily",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
