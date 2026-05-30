"""AI Tool Templates for various domain operations.

All tools use the @ai_tool decorator with LangChain's InjectedToolArg
for proper context injection and docstring parsing.
"""

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

__all__ = [
    "advanced_analysis_template",
    "analysis_template",
    "change_order_template",
    "control_account_template",
    "cost_element_template",
    "cost_event_template",
    "cost_event_type_template",
    "diagram_template",
    "forecast_cost_progress_template",
    "project_template",
    "user_management_template",
    "work_package_template",
]
