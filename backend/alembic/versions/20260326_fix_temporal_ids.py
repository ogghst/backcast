"""Fix temporal entity unique constraints.

Revision ID: 20260326_fix_temporal_ids
Revises: 16efd3b4c551
Create Date: 2026-03-26 12:00:00.000000

This migration fixes incorrect unique constraints on temporal entity root_id columns.
For versioned/temporal entities, there should be MULTIPLE rows per root_id (one per version),
with a PARTIAL unique index ensuring only ONE current version.

IMPORTANT: PostgreSQL does NOT support foreign keys referencing partial indexes.
For temporal entities, referential integrity must be enforced at the application layer.
This migration removes FK constraints and replaces them with application-level validation.

Changes:
1. Drop fk_project_members_project_id_projects (FK - incompatible with partial indexes)
2. Drop fk_project_members_user_id_users (FK - incompatible with partial indexes)
3. Drop fk_project_members_assigned_by_users (FK - incompatible with partial indexes)
4. Drop uq_projects_project_id (regular unique) - create partial index instead
5. Drop uq_users_user_id (regular unique) - correct partial index already exists

Note: The project_members table will now rely on application-level referential integrity
to ensure project_id and user_id references valid current projects and users.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260326_fix_temporal_ids"
down_revision: str | Sequence[str] | None = "16efd3b4c551"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - fix temporal entity unique constraints."""

    # 1. Drop all foreign key constraints that reference the unique constraints we're replacing
    # PostgreSQL doesn't support FKs on partial indexes, so we remove these FKs
    # and rely on application-level referential integrity instead

    # FKs from project_members to projects
    op.drop_constraint(
        "fk_project_members_project_id_projects",
        "project_members",
        type_="foreignkey",
    )

    # FKs from project_members to users
    op.drop_constraint(
        "fk_project_members_user_id_users",
        "project_members",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_project_members_assigned_by_users",
        "project_members",
        type_="foreignkey",
    )

    # 2. Drop the incorrect regular unique constraint on projects.project_id
    op.drop_constraint(
        "uq_projects_project_id",
        "projects",
        type_="unique",
    )

    # 3. Create partial unique index for projects (current versions only)
    # This allows multiple historical versions but only ONE current version per project_id
    op.execute(
        """
        CREATE UNIQUE INDEX uq_projects_project_id_current
        ON projects(project_id)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;
        """
    )

    # 4. Drop the incorrect regular unique constraint on users.user_id
    # The correct partial index (uq_users_current_user_id) already exists
    op.drop_constraint(
        "uq_users_user_id",
        "users",
        type_="unique",
    )


def downgrade() -> None:
    """Downgrade schema - restore original (broken) constraints."""

    # Note: This downgrade will break versioning functionality!
    # It's provided for completeness but should not be used in production.

    # Restore the incorrect regular unique constraint on users.user_id
    op.create_unique_constraint(
        "uq_users_user_id",
        "users",
        ["user_id"],
    )

    # Drop the partial unique index on projects
    op.execute("DROP INDEX IF EXISTS uq_projects_project_id_current;")

    # Restore the incorrect regular unique constraint on projects.project_id
    op.create_unique_constraint(
        "uq_projects_project_id",
        "projects",
        ["project_id"],
    )

    # Restore the foreign key constraints (will work with regular unique constraints)
    op.create_foreign_key(
        "fk_project_members_project_id_projects",
        "project_members",
        "projects",
        ["project_id"],
        ["project_id"],
    )
    op.create_foreign_key(
        "fk_project_members_user_id_users",
        "project_members",
        "users",
        ["user_id"],
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_project_members_assigned_by_users",
        "project_members",
        "users",
        ["assigned_by"],
        ["user_id"],
    )
