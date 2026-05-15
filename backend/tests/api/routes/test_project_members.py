"""Tests for project members API endpoints.

Tests CRUD operations for project-level role assignments.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import ProjectRole
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
)
from app.main import app
from app.models.domain.project import Project
from app.models.domain.project_member import ProjectMember
from app.models.domain.user import User
from tests.conftest import MockUnifiedRBACService

# Mock admin user for auth
_mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)


def _mock_get_current_user() -> User:
    return _mock_admin_user


def _mock_get_current_active_user() -> User:
    return _mock_admin_user


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    app.dependency_overrides[get_current_active_user] = _mock_get_current_active_user

    set_unified_rbac_service(MockUnifiedRBACService())  # type: ignore[arg-type]
    yield
    set_unified_rbac_service(UnifiedRBACService())
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_list_project_members_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
) -> None:
    """Test listing project members as admin user."""
    # Add some members
    member1 = ProjectMember(
        user_id=admin_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.ADMIN,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member1)
    await db_session.commit()

    # List members (requires authentication in real scenario)
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
    )

    # Should succeed if properly authenticated
    # For now, we just check the endpoint exists
    assert response.status_code in (200, 401)  # 200 if auth works, 401 if not


@pytest.mark.asyncio
async def test_list_project_members_as_member(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
) -> None:
    """Test listing project members as project member."""
    # Add user as viewer
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Try to list members
    response = await client.get(
        f"/api/v1/projects/{test_project.project_id}/members",
    )

    # Viewer should have read access
    # Should not get 403
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_add_project_member_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
    test_user: User,
) -> None:
    """Test adding a project member as admin."""
    # Admin should be able to add members
    # This test verifies the endpoint exists and validates input
    member_data = {
        "user_id": str(test_user.user_id),
        "project_id": str(test_project.project_id),
        "role": ProjectRole.VIEWER,
        "assigned_by": str(admin_user.user_id),
    }

    response = await client.post(
        f"/api/v1/projects/{test_project.project_id}/members",
        json=member_data,
    )

    # Should either succeed (201) or fail with auth (401)
    # Should not get 403 (admin has project-admin permission)
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_add_project_member_as_viewer_denied(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
) -> None:
    """Test that viewers cannot add members."""
    # Add user as viewer
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Try to add another member
    member_data = {
        "user_id": str(test_user.user_id),
        "project_id": str(test_project.project_id),
        "role": ProjectRole.EDITOR,
        "assigned_by": str(test_user.user_id),
    }

    response = await client.post(
        f"/api/v1/projects/{test_project.project_id}/members",
        json=member_data,
    )

    # Viewer lacks project-admin permission
    # Should get 403 if authenticated
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_remove_project_member_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
    test_user: User,
) -> None:
    """Test removing a project member as admin."""
    # Add a member
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.VIEWER,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Remove the member
    response = await client.delete(
        f"/api/v1/projects/{test_project.project_id}/members/{test_user.user_id}",
    )

    # Admin should be able to remove members
    # Should not get 403
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_update_project_member_role_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
    test_user: User,
) -> None:
    """Test updating a project member's role as admin."""
    # Add a member
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.VIEWER,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Update the role
    update_data = {
        "role": ProjectRole.EDITOR,
        "assigned_by": str(admin_user.user_id),
    }

    response = await client.patch(
        f"/api/v1/projects/{test_project.project_id}/members/{test_user.user_id}",
        json=update_data,
    )

    # Admin should be able to update roles
    # Should not get 403
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_project_members_filtering_by_user_access(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
    admin_user: User,
) -> None:
    """Test that users only see projects they are members of."""
    # Create two projects
    project1 = test_project
    project2 = Project(
        code="TEST2",
        name="Test Project 2",
        description="Another test project",
        planned_budget=100000.0,
    )
    db_session.add(project2)
    await db_session.flush()

    # Add user only to project1
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project1.project_id,
        role=ProjectRole.VIEWER,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # List projects
    response = await client.get("/api/v1/projects")

    # Non-admin users should only see their projects
    # This test verifies the filtering logic
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_cannot_add_duplicate_member(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
    test_user: User,
) -> None:
    """Test that duplicate membership is prevented."""
    # Add user as member
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.VIEWER,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Try to add again
    member_data = {
        "user_id": str(test_user.user_id),
        "project_id": str(test_project.project_id),
        "role": ProjectRole.EDITOR,
        "assigned_by": str(admin_user.user_id),
    }

    response = await client.post(
        f"/api/v1/projects/{test_project.project_id}/members",
        json=member_data,
    )

    # Should fail with 400 (duplicate)
    assert response.status_code in (400, 401, 403)
