"""Add impact analysis tracking fields to change_orders.

Revision ID: 20260205_add_impact_analysis_fields
Revises: 0206_appr_matrix
Create Date: 2026-02-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260205_impact_fields"
down_revision: str | Sequence[str] | None = "0206_appr_matrix"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add impact analysis tracking fields."""
    # Add new columns for impact analysis tracking
    op.add_column(
        "change_orders",
        sa.Column(
            "impact_analysis_status",
            sa.String(length=20),
            nullable=True,
            comment="Impact analysis state: pending/in_progress/completed/failed/skipped",
        ),
    )
    op.add_column(
        "change_orders",
        sa.Column(
            "impact_analysis_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Stored KPIScorecard results from impact analysis",
        ),
    )
    op.add_column(
        "change_orders",
        sa.Column(
            "impact_score",
            sa.NUMERIC(precision=10, scale=2),
            nullable=True,
            comment="Impact severity score (weighted calculation)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema - remove impact analysis tracking fields."""
    op.drop_column("change_orders", "impact_score")
    op.drop_column("change_orders", "impact_analysis_results")
    op.drop_column("change_orders", "impact_analysis_status")
