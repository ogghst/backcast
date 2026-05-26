"""AI Tool Templates for various domain operations.

This package contains template modules for AI tools:
- project_template: Project and WBE CRUD operations
- analysis_template: EVM and Forecasting analysis tools
- advanced_analysis_template: Advanced project analysis and insights
- change_order_template: Change order management tools

All tools use the @ai_tool decorator with LangChain's InjectedToolArg
for proper context injection and docstring parsing.
"""

from app.ai.tools.templates import (
    advanced_analysis_template,
    analysis_template,
    change_order_template,
    cost_element_template,
    diagram_template,
    forecast_cost_progress_template,
    package_type_template,
    project_template,
    user_management_template,
    work_package_template,
)

__all__ = [
    "advanced_analysis_template",
    "analysis_template",
    "change_order_template",
    "cost_element_template",
    "diagram_template",
    "forecast_cost_progress_template",
    "package_type_template",
    "project_template",
    "user_management_template",
    "work_package_template",
]
