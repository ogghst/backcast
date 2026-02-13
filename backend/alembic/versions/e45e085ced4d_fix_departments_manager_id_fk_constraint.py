"""fix_departments_manager_id_fk_constraint

Revision ID: e45e085ced4d
Revises: 0e0378323809
Create Date: 2026-01-18 00:03:33.681646

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e45e085ced4d'
down_revision: str | Sequence[str] | None = '0e0378323809'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - fix departments.manager_id FK to reference users.user_id.

    NOTE: This is a special case for versioned entities. The manager_id field
    should reference users.user_id (the root entity ID), but we cannot create a
    traditional foreign key constraint because user_id is not unique - it appears
    in multiple rows due to versioning.

    SOLUTION: We drop the incorrect FK constraint that references users.id
    (which would break when users are versioned) and rely on application-level
    validation and ORM relationship mapping to ensure referential integrity.

    The SQLAlchemy model in app/models/domain/department.py correctly defines
    the relationship with ForeignKey("users.user_id"), which allows the ORM
    to handle joins correctly, even without a database-level constraint.
    """
    # Drop the incorrect foreign key constraint
    op.drop_constraint(
        "departments_manager_id_fkey", table_name="departments", type_="foreignkey"
    )


def downgrade() -> None:
    """Downgrade schema - recreate the old (incorrect) FK constraint."""
    # Recreate the old foreign key constraint for rollback
    op.create_foreign_key(
        "departments_manager_id_fkey",
        "departments",
        "users",
        ["manager_id"],
        ["id"],
    )
