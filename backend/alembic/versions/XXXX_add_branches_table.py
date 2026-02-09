"""add branches table and branch_name to change_orders

Revision ID: add_branches_table
Revises: d1ce5ad9a78c
Create Date: 2026-01-13

This migration:
1. Creates a branches table with composite PK (name, project_id)
2. Adds branch_name column to change_orders table
3. Creates main branches for existing projects
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_branches_table"
down_revision: str | Sequence[str] | None = "d1ce5ad9a78c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add branches table and branch_name column."""

    # 1. Create branches table with composite PK
    op.create_table(
        "branches",
        sa.Column(
            "name",
            sa.String(80),
            nullable=False,
            comment="Branch name (e.g., main or BR-CO-2026-001)",
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Project this branch belongs to (no FK constraint as project_id is not unique in projects table)",
        ),
        sa.Column(
            "type",
            sa.String(20),
            nullable=False,
            server_default="main",
            comment="Branch type (main or change_order)",
        ),
        sa.Column(
            "locked",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether branch is locked (prevents writes)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="When branch was created",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User who created the branch",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Soft delete timestamp",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=True,
            comment="Additional branch information",
        ),
        sa.PrimaryKeyConstraint("name", "project_id", name="pk_branches"),
        comment="Branch metadata with project-scoped composite key",
    )

    # 2. Create indexes for branches table
    op.create_index("ix_branches_type", "branches", ["type"])
    op.create_index("ix_branches_project_id", "branches", ["project_id"])
    op.create_index("ix_branches_deleted_at", "branches", ["deleted_at"])

    # 3. Add branch_name column to change_orders
    op.add_column(
        "change_orders",
        sa.Column(
            "branch_name",
            sa.String(80),
            nullable=True,
            comment="Explicit link to branches table",
        ),
    )
    op.create_index("ix_change_orders_branch_name", "change_orders", ["branch_name"])

    # 4. Create main branches for existing projects
    op.execute("""
        INSERT INTO branches (name, project_id, type, locked, created_at, created_by)
        SELECT
            'main' as name,
            project_id,
            'main' as type,
            false as locked,
            NOW() as created_at,
            COALESCE(created_by, '00000000-0000-0000-0000-000000000000'::uuid) as created_by
        FROM projects
        ON CONFLICT (name, project_id) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema - remove branches table and branch_name column."""

    # Remove branch_name column and index
    op.drop_index("ix_change_orders_branch_name", table_name="change_orders")
    op.drop_column("change_orders", "branch_name")

    # Remove branches table and indexes
    op.drop_index("ix_branches_deleted_at", table_name="branches")
    op.drop_index("ix_branches_project_id", table_name="branches")
    op.drop_index("ix_branches_type", table_name="branches")
    op.drop_table("branches")
