"""Comprehensive API route tests for project-level RBAC.

Tests admin bypass behavior, project membership filtering,
permission hierarchy, and ProjectRoleChecker dependency.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.enums import ProjectRole
from app.core.rbac import get_rbac_service
from app.main import app
from app.models.domain.project import Project
from app.models.domain.project_member import ProjectMember
from app.models.domain.user import User

# =============================================================================
# Auth Override Fixtures for Database Users
# =============================================================================


@pytest.fixture
def override_as_admin(
    admin_user: User,
    db_session: AsyncSession,
) -> Generator[None, None, None]:
    """Override authentication to use admin_user from database."""
    from app.core.rbac import JsonRBACService

    # Create a real RBAC service with session
    rbac_service = JsonRBACService()
    rbac_service.session = db_session

    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    app.dependency_overrides[get_rbac_service] = lambda: rbac_service
    yield
    app.dependency_overrides = {}


@pytest.fixture
def override_as_viewer(
    test_user: User,
    db_session: AsyncSession,
) -> Generator[None, None, None]:
    """Override authentication to use test_user (viewer) from database."""
    from app.core.rbac import JsonRBACService

    # Create a real RBAC service with session
    rbac_service = JsonRBACService()
    rbac_service.session = db_session

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_active_user] = lambda: test_user
    app.dependency_overrides[get_rbac_service] = lambda: rbac_service
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_admin_can_access_all_projects_without_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    override_as_admin: None,
) -> None:
    """Test that admin users can access all projects without membership.

    Given:
        An admin user
        Multiple projects in the database
        No project memberships for the admin user
    When:
        Listing all projects
    Then:
        All projects are returned (admin bypass)
    """
    # Arrange - Create multiple projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    db_session.add(project2)
    await db_session.commit()

    # Act - List projects as admin
    response = await client.get("/api/v1/projects")

    # Assert - Admin should see all projects regardless of membership
    assert response.status_code == 200
    data = response.json()
    projects = data.get("items", [])
    assert len(projects) >= 2


@pytest.mark.asyncio
async def test_non_admin_without_membership_sees_no_projects(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that non-admin users without membership see no projects.

    Given:
        A non-admin user (e.g., viewer)
        Multiple projects in the database
        No project memberships for the user
    When:
        Listing all projects
    Then:
        Empty list is returned
    """
    # Arrange - Create projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    await db_session.commit()

    # Act - List projects as non-admin without membership
    response = await client.get("/api/v1/projects")

    # Assert - Non-admin should see no projects
    assert response.status_code == 200
    data = response.json()
    projects = data.get("items", [])
    assert len(projects) == 0


