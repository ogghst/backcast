"""Tests for RBAC @require_permission decorator."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.core.rbac import RBACServiceABC, require_permission, set_rbac_service


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for testing."""

    def __init__(self, permissions: dict[str, list[str]]) -> None:
        """Initialize mock with role-permission mappings.

        Args:
            permissions: Dict mapping role names to their permission lists
        """
        self._permissions = permissions

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        """Check if user's role is in the required roles list."""
        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user's role has the required permission."""
        role_permissions = self._permissions.get(user_role, [])
        return required_permission in role_permissions

    def get_user_permissions(self, user_role: str) -> list[str]:
        """Get all permissions for a given role."""
        return self._permissions.get(user_role, [])

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        """Mock project access check - always return True for tests."""
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        """Mock get user projects - return empty list for tests."""
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Mock get project role - return None for tests."""
        return None


class TestRequirePermissionDecorator:
    """Test suite for @require_permission decorator."""

    def test_require_permission_decorator_granted(self) -> None:
        """Test that decorator permits execution with valid role.

        Given:
            A function decorated with @require_permission("project-read")
            A user with role "admin" that has "project-read" permission
        When:
            The decorated function is called with context containing user_role="admin"
        Then:
            The function executes successfully
            The result is returned as expected
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {
                "admin": ["project-read", "project-write", "project-delete"],
                "viewer": ["project-read"],
                "guest": [],
            }
        )
        set_rbac_service(mock_service)

        # Define a test function with the decorator
        @require_permission("project-read")
        async def test_function(user_role: str, context: Any = None) -> str:
            """Test function that requires permission."""
            return "Success"

        # Act: Call the function with admin role
        import asyncio

        result = asyncio.run(test_function(user_role="admin"))

        # Assert: Function should execute successfully
        assert result == "Success"

    def test_require_permission_decorator_denied(self) -> None:
        """Test that decorator raises PermissionError for invalid role.

        Given:
            A function decorated with @require_permission("project-delete")
            A user with role "viewer" that only has "project-read" permission
        When:
            The decorated function is called with context containing user_role="viewer"
        Then:
            PermissionError is raised
            Error message contains "Permission denied" and the required permission
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {
                "admin": ["project-read", "project-write", "project-delete"],
                "viewer": ["project-read"],
                "guest": [],
            }
        )
        set_rbac_service(mock_service)

        # Define a test function with the decorator
        @require_permission("project-delete")
        async def test_function(user_role: str, context: Any = None) -> str:
            """Test function that requires permission."""
            return "Should not reach here"

        # Act & Assert: Function should raise PermissionError
        import asyncio

        with pytest.raises(PermissionError) as exc_info:
            asyncio.run(test_function(user_role="viewer"))

        # Verify error message
        assert "Permission denied" in str(exc_info.value)
        assert "project-delete" in str(exc_info.value)

    def test_require_permission_decorator_resolves_from_context(self) -> None:
        """Test that decorator resolves user_role from context parameter.

        Given:
            A function decorated with @require_permission
            A context dict containing user_role field
        When:
            The decorated function is called with context dict
        Then:
            The decorator reads user_role from context
            Permission check succeeds for authorized user
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {"admin": ["project-write"], "viewer": ["project-read"]}
        )
        set_rbac_service(mock_service)

        @require_permission("project-write")
        async def test_function(context: dict[str, Any]) -> str:
            """Test function that gets user_role from context."""
            return "Write operation succeeded"

        # Act: Call with context dict containing user_role
        import asyncio

        result = asyncio.run(test_function(context={"user_role": "admin"}))

        # Assert: Function should execute
        assert result == "Write operation succeeded"

    def test_require_permission_decorator_attaches_metadata(self) -> None:
        """Test that decorator attaches _required_permissions metadata.

        Given:
            A function decorated with @require_permission
        When:
            The decorated function is inspected
        Then:
            The function has _required_permissions attribute
            The attribute contains the required permission list
        """

        # Arrange & Act: Define decorated function
        @require_permission("project-read")
        async def test_function(user_role: str, context: Any = None) -> str:
            """Test function."""
            return "Success"

        # Assert: Metadata should be attached
        assert hasattr(test_function, "_required_permissions")
        assert test_function._required_permissions == ["project-read"]

    def test_require_permission_decorator_multiple_permissions(self) -> None:
        """Test that decorator supports multiple required permissions.

        Given:
            A function decorated with @require_permission with multiple permissions
            A user with only some of the required permissions
        When:
            The decorated function is called
        Then:
            PermissionError is raised if any permission is missing
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {"admin": ["project-read", "project-write"], "viewer": ["project-read"]}
        )
        set_rbac_service(mock_service)

        # Define function requiring multiple permissions
        @require_permission("project-read", "project-write")
        async def test_function(user_role: str, context: Any = None) -> str:
            """Test function requiring multiple permissions."""
            return "Success"

        # Act & Assert: Viewer lacks project-write permission
        import asyncio

        with pytest.raises(PermissionError) as exc_info:
            asyncio.run(test_function(user_role="viewer"))

        assert "Permission denied" in str(exc_info.value)

        # But admin has both permissions
        result = asyncio.run(test_function(user_role="admin"))
        assert result == "Success"


class TestRequirePermissionDecoratorEdgeCases:
    """Test suite for @require_permission decorator edge cases."""

    def test_require_permission_with_dict_context(self) -> None:
        """Test decorator works with dict context parameter.

        Given:
            A function decorated with @require_permission
            A dict context with user_role key
        When:
            The function is called
        Then:
            Permission check uses user_role from dict
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {"admin": ["admin-only"], "viewer": ["read-only"]}
        )
        set_rbac_service(mock_service)

        # Define function with dict context
        @require_permission("admin-only")
        async def test_function(user_role: str = None, context: Any = None) -> str:
            """Test function with dict context."""
            return "Success"

        # Act: Call with dict context
        import asyncio

        result = asyncio.run(test_function(context={"user_role": "admin"}))

        # Assert: Should succeed
        assert result == "Success"

    def test_require_permission_with_object_context(self) -> None:
        """Test decorator works with object context parameter.

        Given:
            A function decorated with @require_permission
            An object context with user_role attribute
        When:
            The function is called
        Then:
            Permission check uses user_role from object attribute
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService({"admin": ["admin-only"]})
        set_rbac_service(mock_service)

        # Define function with object context
        @require_permission("admin-only")
        async def test_function(user_role: str = None, context: Any = None) -> str:
            """Test function with object context."""
            return "Success"

        # Create a mock object with user_role attribute
        class MockContext:
            def __init__(self, role: str):
                self.user_role = role

        # Act: Call with object context
        import asyncio

        result = asyncio.run(test_function(context=MockContext("admin")))

        # Assert: Should succeed
        assert result == "Success"

    def test_require_permission_no_user_role_raises_error(self) -> None:
        """Test decorator raises error when user_role not provided.

        Given:
            A function decorated with @require_permission
            No user_role in context or as parameter
        When:
            The function is called
        Then:
            PermissionError is raised
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService({"admin": ["admin-only"]})
        set_rbac_service(mock_service)

        # Define function
        @require_permission("admin-only")
        async def test_function(user_role: str = None, context: Any = None) -> str:
            """Test function."""
            return "Success"

        # Act & Assert: Should raise PermissionError
        import asyncio

        with pytest.raises(PermissionError) as exc_info:
            asyncio.run(test_function(context={}))

        assert "user_role not provided" in str(exc_info.value)

    def test_require_permission_invalid_user_role_type(self) -> None:
        """Test decorator handles invalid user_role type.

        Given:
            A function decorated with @require_permission
            A context with invalid user_role type (not string)
        When:
            The function is called
        Then:
            PermissionError is raised
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService({"admin": ["admin-only"]})
        set_rbac_service(mock_service)

        # Define function
        @require_permission("admin-only")
        async def test_function(user_role: str = None, context: Any = None) -> str:
            """Test function."""
            return "Success"

        # Act & Assert: Should raise PermissionError for non-string user_role
        import asyncio

        with pytest.raises(PermissionError) as exc_info:
            asyncio.run(test_function(context={"user_role": 123}))

        # The error message should indicate the issue
        assert "Permission denied" in str(exc_info.value)


class TestRequirePermissionDecoratorSyncFunctions:
    """Test suite for @require_permission decorator with sync functions."""

    def test_require_permission_with_sync_function(self) -> None:
        """Test that decorator works with synchronous functions.

        Given:
            A synchronous (non-async) function decorated with @require_permission
        When:
            The function is called with proper permissions
        Then:
            The sync wrapper is used
            The function executes successfully
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {"admin": ["admin-action"], "viewer": ["read-only"]}
        )
        set_rbac_service(mock_service)

        # Define a sync function (not async)
        @require_permission("admin-action")
        def sync_function(user_role: str = None, context: Any = None) -> str:
            """Synchronous function requiring permission."""
            return "Sync success"

        # Act: Call with admin role
        result = sync_function(user_role="admin")

        # Assert: Should execute successfully
        assert result == "Sync success"

    def test_require_permission_sync_function_permission_denied(self) -> None:
        """Test that sync decorator raises PermissionError when unauthorized.

        Given:
            A synchronous function decorated with @require_permission
            A user without required permissions
        When:
            The function is called
        Then:
            PermissionError is raised
        """
        # Arrange: Set up mock RBAC service
        mock_service = MockRBACService(
            {"admin": ["admin-action"], "viewer": ["read-only"]}
        )
        set_rbac_service(mock_service)

        @require_permission("admin-action")
        def sync_function(user_role: str = None, context: Any = None) -> str:
            """Synchronous function requiring permission."""
            return "Should not reach here"

        # Act & Assert: Viewer should be denied
        with pytest.raises(PermissionError) as exc_info:
            sync_function(user_role="viewer")

        assert "Permission denied" in str(exc_info.value)
        assert "admin-action" in str(exc_info.value)


