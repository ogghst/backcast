from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app

# Mock user for authentication
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
            "cost-element-type-read",
            "cost-element-type-create",
            "cost-element-type-update",
            "cost-element-type-delete",
            "department-create",  # Needed for setup
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
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_cost_element_type(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test creating a new cost element type."""
    # Create Department first
    dept_resp = await client.post(
        "/api/v1/departments",
        json={"code": f"DEPT-{uuid4().hex[:4].upper()}", "name": "Department Test"},
    )
    assert dept_resp.status_code == 201
    dept_id = dept_resp.json()["department_id"]

    type_data = {
        "code": f"TYPE-{uuid4().hex[:6].upper()}",
        "name": "Test Type",
        "description": "A test type",
        "department_id": dept_id,
    }

    response = await client.post("/api/v1/cost-element-types", json=type_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Type"
    assert "cost_element_type_id" in data
    assert data["department_id"] == dept_id


@pytest.mark.asyncio
async def test_get_cost_element_types(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test retrieving list of cost element types."""
    # Create Department
    dept_resp = await client.post(
        "/api/v1/departments",
        json={
            "code": f"DEPT-LIST-{uuid4().hex[:4].upper()}",
            "name": "Department List",
        },
    )
    dept_id = dept_resp.json()["department_id"]

    # Create types
    for i in range(3):
        await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"TYPE-{i}",
                "name": f"Type {i}",
                "department_id": dept_id,
            },
        )

    # Get all
    response = await client.get("/api/v1/cost-element-types")

    assert response.status_code == 200
    data = response.json()["items"]
    # Note: DB might contain other types from other tests, so we check inclusion
    assert len(data) >= 3
    assert any(t["code"] == "TYPE-0" for t in data)


@pytest.mark.asyncio
async def test_get_cost_element_type_by_id(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test retrieving a specific cost element type."""
    # Create Department
    dept_resp = await client.post(
        "/api/v1/departments",
        json={"code": f"DEPT-GET-{uuid4().hex[:4].upper()}", "name": "Department Get"},
    )
    dept_id = dept_resp.json()["department_id"]

    # Create type
    create_resp = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": "specific-type",
            "name": "Specific Type",
            "department_id": dept_id,
        },
    )
    type_id = create_resp.json()["cost_element_type_id"]

    # Get specific type
    response = await client.get(f"/api/v1/cost-element-types/{type_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Specific Type"
    assert data["code"] == "specific-type"


@pytest.mark.asyncio
async def test_update_cost_element_type(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test updating a cost element type."""
    # Create Department
    dept_resp = await client.post(
        "/api/v1/departments",
        json={"code": f"DEPT-UPD-{uuid4().hex[:4].upper()}", "name": "Department Upd"},
    )
    dept_id = dept_resp.json()["department_id"]

    # Create type
    create_resp = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": "TYPE-UPD",
            "name": "Original Name",
            "department_id": dept_id,
        },
    )
    type_id = create_resp.json()["cost_element_type_id"]

    # Update
    response = await client.put(
        f"/api/v1/cost-element-types/{type_id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["code"] == "TYPE-UPD"


@pytest.mark.asyncio
async def test_delete_cost_element_type(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test soft deleting a cost element type."""
    # Create Department
    dept_resp = await client.post(
        "/api/v1/departments",
        json={"code": f"DEPT-DEL-{uuid4().hex[:4].upper()}", "name": "Department Del"},
    )
    dept_id = dept_resp.json()["department_id"]

    # Create type
    create_resp = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": "TYPE-DEL",
            "name": "To Delete",
            "department_id": dept_id,
        },
    )
    type_id = create_resp.json()["cost_element_type_id"]

    # Delete
    response = await client.delete(f"/api/v1/cost-element-types/{type_id}")
    assert response.status_code == 204

    # Verify not in list
    list_resp = await client.get("/api/v1/cost-element-types")
    types = list_resp.json()["items"]
    assert not any(t["cost_element_type_id"] == type_id for t in types)

    # Verify 404 on get
    get_resp = await client.get(f"/api/v1/cost-element-types/{type_id}")
    assert get_resp.status_code == 404
