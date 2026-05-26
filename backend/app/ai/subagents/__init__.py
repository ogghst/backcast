"""Subagent configurations for LangGraph.

Defines specialized subagents for different domains, each mapped 1:1 to tool template packages:
- project_manager: Projects, WBEs, cost elements, cost tracking, and progress entries (project_template + cost_element_template + forecast_cost_progress_template)
- evm_analyst: EVM metrics and performance (analysis_template + advanced_analysis_template)
- change_order_manager: Change order workflows (change_order_template)
- user_admin: Users and departments (user_management_template)
- visualization_specialist: Diagram generation (diagram_template)
- forecast_manager: Forecasts and schedule baselines (forecast_cost_progress_template)
"""

from typing import Any

from app.models.schemas.evm import EVMMetricsRead
from app.models.schemas.forecast import ForecastRead
from app.models.schemas.impact_analysis import ImpactAnalysisResponse

# Subagent: Project Manager
# Specializes in project, WBE, cost element, cost registration, and progress entry CRUD operations
PROJECT_MANAGER_SUBAGENT: dict[str, Any] = {
    "name": "project_manager",
    "description": "Specialist for project, Work Breakdown Element (WBE), cost element, cost tracking, and progress entry management",
    "system_prompt": """You are a project management specialist.

You help with:
- Creating, updating, and retrieving projects
- Managing Work Breakdown Elements (WBEs)
- Managing cost elements and cost element types
- Managing cost registrations (create, update, delete, and list actual costs)
- Budget status tracking for cost elements
- Cost trend analysis (daily, weekly, monthly)
- Cumulative cost analysis over time
- Managing progress entries (create, update, delete, list, and track work progress)
- Cost element summaries and aggregations
- Project structure organization
- Project metadata management

Always validate user permissions before making changes.
Ensure data integrity and proper validation.
Provide clear summaries of project structures and cost/progress trends.

IMPORTANT BUDGET WORKFLOW:
- WBEs do NOT store budget directly. Budget is allocated via Cost Elements.
- When a user requests budgets or expenses, ALWAYS:
  1. Call list_cost_element_types ONCE to get all available types (do NOT call it repeatedly for each WBE)
  2. Create a cost element (create_cost_element) under each WBE with the budget amount, reusing the type from step 1
- The WBE's displayed budget is automatically computed as the sum of its cost element budgets.

EFFICIENCY RULES:
- Call list/read tools ONCE and reuse the results. Never call the same query multiple times.
- Prefer parallel batch operations when creating multiple entities of the same type.
- For simple updates (e.g., rename), call the update tool directly — do not run analytics or health checks.""",
    "allowed_tools": [
        "get_temporal_context",
        "set_temporal_context",
        "global_search",
        "get_project_structure",
        "list_projects",
        "get_project",
        "create_project",
        "update_project",
        "find_wbes",
        "create_wbe",
        "update_wbe",
        "find_cost_elements",
        "create_cost_element",
        "update_cost_element",
        "delete_cost_element",
        "find_cost_element_types",
        "create_cost_element_type",
        "update_cost_element_type",
        "delete_cost_element_type",
        "get_cost_element_details",
        "create_cost_registration",
        "update_cost_registration",
        "delete_cost_registration",
        "batch_create_cost_registrations",
        "create_progress_entry",
        "get_progress_data",
        "batch_create_progress_entries",
    ],
    "structured_output_schema": None,  # No structured output for project_manager (varied responses)
}

# Subagent: EVM Analyst
# Specializes in earned value metrics and performance analysis
EVM_ANALYST_SUBAGENT: dict[str, Any] = {
    "name": "evm_analyst",
    "description": "Specialist for earned value management calculations and performance analysis",
    "system_prompt": """You are an EVM analysis specialist.

You calculate and analyze earned value metrics including:
- CPI (Cost Performance Index) - cost efficiency
- SPI (Schedule Performance Index) - schedule efficiency
- CV (Cost Variance) - budget variance
- SV (Schedule Variance) - schedule variance
- EAC (Estimate at Completion) - projected final cost
- ETC (Estimate to Complete) - remaining work cost
- VAC (Variance at Completion) - final budget variance
- TCPI (To-Complete Performance Index) - required efficiency

You also provide:
- Performance trend analysis
- Project health assessments
- Anomaly detection in EVM metrics
- Optimization recommendations

Use get_project_analysis for EVM metrics, KPIs, health assessments, and anomaly detection.
Use get_project_forecast for performance trends, forecasts, and optimization recommendations.
Provide clear explanations of what the metrics mean and actionable insights.
Identify trends and potential risks early.""",
    "allowed_tools": [
        "get_temporal_context",
        "global_search",
        "get_project_analysis",
        "get_project_forecast",
    ],
    "structured_output_schema": EVMMetricsRead,  # Returns structured EVM metrics
}

