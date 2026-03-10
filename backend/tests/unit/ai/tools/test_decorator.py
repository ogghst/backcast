"""Tests for @ai_tool decorator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.tools.decorator import ai_tool, to_langchain_tool


class TestAiToolDecorator:
    """Test @ai_tool decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_wraps_function(self):
        """Test decorator preserves function signature."""
        @ai_tool(name="test_tool")
        async def test_func(value: str) -> dict:
            return {"result": value}

        assert hasattr(test_func, "_is_ai_tool")
        assert hasattr(test_func, "_tool_metadata")
        assert test_func._tool_metadata.name == "test_tool"

    @pytest.mark.asyncio
    async def test_decorator_checks_permissions_denied(self):
        """Test decorator enforces RBAC permissions when denied."""
        from app.ai.tools.types import ToolContext

        mock_context = MagicMock(spec=ToolContext)
        mock_context.user_id = "user123"
        mock_context.check_permission = AsyncMock(return_value=False)

        @ai_tool(permissions=["admin-only"])
        async def admin_tool(context: ToolContext) -> dict:
            return {"success": True}

        result = await admin_tool(context=mock_context)
        assert "error" in result
        assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_decorator_checks_permissions_allowed(self):
        """Test decorator allows execution when permissions granted."""
        from app.ai.tools.types import ToolContext

        mock_context = MagicMock(spec=ToolContext)
        mock_context.user_id = "user123"
        mock_context.check_permission = AsyncMock(return_value=True)

        @ai_tool(permissions=["project-read"])
        async def protected_tool(context: ToolContext) -> dict:
            return {"success": True}

        result = await protected_tool(context=mock_context)
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_decorator_injects_context(self):
        """Test decorator passes context to function."""
        from app.ai.tools.types import ToolContext

        mock_context = MagicMock(spec=ToolContext)
        mock_context.user_id = "user123"
        mock_context.check_permission = AsyncMock(return_value=True)

        @ai_tool()
        async def context_tool(context: ToolContext) -> dict:
            return {"user_id": context.user_id}

        result = await context_tool(context=mock_context)
        assert result["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_decorator_handles_errors(self):
        """Test decorator catches and returns errors."""
        from app.ai.tools.types import ToolContext

        mock_context = MagicMock(spec=ToolContext)
        mock_context.check_permission = AsyncMock(return_value=True)

        @ai_tool()
        async def failing_tool(context: ToolContext) -> dict:
            raise ValueError("Test error")

        result = await failing_tool(context=mock_context)
        assert "error" in result
        assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_decorator_requires_context(self):
        """Test decorator returns error when context not provided."""
        @ai_tool()
        async def context_tool(context) -> dict:
            return {"success": True}

        result = await context_tool(context=None)
        assert "error" in result
        assert "context not provided" in result["error"]

    def test_to_langchain_tool_conversion(self):
        """Test conversion to LangChain StructuredTool."""
        from app.ai.tools.types import ToolContext

        @ai_tool(name="test_tool", description="Test description")
        async def test_func(value: str) -> dict:
            return {"result": value}

        mock_context = MagicMock(spec=ToolContext)
        tool = to_langchain_tool(test_func, mock_context)

        assert tool.name == "test_tool"
        assert tool.description == "Test description"

    @pytest.mark.asyncio
    async def test_decorator_defaults_to_function_name(self):
        """Test decorator uses function name when name not provided."""
        @ai_tool()
        async def my_tool() -> dict:
            return {}

        assert my_tool._tool_metadata.name == "my_tool"

    @pytest.mark.asyncio
    async def test_decorator_defaults_to_docstring(self):
        """Test decorator uses docstring when description not provided."""
        @ai_tool()
        async def my_tool() -> dict:
            """My tool description."""
            return {}

        assert my_tool._tool_metadata.description == "My tool description."

    @pytest.mark.asyncio
    async def test_decorator_with_category(self):
        """Test decorator stores category in metadata."""
        @ai_tool(category="projects")
        async def categorized_tool() -> dict:
            return {}

        assert categorized_tool._tool_metadata.category == "projects"

    @pytest.mark.asyncio
    async def test_decorator_with_multiple_permissions(self):
        """Test decorator handles multiple permissions."""
        from app.ai.tools.types import ToolContext

        mock_context = MagicMock(spec=ToolContext)
        mock_context.user_id = "user123"
        # First permission check passes, second fails
        mock_context.check_permission = AsyncMock(side_effect=[True, False])

        @ai_tool(permissions=["read", "admin"])
        async def multi_perm_tool(context: ToolContext) -> dict:
            return {"success": True}

        result = await multi_perm_tool(context=mock_context)
        assert "error" in result
        assert "Permission denied" in result["error"]
