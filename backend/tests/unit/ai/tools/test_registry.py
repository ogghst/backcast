"""Tests for tool registry."""

from unittest.mock import MagicMock

import pytest

from app.ai.tools.decorator import ai_tool
from app.ai.tools.registry import (
    ToolRegistry,
    get_all_tools,
    get_registry,
    get_tools_by_category,
    get_tools_by_permission,
    register_tool,
)
from app.ai.tools.types import ToolContext, ToolMetadata


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        async def test_func() -> dict:
            return {"test": True}

        metadata = ToolMetadata(name="test_tool", description="Test", permissions=[])

        registry.register(test_func, metadata)

        assert "test_tool" in registry._tools
        assert "test_tool" in registry._metadata
        assert registry._metadata["test_tool"].name == "test_tool"

    def test_get_all_metadata(self):
        """Test getting all tool metadata."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        async def func2() -> dict:
            return {}

        metadata1 = ToolMetadata(name="tool1", description="Tool 1", permissions=[])
        metadata2 = ToolMetadata(
            name="tool2", description="Tool 2", permissions=["admin"]
        )

        registry.register(func1, metadata1)
        registry.register(func2, metadata2)

        all_metadata = registry.get_all_metadata()
        assert len(all_metadata) == 2
        metadata_names = {m.name for m in all_metadata}
        assert metadata_names == {"tool1", "tool2"}

    def test_get_by_permission(self):
        """Test filtering tools by permission."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        async def func2() -> dict:
            return {}

        metadata1 = ToolMetadata(
            name="tool1", description="Tool 1", permissions=["project-read"]
        )
        metadata2 = ToolMetadata(
            name="tool2", description="Tool 2", permissions=["admin"]
        )

        registry.register(func1, metadata1)
        registry.register(func2, metadata2)

        admin_tools = registry.get_by_permission("admin")
        assert len(admin_tools) == 1
        assert admin_tools[0].name == "tool2"

        project_tools = registry.get_by_permission("project-read")
        assert len(project_tools) == 1
        assert project_tools[0].name == "tool1"

    def test_get_by_permission_multiple(self):
        """Test filtering tools when tool has multiple permissions."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        metadata1 = ToolMetadata(
            name="tool1", description="Tool 1", permissions=["read", "write", "admin"]
        )

        registry.register(func1, metadata1)

        # Should find tool for any of its permissions
        read_tools = registry.get_by_permission("read")
        assert len(read_tools) == 1

        write_tools = registry.get_by_permission("write")
        assert len(write_tools) == 1

        admin_tools = registry.get_by_permission("admin")
        assert len(admin_tools) == 1

    def test_get_by_category(self):
        """Test filtering tools by category."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        async def func2() -> dict:
            return {}

        metadata1 = ToolMetadata(
            name="tool1", description="Tool 1", permissions=[], category="projects"
        )
        metadata2 = ToolMetadata(
            name="tool2", description="Tool 2", permissions=[], category="analysis"
        )

        registry.register(func1, metadata1)
        registry.register(func2, metadata2)

        project_tools = registry.get_by_category("projects")
        assert len(project_tools) == 1
        assert project_tools[0].name == "tool1"

        analysis_tools = registry.get_by_category("analysis")
        assert len(analysis_tools) == 1
        assert analysis_tools[0].name == "tool2"

    def test_get_by_category_no_category(self):
        """Test filtering tools when tool has no category."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        metadata1 = ToolMetadata(name="tool1", description="Tool 1", permissions=[])

        registry.register(func1, metadata1)

        no_category = registry.get_by_category("projects")
        assert len(no_category) == 0

    @pytest.mark.asyncio
    async def test_as_langchain_tools(self):
        """Test converting to LangChain tools."""

        @ai_tool(name="test_tool", description="Test description")
        async def test_func(value: str) -> dict:
            """Test function description.

            Args:
                value: Input value to process

            Returns:
                Dictionary with result
            """
            return {"result": value}

        registry = ToolRegistry()
        metadata = ToolMetadata(
            name="test_tool", description="Test description", permissions=[]
        )
        registry.register(test_func, metadata)

        mock_context = MagicMock(spec=ToolContext)
        tools = registry.as_langchain_tools(mock_context)

        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "Test description"

    @pytest.mark.asyncio
    async def test_as_langchain_tools_with_permission_filter(self):
        """Test converting to LangChain tools with permission filter."""

        @ai_tool(name="tool1", description="Tool 1", permissions=["read"])
        async def func1() -> dict:
            """First test function.

            Returns:
                Empty dictionary
            """
            return {}

        @ai_tool(name="tool2", description="Tool 2", permissions=["admin"])
        async def func2() -> dict:
            """Second test function.

            Returns:
                Empty dictionary
            """
            return {}

        registry = ToolRegistry()
        registry.register(func1, func1._tool_metadata)
        registry.register(func2, func2._tool_metadata)

        mock_context = MagicMock(spec=ToolContext)

        # Filter to only include tools with "read" permission
        tools = registry.as_langchain_tools(mock_context, permissions=["read"])
        assert len(tools) == 1
        assert tools[0].name == "tool1"

        # Filter to only include tools with "admin" permission
        tools = registry.as_langchain_tools(mock_context, permissions=["admin"])
        assert len(tools) == 1
        assert tools[0].name == "tool2"

    def test_global_registry_singleton(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_global_register_tool(self):
        """Test global register_tool function."""

        async def test_func() -> dict:
            return {}

        metadata = ToolMetadata(
            name="global_test_tool", description="Global test", permissions=[]
        )

        # Clear registry first
        registry = get_registry()
        registry._tools.clear()
        registry._metadata.clear()

        register_tool(test_func, metadata)

        all_tools = get_all_tools()
        tool_names = {t.name for t in all_tools}
        assert "global_test_tool" in tool_names

    def test_global_get_tools_by_permission(self):
        """Test global get_tools_by_permission function."""
        # Clear and setup
        registry = get_registry()
        registry._tools.clear()
        registry._metadata.clear()

        async def test_func() -> dict:
            return {}

        metadata = ToolMetadata(
            name="perm_test_tool",
            description="Permission test",
            permissions=["test-perm"],
        )

        register_tool(test_func, metadata)

        tools = get_tools_by_permission("test-perm")
        assert len(tools) == 1
        assert tools[0].name == "perm_test_tool"

    def test_global_get_tools_by_category(self):
        """Test global get_tools_by_category function."""
        # Clear and setup
        registry = get_registry()
        registry._tools.clear()
        registry._metadata.clear()

        async def test_func() -> dict:
            return {}

        metadata = ToolMetadata(
            name="category_test_tool",
            description="Category test",
            permissions=[],
            category="test-category",
        )

        register_tool(test_func, metadata)

        tools = get_tools_by_category("test-category")
        assert len(tools) == 1
        assert tools[0].name == "category_test_tool"
