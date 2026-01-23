"""drop schedule_baselines_archive table

Revision ID: 16a1d8c94dd3
Revises: 20260118_100000
Create Date: 2026-01-18 18:35:14.099370

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '16a1d8c94dd3'
down_revision: str | Sequence[str] | None = '20260118_100000'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
