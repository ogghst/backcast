"""Integration test for /auth/me endpoint with real database.

This test verifies that admin users get their permissions populated correctly.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_unified import UnifiedRBACService, set_unified_rbac_service
from app.core.security import get_password_hash
from app.models.domain.user import User


async def _create_test_user(
    session: AsyncSession,
    email: str,
    role: str,
    password: str,
) -> User:
    """Create a user row directly in the database for testing."""
    from sqlalchemy import select

    from app.models.domain.rbac import RBACRole
    from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment

    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email=email,
        full_name=f"{role.title()} User",
        is_active=True,
        hashed_password=get_password_hash(password),
        created_by=uuid4(),
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    result = await session.execute(select(RBACRole.id).where(RBACRole.name == role))
    role_id = result.scalar_one_or_none()
    if role_id:
        assignment = UserRoleAssignment(
            id=uuid4(),
            user_id=user.user_id,
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
            role_id=role_id,
            granted_by=user.user_id,
        )
        session.add(assignment)
        await session.flush()
    return user

@pytest.mark.asyncio
async def test_auth_me_returns_admin_permissions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test that /auth/me returns populated permissions for admin users."""
    # Set up unified RBAC service and seed its permission cache
    rbac_service = UnifiedRBACService()
    set_unified_rbac_service(rbac_service)
    await rbac_service.refresh_permissions_cache()

    # Create a test admin user directly in the database
    await _create_test_user(
        db_session, "admin@backcast.org", "admin", "admin123"
    )
    await db_session.commit()

    # Login as admin
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@backcast.org", "password": "admin123"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    access_token = token_data["access_token"]

    # Get /auth/me endpoint
    me_response = await client.get(
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

@pytest.mark.asyncio
async def test_auth_me_viewer_permissions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test that /auth/me returns correct permissions for viewer users."""
    # Set up unified RBAC service and seed its permission cache
    rbac_service = UnifiedRBACService()
    set_unified_rbac_service(rbac_service)
    await rbac_service.refresh_permissions_cache()

    # Create a test viewer user directly in the database
    await _create_test_user(
        db_session, "viewer@backcast.org", "viewer", "viewer123"
    )
    await db_session.commit()

    # Login as viewer
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "viewer@backcast.org", "password": "viewer123"},
    )
    assert login_response.status_code == 200

    token_data = login_response.json()
    access_token = token_data["access_token"]

    # Get /auth/me endpoint
    me_response = await client.get(
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
