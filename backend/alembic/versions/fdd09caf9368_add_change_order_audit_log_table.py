"""add change_order_audit_log table

Revision ID: fdd09caf9368
Revises: add_branches_table
Create Date: 2026-01-14 23:47:06.002980

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fdd09caf9368"
down_revision: str | Sequence[str] | None = "add_branches_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add change_order_audit_log table."""
    op.create_table(
        "change_order_audit_log",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column(
            "change_order_id",
            postgresql.UUID(),
            nullable=False,
            comment="Root UUID of the Change Order",
        ),
        sa.Column(
            "old_status",
            sa.String(length=50),
            nullable=False,
            comment="Previous status value",
        ),
        sa.Column(
            "new_status",
            sa.String(length=50),
            nullable=False,
            comment="New status value",
        ),
        sa.Column(
            "comment",
            sa.Text(),
            nullable=True,
            comment="Optional comment for the transition",
        ),
        sa.Column("changed_by", postgresql.UUID(), nullable=False),
        sa.Column(
            "changed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_change_order_audit_log_change_order_id"),
        "change_order_audit_log",
        ["change_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_order_audit_log_changed_by"),
        "change_order_audit_log",
        ["changed_by"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema - remove change_order_audit_log table."""
    op.drop_index(
        op.f("ix_change_order_audit_log_changed_by"),
        table_name="change_order_audit_log",
    )
    op.drop_index(
        op.f("ix_change_order_audit_log_change_order_id"),
        table_name="change_order_audit_log",
    )
    op.drop_table("change_order_audit_log")
