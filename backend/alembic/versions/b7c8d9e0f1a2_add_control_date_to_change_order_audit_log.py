"""add control_date to change_order_audit_log

Revision ID: b7c8d9e0f1a2
Revises: 03b4089c06af
Create Date: 2026-02-27 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "03b4089c06af"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add control_date column to change_order_audit_log table."""
    # Add control_date column with default to now() for backward compatibility
    # Existing rows will get control_date = changed_at via the server_default
    op.add_column(
        "change_order_audit_log",
        sa.Column(
            "control_date",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Control date for the workflow operation (business/logical time)",
        ),
    )

    # Create index for efficient control_date queries
    # Used by ControlDateValidator to find last operation's control_date
    op.create_index(
        "idx_change_order_audit_log_control_date",
        "change_order_audit_log",
        ["change_order_id", sa.text("control_date DESC")],
    )


def downgrade() -> None:
    """Remove control_date column from change_order_audit_log table."""
    op.drop_index(
        "idx_change_order_audit_log_control_date",
        table_name="change_order_audit_log",
    )
    op.drop_column("change_order_audit_log", "control_date")
