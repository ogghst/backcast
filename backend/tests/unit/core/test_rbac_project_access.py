"""Tests for RBAC project-level access checks.

Tests the project access control methods added to the RBAC service,
including caching, database lookups, and permission checking.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.enums import ProjectRole as EnumProjectRole
from app.core.rbac import JsonRBACService


class TestJsonRBACServiceProjectAccess:
    """Test suite for JsonRBACService project-level access methods."""

    def test_service_initialization_with_session(self) -> None:
        """Test that JsonRBACService initializes with optional session.

        Given:
            A JsonRBACService initialization with session parameter
        When:
            Service is created
        Then:
            Session and cache are properly initialized
        """
        # Arrange
        mock_session = Mock()

        # Act
        import json
        import tempfile
        from pathlib import Path

        config = {"roles": {"admin": {"permissions": ["all"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = JsonRBACService(config_path=temp_path, session=mock_session)

            # Assert
            assert service.session == mock_session
            assert service._project_cache == {}
        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_has_project_access_with_db_session_integration(
        self,
    ) -> None:
        """Test has_project_access with real database session integration.

        Given:
            A user with project membership in the database
            A database session
        When:
            Checking project access
        Then:
            Access is granted based on database membership
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")

    @pytest.mark.asyncio
    async def test_has_project_access_no_membership_in_db(
        self,
    ) -> None:
        """Test has_project_access when user has no membership in database.

        Given:
            A user without project membership in the database
            A database session
        When:
            Checking project access
        Then:
            Access is denied
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")

    @pytest.mark.asyncio
    async def test_get_user_projects_admin_returns_all_projects(
        self,
    ) -> None:
        """Test get_user_projects returns all projects for admin users.

        Given:
            A user with admin role
            Multiple projects in the database
        When:
            Getting user's accessible projects
        Then:
            All project IDs are returned
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")

    @pytest.mark.asyncio
    async def test_get_user_projects_non_admin_returns_memberships(
        self,
    ) -> None:
        """Test get_user_projects returns member projects for non-admin users.

        Given:
            A user with non-admin role
            Multiple project memberships in the database
        When:
            Getting user's accessible projects
        Then:
            Only project IDs where user is a member are returned
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")

    @pytest.mark.asyncio
    async def test_get_project_role_with_db_lookup(self) -> None:
        """Test get_project_role performs database lookup when cache miss.

        Given:
            A user with project membership in the database
            No cached entry
        When:
            Getting user's role in a project
        Then:
            Database lookup is performed and role is cached
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")

    @pytest.mark.asyncio
    async def test_get_project_role_not_member_returns_none(self) -> None:
        """Test get_project_role returns None when user is not a member.

        Given:
            A user without project membership in the database
            No cached entry
        When:
            Getting user's role in a project
        Then:
            None is returned and nothing is cached
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")

    def test_role_has_permission_helper(self) -> None:
        """Test the _role_has_permission helper method.

        Given:
            A JsonRBACService instance
        When:
            Checking if roles have specific permissions
        Then:
            Returns correct boolean for each role/permission combination
        """
        # Arrange
        import json
        import tempfile
        from pathlib import Path

        config = {"roles": {"admin": {"permissions": ["all"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = JsonRBACService(config_path=temp_path)

            # Assert - Project admin has all permissions via wildcards
            assert service._role_has_permission(EnumProjectRole.PROJECT_ADMIN.value, "project-read") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_ADMIN.value, "project-update") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_ADMIN.value, "project-delete") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_ADMIN.value, "change-order-approve") is True

            # Project manager has read/write but not delete
            assert service._role_has_permission(EnumProjectRole.PROJECT_MANAGER.value, "project-read") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_MANAGER.value, "project-update") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_MANAGER.value, "project-delete") is False
            assert service._role_has_permission(EnumProjectRole.PROJECT_MANAGER.value, "change-order-approve") is False

            # Project editor has read and limited write
            assert service._role_has_permission(EnumProjectRole.PROJECT_EDITOR.value, "project-read") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_EDITOR.value, "project-update") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_EDITOR.value, "project-delete") is False
            assert service._role_has_permission(EnumProjectRole.PROJECT_EDITOR.value, "cost-element-create") is True

            # Project viewer only has read
            assert service._role_has_permission(EnumProjectRole.PROJECT_VIEWER.value, "project-read") is True
            assert service._role_has_permission(EnumProjectRole.PROJECT_VIEWER.value, "project-update") is False
            assert service._role_has_permission(EnumProjectRole.PROJECT_VIEWER.value, "cost-element-create") is False

            # Invalid role has no permissions
            assert service._role_has_permission("invalid", "project-read") is False
        finally:
            temp_path.unlink(missing_ok=True)

    def test_cache_ttl_constant(self) -> None:
        """Test that cache TTL is set to 5 minutes.

        Given:
            The JsonRBACService class
        When:
            Checking the _CACHE_TTL constant
        Then:
            TTL is set to 5 minutes
        """
        # Arrange & Act & Assert
        assert JsonRBACService._CACHE_TTL == timedelta(minutes=5)


class TestHasProjectAccess:
    """Test suite for has_project_access method."""

    @pytest.fixture
    def service(self) -> JsonRBACService:
        """Create a JsonRBACService instance for testing.

        Returns:
            Configured JsonRBACService instance
        """
        import json
        import tempfile
        from pathlib import Path

        config = {"roles": {"admin": {"permissions": ["all"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        service = JsonRBACService(config_path=temp_path)
        yield service
        temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_admin_bypasses_project_checks(self, service: JsonRBACService) -> None:
        """Test that system admins always have project access.

        Given:
            A user with system-level admin role
            No project membership
        When:
            Checking project access
        Then:
            Access is granted without database lookup
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()

        # Act
        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="admin",
            project_id=project_id,
            required_permission="project-read",
        )

        # Assert
        assert has_access is True

    @pytest.mark.asyncio
    async def test_no_session_returns_false(self, service: JsonRBACService) -> None:
        """Test that missing database session denies access.

        Given:
            A non-admin user
            No database session configured
        When:
            Checking project access
        Then:
            Access is denied with warning logged
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        service.session = None

        # Act
        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        )

        # Assert
        assert has_access is False

    @pytest.mark.asyncio
    async def test_cache_hit_reduces_db_lookup(self, service: JsonRBACService) -> None:
        """Test that cache hit avoids database lookup.

        Given:
            A cached project membership entry
            A subsequent access check within cache TTL
        When:
            Checking project access
        Then:
            Access is determined from cache without DB lookup
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # Populate cache with valid entry (project_manager has write permission)
        service._project_cache[cache_key] = (EnumProjectRole.PROJECT_MANAGER.value, datetime.now(UTC))

        # Act
        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-update",
        )

        # Assert - Should use cache, project_manager has update permission
        assert has_access is True

    @pytest.mark.asyncio
    async def test_cache_hit_permission_denied(self, service: JsonRBACService) -> None:
        """Test that cache hit correctly denies permissions.

        Given:
            A cached project_viewer role
            A permission that project_viewer doesn't have
        When:
            Checking project access
        Then:
            Access is denied based on cached role
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # Populate cache with project_viewer role
        service._project_cache[cache_key] = (EnumProjectRole.PROJECT_VIEWER.value, datetime.now(UTC))

        # Act
        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-update",
        )

        # Assert - project_viewer doesn't have update permission
        assert has_access is False

    @pytest.mark.asyncio
    async def test_cache_expired_triggers_db_lookup(self, service: JsonRBACService) -> None:
        """Test that expired cache triggers database lookup.

        Given:
            A cached project membership entry past TTL
            No database session (will return False)
        When:
            Checking project access
        Then:
            Database lookup is attempted (and fails without session)
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # Populate cache with expired entry (older than 5 minutes)
        service._project_cache[cache_key] = (
            EnumProjectRole.PROJECT_EDITOR.value,
            datetime.now(UTC) - timedelta(minutes=6),
        )

        # No session means DB lookup will fail
        service.session = None

        # Act
        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        )

        # Assert - Should attempt DB lookup but fail without session
        assert has_access is False

    @pytest.mark.asyncio
    async def test_cache_permission_hierarchy(self, service: JsonRBACService) -> None:
        """Test that cached role respects permission hierarchy.

        Given:
            A cached project_viewer role
            Various permission checks
        When:
            Checking different permissions
        Then:
            project_viewer can read but not write
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # Populate cache with project_viewer role
        service._project_cache[cache_key] = (EnumProjectRole.PROJECT_VIEWER.value, datetime.now(UTC))

        # Act & Assert - project_viewer can read
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        ) is True

        # Act & Assert - project_viewer cannot update
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-update",
        ) is False

        # Act & Assert - project_viewer cannot delete
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-delete",
        ) is False

    @pytest.mark.asyncio
    async def test_cache_editor_permissions(self, service: JsonRBACService) -> None:
        """Test that cached project_editor role has correct permissions.

        Given:
            A cached project_editor role
            Various permission checks
        When:
            Checking different permissions
        Then:
            project_editor can read and update but not delete
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # Populate cache with project_editor role
        service._project_cache[cache_key] = (EnumProjectRole.PROJECT_EDITOR.value, datetime.now(UTC))

        # Act & Assert - project_editor can read
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        ) is True

        # Act & Assert - project_editor can update
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-update",
        ) is True

        # Act & Assert - project_editor cannot delete
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-delete",
        ) is False

        # Act & Assert - project_editor cannot approve change orders
        assert await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="change-order-approve",
        ) is False


