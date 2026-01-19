"""drop schedule_baselines_archive table

Revision ID: 16a1d8c94dd3
Revises: 20260118_100000
Create Date: 2026-01-18 18:35:14.099370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16a1d8c94dd3'
down_revision: Union[str, Sequence[str], None] = '20260118_100000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('DROP TABLE IF EXISTS schedule_baselines_archive CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    # Note: This only recreates an empty table structure.
    # The actual archived data would be lost if this migration is rolled back.
    op.execute('''
        CREATE TABLE schedule_baselines_archive (
            LIKE schedule_baselines INCLUDING ALL
        )
    ''')
