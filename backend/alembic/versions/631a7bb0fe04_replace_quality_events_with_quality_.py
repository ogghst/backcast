"""replace quality_events with quality_impacts + quality_impact_breakdowns

Revision ID: 631a7bb0fe04
Revises: 823cf293a68b
Create Date: 2026-05-20 20:54:08.099783

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "631a7bb0fe04"
down_revision: str | Sequence[str] | None = "823cf293a68b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create quality_impacts table (versionable, same temporal pattern as quality_events)
    op.create_table(
        "quality_impacts",
        sa.Column("quality_impact_id", postgresql.UUID(), nullable=False),
        sa.Column("external_event_id", sa.String(length=100), nullable=False),
        sa.Column("project_id", postgresql.UUID(), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("coq_category", sa.String(length=20), nullable=False),
        sa.Column("cost_impact", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("schedule_impact_days", sa.SmallInteger(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_impacts")),
    )
    op.create_index(
        op.f("ix_quality_impacts_quality_impact_id"),
        "quality_impacts",
        ["quality_impact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_impacts_external_event_id"),
        "quality_impacts",
        ["external_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_impacts_project_id"),
        "quality_impacts",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_impacts_created_by"),
        "quality_impacts",
        ["created_by"],
        unique=False,
    )

    # 2. Create quality_impact_breakdowns table (simple, non-versioned)
    op.create_table(
        "quality_impact_breakdowns",
        sa.Column("quality_impact_breakdown_id", postgresql.UUID(), nullable=False),
        sa.Column("quality_impact_id", postgresql.UUID(), nullable=False),
        sa.Column("wbe_id", postgresql.UUID(), nullable=True),
        sa.Column("cost_element_id", postgresql.UUID(), nullable=True),
        sa.Column("amount", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_impact_breakdowns")),
    )
    op.create_index(
        op.f("ix_quality_impact_breakdowns_quality_impact_breakdown_id"),
        "quality_impact_breakdowns",
        ["quality_impact_breakdown_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_impact_breakdowns_quality_impact_id"),
        "quality_impact_breakdowns",
        ["quality_impact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_impact_breakdowns_wbe_id"),
        "quality_impact_breakdowns",
        ["wbe_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_impact_breakdowns_cost_element_id"),
        "quality_impact_breakdowns",
        ["cost_element_id"],
        unique=False,
    )

    # 3. Drop old quality_events table
    op.drop_index(op.f("ix_quality_events_created_by"), table_name="quality_events")
    op.drop_index(
        op.f("ix_quality_events_quality_event_id"), table_name="quality_events"
    )
    op.drop_index(
        op.f("ix_quality_events_cost_element_id"), table_name="quality_events"
    )
    op.drop_table("quality_events")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Recreate quality_events table
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

    # 2. Drop quality_impact_breakdowns
    op.drop_index(
        op.f("ix_quality_impact_breakdowns_cost_element_id"),
        table_name="quality_impact_breakdowns",
    )
    op.drop_index(
        op.f("ix_quality_impact_breakdowns_wbe_id"),
        table_name="quality_impact_breakdowns",
    )
    op.drop_index(
        op.f("ix_quality_impact_breakdowns_quality_impact_id"),
        table_name="quality_impact_breakdowns",
    )
    op.drop_index(
        op.f("ix_quality_impact_breakdowns_quality_impact_breakdown_id"),
        table_name="quality_impact_breakdowns",
    )
    op.drop_table("quality_impact_breakdowns")

    # 3. Drop quality_impacts
    op.drop_index(op.f("ix_quality_impacts_created_by"), table_name="quality_impacts")
    op.drop_index(op.f("ix_quality_impacts_project_id"), table_name="quality_impacts")
    op.drop_index(
        op.f("ix_quality_impacts_external_event_id"), table_name="quality_impacts"
    )
    op.drop_index(
        op.f("ix_quality_impacts_quality_impact_id"), table_name="quality_impacts"
    )
    op.drop_table("quality_impacts")
