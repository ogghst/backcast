#!/usr/bin/env python3
"""Non-destructive sync of specialist configs from the seed into the live DB.

Applies one or more specialists from ``seed_system_config.json`` without
touching any other data:

  A. Insert each specialist row (idempotent by name); if it already exists,
     reconcile the synced fields (description, presentation_prompt,
     system_prompt, allowed_tools) with the seed.
  B. Append each specialist to ``delegation_config.allowed_specialists`` of
     the main assistants whose seed config lists it (idempotent, append-only).

This avoids a full reseed (which would wipe all project data). Existing
``allowed_specialists`` entries are preserved — a specialist name is only
appended when missing, so other pre-existing delegation entries (the live DB
can lag the seed) are left untouched.

Run with: cd backend && uv run python scripts/sync_specialists.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

# Allow importing app.* when run as a plain script.
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import async_session_maker, engine  # noqa: E402
from app.models.domain.ai import AIAssistantConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

SEED_FILE = backend_dir / "seed" / "seed_system_config.json"

# Specialists this script keeps in sync with the seed. Add a name here (and to
# the seed's ai_specialist_configs) to sync a new specialist non-destructively.
SPECIALIST_NAMES: tuple[str, ...] = (
    "document_manager",
    "web_researcher",
)

# Fields kept in sync with the seed (the source of truth per specialist).
# allowed_tools is the one that changes as new tools are added.
_SYNCED_FIELDS = (
    "description",
    "presentation_prompt",
    "system_prompt",
    "allowed_tools",
)


def _load_specialist_seed(name: str) -> dict[str, Any]:
    """Read a single specialist config from the seed file."""
    with open(SEED_FILE) as f:
        data = json.load(f)
    for spec in data.get("ai_specialist_configs", []):
        if spec.get("name") == name:
            return spec
    raise RuntimeError(f"{name} not found in {SEED_FILE}.")


def _assistants_listing_specialist(name: str) -> set[str]:
    """Names of main assistants whose seed allowed_specialists lists ``name``."""
    with open(SEED_FILE) as f:
        data = json.load(f)
    names: set[str] = set()
    for assistant in data.get("ai_assistant_configs", []):
        allowed = (assistant.get("delegation_config") or {}).get("allowed_specialists")
        if allowed and name in allowed:
            names.add(assistant["name"])
    return names


async def upsert_specialist(session: Any, name: str) -> dict[str, Any]:
    """Insert a specialist from the seed, or reconcile it if it exists.

    Returns ``{"created": bool, "updated_fields": [...]}``.
    """
    seed_spec = _load_specialist_seed(name)

    result = await session.execute(
        select(AIAssistantConfig).where(
            AIAssistantConfig.name == name,
            AIAssistantConfig.agent_type == "specialist",
        )
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        session.add(AIAssistantConfig(**seed_spec))
        logger.info("[A] created specialist '%s'", name)
        return {"created": True, "updated_fields": []}

    updated_fields: list[str] = []
    for field in _SYNCED_FIELDS:
        seed_value = seed_spec.get(field)
        if getattr(existing, field) != seed_value:
            setattr(existing, field, seed_value)
            updated_fields.append(field)
    if updated_fields:
        logger.info("[A] updated specialist '%s' fields: %s", name, updated_fields)
    else:
        logger.info("[A] specialist '%s' already in sync", name)
    return {"created": False, "updated_fields": updated_fields}


async def wire_delegation(session: Any, name: str, target_assistants: set[str]) -> int:
    """Append ``name`` to allowed_specialists of the named assistants.

    Append-only and idempotent; never removes existing entries. Returns the
    number of assistants updated.
    """
    updated = 0
    for asst_name in sorted(target_assistants):
        result = await session.execute(
            select(AIAssistantConfig).where(
                AIAssistantConfig.name == asst_name,
                AIAssistantConfig.agent_type == "main",
            )
        )
        assistant = result.scalar_one_or_none()
        if assistant is None:
            logger.warning("[B] assistant '%s' not found in DB (skip)", asst_name)
            continue

        delegation = dict(assistant.delegation_config or {})
        allowed = list(delegation.get("allowed_specialists") or [])
        if name in allowed:
            logger.info("[B] '%s' already delegates to '%s' (skip)", asst_name, name)
            continue

        allowed.append(name)
        delegation["allowed_specialists"] = allowed
        assistant.delegation_config = delegation
        logger.info("[B] added '%s' to '%s' allowed_specialists", name, asst_name)
        updated += 1
    return updated


async def main() -> None:
    print("=== specialist DB sync ===\n")
    async with async_session_maker() as session:
        try:
            for name in SPECIALIST_NAMES:
                print(f"-- {name} --")
                upsert = await upsert_specialist(session, name)
                if upsert["created"]:
                    print(f"  [A] inserted specialist '{name}'")
                elif upsert["updated_fields"]:
                    print(
                        f"  [A] reconciled '{name}', updated fields: "
                        f"{upsert['updated_fields']}"
                    )
                else:
                    print(f"  [A] '{name}' already in sync")

                targets = _assistants_listing_specialist(name)
                print(f"  [B] target assistants from seed: {sorted(targets) or 'none'}")
                wired = await wire_delegation(session, name, targets)
                print(f"  [B] assistants updated: {wired}")
            await session.commit()
            print("\n=== committed ===")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
