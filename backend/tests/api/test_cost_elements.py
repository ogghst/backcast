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
            "cost-element-type-create",  # Dependencies
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
async def test_create_cost_element(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    deps = setup_dependencies
    element_data = {
        "code": f"CE-{uuid4().hex[:4].upper()}",
        "name": "Cost Element Test",
        "budget_amount": 1000.00,
        "wbe_id": deps["wbe_id"],
        "cost_element_type_id": deps["cost_element_type_id"],
    }

    response = await client.post("/api/v1/cost-elements?branch=main", json=element_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cost Element Test"
    assert "cost_element_id" in data
    assert data["branch"] == "main"


@pytest.mark.asyncio
async def test_create_cost_element_in_branch(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    deps = setup_dependencies
    element_data = {
        "code": f"CE-BRANCH-{uuid4().hex[:4].upper()}",
        "name": "Branch Element",
        "budget_amount": 1000.00,
        "wbe_id": deps["wbe_id"],
        "cost_element_type_id": deps["cost_element_type_id"],
        "branch": "feature-1",  # Pass branch in request body
    }

    # Create in 'feature-1' branch directly (via request body)
    response = await client.post("/api/v1/cost-elements", json=element_data)
    assert response.status_code == 201
    data = response.json()
    assert data["branch"] == "feature-1"


@pytest.mark.asyncio
async def test_update_forks_branch(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    deps = setup_dependencies
    # 1. Create in main
    element_data = {
        "code": f"CE-FORK-{uuid4().hex[:4].upper()}",
        "name": "Original Element",
        "budget_amount": 1000.00,
        "wbe_id": deps["wbe_id"],
        "cost_element_type_id": deps["cost_element_type_id"],
    }
    create_res = await client.post("/api/v1/cost-elements", json=element_data)
    element_id = create_res.json()["cost_element_id"]

    # 2. Update in 'feature-fork' branch (should fork) - pass branch in request body
    update_data = {"name": "Forked Element", "branch": "feature-fork"}
    response = await client.put(f"/api/v1/cost-elements/{element_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Forked Element"
    assert data["branch"] == "feature-fork"

    # 3. Verify main is unchanged
    main_res = await client.get(f"/api/v1/cost-elements/{element_id}?branch=main")
    assert main_res.status_code == 200
    assert main_res.json()["name"] == "Original Element"


@pytest.mark.asyncio
async def test_list_filtering(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    deps = setup_dependencies
    # Create 2 elements
    await client.post(
        "/api/v1/cost-elements",
        json={
            "code": "CE-1",
            "name": "E1",
            "budget_amount": 100,
            "wbe_id": deps["wbe_id"],
            "cost_element_type_id": deps["cost_element_type_id"],
        },
    )

    # List by WBE
    res = await client.get(f"/api/v1/cost-elements?wbe_id={deps['wbe_id']}")
    assert res.status_code == 200
    assert len(res.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_delete_cost_element_branch(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    deps = setup_dependencies
    element_data = {
        "code": f"CE-DEL-{uuid4().hex[:4].upper()}",
        "name": "To Delete",
        "budget_amount": 100,
        "wbe_id": deps["wbe_id"],
        "cost_element_type_id": deps["cost_element_type_id"],
    }
    create_res = await client.post(
        "/api/v1/cost-elements?branch=main", json=element_data
    )
    element_id = create_res.json()["cost_element_id"]

    # Delete in main
    del_res = await client.delete(f"/api/v1/cost-elements/{element_id}?branch=main")
    assert del_res.status_code == 204

    # Verify deleted in main
    get_res = await client.get(f"/api/v1/cost-elements/{element_id}?branch=main")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_get_history_filters_by_branch(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    """Test that get_history correctly filters versions by branch."""
    deps = setup_dependencies

    # 1. Create cost element in main
    element_data = {
        "code": f"CE-HIST-{uuid4().hex[:4].upper()}",
        "name": "Original in Main",
        "budget_amount": 1000.00,
        "wbe_id": deps["wbe_id"],
        "cost_element_type_id": deps["cost_element_type_id"],
    }
    create_res = await client.post("/api/v1/cost-elements", json=element_data)
    assert create_res.status_code == 201
    element_id = create_res.json()["cost_element_id"]

    # 2. Update in main (creates second version in main)
    update_res = await client.put(
        f"/api/v1/cost-elements/{element_id}",
        json={"name": "Updated in Main", "branch": "main"}
    )
    assert update_res.status_code == 200

    # 3. Create version in feature branch (fork)
    feature_update_res = await client.put(
        f"/api/v1/cost-elements/{element_id}",
        json={"name": "Feature Branch Version", "branch": "feature-1"}
    )
    assert feature_update_res.status_code == 200

    # 4. Get history for main branch
    main_history_res = await client.get(
        f"/api/v1/cost-elements/{element_id}/history?branch=main"
    )
    assert main_history_res.status_code == 200
    main_history = main_history_res.json()

    # Should have 2 versions in main (original + update)
    assert len(main_history) == 2
    assert all(v["branch"] == "main" for v in main_history)
    # Most recent first (transaction_time desc)
    assert main_history[0]["name"] == "Updated in Main"
    assert main_history[1]["name"] == "Original in Main"

    # 5. Get history for feature-1 branch
    feature_history_res = await client.get(
        f"/api/v1/cost-elements/{element_id}/history?branch=feature-1"
    )
    assert feature_history_res.status_code == 200
    feature_history = feature_history_res.json()

    # Should have 1 version in feature-1 (the fork)
    assert len(feature_history) == 1
    assert feature_history[0]["branch"] == "feature-1"
    assert feature_history[0]["name"] == "Feature Branch Version"

    # 6. Verify default branch is main
    default_history_res = await client.get(
        f"/api/v1/cost-elements/{element_id}/history"
    )
    assert default_history_res.status_code == 200
    default_history = default_history_res.json()
    assert len(default_history) == 2
    assert all(v["branch"] == "main" for v in default_history)
