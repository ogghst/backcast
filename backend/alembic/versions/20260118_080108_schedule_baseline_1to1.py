"""Schedule Baseline 1:1 Relationship Migration

Revision ID: 20260118_080108
Revises: e45e085ced4d
Create Date: 2026-01-18 08:01:08.000000

This migration enforces a 1:1 relationship between Cost Elements and Schedule Baselines
by inverting the foreign key direction:
- Adds schedule_baseline_id FK to cost_elements table
- Removes cost_element_id FK from schedule_baselines table
- Migrates existing data to preserve current relationships
- Adds unique constraint to enforce 1:1 relationship

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260118_080108"
down_revision: str | None = "e45e085ced4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply 1:1 relationship changes between cost_elements and schedule_baselines."""

    # Step 1: Add schedule_baseline_id column to cost_elements (nullable for now)
    op.execute(
        """
        ALTER TABLE cost_elements
        ADD COLUMN IF NOT EXISTS schedule_baseline_id UUID;
        """
    )

    # Step 2: Create archive table for historical baselines
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule_baselines_archive AS
        SELECT * FROM schedule_baselines;
        """
    )

    # Step 3: Migrate existing data
    # For each cost element, select the most recent schedule baseline
    # and update cost_elements.schedule_baseline_id
    op.execute(
        """
        -- Create a temporary mapping table
        CREATE TEMP TABLE cost_element_baseline_mapping AS
        SELECT DISTINCT ON (ce.cost_element_id, ce.branch)
            ce.id as cost_element_version_id,
            ce.cost_element_id,
            sb.schedule_baseline_id
        FROM cost_elements ce
        LEFT JOIN schedule_baselines sb
            ON ce.cost_element_id = sb.cost_element_id
            AND ce.branch = sb.branch
            AND sb.deleted_at IS NULL
        ORDER BY ce.cost_element_id, ce.branch, sb.transaction_time DESC;
        """
    )

    # Step 4: Update cost_elements with the mapped schedule_baseline_id
    op.execute(
        """
        UPDATE cost_elements ce
        SET schedule_baseline_id = cebm.schedule_baseline_id
        FROM cost_element_baseline_mapping cebm
        WHERE ce.id = cebm.cost_element_version_id;
        """
    )

    # Step 5: Create index on schedule_baseline_id for performance
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cost_elements_schedule_baseline_id
        ON cost_elements(schedule_baseline_id);
        """
    )

    # Step 6: Create unique constraint on schedule_baseline_id to enforce 1:1
    # This uses a partial unique index (only for non-null values) which works
    # with the nullable column and doesn't require FK on schedule_baselines
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cost_elements_schedule_baseline_id
        ON cost_elements(schedule_baseline_id)
        WHERE schedule_baseline_id IS NOT NULL;
        """
    )

    # NOTE: In a bitemporal versioned system, we cannot create a traditional
    # FK constraint from cost_elements.schedule_baseline_id to
    # schedule_baselines.schedule_baseline_id because the referenced column
    # is not unique (appears in multiple version rows).
    #
    # Instead, we enforce referential integrity at the application level
    # through the service layer and use the unique index above to enforce
    # the 1:1 relationship constraint.

    # Step 8: Remove the cost_element_id column from schedule_baselines
    # Note: We keep the column for now for backward compatibility during migration
    # It can be dropped in a future migration once confirmed stable
    # For now, we'll make it nullable
    op.execute(
        """
        ALTER TABLE schedule_baselines
        ALTER COLUMN cost_element_id DROP NOT NULL;
        """
    )

    # Clean up temporary table
    op.execute("DROP TABLE IF EXISTS cost_element_baseline_mapping;")


def downgrade() -> None:
    """Rollback 1:1 relationship changes."""

    # Step 1: Remove unique index
    op.execute(
        """
        DROP INDEX IF EXISTS uq_cost_elements_schedule_baseline_id;
        """
    )

    # Step 2: Remove regular index
    op.execute(
        """
        DROP INDEX IF EXISTS ix_cost_elements_schedule_baseline_id;
        """
    )

    # Step 4: Restore cost_element_id NOT NULL constraint
    op.execute(
        """
        ALTER TABLE schedule_baselines
        ALTER COLUMN cost_element_id SET NOT NULL;
        """
    )

    # Step 5: Remove schedule_baseline_id column from cost_elements
    op.execute(
        """
        ALTER TABLE cost_elements
        DROP COLUMN IF EXISTS schedule_baseline_id;
        """
    )

    # Step 6: Drop archive table
    op.execute(
        """
        DROP TABLE IF EXISTS schedule_baselines_archive;
        """
    )
