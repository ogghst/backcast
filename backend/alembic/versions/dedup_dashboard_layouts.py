"""Clean up duplicate dashboard layouts from clone naming bug.

The clone endpoint ignored the `name` field, always creating
"Copy of {name}" instead of the requested name. This caused
the frontend to create a new clone on every page visit because
the named lookup failed.

For each (user_id, project_id, normalized_name) group across
ALL non-template layouts (both "Copy of X" and correctly-named "X"):
  - Keep only the most recently updated layout
  - Rename "Copy of X" → "X"
  - Delete the rest

Revision ID: dedup_dashboard_layouts
"""

from alembic import op

revision = "dedup_dashboard_layouts"
down_revision = None  # data migration, order doesn't matter
branch_labels = None
depends_on = "20260405_add_dashboard_layouts"


def upgrade() -> None:
    # asyncpg cannot execute multiple statements in one op.execute call,
    # so we split the rename and delete into separate steps.
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id, project_id,
                                    CASE WHEN name LIKE 'Copy of %%' THEN substring(name FROM 10) ELSE name END
                       ORDER BY updated_at DESC
                   ) AS rn,
                   CASE WHEN name LIKE 'Copy of %%' THEN substring(name FROM 10) ELSE name END AS clean_name
            FROM dashboard_layouts
            WHERE is_template = false
        )
        UPDATE dashboard_layouts d
        SET name = r.clean_name
        FROM ranked r
        WHERE d.id = r.id AND r.rn = 1 AND d.name LIKE 'Copy of %'
    """)
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id, project_id,
                                    CASE WHEN name LIKE 'Copy of %%' THEN substring(name FROM 10) ELSE name END
                       ORDER BY updated_at DESC
                   ) AS rn
            FROM dashboard_layouts
            WHERE is_template = false
        )
        DELETE FROM dashboard_layouts
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """)


def downgrade() -> None:
    # No-op: can't reconstruct deleted rows
    pass
