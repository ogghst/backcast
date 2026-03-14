"""Tests for RBACToolNode permission checks."""

from uuid import uuid4

import pytest
from langchain_core.tools import BaseTool, tool

from app.ai.tools.rbac_tool_node import RBACToolNode
from app.ai.tools.types import ToolContext, ToolMetadata
from app.core.rbac import RBACServiceABC, set_rbac_service


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for testing."""

    def __init__(self, permissions: dict[str, list[str]]) -> None:
        """Initialize mock with role-permission mappings."""
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


class TestRBACToolNode:
    """Test suite for RBACToolNode."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        from unittest.mock import AsyncMock

        from sqlalchemy.ext.asyncio import AsyncSession

        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def admin_context(self, mock_session):
        """Create a ToolContext with admin role."""
        return ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

    @pytest.fixture
    def viewer_context(self, mock_session):
        """Create a ToolContext with viewer role."""
        return ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="viewer"
        )

    @pytest.fixture
    def sample_tool(self) -> BaseTool:
        """Create a sample tool with metadata."""

        @tool
        async def test_tool(param1: str) -> str:
            """Test tool.

            Args:
                param1: First parameter

            Returns:
                Result string
            """
            return f"Result: {param1}"

        # Attach metadata
        test_tool._tool_metadata = ToolMetadata(
            name="test_tool",
            description="Test tool",
            permissions=["project-read"],
            category="test",
            version="1.0.0"
        )

        return test_tool

    def test_rbac_tool_node_permission_denied(
        self,
        sample_tool: BaseTool,
        viewer_context: ToolContext
    ) -> None:
        """Test that RBACToolNode returns error when permission denied.

        Given:
            A tool requiring "project-delete" permission
            A viewer role with only "project-read" permission
        When:
            The tool is called via RBACToolNode
        Then:
            An error message is returned
            The tool is not executed
        """
        # Arrange: Set up RBAC service
        mock_service = MockRBACService({
            "admin": ["project-read", "project-write", "project-delete"],
            "viewer": ["project-read"]
        })
        set_rbac_service(mock_service)

        # Create tool with delete permission
        from langchain_core.tools import tool

        @tool
        async def delete_project(project_id: str) -> str:
            """Delete a project.

            Args:
                project_id: Project ID

            Returns:
                Success message
            """
            return f"Deleted {project_id}"

        delete_project._tool_metadata = ToolMetadata(
            name="delete_project",
            description="Delete a project",
            permissions=["project-delete"],
            category="projects",
            version="1.0.0"
        )

        # Create RBACToolNode
        node = RBACToolNode([delete_project], viewer_context)

        # Test that permission check works correctly
        error_message = node._check_tool_permission("delete_project")

        # Assert: Should return error message
        assert error_message is not None
        assert "Permission denied" in error_message
        assert "project-delete" in error_message
        assert "viewer" in error_message

    def test_rbac_tool_node_permission_granted(
        self,
        sample_tool: BaseTool,
        admin_context: ToolContext
    ) -> None:
        """Test that RBACToolNode allows execution when permitted.

        Given:
            A tool requiring "project-read" permission
            An admin role with all permissions
        When:
            The tool permission is checked
        Then:
            Permission check returns None (allowed)
        """
        # Arrange: Set up RBAC service
        mock_service = MockRBACService({
            "admin": ["project-read", "project-write", "project-delete"],
            "viewer": ["project-read"]
        })
        set_rbac_service(mock_service)

        # Create RBACToolNode
        node = RBACToolNode([sample_tool], admin_context)

        # Test that permission check allows execution
        error_message = node._check_tool_permission("test_tool")

        # Assert: Should return None (permission granted)
        assert error_message is None

    def test_rbac_tool_node_stores_context(
        self,
        sample_tool: BaseTool,
        admin_context: ToolContext
    ) -> None:
        """Test that RBACToolNode stores context for permission checks.

        Given:
            An RBACToolNode created with a context
        When:
            The node is inspected
        Then:
            The context is stored and accessible
        """
        # Arrange & Act: Create RBACToolNode
        node = RBACToolNode([sample_tool], admin_context)

        # Assert: Context should be stored
        assert node.context == admin_context
        assert node.context.user_role == "admin"
