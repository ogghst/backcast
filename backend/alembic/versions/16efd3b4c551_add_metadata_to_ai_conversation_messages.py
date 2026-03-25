"""add metadata to ai_conversation_messages

Revision ID: 16efd3b4c551
Revises: 20250323_add_recursion_limit
Create Date: 2026-03-25 01:18:28.007790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '16efd3b4c551'
down_revision: Union[str, Sequence[str], None] = '20250323_add_recursion_limit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add metadata column to ai_conversation_messages."""
    op.add_column('ai_conversation_messages',
                  sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema - remove metadata column from ai_conversation_messages."""
    op.drop_column('ai_conversation_messages', 'metadata')
