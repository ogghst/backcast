"""Project context tools for AI agent.

Provides read-only access to project context information for the LLM.
Tools in this module do NOT modify project state - they only provide
visibility into the current project context.
"""

import asyncio
import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import (
    add_project_metadata,
    add_temporal_metadata,
    log_project_context,
    log_temporal_context,
)
from app.ai.tools.types import RiskLevel, ToolContext
from app.core.rbac import set_rbac_session

logger = logging.getLogger(__name__)

# Reasonable limits for data fetching to prevent memory issues
_MAX_WBES = 5000
_MAX_COST_ELEMENTS = 10000


@ai_tool(
    name="get_project_context",
    description="Returns the current project context for the session. "
    "This provides READ-ONLY information about the project: "
    "project_id, project_name, project_code, user's role in the project. "
    "NOTE: This is informational only. Project context is enforced at the system level. "
    "The project scope is immutable for the session duration - to change projects, "
    "the user must navigate to a different project chat URL.",
    permissions=[],  # No special permissions required
    category="context",
    risk_level=RiskLevel.LOW,
)
async def get_project_context(
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Returns the current project context for the session.

    This tool provides the LLM with visibility into project context
    WITHOUT giving it control. Project context remains immutable
    and can only be changed by navigating to a different project URL.

    Context: Read-only tool for LLM awareness of project state.
    The LLM can query this tool to understand what project context
    it's operating in, but cannot modify it.

    Args:
        context: Injected tool execution context (contains project_id)

    Returns:
        Dictionary containing:
            - project_id: Project UUID or None (global scope)
            - project_name: Project name or None
            - project_code: Project code or None
            - user_role: User's role in the project (admin/editor/viewer) or None
            - scope: "project" if project_id is set, "global" otherwise

    Example:
        >>> await get_project_context(context)
        {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_name": "Automation Line 1",
            "project_code": "AL1",
            "user_role": "editor",
            "scope": "project"
        }

        >>> await get_project_context(context)  # No project context
        {
            "project_id": None,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "global"
        }

    Security:
        This tool is READ-ONLY. It only reads from ToolContext and never
        modifies project state. Project context can only be changed
        by navigating to a different project URL, providing maximum security
        against prompt injection attacks.
    """
    # If no project_id is set, return global scope
    if not context.project_id:
        return {
            "project_id": None,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "global",
        }

    # Project context is set - fetch project details and user role
    try:
        from uuid import UUID

        from app.core.rbac import get_rbac_service

        # Validate project_id format
        project_uuid = UUID(context.project_id)

        # Set session for project-level access checks
        rbac_service = get_rbac_service()
        set_rbac_session(context.session)

        # Get project details
        from app.core.versioning.enums import BranchMode

        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGE if context.branch_mode == "merged" else BranchMode.STRICT
        )

        project = await context.project_service.get_as_of(
            entity_id=project_uuid,
            as_of=context.as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not project:
            # Project not found (may have been deleted)
            return {
                "project_id": context.project_id,
                "project_name": None,
                "project_code": None,
                "user_role": None,
                "scope": "project",
                "error": "Project not found or access denied",
            }

        # Get user's role in the project
        user_uuid = UUID(context.user_id)
        user_role = await rbac_service.get_project_role(
            user_id=user_uuid,
            project_id=project_uuid,
        )

        return {
            "project_id": context.project_id,
            "project_name": project.name,
            "project_code": project.code,
            "user_role": user_role,  # Will be None if not a member
            "scope": "project",
        }

    except (ValueError, TypeError):
        # Invalid UUID format
        return {
            "project_id": context.project_id,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "project",
            "error": "Invalid project ID format",
        }
    except Exception as e:
        # Error fetching project details
        return {
            "project_id": context.project_id,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "project",
            "error": f"Error fetching project details: {str(e)}",
        }


def _build_wbe_tree(
    wbes: list[Any],
    cost_elements_by_wbe: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build nested WBE tree from flat list using parent_wbe_id.

    Args:
        wbes: Flat list of WBE ORM objects with wbe_id, code, name,
              level, budget_allocation, and parent_wbe_id attributes.
        cost_elements_by_wbe: Mapping of WBE ID strings to lists of
              cost element dictionaries.

    Returns:
        List of root WBE nodes, each potentially containing nested
        children following the parent_wbe_id hierarchy.
    """
    wbe_map: dict[str, dict[str, Any]] = {}
    root_nodes: list[dict[str, Any]] = []

    for wbe in wbes:
        node: dict[str, Any] = {
            "id": str(wbe.wbe_id),
            "code": wbe.code,
            "name": wbe.name,
            "level": wbe.level,
            "budget_allocation": (
                float(wbe.budget_allocation) if wbe.budget_allocation else None
            ),
            "children": [],
            "cost_elements": cost_elements_by_wbe.get(str(wbe.wbe_id), []),
        }
        wbe_map[str(wbe.wbe_id)] = node

    for wbe in wbes:
        node = wbe_map[str(wbe.wbe_id)]
        if wbe.parent_wbe_id:
            parent = wbe_map.get(str(wbe.parent_wbe_id))
            if parent:
                parent["children"].append(node)
            else:
                root_nodes.append(node)
        else:
            root_nodes.append(node)

    return root_nodes


@ai_tool(
    name="get_project_structure",
    description="Returns the complete project hierarchy as a nested tree: "
    "Project -> WBEs (nested by parent) -> Cost Elements. "
    "Only available when a project context is active. "
    "Use this to understand the full project structure at a glance.",
    permissions=["project-read"],
    category="context",
    risk_level=RiskLevel.LOW,
)
async def get_project_structure(
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Returns the complete project hierarchy as a nested tree.

    Provides the full project structure with WBEs nested by parent-child
    relationships and cost elements attached to each WBE. Only available
    in project-scoped chat.

    Args:
        context: Injected tool execution context (requires project_id)

    Returns:
        Dictionary containing:
            - project: Project info with nested wbes tree
            Each WBE node has: id, code, name, level, budget_allocation,
            children (nested WBEs), cost_elements (list with id, code,
            name, budget_amount, type)

    Example:
        >>> await get_project_structure(context)
        {
            "project": {
                "id": "123e4567-...",
                "code": "AL1",
                "name": "Automation Line 1",
                "status": "ACT",
                "budget": 1000000.0,
                "wbes": [{
                    "id": "...", "code": "1", "name": "Engineering",
                    "level": 1, "budget_allocation": 500000.0,
                    "children": [...],
                    "cost_elements": [...]
                }]
            }
        }
    """
    from uuid import UUID

    from app.core.rbac import get_rbac_service
    from app.core.versioning.enums import BranchMode
    from app.services.cost_element_service import CostElementService
    from app.services.wbe import WBEService

    # Log context
    log_temporal_context("get_project_structure", context)
    log_project_context("get_project_structure", context)

    # Require project context
    if not context.project_id:
        return {
            "error": "No project context. Navigate to a project chat to use this tool.",
        }

    try:
        # Resolve temporal parameters
        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGE if context.branch_mode == "merged" else BranchMode.STRICT
        )
        project_uuid = UUID(context.project_id)

        # Set session for project-level access checks
        rbac_service = get_rbac_service()
        set_rbac_session(context.session)

        user_uuid = UUID(context.user_id)
        accessible_project_ids = await rbac_service.get_user_projects(
            user_id=user_uuid,
            user_role=context.user_role,
        )

        if project_uuid not in accessible_project_ids:
            return add_project_metadata(
                {"error": "Access denied to this project"}, context
            )

        # Fetch project
        project = await context.project_service.get_as_of(
            entity_id=project_uuid,
            as_of=context.as_of,
            branch=branch,
            branch_mode=branch_mode,
        )
        if not project:
            return add_project_metadata(
                {"error": f"Project {context.project_id} not found"}, context
            )

        # Fetch all WBEs and cost elements concurrently
        wbe_service = WBEService(context.session)
        ce_service = CostElementService(context.session)

        wbes_result, ces_result = await asyncio.gather(
            wbe_service.get_wbes(
                project_id=project_uuid,
                branch=branch,
                branch_mode=branch_mode,
                as_of=context.as_of,
                limit=_MAX_WBES,
            ),
            ce_service.get_cost_elements(
                branch=branch,
                branch_mode=branch_mode,
                limit=_MAX_COST_ELEMENTS,
                as_of=context.as_of,
            ),
        )
        wbes, _ = wbes_result
        all_ces, _ = ces_result

        wbe_ids = {str(w.wbe_id) for w in wbes}
        cost_elements_by_wbe: dict[str, list[dict[str, Any]]] = {}
        for ce in all_ces:
            if str(ce.wbe_id) in wbe_ids:
                ce_list = cost_elements_by_wbe.setdefault(str(ce.wbe_id), [])
                ce_list.append(
                    {
                        "id": str(ce.cost_element_id),
                        "code": ce.code,
                        "name": ce.name,
                        "budget_amount": (
                            float(ce.budget_amount) if ce.budget_amount else 0
                        ),
                        "type": getattr(ce, "cost_element_type_name", None),
                    }
                )

        # Build tree
        wbe_tree = _build_wbe_tree(wbes, cost_elements_by_wbe)

        result = {
            "project": {
                "id": str(project.project_id),
                "code": project.code,
                "name": project.name,
                "status": project.status,
                "budget": float(project.budget) if project.budget else None,
                "wbes": wbe_tree,
            },
        }

        with_project_meta = add_project_metadata(result, context)
        return add_temporal_metadata(with_project_meta, context)

    except Exception as e:
        logger.error(f"Error in get_project_structure: {e}")
        with_project_meta = add_project_metadata({"error": str(e)}, context)
        return add_temporal_metadata(with_project_meta, context)
