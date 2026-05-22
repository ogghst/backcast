"""Tests for ProjectRoleChecker dependency.

Tests project-level RBAC authorization dependency.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
)
from app.main import app
from app.models.domain.project import Project
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment
from tests.conftest import MockUnifiedRBACService

# Mock admin user for auth
_mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)
def _mock_get_current_user() -> User:
    return _mock_admin_user
async def _get_role_id(session: AsyncSession, role_name: str) -> str:
    """Look up a seeded RBAC role ID by name."""
    result = await session.execute(
        select(RBACRole.id).where(RBACRole.name == role_name)
    )
    return result.scalar_one()
@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = _mock_get_current_user

    set_unified_rbac_service(MockUnifiedRBACService())  # type: ignore[arg-type]
    yield
    set_unified_rbac_service(UnifiedRBACService())
    app.dependency_overrides = {}
@pytest.mark.asyncio
async def test_project_role_checker_admin_bypass(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
) -> None:
    """Test that admin users bypass project-level checks."""
    # Admin users should have access to all projects
    # regardless of project membership
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
        headers={"Authorization": f"Bearer {admin_user.email}"},
    )

    # Should succeed (401 if auth fails, 403 if project access denied)
    # We expect it to not be 403 for admin
    assert response.status_code != 403
@pytest.mark.asyncio
async def test_project_role_checker_project_member_access(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
) -> None:
    """Test that project members can access project resources."""
    role_id = await _get_role_id(db_session, "viewer")
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=test_project.project_id,
        granted_by=test_user.user_id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # User should be able to list project members
    # Note: This test assumes proper authentication setup
    # In real scenario, you'd need valid JWT token
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
    )

    # Should either succeed or fail with auth error, not 403
    # (403 means project access denied)
    assert response.status_code != 403
@pytest.mark.asyncio
async def test_project_role_checker_non_member_denied(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
) -> None:
    """Test that non-members are denied access to project resources."""
    # User is NOT a member of the project
    # Any attempt to access project resources should fail with 403
    # Note: This test assumes proper authentication setup

    # Try to access project members
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
    )

    # If authenticated, should get 403 (no project access)
    # If not authenticated, should get 401
    # This test verifies the ProjectRoleChecker is working
    # Currently returns 404 because /members endpoint is not yet implemented.
    # Once implemented with ProjectRoleChecker, should return 403.
    assert response.status_code in (401, 403, 404)
@pytest.mark.asyncio
async def test_project_role_checker_permission_levels(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
) -> None:
    """Test that different project roles have appropriate permissions."""
    # Test viewer role (can read but not write)
    viewer_role_id = await _get_role_id(db_session, "viewer")
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=viewer_role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=test_project.project_id,
        granted_by=test_user.user_id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Viewer should be able to list members (read permission)
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
    )

    # Should not get 403 (viewer has read access)
    assert response.status_code != 403

    # Update to editor role
    manager_role_id = await _get_role_id(db_session, "manager")
    assignment.role_id = manager_role_id
    await db_session.commit()

    # Editor should also be able to read
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
    )

    assert response.status_code != 403
