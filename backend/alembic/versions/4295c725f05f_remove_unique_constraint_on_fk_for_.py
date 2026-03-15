"""remove_unique_constraint_on_fk_for_versioning

Revision ID: 4295c725f05f
Revises: 20260118_forecast_1to1
Create Date: 2026-01-20 07:25:24.132486

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4295c725f05f"
down_revision: str | Sequence[str] | None = "20260118_forecast_1to1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("uq_cost_elements_forecast_id", table_name="cost_elements")
    op.drop_index("uq_cost_elements_schedule_baseline_id", table_name="cost_elements")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        "uq_cost_elements_schedule_baseline_id",
        "cost_elements",
        ["schedule_baseline_id"],
        unique=True,
    )
    op.create_index(
        "uq_cost_elements_forecast_id", "cost_elements", ["forecast_id"], unique=True
    )
