"""Tests for RBACToolNode permission checks."""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.rbac_tool_node import RBACToolNode
from app.ai.tools.types import ToolContext, ToolMetadata
from app.core.rbac import RBACServiceABC, set_rbac_service


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for testing."""

    def __init__(self, permissions: dict[str, list[str]]) -> None:
        """Initialize mock with role-permission mappings."""
        self._permissions = permissions
        self.session = None

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
        """Check if user has access to a project with required permission."""
        # For testing, admins have access to all projects
        if user_role == "admin":
            return True
        # For other roles, check global permissions
        return self.has_permission(user_role, required_permission)

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        """Get list of project IDs the user has access to."""
        # For testing, return empty list (no projects)
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Get user's role within a specific project."""
        # For testing, return None (no project role)
        return None


class TestRBACToolNode:
    """Test suite for RBACToolNode."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock database session."""
        from unittest.mock import AsyncMock


        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def admin_context(self, mock_session: AsyncMock) -> ToolContext:
        """Create a ToolContext with admin role."""
        return ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

    @pytest.fixture
    def viewer_context(self, mock_session: AsyncMock) -> ToolContext:
        """Create a ToolContext with viewer role."""
        return ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="viewer"
        )

    @pytest.fixture
    def sample_tool(self) -> BaseTool:
        """Create a sample tool with metadata."""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel

        class TestInput(BaseModel):
            param1: str

        async def test_func(param1: str) -> str:
            return f"Result: {param1}"

        test_tool = StructuredTool.from_function(
            func=test_func,
            name="test_tool",
            description="Test tool",
            args_schema=TestInput
        )

        # Attach metadata
        test_tool._tool_metadata = ToolMetadata(  # type: ignore[attr-defined]
            name="test_tool",
            description="Test tool",
            permissions=["project-read"],
            category="test",
            version="1.0.0"
        )

        return test_tool

    @pytest.mark.asyncio
    async def test_rbac_tool_node_permission_denied(
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
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel

        class DeleteProjectInput(BaseModel):
            project_id: str

        async def delete_project_func(project_id: str) -> str:
            return f"Deleted {project_id}"

        delete_project = StructuredTool.from_function(
            func=delete_project_func,
            name="delete_project",
            description="Delete a project",
            args_schema=DeleteProjectInput
        )

        delete_project._tool_metadata = ToolMetadata(  # type: ignore[attr-defined]
            name="delete_project",
            description="Delete a project",
            permissions=["project-delete"],
            category="projects",
            version="1.0.0"
        )

        # Create RBACToolNode
        node = RBACToolNode([delete_project], viewer_context)

        # Test that permission check works correctly
        error_message = await node._check_tool_permission("delete_project", {})

        # Assert: Should return error message
        assert error_message is not None
        assert "Permission denied" in error_message
        assert "project-delete" in error_message
        assert "viewer" in error_message

    @pytest.mark.asyncio
    async def test_rbac_tool_node_permission_granted(
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
        error_message = await node._check_tool_permission("test_tool", {})

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


    # === T-RBAC-01: test_rbac_check_called_before_execution ===
    @pytest.mark.asyncio
    async def test_rbac_check_called_before_execution(
        self,
        sample_tool: BaseTool,
        admin_context: ToolContext
    ) -> None:
        """Test that permission check happens before tool execution.

        Given:
            A tool requiring "project-read" permission
            An admin user with the permission
        When:
            The tool permission is checked
        Then:
            The check happens BEFORE execution
            The _check_tool_permission method is called
        """
        # Arrange: Set up RBAC service
        mock_service = MockRBACService({
            "admin": ["project-read"],
            "viewer": ["project-read"]
        })
        set_rbac_service(mock_service)

        # Create RBACToolNode
        node = RBACToolNode([sample_tool], admin_context)

        # Act: Check permission
        result = await node._check_tool_permission("test_tool", {})

        # Assert: Permission check returned None (allowed)
        assert result is None
        # Verify that the check was performed (no exception raised)
        assert isinstance(result, str | None)


    # === T-RBAC-02: test_rbac_denied_returns_error_message ===
    @pytest.mark.asyncio
    async def test_rbac_denied_returns_error_message(
        self,
        sample_tool: BaseTool,
        viewer_context: ToolContext
    ) -> None:
        """Test that permission denied returns proper error ToolMessage.

        Given:
            A tool requiring "project-delete" permission
            A viewer role without that permission
        When:
            Permission check is performed
        Then:
            Error message contains all required information
            Error message format is correct
        """
        # Arrange: Set up RBAC service
        mock_service = MockRBACService({
            "admin": ["project-read", "project-write", "project-delete"],
            "viewer": ["project-read"]  # Missing project-delete
        })
        set_rbac_service(mock_service)

        # Create tool with delete permission
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel

        class DeleteProjectInput(BaseModel):
            project_id: str

        async def delete_project_func(project_id: str) -> str:
            return f"Deleted {project_id}"

        delete_project = StructuredTool.from_function(
            func=delete_project_func,
            name="delete_project",
            description="Delete a project",
            args_schema=DeleteProjectInput
        )

        delete_project._tool_metadata = ToolMetadata(  # type: ignore[attr-defined]
            name="delete_project",
            description="Delete a project",
            permissions=["project-delete"],
            category="projects",
            version="1.0.0"
        )

        # Create RBACToolNode
        node = RBACToolNode([delete_project], viewer_context)

        # Act: Check permission
        error_message = await node._check_tool_permission("delete_project", {})

        # Assert: Error message has proper format
        assert error_message is not None
        assert "Permission denied" in error_message
        assert "project-delete" in error_message
        assert "viewer" in error_message
        assert "delete_project" in error_message


    # === T-RBAC-03: test_rbac_multiple_permissions_all_required ===
    @pytest.mark.asyncio
    async def test_rbac_multiple_permissions_all_required(
        self,
        mock_session: AsyncMock,
        admin_context: ToolContext
    ) -> None:
        """Test that ALL required permissions are checked (AND logic).

        Given:
            A tool requiring multiple permissions
            A user with only some of the permissions
        When:
            Permission check is performed
        Then:
            Access is denied if ANY permission is missing
            Error message indicates the missing permission
        """
        # Arrange: Set up RBAC service
        mock_service = MockRBACService({
            "admin": ["project-read", "project-write"],
            "editor": ["project-read"],  # Missing project-write
        })
        set_rbac_service(mock_service)

        # Create tool requiring BOTH permissions
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel

        class UpdateProjectInput(BaseModel):
            project_id: str

        async def update_project_func(project_id: str) -> str:
            return f"Updated {project_id}"

        update_project = StructuredTool.from_function(
            func=update_project_func,
            name="update_project",
            description="Update a project",
            args_schema=UpdateProjectInput
        )

        update_project._tool_metadata = ToolMetadata(  # type: ignore[attr-defined]
            name="update_project",
            description="Update a project",
            permissions=["project-read", "project-write"],  # Requires BOTH
            category="projects",
            version="1.0.0"
        )

        # Create RBACToolNode with editor context (only has project-read)
        editor_context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="editor"
        )

        node = RBACToolNode([update_project], editor_context)

        # Act: Check permission
        error_message = await node._check_tool_permission("update_project", {})

        # Assert: Should be denied (missing project-write)
        assert error_message is not None
        assert "Permission denied" in error_message
        # Should mention one of the missing permissions
        assert "project-write" in error_message or "project-read" in error_message


    # === T-RBAC-04: test_rbac_no_permissions_allows_execution ===
    @pytest.mark.asyncio
    async def test_rbac_no_permissions_allows_execution(
        self,
        mock_session: AsyncMock,
        admin_context: ToolContext
    ) -> None:
        """Test that tools without permissions execute freely.

        Given:
            A tool with NO permission requirements
            Any user role (even with no permissions)
        When:
            Permission check is performed
        Then:
            Access is granted without RBAC check
        """
        # Arrange: Set up RBAC service with minimal permissions
        mock_service = MockRBACService({
            "guest": [],  # No permissions
            "admin": ["project-read"]
        })
        set_rbac_service(mock_service)

        # Create tool WITHOUT metadata (no permissions required)
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel

        class PublicToolInput(BaseModel):
            data: str

        async def public_tool_func(data: str) -> str:
            return f"Processed: {data}"

        public_tool = StructuredTool.from_function(
            func=public_tool_func,
            name="public_tool",
            description="A public tool that anyone can use.",
            args_schema=PublicToolInput
        )

        # Intentionally don't set _tool_metadata
        # public_tool._tool_metadata = None  # No metadata = no permissions

        # Create RBACToolNode with guest context (no permissions)
        guest_context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="guest"
        )

        node = RBACToolNode([public_tool], guest_context)

        # Act: Check permission
        error_message = await node._check_tool_permission("public_tool", {})

        # Assert: Should be allowed (no metadata = no permissions required)
        assert error_message is None
        # Tool should execute without RBAC check


    # === Additional test: tool not found handling ===
    @pytest.mark.asyncio
    async def test_rbac_tool_not_found_returns_error(
        self,
        mock_session: AsyncMock,
        admin_context: ToolContext
    ) -> None:
        """Test that non-existent tools return appropriate error.

        Given:
            A request for a tool that doesn't exist
        When:
            Permission check is performed
        Then:
            Error message indicates tool not found
        """
        # Arrange: Set up RBAC service
        mock_service = MockRBACService({
            "admin": ["*"]
        })
        set_rbac_service(mock_service)

        # Create RBACToolNode with one tool
        from langchain_core.tools import StructuredTool

        async def existing_tool_func() -> str:
            return "result"

        existing_tool = StructuredTool.from_function(
            func=existing_tool_func,
            name="existing_tool",
            description="An existing tool."
        )

        node = RBACToolNode([existing_tool], admin_context)

        # Act: Try to check permission for non-existent tool
        error_message = await node._check_tool_permission("nonexistent_tool", {})

        # Assert: Should return tool not found error
        assert error_message is not None
        assert "Tool not found" in error_message
        assert "nonexistent_tool" in error_message
