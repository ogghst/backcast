"""drop_project_budget_column

Revision ID: 35987dee63b3
Revises: 20260417_e05_u07
Create Date: 2026-04-18 14:33:34.327258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35987dee63b3'
down_revision: Union[str, Sequence[str], None] = '20260417_e05_u07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop budget column from projects table."""
    op.drop_column('projects', 'budget')


def downgrade() -> None:
    """Re-add budget column to projects table."""
    op.add_column('projects', sa.Column('budget', sa.Numeric(15, 2), server_default='0'))
