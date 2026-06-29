"""Idempotent startup seeder for default users, RBAC roles, and role assignments.

Safe to run on every application startup. Each step checks for existing data
and skips if already present.
"""

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SYSTEM_ACTOR = UUID("00000000-0000-0000-0000-000000000001")

# ---------------------------------------------------------------------------
# Default users
# ---------------------------------------------------------------------------

DEFAULT_USERS: list[dict[str, str | UUID]] = [
    {
        "user_id": UUID("e03556f3-4385-5d68-a685-af307fc8af5c"),
        "email": "admin@backcast.org",
        "password": "adminadmin",
        "full_name": "Admin User",
    },
    {
        "user_id": UUID("4395b53f-d92a-4ad5-aca4-33ba78cc876b"),
        "email": "pm@backcast.org",
        "password": "backcast",
        "full_name": "Project Manager",
    },
    {
        "user_id": UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        "email": "viewer@backcast.org",
        "password": "backcast",
        "full_name": "Viewer User",
    },
    {
        "user_id": UUID("b2c3d4e5-f6a7-8901-bcde-f23456789012"),
        "email": "controller@backcast.org",
        "password": "backcast",
        "full_name": "Cost Controller",
    },
    {
        "user_id": UUID("c3d4e5f6-a7b8-9012-cdef-345678901234"),
        "email": "pmo-director@backcast.org",
        "password": "backcast",
        "full_name": "PMO Director",
    },
]

