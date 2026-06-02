"""Add planner_prompt to assistant_configs

Revision ID: 20260601_planner_prompt
Revises: None (standalone migration for feature branch)
Create Date: 2026-06-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260601_planner_prompt"
down_revision: Union[str, None] = None
# Standalone migration for the feature branch.
# When merging to main, set down_revision to the appropriate head.
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Add planner_prompt column to ai_assistant_configs."""
    op.add_column(
        "ai_assistant_configs",
        sa.Column("planner_prompt", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove planner_prompt column from ai_assistant_configs."""
    op.drop_column("ai_assistant_configs", "planner_prompt")
