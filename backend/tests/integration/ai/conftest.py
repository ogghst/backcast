"""Configuration for AI integration tests."""

import pytest

from app.core.rbac import RBACServiceABC, set_rbac_service


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for testing.

    Provides controlled permissions for testing RBAC functionality.
    """

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        """Check if user's role is in the required roles list."""
        if not required_roles:
            return False
        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user's role has the required permission."""
        # Define test permissions
        role_permissions: dict[str, list[str]] = {
            "admin": [
                "project-read", "project-create", "project-update", "project-delete",
                "wbe-read", "wbe-create", "wbe-update", "wbe-delete",
                "change-order-read", "change-order-create", "change-order-update",
                "evm-read", "evm-create",
            ],
            "manager": [
                "project-read", "project-create", "project-update",
                "wbe-read", "wbe-create", "wbe-update",
                "change-order-read", "change-order-create", "change-order-update",
                "evm-read", "evm-create",
            ],
            "viewer": [
                "project-read",
                "wbe-read",
                "change-order-read",
                "evm-read",
            ],
            "guest": [],  # No permissions
        }

        permissions = role_permissions.get(user_role, [])
        return required_permission in permissions

    def get_user_permissions(self, user_role: str) -> list[str]:
        """Get all permissions for a given role."""
        role_permissions: dict[str, list[str]] = {
            "admin": [
                "project-read", "project-create", "project-update", "project-delete",
                "wbe-read", "wbe-create", "wbe-update", "wbe-delete",
                "change-order-read", "change-order-create", "change-order-update",
                "evm-read", "evm-create",
            ],
            "manager": [
                "project-read", "project-create", "project-update",
                "wbe-read", "wbe-create", "wbe-update",
                "change-order-read", "change-order-create", "change-order-update",
                "evm-read", "evm-create",
            ],
            "viewer": [
                "project-read",
                "wbe-read",
                "change-order-read",
                "evm-read",
            ],
            "guest": [],  # No permissions
        }

        return role_permissions.get(user_role, [])


@pytest.fixture(autouse=True)
def setup_mock_rbac():
    """Automatically use mock RBAC service for all AI integration tests."""
    mock_service = MockRBACService()
    original_service = None

    # Store and replace the global service
    from app.core import rbac as rbac_module
    original_service = rbac_module._rbac_service
    set_rbac_service(mock_service)

    yield

    # Restore original service
    rbac_module._rbac_service = original_service
