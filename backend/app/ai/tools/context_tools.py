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
from app.core.rbac_unified import get_unified_rbac_service, set_unified_rbac_session
from app.db.session import DB_CONCURRENCY_SEMAPHORE

logger = logging.getLogger(__name__)

# Reasonable limits for data fetching to prevent memory issues
_MAX_WBS_ELEMENTS = 5000
_MAX_WORK_PACKAGES = 10000


@ai_tool(
    name="get_project_context",
    description="Read current project scope and user role.",
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
            - contract_value: Contract value (Decimal as float, may be None)
            - currency: ISO 4217 currency code (e.g. 'EUR')
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

        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )

        # Validate project_id format
        project_uuid = UUID(context.project_id)

        # Set session for project-level access checks
        set_unified_rbac_session(context.session)
        unified_service = get_unified_rbac_service()

        # Get project details
        from app.core.versioning.enums import BranchMode

        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGED
            if context.branch_mode == "merged"
            else BranchMode.ISOLATED
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

        # Get user's roles in the project
        user_uuid = UUID(context.user_id)
        user_roles = await unified_service.get_project_roles(
            user_id=user_uuid,
            project_id=project_uuid,
        )

        return {
            "project_id": context.project_id,
            "project_name": project.name,
            "project_code": project.code,
            "contract_value": (
                float(project.contract_value) if project.contract_value else None
            ),
            "currency": project.currency,
            "user_roles": user_roles,  # Empty list if not a member
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


def _build_wbs_tree(
    wbs_elements: list[Any],
    work_packages_by_wbs: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build nested WBS Element tree from flat list using parent_wbs_element_id.

    Args:
        wbs_elements: Flat list of WBSElement ORM objects with wbs_element_id, code,
              name, level, budget_allocation, and parent_wbs_element_id attributes.
        work_packages_by_wbs: Mapping of WBS Element ID strings to lists of
              work package dictionaries.

    Returns:
        List of root WBS nodes, each potentially containing nested
        children following the parent_wbs_element_id hierarchy.
    """
    wbs_map: dict[str, dict[str, Any]] = {}
    root_nodes: list[dict[str, Any]] = []

    for wbs in wbs_elements:
        node: dict[str, Any] = {
            "id": str(wbs.wbs_element_id),
            "code": wbs.code,
            "name": wbs.name,
            "level": wbs.level,
            "budget_allocation": (
                float(wbs.budget_allocation) if wbs.budget_allocation else None
            ),
            "children": [],
            "work_packages": work_packages_by_wbs.get(str(wbs.wbs_element_id), []),
        }
        wbs_map[str(wbs.wbs_element_id)] = node

    for wbs in wbs_elements:
        node = wbs_map[str(wbs.wbs_element_id)]
        parent_id = getattr(wbs, "parent_wbs_element_id", None)
        if parent_id:
            parent = wbs_map.get(str(parent_id))
            if parent:
                parent["children"].append(node)
            else:
                root_nodes.append(node)
        else:
            root_nodes.append(node)

    return root_nodes


@ai_tool(
    name="get_project_structure",
    description="Read project WBS hierarchy as nested tree.",
    permissions=["project-read"],
    category="context",
    risk_level=RiskLevel.LOW,
)
async def get_project_structure(
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Returns the complete project hierarchy as a nested tree.

    Provides the full project structure with WBS Elements nested by parent-child
    relationships and work packages attached to each WBS Element. Only available
    in project-scoped chat.

    Args:
        context: Injected tool execution context (requires project_id)

    Returns:
        Dictionary containing:
            - project: Project info with nested wbs_elements tree
            Each WBS node has: id, code, name, level, budget_allocation,
            children (nested WBS Elements), work_packages (list with id, code,
            name, budget_amount, status)

    Example:
        >>> await get_project_structure(context)
        {
            "project": {
                "id": "123e4567-...",
                "code": "AL1",
                "name": "Automation Line 1",
                "status": "ACT",
                "budget": 1000000.0,
                "contract_value": 1000000.0,
                "currency": "EUR",
                "wbs_elements": [{
                    "id": "...", "code": "1", "name": "Engineering",
                    "level": 1, "budget_allocation": 500000.0,
                    "children": [...],
                    "work_packages": [...]
                }]
            }
        }
    """
    from uuid import UUID

    from app.core.versioning.enums import BranchMode
    from app.services.wbs_element_service import WBSElementService
    from app.services.work_package_service import WorkPackageService

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
            BranchMode.MERGED
            if context.branch_mode == "merged"
            else BranchMode.ISOLATED
        )
        project_uuid = UUID(context.project_id)

        # Set session for project-level access checks
        set_unified_rbac_session(context.session)
        unified_service = get_unified_rbac_service()

        user_uuid = UUID(context.user_id)
        accessible_project_ids = await unified_service.get_accessible_projects(
            user_id=user_uuid,
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

        # Fetch all WBS Elements and work packages concurrently
        wbs_service = WBSElementService(context.session)
        wp_service = WorkPackageService(context.session)

        async with DB_CONCURRENCY_SEMAPHORE:
            wbs_result, wp_result = await asyncio.gather(
                wbs_service.get_wbs_elements(
                    project_id=project_uuid,
                    branch=branch,
                    branch_mode=branch_mode,
                    as_of=context.as_of,
                    limit=_MAX_WBS_ELEMENTS,
                ),
                wp_service.get_work_packages(
                    branch=branch,
                    branch_mode=branch_mode,
                    as_of=context.as_of,
                    limit=_MAX_WORK_PACKAGES,
                ),
            )
        wbs_elements, _ = wbs_result
        all_wps, _ = wp_result

        # Build a mapping from control_account_id to wbs_element_id
        # We need to resolve ControlAccount -> WBSElement for the tree
        from typing import cast as typing_cast

        from sqlalchemy import func as sql_func
        from sqlalchemy import select as sql_select

        from app.models.domain.control_account import ControlAccount

        ca_stmt = sql_select(
            ControlAccount.control_account_id,
            ControlAccount.wbs_element_id,
        ).where(
            ControlAccount.branch == branch,
            sql_func.upper(typing_cast(Any, ControlAccount).valid_time).is_(None),
            typing_cast(Any, ControlAccount).deleted_at.is_(None),
        )
        ca_result = await context.session.execute(ca_stmt)
        ca_to_wbs = {
            str(row.control_account_id): str(row.wbs_element_id)
            for row in ca_result.all()
        }

        wbs_ids = {str(w.wbs_element_id) for w in wbs_elements}
        # Also include parent WBS IDs from control accounts
        for wbs_id in ca_to_wbs.values():
            wbs_ids.add(wbs_id)

        work_packages_by_wbs: dict[str, list[dict[str, Any]]] = {}
        for wp in all_wps:
            ca_wbs_id = ca_to_wbs.get(str(wp.control_account_id))
            if ca_wbs_id and ca_wbs_id in wbs_ids:
                wp_list = work_packages_by_wbs.setdefault(wbs_id, [])
                wp_list.append(
                    {
                        "id": str(wp.work_package_id),
                        "code": wp.code,
                        "name": wp.name,
                        "budget_amount": (
                            float(wp.budget_amount) if wp.budget_amount else 0
                        ),
                        "status": wp.status,
                    }
                )

        # Build tree
        wbs_tree = _build_wbs_tree(wbs_elements, work_packages_by_wbs)

        result = {
            "project": {
                "id": str(project.project_id),
                "code": project.code,
                "name": project.name,
                "status": project.status,
                "budget": float(project.budget) if project.budget else None,
                "contract_value": (
                    float(project.contract_value) if project.contract_value else None
                ),
                "currency": project.currency,
                "wbs_elements": wbs_tree,
            },
        }

        with_project_meta = add_project_metadata(result, context)
        return add_temporal_metadata(with_project_meta, context)

    except Exception as e:
        logger.error(f"Error in get_project_structure: {e}")
        with_project_meta = add_project_metadata({"error": str(e)}, context)
        return add_temporal_metadata(with_project_meta, context)
