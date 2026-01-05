"""Add password_changed_at to users table

Revision ID: 3c4d5e6f7a8b
Revises: 2ebc6a370a30
Create Date: 2026-01-02 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c4d5e6f7a8b"
down_revision: str | Sequence[str] | None = "2ebc6a370a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add password_changed_at column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    """Remove password_changed_at column from users table."""
    op.drop_column("users", "password_changed_at")
