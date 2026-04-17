"""add quality_events table

Revision ID: 20260417_e05_u07
Revises: d270ea9e1bd8
Create Date: 2026-04-17 00:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_e05_u07"
down_revision: str | Sequence[str] | None = "d270ea9e1bd8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "quality_events",
        sa.Column("quality_event_id", postgresql.UUID(), nullable=False),
        sa.Column("cost_element_id", postgresql.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cost_impact", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_events")),
    )
    op.create_index(
        op.f("ix_quality_events_cost_element_id"),
        "quality_events",
        ["cost_element_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_events_quality_event_id"),
        "quality_events",
        ["quality_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_events_created_by"),
        "quality_events",
        ["created_by"],
        unique=False,
    )
    # Note: Foreign key to cost_elements.cost_element_id omitted because that column
    # doesn't have a unique constraint. Referential integrity enforced at application level.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_quality_events_created_by"), table_name="quality_events"
    )
    op.drop_index(
        op.f("ix_quality_events_quality_event_id"),
        table_name="quality_events",
    )
    op.drop_index(
        op.f("ix_quality_events_cost_element_id"), table_name="quality_events"
    )
    op.drop_table("quality_events")
