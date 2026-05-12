"""Integration test for /auth/me endpoint with real database.

This test verifies that admin users get their permissions populated correctly.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_me_returns_admin_permissions(async_client: AsyncClient) -> None:
    """Test that /auth/me returns populated permissions for admin users."""
    # Login as admin
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@backcast.org", "password": "admin123"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    access_token = token_data["access_token"]

    # Get /auth/me endpoint
    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200

    user_data = me_response.json()

    # Verify user data
    assert user_data["email"] == "admin@backcast.org"
    assert user_data["role"] == "admin"
    assert user_data["is_active"] is True

    # CRITICAL: Verify permissions array is NOT empty
    assert "permissions" in user_data
    assert isinstance(user_data["permissions"], list)

    # Admin should have many permissions, not an empty array
    assert len(user_data["permissions"]) > 0, "Admin user should have permissions!"

    # Verify some expected admin permissions are present
    expected_permissions = [
        "user-read",
        "user-create",
        "user-update",
        "user-delete",
        "project-read",
        "project-create",
        "change-order-read",
        "change-order-create",
        "change-order-approve",
    ]

    for perm in expected_permissions:
        assert perm in user_data["permissions"], f"Admin should have {perm} permission"

    print(f"✓ Admin user has {len(user_data['permissions'])} permissions")


@pytest.mark.asyncio
async def test_auth_me_viewer_permissions(async_client: AsyncClient) -> None:
    """Test that /auth/me returns correct permissions for viewer users."""
    # Login as viewer (assuming user exists from seeding)
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "viewer@backcast.org", "password": "viewer123"},
    )
    # Viewer might not exist in test DB, so skip if login fails
    if login_response.status_code != 200:
        pytest.skip("Viewer user not found in test database")

    token_data = login_response.json()
    access_token = token_data["access_token"]

    # Get /auth/me endpoint
    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200

    user_data = me_response.json()

    # Verify user data
    assert user_data["role"] == "viewer"
    assert len(user_data["permissions"]) > 0, "Viewer user should have permissions!"

    # Verify viewer has read-only permissions
    assert "project-read" in user_data["permissions"]
    assert "department-read" in user_data["permissions"]

    # Viewer should NOT have write permissions
    assert "user-delete" not in user_data["permissions"]
    assert "project-delete" not in user_data["permissions"]

    print(f"✓ Viewer user has {len(user_data['permissions'])} permissions")
