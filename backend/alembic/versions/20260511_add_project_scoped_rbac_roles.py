"""Add 4 project-scoped RBAC roles with permissions.

Revision ID: 20260511_project_rbac_roles
Revises: 20260510_unified_rbac_data
Create Date: 2026-05-11

Inserts project_admin, project_manager, project_editor, project_viewer
into rbac_roles (is_system=True) and their permissions into
rbac_role_permissions. Idempotent via NOT EXISTS checks.
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260511_project_rbac_roles"
down_revision: str | Sequence[str] | None = "20260510_unified_rbac_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Role definitions: name -> (description, permissions)
PROJECT_ROLES: dict[str, tuple[str, list[str]]] = {
    "project_admin": (
        "Full project management including member management",
        [
            "project-read",
            "project-update",
            "project-delete",
            "project-members-manage",
            "cost-element-create",
            "cost-element-read",
            "cost-element-update",
            "cost-element-delete",
            "wbe-create",
            "wbe-read",
            "wbe-update",
            "wbe-delete",
            "progress-entry-create",
            "progress-entry-read",
            "progress-entry-update",
            "progress-entry-delete",
            "change-order-create",
            "change-order-read",
            "change-order-update",
            "change-order-delete",
            "forecast-create",
            "forecast-read",
            "forecast-update",
            "forecast-delete",
        ],
    ),
    "project_manager": (
        "Project CRUD, cost elements, WBEs, forecasts",
        [
            "project-read",
            "project-update",
            "cost-element-create",
            "cost-element-read",
            "cost-element-update",
            "cost-element-delete",
            "wbe-create",
            "wbe-read",
            "wbe-update",
            "wbe-delete",
            "progress-entry-create",
            "progress-entry-read",
            "progress-entry-update",
            "progress-entry-delete",
            "change-order-create",
            "change-order-read",
            "forecast-create",
            "forecast-read",
            "forecast-update",
            "forecast-delete",
        ],
    ),
    "project_editor": (
        "Create/update cost elements, progress entries",
        [
            "project-read",
            "project-update",
            "cost-element-create",
            "cost-element-read",
            "cost-element-update",
            "wbe-read",
            "progress-entry-create",
            "progress-entry-read",
            "progress-entry-update",
            "change-order-read",
            "forecast-create",
            "forecast-read",
            "forecast-update",
        ],
    ),
    "project_viewer": (
        "Read-only project access",
        [
            "project-read",
            "cost-element-read",
            "wbe-read",
            "progress-entry-read",
            "change-order-read",
            "forecast-read",
        ],
    ),
}


def upgrade() -> None:
    """Insert project-scoped roles and permissions.

    Uses NOT EXISTS for idempotency -- safe to run multiple times.
    """
    conn = op.get_bind()

    for role_name, (description, permissions) in PROJECT_ROLES.items():
        # Insert role if not exists
        conn.execute(
            text("""
                INSERT INTO rbac_roles (id, name, description, is_system,
                                        created_at, updated_at)
                SELECT gen_random_uuid(),
                       CAST(:name AS VARCHAR(100)),
                       :description,
                       TRUE,
                       now(),
                       now()
                WHERE NOT EXISTS (
                    SELECT 1 FROM rbac_roles WHERE name = CAST(:name AS VARCHAR(100))
                )
            """),
            {"name": role_name, "description": description},
        )

        # Insert permissions for this role if not exists
        for perm in permissions:
            conn.execute(
                text("""
                    INSERT INTO rbac_role_permissions (
                        id, role_id, permission, created_at, updated_at
                    )
                    SELECT gen_random_uuid(),
                           r.id,
                           CAST(:permission AS VARCHAR(100)),
                           now(),
                           now()
                    FROM rbac_roles r
                    WHERE r.name = CAST(:role_name AS VARCHAR(100))
                      AND NOT EXISTS (
                        SELECT 1 FROM rbac_role_permissions rp
                        WHERE rp.role_id = r.id
                          AND rp.permission = CAST(:permission AS VARCHAR(100))
                    )
                """),
                {"role_name": role_name, "permission": perm},
            )

    # Log results
    project_role_count = conn.execute(
        text(
            "SELECT count(*) FROM rbac_roles "
            "WHERE name IN ('project_admin','project_manager',"
            "'project_editor','project_viewer')"
        )
    ).scalar()
    print(f"Project RBAC roles migration: {project_role_count} project roles exist")


def downgrade() -> None:
    """Remove project-scoped roles and their permissions.

    Cascades via FK delete-orphan, but we delete permissions
    explicitly first for clarity.
    """
    conn = op.get_bind()

    role_names = tuple(PROJECT_ROLES.keys())

    # Delete permissions first (explicit, even though FK cascades handle it)
    conn.execute(
        text("""
            DELETE FROM rbac_role_permissions
            WHERE role_id IN (
                SELECT id FROM rbac_roles
                WHERE name = ANY(:names)
            )
        """),
        {"names": list(role_names)},
    )

    # Delete roles
    conn.execute(
        text("""
            DELETE FROM rbac_roles
            WHERE name = ANY(:names)
        """),
        {"names": list(role_names)},
    )
