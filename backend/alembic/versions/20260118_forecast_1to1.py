"""Forecast 1:1 Relationship Migration

Revision ID: 20260118_forecast_1to1
Revises: 16a1d8c94dd3
Create Date: 2026-01-18

This migration enforces a 1:1 relationship between Cost Elements and Forecasts
by inverting the foreign key direction:
- Adds forecast_id FK to cost_elements table
- Removes cost_element_id FK from forecasts table
- Adds unique constraint to enforce 1:1 relationship
- No data migration needed (starting fresh)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260118_forecast_1to1"
down_revision: str | None = "16a1d8c94dd3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply 1:1 relationship changes between cost_elements and forecasts."""

    # Step 1: Add forecast_id column to cost_elements (nullable for now)
    op.execute(
        """
        ALTER TABLE cost_elements
        ADD COLUMN IF NOT EXISTS forecast_id UUID;
        """
    )

    # Step 2: Create index on forecast_id for performance
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cost_elements_forecast_id
        ON cost_elements(forecast_id);
        """
    )

    # Step 3: Create unique constraint on forecast_id to enforce 1:1
    # This uses a partial unique index (only for non-null values) which works
    # with the nullable column and doesn't require FK on forecasts
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cost_elements_forecast_id
        ON cost_elements(forecast_id)
        WHERE forecast_id IS NOT NULL;
        """
    )

    # NOTE: In a bitemporal versioned system, we cannot create a traditional
    # FK constraint from cost_elements.forecast_id to forecasts.forecast_id
    # because the referenced column is not unique (appears in multiple version rows).
    #
    # Instead, we enforce referential integrity at the application level
    # through the service layer and use the unique index above to enforce
    # the 1:1 relationship constraint.

    # Step 4: Remove the cost_element_id column from forecasts
    # Note: We make it nullable first for backward compatibility during migration
    op.execute(
        """
        ALTER TABLE forecasts
        ALTER COLUMN cost_element_id DROP NOT NULL;
        """
    )

    # Step 5: Drop the cost_element_id column from forecasts
    op.execute(
        """
        ALTER TABLE forecasts
        DROP COLUMN IF EXISTS cost_element_id;
        """
    )


def downgrade() -> None:
    """Rollback 1:1 relationship changes."""

    # Step 1: Restore cost_element_id column to forecasts (nullable)
    op.execute(
        """
        ALTER TABLE forecasts
        ADD COLUMN IF NOT EXISTS cost_element_id UUID;
        """
    )

    # Step 2: Remove unique index
    op.execute(
        """
        DROP INDEX IF EXISTS uq_cost_elements_forecast_id;
        """
    )

    # Step 3: Remove regular index
    op.execute(
        """
        DROP INDEX IF EXISTS ix_cost_elements_forecast_id;
        """
    )

    # Step 4: Remove forecast_id column from cost_elements
    op.execute(
        """
        ALTER TABLE cost_elements
        DROP COLUMN IF EXISTS forecast_id;
        """
    )
