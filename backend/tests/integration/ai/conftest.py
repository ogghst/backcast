"""Configuration for AI integration tests."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.ai.agent_service import AgentService
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

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        """Check if user has access to a project with required permission.

        For testing, admins always have access, others need membership.
        """
        # System admins bypass project-level checks
        if user_role == "admin":
            return True

        # For non-admins, require explicit project membership
        # In tests, we'll deny by default unless explicitly granted
        return False

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        """Get list of project IDs the user has access to.

        For testing, admins get all projects, others get empty list.
        """
        # System admins have access to all projects
        if user_role == "admin":
            # Return empty list for testing - tests will override as needed
            return []

        # Non-admin users: return empty by default
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Get user's role within a specific project.

        For testing, return None by default.
        """
        # No membership by default
        return None


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


@pytest.fixture
def mock_agent_service():
    """Create a mock AgentService for testing."""
    return MagicMock(spec=AgentService)


@pytest.fixture
def mock_project_service():
    """Create a mock ProjectService for testing."""
    service = MagicMock()
    service.get_projects = AsyncMock(return_value=([], 0))
    service.get_by_id = AsyncMock(return_value=None)
    service.create_project = AsyncMock(return_value=None)
    service.update_project = AsyncMock(return_value=None)
    return service
