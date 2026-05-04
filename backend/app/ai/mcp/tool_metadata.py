"""MCP tool metadata wrapper for Backcast's RBAC/tool pipeline.

Wraps tools discovered from MCP servers with Backcast's ToolMetadata
so they flow through the existing permission and risk-level filtering.
"""

from langchain_core.tools import BaseTool

from app.ai.tools.types import RiskLevel, ToolMetadata


def wrap_mcp_tool(tool: BaseTool, server_name: str) -> BaseTool:
    """Attach Backcast ToolMetadata to an MCP-discovered tool.

    Args:
        tool: LangChain BaseTool discovered from an MCP server.
        server_name: Name of the MCP server that owns this tool.

    Returns:
        The same tool instance with ``_tool_metadata`` attached.
    """
    metadata = ToolMetadata(
        name=tool.name,
        description=tool.description or "",
        permissions=["mcp-tool-execute"],
        category=f"mcp:{server_name}",
        risk_level=RiskLevel.HIGH,
    )
    tool._tool_metadata = metadata  # type: ignore[attr-defined]
    return tool
