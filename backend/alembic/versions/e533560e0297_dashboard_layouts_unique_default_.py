"""dashboard_layouts unique default partial indexes

Revision ID: e533560e0297
Revises: c5d64be2c146
Create Date: 2026-06-29 14:59:32.355966

G8 structural fix for the concurrent first-visit-clone race on
``dashboard_layouts.is_default``. Two clones racing the same user's first visit
to a project (or the global dashboard) can both pass the
``_clear_default_for_user_project`` read-then-write guard and both insert
``is_default=True`` non-template rows, leaving duplicate defaults in the same
scope.

These two NULL-safe unique partial indexes make the invariant DB-enforced and
serialization-safe. Postgres treats NULL != NULL in unique indexes, so a single
``(user_id, project_id)`` index would NOT prevent duplicate GLOBAL defaults
(``project_id IS NULL``). Two partial indexes are required:

1. ``uq_dashboard_layouts_default_global`` UNIQUE on ``(user_id)`` WHERE
   ``is_template = false AND is_default = true AND project_id IS NULL`` —
   at most one default GLOBAL layout per user.
2. ``uq_dashboard_layouts_default_project`` UNIQUE on ``(user_id, project_id)``
   WHERE ``is_template = false AND is_default = true AND project_id IS NOT
   NULL`` — at most one default layout per (user, project).

A dedup pre-step hard-deletes pre-existing duplicate ``is_default=True``
non-template rows per scope (keeping the oldest / lowest ``id``) so the unique
index can be created. The downgrade does NOT undo the dedup deletes — that data
is gone — it only drops the indexes.

Mirrors the C1 pattern in ``c93e9767de59_custom_fields_phase0.py``.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e533560e0297"
down_revision: Union[str, Sequence[str], None] = "c5d64be2c146"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Partial-index WHERE clauses (mirrored in the ORM model
# app/models/domain/dashboard_layout.py __table_args__).
# ---------------------------------------------------------------------------
_GLOBAL_WHERE = "is_template = false AND is_default = true AND project_id IS NULL"
_PROJECT_WHERE = (
    "is_template = false AND is_default = true AND project_id IS NOT NULL"
)


def upgrade() -> None:
    """Upgrade schema."""
    # -------------------------------------------------------------------------
    # Dedup pre-step: hard-delete duplicate is_default=True non-template rows
    # per (user_id, project_id) scope, keeping the oldest (lowest id).
    #
    # Safe no-op on a clean DB. The lost-first-visit-clone race that could
    # create such duplicates is exactly what the partial indexes below now
    # prevent at the DB layer. The downgrade does NOT undo these deletes —
    # that data is unrecoverable; it only drops the indexes.
    # -------------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            DELETE FROM dashboard_layouts
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY user_id,
                                            COALESCE(project_id, '00000000-0000-0000-0000-000000000000')
                               ORDER BY id ASC
                           ) AS rn
                    FROM dashboard_layouts
                    WHERE is_template = false
                      AND is_default = true
                  ) s
                WHERE rn > 1
            )
            """
        )
    )

    # -------------------------------------------------------------------------
    # (1) UNIQUE on (user_id) WHERE is_template=false AND is_default=true AND
    #     project_id IS NULL — at most one default GLOBAL layout per user.
    # -------------------------------------------------------------------------
    op.create_index(
        "uq_dashboard_layouts_default_global",
        "dashboard_layouts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text(_GLOBAL_WHERE),
    )

    # -------------------------------------------------------------------------
    # (2) UNIQUE on (user_id, project_id) WHERE is_template=false AND
    #     is_default=true AND project_id IS NOT NULL — at most one default
    #     layout per (user, project).
    # -------------------------------------------------------------------------
    op.create_index(
        "uq_dashboard_layouts_default_project",
        "dashboard_layouts",
        ["user_id", "project_id"],
        unique=True,
        postgresql_where=sa.text(_PROJECT_WHERE),
    )


def downgrade() -> None:
    """Downgrade schema (reverse of upgrade, EXCEPT the dedup deletes — that
    data is unrecoverable; only the indexes are dropped)."""
    op.drop_index(
        "uq_dashboard_layouts_default_project",
        table_name="dashboard_layouts",
        postgresql_where=sa.text(_PROJECT_WHERE),
    )
    op.drop_index(
        "uq_dashboard_layouts_default_global",
        table_name="dashboard_layouts",
        postgresql_where=sa.text(_GLOBAL_WHERE),
    )
