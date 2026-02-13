"""Add forecasts table

Revision ID: e5f6g7h8i9j0
Revises: fdd09caf9368
Create Date: 2026-01-16 07:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: str | None = "fdd09caf9368"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create forecasts table."""
    # Create forecasts table
    # NOTE: No FK constraints on cost_element_id because in a
    # bitemporal system, these are root IDs that appear in multiple rows (versions).
    # FK constraints require UNIQUE, which root IDs cannot have.
    # Referential integrity is enforced at the application level.
    op.execute(
        """
        CREATE TABLE forecasts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            forecast_id UUID NOT NULL,
            cost_element_id UUID NOT NULL,
            eac_amount NUMERIC(15, 2) NOT NULL,
            basis_of_estimate TEXT NOT NULL,
            approved_date TIMESTAMPTZ,
            approved_by UUID,
            -- Versioning columns (from VersionableMixin)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            -- Branching columns (from BranchableMixin)
            branch VARCHAR(255) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(255)
        );
        """
    )

    # Create indexes
    op.execute("CREATE INDEX ix_forecasts_forecast_id ON forecasts(forecast_id);")
    op.execute(
        "CREATE INDEX ix_forecasts_cost_element_id ON forecasts(cost_element_id);"
    )
    op.execute("CREATE INDEX ix_forecasts_branch ON forecasts(branch);")
    op.execute("CREATE INDEX ix_forecasts_created_by ON forecasts(created_by);")

    # Create temporal indexes
    op.execute(
        "CREATE INDEX ix_forecasts_valid_time ON forecasts USING GIST (valid_time);"
    )
    op.execute(
        "CREATE INDEX ix_forecasts_transaction_time "
        "ON forecasts USING GIST (transaction_time);"
    )

    # NOTE: EXCLUDE constraint for version overlap is not added here
    # to match existing entity patterns.
    # Version overlap prevention is handled at the application level via Commands.


def downgrade() -> None:
    """Drop forecasts table."""
    op.execute("DROP TABLE IF EXISTS forecasts CASCADE;")
