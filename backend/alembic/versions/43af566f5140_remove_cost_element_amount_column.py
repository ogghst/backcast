"""remove cost_element amount column

Revision ID: 43af566f5140
Revises: c115477454ca
Create Date: 2026-05-30 15:15:26.977771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43af566f5140'
down_revision: Union[str, Sequence[str], None] = 'c115477454ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove amount column from cost_elements — budget lives on WorkPackage.budget_amount."""
    op.drop_column('cost_elements', 'amount')


def downgrade() -> None:
    """Restore amount column on cost_elements."""
    op.add_column(
        'cost_elements',
        sa.Column(
            'amount',
            sa.NUMERIC(precision=15, scale=2),
            server_default=sa.text('0'),
            autoincrement=False,
            nullable=False,
        ),
    )
