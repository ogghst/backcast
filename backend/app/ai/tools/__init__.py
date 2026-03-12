"""AI Tools for natural language queries.

Provides tools that can be used by LangGraph agents.
Tools are decorated with @ai_tool and return LangChain BaseTool instances.
"""

import logging

from langchain_core.tools import BaseTool

from app.ai.tools.project_tools import get_project, list_projects
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


def create_project_tools(context: ToolContext) -> list[BaseTool]:
    """Create LangChain BaseTool instances for all available AI operations.

    Note: This function collects tools from multiple modules. Tools are already
    BaseTool instances from the @ai_tool decorator.

    Args:
        context: Tool context initialized with the authenticated user's session and ID

    Returns:
        List of BaseTool instances ready to be bound to LangGraph agents

    Example:
        ```python
        from app.ai.tools import create_project_tools
        from app.ai.tools.types import ToolContext

        context = ToolContext(session, user_id, user_role="admin")
        tools = create_project_tools(context)

        # Tools can be used directly in LangGraph
        graph = create_graph(llm, tools)
        ```
    """
    # Import tool modules
    from app.ai.tools import project_tools
    from app.ai.tools.templates import (
        analysis_template,
        change_order_template,
        crud_template,
    )

    # Collect all tools from project_tools (production tools)
    tools: list[BaseTool] = [
        project_tools.list_projects,
        project_tools.get_project,
    ]

    # Add tools from crud_template (Project and WBE CRUD operations)
    # Note: list_projects and get_project are duplicates, so we only add unique ones
    crud_tools = [
        crud_template.create_project,
        crud_template.update_project,
        crud_template.list_wbes,
        crud_template.get_wbe,
        crud_template.create_wbe,
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

    # Filter to only BaseTool instances
    base_tools: list[BaseTool] = [
        tool for tool in tools if isinstance(tool, BaseTool)
    ]

    logger.info(f"Created {len(base_tools)} tools for AI chat")
    return base_tools


# Re-export for backwards compatibility
__all__ = [
    "create_project_tools",
    "ToolContext",
    "list_projects",
    "get_project",
]
