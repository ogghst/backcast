"""Add schedule_baselines table

Revision ID: f1a2b3c4d5e6
Revises: e5f6g7h8i9j0
Create Date: 2026-01-16 08:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e5f6g7h8i9j0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create schedule_baselines table and progression_type enum."""

    # Create ENUM type for progression types
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE progression_type AS ENUM ('LINEAR', 'GAUSSIAN', 'LOGARITHMIC');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # Create schedule_baselines table
    # NOTE: No FK constraints on cost_element_id because in a
    # bitemporal system, these are root IDs that appear in multiple rows (versions).
    # FK constraints require UNIQUE, which root IDs cannot have.
    # Referential integrity is enforced at the application level.
    op.execute(
        """
        CREATE TABLE schedule_baselines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            schedule_baseline_id UUID NOT NULL,
            cost_element_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            start_date TIMESTAMPTZ NOT NULL,
            end_date TIMESTAMPTZ NOT NULL,
            progression_type progression_type NOT NULL DEFAULT 'LINEAR',
            description TEXT,
            -- Versioning columns (from VersionableMixin)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            -- Branching columns (from BranchableMixin)
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        );
        """
    )

    # Create indexes
    op.execute(
        "CREATE INDEX ix_schedule_baselines_schedule_baseline_id "
        "ON schedule_baselines(schedule_baseline_id);"
    )
    op.execute(
        "CREATE INDEX ix_schedule_baselines_cost_element_id "
        "ON schedule_baselines(cost_element_id);"
    )
    op.execute("CREATE INDEX ix_schedule_baselines_name ON schedule_baselines(name);")
    op.execute(
        "CREATE INDEX ix_schedule_baselines_start_date "
        "ON schedule_baselines(start_date);"
    )
    op.execute(
        "CREATE INDEX ix_schedule_baselines_end_date ON schedule_baselines(end_date);"
    )
    op.execute(
        "CREATE INDEX ix_schedule_baselines_branch ON schedule_baselines(branch);"
    )
    op.execute(
        "CREATE INDEX ix_schedule_baselines_created_by "
        "ON schedule_baselines(created_by);"
    )

    # Create temporal indexes for efficient range queries
    op.execute(
        "CREATE INDEX ix_schedule_baselines_valid_time "
        "ON schedule_baselines USING GIST (valid_time);"
    )
    op.execute(
        "CREATE INDEX ix_schedule_baselines_transaction_time "
        "ON schedule_baselines USING GIST (transaction_time);"
    )


def downgrade() -> None:
    """Drop schedule_baselines table and progression_type enum."""
    op.execute("DROP TABLE IF EXISTS schedule_baselines CASCADE;")
    op.execute("DROP TYPE IF EXISTS progression_type;")
