
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
            "project-create",
            "project-read",
            "wbe-create",
            "wbe-read",
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
async def test_create_project_on_branch(client: AsyncClient) -> None:
    project_data = {
        "code": f"P-{uuid4().hex[:4].upper()}",
        "name": "Branch Project",
        "budget": 100000,
        "branch": "draft-1"
    }
    response = await client.post("/api/v1/projects", json=project_data)
    assert response.status_code == 201
    data = response.json()
    assert data["branch"] == "draft-1"

    # Verify we can fetch it on that branch
    get_res = await client.get(f"/api/v1/projects/{data['id']}?branch=draft-1")
    assert get_res.status_code == 200
    assert get_res.json()["branch"] == "draft-1"

    # Verify it does NOT exist on main (since it was created on draft-1 only)
    # Actually, projects usually start on main. But IF we allow creating on another branch directly...
    # TemporalService.get_projects filters by branch.
    # If mode is STRICT, we expect 404 on main?
    # Or get_projects returns list.

    # Let's check get by ID on main
    get_main = await client.get(f"/api/v1/projects/{data['id']}?branch=main")
    # It might return 404 if not found on main.
    assert get_main.status_code == 404

@pytest.mark.asyncio
async def test_create_wbe_on_branch(client: AsyncClient) -> None:
    # 1. Create Project on main
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Main Project", "budget": 100},
    )
    proj_id = proj_res.json()["project_id"]

    # 2. Create WBE on 'feature-1' branch
    wbe_data = {
        "project_id": proj_id,
        "code": "1.1",
        "name": "Feature WBE",
        "branch": "feature-1"
    }
    wbe_res = await client.post("/api/v1/wbes", json=wbe_data)
    assert wbe_res.status_code == 201
    data = wbe_res.json()
    assert data["branch"] == "feature-1"

    # 3. Verify fetch on feature-1
    get_feature = await client.get(f"/api/v1/wbes/{data['id']}?branch=feature-1")
    assert get_feature.status_code == 200

    # 4. Verify fetch on main (should be 404)
    get_main = await client.get(f"/api/v1/wbes/{data['id']}?branch=main")
    assert get_main.status_code == 404
