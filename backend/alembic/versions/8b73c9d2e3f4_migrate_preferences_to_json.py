"""Migrate preferences to JSON column

Revision ID: 8b73c9d2e3f4
Revises: 7172847aa226
Create Date: 2026-01-03 01:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b73c9d2e3f4"
down_revision: str | Sequence[str] | None = "3c4d5e6f7a8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: Add preferences JSONB column and drop user_preferences table."""
    # Add preferences JSONB column to users table
    op.add_column(
        "users",
        sa.Column(
            "preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )

    # Drop the old user_preferences table (data will be lost as per user confirmation)
    op.drop_table("user_preferences")


def downgrade() -> None:
    """Downgrade schema: Recreate user_preferences table and remove JSON column."""
    # Recreate user_preferences table
    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("theme", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Remove preferences column from users
    op.drop_column("users", "preferences")
