"""add quality_impact_id to cost_registrations, drop breakdowns

Revision ID: cc19af7150e4
Revises: 631a7bb0fe04
Create Date: 2026-05-20 23:00:18.003125

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc19af7150e4"
down_revision: str | Sequence[str] | None = "631a7bb0fe04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add quality_impact_id column to cost_registrations.
    # When set, this cost registration is a quality cost allocation.
    op.add_column(
        "cost_registrations",
        sa.Column("quality_impact_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_cost_registrations_quality_impact_id",
        "cost_registrations",
        ["quality_impact_id"],
    )

    # Drop the breakdowns table -- quality costs are now tracked via
    # CostRegistration.quality_impact_id instead.
    op.drop_table("quality_impact_breakdowns")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate quality_impact_breakdowns table.
    op.create_table(
        "quality_impact_breakdowns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("quality_impact_breakdown_id", sa.UUID(), nullable=False),
        sa.Column("quality_impact_id", sa.UUID(), nullable=False),
        sa.Column("wbe_id", sa.UUID(), nullable=True),
        sa.Column("cost_element_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.NUMERIC(precision=15, scale=2), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quality_impact_breakdowns_quality_impact_breakdown_id",
        "quality_impact_breakdowns",
        ["quality_impact_breakdown_id"],
    )
    op.create_index(
        "ix_quality_impact_breakdowns_quality_impact_id",
        "quality_impact_breakdowns",
        ["quality_impact_id"],
    )
    op.create_index(
        "ix_quality_impact_breakdowns_wbe_id",
        "quality_impact_breakdowns",
        ["wbe_id"],
    )
    op.create_index(
        "ix_quality_impact_breakdowns_cost_element_id",
        "quality_impact_breakdowns",
        ["cost_element_id"],
    )

    # Remove quality_impact_id column from cost_registrations.
    op.drop_index(
        "ix_cost_registrations_quality_impact_id",
        table_name="cost_registrations",
    )
    op.drop_column("cost_registrations", "quality_impact_id")
