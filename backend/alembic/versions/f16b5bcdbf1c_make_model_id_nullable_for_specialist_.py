"""make model_id nullable for specialist agents

Revision ID: f16b5bcdbf1c
Revises: 70793b2368af
Create Date: 2026-05-25 08:09:53.032305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f16b5bcdbf1c'
down_revision: Union[str, Sequence[str], None] = '70793b2368af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'ai_assistant_configs',
        'model_id',
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'ai_assistant_configs',
        'model_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