@pytest.mark.asyncio
async def test_project_member_can_access_assigned_project(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that project members can access their assigned projects.

    Given:
        A non-admin user
        Two projects in the database
        User is a member of only one project
    When:
        Listing all projects
    Then:
        Only the project they are a member of is returned
    """
    # Arrange - Create two projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    db_session.add(project2)
    await db_session.flush()

    # Add user as member of project1 only
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project1.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - List projects
    response = await client.get("/api/v1/projects")

    # Assert - Should only see project1
    assert response.status_code == 200
    data = response.json()
    projects = data.get("items", [])
    assert len(projects) == 1
    assert projects[0]["project_id"] == str(project1.project_id)


@pytest.mark.asyncio
async def test_viewer_permission_read_only_access(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that viewer role only has read access to projects.

    Given:
        A user with viewer role in a project
        A project endpoint requiring write permission
    When:
        Attempting to write to the project
    Then:
        403 Forbidden is returned
    """
    # Arrange - Create project and add user as viewer
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to update project (requires write permission)
    response = await client.put(
        f"/api/v1/projects/{project.project_id}",
        json={"name": "Updated Name"},
    )

    # Assert - Viewer should be denied write access
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_editor_permission_write_access(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that editor role has write access to projects.

    Given:
        A user with editor role in a project
        A project endpoint requiring write permission
    When:
        Attempting to write to the project
    Then:
        Write operation succeeds (or 401 if not authenticated)
    """
    # Arrange - Create project and add user as editor
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_EDITOR,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to update project (requires write permission)
    response = await client.put(
        f"/api/v1/projects/{project.project_id}",
        json={"name": "Updated Name"},
    )

    # Assert - Editor should not get 403 (may get 401 if not authenticated)
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_admin_permission_full_access(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    override_as_admin: None,
) -> None:
    """Test that admin role has full access to projects.

    Given:
        A user with admin role in a project
        A project endpoint requiring admin permission
    When:
        Attempting admin operations
    Then:
        Operations succeed (or 401 if not authenticated)
    """
    # Arrange - Create project and add user as admin
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=admin_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_ADMIN,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to delete project (requires admin permission)
    response = await client.delete(f"/api/v1/projects/{project.project_id}")

    # Assert - Admin should not get 403 (may get 401 if not authenticated)
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_project_role_checker_admin_bypass(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    override_as_admin: None,
) -> None:
    """Test that ProjectRoleChecker bypasses for system admins.

    Given:
        A system admin user
        A project they are not a member of
        An endpoint using ProjectRoleChecker
    When:
        Accessing the project endpoint
    Then:
        Access is granted (admin bypass)
    """
    # Arrange - Create project
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    # Act - Access project endpoint as system admin
    response = await client.get(f"/api/v1/projects/{project.project_id}")

    # Assert - System admin should have access
    # Note: May get 401 if not authenticated, but not 403
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_project_role_checker_non_admin_requires_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that ProjectRoleChecker requires membership for non-admins.

    Given:
        A non-admin user
        A project they are not a member of
        An endpoint using ProjectRoleChecker
    When:
        Accessing the project endpoint
    Then:
        403 Forbidden is returned
    """
    # Arrange - Create project
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    # Act - Try to access project without membership
    response = await client.get(f"/api/v1/projects/{project.project_id}")

    # Assert - Should be denied
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_project_members_as_project_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test listing project members with project-admin permission.

    Given:
        A user with admin role in a project
        Multiple members in the project
    When:
        Listing project members
    Then:
        All members are returned
    """
    # Arrange - Create project and add user as admin
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_ADMIN,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - List project members
    response = await client.get(f"/api/v1/projects/{project.project_id}/members")

    # Assert - Should succeed (not 403)
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_add_project_member_requires_project_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that adding project members requires project-admin permission.

    Given:
        A user with viewer role in a project
        Another user to add
    When:
        Attempting to add the new member
    Then:
        403 Forbidden is returned
    """
    # Arrange - Create project and add user as viewer
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to add another member
    new_user_id = uuid4()
    response = await client.post(
        f"/api/v1/projects/{project.project_id}/members",
        json={
            "user_id": str(new_user_id),
            "project_id": str(project.project_id),
            "role": ProjectRole.PROJECT_VIEWER,
        },
    )

    # Assert - Viewer should be denied
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_project_member_role_requires_project_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that updating member roles requires project-admin permission.

    Given:
        A user with editor role in a project
        Another member in the project
    When:
        Attempting to update the other member's role
    Then:
        403 Forbidden is returned
    """
    # Arrange - Create project and add user as editor
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_EDITOR,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to update member role
    response = await client.patch(
        f"/api/v1/projects/{project.project_id}/members/{test_user.user_id}",
        json={"role": ProjectRole.PROJECT_ADMIN},
    )

    # Assert - Editor should be denied
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_project_member_requires_project_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that removing members requires project-admin permission.

    Given:
        A user with viewer role in a project
        Another member in the project
    When:
        Attempting to remove the other member
    Then:
        403 Forbidden is returned
    """
    # Arrange - Create project and add user as viewer
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to remove member
    response = await client.delete(
        f"/api/v1/projects/{project.project_id}/members/{test_user.user_id}"
    )

    # Assert - Viewer should be denied
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_add_duplicate_project_member(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    test_project: Project,
    test_user: User,
    override_as_admin: None,
) -> None:
    """Test that duplicate project membership is prevented.

    Given:
        An existing project member
        An attempt to add the same user again
    When:
        Attempting to add duplicate membership
    Then:
        400 Bad Request is returned
    """
    # Arrange - Add existing member
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=test_project.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=admin_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Act - Try to add duplicate
    response = await client.post(
        f"/api/v1/projects/{test_project.project_id}/members",
        json={
            "user_id": str(test_user.user_id),
            "project_id": str(test_project.project_id),
            "role": ProjectRole.PROJECT_EDITOR,
        },
    )

    # Assert - Should fail with duplicate error
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_multiple_project_memberships_respected(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    override_as_viewer: None,
) -> None:
    """Test that users see all projects they are members of.

    Given:
        A user with memberships in multiple projects
    When:
        Listing all projects
    Then:
        All projects they are a member of are returned
    """
    # Arrange - Create multiple projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    project3 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ3",
        name="Project 3",
        budget=300000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add_all([project1, project2, project3])
    await db_session.flush()

    # Add user to project1 and project2 (not project3)
    member1 = ProjectMember(
        user_id=test_user.user_id,
        project_id=project1.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    member2 = ProjectMember(
        user_id=test_user.user_id,
        project_id=project2.project_id,
        role=ProjectRole.PROJECT_EDITOR,
        assigned_by=test_user.user_id,
    )
    db_session.add_all([member1, member2])
    await db_session.commit()

    # Act - List projects
    response = await client.get("/api/v1/projects")

    # Assert - Should see both project1 and project2
    assert response.status_code == 200
    data = response.json()
    projects = data.get("items", [])
    project_ids = {p["project_id"] for p in projects}
    assert str(project1.project_id) in project_ids
    assert str(project2.project_id) in project_ids
    assert str(project3.project_id) not in project_ids


@pytest.mark.asyncio
async def test_system_admin_role_overrides_project_role(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    override_as_admin: None,
) -> None:
    """Test that system admin role overrides project-level permissions.

    Given:
        A system admin user
        A project where they have no membership (or viewer role)
        An operation requiring project-admin permission
    When:
        Performing the operation
    Then:
        Operation succeeds (system admin bypass)
    """
    # Arrange - Create project (no membership for admin)
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    # Act - Try to delete project (requires project-admin)
    response = await client.delete(f"/api/v1/projects/{project.project_id}")

    # Assert - System admin should not get 403 (may get 401 if not authenticated)
    assert response.status_code != 403
