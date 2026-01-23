"""add_indexes_for_evm_performance

Revision ID: f69c57fcc47d
Revises: 4295c725f05f
Create Date: 2026-01-22 15:15:07.275266

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f69c57fcc47d'
down_revision: str | Sequence[str] | None = '4295c725f05f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Add indexes to optimize EVM time-series query performance.

    Performance Requirements:
    - Time-series queries < 1s for 1-year range
    - Summary metrics < 500ms

    Query patterns optimized:
    1. Cost registrations by cost_element and registration_date (for AC calculation)
    2. Progress entries by cost_element and reported_date (for EV calculation)
    3. Cost elements by schedule_baseline_id (for PV calculation)
    4. WBEs by project_id (for WBE aggregation)
    """
    # Index for cost_registrations: (cost_element_id, registration_date)
    # Used by: get_cumulative_costs, get_costs_by_period
    # This dramatically speeds up AC (Actual Cost) time-series queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cost_registrations_cost_element_date
        ON cost_registrations (cost_element_id, registration_date)
    """)

    # Index for progress_entries: (cost_element_id, reported_date)
    # Used by: get_progress_history, latest progress lookups
    # This dramatically speeds up EV (Earned Value) time-series queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_progress_entries_cost_element_reported_date
        ON progress_entries (cost_element_id, reported_date)
    """)

    # Index for wbes: project_id
    # Used by: WBE aggregation for project-level EVM metrics
    # Note: cost_elements schedule_baseline_id index already exists
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_wbes_project_id
        ON wbes (project_id)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes in reverse order
    op.execute('DROP INDEX IF EXISTS ix_wbes_project_id')
    op.execute('DROP INDEX IF EXISTS ix_progress_entries_cost_element_reported_date')
    op.execute('DROP INDEX IF EXISTS ix_cost_registrations_cost_element_date')
