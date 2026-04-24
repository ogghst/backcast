"""add updated_at column to rbac_role_permissions

The RBACRolePermission model inherits from SimpleEntityBase which defines
an ``updated_at`` column, but the original migration (7fc133112eef) omitted
it.  This adds the missing column with a server default.

Revision ID: 87c3b39736a6
Revises: 7fc133112eef
Create Date: 2026-04-23 20:46:16.562166

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "87c3b39736a6"
down_revision: str | Sequence[str] | None = "7fc133112eef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add updated_at column to rbac_role_permissions."""
    op.add_column(
        "rbac_role_permissions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    """Remove updated_at column from rbac_role_permissions."""
    op.drop_column("rbac_role_permissions", "updated_at")