# ---------------------------------------------------------------------------
# RBAC roles and permissions
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, dict[str, str | list[str]]] = {
    "admin": {
        "description": "Full system administrator with unrestricted access",
        "permissions": [
            "user-read",
            "user-create",
            "user-update",
            "user-delete",
            "role-assignment-read",
            "role-assignment-create",
            "role-assignment-update",
            "role-assignment-delete",
            "organizational-unit-read",
            "organizational-unit-create",
            "organizational-unit-update",
            "organizational-unit-delete",
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "project-documents-read",
            "project-documents-write",
            "project-documents-delete",
            "wbs-element-read",
            "wbs-element-create",
            "wbs-element-update",
            "wbs-element-delete",
            "control-account-read",
            "control-account-create",
            "control-account-update",
            "control-account-delete",
            "work-package-read",
            "work-package-create",
            "work-package-update",
            "work-package-delete",
            "cost-element-type-read",
            "cost-element-type-create",
            "cost-element-type-update",
            "cost-element-type-delete",
            "custom-entity-template-read",
            "custom-entity-template-create",
            "custom-entity-template-update",
            "custom-entity-template-delete",
            "cost-event-type-read",
            "cost-event-type-create",
            "cost-event-type-update",
            "cost-event-type-delete",
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-delete",
            "cost-event-read",
            "cost-event-create",
            "cost-event-update",
            "cost-event-delete",
            "cost-registration-read",
            "cost-registration-create",
            "cost-registration-update",
            "cost-registration-delete",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
            "change-order-submit",
            "change-order-approve",
            "change-order-implement",
            "change-order-recover",
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "forecast-delete",
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "schedule-baseline-delete",
            "progress-entry-read",
            "progress-entry-create",
            "progress-entry-update",
            "progress-entry-delete",
            "evm-read",
            "evm-create",
            "evm-update",
            "evm-delete",
            "ai-config-read",
            "ai-config-create",
            "ai-config-update",
            "ai-config-delete",
            "ai-chat",
            "mcp-server-read",
            "mcp-server-create",
            "mcp-server-update",
            "mcp-server-delete",
            "mcp-tool-execute",
            "dashboard-template-update",
            "project-budget-settings-read",
            "project-budget-settings-write",
            "change-order-workflow-config-manage",
            "change-order-workflow-config-override",
            "change-order-escalate",
            "temporal-write",
            "system-dump-reseed",
            "agent-schedule-manage",
            "notifications-send",
            "portfolio-read",
            "customer-read",
            "customer-create",
            "customer-update",
            "customer-delete",
            "currency-rate-read",
            "currency-rate-create",
            "currency-rate-update",
        ],
    },
    "manager": {
        "description": "Project manager with most CRUD permissions",
        "permissions": [
            "user-read",
            "user-update",
            "organizational-unit-read",
            "organizational-unit-create",
            "organizational-unit-update",
            "organizational-unit-delete",
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "project-documents-read",
            "project-documents-write",
            "wbs-element-read",
            "wbs-element-create",
            "wbs-element-update",
            "wbs-element-delete",
            "control-account-read",
            "control-account-create",
            "control-account-update",
            "control-account-delete",
            "work-package-read",
            "work-package-create",
            "work-package-update",
            "work-package-delete",
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-type-read",
            "custom-entity-template-read",
            "cost-event-type-read",
            "cost-event-read",
            "cost-event-create",
            "cost-event-update",
            "cost-event-delete",
            "cost-registration-read",
            "cost-registration-create",
            "cost-registration-update",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
            "change-order-submit",
            "change-order-approve",
            "change-order-implement",
            "change-order-escalate",
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "forecast-delete",
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "schedule-baseline-delete",
            "progress-entry-read",
            "progress-entry-create",
            "progress-entry-update",
            "progress-entry-delete",
            "evm-read",
            "evm-create",
            "evm-update",
            "evm-delete",
            "ai-chat",
            "project-budget-settings-read",
            "project-budget-settings-write",
            "agent-schedule-manage",
            "notifications-send",
            "portfolio-read",
            "customer-read",
            "customer-create",
            "customer-update",
            "customer-delete",
        ],
    },
    "cost-controller": {
        "description": (
            "Cost controlling analyst — read-heavy cost/EVM access plus "
            "forecast revision; no project/structure CRUD or approvals."
        ),
        "permissions": [
            "portfolio-read",
            "project-read",
            "project-documents-read",
            "wbs-element-read",
            "control-account-read",
            "work-package-read",
            "cost-element-read",
            "cost-element-type-read",
            "cost-event-read",
            "cost-event-type-read",
            "cost-registration-read",
            "change-order-read",
            "forecast-read",
            "schedule-baseline-read",
            "evm-read",
            "progress-entry-read",
            "custom-entity-template-read",
            "project-budget-settings-read",
            "organizational-unit-read",
            "customer-read",
            "currency-rate-read",
            "user-read",
            "forecast-update",
        ],
    },
    "pmo-director": {
        "description": (
            "PMO director — read-heavy portfolio/schedule oversight plus "
            "change-order governance; no structural CRUD or cost writes."
        ),
        "permissions": [
            "portfolio-read",
            "project-read",
            "project-documents-read",
            "wbs-element-read",
            "control-account-read",
            "work-package-read",
            "cost-element-read",
            "cost-element-type-read",
            "cost-event-read",
            "cost-event-type-read",
            "cost-registration-read",
            "change-order-read",
            "forecast-read",
            "schedule-baseline-read",
            "evm-read",
            "progress-entry-read",
            "custom-entity-template-read",
            "project-budget-settings-read",
            "organizational-unit-read",
            "customer-read",
            "currency-rate-read",
            "user-read",
            "change-order-submit",
            "change-order-approve",
            "change-order-escalate",
        ],
    },
    "viewer": {
        "description": "Read-only access across the system",
        "permissions": [
            "organizational-unit-read",
            "project-read",
            "project-documents-read",
            "wbs-element-read",
            "control-account-read",
            "work-package-read",
            "cost-element-read",
            "cost-element-type-read",
            "custom-entity-template-read",
            "cost-event-type-read",
            "cost-event-read",
            "cost-registration-read",
            "change-order-read",
            "change-order-approve",
            "forecast-read",
            "schedule-baseline-read",
            "customer-read",
            # portfolio-read is intentionally NOT granted to viewer/ai-viewer:
            # portfolio dashboards are manager+ only (locked decision).
        ],
    },
    "ai-viewer": {
        "description": "Read access with AI chat capability",
        "permissions": [
            "project-read",
            "project-documents-read",
            "wbs-element-read",
            "control-account-read",
            "work-package-read",
            "cost-element-read",
            "cost-element-type-read",
            "custom-entity-template-read",
            "cost-event-type-read",
            "cost-event-read",
            "cost-registration-read",
            "change-order-read",
            "forecast-read",
            "schedule-baseline-read",
            "evm-read",
            "user-read",
            "organizational-unit-read",
            "ai-chat",
            "mcp-tool-execute",
            "progress-entry-read",
            "customer-read",
        ],
    },
    "ai-manager": {
        "description": "AI agent with read/write access",
        "permissions": [
            "project-read",
            "project-create",
            "project-update",
            "project-documents-read",
            "project-documents-write",
            "wbs-element-read",
            "wbs-element-create",
            "wbs-element-update",
            "wbs-element-delete",
            "control-account-read",
            "control-account-create",
            "control-account-update",
            "control-account-delete",
            "work-package-read",
            "work-package-create",
            "work-package-update",
            "work-package-delete",
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-delete",
            "cost-element-type-read",
            "cost-element-type-create",
            "cost-element-type-update",
            "cost-element-type-delete",
            "custom-entity-template-read",
            "custom-entity-template-create",
            "custom-entity-template-update",
            "custom-entity-template-delete",
            "cost-event-type-read",
            "cost-event-read",
            "cost-event-create",
            "cost-event-update",
            "cost-event-delete",
            "cost-registration-read",
            "cost-registration-create",
            "cost-registration-update",
            "cost-registration-delete",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
            "change-order-submit",
            "change-order-approve",
            "change-order-implement",
            "change-order-escalate",
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "forecast-delete",
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "schedule-baseline-delete",
            "mcp-server-read",
            "mcp-tool-execute",
            "progress-entry-read",
            "progress-entry-create",
            "progress-entry-update",
            "progress-entry-delete",
            "evm-read",
            "evm-create",
            "evm-update",
            "evm-delete",
            "ai-chat",
            "user-read",
            "organizational-unit-read",
            "project-delete",
            "agent-schedule-manage",
            "notifications-send",
            "portfolio-read",
            "customer-read",
            "customer-create",
            "customer-update",
            "customer-delete",
        ],
    },
    "ai-admin": {
        "description": "AI agent with full administrative access",
        "permissions": [
            "user-read",
            "user-create",
            "user-update",
            "user-delete",
            "organizational-unit-read",
            "organizational-unit-create",
            "organizational-unit-update",
            "organizational-unit-delete",
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "project-documents-read",
            "project-documents-write",
            "project-documents-delete",
            "wbs-element-read",
            "wbs-element-create",
            "wbs-element-update",
            "wbs-element-delete",
            "control-account-read",
            "control-account-create",
            "control-account-update",
            "control-account-delete",
            "work-package-read",
            "work-package-create",
            "work-package-update",
            "work-package-delete",
            "cost-element-type-read",
            "cost-element-type-create",
            "cost-element-type-update",
            "cost-element-type-delete",
            "custom-entity-template-read",
            "custom-entity-template-create",
            "custom-entity-template-update",
            "custom-entity-template-delete",
            "cost-event-type-read",
            "cost-event-type-create",
            "cost-event-type-update",
            "cost-event-type-delete",
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-delete",
            "cost-event-read",
            "cost-event-create",
            "cost-event-update",
            "cost-event-delete",
            "cost-registration-read",
            "cost-registration-create",
            "cost-registration-update",
            "cost-registration-delete",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
            "change-order-submit",
            "change-order-approve",
            "change-order-implement",
            "change-order-escalate",
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "forecast-delete",
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "schedule-baseline-delete",
            "progress-entry-read",
            "progress-entry-create",
            "progress-entry-update",
            "progress-entry-delete",
            "evm-read",
            "evm-create",
            "evm-update",
            "evm-delete",
            "ai-config-read",
            "ai-config-create",
            "ai-config-update",
            "ai-config-delete",
            "ai-chat",
            "mcp-server-read",
            "mcp-server-create",
            "mcp-server-update",
            "mcp-server-delete",
            "mcp-tool-execute",
            "dashboard-template-update",
            "project-budget-settings-read",
            "project-budget-settings-write",
            "change-order-workflow-config-manage",
            "change-order-workflow-config-override",
            "temporal-write",
            "notifications-send",
            "portfolio-read",
            "customer-read",
            "customer-create",
            "customer-update",
            "customer-delete",
            "currency-rate-read",
            "currency-rate-create",
            "currency-rate-update",
        ],
    },
}

