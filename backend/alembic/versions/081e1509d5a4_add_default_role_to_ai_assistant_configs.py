"""add default_role to ai_assistant_configs

Revision ID: 081e1509d5a4
Revises: 35987dee63b3
Create Date: 2026-04-23 14:33:25.275087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '081e1509d5a4'
down_revision: Union[str, Sequence[str], None] = '35987dee63b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add default_role column to ai_assistant_configs."""
    op.add_column(
        'ai_assistant_configs',
        sa.Column(
            'default_role',
            sa.String(length=50),
            nullable=True,
            comment='RBAC role for permission filtering (e.g., ai-viewer, ai-manager, ai-admin)',
        ),
    )


def downgrade() -> None:
    """Remove default_role column from ai_assistant_configs."""
    op.drop_column('ai_assistant_configs', 'default_role')
