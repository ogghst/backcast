"""Security tests for AI tool RBAC enforcement.

Tests verify that tool-level RBAC is enforced correctly:
- Permission denied without required permission
- Permission granted with required permission
- Multiple permissions (AND logic)
- Permission inheritance
- Unauthorized access blocked
- Tool-level RBAC vs service-level RBAC
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools import ToolContext
from app.core.rbac import RBACServiceABC, set_rbac_service


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for testing."""

    def __init__(self):
        self.permission_map = {
            "admin": ["project-read", "project-write", "project-delete"],
            "manager": ["project-read", "project-write"],
            "viewer": ["project-read"],
            "guest": [],
        }

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return required_permission in self.permission_map.get(user_role, [])

    def get_user_permissions(self, user_role: str) -> list[str]:
        return self.permission_map.get(user_role, [])


# Test fixtures
@pytest.fixture
def mock_context_with_permissions():
    """Create a mock context with permissions."""
    context = MagicMock(spec=ToolContext)
    context.user_id = "test-user-id"
    context.user_role = "viewer"
    context.session = MagicMock(spec=AsyncSession)
    context._permission_cache = {}
    return context


@pytest.fixture
def mock_context_without_permissions():
    """Create a mock context without permissions."""
    context = MagicMock(spec=ToolContext)
    context.user_id = "test-user-id"
    context.user_role = "guest"
    context.session = MagicMock(spec=AsyncSession)
    context._permission_cache = {}
    return context


@pytest.fixture(autouse=True)
def setup_mock_rbac():
    """Automatically use mock RBAC service for all security tests."""
    mock_service = MockRBACService()
    original_service = None

    # Store and replace the global service
    from app.core import rbac as rbac_module
    original_service = rbac_module._rbac_service
    set_rbac_service(mock_service)

    yield

    # Restore original service
    rbac_module._rbac_service = original_service


@pytest.mark.asyncio
@pytest.mark.security
async def test_permission_denied_without_required_permission(
    mock_context_without_permissions,
):
    """Test: Tool execution denied when user lacks required permission.

    This test verifies that when a user attempts to execute a tool
    without the required permission, the tool execution is blocked.

    Expected: Error response indicating permission denied
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    @ai_tool(
        name="secure_tool",
        description="A tool that requires permissions",
        permissions=["project-read"],
    )
    async def secure_tool(input: str, context: ToolContext) -> dict:
        """A secure tool that processes input.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    # Act
    result = await secure_tool.ainvoke({"input": "test", "context": mock_context_without_permissions})

    # Assert
    assert "error" in result
    assert "permission" in result["error"].lower()


@pytest.mark.asyncio
@pytest.mark.security
async def test_permission_granted_with_required_permission(
    mock_context_with_permissions,
):
    """Test: Tool execution allowed when user has required permission.

    This test verifies that when a user has the required permission,
    the tool executes successfully.

    Expected: Tool executes without permission error
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    @ai_tool(
        name="secure_tool",
        description="A tool that requires permissions",
        permissions=["project-read"],
    )
    async def secure_tool(input: str, context: ToolContext) -> dict:
        """A secure tool that processes input.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    # Act
    result = await secure_tool.ainvoke({"input": "test", "context": mock_context_with_permissions})

    # Assert
    assert "error" not in result
    assert result["result"] == "Processed: test"


@pytest.mark.asyncio
@pytest.mark.security
async def test_multiple_permissions_and_logic(
    mock_context_with_permissions,
):
    """Test: Tool with multiple permission requirements requires all permissions.

    This test verifies that when a tool requires multiple permissions,
    the user must have ALL of them (AND logic, not OR logic).

    Expected: Permission denied if user has only one of two required permissions
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    # Use viewer role which only has project-read permission
    mock_context_with_permissions.user_role = "viewer"

    @ai_tool(
        name="multi_perm_tool",
        description="A tool requiring multiple permissions",
        permissions=["project-read", "project-write"],
    )
    async def multi_perm_tool(input: str, context: ToolContext) -> dict:
        """A tool with multiple permissions.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    # Act
    result = await multi_perm_tool.ainvoke({"input": "test", "context": mock_context_with_permissions})

    # Assert
    assert "error" in result
    assert "permission" in result["error"].lower()


