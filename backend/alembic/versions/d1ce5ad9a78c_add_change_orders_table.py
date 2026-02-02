"""add change_orders table

Revision ID: d1ce5ad9a78c
Revises: 5ae1f9320c4b
Create Date: 2026-01-12 07:32:48.080042

Simplified migration to only add change_orders table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1ce5ad9a78c"
down_revision: str | Sequence[str] | None = "5ae1f9320c4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add change_orders table."""
    # Create change_orders table with TSTZRANGE fields
    op.create_table(
        "change_orders",
        sa.Column(
            "change_order_id",
            postgresql.UUID(),
            nullable=False,
            comment="Root UUID identifier for EVCS versioning",
        ),
        sa.Column(
            "code",
            sa.String(length=50),
            nullable=False,
            comment="Business identifier (e.g., CO-2026-001)",
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(),
            nullable=False,
            comment="Reference to the Project this change applies to",
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
            comment="Brief title of the change",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Detailed description of what the change entails",
        ),
        sa.Column(
            "justification",
            sa.Text(),
            nullable=True,
            comment="Business justification for the change",
        ),
        sa.Column(
            "effective_date",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When the change should take effect",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="Draft",
            comment="Workflow state",
        ),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column(
            "valid_time",
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column(
            "transaction_time",
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(), nullable=False),
        sa.Column("deleted_by", postgresql.UUID(), nullable=True),
        sa.Column(
            "branch", sa.String(length=80), nullable=False, server_default="main"
        ),
        sa.Column("parent_id", postgresql.UUID(), nullable=True),
        sa.Column("merge_from_branch", sa.String(length=80), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    # Note: code is NOT unique because the same code appears in multiple branches
    # (main, co-CO-001, co-CO-002, etc.)
    op.create_index(
        op.f("ix_change_orders_change_order_id"),
        "change_orders",
        ["change_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_orders_code"), "change_orders", ["code"], unique=False
    )
    op.create_index(
        op.f("ix_change_orders_project_id"),
        "change_orders",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_orders_created_by"),
        "change_orders",
        ["created_by"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema - remove change_orders table."""
    op.drop_index(op.f("ix_change_orders_created_by"), table_name="change_orders")
    op.drop_index(op.f("ix_change_orders_project_id"), table_name="change_orders")
    op.drop_index(op.f("ix_change_orders_code"), table_name="change_orders")
    op.drop_index(op.f("ix_change_orders_change_order_id"), table_name="change_orders")
    op.drop_table("change_orders")