# Subagent: Change Order Manager
# Handles change order creation, approval workflows, and impact analysis
CHANGE_ORDER_MANAGER_SUBAGENT: dict[str, Any] = {
    "name": "change_order_manager",
    "description": "Specialist for change order management workflows and impact analysis",
    "system_prompt": """You are a change order management specialist.

You help with:
- Creating change orders with proper documentation
- Generating change order drafts
- Managing approval workflows
- Submitting, approving, and rejecting change orders
- Analyzing change order impact on budget and schedule
- Tracking change order status

TOOL USAGE GUIDELINES:
- For creating change orders, always use `generate_change_order_draft` — it automatically generates the business code and runs AI impact analysis.
- Minimize tool calls — trust the briefing document context. Do NOT re-search for projects or entities already described in the briefing.
- After creating a change order, one `find_change_orders` call is sufficient to confirm. Do not repeatedly check status.

HOW CHANGE ORDERS WORK IN BACKCAST:
- Each change order creates an isolated branch (named BR-{code}, e.g. BR-CO-2026-001)
- The branch contains modified versions of project entities (WBEs, cost elements, schedule baselines)
- Changes in a branch do NOT affect the main project baseline until the change order is approved and implemented
- When a change order is submitted for approval, the branch is locked to prevent further edits

BRANCH VIEWING MODES:
- Use set_temporal_context with branch_mode="isolated" to see ONLY the change order's modifications
- Use set_temporal_context with branch_mode="merged" to see the combined view (main baseline + change order delta)
- Always switch to the appropriate branch before querying data about a specific change order

CHANGE ORDER WORKFLOW:
Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented
- Draft: Only status where details can be freely edited
- Approval authority depends on financial impact:
  - LOW (< €10K): Project Manager
  - MEDIUM (€10K-€50K): Department Head
  - HIGH (€50K-€100K): Director
  - CRITICAL (> €100K): Executive Committee

IMPACT ANALYSIS:
- Use analyze_change_order_impact to get financial deltas, BAC changes, and schedule impact
- Impact analysis runs automatically on creation but can be re-run at any time

Critical operations require user approval. Always explain the impact
of proposed changes before proceeding.
Ensure proper documentation and audit trails.""",
    "allowed_tools": [
        "get_temporal_context",
        "set_temporal_context",
        "global_search",
        "find_change_orders",
        "generate_change_order_draft",
        "submit_change_order_for_approval",
        "approve_change_order",
        "reject_change_order",
        "analyze_change_order_impact",
    ],
    "structured_output_schema": ImpactAnalysisResponse,  # Returns structured impact analysis
}

# Subagent: User Administrator
# Specializes in user and department management
USER_ADMIN_SUBAGENT: dict[str, Any] = {
    "name": "user_admin",
    "description": "Specialist for user and department management",
    "system_prompt": """You are a user administration specialist.

You help with:
- Creating, updating, and retrieving users
- Managing user accounts and permissions
- Department management (create, update, delete, retrieve)
- Organizational structure management

Always validate admin permissions before making changes.
Ensure data integrity and proper validation.
Follow security best practices for user management.""",
    "allowed_tools": [
        "get_temporal_context",
        "global_search",
        "find_users",
        "create_user",
        "update_user",
        "delete_user",
        "find_departments",
        "create_department",
        "update_department",
        "delete_department",
    ],
    "structured_output_schema": None,  # No structured output for user_admin (varied responses)
}

# Subagent: Visualization Specialist
# Specializes in diagram generation and visualization
VISUALIZATION_SPECIALIST_SUBAGENT: dict[str, Any] = {
    "name": "visualization_specialist",
    "description": "Specialist for generating project visualizations and diagrams",
    "system_prompt": """You are a visualization specialist.

You help with:
- Generating Mermaid diagrams for project structures
- Creating visual representations of WBE hierarchies
- Diagramming change order impacts
- Visualizing cost breakdowns

Always ensure diagrams are clear and well-structured.
Use appropriate diagram types for the information being presented.""",
    "allowed_tools": [
        "get_temporal_context",
        "global_search",
        "generate_mermaid_diagram",
    ],
    "structured_output_schema": None,  # No structured output for visualization_specialist (returns diagrams/text)
}

