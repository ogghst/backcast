"""Progress Entries Table Migration

Revision ID: 20260118_100000
Revises: 20260118_090108
Create Date: 2026-01-18 10:00:00.000000

This migration creates the progress_entries table for tracking work completion
percentage for cost elements, enabling Earned Value Management (EVM) calculations.

Progress entries are versionable (NOT branchable) - progress is a global fact
across all branches, similar to cost registrations.

Table Structure:
- progress_entry_id: Root ID for aggregation (UUID)
- cost_element_id: Foreign key to cost_elements
- progress_percentage: Work completion (0.00 to 100.00)
- reported_date: Business date when progress was measured
- reported_by_user_id: User who reported the progress
- notes: Optional notes (e.g., justification for decrease)
- valid_time: TSTZRANGE for business time tracking
- transaction_time: TSTZRANGE for system time tracking
- deleted_at: Soft delete timestamp
- created_by: User who created the entry
- deleted_by: User who deleted the entry

Indexes:
- progress_entry_id: For root ID lookups
- cost_element_id: For filtering by cost element
- reported_date: For time-travel queries and historical analysis
- GIST indexes on valid_time and transaction_time for range queries
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260118_100000"
down_revision: str | None = "20260118_090108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create progress_entries table with bitemporal versioning support."""

    # Create btree_gist extension if not exists (required for GIST indexes on TSTZRANGE)
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;
        """
    )

    # Create progress_entries table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS progress_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            progress_entry_id UUID NOT NULL,
            cost_element_id UUID NOT NULL,
            progress_percentage NUMERIC(5, 2) NOT NULL,
            notes TEXT,

            -- Bitemporal versioning fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMP WITH TIME ZONE,

            -- Audit fields
            created_by UUID NOT NULL,
            deleted_by UUID,

            -- Standard timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        );
        """
    )

    # Create index on progress_entry_id for root ID lookups
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_progress_entries_progress_entry_id
        ON progress_entries(progress_entry_id);
        """
    )

    # Create index on cost_element_id for filtering by cost element
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_progress_entries_cost_element_id
        ON progress_entries(cost_element_id);
        """
    )

    # Create GIST index on valid_time for range queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_progress_entries_valid_time
        ON progress_entries USING GIST(valid_time);
        """
    )

    # Create GIST index on transaction_time for range queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_progress_entries_transaction_time
        ON progress_entries USING GIST(transaction_time);
        """
    )

    # Create partial unique index for current versions (open-ended valid_time, not deleted)
    # This ensures efficient queries for current progress entries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_progress_entries_current_versions
        ON progress_entries(progress_entry_id)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;
        """
    )

    # Note: Foreign key constraints omitted because referenced columns don't have unique constraints.
    # Referential integrity is enforced at application level.
    # This follows the same pattern as cost_registrations table (see 0e0378323809)
    # Omitted foreign keys:
    # - cost_element_id -> cost_elements(cost_element_id) [no unique constraint]
    # - created_by -> users(user_id) [no unique constraint, should reference users.id]
    # - deleted_by -> users(user_id) [no unique constraint, should reference users.id]
    # - reported_by_user_id -> users(user_id) [no unique constraint, should reference users.id]

    # Add check constraint for progress_percentage range (0.00 to 100.00)
    op.execute(
        """
        ALTER TABLE progress_entries
        ADD CONSTRAINT chk_progress_entries_percentage_range
        CHECK (progress_percentage >= 0.00 AND progress_percentage <= 100.00);
        """
    )

    # Add exclusion constraint to prevent overlapping valid_time ranges
    # for the same progress_entry_id
    op.execute(
        """
        ALTER TABLE progress_entries
        ADD CONSTRAINT excl_progress_entries_overlap
        EXCLUDE USING GIST (
            progress_entry_id WITH =,
            valid_time WITH &&
        );
        """
    )

    # Add comment to table
    op.execute(
        """
        COMMENT ON TABLE progress_entries IS
        'Progress tracking for cost elements - versionable, not branchable.
        Progress is tracked as a percentage (0-100) and is valid for a specific time period.
        Like cost registrations, progress is a global fact (not branchable) - work completed
        is the same across all change order branches.';
        """
    )


def downgrade() -> None:
    """Drop progress_entries table and all related indexes."""

    # Drop table (automatically drops all constraints and indexes)
    op.execute(
        """
        DROP TABLE IF EXISTS progress_entries CASCADE;
        """
    )

    # Drop btree_gist extension (optional, as other migrations might use it)
    # Commented out to avoid breaking other tables that depend on it
    # op.execute("DROP EXTENSION IF EXISTS btree_gist CASCADE;")
