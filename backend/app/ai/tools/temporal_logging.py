"""Context logging helper functions.

Provides utilities for logging temporal and project context and adding metadata
to tool results for observability and debugging.
"""

import logging
from typing import Any

from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


def log_temporal_context(
    tool_name: str,
    context: ToolContext,
) -> None:
    """Log temporal context application for observability.

    Logs the temporal context (as_of, branch_name, branch_mode) being used
    by a tool for database queries. This provides security observability and
    debugging capabilities.

    Args:
        tool_name: Name of the tool being executed
        context: ToolContext containing temporal parameters

    Example:
        >>> log_temporal_context("list_projects", context)
        # Logs: [TEMPORAL_CONTEXT] Tool 'list_projects' executing with
        #       as_of=2025-06-15 12:00:00, branch=feature-1, mode=isolated
    """
    as_of_str = context.as_of.isoformat() if context.as_of else "None (current time)"
    branch_str = context.branch_name or "main"
    mode_str = context.branch_mode or "merged"

    logger.info(
        f"[TEMPORAL_CONTEXT] Tool '{tool_name}' executing with "
        f"as_of={as_of_str}, branch={branch_str}, mode={mode_str}"
    )


def add_temporal_metadata(
    result: dict[str, Any],
    context: ToolContext,
) -> dict[str, Any]:
    """Add temporal context metadata to tool result.

    Adds a `_temporal_context` field to the tool result containing the
    temporal parameters used for the query. This provides observability
    and helps users understand what data they're viewing.

    Args:
        result: Original tool result dictionary
        context: ToolContext containing temporal parameters

    Returns:
        Enhanced result dictionary with `_temporal_context` field added

    Example:
        >>> result = {"projects": [...], "total": 5}
        >>> enhanced = add_temporal_metadata(result, context)
        >>> enhanced["_temporal_context"]
        {'as_of': '2025-06-15T12:00:00', 'branch_name': 'feature-1', 'branch_mode': 'isolated'}
    """
    # Create temporal metadata (keys match ToolContext field names)
    temporal_metadata = {
        "as_of": context.as_of.isoformat() if context.as_of else None,
        "branch_name": context.branch_name or "main",
        "branch_mode": context.branch_mode or "merged",
    }

    # Add metadata to result (preserving all existing fields)
    enhanced_result = {**result, "_temporal_context": temporal_metadata}

    return enhanced_result


def log_project_context(
    tool_name: str,
    context: ToolContext,
) -> None:
    """Log project context application for observability.

    Logs the project context (project_id) being used by a tool for database
    queries. This provides security observability and debugging capabilities.

    Args:
        tool_name: Name of the tool being executed
        context: ToolContext containing project_id parameter

    Example:
        >>> log_project_context("list_wbes", context)
        # Logs: [PROJECT_CONTEXT] Tool 'list_wbes' executing with
        #       project=123e4567-e89b-12d3-a456-426614174000
    """
    project_str = context.project_id or "None (global)"
    logger.info(
        f"[PROJECT_CONTEXT] Tool '{tool_name}' executing with project={project_str}"
    )


def add_project_metadata(
    result: dict[str, Any],
    context: ToolContext,
) -> dict[str, Any]:
    """Add project context metadata to tool result.

    Adds a `_project_context` field to the tool result containing the
    project_id used for the query. This provides observability and helps
    users understand what data they're viewing.

    Args:
        result: Original tool result dictionary
        context: ToolContext containing project_id parameter

    Returns:
        Enhanced result dictionary with `_project_context` field added

    Example:
        >>> result = {"wbes": [...], "total": 5}
        >>> enhanced = add_project_metadata(result, context)
        >>> enhanced["_project_context"]
        {'project_id': '123e4567-e89b-12d3-a456-426614174000'}
    """
    # Create project metadata (keys match ToolContext field names)
    project_metadata = {
        "project_id": context.project_id,
    }

    # Add metadata to result (preserving all existing fields)
    enhanced_result = {**result, "_project_context": project_metadata}

    return enhanced_result
