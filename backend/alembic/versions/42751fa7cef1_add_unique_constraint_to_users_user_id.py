"""add_unique_constraint_to_users_and_projects_root_id

Revision ID: 42751fa7cef1
Revises: 021bb7eeaa21
Create Date: 2026-03-21 15:38:06.886155

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '42751fa7cef1'
down_revision: str | Sequence[str] | None = '1fd0ec9f01a4'  # Comes before project_members
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Add unique constraints to root ID columns to allow foreign key references.
    This is required for the project_members table foreign key constraints.
    """
    # Add unique constraint to users.user_id
    op.create_unique_constraint(
        "uq_users_user_id",
        "users",
        ["user_id"]
    )

    # Add unique constraint to projects.project_id
    op.create_unique_constraint(
        "uq_projects_project_id",
        "projects",
        ["project_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_users_user_id",
        "users",
        type_="unique"
    )
    op.drop_constraint(
        "uq_projects_project_id",
        "projects",
        type_="unique"
    )
