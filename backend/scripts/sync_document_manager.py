#!/usr/bin/env python3
"""Non-destructive sync of the ``document_manager`` specialist into the live DB.

Applies the ``document_manager`` specialist (and its delegation wiring) from
``seed_system_config.json`` without touching any other data:

  A. Insert the ``document_manager`` specialist row (idempotent by name).
  B. Append ``document_manager`` to ``delegation_config.allowed_specialists``
     of the main assistants whose seed config lists it (ai-manager, ai-admin).

This avoids a full reseed (which would wipe all project data). Existing
``allowed_specialists`` entries are preserved — the specialist name is only
appended when missing.

Run with: cd backend && uv run python scripts/sync_document_manager.py
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
SPECIALIST_NAME = "document_manager"


def _load_document_manager_seed() -> dict[str, Any]:
    """Read the document_manager specialist config from the seed file."""
    with open(SEED_FILE) as f:
        data = json.load(f)
    for spec in data.get("ai_specialist_configs", []):
        if spec.get("name") == SPECIALIST_NAME:
            return spec
    raise RuntimeError(
        f"{SPECIALIST_NAME} not found in {SEED_FILE}. "
        "Add it to seed_system_config.json first."
    )


def _main_assistants_listing_document_manager(
    seed_doc_manager_specialist: dict[str, Any] | None,
) -> set[str]:
    """Names of main assistants in the seed whose allowed_specialists lists document_manager."""
    with open(SEED_FILE) as f:
        data = json.load(f)
    names: set[str] = set()
    for assistant in data.get("ai_assistant_configs", []):
        allowed = (assistant.get("delegation_config") or {}).get(
            "allowed_specialists"
        )
        if allowed and SPECIALIST_NAME in allowed:
            names.add(assistant["name"])
    return names


# Fields kept in sync with the seed (the source of truth for this specialist).
# allowed_tools is the one that changes as new document tools are added.
_SYNCED_FIELDS = (
    "description",
    "presentation_prompt",
    "system_prompt",
    "allowed_tools",
)


async def upsert_document_manager_specialist(session: Any) -> dict[str, Any]:
    """Insert the document_manager specialist, or reconcile it with the seed.

    On first run, inserts the specialist from the seed. On subsequent runs,
    updates the synced fields to match the seed so the live DB tracks seed
    edits without a full reseed (which would wipe all project data).

    Returns:
        ``{"created": bool, "updated_fields": [...]}``.
    """
    seed_spec = _load_document_manager_seed()

    result = await session.execute(
        select(AIAssistantConfig).where(
            AIAssistantConfig.name == SPECIALIST_NAME,
            AIAssistantConfig.agent_type == "specialist",
        )
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        session.add(AIAssistantConfig(**seed_spec))
        logger.info("[A] created specialist '%s'", SPECIALIST_NAME)
        return {"created": True, "updated_fields": []}

    updated_fields: list[str] = []
    for field in _SYNCED_FIELDS:
        seed_value = seed_spec.get(field)
        if getattr(existing, field) != seed_value:
            setattr(existing, field, seed_value)
            updated_fields.append(field)
    if updated_fields:
        logger.info(
            "[A] updated specialist '%s' fields: %s",
            SPECIALIST_NAME,
            updated_fields,
        )
    else:
        logger.info("[A] specialist '%s' already in sync", SPECIALIST_NAME)
    return {"created": False, "updated_fields": updated_fields}


async def wire_delegation(session: Any, target_assistant_names: set[str]) -> int:
    """Append document_manager to allowed_specialists of the named assistants.

    Only appends when missing; never removes existing entries. Returns the
    number of assistants updated.
    """
    updated = 0
    for name in sorted(target_assistant_names):
        result = await session.execute(
            select(AIAssistantConfig).where(
                AIAssistantConfig.name == name,
                AIAssistantConfig.agent_type == "main",
            )
        )
        assistant = result.scalar_one_or_none()
        if assistant is None:
            logger.warning("[B] assistant '%s' not found in DB (skip)", name)
            continue

        delegation = dict(assistant.delegation_config or {})
        allowed = list(delegation.get("allowed_specialists") or [])
        if SPECIALIST_NAME in allowed:
            logger.info(
                "[B] '%s' already delegates to '%s' (skip)", name, SPECIALIST_NAME
            )
            continue

        allowed.append(SPECIALIST_NAME)
        delegation["allowed_specialists"] = allowed
        assistant.delegation_config = delegation
        logger.info(
            "[B] added '%s' to '%s' allowed_specialists", SPECIALIST_NAME, name
        )
        updated += 1
    return updated


async def main() -> None:
    print("=== document_manager DB sync ===\n")
    async with async_session_maker() as session:
        try:
            upsert = await upsert_document_manager_specialist(session)
            targets = _main_assistants_listing_document_manager(None)
            if upsert["created"]:
                print(f"[A] specialist inserted: {SPECIALIST_NAME}")
            elif upsert["updated_fields"]:
                print(
                    f"[A] specialist reconciled, updated fields: "
                    f"{upsert['updated_fields']}"
                )
            else:
                print("[A] specialist already in sync")
            print(f"[B] target assistants from seed: {sorted(targets) or 'none'}")
            wired = await wire_delegation(session, targets)
            print(f"[B] assistants updated: {wired}")
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
