"""Tests for RBAC @require_permission decorator."""

from pathlib import Path
from typing import Any
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
