"""add enforce_budget to project_budget_settings

Revision ID: d270ea9e1bd8
Revises: 49226017fda2
Create Date: 2026-04-17 00:16:04.991327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd270ea9e1bd8'
down_revision: Union[str, Sequence[str], None] = '49226017fda2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'project_budget_settings',
        sa.Column(
            'enforce_budget',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('project_budget_settings', 'enforce_budget')