# Map default user emails to their global role name
USER_ROLE_MAP: dict[str, str] = {
    "admin@backcast.org": "admin",
    "pm@backcast.org": "manager",
    "viewer@backcast.org": "viewer",
    "controller@backcast.org": "cost-controller",
    "pmo-director@backcast.org": "pmo-director",
}


async def seed_users_and_rbac(session: AsyncSession) -> None:
    """Seed default users, RBAC roles/permissions, and role assignments.

    Idempotent -- each step checks for existing rows and skips if present.
    Safe to call on every application startup.
    """
    from app.core.security import get_password_hash

    await _seed_users(session, get_password_hash)
    role_map = await _seed_rbac_roles(session)
    await _seed_role_assignments(session, role_map)


async def seed_users_and_rbac_from_data(
    session: AsyncSession,
    data: dict[str, Any],
) -> None:
    """Seed users, RBAC roles/permissions, and role assignments from a data dict.

    Accepts a dict matching the seed_data.json schema:
    {
        "rbac_roles": { "<role_name>": { "description": "...", "permissions": [...] } },
        "users": [{ "user_id": "...", "email": "...", "password": "...", "full_name": "..." }],
        "user_role_assignments": { "email@domain": "role_name" }
    }

    This is the function the API reseed endpoint calls.
    """
    from app.core.security import get_password_hash
    from app.models.domain.rbac import RBACRole, RBACRolePermission
    from app.models.domain.user import User
    from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment

    rbac_roles = data["rbac_roles"]
    users_data = data["users"]
    role_assignments = data["user_role_assignments"]

    # Seed users
    # Build a map of user_id -> password from default users for fallback
    default_passwords: dict[str, str] = {
        str(u["user_id"]): str(u["password"]) for u in DEFAULT_USERS
    }

    for user_def in users_data:
        user_id = UUID(user_def["user_id"])
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            continue

        # Use provided password, or fall back to default, or use "backcast"
        password = str(user_def.get("password", ""))
        if not password:
            password = default_passwords.get(str(user_id), "backcast")

        user = User(
            id=user_id,
            user_id=user_id,
            email=str(user_def["email"]),
            hashed_password=get_password_hash(password),
            full_name=str(user_def["full_name"]),
            is_active=True,
            created_by=SYSTEM_ACTOR,
        )
        session.add(user)
        logger.info("Seeded user %s", user_def["email"])

    await session.flush()

    # Seed RBAC roles and permissions
    existing_result = await session.execute(select(RBACRole))
    existing_roles: dict[str, UUID] = {
        r.name: r.id for r in existing_result.scalars().all()
    }
    role_map: dict[str, UUID] = {}

    for role_name, role_def in rbac_roles.items():
        if role_name in existing_roles:
            role_map[role_name] = existing_roles[role_name]
        else:
            role_id = uuid4()
            session.add(
                RBACRole(
                    id=role_id,
                    name=role_name,
                    description=str(role_def["description"]),
                    is_system=True,
                )
            )
            role_map[role_name] = role_id
            logger.info("Seeded role %s", role_name)

    await session.flush()

    # Seed permissions for each role
    for role_name, role_def in rbac_roles.items():
        role_id = role_map[role_name]
        result = await session.execute(
            select(RBACRolePermission.permission).where(
                RBACRolePermission.role_id == role_id
            )
        )
        existing_perms: set[str] = {row[0] for row in result.all()}

        permissions = role_def["permissions"]
        assert isinstance(permissions, list)
        new_perms = set(permissions) - existing_perms
        for perm in sorted(new_perms):
            session.add(
                RBACRolePermission(
                    id=uuid4(),
                    role_id=role_id,
                    permission=perm,
                )
            )
        if new_perms:
            logger.info("Seeded %d permissions for role %s", len(new_perms), role_name)

    await session.flush()

    # Seed role assignments
    # Build email -> user_id mapping
    email_to_user_id: dict[str, UUID] = {
        u["email"]: UUID(u["user_id"]) for u in users_data
    }

    existing_assignments = await session.execute(select(UserRoleAssignment))
    existing: set[tuple[str, str]] = {
        (str(a.user_id), str(a.role_id)) for a in existing_assignments.scalars().all()
    }

    for email, role_name in role_assignments.items():
        user_id = email_to_user_id[email]
        role_id = role_map[role_name]
        key = (str(user_id), str(role_id))
        if key in existing:
            continue
        assignment = UserRoleAssignment(
            id=uuid4(),
            user_id=user_id,
            role_id=role_id,
            scope_type=ScopeType.GLOBAL.value,
            scope_id=None,
            granted_by=SYSTEM_ACTOR,
        )
        session.add(assignment)
        logger.info("Seeded role assignment: %s -> %s", email, role_name)

    await session.flush()


