"""add_plan_data_to_sessions

Revision ID: bc147fc0eb64
Revises: a1b2c3d4e5f6
Create Date: 2026-06-11 08:22:23.482043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bc147fc0eb64'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add plan_data JSONB column to ai_conversation_sessions."""
    with op.batch_alter_table('ai_conversation_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'plan_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Serialized PlanDocument with execution steps and progress',
        ))


def downgrade() -> None:
    """Remove plan_data column from ai_conversation_sessions."""
    with op.batch_alter_table('ai_conversation_sessions', schema=None) as batch_op:
        batch_op.drop_column('plan_data')
