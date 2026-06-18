"""AI Tools for natural language queries.

Provides tools that can be used by LangGraph agents.
Tools are decorated with @ai_tool and return LangChain BaseTool instances.
"""

import logging

from langchain_core.tools import BaseTool

from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext

logger = logging.getLogger(__name__)

_cached_tools: list[BaseTool] | None = None


def invalidate_tool_cache() -> None:
    """Clear the cached tool list so the next call rebuilds it from scratch.

    Must be called when MCP tools are added, removed, or reconfigured at
    runtime so that ``create_project_tools()`` returns a fresh list on
    its next invocation.
    """
    global _cached_tools
    _cached_tools = None
    logger.debug("Tool cache invalidated")


def filter_tools_by_execution_mode(
    tools: list[BaseTool],
    execution_mode: ExecutionMode,
) -> list[BaseTool]:
    """Filter tools based on execution mode and risk level.

    Args:
        tools: List of tools to filter
        execution_mode: Current execution mode

    Returns:
        Filtered list of tools that are allowed in the current mode

    Rules:
        - SAFE mode: Only LOW risk tools
        - STANDARD mode: LOW and HIGH risk tools (CRITICAL tools blocked)
        - EXPERT mode: All tools
    """
    filtered_tools: list[BaseTool] = []

    for tool in tools:
        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no risk level - assume high (safe default)
            risk_level = RiskLevel.HIGH
        else:
            risk_level = metadata.risk_level

        # Filter based on execution mode
        if execution_mode == ExecutionMode.SAFE:
            if risk_level == RiskLevel.LOW:
                filtered_tools.append(tool)
            else:
                logger.debug(
                    f"Filtering out tool '{tool.name}' (risk={risk_level.value}) in SAFE mode"
                )
        elif execution_mode == ExecutionMode.STANDARD:
            if risk_level != RiskLevel.CRITICAL:
                filtered_tools.append(tool)
            else:
                logger.debug(
                    f"Filtering out tool '{tool.name}' (risk={risk_level.value}) in STANDARD mode"
                )
        else:
            # Expert mode allows all tools
            filtered_tools.append(tool)

    logger.info(
        f"Filtered {len(tools)} tools down to {len(filtered_tools)} for execution_mode={execution_mode.value}"
    )
    return filtered_tools


async def filter_tools_by_role(
    tools: list[BaseTool],
    role: str,
) -> list[BaseTool]:
    """Filter tools based on assistant RBAC role permissions.

    Removes tools whose required permissions are not granted by the role.
    Tools without permissions metadata are always allowed.

    On cache miss, triggers an on-demand refresh of the permissions cache
    before filtering. Falls back to an empty permission set (deny all
    permissioned tools) if refresh also fails.

    Args:
        tools: List of tools to filter
        role: RBAC role string (e.g., "ai-viewer", "ai-manager", "ai-admin")

    Returns:
        Filtered list of tools the role is permitted to use
    """
    from app.core.rbac_unified import get_unified_rbac_service

    unified_service = get_unified_rbac_service()
    filtered: list[BaseTool] = []

    # Batch: load all permissions once from cache, use set.issubset
    # Use get_permissions_with_refresh to handle cache misses gracefully
    perms = await unified_service.get_permissions_with_refresh(role)
    role_permissions: set[str] = set(perms)

    for tool in tools:
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None or not metadata.permissions:
            # No permissions required -- always allow
            filtered.append(tool)
            continue

        # Check ALL required permissions for this tool
        has_all = set(metadata.permissions).issubset(role_permissions)

        if has_all:
            filtered.append(tool)
        else:
            logger.debug(
                f"Filtering out tool '{tool.name}' -- "
                f"role '{role}' lacks required permissions: {metadata.permissions}"
            )

    logger.info(f"Filtered {len(tools)} tools down to {len(filtered)} for role={role}")
    return filtered


