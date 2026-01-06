"""Integration tests for WBE API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
)


def mock_get_current_user():
    return mock_admin_user


def mock_get_current_active_user():
    return mock_admin_user


# Mock RBAC service that allows everything
class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "wbe-read",
            "wbe-create",
            "wbe-update",
            "wbe-delete",
        ]


def mock_get_rbac_service():
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth():
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def test_project(client: AsyncClient):
    """Create a test project for WBE tests."""
    project_data = {
        "name": "WBE Test Project",
        "code": "WBE-TEST",
        "budget": 500000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    return response.json()


@pytest.mark.asyncio
async def test_create_wbe(client: AsyncClient, override_auth, db_session, test_project):
    """Test creating a new WBE."""
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "1.0",
        "name": "Phase 1",
        "budget_allocation": 100000,
        "level": 1,
        "description": "First phase of the project",
    }

    response = await client.post("/api/v1/wbes", json=wbe_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Phase 1"
    assert data["code"] == "1.0"
    assert float(data["budget_allocation"]) == 100000.0
    assert data["project_id"] == test_project["project_id"]
    assert "id" in data
    assert "wbe_id" in data


@pytest.mark.asyncio
async def test_create_wbe_duplicate_code(
    client: AsyncClient, override_auth, db_session, test_project
):
    """Test creating WBE with duplicate code in same project fails."""
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "1.1",
        "name": "WBE 1",
        "budget_allocation": 50000,
        "level": 1,
    }

    # Create first WBE
    response1 = await client.post("/api/v1/wbes", json=wbe_data)
    assert response1.status_code == 201

    # Try to create duplicate
    wbe_data["name"] = "WBE 2"
    response2 = await client.post("/api/v1/wbes", json=wbe_data)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_get_wbes_by_project(
    client: AsyncClient, override_auth, db_session, test_project
):
    """Test retrieving WBEs filtered by project."""
    # Create multiple WBEs
    for i in range(3):
        wbe_data = {
            "project_id": test_project["project_id"],
            "code": f"1.{i}",
            "name": f"WBE {i}",
            "budget_allocation": 10000 * (i + 1),
            "level": 1,
        }
        await client.post("/api/v1/wbes", json=wbe_data)

    # Get WBEs for project
    response = await client.get(f"/api/v1/wbes?project_id={test_project['project_id']}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(w["project_id"] == test_project["project_id"] for w in data)


@pytest.mark.asyncio
async def test_get_wbe_by_id(
    client: AsyncClient, override_auth, db_session, test_project
):
    """Test retrieving a specific WBE."""
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "2.0",
        "name": "Specific WBE",
        "budget_allocation": 75000,
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    wbe_id = create_response.json()["wbe_id"]

    # Get specific WBE
    response = await client.get(f"/api/v1/wbes/{wbe_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Specific WBE"
    assert data["code"] == "2.0"


@pytest.mark.asyncio
async def test_update_wbe(client: AsyncClient, override_auth, db_session, test_project):
    """Test updating a WBE creates new version."""
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "3.0",
        "name": "Original WBE",
        "budget_allocation": 50000,
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    wbe_id = create_response.json()["wbe_id"]

    # Update WBE
    update_data = {
        "name": "Updated WBE",
        "budget_allocation": 75000,
    }
    response = await client.put(f"/api/v1/wbes/{wbe_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated WBE"
    assert float(data["budget_allocation"]) == 75000
    assert data["code"] == "3.0"  # Code should remain unchanged


@pytest.mark.asyncio
async def test_delete_wbe(client: AsyncClient, override_auth, db_session, test_project):
    """Test soft deleting a WBE."""
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "4.0",
        "name": "To Delete",
        "budget_allocation": 25000,
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    wbe_id = create_response.json()["wbe_id"]

    # Delete WBE
    response = await client.delete(f"/api/v1/wbes/{wbe_id}")

    assert response.status_code == 204

    # Verify WBE is not in list
    list_response = await client.get(
        f"/api/v1/wbes?project_id={test_project['project_id']}"
    )
    wbes = list_response.json()
    assert not any(w["code"] == "4.0" for w in wbes)


@pytest.mark.asyncio
async def test_get_wbe_history(
    client: AsyncClient, override_auth, db_session, test_project
):
    """Test retrieving version history for a WBE."""
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "5.0",
        "name": "History WBE",
        "budget_allocation": 30000,
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    wbe_id = create_response.json()["wbe_id"]

    # Update WBE to create second version
    await client.put(
        f"/api/v1/wbes/{wbe_id}",
        json={"name": "Updated History WBE"},
    )

    # Get history
    response = await client.get(f"/api/v1/wbes/{wbe_id}/history")

    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 2
    assert any(h["name"] == "Updated History WBE" for h in history)
    assert any(h["name"] == "History WBE" for h in history)


@pytest.mark.asyncio
async def test_wbe_hierarchical_structure(
    client: AsyncClient, override_auth, db_session, test_project
):
    """Test creating hierarchical WBE structure."""
    # Create parent WBE
    parent_data = {
        "project_id": test_project["project_id"],
        "code": "1.0",
        "name": "Parent WBE",
        "budget_allocation": 100000,
        "level": 1,
    }
    parent_response = await client.post("/api/v1/wbes", json=parent_data)
    parent_id = parent_response.json()["wbe_id"]

    # Create child WBE
    child_data = {
        "project_id": test_project["project_id"],
        "code": "1.1",
        "name": "Child WBE",
        "budget_allocation": 50000,
        "level": 2,
        "parent_wbe_id": parent_id,
    }
    child_response = await client.post("/api/v1/wbes", json=child_data)

    assert child_response.status_code == 201
    child_data_resp = child_response.json()
    assert child_data_resp["parent_wbe_id"] == parent_id
    assert child_data_resp["level"] == 2
