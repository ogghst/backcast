"""add notifications foreign key constraint

Revision ID: 286db0b842be
Revises: 20260509_holiday_custom
Create Date: 2026-05-08 23:07:36.566976

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "286db0b842be"
down_revision: str | Sequence[str] | None = "20260509_holiday_custom"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Add foreign key constraint from notifications.user_id to users.id.
    This ensures referential integrity - notifications cannot reference
    non-existent users.
    """
    op.create_foreign_key(
        "fk_notifications_user_id",
        "notifications",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema.

    Remove the foreign key constraint from notifications.user_id.
    """
    op.drop_constraint("fk_notifications_user_id", "notifications", type_="foreignkey")
