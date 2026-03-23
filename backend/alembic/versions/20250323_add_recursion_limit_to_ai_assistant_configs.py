"""Add recursion_limit field to AIAssistantConfig.

Revision ID: 20250323_add_recursion_limit
Revises: add_forecast_cost_progress_tools
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250323_add_recursion_limit'
down_revision: Union[str, Sequence[str], None] = 'add_forecast_cost_progress_tools'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add recursion_limit column to ai_assistant_configs."""
    op.add_column(
        'ai_assistant_configs',
        sa.Column(
            'recursion_limit',
            sa.Integer(),
            nullable=True,
            comment='LangGraph recursion limit (maximum steps in agent execution loop)'
        )
    )


def downgrade() -> None:
    """Downgrade schema: Remove recursion_limit column from ai_assistant_configs."""
    op.drop_column('ai_assistant_configs', 'recursion_limit')
