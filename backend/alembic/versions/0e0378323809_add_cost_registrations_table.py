"""add cost_registrations table

Revision ID: 0e0378323809
Revises: f1a2b3c4d5e6
Create Date: 2026-01-16 07:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0e0378323809"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cost_registrations",
        sa.Column("cost_registration_id", postgresql.UUID(), nullable=False),
        sa.Column("cost_element_id", postgresql.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=50), nullable=True),
        sa.Column("registration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("invoice_number", sa.String(length=100), nullable=True),
        sa.Column("vendor_reference", sa.String(length=255), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_registrations")),
    )
    op.create_index(
        op.f("ix_cost_registrations_cost_element_id"),
        "cost_registrations",
        ["cost_element_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cost_registrations_cost_registration_id"),
        "cost_registrations",
        ["cost_registration_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cost_registrations_created_by"),
        "cost_registrations",
        ["created_by"],
        unique=False,
    )
    # Note: Foreign key to cost_elements.cost_element_id omitted because that column
    # doesn't have a unique constraint. Referential integrity enforced at application level.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_cost_registrations_created_by"), table_name="cost_registrations"
    )
    op.drop_index(
        op.f("ix_cost_registrations_cost_registration_id"),
        table_name="cost_registrations",
    )
    op.drop_index(
        op.f("ix_cost_registrations_cost_element_id"), table_name="cost_registrations"
    )
    op.drop_table("cost_registrations")
