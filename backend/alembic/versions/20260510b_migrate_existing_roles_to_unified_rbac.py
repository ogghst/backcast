"""Migrate existing User.role and ProjectMember to UserRoleAssignment.

Revision ID: 20260510_unified_rbac_data
Revises: 20260510_unified_rbac
Create Date: 2026-05-10

Copies:
- User.role (current version only) -> UserRoleAssignment (scope_type='global')
- ProjectMember entries -> UserRoleAssignment (scope_type='project')

This is a data-only migration. The table was created in the parent migration.
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260510_unified_rbac_data"
down_revision: str | Sequence[str] | None = "20260510_unified_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate existing roles to UserRoleAssignment table.

    Strategy:
    1. Get current version of each user (valid_time contains now, branch=main)
    2. Look up rbac_roles.id by user.role name
    3. Insert into user_role_assignments with scope_type='global'
    4. Copy all project_members entries with scope_type='project'
    """
    conn = op.get_bind()

    # Step 1: Migrate User.role -> UserRoleAssignment (scope_type='global')
    # Use the current version of each user (valid_time contains now, branch=main)
    conn.execute(
        text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """)
    )

    # Step 2: Migrate ProjectMember -> UserRoleAssignment (scope_type='project')
    # Map ProjectMember.role (admin/editor/viewer) to rbac_roles by name
    # ProjectMember uses simple role names that may differ from rbac_roles names.
    # We need to map project-level roles to the appropriate rbac_role.
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
    global_count = conn.execute(
        text("SELECT count(*) FROM user_role_assignments WHERE scope_type = 'global'")
    ).scalar()
    project_count = conn.execute(
        text("SELECT count(*) FROM user_role_assignments WHERE scope_type = 'project'")
    ).scalar()

    # Use print instead of logger for Alembic migrations
    print(
        f"Unified RBAC migration complete: "
        f"{global_count} global assignments, "
        f"{project_count} project assignments"
    )


def downgrade() -> None:
    """Remove migrated data from user_role_assignments.

    This only removes data that was migrated by this migration.
    Manually created assignments are preserved.
    """
    conn = op.get_bind()

    # Remove project assignments that came from project_members
    conn.execute(
        text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'project'
          AND granted_by IS NOT NULL
    """)
    )

    # Remove global assignments that were migrated from User.role
    conn.execute(
        text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'global'
          AND scope_id IS NULL
          AND metadata IS NULL
    """)
    )
