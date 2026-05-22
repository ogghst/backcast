"""add_currency_to_projects

Revision ID: 823cf293a68b
Revises: 499a0db5c672
Create Date: 2026-05-19 22:26:51.067090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '823cf293a68b'
down_revision: Union[str, Sequence[str], None] = '499a0db5c672'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add currency column to projects table."""
    op.add_column('projects', sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'))


def downgrade() -> None:
    """Remove currency column from projects table."""
    op.drop_column('projects', 'currency')
