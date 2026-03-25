"""Temporal context tools for AI agent.

Provides read-only access to temporal context information for the LLM.
Tools in this module do NOT modify temporal state - they only provide
visibility into the current temporal context.
"""

from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext


@ai_tool(
    name="get_temporal_context",
    description="Returns the current temporal context for the session. "
    "This provides READ-ONLY information about the temporal view: "
    "as_of date (timestamp for time-travel queries, null = current time), "
    "branch_name (the branch being queried), "
    "branch_mode (how branch data is combined: 'merged' or 'isolated'). "
    "NOTE: This is informational only. To change temporal context, "
    "use the Time Machine component in the UI.",
    permissions=[],  # No special permissions required
    category="temporal",
    risk_level=RiskLevel.LOW,
)
async def get_temporal_context(
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Returns the current temporal context for the session.

    This tool provides the LLM with visibility into temporal context
    WITHOUT giving it control. Temporal context remains immutable
    and can only be changed through the Time Machine UI.

    Context: Read-only tool for LLM awareness of temporal state.
    The LLM can query this tool to understand what temporal context
    it's operating in, but cannot modify it.

    Args:
        context: Injected tool execution context (contains temporal parameters)

    Returns:
        Dictionary containing:
            - as_of: ISO format timestamp or None (current time)
            - branch_name: Branch name (defaults to "main")
            - branch_mode: Branch mode ("merged" or "isolated", defaults to "merged")

    Example:
        >>> await get_temporal_context(context)
        {
            "as_of": "2025-06-15T12:30:45",
            "branch_name": "feature-1",
            "branch_mode": "isolated"
        }

    Security:
        This tool is READ-ONLY. It only reads from ToolContext and never
        modifies temporal state. Temporal context can only be changed
        through the Time Machine UI component, providing maximum security
        against prompt injection attacks.
    """
    return {
        "as_of": context.as_of.isoformat() if context.as_of else None,
        "branch_name": context.branch_name or "main",
        "branch_mode": context.branch_mode or "merged",
    }