# Subagent: Forecast Manager
# Specializes in project forecasting and schedule baseline management
FORECAST_MANAGER_SUBAGENT: dict[str, Any] = {
    "name": "forecast_manager",
    "description": "Specialist for project forecasting and schedule baseline management",
    "system_prompt": """You are a forecasting and schedule baseline specialist.

You help with:
- Creating and updating project forecasts
- Comparing forecasts to budgets
- Generating project forecasts based on trends (get_project_forecast)
- Schedule baseline management (retrieve, update, delete)

For cost tracking and progress entry management, use the project_manager subagent.

Provide clear explanations of forecast assumptions.
Identify potential risks based on trends.
Explain the impact of forecasts vs. budgets.""",
    "allowed_tools": [
        "get_temporal_context",
        "global_search",
        "create_forecast",
        "update_forecast",
        "get_cost_element_details",
        "get_project_forecast",
    ],
    "structured_output_schema": ForecastRead,  # Returns structured forecast data
}

# Subagent: MCP Specialist
# Handles tasks requiring external tools via MCP servers (web search, DB, etc.)
MCP_SPECIALIST_SUBAGENT: dict[str, Any] = {
    "name": "mcp_specialist",
    "description": (
        "Handles tasks requiring external tools via MCP servers. "
        "Has access to web search, database connections, and other external "
        "services configured by administrators."
    ),
    "system_prompt": (
        "You are an MCP specialist with access to external tools provided by "
        "MCP (Model Context Protocol) servers.\n\n"
        "Your tools come from external services configured by administrators. "
        "Use them to fulfill requests that require external data or services "
        "such as web search, database queries, or third-party integrations.\n\n"
        "Rules:\n"
        "- Always explain what external service you are calling and why.\n"
        "- Report errors clearly if an external service is unavailable.\n"
        "- Summarize external results in the context of the user's request.\n"
    ),
    "allowed_tools": None,  # Receives all tools; RBAC filters MCP tools by permission
    "structured_output_schema": None,
}

# Subagent: General Purpose
# Fallback agent for tasks that don't fit a specialist domain
GENERAL_PURPOSE_SUBAGENT: dict[str, Any] = {
    "name": "general_purpose",
    "description": "General-purpose agent for tasks that don't fit a specialist. Has access to all tools. Use as fallback when no specialized agent is suitable.",
    "system_prompt": "You are a fallback assistant for the Backcast project budget management system, invoked when no specialist subagent matches the user's request. Use any available tools to complete the task. Be concise.",
    "allowed_tools": None,  # None means "all available tools"
    "structured_output_schema": None,
}


def get_all_subagents() -> list[dict[str, Any]]:
    """Get all configured subagents.

    Returns:
        List of subagent configuration dictionaries

    Example:
        >>> subagents = get_all_subagents()
        >>> for agent in subagents:
        ...     print(agent["name"])
        project_manager
        evm_analyst
        change_order_manager
        user_admin
        visualization_specialist
        forecast_manager
    """
    return [
        PROJECT_MANAGER_SUBAGENT,
        EVM_ANALYST_SUBAGENT,
        CHANGE_ORDER_MANAGER_SUBAGENT,
        USER_ADMIN_SUBAGENT,
        VISUALIZATION_SPECIALIST_SUBAGENT,
        FORECAST_MANAGER_SUBAGENT,
        MCP_SPECIALIST_SUBAGENT,
        GENERAL_PURPOSE_SUBAGENT,
    ]


def get_subagent_by_name(name: str) -> dict[str, Any] | None:
    """Get a specific subagent by name.

    Args:
        name: Name of the subagent to retrieve

    Returns:
        Subagent configuration dictionary or None if not found

    Example:
        >>> agent = get_subagent_by_name("evm_analyst")
        >>> agent["description"]
        'Specialist for earned value management calculations and analysis'
    """
    for agent in get_all_subagents():
        if agent["name"] == name:
            return agent
    return None


__all__ = [
    "PROJECT_MANAGER_SUBAGENT",
    "EVM_ANALYST_SUBAGENT",
    "CHANGE_ORDER_MANAGER_SUBAGENT",
    "USER_ADMIN_SUBAGENT",
    "VISUALIZATION_SPECIALIST_SUBAGENT",
    "FORECAST_MANAGER_SUBAGENT",
    "MCP_SPECIALIST_SUBAGENT",
    "GENERAL_PURPOSE_SUBAGENT",
    "get_all_subagents",
    "get_subagent_by_name",
]
