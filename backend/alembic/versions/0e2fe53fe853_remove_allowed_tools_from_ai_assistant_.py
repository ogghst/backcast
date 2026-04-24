"""remove allowed_tools from ai_assistant_configs

Revision ID: 0e2fe53fe853
Revises: 87c3b39736a6
Create Date: 2026-04-24 18:30:19.630094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e2fe53fe853'
down_revision: Union[str, Sequence[str], None] = '87c3b39736a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the allowed_tools column from ai_assistant_configs table
    op.drop_column('ai_assistant_configs', 'allowed_tools')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the allowed_tools column for rollback
    op.add_column(
        'ai_assistant_configs',
        sa.Column(
            'allowed_tools',
            sa.ARRAY(sa.Text()),
            nullable=True
        )
    )
