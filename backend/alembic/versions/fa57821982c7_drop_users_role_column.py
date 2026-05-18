"""drop_users_role_column

Revision ID: fa57821982c7
Revises: 1eba1b50cdf5
Create Date: 2026-05-16 06:43:25.307193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa57821982c7'
down_revision: Union[str, Sequence[str], None] = '1eba1b50cdf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the role column from users table.

    Role information is now stored exclusively in UserRoleAssignment
    (unified RBAC), making the User.role column redundant.
    """
    op.drop_column("users", "role")


def downgrade() -> None:
    """Re-add the role column to users table."""
    op.add_column(
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer")
    )
