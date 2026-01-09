"""add_indexes_for_server_side_filtering

Adds indexes on frequently filtered columns to improve performance
of server-side search, filtering, and sorting operations.

Indexes added:
- projects.status (filtered by status)
- projects.name (searched and sorted)
- wbes.level (filtered by level)
- wbes.name (searched and sorted)
- cost_elements.name (searched and sorted)

Revision ID: 5ae1f9320c4b
Revises: b2c3d4e5f6g7
Create Date: 2026-01-08 14:54:46.294342

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ae1f9320c4b"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6g7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes for server-side filtering performance."""
    # Projects table
    op.create_index("ix_projects_status", "projects", ["status"], unique=False)
    op.create_index("ix_projects_name", "projects", ["name"], unique=False)

    # WBEs table
    op.create_index("ix_wbes_level", "wbes", ["level"], unique=False)
    op.create_index("ix_wbes_name", "wbes", ["name"], unique=False)

    # Cost Elements table
    op.create_index("ix_cost_elements_name", "cost_elements", ["name"], unique=False)


def downgrade() -> None:
    """Remove indexes for server-side filtering."""
    # Drop in reverse order
    op.drop_index("ix_cost_elements_name", table_name="cost_elements")
    op.drop_index("ix_wbes_name", table_name="wbes")
    op.drop_index("ix_wbes_level", table_name="wbes")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
