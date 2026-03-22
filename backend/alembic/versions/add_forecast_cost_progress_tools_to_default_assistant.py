"""Add Forecast, Cost Registration, and Progress Entry tools to Default Project Assistant.

This data migration adds the 13 new AI tools from the forecast_cost_progress_template
to the Default Project Assistant configuration.

Revision ID: add_forecast_cost_progress_tools
Revises:
Create Date: 2026-03-22

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_forecast_cost_progress_tools'
down_revision: str | None = '021bb7eeaa21'  # add_project_members_table
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Define the new tools to add
NEW_TOOLS = [
    'get_forecast',
    'create_forecast',
    'update_forecast',
    'compare_forecast_to_budget',
    'get_budget_status',
    'create_cost_registration',
    'list_cost_registrations',
    'get_cost_trends',
    'get_cumulative_costs',
    'get_latest_progress',
    'create_progress_entry',
    'get_progress_history',
    'get_cost_element_summary',
]

DEFAULT_ASSISTANT_ID = '77777777-7777-7777-7777-777777777777'


def upgrade() -> None:
    """Add new tools to the Default Project Assistant configuration.

    This script appends the 13 new Forecast, Cost Registration, and Progress
    Entry tools to the allowed_tools array for the Default Project Assistant.
    """
    # Get the connection
    conn = op.get_bind()

    # Check if the Default Project Assistant exists
    result = conn.execute(
        sa.text("SELECT allowed_tools FROM ai_assistant_configs WHERE id = :id"),
        {"id": DEFAULT_ASSISTANT_ID}
    )
    row = result.fetchone()

    if row is None:
        # Default Assistant doesn't exist, skip migration
        print("Warning: Default Project Assistant not found, skipping migration")
        return

    current_tools = row[0]

    # Filter out tools that are already in the array to avoid duplicates
    tools_to_add = [tool for tool in NEW_TOOLS if tool not in current_tools]

    if not tools_to_add:
        print("All tools already exist in Default Project Assistant configuration")
        return

    # Append the new tools to the existing array
    # Using PostgreSQL array append operator: ||
    conn.execute(
        sa.text("""
            UPDATE ai_assistant_configs
            SET allowed_tools = allowed_tools || :new_tools
            WHERE id = :id
        """),
        {"new_tools": tools_to_add, "id": DEFAULT_ASSISTANT_ID}
    )

    print(f"Added {len(tools_to_add)} new tools to Default Project Assistant: {tools_to_add}")


def downgrade() -> None:
    """Remove the new tools from the Default Project Assistant configuration.

    This removes the 13 Forecast, Cost Registration, and Progress Entry tools
    from the allowed_tools array for the Default Project Assistant.
    """
    conn = op.get_bind()

    # Remove the new tools from the array using array_remove
    # We need to call array_remove for each tool
    for tool in NEW_TOOLS:
        conn.execute(
            sa.text("""
                UPDATE ai_assistant_configs
                SET allowed_tools = array_remove(allowed_tools, :tool)
                WHERE id = :id AND :tool = ANY(allowed_tools)
            """),
            {"tool": tool, "id": DEFAULT_ASSISTANT_ID}
        )

    print(f"Removed {len(NEW_TOOLS)} tools from Default Project Assistant")
