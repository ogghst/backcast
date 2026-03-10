"""AI Tools for natural language queries.

This module provides the new tool standardization system using @ai_tool decorator.
The old implementation is preserved for reference during migration.

New Tool System:
- Use @ai_tool decorator to create tools
- Tools are auto-discovered by the registry
- Context injection with ToolContext
- RBAC enforcement via permissions

Example:
    @ai_tool(
        name="list_projects",
        description="List all projects",
        permissions=["project-read"],
        category="projects"
    )
    async def list_projects(
        search: str | None = None,
        context: ToolContext = None
    ) -> dict[str, Any]:
        # Implementation
        pass
"""

from app.ai.tools.decorator import ai_tool, to_langchain_tool
from app.ai.tools.registry import (
    as_langchain_tools,
    get_all_tools,
    get_registry,
    get_tools_by_category,
    get_tools_by_permission,
    register_tool,
)
from app.ai.tools.types import ToolContext, ToolMetadata

__all__ = [
    # Decorator
    "ai_tool",
    "to_langchain_tool",
    # Registry
    "get_registry",
    "register_tool",
    "get_all_tools",
    "get_tools_by_permission",
    "get_tools_by_category",
    "as_langchain_tools",
    # Types
    "ToolContext",
    "ToolMetadata",
]
