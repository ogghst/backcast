"""Subagent configurations for Deep Agents SDK.

Defines specialized subagents for different domains, each mapped 1:1 to tool template packages:
- project_manager: Projects and WBEs (crud_template)
- evm_analyst: EVM metrics and performance (analysis_template + advanced_analysis_template)
- change_order_manager: Change order workflows (change_order_template)
- cost_controller: Cost elements and schedules (cost_element_template)
- user_admin: Users and departments (user_management_template)
- visualization_specialist: Diagram generation (diagram_template)
- forecast_manager: Forecasts and cost tracking (forecast_cost_progress_template)
"""

from typing import Any

# Subagent: Project Manager
# Specializes in project and WBE CRUD operations
PROJECT_MANAGER_SUBAGENT: dict[str, Any] = {
    "name": "project_manager",
    "description": "Specialist for project and Work Breakdown Element (WBE) management",
    "system_prompt": """You are a project management specialist.

You help with:
- Creating, updating, and retrieving projects
- Managing Work Breakdown Elements (WBEs)
- Project structure organization
- Project metadata management

Always validate user permissions before making changes.
Ensure data integrity and proper validation.
Provide clear summaries of project structures.""",
    "allowed_tools": [
        "list_projects",
        "get_project",
        "create_project",
        "update_project",
        "list_wbes",
        "get_wbe",
        "create_wbe",
    ],
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

Always use the calculate_evm_metrics tool for accurate calculations.
Provide clear explanations of what the metrics mean and actionable insights.
Identify trends and potential risks early.""",
    "allowed_tools": [
        "calculate_evm_metrics",
        "get_evm_performance_summary",
        "analyze_cost_variance",
        "analyze_schedule_variance",
        "get_project_kpis",
        "assess_project_health",
        "detect_evm_anomalies",
        "generate_optimization_suggestions",
    ],
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

Critical operations require user approval. Always explain the impact
of proposed changes before proceeding.
Ensure proper documentation and audit trails.""",
    "allowed_tools": [
        "list_change_orders",
        "get_change_order",
        "create_change_order",
        "generate_change_order_draft",
        "submit_change_order_for_approval",
        "approve_change_order",
        "reject_change_order",
        "analyze_change_order_impact",
    ],
}

# Subagent: Cost Controller
# Specializes in cost elements and schedule baseline management
COST_CONTROLLER_SUBAGENT: dict[str, Any] = {
    "name": "cost_controller",
    "description": "Specialist for cost elements, cost element types, and schedule baseline management",
    "system_prompt": """You are a cost control specialist.

You help with:
- Managing cost elements (create, update, delete, retrieve)
- Managing cost element types (categories and classifications)
- Schedule baseline management (create, update, delete)
- Cost element summaries and aggregations
- Cost structure organization

Always validate user permissions before making changes.
Ensure data integrity and proper validation.
Explain the impact of cost changes on the overall budget.""",
    "allowed_tools": [
        "list_cost_elements",
        "get_cost_element",
        "create_cost_element",
        "update_cost_element",
        "delete_cost_element",
        "get_schedule_baseline",
        "update_schedule_baseline",
        "delete_schedule_baseline",
        "list_cost_element_types",
        "get_cost_element_type",
        "create_cost_element_type",
        "update_cost_element_type",
        "delete_cost_element_type",
        "get_cost_element_summary",
    ],
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
        "list_users",
        "get_user",
        "create_user",
        "update_user",
        "delete_users",
        "list_departments",
        "get_department",
        "create_department",
        "update_department",
        "delete_department",
    ],
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
        "generate_mermaid_diagram",
    ],
}

# Subagent: Forecast Manager
# Specializes in forecasts, cost tracking, and progress management
FORECAST_MANAGER_SUBAGENT: dict[str, Any] = {
    "name": "forecast_manager",
    "description": "Specialist for project forecasting, cost tracking, and progress management",
    "system_prompt": """You are a forecasting and cost tracking specialist.

You help with:
- Creating and updating project forecasts
- Comparing forecasts to budgets
- Generating project forecasts based on trends
- Comparing forecast scenarios
- Analyzing forecast accuracy
- Budget status tracking
- Cost registration and tracking
- Cost trend analysis
- Cumulative cost analysis
- Progress entry and tracking
- Forecast trend analysis

Provide clear explanations of forecast assumptions.
Identify potential risks based on trends.
Explain the impact of actual costs vs. forecasts.""",
    "allowed_tools": [
        "get_forecast",
        "create_forecast",
        "update_forecast",
        "compare_forecast_to_budget",
        "get_budget_status",
        "generate_project_forecast",
        "compare_forecast_scenarios",
        "get_forecast_accuracy",
        "create_cost_registration",
        "list_cost_registrations",
        "get_cost_trends",
        "get_cumulative_costs",
        "get_latest_progress",
        "create_progress_entry",
        "get_progress_history",
        "analyze_forecast_trends",
    ],
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
        cost_controller
        user_admin
        visualization_specialist
        forecast_manager
    """
    return [
        PROJECT_MANAGER_SUBAGENT,
        EVM_ANALYST_SUBAGENT,
        CHANGE_ORDER_MANAGER_SUBAGENT,
        COST_CONTROLLER_SUBAGENT,
        USER_ADMIN_SUBAGENT,
        VISUALIZATION_SPECIALIST_SUBAGENT,
        FORECAST_MANAGER_SUBAGENT,
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
    "COST_CONTROLLER_SUBAGENT",
    "USER_ADMIN_SUBAGENT",
    "VISUALIZATION_SPECIALIST_SUBAGENT",
    "FORECAST_MANAGER_SUBAGENT",
    "get_all_subagents",
    "get_subagent_by_name",
]
