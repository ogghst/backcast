"""dashboard_layout role + scope columns

Revision ID: c5d64be2c146
Revises: 44d00c4e21f7
Create Date: 2026-06-29 09:20:18.914194

Adds two nullable, indexed columns to ``dashboard_layouts`` to support
role-tagged portfolio templates (Phase 7 of global-dashboard-widgets):

- ``role`` (VARCHAR(64)) — which role a portfolio template defaults to.
- ``scope`` (VARCHAR(16)) — template audience discriminator
  (``"project"`` vs ``"portfolio"``).

Existing project templates (the 4 seeded at startup) are backfilled to
``scope = 'project'``. Non-template user layouts keep ``scope = NULL``
(they are distinguished by ``project_id``, not ``scope``).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d64be2c146"
down_revision: Union[str, Sequence[str], None] = "44d00c4e21f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ``role`` + ``scope`` columns and backfill existing templates."""
    with op.batch_alter_table("dashboard_layouts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("scope", sa.String(length=16), nullable=True))
        batch_op.create_index(
            op.f("ix_dashboard_layouts_role"), ["role"], unique=False
        )
        batch_op.create_index(
            op.f("ix_dashboard_layouts_scope"), ["scope"], unique=False
        )

    # Tag already-seeded project templates so a fresh filter by scope works.
    # Non-template user layouts intentionally keep scope NULL.
    op.execute(
        "UPDATE dashboard_layouts SET scope = 'project' "
        "WHERE is_template = true AND scope IS NULL"
    )


def downgrade() -> None:
    """Drop the ``role`` + ``scope`` columns."""
    with op.batch_alter_table("dashboard_layouts", schema=None) as batch_op:
        batch_op.drop_index(op.f("ix_dashboard_layouts_scope"))
        batch_op.drop_index(op.f("ix_dashboard_layouts_role"))
        batch_op.drop_column("scope")
        batch_op.drop_column("role")
