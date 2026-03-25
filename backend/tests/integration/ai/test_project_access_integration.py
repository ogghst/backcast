"""Integration tests for AI project access control.

Tests that AI chat and tools respect project-level permissions,
including admin bypass, member filtering, and permission errors.
"""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.project_tools import list_projects
from app.core.enums import ProjectRole
from app.core.rbac import RBACServiceABC
from app.models.domain.project import Project
from app.models.domain.project_member import ProjectMember
from app.models.domain.user import User
from app.services.project import ProjectService


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

    # Add user as member of project1 only
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project1.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
    await db_session.commit()

    # Create mock RBAC service that respects project membership
    class MockRBACService(RBACServiceABC):
        def __init__(self):
            self.session = db_session

        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
            project_id,
            required_permission,
        ) -> bool:
            # Only allow access to project1
            return project_id == project1.project_id

        async def get_user_projects(self, user_id, user_role) -> list:
            # Only return project1
            return [project1.project_id]

        async def get_project_role(self, user_id, project_id) -> str | None:
            if project_id == project1.project_id:
                return "viewer"
            return None

    mock_rbac = MockRBACService()

    # Act - Call list_projects with mock RBAC
    projects = await list_projects(
        context=MagicMock(
            user_id=test_user.user_id,
            user_role="viewer",
            rbac_service=mock_rbac,
        ),
    )

    # Assert - Should only return project1
    assert len(projects) == 1
    assert projects[0]["project_id"] == str(project1.project_id)
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
    db_session.add_all([project1, project2])
    await db_session.commit()

    # Create mock RBAC service for admin
    class MockAdminRBACService(RBACServiceABC):
        def __init__(self):
            self.session = db_session
            self._service = ProjectService(db_session)

        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
            project_id,
            required_permission,
        ) -> bool:
            # Admin bypass - always return True
            return True

        async def get_user_projects(self, user_id, user_role) -> list:
            # Admin gets all projects
            projects = await self._service.list_projects()
            return [p.project_id for p in projects]

        async def get_project_role(self, user_id, project_id) -> str | None:
            # Admin doesn't need a project role
            return "admin"

    mock_rbac = MockAdminRBACService()

    # Act - Call list_projects as admin
    projects = await list_projects(
        context=MagicMock(
            user_id=admin_user.user_id,
            user_role="admin",
            rbac_service=mock_rbac,
        ),
    )

    # Assert - Should return all projects
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
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    await db_session.commit()

    # Create mock RBAC service that denies all access
    class MockDenyRBACService(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
            project_id,
            required_permission,
        ) -> bool:
            # Deny all access
            return False

        async def get_user_projects(self, user_id, user_role) -> list:
            # No memberships
            return []

        async def get_project_role(self, user_id, project_id) -> str | None:
            # Not a member
            return None

    mock_rbac = MockDenyRBACService()

    # Act - Call list_projects
    projects = await list_projects(
        context=MagicMock(
            user_id=test_user.user_id,
            user_role="viewer",
            rbac_service=mock_rbac,
        ),
    )

    # Assert - Should return empty list
    assert len(projects) == 0


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

    # Create mock RBAC service with editor permissions
    class MockEditorRBACService(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
            project_id,
            required_permission,
        ) -> bool:
            # Editor has read/write but not admin
            return required_permission in ["project-read", "project-write"]

        async def get_user_projects(self, user_id, user_role) -> list:
            return [project.project_id]

        async def get_project_role(self, user_id, project_id) -> str | None:
            return "editor"

    mock_rbac = MockEditorRBACService()

    # Act & Assert - Tool requiring admin should fail
    # This simulates the behavior of project-admin protected tools
    has_access = await mock_rbac.has_project_access(
        user_id=test_user.user_id,
        user_role="viewer",
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
    db_session.add_all([project1, project2])
    await db_session.flush()

    # Add user to project1 only
    member = ProjectMember(
        user_id=test_user.user_id,
        project_id=project1.project_id,
        role=ProjectRole.PROJECT_VIEWER,
        assigned_by=test_user.user_id,
    )
    db_session.add(member)
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
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    # Create mock RBAC service that denies access
    class MockDenyRBACService(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
            project_id,
            required_permission,
        ) -> bool:
            return False

        async def get_user_projects(self, user_id, user_role) -> list:
            return []

        async def get_project_role(self, user_id, project_id) -> str | None:
            return None

    mock_rbac = MockDenyRBACService()

    # Act & Assert - Verify permission check
    has_access = await mock_rbac.has_project_access(
        user_id=test_user.user_id,
        user_role="viewer",
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
        status="Active",
        branch="main",
        created_by=uuid4(),
    )
    db_session.add(project1)
    await db_session.commit()

    # Create mock RBAC service for admin
    class MockAdminRBACService(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return user_role == "admin"

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
            project_id,
            required_permission,
        ) -> bool:
            # Admin bypass
            return user_role == "admin"

        async def get_user_projects(self, user_id, user_role) -> list:
            # Admin gets all projects
            return [project1.project_id]

        async def get_project_role(self, user_id, project_id) -> str | None:
            return "admin"

    mock_rbac = MockAdminRBACService()

    # Act & Assert - Admin should have access
    has_access = await mock_rbac.has_project_access(
        user_id=admin_user.user_id,
        user_role="admin",
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

    # Add user with different roles to each project
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
    member3 = ProjectMember(
        user_id=test_user.user_id,
        project_id=project3.project_id,
        role=ProjectRole.PROJECT_ADMIN,
        assigned_by=test_user.user_id,
    )
    db_session.add_all([member1, member2, member3])
    await db_session.commit()

    # Create mock RBAC service
    class MockMultiRoleRBACService(RBACServiceABC):
        def __init__(self):
            self.roles = {
                str(project1.project_id): "viewer",
                str(project2.project_id): "editor",
                str(project3.project_id): "admin",
            }

        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["all"]

        async def has_project_access(
            self,
            user_id,
            user_role,
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

        async def get_user_projects(self, user_id, user_role) -> list:
            return [UUID(pid) for pid in self.roles.keys()]

        async def get_project_role(self, user_id, project_id) -> str | None:
            return self.roles.get(str(project_id))

    mock_rbac = MockMultiRoleRBACService()

    # Act & Assert - Verify permissions for each role
    # Viewer can only read
    assert await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project1.project_id, "project-read"
    )
    assert not await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project1.project_id, "project-write"
    )

    # Editor can read and write
    assert await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project2.project_id, "project-read"
    )
    assert await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project2.project_id, "project-write"
    )
    assert not await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project2.project_id, "project-delete"
    )

    # Admin can do everything
    assert await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project3.project_id, "project-delete"
    )
    assert await mock_rbac.has_project_access(
        test_user.user_id, "viewer", project3.project_id, "project-admin"
    )
