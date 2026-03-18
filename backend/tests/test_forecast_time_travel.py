"""Test forecast time travel semantics.

This test reproduces the issue where updating a forecast with a future control_date
makes it unavailable for queries with as_of dates before that control_date.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
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
        return [
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "forecast-read",
            "forecast-update",
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


@pytest.mark.asyncio
async def test_forecast_time_travel_with_future_control_date(
    client: AsyncClient,
) -> None:
    """Test that forecasts can be queried with as_of dates before their control_date.

    Scenario:
    1. Create cost element at current time
    2. Create initial forecast at current time
    3. Update forecast with control_date in the future (current time + 10 days)
    4. Query forecast at as_of = control_date - 1 day (before control_date, but after initial creation)

    Expected: Should return the old forecast version because its valid_time covers the query date.
    Actual Bug: Returns 404 because get_as_of() uses System Time Travel semantics which requires
    transaction_time to contain as_of.
    """
    # Calculate dynamic dates to ensure they're always in the future
    now = datetime.now(timezone.utc)  # noqa: UP017
    future_control_date = now + timedelta(days=10)
    query_as_of_date = future_control_date - timedelta(days=1)

    # Create dependencies
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept"},
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
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj", "budget": 100},
    )
    proj_id = proj_res.json()["project_id"]

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

    # 1. Create cost element (auto-creates forecast)
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": "CE-TEST-001",
            "name": "Test Cost Element",
            "budget_amount": "1000.00",
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
            "branch": "main",
        },
    )
    assert ce_res.status_code == 201
    cost_element_id = ce_res.json()["cost_element_id"]

    # 2. Update forecast with future control_date
    update_res = await client.put(
        f"/api/v1/cost-elements/{cost_element_id}/forecast",
        json={
            "eac_amount": "700.00",
            "basis_of_estimate": "Updated forecast",
            "control_date": future_control_date.isoformat(),
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["eac_amount"] == "700.00"

    # 3. Query at as_of = control_date - 1 day (before control_date)
    # This should return the OLD version (eac_amount=1000)
    query_res = await client.get(
        f"/api/v1/cost-elements/{cost_element_id}/forecast",
        params={"as_of": query_as_of_date.isoformat(), "branch": "main"},
    )

    # Bug: Returns 404 instead of old version
    assert query_res.status_code == 200, (
        f"Expected 200, got {query_res.status_code}. Forecast should be visible at as_of date before control_date. Response: {query_res.text}"
    )

    forecast_data = query_res.json()
    assert forecast_data["eac_amount"] == "1000.00", (
        f"Expected old forecast (1000.00), got {forecast_data['eac_amount']}"
    )
