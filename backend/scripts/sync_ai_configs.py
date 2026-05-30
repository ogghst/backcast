#!/usr/bin/env python3
"""Sync AI configs (assistants, specialists, RBAC) from seed files into the database.

Run with: cd backend && uv run python scripts/sync_ai_configs.py
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add the backend directory to sys.path to allow importing app
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.db.session import async_session_maker, engine  # noqa: E402

logger = logging.getLogger(__name__)

SEED_DIR = backend_dir / "seed"
SPECIALIST_SEED = SEED_DIR / "ai_specialist_configs.json"
ASSISTANT_SEED = SEED_DIR / "ai_assistant_configs.json"

# Track all changes for summary
changes: list[str] = []


def _load_json(path: Path) -> list[dict[str, Any]]:
    with open(path) as f:
        return json.load(f)


async def sync_forecast_manager(session: AsyncSession) -> None:
    """A) Deactivate forecast_manager specialist."""
    from app.models.domain.ai import AIAssistantConfig

    stmt = select(AIAssistantConfig).where(
        AIAssistantConfig.name == "forecast_manager",
        AIAssistantConfig.is_system.is_(True),
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config and config.is_active:
        config.is_active = False
        changes.append("Deactivated forecast_manager specialist")
        print("  [A] Deactivated forecast_manager")
    else:
        print("  [A] forecast_manager already inactive or not found (skip)")


async def sync_project_manager(session: AsyncSession) -> None:
    """B) Update project_manager specialist tools and prompt."""
    from app.models.domain.ai import AIAssistantConfig

    seed_data = _load_json(SPECIALIST_SEED)
    pm_seed = next((s for s in seed_data if s["name"] == "project_manager"), None)
    if not pm_seed:
        print("  [B] project_manager not found in seed file (skip)")
        return

    stmt = select(AIAssistantConfig).where(
        AIAssistantConfig.name == "project_manager",
        AIAssistantConfig.is_system.is_(True),
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        print("  [B] project_manager not found in DB (skip)")
        return

    updated = False
    if config.allowed_tools != pm_seed["allowed_tools"]:
        config.allowed_tools = pm_seed["allowed_tools"]
        changes.append("Updated project_manager allowed_tools")
        updated = True

    if config.system_prompt != pm_seed["system_prompt"]:
        config.system_prompt = pm_seed["system_prompt"]
        changes.append("Updated project_manager system_prompt")
        updated = True

    if updated:
        print("  [B] Updated project_manager tools + prompt")
    else:
        print("  [B] project_manager already in sync (skip)")


async def create_accountant(session: AsyncSession) -> None:
    """C) Create accountant specialist if not exists."""
    from app.models.domain.ai import AIAssistantConfig

    stmt = select(AIAssistantConfig).where(
        AIAssistantConfig.name == "accountant",
        AIAssistantConfig.is_system.is_(True),
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        print("  [C] accountant already exists (skip)")
        return

    seed_data = _load_json(SPECIALIST_SEED)
    acct_seed = next((s for s in seed_data if s["name"] == "accountant"), None)
    if not acct_seed:
        print("  [C] accountant not found in seed file (skip)")
        return

    config = AIAssistantConfig(
        id=uuid4(),
        name=acct_seed["name"],
        description=acct_seed["description"],
        model_id=acct_seed["model_id"],
        system_prompt=acct_seed["system_prompt"],
        temperature=acct_seed.get("temperature"),
        max_tokens=acct_seed.get("max_tokens"),
        is_active=acct_seed["is_active"],
        default_role=acct_seed["default_role"],
        agent_type=acct_seed["agent_type"],
        is_system=acct_seed["is_system"],
        allowed_tools=acct_seed["allowed_tools"],
        structured_output_schema=acct_seed.get("structured_output_schema"),
    )
    session.add(config)
    changes.append("Created accountant specialist")
    print("  [C] Created accountant specialist")


async def sync_main_assistants(session: AsyncSession) -> None:
    """D) Update main assistants' delegation_config."""
    from app.models.domain.ai import AIAssistantConfig

    seed_data = _load_json(ASSISTANT_SEED)
    main_ids = {
        "77777777-7777-7777-7777-777777777777",
        "88888888-8888-8888-8888-888888888888",
        "99999999-9999-9999-9999-999999999999",
    }

    for seed in seed_data:
        seed_id = seed["id"]
        if seed_id not in main_ids:
            continue

        stmt = select(AIAssistantConfig).where(AIAssistantConfig.id == seed_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()
        if not config:
            print(f"  [D] Assistant {seed['name']} ({seed_id}) not found in DB (skip)")
            continue

        if config.delegation_config != seed["delegation_config"]:
            config.delegation_config = seed["delegation_config"]
            changes.append(f"Updated delegation_config for {seed['name']}")
            print(f"  [D] Updated delegation_config for {seed['name']}")
        else:
            print(f"  [D] {seed['name']} delegation_config already in sync (skip)")


async def sync_ai_admin_role(session: AsyncSession) -> None:
    """E) Create ai-admin RBAC role if not exists, sync permissions."""
    from app.db.seed_users_rbac import ROLE_PERMISSIONS
    from app.models.domain.rbac import RBACRole, RBACRolePermission

    role_name = "ai-admin"
    role_def = ROLE_PERMISSIONS[role_name]
    expected_perms = set(role_def["permissions"])

    stmt = select(RBACRole).where(RBACRole.name == role_name)
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        role = RBACRole(
            id=uuid4(),
            name=role_name,
            description=str(role_def["description"]),
            is_system=True,
        )
        session.add(role)
        await session.flush()
        changes.append(f"Created RBAC role: {role_name}")
        print(f"  [E] Created RBAC role: {role_name}")
    else:
        print(f"  [E] RBAC role {role_name} already exists")

    # Sync permissions
    result = await session.execute(
        select(RBACRolePermission.permission).where(
            RBACRolePermission.role_id == role.id
        )
    )
    existing_perms = {row[0] for row in result.all()}
    missing = expected_perms - existing_perms

    for perm in sorted(missing):
        session.add(
            RBACRolePermission(id=uuid4(), role_id=role.id, permission=perm)
        )

    if missing:
        changes.append(
            f"Added {len(missing)} permissions to {role_name}: {sorted(missing)}"
        )
        print(f"  [E] Added {len(missing)} missing permissions to {role_name}")
    else:
        print(f"  [E] {role_name} permissions already in sync")


async def sync_ai_viewer_permissions(session: AsyncSession) -> None:
    """F) Sync ai-viewer permissions (add project-documents-read if missing)."""
    from app.db.seed_users_rbac import ROLE_PERMISSIONS
    from app.models.domain.rbac import RBACRole, RBACRolePermission

    role_name = "ai-viewer"
    role_def = ROLE_PERMISSIONS[role_name]
    expected_perms = set(role_def["permissions"])

    stmt = select(RBACRole).where(RBACRole.name == role_name)
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        print(f"  [F] Role {role_name} not found (skip)")
        return

    result = await session.execute(
        select(RBACRolePermission.permission).where(
            RBACRolePermission.role_id == role.id
        )
    )
    existing_perms = {row[0] for row in result.all()}
    missing = expected_perms - existing_perms

    for perm in sorted(missing):
        session.add(
            RBACRolePermission(id=uuid4(), role_id=role.id, permission=perm)
        )

    if missing:
        changes.append(
            f"Added {len(missing)} permissions to {role_name}: {sorted(missing)}"
        )
        print(f"  [F] Added {len(missing)} missing permissions to {role_name}")
    else:
        print(f"  [F] {role_name} permissions already in sync")


async def sync_ai_manager_permissions(session: AsyncSession) -> None:
    """G) Sync ai-manager permissions."""
    from app.db.seed_users_rbac import ROLE_PERMISSIONS
    from app.models.domain.rbac import RBACRole, RBACRolePermission

    role_name = "ai-manager"
    role_def = ROLE_PERMISSIONS[role_name]
    expected_perms = set(role_def["permissions"])

    stmt = select(RBACRole).where(RBACRole.name == role_name)
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        print(f"  [G] Role {role_name} not found (skip)")
        return

    result = await session.execute(
        select(RBACRolePermission.permission).where(
            RBACRolePermission.role_id == role.id
        )
    )
    existing_perms = {row[0] for row in result.all()}
    missing = expected_perms - existing_perms

    for perm in sorted(missing):
        session.add(
            RBACRolePermission(id=uuid4(), role_id=role.id, permission=perm)
        )

    if missing:
        changes.append(
            f"Added {len(missing)} permissions to {role_name}: {sorted(missing)}"
        )
        print(f"  [G] Added {len(missing)} missing permissions to {role_name}")
    else:
        print(f"  [G] {role_name} permissions already in sync")


async def fix_user_admin_tools(session: AsyncSession) -> None:
    """H) Fix user_admin specialist stale tool names."""
    from app.models.domain.ai import AIAssistantConfig

    replacements = {
        "find_departments": "find_organizational_units",
        "create_department": "create_organizational_unit",
        "update_department": "update_organizational_unit",
        "delete_department": "delete_organizational_unit",
    }

    stmt = select(AIAssistantConfig).where(
        AIAssistantConfig.name == "user_admin",
        AIAssistantConfig.is_system.is_(True),
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if not config or not config.allowed_tools:
        print("  [H] user_admin not found or no tools (skip)")
        return

    tools = list(config.allowed_tools)
    updated_tools: list[str] = []
    has_changes = False
    for tool in tools:
        replacement = replacements.get(tool)
        if replacement:
            updated_tools.append(replacement)
            has_changes = True
        else:
            updated_tools.append(tool)

    if has_changes:
        config.allowed_tools = updated_tools
        changes.append("Fixed user_admin stale tool names (department -> organizational_unit)")
        print("  [H] Fixed user_admin stale tool names")
    else:
        print("  [H] user_admin tools already correct (skip)")


async def sync_evm_analyst_tools(session: AsyncSession) -> None:
    """I) Sync evm_analyst tools to match seed file."""
    from app.models.domain.ai import AIAssistantConfig

    seed_data = _load_json(SPECIALIST_SEED)
    evm_seed = next((s for s in seed_data if s["name"] == "evm_analyst"), None)
    if not evm_seed:
        print("  [I] evm_analyst not found in seed file (skip)")
        return

    stmt = select(AIAssistantConfig).where(
        AIAssistantConfig.name == "evm_analyst",
        AIAssistantConfig.is_system.is_(True),
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        print("  [I] evm_analyst not found in DB (skip)")
        return

    if config.allowed_tools != evm_seed["allowed_tools"]:
        config.allowed_tools = evm_seed["allowed_tools"]
        changes.append("Synced evm_analyst allowed_tools from seed")
        print("  [I] Synced evm_analyst allowed_tools from seed")
    else:
        print("  [I] evm_analyst tools already in sync (skip)")


async def main() -> None:
    print("=== AI Config Sync Script ===\n")

    async with async_session_maker() as session:
        try:
            print("[A] Deactivating forecast_manager...")
            await sync_forecast_manager(session)

            print("\n[B] Updating project_manager specialist...")
            await sync_project_manager(session)

            print("\n[C] Creating accountant specialist...")
            await create_accountant(session)

            print("\n[D] Updating main assistants delegation_config...")
            await sync_main_assistants(session)

            print("\n[E] Syncing ai-admin RBAC role...")
            await sync_ai_admin_role(session)

            print("\n[F] Syncing ai-viewer permissions...")
            await sync_ai_viewer_permissions(session)

            print("\n[G] Syncing ai-manager permissions...")
            await sync_ai_manager_permissions(session)

            print("\n[H] Fixing user_admin stale tools...")
            await fix_user_admin_tools(session)

            print("\n[I] Syncing evm_analyst tools...")
            await sync_evm_analyst_tools(session)

            await session.commit()
            print("\n=== All changes committed ===\n")

        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Print summary
    if changes:
        print("=== SUMMARY OF CHANGES ===")
        for i, change in enumerate(changes, 1):
            print(f"  {i}. {change}")
        print(f"\nTotal: {len(changes)} change(s)")
    else:
        print("No changes needed -- everything already in sync.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
