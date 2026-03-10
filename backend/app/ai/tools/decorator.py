"""@ai_tool decorator for LangGraph tool standardization.

This decorator converts async functions into LangGraph-compatible tools with:
- Automatic schema generation from function signatures
- RBAC permission checking
- Context injection (db_session, user_id)
- Error handling and logging
- Tool metadata generation
"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from langchain_core.tools import StructuredTool

from .types import ToolContext, ToolMetadata

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def ai_tool(
    name: str | None = None,
    description: str | None = None,
    permissions: list[str] | None = None,
    category: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to convert async function into LangGraph tool.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        permissions: Required permissions for RBAC
        category: Tool category for organization

    Returns:
        Decorated function with tool metadata

    Example:
        @ai_tool(
            name="list_projects",
            description="List all projects",
            permissions=["project-read"],
            category="projects"
        )
        async def list_projects(
            search: str | None = None,
            context: ToolContext = Depends(get_tool_context)
        ) -> dict[str, Any]:
            # Implementation
            pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Extract metadata from function
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"
        tool_permissions = permissions or []
        tool_category = category

        # Create ToolMetadata
        metadata = ToolMetadata(
            name=tool_name,
            description=tool_description,
            permissions=tool_permissions,
            category=tool_category,
            version="1.0.0"
        )

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract context from kwargs
            context_obj: ToolContext | None = kwargs.pop("context", None)  # type: ignore[assignment]

            # Validate context
            if context_obj is None:
                logger.error(f"Tool {tool_name} called without context")
                return {"error": "Tool context not provided"}  # type: ignore[return-value]

            # Check permissions
            for permission in tool_permissions:
                if not await context_obj.check_permission(permission):
                    logger.warning(
                        f"Permission denied: user={context_obj.user_id} "
                        f"tool={tool_name} permission={permission}"
                    )
                    return {"error": f"Permission denied: {permission} required"}  # type: ignore[return-value]

            # Execute original function with context
            try:
                result = await cast(Awaitable[T], func(*args, context=context_obj, **kwargs))  # type: ignore[arg-type]
                return result
            except Exception as e:
                logger.error(f"Error in tool {tool_name}: {e}", exc_info=True)
                return {"error": str(e)}  # type: ignore[return-value]

        # Attach metadata to wrapper
        wrapper._tool_metadata = metadata  # type: ignore[attr-defined]
        wrapper._is_ai_tool = True  # type: ignore[attr-defined]

        return wrapper  # type: ignore[return-value]

    return decorator


def to_langchain_tool(
    func: Callable[..., Any],
    context: ToolContext
) -> StructuredTool:
    """Convert @ai_tool decorated function to LangChain StructuredTool.

    Args:
        func: Decorated function
        context: Tool context for execution

    Returns:
        LangChain StructuredTool instance
    """
    metadata = getattr(func, "_tool_metadata", None)

    async def wrapped(**kwargs: Any) -> str:
        """Wrapped function that includes context."""
        import json
        result = await func(context=context, **kwargs)
        return json.dumps(result)

    return StructuredTool.from_function(
        coroutine=wrapped,
        name=metadata.name if metadata else func.__name__,
        description=metadata.description if metadata else func.__doc__ or "",
        args_schema=None,  # Will be auto-generated from signature
    )
