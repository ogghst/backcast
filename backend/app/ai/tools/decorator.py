"""@ai_tool decorator for LangGraph tool standardization.

This decorator converts async functions into LangGraph-compatible tools with:
- Automatic schema generation from function signatures (via LangChain @tool)
- Docstring parsing for parameter descriptions
- RBAC permission checking via metadata
- Context injection support with InjectedToolArg
- Error handling and logging
- Tool metadata generation

Composes with LangChain's @tool(parse_docstring=True) to leverage
native docstring parsing for parameter descriptions.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from langchain_core.tools import BaseTool, tool

from .types import ToolContext, ToolMetadata

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def ai_tool(
    name: str | None = None,
    description: str | None = None,
    permissions: list[str] | None = None,
    category: str | None = None,
) -> Callable[[Callable[P, Any]], BaseTool]:
    """Decorator to convert async function into LangChain BaseTool.

    This decorator composes with LangChain's @tool(parse_docstring=True) to:
    - Automatically parse Google-style docstrings for parameter descriptions
    - Generate Pydantic schemas from function signatures
    - Support InjectedToolArg for context parameter hiding
    - Attach RBAC metadata for permission checking

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        permissions: Required permissions for RBAC
        category: Tool category for organization

    Returns:
        LangChain BaseTool instance (not the original function)

    Example:
        ```python
        @ai_tool(
            name="list_projects",
            description="List all projects in the system",
            permissions=["project-read"],
            category="projects"
        )
        async def list_projects(
            search: str | None = None,
            limit: int = 20,
            context: Annotated[ToolContext, InjectedToolArg],
        ) -> dict[str, Any]:
            \"\"\"List projects with optional search filter.

            Context: Provides database session and user context.

            Args:
                search: Optional search term for project names
                limit: Maximum results to return (default 20)
                context: Injected tool execution context

            Returns:
                Dictionary with projects list and total count

            Raises:
                ValueError: If search is invalid
            \"\"\"
            # Implementation
            return {"projects": [], "total": 0}
        ```

    Note:
        - Use `Annotated[ToolContext, InjectedToolArg]` for context parameter
        - This excludes context from the tool schema while injecting it at runtime
        - Docstring Args sections are parsed for parameter descriptions
        - The decorator returns a BaseTool, not the original function
    """

    def decorator(func: Callable[P, Any]) -> BaseTool:
        # Extract metadata from decorator parameters or function
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"
        tool_permissions = permissions or []
        tool_category = category

        # Create ToolMetadata for RBAC
        metadata = ToolMetadata(
            name=tool_name,
            description=tool_description,
            permissions=tool_permissions,
            category=tool_category,
            version="1.0.0"
        )

        # Wrap function to inject context and handle permissions
        @wraps(func)
        async def wrapped_with_context(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Extract context from kwargs
            context_obj_arg = kwargs.get("context")
            context_obj: ToolContext | None = None

            # Type check for context
            if isinstance(context_obj_arg, ToolContext):
                context_obj = context_obj_arg
            elif context_obj_arg is not None:
                # Try to cast if it has the right attributes
                if hasattr(context_obj_arg, "session") and hasattr(context_obj_arg, "user_id"):
                    context_obj = context_obj_arg  # type: ignore[assignment]

            # Validate context
            if context_obj is None:
                logger.error(f"Tool {tool_name} called without context")
                return {"error": "Tool context not provided"}

            # Check permissions via RBAC service
            from app.core.rbac import get_rbac_service
            rbac_service = get_rbac_service()

            for permission in tool_permissions:
                if not rbac_service.has_permission(context_obj.user_role, permission):
                    logger.warning(
                        f"Permission denied: user_role={context_obj.user_role} "
                        f"tool={tool_name} permission={permission}"
                    )
                    return {"error": f"Permission denied: {permission} required"}

            # Execute original function
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error in tool {tool_name}: {e}", exc_info=True)
                return {"error": str(e)}

        # Apply LangChain's @tool decorator with parse_docstring=True
        # This enables automatic docstring parsing for parameter descriptions
        # Note: LangChain's tool() decorator returns Any, but we know it's BaseTool
        langchain_tool_instance: BaseTool = tool(
            parse_docstring=True,
            description=tool_description,
        )(wrapped_with_context)

        # Override name if provided (LangChain uses function name by default)
        if name:
            langchain_tool_instance.name = name

        # Attach our metadata for RBAC checking
        langchain_tool_instance._tool_metadata = metadata  # type: ignore[attr-defined]
        langchain_tool_instance._is_ai_tool = True  # type: ignore[attr-defined]

        return langchain_tool_instance

    return decorator


def to_langchain_tool(
    func: Callable[..., Any],
    context: ToolContext,
) -> BaseTool:
    """Convert @ai_tool decorated function to LangChain BaseTool with context.

    Note: This function is now deprecated as @ai_tool returns BaseTool directly.
    Kept for backward compatibility.

    Args:
        func: Decorated function (should already be a BaseTool)
        context: Tool context for execution

    Returns:
        LangChain BaseTool instance (just returns func if already BaseTool)
    """
    # If func is already a BaseTool (new decorator), return as-is
    if isinstance(func, BaseTool):
        return func

    # Otherwise, use old conversion logic (deprecated)
    metadata = getattr(func, "_tool_metadata", None)

    async def wrapped(**kwargs: Any) -> str:
        """Wrapped function that includes context."""
        import json

        result = await func(context=context, **kwargs)
        return json.dumps(result)

    # Note: tool() decorator returns Any, but we know it's BaseTool
    # Type ignore needed for deprecated function - complex overload signatures
    return tool(  # type: ignore[call-overload]
        name=metadata.name if metadata else func.__name__,
        description=metadata.description if metadata else func.__doc__ or "",
    )(wrapped)
