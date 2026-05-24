"""merge_heads

Revision ID: a5f161337f03
Revises: 99e3a2d414dd, dedup_dashboard_layouts
Create Date: 2026-05-24 08:40:29.839225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5f161337f03'
down_revision: Union[str, Sequence[str], None] = ('99e3a2d414dd', 'dedup_dashboard_layouts')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
