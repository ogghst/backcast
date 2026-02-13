"""Fix unique index to only apply to current cost element versions.

Revision ID: 20260118_090108
Revises: 20260118_080108
Create Date: 2026-01-18 09:01:08.000000

This migration fixes the unique index on schedule_baseline_id to only apply
to current versions (where valid_time has no upper bound AND deleted_at IS NULL).
This allows multiple historical versions of the same cost element to reference
the same baseline while enforcing 1:1 relationship for current versions.

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260118_090108"
down_revision: str | None = "20260118_080108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Fix unique index to only apply to current versions."""

    # Drop the old unique index
    op.execute(
        """
        DROP INDEX IF EXISTS uq_cost_elements_schedule_baseline_id;
        """
    )

    # Create a new unique index that only applies to current versions
    # Current versions are those where:
    # - schedule_baseline_id IS NOT NULL
    # - deleted_at IS NULL (not soft deleted)
    # - upper(valid_time) IS NULL (current version, not historical)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cost_elements_schedule_baseline_id
        ON cost_elements(schedule_baseline_id)
        WHERE schedule_baseline_id IS NOT NULL
        AND deleted_at IS NULL
        AND upper(valid_time) IS NULL;
        """
    )


def downgrade() -> None:
    """Revert to the original unique index."""

    # Drop the fixed unique index
    op.execute(
        """
        DROP INDEX IF EXISTS uq_cost_elements_schedule_baseline_id;
        """
    )

    # Restore the original unique index
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cost_elements_schedule_baseline_id
        ON cost_elements(schedule_baseline_id)
        WHERE schedule_baseline_id IS NOT NULL;
        """
    )
