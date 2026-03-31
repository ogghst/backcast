"""Temporal context tools for AI agent.

Provides read-only access to temporal context information for the LLM.
Tools in this module do NOT modify temporal state - they only provide
visibility into the current temporal context.
"""

from datetime import datetime
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext


@ai_tool(
    name="get_temporal_context",
    description="Returns the current temporal context for the session. "
    "This provides READ-ONLY information about the temporal view: "
    "as_of date (timestamp for time-travel queries, null = current time), "
    "current_date (human-readable date: 'Sunday, June 15, 2025 at 12:30 PM'), "
    "branch_name (the branch being queried), "
    "branch_mode (how branch data is combined: 'merged' or 'isolated'). "
    "The 'as_of' date represents YOUR CURRENT DATE as the AI agent - use this "
    "to answer questions like 'what is the current day' or 'what month is it'. "
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
            - current_date: Human-readable format (e.g., "Sunday, June 15, 2025 at 12:30 PM")
                         Uses system time when as_of is None
            - branch_name: Branch name (defaults to "main")
            - branch_mode: Branch mode ("merged" or "isolated", defaults to "merged")

    Example:
        >>> await get_temporal_context(context)
        {
            "as_of": "2025-06-15T12:30:45",
            "current_date": "Sunday, June 15, 2025 at 12:30 PM",
            "branch_name": "feature-1",
            "branch_mode": "isolated"
        }

    Security:
        This tool is READ-ONLY. It only reads from ToolContext and never
        modifies temporal state. Temporal context can only be changed
        through the Time Machine UI component, providing maximum security
        against prompt injection attacks.
    """
    # Use system time when as_of is None, otherwise use the provided as_of time
    current_time = context.as_of if context.as_of else datetime.now()

    return {
        "as_of": context.as_of.isoformat() if context.as_of else None,
        "current_date": current_time.strftime("%A, %B %d, %Y at %I:%M %p"),
        "branch_name": context.branch_name or "main",
        "branch_mode": context.branch_mode or "merged",
    }
