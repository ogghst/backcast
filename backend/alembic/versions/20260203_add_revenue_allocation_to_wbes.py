"""Add revenue_allocation to wbes table.

Revision ID: 0206_rev_alloc
Revises: 6ca38f4c2cdc
Create Date: 2026-02-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0206_rev_alloc"
down_revision: str | None = "6ca38f4c2cdc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add revenue_allocation column to wbes table."""
    op.add_column(
        "wbes",
        sa.Column(
            "revenue_allocation",
            postgresql.NUMERIC(precision=15, scale=2),
            nullable=True,
            comment="Revenue allocated to this WBE from project contract value",
        ),
    )


def downgrade() -> None:
    """Remove revenue_allocation column from wbes table."""
    op.drop_column("wbes", "revenue_allocation")
