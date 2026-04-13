"""Add get_project_structure tool to assistant configs.

Adds the new get_project_structure context tool to the Friendly Project Analyzer
and Senior Project Manager assistant configurations.

Revision ID: 20260413_add_project_structure
Revises: 583e02d40480
Create Date: 2026-04-13

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260413_add_project_structure'
down_revision: str | Sequence[str] | None = '583e02d40480'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TOOL = 'get_project_structure'

ASSISTANT_IDS = [
    '77777777-7777-7777-7777-777777777777',  # Friendly Project Analyzer
    '88888888-8888-8888-8888-888888888888',  # Senior Project Manager
]


def upgrade() -> None:
    """Add get_project_structure tool to assistant configs."""
    conn = op.get_bind()

    for assistant_id in ASSISTANT_IDS:
        result = conn.execute(
            sa.text("SELECT allowed_tools FROM ai_assistant_configs WHERE id = :id"),
            {"id": assistant_id},
        )
        row = result.fetchone()

        if row is None:
            continue

        current_tools = row[0]

        if NEW_TOOL in current_tools:
            continue

        conn.execute(
            sa.text("""
                UPDATE ai_assistant_configs
                SET allowed_tools = allowed_tools || :new_tool
                WHERE id = :id
            """),
            {"new_tool": [NEW_TOOL], "id": assistant_id},
        )


def downgrade() -> None:
    """Remove get_project_structure tool from assistant configs."""
    conn = op.get_bind()

    for assistant_id in ASSISTANT_IDS:
        conn.execute(
            sa.text("""
                UPDATE ai_assistant_configs
                SET allowed_tools = array_remove(allowed_tools, :tool)
                WHERE id = :id
            """),
            {"tool": NEW_TOOL, "id": assistant_id},
        )
