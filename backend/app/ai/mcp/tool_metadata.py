"""MCP tool metadata wrapper for Backcast's RBAC/tool pipeline.

Wraps tools discovered from MCP servers with Backcast's ToolMetadata
so they flow through the existing permission and risk-level filtering.
"""

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from app.ai.config import AI_MCP_TOOL_CATEGORY_PREFIX
from app.ai.tools.types import RiskLevel, ToolMetadata

BACKCAST_INJECTED_PARAMS = frozenset(
    {"branch_name", "branch_mode", "as_of", "project_id"}
)


def _strip_backcast_kwargs(
    original: Callable[..., Any],
) -> Callable[..., Any]:
    """Wrap an async tool coroutine to strip Backcast-injected params.

    The temporal context middleware injects ``branch_name``, ``branch_mode``,
    ``as_of``, and ``project_id`` into every tool call.  MCP tools have strict
    Pydantic schemas that reject unknown arguments, so we strip them here.
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        cleaned = {k: v for k, v in kwargs.items() if k not in BACKCAST_INJECTED_PARAMS}
        return await original(*args, **cleaned)

    return wrapper


def wrap_mcp_tool(tool: BaseTool, server_name: str) -> BaseTool:
    """Attach Backcast ToolMetadata to an MCP-discovered tool.

    Wraps the tool's coroutine to strip Backcast-injected params that MCP
    tools don't accept, then attaches RBAC metadata.

    Args:
        tool: LangChain BaseTool discovered from an MCP server.
        server_name: Name of the MCP server that owns this tool.

    Returns:
        The same tool instance with ``_tool_metadata`` attached.
    """
    if isinstance(tool, StructuredTool) and tool.coroutine is not None:
        tool.coroutine = _strip_backcast_kwargs(tool.coroutine)

    metadata = ToolMetadata(
        name=tool.name,
        description=tool.description or "",
        permissions=["mcp-tool-execute"],
        category=f"{AI_MCP_TOOL_CATEGORY_PREFIX}{server_name}",
        risk_level=RiskLevel.HIGH,
    )
    tool._tool_metadata = metadata  # type: ignore[attr-defined]
    return tool