def create_project_tools(context: ToolContext) -> list[BaseTool]:
    """Create LangChain BaseTool instances for all available AI operations.

    Note: Tools are cached as singletons. The ToolContext argument is accepted
    for backward compatibility but tools retrieve their context at runtime via
    context variables, not from this argument.

    Args:
        context: Tool context (unused, kept for backward compatibility)

    Returns:
        List of BaseTool instances ready to be bound to LangGraph agents
    """
    global _cached_tools

    if _cached_tools is not None:
        logger.debug(f"Returning cached tool list ({len(_cached_tools)} tools)")
        return _cached_tools

    # Import tool modules
    from app.ai.tools import (
        ask_user as ask_user_module,
    )
    from app.ai.tools import (
        briefing_tools,
        context_tools,
        document_tools,
        project_tools,
        temporal_tools,
    )
    from app.ai.tools.templates import (
        advanced_analysis_template,
        analysis_template,
        change_order_template,
        control_account_template,
        cost_element_template,
        cost_event_template,
        cost_event_type_template,
        diagram_template,
        forecast_cost_progress_template,
        project_template,
        user_management_template,
        work_package_template,
    )

    # --- Category: "projects" (Project + WBS hierarchy) ---
    tools: list[BaseTool] = [
        # From project_tools (read/search)
        project_tools.list_projects,
        project_tools.get_project,
        # From project_template (Project CRUD)
        project_template.create_project,
        project_template.update_project,
        project_template.delete_project,
        project_template.batch_create_projects,
        # From project_template (WBS Element CRUD)
        project_template.find_wbs_elements,
        project_template.create_wbs_element,
        project_template.update_wbs_element,
        project_template.delete_wbs_element,
        project_template.batch_create_wbs_elements,
        project_template.batch_update_wbs_elements,
    ]

    # --- Category: "cost-management" (all cost-related entities) ---
    cost_management_tools = [
        # From cost_element_template (Cost Element + Cost Element Type CRUD)
        cost_element_template.find_cost_elements,
        cost_element_template.create_cost_element,
        cost_element_template.update_cost_element,
        cost_element_template.delete_cost_element,
        cost_element_template.find_cost_element_types,
        cost_element_template.create_cost_element_type,
        cost_element_template.update_cost_element_type,
        cost_element_template.delete_cost_element_type,
        cost_element_template.batch_create_cost_elements,
        cost_element_template.batch_delete_cost_elements,
        # From cost_event_template (Cost Event CRUD + COQ)
        cost_event_template.find_cost_events,
        cost_event_template.create_cost_event,
        cost_event_template.update_cost_event,
        cost_event_template.delete_cost_event,
        cost_event_template.batch_create_cost_events,
        cost_event_template.get_coq_data,
        # From cost_event_type_template (Cost Event Type CRUD)
        cost_event_type_template.find_cost_event_types,
        cost_event_type_template.create_cost_event_type,
        cost_event_type_template.update_cost_event_type,
        cost_event_type_template.delete_cost_event_type,
        cost_event_type_template.batch_create_cost_element_types,
        # From forecast_cost_progress_template (Forecast + Cost Registration)
        forecast_cost_progress_template.create_forecast,
        forecast_cost_progress_template.update_forecast,
        forecast_cost_progress_template.delete_forecast,
        forecast_cost_progress_template.batch_create_forecasts,
        forecast_cost_progress_template.get_cost_element_details,
        forecast_cost_progress_template.create_cost_registration,
        forecast_cost_progress_template.update_cost_registration,
        forecast_cost_progress_template.delete_cost_registration,
        forecast_cost_progress_template.list_cost_registrations,
        forecast_cost_progress_template.batch_create_cost_registrations,
    ]
    tools.extend(cost_management_tools)

    # --- Category: "work-tracking" (work execution tracking) ---
    work_tracking_tools = [
        # From control_account_template (Control Account CRUD + budget)
        control_account_template.find_control_accounts,
        control_account_template.create_control_account,
        control_account_template.update_control_account,
        control_account_template.delete_control_account,
        control_account_template.get_control_account_budget,
        control_account_template.batch_create_control_accounts,
        # From work_package_template (Work Package CRUD + budget status)
        work_package_template.find_work_packages,
        work_package_template.create_work_package,
        work_package_template.update_work_package,
        work_package_template.delete_work_package,
        work_package_template.batch_create_work_packages,
        work_package_template.get_work_package_budget_status,
        work_package_template.batch_get_work_package_budget_status,
        # From forecast_cost_progress_template (Progress Entry)
        forecast_cost_progress_template.create_progress_entry,
        forecast_cost_progress_template.update_progress_entry,
        forecast_cost_progress_template.delete_progress_entry,
        forecast_cost_progress_template.batch_create_progress_entries,
        forecast_cost_progress_template.get_progress_data,
    ]
    tools.extend(work_tracking_tools)

    # --- Category: "change-orders" (change order workflow) ---
    change_order_tools = [
        change_order_template.find_change_orders,
        change_order_template.create_change_order,
        change_order_template.submit_change_order_for_approval,
        change_order_template.approve_change_order,
        change_order_template.reject_change_order,
        change_order_template.analyze_change_order_impact,
        change_order_template.delete_change_order,
        change_order_template.batch_create_change_orders,
    ]
    tools.extend(change_order_tools)

    # --- Category: "analysis" (EVM metrics, forecasting, search) ---
    analysis_tools = [
        analysis_template.get_project_analysis,
        advanced_analysis_template.get_project_forecast,
        project_tools.global_search,
    ]
    tools.extend(analysis_tools)

    # --- Category: "users" (User + Organizational Unit management) ---
    user_management_tools = [
        user_management_template.find_users,
        user_management_template.create_user,
        user_management_template.update_user,
        user_management_template.delete_user,
        user_management_template.batch_create_users,
        user_management_template.find_organizational_units,
        user_management_template.create_organizational_unit,
        user_management_template.update_organizational_unit,
        user_management_template.delete_organizational_unit,
        user_management_template.batch_create_organizational_units,
    ]
    tools.extend(user_management_tools)

    # --- Category: "context" (read-only context for AI) ---
    context_tools_list = [
        temporal_tools.get_temporal_context,
        temporal_tools.set_temporal_context,
        temporal_tools.list_branches,
        context_tools.get_project_context,
        context_tools.set_project_context,
        context_tools.get_project_structure,
        briefing_tools.get_briefing,
        document_tools.search_documents,
        document_tools.read_document,
        document_tools.add_document,  # document write (project-documents-write)
        document_tools.list_folders,  # document folders (read)
        document_tools.create_folder,  # document folders (write)
        document_tools.delete_folder,  # document folders (delete)
    ]
    tools.extend(context_tools_list)

    # --- Category: "interaction" (user-facing features) ---
    interaction_tools = [
        ask_user_module.ask_user,
        diagram_template.generate_mermaid_diagram,
    ]
    tools.extend(interaction_tools)

    # Filter to only BaseTool instances
    base_tools: list[BaseTool] = [tool for tool in tools if isinstance(tool, BaseTool)]

    # Append MCP tools discovered from configured external servers
    from app.ai.mcp.client_manager import MCPClientManager

    mcp_manager = MCPClientManager()
    base_tools.extend(mcp_manager.get_all_tools())

    _cached_tools = base_tools
    logger.info(f"Created and cached {len(base_tools)} tools for AI chat")
    return base_tools


# Re-export for backwards compatibility
__all__ = [
    "create_project_tools",
    "filter_tools_by_execution_mode",
    "filter_tools_by_role",
    "invalidate_tool_cache",
    "ToolContext",
]
