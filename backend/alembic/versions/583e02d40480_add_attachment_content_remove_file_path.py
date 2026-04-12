"""add_attachment_content_remove_file_path

Revision ID: 583e02d40480
Revises: 4b64f142cdf3
Create Date: 2026-04-12 21:25:34.368067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '583e02d40480'
down_revision: Union[str, Sequence[str], None] = '4b64f142cdf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add content column and remove file_path from ai_conversation_attachments."""
    op.add_column(
        'ai_conversation_attachments',
        sa.Column('content', sa.Text(), nullable=True),
    )
    op.drop_column('ai_conversation_attachments', 'file_path')


def downgrade() -> None:
    """Restore file_path column and remove content from ai_conversation_attachments."""
    op.add_column(
        'ai_conversation_attachments',
        sa.Column('file_path', sa.VARCHAR(length=500), autoincrement=False, nullable=False),
    )
    op.drop_column('ai_conversation_attachments', 'content')
