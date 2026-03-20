"""Add project and branch context to AI conversation sessions.

Phase 3E: Session Context Enhancement
- Add project_id column (UUID, nullable, indexed)
- Add branch_id column (UUID, nullable, indexed)

Revision ID: phase3e_session_context
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260320_phase3e_session_context'
down_revision: Union[str, None] = '7947e91eb50c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project_id and branch_id columns to ai_conversation_sessions table."""
    # Add project_id column
    op.add_column(
        'ai_conversation_sessions',
        sa.Column(
            'project_id',
            postgresql.UUID(),
            nullable=True,
            comment='Optional project context'
        )
    )

    # Add index for project_id
    op.create_index(
        'ix_ai_conversation_sessions_project_id',
        'ai_conversation_sessions',
        ['project_id'],
        unique=False
    )

    # Add branch_id column
    op.add_column(
        'ai_conversation_sessions',
        sa.Column(
            'branch_id',
            postgresql.UUID(),
            nullable=True,
            comment='Optional branch or change order context'
        )
    )

    # Add index for branch_id
    op.create_index(
        'ix_ai_conversation_sessions_branch_id',
        'ai_conversation_sessions',
        ['branch_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove project_id and branch_id columns from ai_conversation_sessions table."""
    # Drop indexes
    op.drop_index('ix_ai_conversation_sessions_branch_id', table_name='ai_conversation_sessions')
    op.drop_index('ix_ai_conversation_sessions_project_id', table_name='ai_conversation_sessions')

    # Drop columns
    op.drop_column('ai_conversation_sessions', 'branch_id')
    op.drop_column('ai_conversation_sessions', 'project_id')
