"""AI Tool Templates for various domain operations.

This package contains template modules for AI tools:
- crud_template: Project and WBE CRUD operations
- analysis_template: EVM and Forecasting analysis tools
- change_order_template: Change order management tools

All tools use the @ai_tool decorator with LangChain's InjectedToolArg
for proper context injection and docstring parsing.
"""

from app.ai.tools.templates import (
    analysis_template,
    change_order_template,
    crud_template,
)

__all__ = [
    "analysis_template",
    "change_order_template",
    "crud_template",
]
