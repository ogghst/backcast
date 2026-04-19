"""Tool registry for auto-discovery and management of AI tools."""

import importlib
import inspect
import logging
from typing import Any

from langchain_core.tools import BaseTool

from app.ai.tools.types import ToolContext, ToolMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for AI tools with auto-discovery and filtering.

    Provides centralized tool management with:
    - Auto-discovery of @ai_tool decorated functions
    - Permission-based filtering
    - Category grouping
    - LangChain BaseTool conversion (typically StructuredTool)
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tools: dict[str, Any] = {}
        self._metadata: dict[str, ToolMetadata] = {}

    def register(self, func: Any, metadata: ToolMetadata) -> None:
        """Register a tool function with metadata.

        Args:
            func: Tool function (decorated with @ai_tool)
            metadata: Tool metadata
        """
        tool_name = metadata.name
        self._tools[tool_name] = func
        self._metadata[tool_name] = metadata
        logger.info(f"Registered tool: {tool_name}")

    def get_all_metadata(self) -> list[ToolMetadata]:
        """Get metadata for all registered tools.

        Returns:
            List of all tool metadata
        """
        return list(self._metadata.values())

    def get_by_permission(self, permission: str) -> list[ToolMetadata]:
        """Get tools that require a specific permission.

        Args:
            permission: Permission string

        Returns:
            List of tool metadata requiring the permission
        """
        return [
            metadata
            for metadata in self._metadata.values()
            if permission in metadata.permissions
        ]

    def get_by_category(self, category: str) -> list[ToolMetadata]:
        """Get tools in a specific category.

        Args:
            category: Category name

        Returns:
            List of tool metadata in the category
        """
        return [
            metadata
            for metadata in self._metadata.values()
            if metadata.category == category
        ]

    def as_langchain_tools(
        self, context: ToolContext, permissions: list[str] | None = None
    ) -> list[BaseTool]:
        """Convert registered tools to LangChain BaseTool instances.

        Args:
            context: Tool context for execution
            permissions: Optional permission filter (only include tools with these permissions)

        Returns:
            List of LangChain BaseTool instances (typically StructuredTool)
        """
        from app.ai.tools.decorator import to_langchain_tool

        tools: list[BaseTool] = []
        for name, func in self._tools.items():
            metadata = self._metadata[name]

            # Filter by permissions if specified
            if permissions:
                if not any(p in permissions for p in metadata.permissions):
                    continue

            # Convert to LangChain tool
            langchain_tool = to_langchain_tool(func, context)
            tools.append(langchain_tool)

        return tools

    def discover_and_register(self, module_path: str) -> None:
        """Discover and register @ai_tool decorated functions in a module.

        Args:
            module_path: Python module path (e.g., "app.ai.tools.project_tools")
        """
        try:
            module = importlib.import_module(module_path)

            for _name, obj in inspect.getmembers(module):
                if hasattr(obj, "_is_ai_tool") and obj._is_ai_tool:
                    metadata = getattr(obj, "_tool_metadata", None)
                    if metadata:
                        self.register(obj, metadata)
                        logger.info(f"Auto-discovered tool: {metadata.name}")

        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    return _registry


def register_tool(func: Any, metadata: ToolMetadata) -> None:
    """Register a tool with the global registry.

    Args:
        func: Tool function
        metadata: Tool metadata
    """
    _registry.register(func, metadata)


def get_all_tools() -> list[ToolMetadata]:
    """Get all registered tool metadata.

    Returns:
        List of all tool metadata
    """
    return _registry.get_all_metadata()


def get_tools_by_permission(permission: str) -> list[ToolMetadata]:
    """Get tools requiring a specific permission.

    Args:
        permission: Permission string

    Returns:
        List of tool metadata
    """
    return _registry.get_by_permission(permission)


def get_tools_by_category(category: str) -> list[ToolMetadata]:
    """Get tools in a specific category.

    Args:
        category: Category name

    Returns:
        List of tool metadata
    """
    return _registry.get_by_category(category)


def as_langchain_tools(
    context: ToolContext, permissions: list[str] | None = None
) -> list[BaseTool]:
    """Get all tools as LangChain BaseTool instances.

    Args:
        context: Tool context
        permissions: Optional permission filter

    Returns:
        List of LangChain BaseTool instances (typically StructuredTool)
    """
    return _registry.as_langchain_tools(context, permissions)
