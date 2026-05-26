"""Temporal context tools for AI agent.

Provides read and write access to temporal context information for the LLM.
- get_temporal_context: Read-only visibility into current temporal state
- set_temporal_context: Change the temporal viewing context (as_of, branch, mode)
"""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.execution.agent_event import AgentEvent
from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.services.branch_service import BranchService


@ai_tool(
    name="get_temporal_context",
    description="Read current temporal context (date, branch, mode).",
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
    current_time = context.as_of if context.as_of else datetime.now(UTC)

    return {
        "as_of": context.as_of.isoformat() if context.as_of else None,
        "current_date": current_time.strftime("%A, %B %d, %Y at %I:%M %p"),
        "branch_name": context.branch_name or "main",
        "branch_mode": context.branch_mode or "merged",
    }


@ai_tool(
    name="set_temporal_context",
    description="Change temporal context (date, branch, mode).",
    permissions=["temporal-write"],
    category="temporal",
    risk_level=RiskLevel.LOW,
)
async def set_temporal_context(
    as_of: str | None = None,
    branch_name: str | None = None,
    branch_mode: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Change the temporal viewing context for this session.

    Only provided parameters are changed; unset parameters remain unchanged.

    Args:
        as_of: ISO datetime string to set the temporal view point, or "now" to reset to current time (e.g. "2025-01-15" or "2025-06-15T12:30:00")
        branch_name: Branch name to switch to (e.g. "main", "BR-001"). Must be an existing branch for the current project.
        branch_mode: How to display branch data - "merged" (combine with main branch) or "isolated" (show only this branch)
        context: Injected tool execution context

    Returns:
        Dictionary with success status and details of what changed

    Example:
        >>> await set_temporal_context(as_of="2025-01-15", context=ctx)
        {"success": True, "message": "Temporal context updated", "changes": {...}}
    """
    if as_of is None and branch_name is None and branch_mode is None:
        return {
            "error": "At least one parameter must be provided (as_of, branch_name, or branch_mode)"
        }

    changes: dict[str, dict[str, str | None]] = {}

    # Validate and parse as_of
    parsed_as_of: datetime | None | object = object()  # sentinel for "not provided"
    if as_of is not None:
        if as_of.lower() == "now":
            parsed_as_of = None
        else:
            try:
                parsed_as_of = datetime.fromisoformat(as_of)
            except ValueError:
                return {
                    "error": f"Invalid as_of format: '{as_of}'. "
                    "Use ISO format like '2025-01-15' or '2025-06-15T12:30:00', or 'now' for current time"
                }

    # Validate branch_mode
    if branch_mode is not None and branch_mode not in ("merged", "isolated"):
        return {
            "error": f"Invalid branch_mode: '{branch_mode}'. Must be 'merged' or 'isolated'"
        }

    # Validate branch_name against DB if project context exists
    if branch_name is not None and context.project_id is not None:
        if branch_name != "main":
            try:
                svc = BranchService(context.session)
                branches = await svc.list_branches_as_of(UUID(context.project_id))
                valid_names = [b.name for b in branches]
                if branch_name not in valid_names:
                    return {
                        "error": f"Branch '{branch_name}' not found for this project. "
                        f"Available branches: main{', ' + ', '.join(valid_names) if valid_names else ''}"
                    }
            except Exception:
                pass  # Allow on validation failure

    # Capture old values and apply changes
    if as_of is not None:
        old_as_of = context.as_of.isoformat() if context.as_of else None
        context.as_of = parsed_as_of if parsed_as_of is not None else None  # type: ignore[assignment]
        new_as_of = context.as_of.isoformat() if context.as_of else None
        changes["as_of"] = {"from": old_as_of, "to": new_as_of}

    if branch_name is not None:
        old_branch = context.branch_name or "main"
        context.branch_name = branch_name
        changes["branch_name"] = {"from": old_branch, "to": branch_name}

    if branch_mode is not None:
        old_mode = context.branch_mode or "merged"
        context.branch_mode = branch_mode  # type: ignore[assignment]
        changes["branch_mode"] = {"from": old_mode, "to": branch_mode}

    # Publish event for frontend
    if context._event_bus is not None:
        context._event_bus.publish(
            AgentEvent(
                event_type="temporal_context_change",
                data={
                    "as_of": context.as_of.isoformat() if context.as_of else None,
                    "branch_name": context.branch_name or "main",
                    "branch_mode": context.branch_mode or "merged",
                },
            )
        )

    return {
        "success": True,
        "message": "Temporal context updated",
        "changes": changes,
    }
