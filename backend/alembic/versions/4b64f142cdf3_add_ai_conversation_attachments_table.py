"""add ai_conversation_attachments table

Revision ID: 4b64f142cdf3
Revises: 20260405_add_dashboard_layouts
Create Date: 2026-04-11 12:20:02.531134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b64f142cdf3'
down_revision: Union[str, Sequence[str], None] = '20260405_add_dashboard_layouts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ai_conversation_attachments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['ai_conversation_messages.id'], name=op.f('fk_ai_conversation_attachments_message_id')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_conversation_attachments'))
    )
    op.create_index(op.f('ix_ai_conversation_attachments_message_id'), 'ai_conversation_attachments', ['message_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ai_conversation_attachments_message_id'), table_name='ai_conversation_attachments')
    op.drop_table('ai_conversation_attachments')