async def _seed_users(
    session: AsyncSession,
    get_password_hash: Callable[[str], str],
) -> None:
    """Create default users if they do not exist."""
    from app.models.domain.user import User

    for user_def in DEFAULT_USERS:
        stmt = select(User).where(User.user_id == user_def["user_id"])
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            continue

        user = User(
            id=user_def["user_id"],
            user_id=user_def["user_id"],
            email=str(user_def["email"]),
            hashed_password=get_password_hash(str(user_def["password"])),
            full_name=str(user_def["full_name"]),
            is_active=True,
            created_by=SYSTEM_ACTOR,
        )
        session.add(user)
        logger.info("Seeded user %s", user_def["email"])

    await session.flush()


async def _seed_rbac_roles(session: AsyncSession) -> dict[str, UUID]:
    """Create RBAC roles and permissions. Returns {role_name: role_id}."""
    from app.models.domain.rbac import RBACRole, RBACRolePermission

    role_map: dict[str, UUID] = {}

    # Load existing roles to avoid duplicates
    result = await session.execute(select(RBACRole))
    existing_roles: dict[str, UUID] = {r.name: r.id for r in result.scalars().all()}

    for role_name, role_def in ROLE_PERMISSIONS.items():
        if role_name in existing_roles:
            role_map[role_name] = existing_roles[role_name]
        else:
            role_id = uuid4()
            session.add(
                RBACRole(
                    id=role_id,
                    name=role_name,
                    description=str(role_def["description"]),
                    is_system=True,
                )
            )
            role_map[role_name] = role_id
            logger.info("Seeded role %s", role_name)

    await session.flush()

    # Seed permissions for each role
    for role_name, role_def in ROLE_PERMISSIONS.items():
        role_id = role_map[role_name]

        # Get existing permissions for this role
        result = await session.execute(
            select(RBACRolePermission.permission).where(
                RBACRolePermission.role_id == role_id
            )
        )
        existing_perms: set[str] = {row[0] for row in result.all()}

        permissions = role_def["permissions"]
        assert isinstance(permissions, list)
        new_perms = set(permissions) - existing_perms
        for perm in sorted(new_perms):
            session.add(
                RBACRolePermission(
                    id=uuid4(),
                    role_id=role_id,
                    permission=perm,
                )
            )

        if new_perms:
            logger.info("Seeded %d permissions for role %s", len(new_perms), role_name)

    await session.flush()
    return role_map


async def _seed_role_assignments(
    session: AsyncSession,
    role_map: dict[str, UUID],
) -> None:
    """Assign global roles to default users."""
    from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment

    # Load existing assignments
    result = await session.execute(select(UserRoleAssignment))
    existing: set[tuple[str, str]] = {
        (str(a.user_id), str(a.role_id)) for a in result.scalars().all()
    }

    for user_def in DEFAULT_USERS:
        role_name = USER_ROLE_MAP[str(user_def["email"])]
        role_id = role_map[role_name]
        key = (str(user_def["user_id"]), str(role_id))

        if key in existing:
            continue

        assignment = UserRoleAssignment(
            id=uuid4(),
            user_id=user_def["user_id"],
            role_id=role_id,
            scope_type=ScopeType.GLOBAL.value,
            scope_id=None,
            granted_by=SYSTEM_ACTOR,
        )
        session.add(assignment)
        logger.info("Seeded role assignment: %s -> %s", user_def["email"], role_name)

    await session.flush()
