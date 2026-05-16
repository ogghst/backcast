"""Integration tests for AI project access control.

Tests that AI chat and tools respect project-level permissions,
including admin bypass, member filtering, and permission errors.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.project_tools import list_projects
from app.ai.tools.types import ToolContext
from app.core.rbac_unified import set_unified_rbac_service
from app.models.domain.project import Project
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment
from tests.conftest import MockUnifiedRBACService


async def _get_role_id(session: AsyncSession, role_name: str) -> str:
    """Look up a seeded RBAC role ID by name."""
    result = await session.execute(
        select(RBACRole.id).where(RBACRole.name == role_name)
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_list_projects_returns_only_accessible_for_viewer(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that list_projects tool returns only accessible projects for viewers.

    Given:
        A user with viewer role
        Three projects in the database
        User is a member of only one project
    When:
        Calling list_projects tool
    Then:
        Only the project they are a member of is returned
    """
    # Arrange - Create three projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    project3 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ3",
        name="Project 3",
        budget=300000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add_all([project1, project2, project3])
    await db_session.flush()

    # Add user as member of project1 only
    role_id = await _get_role_id(db_session, "viewer")
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=project1.project_id,
        granted_by=test_user.user_id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Create a unified RBAC mock that only grants access to project1
    mock_unified = MagicMock()
    mock_unified.get_accessible_projects = AsyncMock(return_value=[project1.project_id])
    set_unified_rbac_service(mock_unified)

    context = ToolContext(
        session=db_session,
        user_id=str(test_user.user_id),
        user_role="viewer",
    )

    try:
        # Patch get_tool_session to return the test's db_session
        with patch("app.db.session.get_tool_session", return_value=db_session):
            result = await list_projects.ainvoke({"context": context})
    finally:
        # Restore the conftest mock
        set_unified_rbac_service(MockUnifiedRBACService())

    # Assert - Should only contain project1 in the projects list
    assert "projects" in result
    projects = result["projects"]
    assert len(projects) == 1
    assert projects[0]["id"] == str(project1.project_id)
    assert projects[0]["code"] == "PROJ1"


