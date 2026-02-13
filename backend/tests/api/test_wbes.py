"""Integration tests for WBE API endpoints."""

from collections.abc import Generator
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


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
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


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def test_project(client: AsyncClient) -> dict[str, Any]:
    """Create a test project for WBE tests."""
    project_data = {
        "name": "WBE Test Project",
        "code": "WBE-TEST",
        "budget": 500000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_wbe(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
    # Response is paginated: {"items": [...], "total": 3, "page": 1, "per_page": 20}
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert all(w["project_id"] == test_project["project_id"] for w in data["items"])


@pytest.mark.asyncio
async def test_get_wbe_by_id(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
async def test_update_wbe(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
async def test_delete_wbe(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
    wbes_data = list_response.json()
    # Response is paginated: {"items": [...], "total": 0, "page": 1, "per_page": 20}
    wbes = wbes_data["items"]
    assert not any(w["code"] == "4.0" for w in wbes)


@pytest.mark.asyncio
async def test_get_wbe_history(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
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


@pytest.mark.asyncio
async def test_create_wbe_with_control_date(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test creating WBE with explicit control_date."""
    # Future date to ensure it's different from "now"
    control_date = "2026-03-03T10:00:00+00:00"

    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "CD-1.0",
        "name": "Control Date WBE",
        "budget_allocation": 100000,
        "level": 1,
        "control_date": control_date,
    }

    response = await client.post("/api/v1/wbes", json=wbe_data)
    assert response.status_code == 201
    data = response.json()

    # Verify valid_time starts at control_date
    assert data["valid_time"].startswith(f"[{control_date[:10]}")


@pytest.mark.asyncio
async def test_update_wbe_with_control_date(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test updating WBE with explicit control_date."""
    # 1. Create standard WBE
    create_resp = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": test_project["project_id"],
            "code": "CD-2.0",
            "name": "Update Test WBE",
            "budget_allocation": 50000,
            "level": 1,
        },
    )
    wbe_id = create_resp.json()["wbe_id"]

    # 2. Update with control date
    control_date = "2026-04-01T10:00:00+00:00"
    update_data = {"name": "Updated With Control Date", "control_date": control_date}

    response = await client.put(f"/api/v1/wbes/{wbe_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()

    # Verify new version starts at control_date
    assert data["valid_time"].startswith(f"[{control_date[:10]}")


@pytest.mark.asyncio
async def test_delete_wbe_with_control_date(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test deleting WBE with explicit control_date."""
    # 1. Create WBE
    create_resp = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": test_project["project_id"],
            "code": "CD-3.0",
            "name": "Delete Test WBE",
            "budget_allocation": 50000,
            "level": 1,
        },
    )
    wbe_id = create_resp.json()["wbe_id"]

    # 2. Delete with control date
    control_date = "2026-05-01T10:00:00+00:00"
    response = await client.delete(
        f"/api/v1/wbes/{wbe_id}", params={"control_date": control_date}
    )
    assert response.status_code == 204

    # 3. Verify deletion happened effectively at control_date
    # Query BEFORE control date - should still exist
    before_date = "2026-04-30T10:00:00+00:00"
    resp_before = await client.get(
        f"/api/v1/wbes/{wbe_id}", params={"as_of": before_date}
    )
    assert resp_before.status_code == 200

    # Query AFTER control date - should be gone
    after_date = "2026-05-02T10:00:00+00:00"
    resp_after = await client.get(
        f"/api/v1/wbes/{wbe_id}", params={"as_of": after_date}
    )
    assert resp_after.status_code == 404


@pytest.mark.asyncio
async def test_wbe_level_inference(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test automatic level inference logic."""
    # 1. Create root WBE (no parent) -> Should be Level 1
    root_data = {
        "project_id": test_project["project_id"],
        "code": "L1",
        "name": "Level 1 WBE",
        "budget_allocation": 100000,
        # note: no level provided
    }
    root_resp = await client.post("/api/v1/wbes", json=root_data)
    # assert root_resp.status_code == 201
    if root_resp.status_code != 201:
        print(root_resp.json())
    assert root_resp.status_code == 201
    root_wbe = root_resp.json()
    assert root_wbe["level"] == 1
    root_id = root_wbe["wbe_id"]

    # 2. Create child WBE (parent = root) -> Should be Level 2
    child_data = {
        "project_id": test_project["project_id"],
        "code": "L2",
        "name": "Level 2 WBE",
        "budget_allocation": 50000,
        "parent_wbe_id": root_id,
        # note: no level provided
    }
    child_resp = await client.post("/api/v1/wbes", json=child_data)
    assert child_resp.status_code == 201
    child_wbe = child_resp.json()
    assert child_wbe["level"] == 2
    assert child_wbe["parent_wbe_id"] == root_id
    child_id = child_wbe["wbe_id"]

    # 3. Create sub-child WBE (parent = child) -> Should be Level 3
    sub_child_data = {
        "project_id": test_project["project_id"],
        "code": "L3",
        "name": "Level 3 WBE",
        "budget_allocation": 25000,
        "parent_wbe_id": child_id,
    }
    sub_resp = await client.post("/api/v1/wbes", json=sub_child_data)
    assert sub_resp.status_code == 201
    sub_wbe = sub_resp.json()
    assert sub_wbe["level"] == 3
    sub_id = sub_wbe["wbe_id"]

    # 4. Update child to be root (remove parent) -> Should likely become Level 1
    update_to_root = {"parent_wbe_id": None}
    update_resp = await client.put(f"/api/v1/wbes/{sub_id}", json=update_to_root)
    assert update_resp.status_code == 200
    updated_sub = update_resp.json()
    assert updated_sub["level"] == 1
    assert updated_sub["parent_wbe_id"] is None

    # 5. Update root to be child of another (move) -> Should adopt new level
    new_root_data = {
        "project_id": test_project["project_id"],
        "code": "L1-New",
        "name": "New Root",
        "budget_allocation": 100000,
    }
    new_root_resp = await client.post("/api/v1/wbes", json=new_root_data)
    new_root_id = new_root_resp.json()["wbe_id"]

    # Move our previous L3 (now L1) under New Root
    update_move = {"parent_wbe_id": new_root_id}
    move_resp = await client.put(f"/api/v1/wbes/{sub_id}", json=update_move)
    assert move_resp.status_code == 200
    moved_wbe = move_resp.json()
    assert moved_wbe["level"] == 2
    assert moved_wbe["parent_wbe_id"] == new_root_id


@pytest.mark.asyncio
async def test_get_wbes_param_filter(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test filtering by parent_wbe_id parameter."""
    # Create Root WBE
    root_data = {
        "project_id": test_project["project_id"],
        "code": "TF-1",
        "name": "Root",
        "budget_allocation": 100,
    }
    root_resp = await client.post("/api/v1/wbes", json=root_data)
    root_id = root_resp.json()["wbe_id"]

    # Create Child WBE
    child_data = {
        "project_id": test_project["project_id"],
        "code": "TF-1.1",
        "name": "Child",
        "budget_allocation": 50,
        "parent_wbe_id": root_id,
    }
    await client.post("/api/v1/wbes", json=child_data)

    # 1. Test "null" filter (Root only)
    resp_null = await client.get(
        "/api/v1/wbes",
        params={"project_id": test_project["project_id"], "parent_wbe_id": "null"},
    )
    assert resp_null.status_code == 200
    # Hierarchical filter (including "null" for root) returns list directly
    data_null = resp_null.json()
    # Should contain Root, should NOT contain Child
    assert any(w["code"] == "TF-1" for w in data_null)
    assert not any(w["code"] == "TF-1.1" for w in data_null)

    # 2. Test Specific ID filter
    resp_specific = await client.get(
        "/api/v1/wbes",
        params={
            "project_id": test_project["project_id"],
            "parent_wbe_id": str(root_id),
        },
    )
    assert resp_specific.status_code == 200
    # Hierarchical filter returns list directly, not PaginatedResponse
    data_specific = resp_specific.json()
    # Should contain Child, should NOT contain Root
    assert any(w["code"] == "TF-1.1" for w in data_specific)
    assert not any(w["code"] == "TF-1" for w in data_specific)

    # 3. Test No Filter (All)
    resp_all = await client.get(
        "/api/v1/wbes", params={"project_id": test_project["project_id"]}
    )
    assert resp_all.status_code == 200
    data_all = resp_all.json()["items"]
    # Should contain BOTH if pagination allows
    codes = [w["code"] for w in data_all]
    assert "TF-1" in codes
    assert "TF-1.1" in codes
