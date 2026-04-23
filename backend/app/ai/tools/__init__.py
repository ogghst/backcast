"""AI Tools for natural language queries.

Provides tools that can be used by LangGraph agents.
Tools are decorated with @ai_tool and return LangChain BaseTool instances.
"""

import logging

from langchain_core.tools import BaseTool

from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext

logger = logging.getLogger(__name__)

_cached_tools: list[BaseTool] | None = None


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
            # Standard mode: LOW and HIGH allowed. CRITICAL blocked.
            # Include all tools - approval/blocking handled by InterruptNode
            filtered_tools.append(tool)
        else:
            # Expert mode allows all tools
            filtered_tools.append(tool)

    logger.info(
        f"Filtered {len(tools)} tools down to {len(filtered_tools)} for execution_mode={execution_mode.value}"
    )
    return filtered_tools


def filter_tools_by_role(
    tools: list[BaseTool],
    role: str,
) -> list[BaseTool]:
    """Filter tools based on assistant RBAC role permissions.

    Removes tools whose required permissions are not granted by the role.
    Tools without permissions metadata are always allowed.

    Args:
        tools: List of tools to filter
        role: RBAC role string (e.g., "ai-viewer", "ai-manager", "ai-admin")

    Returns:
        Filtered list of tools the role is permitted to use
    """
    from app.core.rbac import get_rbac_service

    rbac_service = get_rbac_service()
    filtered: list[BaseTool] = []

    for tool in tools:
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None or not metadata.permissions:
            # No permissions required -- always allow
            filtered.append(tool)
            continue

        # Check ALL required permissions for this tool
        has_all = all(
            rbac_service.has_permission(role, perm)
            for perm in metadata.permissions
        )
        if has_all:
            filtered.append(tool)
        else:
            logger.debug(
                f"Filtering out tool '{tool.name}' -- "
                f"role '{role}' lacks required permissions: {metadata.permissions}"
            )

    logger.info(
        f"Filtered {len(tools)} tools down to {len(filtered)} for role={role}"
    )
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
    from app.ai.tools import context_tools, project_tools, temporal_tools
    from app.ai.tools.templates import (
        advanced_analysis_template,
        analysis_template,
        change_order_template,
        cost_element_template,
        crud_template,
        diagram_template,
        forecast_cost_progress_template,
        user_management_template,
    )

    # Collect all tools from project_tools (production tools)
    tools: list[BaseTool] = [
        project_tools.list_projects,
        project_tools.get_project,
        project_tools.global_search,
    ]

    # Add context tools (read-only for LLM awareness)
    context_tools_list = [
        temporal_tools.get_temporal_context,
        context_tools.get_project_context,
        context_tools.get_project_structure,
    ]
    tools.extend(context_tools_list)

    # Add tools from crud_template (Project and WBE CRUD operations)
    # Note: list_projects and get_project are duplicates, so we only add unique ones
    crud_tools = [
        crud_template.create_project,
        crud_template.update_project,
        crud_template.list_wbes,
        crud_template.get_wbe,
        crud_template.create_wbe,
        crud_template.update_wbe,
    ]
    tools.extend(crud_tools)

    # Add tools from analysis_template (EVM and Forecasting)
    analysis_tools = [
        analysis_template.calculate_evm_metrics,
        analysis_template.get_evm_performance_summary,
        analysis_template.analyze_cost_variance,
        analysis_template.analyze_schedule_variance,
        analysis_template.generate_project_forecast,
        analysis_template.compare_forecast_scenarios,
        analysis_template.get_forecast_accuracy,
        analysis_template.get_project_kpis,
    ]
    tools.extend(analysis_tools)

    # Add tools from change_order_template (Change Order management)
    change_order_tools = [
        change_order_template.list_change_orders,
        change_order_template.get_change_order,
        change_order_template.create_change_order,
        change_order_template.generate_change_order_draft,
        change_order_template.submit_change_order_for_approval,
        change_order_template.approve_change_order,
        change_order_template.reject_change_order,
        change_order_template.analyze_change_order_impact,
    ]
    tools.extend(change_order_tools)

    # Add tools from cost_element_template (Cost Element, Schedule Baseline, Cost Element Type CRUD)
    cost_element_tools = [
        cost_element_template.list_cost_elements,
        cost_element_template.get_cost_element,
        cost_element_template.create_cost_element,
        cost_element_template.update_cost_element,
        cost_element_template.delete_cost_element,
        cost_element_template.get_schedule_baseline,
        cost_element_template.update_schedule_baseline,
        cost_element_template.delete_schedule_baseline,
        cost_element_template.list_cost_element_types,
        cost_element_template.get_cost_element_type,
        cost_element_template.create_cost_element_type,
        cost_element_template.update_cost_element_type,
        cost_element_template.delete_cost_element_type,
    ]
    tools.extend(cost_element_tools)

    # Add tools from user_management_template (User and Department CRUD)
    user_management_tools = [
        user_management_template.list_users,
        user_management_template.get_user,
        user_management_template.create_user,
        user_management_template.update_user,
        user_management_template.delete_user,
        user_management_template.list_departments,
        user_management_template.get_department,
        user_management_template.create_department,
        user_management_template.update_department,
        user_management_template.delete_department,
    ]
    tools.extend(user_management_tools)

    # Add tools from advanced_analysis_template (Advanced analysis and insights)
    advanced_analysis_tools = [
        advanced_analysis_template.assess_project_health,
        advanced_analysis_template.detect_evm_anomalies,
        advanced_analysis_template.analyze_forecast_trends,
        advanced_analysis_template.generate_optimization_suggestions,
    ]
    tools.extend(advanced_analysis_tools)

    # Add tools from diagram_template (Mermaid diagram generation)
    diagram_tools = [
        diagram_template.generate_mermaid_diagram,
    ]
    tools.extend(diagram_tools)

    # Add tools from forecast_cost_progress_template (Forecast, Cost Registration, Progress Entry)
    forecast_cost_progress_tools = [
        forecast_cost_progress_template.get_forecast,
        forecast_cost_progress_template.create_forecast,
        forecast_cost_progress_template.update_forecast,
        forecast_cost_progress_template.compare_forecast_to_budget,
        forecast_cost_progress_template.get_budget_status,
        forecast_cost_progress_template.create_cost_registration,
        forecast_cost_progress_template.list_cost_registrations,
        forecast_cost_progress_template.get_cost_registration,
        forecast_cost_progress_template.update_cost_registration,
        forecast_cost_progress_template.delete_cost_registration,
        forecast_cost_progress_template.get_cost_trends,
        forecast_cost_progress_template.get_cumulative_costs,
        forecast_cost_progress_template.list_progress_entries,
        forecast_cost_progress_template.get_latest_progress,
        forecast_cost_progress_template.create_progress_entry,
        forecast_cost_progress_template.get_progress_entry,
        forecast_cost_progress_template.update_progress_entry,
        forecast_cost_progress_template.delete_progress_entry,
        forecast_cost_progress_template.get_progress_history,
        forecast_cost_progress_template.get_cost_element_summary,
    ]
    tools.extend(forecast_cost_progress_tools)

    # Filter to only BaseTool instances
    base_tools: list[BaseTool] = [tool for tool in tools if isinstance(tool, BaseTool)]

    _cached_tools = base_tools
    logger.info(f"Created and cached {len(base_tools)} tools for AI chat")
    return base_tools


# Re-export for backwards compatibility
__all__ = [
    "create_project_tools",
    "filter_tools_by_execution_mode",
    "filter_tools_by_role",
    "ToolContext",
    "list_projects",
    "get_project",
]