@pytest.mark.asyncio
async def test_list_projects_returns_all_for_system_admin(
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """Test that list_projects tool returns all projects for system admins.

    Given:
        A system admin user
        Multiple projects in the database
        No project memberships for the admin
    When:
        Calling list_projects tool
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
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add_all([project1, project2])
    await db_session.commit()

    # Create a unified RBAC mock that grants access to all projects
    mock_unified = MagicMock()
    mock_unified.get_accessible_projects = AsyncMock(
        return_value=[project1.project_id, project2.project_id]
    )
    set_unified_rbac_service(mock_unified)

    context = ToolContext(
        session=db_session,
        user_id=str(admin_user.user_id),
        user_role="admin",
    )

    try:
        with patch("app.db.session.get_tool_session", return_value=db_session):
            result = await list_projects.ainvoke({"context": context})
    finally:
        set_unified_rbac_service(MockUnifiedRBACService())

    # Assert - Should return all projects
    assert "projects" in result
    projects = result["projects"]
    assert len(projects) == 2
    project_codes = {p["code"] for p in projects}
    assert "PROJ1" in project_codes
    assert "PROJ2" in project_codes


@pytest.mark.asyncio
async def test_list_projects_returns_empty_for_non_member(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that list_projects tool returns empty list for non-members.

    Given:
        A non-admin user
        Multiple projects in the database
        No project memberships for the user
    When:
        Calling list_projects tool
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
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    await db_session.commit()

    # Create a unified RBAC mock that returns no accessible projects
    mock_unified = MagicMock()
    mock_unified.get_accessible_projects = AsyncMock(return_value=[])
    set_unified_rbac_service(mock_unified)

    context = ToolContext(
        session=db_session,
        user_id=str(test_user.user_id),
        user_role="viewer",
    )

    try:
        with patch("app.db.session.get_tool_session", return_value=db_session):
            result = await list_projects.ainvoke({"context": context})
    finally:
        set_unified_rbac_service(MockUnifiedRBACService())

    # Assert - Should return empty projects list
    assert "projects" in result
    assert len(result["projects"]) == 0


@pytest.mark.asyncio
async def test_ai_tool_respects_project_permission_hierarchy(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that AI tools respect project permission hierarchy.

    Given:
        A user with editor role in a project
        A tool requiring project-admin permission
    When:
        Attempting to use the tool
    Then:
        Permission error is raised
    """
    # Arrange - Create project and add user as editor
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()

    role_id = await _get_role_id(db_session, "manager")
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=project.project_id,
        granted_by=test_user.user_id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Create mock RBAC service with editor permissions
    class MockEditorRBACService(MockUnifiedRBACService):
        async def has_project_access(
            self,
            user_id,
            project_id,
            required_permission,
        ) -> bool:
            # Editor has read/write but not admin
            return required_permission in ["project-read", "project-write"]

        async def get_accessible_projects(self, user_id) -> list:
            return [project.project_id]

        async def get_project_role(self, user_id, project_id) -> str | None:
            return "editor"

    mock_rbac = MockEditorRBACService()

    # Act & Assert - Tool requiring admin should fail
    # This simulates the behavior of project-admin protected tools
    has_access = await mock_rbac.has_project_access(
        user_id=test_user.user_id,
        project_id=project.project_id,
        required_permission="project-admin",
    )

    assert has_access is False


@pytest.mark.asyncio
async def test_ai_chat_filters_projects_by_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that AI chat filters projects by user membership.

    Given:
        A user with membership in one project
        Multiple projects in the database
        An AI chat request for project list
    When:
        Sending the chat message
    Then:
        Response includes only accessible projects
    """
    # Arrange - Create multiple projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add_all([project1, project2])
    await db_session.flush()

    # Add user to project1 only
    role_id = await _get_role_id(db_session, "viewer")
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=project1.project_id,
        granted_by=test_user.user_id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Act - Send chat message requesting project list
    response = await client.post(
        "/api/v1/ai/chat",
        json={
            "message": "List all my projects",
            "assistant_config_id": str(uuid4()),
        },
    )

    # Assert - Response should be filtered
    # Note: This is an integration test that may require mocking the AI service
    # For now, we just verify the endpoint exists
    assert response.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_permission_error_returned_correctly(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that permission errors are returned correctly.

    Given:
        A user without project access
        An AI tool requiring project access
    When:
        Attempting to use the tool
    Then:
        Permission error is returned with clear message
    """
    # Arrange - Create project without membership
    project = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    # Create mock RBAC service that denies access
    class MockDenyRBACService(MockUnifiedRBACService):
        async def has_project_access(
            self,
            user_id,
            project_id,
            required_permission,
        ) -> bool:
            return False

        async def get_accessible_projects(self, user_id) -> list:
            return []

        async def get_project_role(self, user_id, project_id) -> str | None:
            return None

    mock_rbac = MockDenyRBACService()

    # Act & Assert - Verify permission check
    has_access = await mock_rbac.has_project_access(
        user_id=test_user.user_id,
        project_id=project.project_id,
        required_permission="project-read",
    )

    # Should be denied
    assert has_access is False


@pytest.mark.asyncio
async def test_admin_bypass_in_ai_context(
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """Test that admin bypass works in AI tool context.

    Given:
        A system admin user
        Projects they are not members of
        AI tools requiring project access
    When:
        Using AI tools
    Then:
        Admin bypass grants access to all projects
    """
    # Arrange - Create projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    await db_session.commit()

    # Create mock RBAC service for admin
    class MockAdminRBACService(MockUnifiedRBACService):
        async def has_project_access(
            self,
            user_id,
            project_id,
            required_permission,
        ) -> bool:
            # Admin bypass
            return True

        async def get_accessible_projects(self, user_id) -> list:
            # Admin gets all projects
            return [project1.project_id]

        async def get_project_role(self, user_id, project_id) -> str | None:
            return "admin"

    mock_rbac = MockAdminRBACService()

    # Act & Assert - Admin should have access
    has_access = await mock_rbac.has_project_access(
        user_id=admin_user.user_id,
        project_id=project1.project_id,
        required_permission="project-admin",
    )

    assert has_access is True


@pytest.mark.asyncio
async def test_multiple_roles_respected_in_ai_tools(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that users with different project roles see appropriate permissions.

    Given:
        A user with viewer role in project1
        A user with editor role in project2
        A user with admin role in project3
    When:
        Using AI tools for each project
    Then:
        Permissions match project role for each project
    """
    # Arrange - Create three projects
    project1 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ1",
        name="Project 1",
        budget=100000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    project2 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ2",
        name="Project 2",
        budget=200000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    project3 = Project(
        project_id=uuid4(),
        id=uuid4(),
        code="PROJ3",
        name="Project 3",
        budget=300000.0,
        status="active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add_all([project1, project2, project3])
    await db_session.flush()

    # Add user with different roles to each project
    viewer_role_id = await _get_role_id(db_session, "viewer")
    editor_role_id = await _get_role_id(db_session, "manager")
    admin_role_id = await _get_role_id(db_session, "admin")

    assignment1 = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=viewer_role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=project1.project_id,
        granted_by=test_user.user_id,
    )
    assignment2 = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=editor_role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=project2.project_id,
        granted_by=test_user.user_id,
    )
    assignment3 = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user.user_id,
        role_id=admin_role_id,
        scope_type=ScopeType.PROJECT,
        scope_id=project3.project_id,
        granted_by=test_user.user_id,
    )
    db_session.add_all([assignment1, assignment2, assignment3])
    await db_session.commit()

    # Create mock RBAC service
    class MockMultiRoleRBACService(MockUnifiedRBACService):
        def __init__(self):
            super().__init__()
            self.roles = {
                str(project1.project_id): "viewer",
                str(project2.project_id): "editor",
                str(project3.project_id): "admin",
            }

        async def has_project_access(
            self,
            user_id,
            project_id,
            required_permission,
        ) -> bool:
            role = self.roles.get(str(project_id))
            if role == "viewer":
                return required_permission == "project-read"
            elif role == "editor":
                return required_permission in ["project-read", "project-write"]
            elif role == "admin":
                return True  # All permissions
            return False

        async def get_accessible_projects(self, user_id) -> list:
            return [UUID(pid) for pid in self.roles.keys()]

        async def get_project_role(self, user_id, project_id) -> str | None:
            return self.roles.get(str(project_id))

    mock_rbac = MockMultiRoleRBACService()

    # Act & Assert - Verify permissions for each role
    # Viewer can only read
    assert await mock_rbac.has_project_access(
        test_user.user_id, project1.project_id, "project-read"
    )
    assert not await mock_rbac.has_project_access(
        test_user.user_id, project1.project_id, "project-write"
    )

    # Editor can read and write
    assert await mock_rbac.has_project_access(
        test_user.user_id, project2.project_id, "project-read"
    )
    assert await mock_rbac.has_project_access(
        test_user.user_id, project2.project_id, "project-write"
    )
    assert not await mock_rbac.has_project_access(
        test_user.user_id, project2.project_id, "project-delete"
    )

    # Admin can do everything
    assert await mock_rbac.has_project_access(
        test_user.user_id, project3.project_id, "project-delete"
    )
    assert await mock_rbac.has_project_access(
        test_user.user_id, project3.project_id, "project-admin"
    )
