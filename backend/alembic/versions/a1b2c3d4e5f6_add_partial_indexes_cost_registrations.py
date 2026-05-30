"""add_partial_indexes_cost_registrations

Revision ID: a1b2c3d4e5f6
Revises: 43af566f5140
Create Date: 2026-05-31

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "43af566f5140"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add partial indexes for current-version cost_registration queries.

    INDEX 1: (cost_element_id, registration_date) WHERE current version and not deleted
        Covers: get_total_for_cost_element, get_totals_for_cost_elements,
                get_budget_status, get_project_budget_status,
                get_wbs_element_budget_status, batch variants

    INDEX 2: (cost_registration_id) WHERE current version and not deleted
        Covers: get_by_id, soft_delete, update -- find current version by root ID
    """
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cr_cost_element_id_current
        ON cost_registrations (cost_element_id, registration_date)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cr_cost_registration_id_current
        ON cost_registrations (cost_registration_id)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL
    """)


def downgrade() -> None:
    """Remove partial indexes on cost_registrations."""
    op.execute("DROP INDEX IF EXISTS ix_cr_cost_registration_id_current")
    op.execute("DROP INDEX IF EXISTS ix_cr_cost_element_id_current")
