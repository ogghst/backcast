"""drop_unique_constraint_multi_role

Revision ID: 64f26b376a85
Revises: c979abba696b
Create Date: 2026-05-15 07:49:33.390656

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "64f26b376a85"
down_revision: Union[str, Sequence[str], None] = "c979abba696b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unique constraint to allow multiple roles per scope."""
    op.drop_constraint(
        "uq_user_role_assignment_scope", "user_role_assignments", type_="unique"
    )


def downgrade() -> None:
    """Re-create unique constraint (will fail if duplicate rows exist)."""
    op.create_unique_constraint(
        "uq_user_role_assignment_scope",
        "user_role_assignments",
        ["user_id", "scope_type", "scope_id"],
    )