class TestJsonRBACServiceEdgeCases:
    """Test suite for JsonRBACService edge cases."""

    def test_has_role_with_empty_required_roles(self) -> None:
        """Test that has_role returns False for empty required_roles list.

        Given:
            A user with any role
            An empty required_roles list
        When:
            has_role is called
        Then:
            Returns False (empty list means no valid roles)
        """
        # Arrange: Create JsonRBACService
        import json
        import tempfile

        from app.core.rbac import JsonRBACService

        # Create a temporary config file
        config = {
            "roles": {
                "admin": {"permissions": ["all"]},
                "viewer": {"permissions": ["read"]},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()  # Ensure data is written
            temp_path = Path(f.name)

        try:
            # Act: Check with empty required_roles
            service = JsonRBACService(config_path=temp_path)
            result = service.has_role("admin", [])

            # Assert: Should return False for empty list
            assert result is False
        finally:
            # Cleanup
            temp_path.unlink(missing_ok=True)

    def test_json_rbac_service_file_not_found(self) -> None:
        """Test that JsonRBACService raises FileNotFoundError for missing config.

        Given:
            A non-existent config file path
        When:
            JsonRBACService is initialized
        Then:
            FileNotFoundError is raised
            Error message includes the file path
        """
        # Arrange: Use a non-existent path
        non_existent_path = Path("/tmp/non_existent_rbac_config_12345.json")

        # Act & Assert: Should raise FileNotFoundError
        from app.core.rbac import JsonRBACService

        with pytest.raises(FileNotFoundError) as exc_info:
            JsonRBACService(config_path=non_existent_path)

        # Verify error message contains path
        assert str(non_existent_path) in str(exc_info.value)

    def test_get_user_permissions_unknown_role(self) -> None:
        """Test that get_user_permissions returns empty list for unknown role.

        Given:
            A role that doesn't exist in the configuration
        When:
            get_user_permissions is called with the unknown role
        Then:
            An empty list is returned
        """
        # Arrange: Create JsonRBACService
        import json
        import tempfile

        from app.core.rbac import JsonRBACService

        config = {
            "roles": {
                "admin": {"permissions": ["all"]},
                "viewer": {"permissions": ["read"]},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            # Act: Get permissions for unknown role
            service = JsonRBACService(config_path=temp_path)
            permissions = service.get_user_permissions("unknown_role")

            # Assert: Should return empty list
            assert permissions == []
        finally:
            temp_path.unlink(missing_ok=True)

    def test_get_user_permissions_role_with_no_permissions(self) -> None:
        """Test that get_user_permissions handles roles with empty permissions.

        Given:
            A role that exists but has no permissions defined
        When:
            get_user_permissions is called with that role
        Then:
            An empty list is returned
        """
        # Arrange: Create JsonRBACService with role that has no permissions
        import json
        import tempfile

        from app.core.rbac import JsonRBACService

        config = {
            "roles": {
                "admin": {"permissions": ["all"]},
                "guest": {},  # No permissions key
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            # Act: Get permissions for guest role
            service = JsonRBACService(config_path=temp_path)
            permissions = service.get_user_permissions("guest")

            # Assert: Should return empty list
            assert permissions == []
        finally:
            temp_path.unlink(missing_ok=True)

    def test_get_user_permissions_missing_permissions_key(self) -> None:
        """Test that get_user_permissions handles role config without permissions key.

        Given:
            A role configuration that doesn't have a 'permissions' key
        When:
            get_user_permissions is called with that role
        Then:
            An empty list is returned (default value)
        """
        # Arrange: Create JsonRBACService with incomplete config
        import json
        import tempfile

        from app.core.rbac import JsonRBACService

        config = {
            "roles": {
                "admin": {"permissions": ["all"]},
                "custom": {"description": "Custom role"},  # No permissions key
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            # Act: Get permissions for custom role
            service = JsonRBACService(config_path=temp_path)
            permissions = service.get_user_permissions("custom")

            # Assert: Should return empty list
            assert permissions == []
        finally:
            temp_path.unlink(missing_ok=True)


class TestAIRoles:
    """Test suite for AI-specific RBAC roles.

    Uses the REAL config/rbac.json via JsonRBACService to verify
    that each AI role has the correct permission set.
    """

    @pytest.fixture(autouse=True)
    def setup_rbac_service(self) -> None:
        """Set up JsonRBACService pointing at the real rbac.json."""
        from app.core.rbac import JsonRBACService

        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        config_path = base_dir / "config" / "rbac.json"
        self.service = JsonRBACService(config_path=config_path)

    # --- ai-viewer tests ---

    def test_ai_viewer_has_read_permissions(self) -> None:
        """Verify ai-viewer has all expected read-only permissions.

        Given:
            The real rbac.json configuration
        When:
            ai-viewer role permissions are checked
        Then:
            All read permissions are present
            No write/create permissions are present
        """
        # Arrange
        read_permissions = [
            "project-read",
            "wbe-read",
            "cost-element-read",
            "cost-element-type-read",
            "cost-registration-read",
            "change-order-read",
            "forecast-read",
            "schedule-baseline-read",
            "evm-read",
            "user-read",
            "department-read",
            "quality-event-read",
            "ai-chat",
            "progress-entry-read",
        ]
        denied_permissions = [
            "project-create",
            "project-update",
            "cost-element-create",
            "cost-element-update",
            "wbe-create",
            "wbe-update",
            "cost-registration-create",
            "change-order-create",
            "forecast-create",
            "user-create",
            "user-delete",
        ]

        # Act & Assert: all read permissions present
        for perm in read_permissions:
            assert self.service.has_permission("ai-viewer", perm), (
                f"ai-viewer should have '{perm}'"
            )

        # Assert: no write permissions
        for perm in denied_permissions:
            assert not self.service.has_permission("ai-viewer", perm), (
                f"ai-viewer should NOT have '{perm}'"
            )

    def test_ai_viewer_cannot_access_any_write_permissions(self) -> None:
        """Verify ai-viewer cannot access ANY create/update/delete permissions.

        Given:
            The real rbac.json configuration
        When:
            All known create/update/delete permissions are checked against ai-viewer
        Then:
            None of them are granted

        This is the systematic negative test: it scans every permission in the
        entire config for patterns matching *-create, *-update, *-delete, and
        verifies ai-viewer has none of them.
        """
        # Collect all write-suffix permissions from the entire config
        write_suffixes = ("-create", "-update", "-delete", "-write")
        all_write_perms: set[str] = set()

        for role_config in self.service._config.get("roles", {}).values():
            for perm in role_config.get("permissions", []):
                if any(perm.endswith(suffix) for suffix in write_suffixes):
                    all_write_perms.add(perm)

        # Assert: ai-viewer has none of them
        for perm in sorted(all_write_perms):
            assert not self.service.has_permission("ai-viewer", perm), (
                f"ai-viewer should NOT have write permission '{perm}'"
            )

    # --- ai-manager tests ---

    def test_ai_manager_has_crud_permissions(self) -> None:
        """Verify ai-manager has CRUD permissions for project entities.

        Given:
            The real rbac.json configuration
        When:
            ai-manager role permissions are checked
        Then:
            Create/update permissions are present
            Delete permissions for project/user entities are absent
        """
        # Arrange
        allowed_permissions = [
            "project-read",
            "project-create",
            "project-update",
            "wbe-read",
            "wbe-create",
            "wbe-update",
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-type-read",
            "cost-registration-read",
            "cost-registration-create",
            "cost-registration-update",
            "cost-registration-delete",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-submit",
            "change-order-approve",
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "progress-entry-read",
            "progress-entry-create",
            "quality-event-read",
            "quality-event-create",
            "quality-event-update",
            "quality-event-write",
            "evm-read",
            "evm-create",
            "evm-update",
            "evm-delete",
            "ai-chat",
        ]
        denied_permissions = [
            "project-delete",
            "user-delete",
            "user-create",
        ]

        # Act & Assert: all CRUD permissions present
        for perm in allowed_permissions:
            assert self.service.has_permission("ai-manager", perm), (
                f"ai-manager should have '{perm}'"
            )

        # Assert: no destructive admin permissions
        for perm in denied_permissions:
            assert not self.service.has_permission("ai-manager", perm), (
                f"ai-manager should NOT have '{perm}'"
            )

    # --- ai-admin tests ---

    def test_ai_admin_has_admin_permissions(self) -> None:
        """Verify ai-admin has admin permissions for users/departments/types.

        Given:
            The real rbac.json configuration
        When:
            ai-admin role permissions are checked
        Then:
            User CRUD, department CRUD, cost-element-type CRUD are present
            Entity write permissions (wbe, forecast) are absent
        """
        # Arrange
        allowed_permissions = [
            "project-read",
            "user-read",
            "user-create",
            "user-update",
            "user-delete",
            "department-read",
            "department-create",
            "department-update",
            "department-delete",
            "cost-element-type-read",
            "cost-element-type-create",
            "cost-element-type-update",
            "cost-element-type-delete",
        ]
        denied_permissions = [
            "wbe-create",
            "wbe-update",
            "wbe-delete",
            "forecast-create",
            "forecast-update",
            "cost-element-create",
            "cost-registration-create",
            "change-order-create",
            "evm-create",
            "ai-chat",
        ]

        # Act & Assert: all admin permissions present
        for perm in allowed_permissions:
            assert self.service.has_permission("ai-admin", perm), (
                f"ai-admin should have '{perm}'"
            )

        # Assert: no project entity write permissions
        for perm in denied_permissions:
            assert not self.service.has_permission("ai-admin", perm), (
                f"ai-admin should NOT have '{perm}'"
            )


class TestContextvarSession:
    """Test suite for contextvar-based session injection in RBAC service."""

    def test_get_rbac_session_returns_none_by_default(self) -> None:
        """get_rbac_session() returns None when no session has been set.

        Given:
            A fresh contextvar state (no prior set_rbac_session calls in this test)
        When:
            get_rbac_session() is called
        Then:
            None is returned (the contextvar default)
        """
        from app.core.rbac import get_rbac_session, set_rbac_session

        # Clear any previous state to ensure clean slate
        set_rbac_session(None)

        result = get_rbac_session()
        assert result is None

    def test_set_rbac_session_clears_session(self) -> None:
        """set_rbac_session(None) clears a previously set session.

        Given:
            A session previously set via set_rbac_session()
        When:
            set_rbac_session(None) is called
        Then:
            get_rbac_session() returns None
        """
        from app.core.rbac import get_rbac_session, set_rbac_session

        # Arrange: set a session
        mock_session = MagicMock()
        set_rbac_session(mock_session)
        assert get_rbac_session() is mock_session

        # Act: clear the session
        set_rbac_session(None)

        # Assert: session is now None
        assert get_rbac_session() is None

    @pytest.mark.asyncio
    async def test_contextvar_session_isolation(self) -> None:
        """Two concurrent tasks with different sessions must not interfere.

        Given:
            Two async tasks that each set a different session via set_rbac_session()
        When:
            Both tasks run concurrently with an interleaving point
        Then:
            Each task reads back its own session without interference from the other

        This verifies the contextvar provides task-scoped isolation, which is
        critical for concurrent WebSocket connections using the RBAC singleton.
        """
        import asyncio

        from app.core.rbac import get_rbac_session, set_rbac_session

        results: dict[str, Any] = {}

        async def task_a() -> None:
            mock_session_a = MagicMock()
            set_rbac_session(mock_session_a)
            await asyncio.sleep(0.01)  # Let other task run
            results["a"] = get_rbac_session()

        async def task_b() -> None:
            mock_session_b = MagicMock()
            set_rbac_session(mock_session_b)
            await asyncio.sleep(0.01)  # Let other task run
            results["b"] = get_rbac_session()

        await asyncio.gather(task_a(), task_b())
        assert results["a"] is not results["b"]

    @pytest.mark.asyncio
    async def test_contextvar_fallback_in_has_project_access(self) -> None:
        """has_project_access uses contextvar session when self.session is None.

        Given:
            A JsonRBACService with session=None (no direct session)
            A mock session set via set_rbac_session()
        When:
            has_project_access() is called
        Then:
            The contextvar session is used as fallback instead of returning False

        This verifies the contextvar fallback chain: self.session (priority)
        falls back to get_rbac_session() from the contextvar.
        """
        import json
        import tempfile
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from app.core.rbac import JsonRBACService, set_rbac_session

        # Arrange: Create a JsonRBACService with session=None
        config = {
            "roles": {
                "viewer": {"permissions": ["project-read"]},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = JsonRBACService(config_path=temp_path, session=None)

            # Create a mock session that returns a project member with viewer role
            # Note: member.role must be a valid ProjectRole enum value
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_member = MagicMock()
            mock_member.role = "project_viewer"
            mock_result.scalar_one_or_none.return_value = mock_member
            mock_session.execute.return_value = mock_result

            # Set contextvar session
            set_rbac_session(mock_session)

            user_id = uuid4()
            project_id = uuid4()

            # Act: Call has_project_access (should use contextvar fallback)
            result = await service.has_project_access(
                user_id=user_id,
                user_role="viewer",
                project_id=project_id,
                required_permission="project-read",
            )

            # Assert: Should use the contextvar session and return True
            assert result is True
            mock_session.execute.assert_called_once()
        finally:
            temp_path.unlink(missing_ok=True)
