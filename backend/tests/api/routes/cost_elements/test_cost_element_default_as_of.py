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
            "project-create",
            "wbe-create",
            "department-create",
            "cost-element-type-create",
        ]

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
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept"},
    )
    if dept_res.status_code != 201:
        raise Exception(f"Dept failed: {dept_res.text}")
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
    if type_res.status_code != 201:
        raise Exception(f"Type failed: {type_res.text}")
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj"},
    )
    if proj_res.status_code != 201:
        raise Exception(f"Proj failed: {proj_res.text}")
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
    if wbe_res.status_code != 201:
        raise Exception(f"WBE failed: {wbe_res.text}")
    wbe_id = wbe_res.json()["wbe_id"]

    return {
        "department_id": dept_id,
        "cost_element_type_id": type_id,
        "project_id": proj_id,
        "wbe_id": wbe_id,
    }


@pytest.mark.asyncio
async def test_create_future_cost_element_and_query_default(
    client: AsyncClient, setup_dependencies: dict
) -> None:
    deps = setup_dependencies
    future_date = datetime.now(UTC) + timedelta(days=10)

    # Use string for budget to avoid Decimal validation issues
    element_data = {
        "code": f"CE-FUTURE-{uuid4().hex[:4].upper()}",
        "name": "Future Element",
        "budget_amount": "1000.00",
        "wbe_id": deps["wbe_id"],
        "cost_element_type_id": deps["cost_element_type_id"],
        "branch": "main",
        "control_date": future_date.isoformat(),
    }

    # Create in future
    response = await client.post("/api/v1/cost-elements", json=element_data)
    assert response.status_code == 201, f"Failed to create: {response.text}"
    created_id = response.json()["cost_element_id"]

    # Query with default as_of (should be now) -> Should NOT find it
    res_list = await client.get("/api/v1/cost-elements")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    found = any(i["cost_element_id"] == created_id for i in items)
    assert not found, "Should not find future cost element with default query"

    # Query specific ID with default as_of (should be now) -> Should be 404
    res_single = await client.get(f"/api/v1/cost-elements/{created_id}")
    assert res_single.status_code == 404, (
        "Should not find future cost element by ID with default query"
    )

    # Query with explicit future as_of -> Should find it
    future_iso = (future_date + timedelta(minutes=1)).isoformat()
    res_future_list = await client.get(
        "/api/v1/cost-elements", params={"as_of": future_iso}
    )
    assert res_future_list.status_code == 200
    items_future = res_future_list.json()["items"]
    found_future = any(i["cost_element_id"] == created_id for i in items_future)
    assert found_future, "Should find future cost element with valid as_of"

    res_future_single = await client.get(
        f"/api/v1/cost-elements/{created_id}", params={"as_of": future_iso}
    )
    assert res_future_single.status_code == 200
