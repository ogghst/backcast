#!/usr/bin/env python3
"""Non-destructive sync of specialist configs from the seed into the live DB.

Applies one or more specialists from ``seed_system_config.json`` without
touching any other data:

  A. Insert each specialist row (idempotent by name); if it already exists,
     reconcile the synced fields (description, presentation_prompt,
     system_prompt, allowed_tools) with the seed.
  B. Append each specialist to ``delegation_config.allowed_specialists`` of
     the main assistants whose seed config lists it (idempotent, append-only).
  C. After committing, invalidate the ``db_loader`` in-process cache so the
     new roster is visible immediately (the default TTL is 5 minutes) and
     re-read the roster from the DB to assert the expected specialists are
     present and active.

The set of specialists to sync is derived from the seed's
``ai_specialist_configs`` keys — there is no hardcoded allowlist, so adding a
specialist to the seed is enough; it will not be silently skipped.

This avoids a full reseed (which would wipe all project data). Existing
``allowed_specialists`` entries are preserved — a specialist name is only
appended when missing, so other pre-existing delegation entries (the live DB
can lag the seed) are left untouched.

Graph-compile cache caveat
--------------------------
``invalidate_cache()`` only clears the ``db_loader`` specialist-config cache
(process-local). Compiled LangGraph subagent graphs are built lazily on the
next request and may hold a stale snapshot for the lifetime of the running
process. A **process restart** is the only guaranteed flush of the
graph-compile layer; mid-process, the next graph build picks up the new DB
state. Mid-session sync also orphans in-flight executions — coordinate with
active chat sessions before running.

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

from app.ai.subagents.db_loader import invalidate_cache  # noqa: E402
from app.db.session import async_session_maker, engine  # noqa: E402
from app.models.domain.ai import AIAssistantConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

SEED_FILE = backend_dir / "seed" / "seed_system_config.json"

# Fields kept in sync with the seed (the source of truth per specialist).
# allowed_tools is the one that changes as new tools are added.
_SYNCED_FIELDS = (
    "description",
    "presentation_prompt",
    "system_prompt",
    "allowed_tools",
)


def _load_seed() -> dict[str, Any]:
    """Read the full seed file."""
    with open(SEED_FILE) as f:
        return json.load(f)


def _seed_specialist_names() -> list[str]:
    """Specialist names declared in the seed (the source of truth).

    Replaces the former hardcoded allowlist so adding a specialist to the seed
    is enough — it can no longer be silently skipped by an out-of-date tuple.
    """
    data = _load_seed()
    return [s["name"] for s in data.get("ai_specialist_configs", []) if s.get("name")]


def _load_specialist_seed(name: str) -> dict[str, Any]:
    """Read a single specialist config from the seed file."""
    data = _load_seed()
    for spec in data.get("ai_specialist_configs", []):
        if spec.get("name") == name:
            return spec
    raise RuntimeError(f"{name} not found in {SEED_FILE}.")


def _assistants_listing_specialist(name: str) -> set[str]:
    """Names of main assistants whose seed allowed_specialists lists ``name``."""
    data = _load_seed()
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


async def assert_roster(session: Any, expected_names: list[str]) -> None:
    """Post-sync assertion: re-read specialists from DB and verify presence.

    Confirms every seed-declared specialist exists in the live DB and is
    active. Raises ``RuntimeError`` if any are missing or inactive so a
    partial/failed sync is never reported as success.
    """
    result = await session.execute(
        select(AIAssistantConfig.name, AIAssistantConfig.is_active).where(
            AIAssistantConfig.agent_type == "specialist"
        )
    )
    rows = dict(result.all())

    missing = [n for n in expected_names if n not in rows]
    inactive = [n for n in expected_names if n in rows and not rows[n]]
    if missing or inactive:
        raise RuntimeError(
            f"post-sync assertion failed: missing={missing} inactive={inactive}"
        )
    logger.info(
        "[C] roster assertion passed: %d specialists present & active", len(rows)
    )


async def main() -> None:
    specialist_names = _seed_specialist_names()
    print(f"=== specialist DB sync ({len(specialist_names)} from seed) ===\n")
    print(f"  seed specialists: {specialist_names}\n")
    async with async_session_maker() as session:
        try:
            for name in specialist_names:
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

            await assert_roster(session, specialist_names)
            print("=== post-sync roster assertion passed ===\n")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Clear the db_loader specialist-config cache (process-local, 5-min TTL)
    # so the new roster is visible immediately to the next graph build.
    invalidate_cache()
    print("=== db_loader cache invalidated ===")
    print(
        "NOTE: compiled graphs may hold a stale snapshot until process restart "
        "(see module docstring)."
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
