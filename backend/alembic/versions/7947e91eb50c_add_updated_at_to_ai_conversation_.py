"""add_updated_at_to_ai_conversation_messages

Revision ID: 7947e91eb50c
Revises: c65f1ef54182
Create Date: 2026-03-08 23:38:15.788734

This migration fixes a bug in the initial AI tables migration where the
ai_conversation_messages table was missing the updated_at column that
should be present on all SimpleEntityBase tables.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7947e91eb50c'
down_revision: str | Sequence[str] | None = 'c65f1ef54182'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing updated_at column to ai_conversation_messages table."""
    op.add_column(
        'ai_conversation_messages',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Remove updated_at column from ai_conversation_messages table."""
    op.drop_column('ai_conversation_messages', 'updated_at')
