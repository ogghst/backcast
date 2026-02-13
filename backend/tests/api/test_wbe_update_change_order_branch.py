"""Test WBE update in change order branches.

This test verifies that when a WBE is updated in a change order branch
where it doesn't exist yet, the system correctly falls back to the main
branch and creates a new version on the change order branch.
"""

from collections.abc import Generator
from typing import Any, cast

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User
from uuid import uuid4


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
        "name": "WBE CO Test Project",
        "code": "WBE-CO-TEST",
        "budget": 500000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_update_wbe_in_change_order_branch_fallback_to_main(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test that updating a WBE in a change order branch falls back to main.

    Scenario:
    1. Create a WBE on main branch
    2. Try to update it on a change order branch (BR-123) where it doesn't exist
    3. Verify the update succeeds and creates a new version on BR-123

    This test validates the fix for the 404 error when updating WBEs in
    change order branches for the first time.
    """
    # Step 1: Create a WBE on main branch
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "1.0",
        "name": "Test WBE",
        "budget_allocation": 10000,
        "level": 1,
    }

    response = await client.post("/api/v1/wbes", json=wbe_data)
    assert response.status_code == 201
    created_wbe = cast(dict[str, Any], response.json())
    assert created_wbe["branch"] == "main"
    assert created_wbe["name"] == "Test WBE"

    # Step 2: Update the WBE in a change order branch where it doesn't exist yet
    wbe_update = {
        "name": "Updated WBE in CO Branch",
        "branch": "BR-123",  # Change order branch
    }

    # This should NOT raise a 404 error
    response = await client.put(
        f"/api/v1/wbes/{created_wbe['wbe_id']}", json=wbe_update
    )

    assert response.status_code == 200
    updated_wbe = cast(dict[str, Any], response.json())

    # Step 3: Verify the update created a new version on BR-123
    assert updated_wbe["wbe_id"] == created_wbe["wbe_id"]
    assert updated_wbe["name"] == "Updated WBE in CO Branch"
    assert updated_wbe["branch"] == "BR-123"  # New version on change order branch
    # Note: parent_id is not returned in the API response

    # Verify we can retrieve the WBE on the BR-123 branch
    response = await client.get(
        f"/api/v1/wbes/{created_wbe['wbe_id']}?branch=BR-123"
    )
    assert response.status_code == 200
    co_version = cast(dict[str, Any], response.json())
    assert co_version["name"] == "Updated WBE in CO Branch"
    assert co_version["branch"] == "BR-123"


@pytest.mark.asyncio
async def test_update_wbe_existing_on_change_order_branch(
    client: AsyncClient,
    override_auth: None,
    db_session: AsyncSession,
    test_project: dict[str, Any],
) -> None:
    """Test that updating a WBE that already exists on a change order branch works normally.

    Scenario:
    1. Create a WBE on main branch
    2. Create a version on BR-123 branch
    3. Update it again on BR-123 branch
    4. Verify it updates the existing BR-123 version
    """
    # Step 1: Create on main
    wbe_data = {
        "project_id": test_project["project_id"],
        "code": "1.0",
        "name": "Original WBE",
        "budget_allocation": 10000,
        "level": 1,
    }

    response = await client.post("/api/v1/wbes", json=wbe_data)
    assert response.status_code == 201
    main_wbe = cast(dict[str, Any], response.json())

    # Step 2: Create a version on BR-123
    wbe_update_first = {
        "name": "First CO Update",
        "branch": "BR-123",
    }

    response = await client.put(
        f"/api/v1/wbes/{main_wbe['wbe_id']}", json=wbe_update_first
    )
    assert response.status_code == 200
    first_co_wbe = cast(dict[str, Any], response.json())
    assert first_co_wbe["branch"] == "BR-123"
    assert first_co_wbe["name"] == "First CO Update"

    # Step 3: Update again on BR-123
    wbe_update_second = {
        "name": "Second CO Update",
        "branch": "BR-123",
    }

    response = await client.put(
        f"/api/v1/wbes/{main_wbe['wbe_id']}", json=wbe_update_second
    )
    assert response.status_code == 200
    second_co_wbe = cast(dict[str, Any], response.json())

    # Step 4: Verify it updated the BR-123 version
    assert second_co_wbe["branch"] == "BR-123"
    assert second_co_wbe["name"] == "Second CO Update"
    # Note: parent_id is not returned in the API response
