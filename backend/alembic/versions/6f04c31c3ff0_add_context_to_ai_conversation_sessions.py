"""add_context_to_ai_conversation_sessions

Revision ID: 6f04c31c3ff0
Revises: 20260413_add_project_structure
Create Date: 2026-04-13 22:34:54.247772

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6f04c31c3ff0'
down_revision: str | Sequence[str] | None = '20260413_add_project_structure'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Add context jsonb column to ai_conversation_sessions table.
    Set default value for existing rows.
    Create composite index on (user_id, context->>'type').
    """
    # Add context column as nullable first
    op.add_column(
        'ai_conversation_sessions',
        sa.Column(
            'context',
            sa.JSON(),
            nullable=True,
            comment='Session context (type, id, name)'
        )
    )

    # Set default value for existing rows
    op.execute(
        "UPDATE ai_conversation_sessions SET context = '{\"type\": \"general\"}'::jsonb "
        "WHERE context IS NULL"
    )

    # Now make the column non-nullable with default
    op.alter_column(
        'ai_conversation_sessions',
        'context',
        nullable=False,
        server_default=sa.text("'{\"type\": \"general\"}'::jsonb")
    )

    # Create composite index on (user_id, context->>'type')
    # This index supports efficient filtering by user and context type
    op.execute(
        'CREATE INDEX idx_ai_conversation_sessions_user_context_type '
        'ON ai_conversation_sessions ((context->>\'type\')) '
        'WHERE user_id IS NOT NULL'
    )


def downgrade() -> None:
    """Downgrade schema.

    Remove context column and index.
    """
    # Drop the index
    op.execute('DROP INDEX IF EXISTS idx_ai_conversation_sessions_user_context_type')

    # Remove the default value
    op.alter_column(
        'ai_conversation_sessions',
        'context',
        server_default=None
    )

    # Drop the column
    op.drop_column('ai_conversation_sessions', 'context')
