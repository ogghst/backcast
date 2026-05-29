"""fix_rbac_permission_naming

Revision ID: c115477454ca
Revises: ansi748_full_restructure
Create Date: 2026-05-27 22:53:24.648326

Remove stale RBAC permissions that were renamed during ANSI-748 migration.
The new permission names (wbs-element-*, organizational-unit-*, cost-event-*)
were already seeded alongside the old ones. This migration only cleans up
the duplicate old-named rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c115477454ca"
down_revision: Union[str, Sequence[str], None] = "ansi748_full_restructure"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Stale permissions to remove (replaced by ANSI-748 names).
# wbe-*           -> wbs-element-*
# department-*    -> organizational-unit-*
# quality-event-* -> cost-event-* (including quality-event-write which has no replacement)
STALE_PERMISSIONS = [
    "wbe-create",
    "wbe-read",
    "wbe-update",
    "wbe-delete",
    "department-create",
    "department-read",
    "department-update",
    "department-delete",
    "quality-event-create",
    "quality-event-read",
    "quality-event-update",
    "quality-event-delete",
    "quality-event-write",
]


def upgrade() -> None:
    """Remove stale RBAC permission rows with old naming."""
    rp = sa.table(
        "rbac_role_permissions",
        sa.column("id", sa.Uuid),
        sa.column("role_id", sa.Uuid),
        sa.column("permission", sa.String),
    )
    op.execute(
        rp.delete().where(
            rp.c.permission.in_(STALE_PERMISSIONS)
        )
    )


def downgrade() -> None:
    """No-op: stale permissions were duplicates, not recoverable from this point."""
    pass