class TestGetUserProjects:
    """Test suite for get_user_projects method."""

    @pytest.fixture
    def service(self) -> JsonRBACService:
        """Create a JsonRBACService instance for testing.

        Returns:
            Configured JsonRBACService instance
        """
        import json
        import tempfile
        from pathlib import Path

        config = {"roles": {"admin": {"permissions": ["all"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        service = JsonRBACService(config_path=temp_path)
        yield service
        temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_no_session_returns_empty_list(self, service: JsonRBACService) -> None:
        """Test that missing database session returns empty list.

        Given:
            A user without admin role
            No database session configured
        When:
            Getting user's accessible projects
        Then:
            Empty list is returned
        """
        # Arrange
        user_id = uuid4()
        service.session = None

        # Act
        projects = await service.get_user_projects(user_id=user_id, user_role="user")

        # Assert
        assert projects == []

    @pytest.mark.asyncio
    async def test_admin_no_session_returns_empty(self, service: JsonRBACService) -> None:
        """Test that admin without database session returns empty list.

        Given:
            An admin user
            No database session configured
        When:
            Getting user's accessible projects
        Then:
            Empty list is returned (admin needs DB to get all projects)
        """
        # Arrange
        user_id = uuid4()
        service.session = None

        # Act
        projects = await service.get_user_projects(user_id=user_id, user_role="admin")

        # Assert
        assert projects == []

    @pytest.mark.asyncio
    async def test_non_admin_empty_memberships(self, service: JsonRBACService) -> None:
        """Test that non-admin user with no memberships returns empty list.

        Given:
            A non-admin user
            No project memberships in database
        When:
            Getting user's accessible projects
        Then:
            Empty list is returned
        """
        # This test requires a real database session - skip for unit tests
        # Integration tests cover this scenario
        pytest.skip("Requires real database session - covered in integration tests")


class TestGetProjectRole:
    """Test suite for get_project_role method."""

    @pytest.fixture
    def service(self) -> JsonRBACService:
        """Create a JsonRBACService instance for testing.

        Returns:
            Configured JsonRBACService instance
        """
        import json
        import tempfile
        from pathlib import Path

        config = {"roles": {"admin": {"permissions": ["all"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        service = JsonRBACService(config_path=temp_path)
        yield service
        temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_no_session_returns_none(self, service: JsonRBACService) -> None:
        """Test that missing database session returns None.

        Given:
            No database session configured
        When:
            Getting user's role in a project
        Then:
            None is returned
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        service.session = None

        # Act
        role = await service.get_project_role(user_id=user_id, project_id=project_id)

        # Assert
        assert role is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_role(self, service: JsonRBACService) -> None:
        """Test that cache hit returns cached role without DB lookup.

        Given:
            A cached role entry within TTL
        When:
            Getting user's role in a project
        Then:
            Cached role is returned without database lookup
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)
        cached_role = EnumProjectRole.PROJECT_VIEWER.value

        # Populate cache
        service._project_cache[cache_key] = (cached_role, datetime.now(UTC))

        # Act
        role = await service.get_project_role(user_id=user_id, project_id=project_id)

        # Assert
        assert role == cached_role

    @pytest.mark.asyncio
    async def test_cache_expired_without_session(self, service: JsonRBACService) -> None:
        """Test that expired cache without session returns None.

        Given:
            An expired cache entry
            No database session
        When:
            Getting user's role in a project
        Then:
            None is returned (DB lookup fails)
        """
        # Arrange
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # Populate cache with expired entry
        service._project_cache[cache_key] = (
            EnumProjectRole.PROJECT_ADMIN.value,
            datetime.now(UTC) - timedelta(minutes=6),
        )

        service.session = None

        # Act
        role = await service.get_project_role(user_id=user_id, project_id=project_id)

        # Assert - Should attempt DB lookup but fail
        assert role is None


class TestRBACServiceAbstractMethods:
    """Test suite for RBACServiceABC abstract method compliance."""

    def test_json_rbac_service_implements_all_abstract_methods(
        self,
    ) -> None:
        """Test that JsonRBACService implements all abstract methods.

        Given:
            The RBACServiceABC abstract base class
            The JsonRBACService concrete implementation
        When:
            Checking method implementation
        Then:
            All abstract methods are implemented
        """
        # Arrange & Act
        import json
        import tempfile
        from pathlib import Path

        config = {"roles": {"admin": {"permissions": ["all"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = JsonRBACService(config_path=temp_path)

            # Assert - All abstract methods are implemented
            assert hasattr(service, "has_role")
            assert callable(service.has_role)

            assert hasattr(service, "has_permission")
            assert callable(service.has_permission)

            assert hasattr(service, "get_user_permissions")
            assert callable(service.get_user_permissions)

            assert hasattr(service, "has_project_access")
            assert callable(service.has_project_access)

            assert hasattr(service, "get_user_projects")
            assert callable(service.get_user_projects)

            assert hasattr(service, "get_project_role")
            assert callable(service.get_project_role)
        finally:
            temp_path.unlink(missing_ok=True)


class TestProjectRoleEnum:
    """Test suite for ProjectRole enum from app.core.enums."""

    def test_project_role_values(self) -> None:
        """Test that ProjectRole enum has correct values.

        Given:
            The ProjectRole enum
        When:
            Accessing enum values
        Then:
            Expected role values are present
        """
        assert EnumProjectRole.PROJECT_ADMIN.value == "project_admin"
        assert EnumProjectRole.PROJECT_MANAGER.value == "project_manager"
        assert EnumProjectRole.PROJECT_EDITOR.value == "project_editor"
        assert EnumProjectRole.PROJECT_VIEWER.value == "project_viewer"

    def test_project_admin_has_wildcard_permissions(self) -> None:
        """Test that project_admin role has wildcard permissions.

        Given:
            The project_admin role
        When:
            Getting permissions
        Then:
            Wildcard patterns are present for all resources
        """
        permissions = EnumProjectRole.PROJECT_ADMIN.permissions

        # Should have wildcards for all resource types
        assert any("project-*" in perm for perm in permissions)
        assert any("cost-element-*" in perm for perm in permissions)
        assert any("wbe-*" in perm for perm in permissions)
        assert any("change-order-*" in perm for perm in permissions)

    def test_project_manager_has_read_write_permissions(self) -> None:
        """Test that project_manager has read and write permissions.

        Given:
            The project_manager role
        When:
            Getting permissions
        Then:
            Read and write permissions are present
        """
        permissions = EnumProjectRole.PROJECT_MANAGER.permissions

        # Should have read and update
        assert "project-read" in permissions
        assert "project-update" in permissions

        # Should not have delete
        assert "project-delete" not in permissions

    def test_project_editor_has_limited_write_permissions(self) -> None:
        """Test that project_editor has limited write permissions.

        Given:
            The project_editor role
        When:
            Getting permissions
        Then:
            Can read and update some resources but not delete
        """
        permissions = EnumProjectRole.PROJECT_EDITOR.permissions

        # Should have read and update
        assert "project-read" in permissions
        assert "project-update" in permissions
        assert "cost-element-create" in permissions

        # Should not have delete
        assert "project-delete" not in permissions
        assert "cost-element-delete" not in permissions

    def test_project_viewer_has_read_only_permissions(self) -> None:
        """Test that project_viewer has only read permissions.

        Given:
            The project_viewer role
        When:
            Getting permissions
        Then:
            Only read permissions are present
        """
        permissions = EnumProjectRole.PROJECT_VIEWER.permissions

        # Should have read
        assert "project-read" in permissions
        assert "cost-element-read" in permissions

        # Should not have write
        assert "project-update" not in permissions
        assert "cost-element-create" not in permissions

    def test_permissions_follow_hierarchy(self) -> None:
        """Test that permissions follow role hierarchy.

        Given:
            The project role hierarchy
        When:
            Comparing permission capabilities
        Then:
            project_admin can do everything project_manager can do, etc.
        """
        admin_perms = EnumProjectRole.PROJECT_ADMIN.permissions
        manager_perms = EnumProjectRole.PROJECT_MANAGER.permissions
        editor_perms = EnumProjectRole.PROJECT_EDITOR.permissions
        viewer_perms = EnumProjectRole.PROJECT_VIEWER.permissions

        # Admin has wildcard permissions that cover all specific permissions
        assert any("project-*" in perm for perm in admin_perms)
        assert any("cost-element-*" in perm for perm in admin_perms)

        # Manager has read and update but not delete (uses specific permissions)
        assert "project-read" in manager_perms
        assert "project-update" in manager_perms
        assert "project-delete" not in manager_perms

        # Editor has read and some create/update
        assert "project-read" in editor_perms
        assert "project-update" in editor_perms
        assert "project-delete" not in editor_perms

        # Viewer only has read
        assert "project-read" in viewer_perms
        assert "project-update" not in viewer_perms

        # Verify hierarchy through permission inclusion
        # Admin can do everything via wildcards
        # Manager can read/update but not delete
        # Editor can read/update but has fewer create permissions than manager
        # Viewer only has read

        # Manager has more permissions than editor (change-order-create, change-order-update)
        assert "change-order-create" in manager_perms
        assert "change-order-create" not in editor_perms

        # Editor has more permissions than viewer (can create/update)
        assert "cost-element-create" in editor_perms
        assert "cost-element-create" not in viewer_perms