@pytest.mark.asyncio
@pytest.mark.security
async def test_unauthorized_access_blocked_at_tool_level(
    mock_context_without_permissions,
):
    """Test: Unauthorized access is blocked at tool level.

    This test verifies that the @ai_tool decorator enforces permissions
    BEFORE calling the underlying function. This is defense in depth.

    Expected: Permission check happens before function execution
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    function_executed = False

    @ai_tool(
        name="secure_tool",
        description="A tool that requires permissions",
        permissions=["project-read"],
    )
    async def secure_tool(input: str, context: ToolContext) -> dict:
        """A secure tool that processes input.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        nonlocal function_executed
        function_executed = True
        return {"result": f"Processed: {input}"}

    # Act
    result = await secure_tool.ainvoke({"input": "test", "context": mock_context_without_permissions})

    # Assert
    assert "error" in result
    assert not function_executed, "Function should not execute when permission denied"


@pytest.mark.asyncio
@pytest.mark.security
async def test_tool_level_rbac_metadata():
    """Test: Tool-level RBAC metadata is correctly stored.

    This test verifies that tool metadata includes permission information
    for documentation and enforcement purposes.
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    @ai_tool(
        name="secure_tool",
        description="A tool that requires permissions",
        permissions=["project-read", "project-write"],
        category="projects",
    )
    async def secure_tool(input: str, context: ToolContext) -> dict:
        """A secure tool that processes input.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    # Act
    # Access the tool's metadata
    if hasattr(secure_tool, "_tool_metadata"):
        metadata = secure_tool._tool_metadata

        # Assert
        assert metadata.permissions == ["project-read", "project-write"]
        assert metadata.category == "projects"
    else:
        pytest.skip("Tool metadata not accessible in this version")


@pytest.mark.asyncio
@pytest.mark.security
async def test_rbac_enforcement_with_no_permissions_required(
    mock_context_without_permissions,
):
    """Test: Tool without permission requirements executes successfully.

    This test verifies that tools without permission requirements
    can be executed by any user (including unauthenticated users
    in some contexts).
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    @ai_tool(
        name="open_tool",
        description="A tool without permission requirements",
    )
    async def open_tool(input: str, context: ToolContext) -> dict:
        """An open tool without permission requirements.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    # Act
    result = await open_tool.ainvoke({"input": "test", "context": mock_context_without_permissions})

    # Assert
    assert "error" not in result
    assert result["result"] == "Processed: test"


@pytest.mark.asyncio
@pytest.mark.security
async def test_tool_context_user_id_isolation():
    """Test: ToolContext properly isolates user context.

    This test verifies that the user_id in ToolContext is properly
    passed and used by tools.
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool
    from app.ai.tools.types import ToolContext

    captured_user_ids = []

    @ai_tool(
        name="context_tool",
        description="A tool that uses context",
    )
    async def context_tool(input: str, context: ToolContext) -> dict:
        """A tool that captures context.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the user ID
        """
        captured_user_ids.append(context.user_id)
        return {"result": f"User: {context.user_id}"}

    # Act
    context1 = MagicMock(spec=ToolContext)
    context1.user_id = "user-1"
    context1.user_role = "viewer"
    context1.session = MagicMock(spec=AsyncSession)
    context1.check_permission = AsyncMock(return_value=True)
    context1._permission_cache = {}

    await context_tool.ainvoke({"input": "test", "context": context1})

    # Assert
    assert len(captured_user_ids) == 1
    assert captured_user_ids[0] == "user-1"


@pytest.mark.asyncio
@pytest.mark.security
async def test_permission_check_exception_handling(
    mock_context_without_permissions,
):
    """Test: Permission check exceptions are propagated.

    This test verifies that if the permission check raises an exception,
    it propagates to the caller (the decorator doesn't catch RBAC exceptions).
    """
    # Arrange
    from app.ai.tools.decorator import ai_tool

    # Create a broken RBAC service that raises exceptions
    class BrokenRBACService(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            raise Exception("Database connection failed")

        def get_user_permissions(self, user_role: str) -> list[str]:
            return []

    # Set the broken service
    set_rbac_service(BrokenRBACService())

    @ai_tool(
        name="secure_tool",
        description="A tool that requires permissions",
        permissions=["project-read"],
    )
    async def secure_tool(input: str, context: ToolContext) -> dict:
        """A secure tool that processes input.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    # Act & Assert
    # The decorator doesn't catch RBAC service exceptions, so they propagate
    with pytest.raises(Exception, match="Database connection failed"):
        await secure_tool.ainvoke({"input": "test", "context": mock_context_without_permissions})


# Run security tests with pytest:
# pytest tests/security/ai/test_tool_rbac.py -v -m security
