"""add_ai_agent_executions_table

Revision ID: 6c93c299c703
Revises: 20260326_add_refresh_tokens
Create Date: 2026-03-29 05:45:42.116363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c93c299c703'
down_revision: Union[str, Sequence[str], None] = '20260326_add_refresh_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('ai_agent_executions',
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('execution_mode', sa.String(length=20), nullable=False),
    sa.Column('total_tokens', sa.Integer(), nullable=False),
    sa.Column('tool_calls_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['ai_conversation_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_agent_executions_session_id'), 'ai_agent_executions', ['session_id'], unique=False)
    op.add_column('ai_conversation_sessions', sa.Column('active_execution_id', sa.UUID(), nullable=True, comment='Reference to the currently running or last agent execution'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ai_conversation_sessions', 'active_execution_id')
    op.drop_index(op.f('ix_ai_agent_executions_session_id'), table_name='ai_agent_executions')
    op.drop_table('ai_agent_executions')
