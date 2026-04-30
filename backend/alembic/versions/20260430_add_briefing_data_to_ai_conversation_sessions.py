"""add briefing_data to ai_conversation_sessions

Revision ID: 20260430
Revises: d053a34379f4
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260430'
down_revision: Union[str, Sequence[str], None] = 'd053a34379f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Add briefing_data JSONB column to ai_conversation_sessions table
    to persist specialist findings across agent executions.
    """
    op.add_column(
        'ai_conversation_sessions',
        sa.Column(
            'briefing_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Serialized BriefingDocument with accumulated specialist findings'
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ai_conversation_sessions', 'briefing_data')
