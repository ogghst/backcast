"""Integration tests for Time Machine / Time-Travel functionality."""

import time
from collections.abc import Generator
from datetime import UTC, datetime
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
    """Create a test project for time-travel tests."""
    project_data = {
        "name": "Time Travel Test Project",
        "code": "TT-TEST",
        "budget": 1000000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    return cast(dict[str, Any], response.json())


def format_as_of(dt: datetime) -> str:
    """Format datetime for as_of query parameter."""
    # Use ISO format without microseconds for cleaner URLs
    return dt.replace(microsecond=0).isoformat()


@pytest.mark.asyncio
async def test_wbe_time_travel_basic(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """
    Test basic time-travel: Create WBE at time X, query at time Y < X.

    Scenario:
    1. Record timestamp T1 (before creation)
    2. Create WBE A at time X
    3. Query WBE at time T1 (before creation) - should NOT find WBE A
    4. Query WBE at current time - should find WBE A
    """
    # T1: Record timestamp BEFORE creating WBE
    time_before_creation = datetime.now(UTC)

    # Longer delay to ensure clear temporal separation
    time.sleep(1.0)

    # X: Create WBE A
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "TT-1.0",
        "name": "Time Travel WBE A",
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    assert create_response.status_code == 201
    wbe_a = create_response.json()
    wbe_a_id = wbe_a["wbe_id"]

    # Query at T1 (before creation) - should return 404
    as_of_param = format_as_of(time_before_creation)
    response_before = await client.get(
        f"/api/v1/wbes/{wbe_a_id}", params={"as_of": as_of_param}
    )
    assert response_before.status_code == 404, (
        f"WBE should not exist at time {as_of_param} (before creation). "
        f"Got status {response_before.status_code}"
    )

    # Query at current time - should return 200
    response_current = await client.get(f"/api/v1/wbes/{wbe_a_id}")
    assert response_current.status_code == 200
    current_wbe = response_current.json()
    assert current_wbe["name"] == "Time Travel WBE A"


@pytest.mark.asyncio
async def test_wbe_time_travel_update(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """
    Test time-travel with updates: View WBE at different points in its history.

    Scenario:
    1. Create WBE with name "Version 1" at time T1
    2. Record timestamp T2
    3. Update WBE to name "Version 2" at time T3
    4. Query at T2 - should see "Version 1"
    5. Query at current - should see "Version 2"
    """
    # T1: Create WBE
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "TT-2.0",
        "name": "Version 1",
        "budget_allocation": 100000,
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    assert create_response.status_code == 201
    wbe_id = create_response.json()["wbe_id"]

    # Delay for temporal separation
    time.sleep(1.0)

    # T2: Record timestamp after creation but before update
    time_after_v1 = datetime.now(UTC)

    # Delay for temporal separation
    time.sleep(1.0)

    # T3: Update WBE
    update_data = {"name": "Version 2", "budget_allocation": 150000}
    update_response = await client.put(f"/api/v1/wbes/{wbe_id}", json=update_data)
    assert update_response.status_code == 200

    # Query at T2 - should see Version 1
    as_of_v1 = format_as_of(time_after_v1)
    response_v1 = await client.get(f"/api/v1/wbes/{wbe_id}", params={"as_of": as_of_v1})
    assert response_v1.status_code == 200
    wbe_v1 = response_v1.json()
    assert wbe_v1["name"] == "Version 1"
    assert float(wbe_v1["budget_allocation"]) == 100000.0

    # Query at current - should see Version 2
    response_current = await client.get(f"/api/v1/wbes/{wbe_id}")
    assert response_current.status_code == 200
    wbe_current = response_current.json()
    assert wbe_current["name"] == "Version 2"
    assert float(wbe_current["budget_allocation"]) == 150000.0


@pytest.mark.asyncio
async def test_wbe_time_travel_delete(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """
    Test time-travel with deletion: View deleted WBE at time before deletion.

    Scenario:
    1. Create WBE at time T1
    2. Record timestamp T2
    3. Delete WBE at time T3
    4. Query at T2 - should see WBE (before deletion)
    5. Query at current - should return 404 (after deletion)
    """
    # T1: Create WBE
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "TT-3.0",
        "name": "To Be Deleted",
        "budget_allocation": 75000,
        "level": 1,
    }
    create_response = await client.post("/api/v1/wbes", json=wbe_data)
    assert create_response.status_code == 201
    wbe_id = create_response.json()["wbe_id"]

    # Delay for temporal separation
    time.sleep(1.0)

    # T2: Record timestamp before deletion
    time_before_delete = datetime.now(UTC)

    # Delay for temporal separation
    time.sleep(1.0)

    # T3: Delete WBE
    delete_response = await client.delete(f"/api/v1/wbes/{wbe_id}")
    assert delete_response.status_code == 204

    # Query at T2 (before deletion) - should see WBE
    as_of_before_delete = format_as_of(time_before_delete)
    response_before_delete = await client.get(
        f"/api/v1/wbes/{wbe_id}", params={"as_of": as_of_before_delete}
    )
    assert response_before_delete.status_code == 200
    wbe_before_delete = response_before_delete.json()
    assert wbe_before_delete["name"] == "To Be Deleted"

    # Query at current (after deletion) - should return 404
    response_current = await client.get(f"/api/v1/wbes/{wbe_id}")
    assert response_current.status_code == 404


@pytest.mark.asyncio
async def test_project_time_travel(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
) -> None:
    """
    Test time-travel for projects.

    Scenario:
    1. Create project with budget 500k at T1
    2. Record timestamp T2
    3. Update project to budget 750k at T3
    4. Query at T2 - should see 500k
    5. Query at current - should see 750k
    """
    # T1: Create project
    project_data = {
        "name": "Time Travel Project",
        "code": "TT-PROJ",
        "budget": 500000,
    }
    create_response = await client.post("/api/v1/projects", json=project_data)
    assert create_response.status_code == 201
    project = create_response.json()
    project_id = project["project_id"]

    # Delay for temporal separation
    time.sleep(1.0)

    # T2: Record timestamp
    time_after_create = datetime.now(UTC)

    # Delay for temporal separation
    time.sleep(1.0)

    # T3: Update project
    update_data = {"budget": 750000}
    update_response = await client.put(
        f"/api/v1/projects/{project_id}", json=update_data
    )
    assert update_response.status_code == 200

    # Query at T2 - should see original budget
    as_of_original = format_as_of(time_after_create)
    response_original = await client.get(
        f"/api/v1/projects/{project_id}", params={"as_of": as_of_original}
    )
    assert response_original.status_code == 200
    project_original = response_original.json()
    assert float(project_original["budget"]) == 500000.0

    # Query at current - should see updated budget
    response_current = await client.get(f"/api/v1/projects/{project_id}")
    assert response_current.status_code == 200
    project_current = response_current.json()
    assert float(project_current["budget"]) == 750000.0


@pytest.mark.asyncio
async def test_multiple_wbes_time_travel(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """
    Test time-travel with multiple WBEs created at different times.

    Scenario:
    1. Create WBE A at time T1
    2. Record timestamp T2
    3. Create WBE B at time T3
    4. Record timestamp T4
    5. Create WBE C at time T5
    6. Query at T2 - should only see WBE A
    7. Query at T4 - should see WBE A and B
    8. Query at current - should see all three
    """
    # T1: Create WBE A
    wbe_a_data = {
        "project_id": test_project["project_id"],
        "code": "TT-A",
        "name": "WBE A",
        "budget_allocation": 10000,
        "level": 1,
    }
    response_a = await client.post("/api/v1/wbes", json=wbe_a_data)
    assert response_a.status_code == 201
    wbe_a_id = response_a.json()["wbe_id"]

    time.sleep(1.0)

    # T2: Record timestamp after A
    time_after_a = datetime.now(UTC)

    time.sleep(1.0)

    # T3: Create WBE B
    wbe_b_data = {
        "project_id": test_project["project_id"],
        "code": "TT-B",
        "name": "WBE B",
        "budget_allocation": 20000,
        "level": 1,
    }
    response_b = await client.post("/api/v1/wbes", json=wbe_b_data)
    assert response_b.status_code == 201
    wbe_b_id = response_b.json()["wbe_id"]

    time.sleep(1.0)

    # T4: Record timestamp after B
    time_after_b = datetime.now(UTC)

    time.sleep(1.0)

    # T5: Create WBE C
    wbe_c_data = {
        "project_id": test_project["project_id"],
        "code": "TT-C",
        "name": "WBE C",
        "budget_allocation": 30000,
        "level": 1,
    }
    response_c = await client.post("/api/v1/wbes", json=wbe_c_data)
    assert response_c.status_code == 201
    wbe_c_id = response_c.json()["wbe_id"]

    # Query WBE A at T2 - should exist
    response_a_at_t2 = await client.get(
        f"/api/v1/wbes/{wbe_a_id}", params={"as_of": format_as_of(time_after_a)}
    )
    assert response_a_at_t2.status_code == 200

    # Query WBE B at T2 - should NOT exist (created later)
    response_b_at_t2 = await client.get(
        f"/api/v1/wbes/{wbe_b_id}", params={"as_of": format_as_of(time_after_a)}
    )
    assert response_b_at_t2.status_code == 404

    # Query WBE B at T4 - should exist
    response_b_at_t4 = await client.get(
        f"/api/v1/wbes/{wbe_b_id}", params={"as_of": format_as_of(time_after_b)}
    )
    assert response_b_at_t4.status_code == 200

    # Query WBE C at T4 - should NOT exist (created later)
    response_c_at_t4 = await client.get(
        f"/api/v1/wbes/{wbe_c_id}", params={"as_of": format_as_of(time_after_b)}
    )
    assert response_c_at_t4.status_code == 404

    # Query all at current - should all exist
    response_a_current = await client.get(f"/api/v1/wbes/{wbe_a_id}")
    response_b_current = await client.get(f"/api/v1/wbes/{wbe_b_id}")
    response_c_current = await client.get(f"/api/v1/wbes/{wbe_c_id}")

    assert response_a_current.status_code == 200
    assert response_b_current.status_code == 200
    assert response_c_current.status_code == 200
