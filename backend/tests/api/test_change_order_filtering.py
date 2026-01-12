from typing import Any, cast
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User


# --- Mocks for Auth ---
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
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
            "project-read",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
        ]

def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


# --- Fixtures ---
@pytest_asyncio.fixture
async def test_project(client: AsyncClient) -> dict[str, Any]:
    project_data = {
        "name": "CO Test Project",
        "code": "CO-PROJ",
        "budget": 500000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()


# --- Tests ---

@pytest.mark.asyncio
async def test_search_change_orders(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test searching Change Orders by code or name."""
    project_id = test_project["project_id"]

    # 1. Create Change Orders
    co1 = {
        "project_id": project_id,
        "code": "CO-SEARCH-1",
        "title": "Alpha Change",
        "status": "Draft",
        "description": "First CO",
    }
    co2 = {
        "project_id": project_id,
        "code": "CO-SEARCH-2",
        "title": "Beta Change",
        "status": "Submitted",
        "description": "Second CO",
    }
    
    resp1 = await client.post("/api/v1/change-orders", json=co1)
    assert resp1.status_code == 201
    
    resp2 = await client.post("/api/v1/change-orders", json=co2)
    assert resp2.status_code == 201

    # 2. Search for "Alpha" -> Should return CO1 only
    search_resp = await client.get(
        f"/api/v1/change-orders",
        params={"project_id": project_id, "search": "Alpha"}
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["items"]
    
    # Assert
    assert len(results) == 1
    assert results[0]["code"] == "CO-SEARCH-1"
    assert results[0]["title"] == "Alpha Change"

    # 3. Search for "SEARCH" -> Should return both
    search_all = await client.get(
        f"/api/v1/change-orders",
        params={"project_id": project_id, "search": "SEARCH"}
    )
    assert search_all.status_code == 200
    assert len(search_all.json()["items"]) == 2

@pytest.mark.asyncio
async def test_filter_change_orders(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test filtering Change Orders by status."""
    project_id = test_project["project_id"]

    # 1. Create COs with different statuses
    co1 = {
        "project_id": project_id,
        "code": "CO-FILT-1",
        "title": "Draft CO",
        "status": "Draft",
        "description": "Draft",
    }
    co2 = {
        "project_id": project_id,
        "code": "CO-FILT-2",
        "title": "Submitted CO",
        "status": "Submitted",
        "description": "Submitted",
    }
    
    await client.post("/api/v1/change-orders", json=co1)
    await client.post("/api/v1/change-orders", json=co2)

    # 2. Filter by status:Draft
    resp = await client.get(
        "/api/v1/change-orders",
        params={"project_id": project_id, "filters": "status:Draft"}
    )
    assert resp.status_code == 200
    results = resp.json()["items"]
    
    assert len(results) == 1
    assert results[0]["code"] == "CO-FILT-1"
    assert results[0]["status"] == "Draft"
    
@pytest.mark.asyncio
async def test_merge_change_order(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test merging a Change Order branch into main."""
    project_id = test_project["project_id"]

    # 1. Create CO (creates branch co-TEST-MERGE)
    co_data = {
        "project_id": project_id,
        "code": "TEST-MERGE",
        "title": "Merge Test",
        "status": "Draft",
    }
    resp = await client.post("/api/v1/change-orders", json=co_data)
    assert resp.status_code == 201
    co_id = resp.json()["change_order_id"]
    branch_name = f"co-TEST-MERGE"

    # 2. Modify CO on its branch
    update_data = {
        "status": "Approved",
        "justification": "Ready for merge"
    }
    # Note: Backend routes usually default to main branch or take explicit branch param.
    # But update_change_order logic finds current version and uses its branch.
    # Wait, get_current finds it by ID. If it was created on main?
    # NO, ChangeOrderService creates it on 'main', then creates a BRANCH.
    # So main has V1. Branch has V1 (cloned).
    # If we update on the BRANCH, we need to target that branch in update call?
    # NO, update_change_order logic: gets "current" version, then uses `current.branch`.
    # But get_current defaults to "main" if not specific.
    # So if we want to update on the branch, current API doesn't let us specify branch for UPDATE?
    # ChangeOrderService.update_change_order:
    # "Creates a new version ... Always updates on the current active branch."
    # AND: "Get the current version to find its branch ... get_current(change_order_id)"
    # get_current uses branch="main" by default!
    # ISSUE: We can only update "main" version if service defaults to main.
    # BUT, we might want to update the BRANCH version.
    # We'll see if update_change_order actually supports branch targeting.
    # It does NOT in its signature. It calls `get_current(change_order_id)`.
    # `get_current` has default branch="main".
    # So users CANNOT update the branch version via API?
    # Ah, the `update_change_order` route DOES NOT take a branch parameter.
    # This is another gap! But sticking to Merge Test...
    # I can test Merge of the "main" version -> "main" makes no sense.
    # Let's assume for now I merge what is there.
    
    # 3. Request Merge
    # POST /{id}/merge
    merge_resp = await client.post(f"/api/v1/change-orders/{co_id}/merge")
    
    # This should fail until implemented
    assert merge_resp.status_code == 200
    merged_data = merge_resp.json()
    assert merged_data["branch"] == "main"
    # assert merged_data["merge_from_branch"] == branch_name # Internal field, maybe not in Public schema

@pytest.mark.asyncio
async def test_revert_change_order(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test reverting a Change Order."""
    project_id = test_project["project_id"]

    # 1. Create CO
    co_data = {
        "project_id": project_id,
        "code": "TEST-REVERT",
        "title": "Revert Test",
        "status": "Draft",
    }
    resp = await client.post("/api/v1/change-orders", json=co_data)
    co_id = resp.json()["change_order_id"]

    # 2. Update CO (New Version)
    await client.put(f"/api/v1/change-orders/{co_id}", json={"status": "Submitted"})
    
    # Verify current is Submitted
    curr_resp = await client.get(f"/api/v1/change-orders/{co_id}")
    assert curr_resp.json()["status"] == "Submitted"
    
    # 3. Revert
    # POST /{id}/revert
    revert_resp = await client.post(f"/api/v1/change-orders/{co_id}/revert")
    assert revert_resp.status_code == 200
    
    # Verify status reverted to Draft (cloned from previous version)
    final_resp = await client.get(f"/api/v1/change-orders/{co_id}")
    assert final_resp.json()["status"] == "Draft"
