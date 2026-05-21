"""Rename quality_impacts to work_packages with new columns.

Revision ID: a0b1c2d3e4f5
Revises: cc19af7150e4
Create Date: 2026-05-21

Generalizes QualityImpact into WorkPackage:
- Renames table quality_impacts -> work_packages
- Renames root ID column quality_impact_id -> work_package_id
- Renames FK column on cost_registrations: quality_impact_id -> work_package_id
- Adds columns: name (required), package_type (required), description (nullable), status (required, default 'open')
- Backfills existing rows with package_type='quality_impact', status='open', generated name
- Recreates indexes with new column names
- Adds partial index for COQ queries on package_type='quality_impact'
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0b1c2d3e4f5"
down_revision: str | Sequence[str] | None = "cc19af7150e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade: rename table, rename columns, add new columns, backfill data."""
    # ------------------------------------------------------------------
    # Step 1: Add new nullable columns first (so we can backfill them)
    # ------------------------------------------------------------------
    op.add_column(
        "quality_impacts",
        sa.Column("name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "quality_impacts",
        sa.Column("package_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "quality_impacts",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "quality_impacts",
        sa.Column("status", sa.String(length=20), nullable=True),
    )

    # ------------------------------------------------------------------
    # Step 2: Backfill existing rows
    # ------------------------------------------------------------------
    # Set package_type = 'quality_impact' for all existing rows
    op.execute(
        "UPDATE quality_impacts SET package_type = 'quality_impact', "
        "status = 'open', "
        "name = COALESCE(external_event_id, 'Work Package ' || quality_impact_id::text) "
        "WHERE package_type IS NULL"
    )

    # ------------------------------------------------------------------
    # Step 3: Make columns NOT NULL after backfill
    # ------------------------------------------------------------------
    op.alter_column("quality_impacts", "name", nullable=False)
    op.alter_column("quality_impacts", "package_type", nullable=False)
    op.alter_column("quality_impacts", "status", nullable=False)

    # Set default for status on new rows
    op.alter_column(
        "quality_impacts",
        "status",
        server_default="open",
    )

    # ------------------------------------------------------------------
    # Step 4: Make quality-specific columns nullable for non-quality types
    # ------------------------------------------------------------------
    op.alter_column("quality_impacts", "external_event_id", nullable=True)
    op.alter_column("quality_impacts", "coq_category", nullable=True)

    # ------------------------------------------------------------------
    # Step 5: Drop old indexes on quality_impacts
    # ------------------------------------------------------------------
    op.drop_index("ix_quality_impacts_quality_impact_id", table_name="quality_impacts")
    op.drop_index("ix_quality_impacts_external_event_id", table_name="quality_impacts")
    op.drop_index("ix_quality_impacts_project_id", table_name="quality_impacts")
    op.drop_index("ix_quality_impacts_created_by", table_name="quality_impacts")

    # ------------------------------------------------------------------
    # Step 6: Rename root ID column on quality_impacts
    # ------------------------------------------------------------------
    op.alter_column(
        "quality_impacts", "quality_impact_id", new_column_name="work_package_id"
    )

    # ------------------------------------------------------------------
    # Step 7: Rename table quality_impacts -> work_packages
    # ------------------------------------------------------------------
    op.rename_table("quality_impacts", "work_packages")

    # ------------------------------------------------------------------
    # Step 8: Recreate indexes with new table and column names
    # ------------------------------------------------------------------
    op.create_index(
        "ix_work_packages_work_package_id",
        "work_packages",
        ["work_package_id"],
    )
    op.create_index(
        "ix_work_packages_external_event_id",
        "work_packages",
        ["external_event_id"],
    )
    op.create_index(
        "ix_work_packages_project_id",
        "work_packages",
        ["project_id"],
    )
    op.create_index(
        "ix_work_packages_created_by",
        "work_packages",
        ["created_by"],
    )
    op.create_index(
        "ix_work_packages_package_type",
        "work_packages",
        ["package_type"],
    )
    # Composite index for filtered list queries
    op.create_index(
        "ix_work_packages_project_id_package_type",
        "work_packages",
        ["project_id", "package_type"],
    )
    # Partial index for COQ queries
    op.execute(
        "CREATE INDEX ix_work_packages_quality_type "
        "ON work_packages (project_id, work_package_id) "
        "WHERE package_type = 'quality_impact'"
    )

    # ------------------------------------------------------------------
    # Step 9: Rename FK column on cost_registrations
    # ------------------------------------------------------------------
    # Drop old index first
    op.drop_index(
        "ix_cost_registrations_quality_impact_id",
        table_name="cost_registrations",
    )
    # Rename column
    op.alter_column(
        "cost_registrations", "quality_impact_id", new_column_name="work_package_id"
    )
    # Create new index
    op.create_index(
        "ix_cost_registrations_work_package_id",
        "cost_registrations",
        ["work_package_id"],
    )


def downgrade() -> None:
    """Downgrade: reverse all changes back to quality_impacts."""
    # ------------------------------------------------------------------
    # Step 1: Rename FK column on cost_registrations back
    # ------------------------------------------------------------------
    op.drop_index(
        "ix_cost_registrations_work_package_id",
        table_name="cost_registrations",
    )
    op.alter_column(
        "cost_registrations", "work_package_id", new_column_name="quality_impact_id"
    )
    op.create_index(
        "ix_cost_registrations_quality_impact_id",
        "cost_registrations",
        ["quality_impact_id"],
    )

    # ------------------------------------------------------------------
    # Step 2: Drop new indexes on work_packages
    # ------------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS ix_work_packages_quality_type")
    op.drop_index("ix_work_packages_project_id_package_type", table_name="work_packages")
    op.drop_index("ix_work_packages_package_type", table_name="work_packages")
    op.drop_index("ix_work_packages_created_by", table_name="work_packages")
    op.drop_index("ix_work_packages_project_id", table_name="work_packages")
    op.drop_index("ix_work_packages_external_event_id", table_name="work_packages")
    op.drop_index("ix_work_packages_work_package_id", table_name="work_packages")

    # ------------------------------------------------------------------
    # Step 3: Rename root ID column back
    # ------------------------------------------------------------------
    op.alter_column(
        "work_packages", "work_package_id", new_column_name="quality_impact_id"
    )

    # ------------------------------------------------------------------
    # Step 4: Rename table back
    # ------------------------------------------------------------------
    op.rename_table("work_packages", "quality_impacts")

    # ------------------------------------------------------------------
    # Step 5: Recreate old indexes
    # ------------------------------------------------------------------
    op.create_index(
        "ix_quality_impacts_quality_impact_id",
        "quality_impacts",
        ["quality_impact_id"],
    )
    op.create_index(
        "ix_quality_impacts_external_event_id",
        "quality_impacts",
        ["external_event_id"],
    )
    op.create_index(
        "ix_quality_impacts_project_id",
        "quality_impacts",
        ["project_id"],
    )
    op.create_index(
        "ix_quality_impacts_created_by",
        "quality_impacts",
        ["created_by"],
    )

    # ------------------------------------------------------------------
    # Step 6: Make quality-specific columns NOT NULL again
    # ------------------------------------------------------------------
    # Backfill any nulls first (shouldn't happen if only quality_impact type existed)
    op.execute(
        "UPDATE quality_impacts SET external_event_id = 'UNKNOWN' "
        "WHERE external_event_id IS NULL"
    )
    op.execute(
        "UPDATE quality_impacts SET coq_category = 'nonconformance' "
        "WHERE coq_category IS NULL"
    )
    op.alter_column("quality_impacts", "external_event_id", nullable=False)
    op.alter_column("quality_impacts", "coq_category", nullable=False)

    # ------------------------------------------------------------------
    # Step 7: Drop new columns
    # ------------------------------------------------------------------
    op.alter_column("quality_impacts", "status", server_default=None)
    op.drop_column("quality_impacts", "status")
    op.drop_column("quality_impacts", "description")
    op.drop_column("quality_impacts", "package_type")
    op.drop_column("quality_impacts", "name")
