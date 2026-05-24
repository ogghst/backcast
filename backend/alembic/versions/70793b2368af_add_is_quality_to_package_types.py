"""add_is_quality_to_package_types

Revision ID: 70793b2368af
Revises: a5f161337f03
Create Date: 2026-05-24 08:40:36.998853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70793b2368af'
down_revision: Union[str, Sequence[str], None] = 'a5f161337f03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_quality boolean column to package_types and backfill quality_impact rows."""
    op.add_column(
        "package_types",
        sa.Column("is_quality", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE package_types SET is_quality = true WHERE code = 'quality_impact'")


def downgrade() -> None:
    """Remove is_quality column from package_types."""
    op.drop_column("package_types", "is_quality")
