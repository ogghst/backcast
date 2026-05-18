"""Migrate project_members to user_role_assignments with correct role mapping.

Revision ID: 20260511b_migrate_project_members
Revises: 20260511_project_rbac_roles
Create Date: 2026-05-11

Re-runs the project member-to-unified-RBAC migration now that rbac_roles
contains matching project-scoped role names (project_admin, project_manager,
project_editor, project_viewer). The original migration 20260510b ran before
these roles existed, resulting in 0 rows migrated for project members.

Idempotent via NOT EXISTS -- safe to run multiple times.
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260511b_proj_member_migr"
down_revision: str | Sequence[str] | None = "20260511_project_rbac_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Insert user_role_assignments from project_members + rbac_roles.

    JOINs on rbac_roles.name = project_members.role, which now works
    because the 20260511_project_rbac_roles migration inserted matching
    role names. Uses NOT EXISTS to skip already-migrated rows.
    """
    conn = op.get_bind()

    conn.execute(
        text("""
            INSERT INTO user_role_assignments (
                id, user_id, role_id, scope_type, scope_id,
                metadata, granted_by, granted_at, expires_at,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                pm.user_id,
                r.id,
                'project',
                pm.project_id,
                NULL,
                pm.assigned_by,
                COALESCE(pm.assigned_at, now()),
                NULL,
                now(),
                now()
            FROM project_members pm
            JOIN rbac_roles r ON r.name = pm.role
            WHERE NOT EXISTS (
                SELECT 1 FROM user_role_assignments ura
                WHERE ura.user_id = pm.user_id
                  AND ura.scope_type = 'project'
                  AND ura.scope_id = pm.project_id
            )
        """)
    )

    # Log migration results
    project_count = conn.execute(
        text(
            "SELECT count(*) FROM user_role_assignments WHERE scope_type = 'project'"
        )
    ).scalar()
    print(
        f"Project member migration complete: "
        f"{project_count} project-scoped assignments"
    )


def downgrade() -> None:
    """Remove all project-scoped user_role_assignments.

    These will be re-created on re-upgrade from project_members data.
    """
    conn = op.get_bind()

    conn.execute(
        text(
            "DELETE FROM user_role_assignments WHERE scope_type = 'project'"
        )
    )
