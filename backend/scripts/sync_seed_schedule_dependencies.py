#!/usr/bin/env python3
# ruff: noqa: E402
"""Non-destructive sync of seed Schedule Dependencies.

Ensures the schedule dependencies defined in ``seed_projects.json`` exist on
branch ``main`` for the seeded project, so the Gantt chart renders dependency
links in dev data without requiring a full reseed.

For each seed dependency:
  1. Resolve ``predecessor_id`` / ``successor_id`` / ``project_id`` from the
     seed entry (stable seed UUIDs that already exist as Work Packages with
     linked Schedule Baselines).
  2. Create the dependency via ``ScheduleDependencyService.create`` — the
     canonical validated path (self-reference, schedule existence, duplicate,
     and cycle checks). The service's ``_validate_no_duplicate`` is the
     idempotency mechanism: it raises ``DuplicateDependencyError`` if an
     identical ``(predecessor, successor, type, branch)`` link already exists,
     which we treat as a skip.

This is non-destructive and idempotent: running it repeatedly only inserts
missing seed dependencies and never touches anything else (no truncation, no
deletes, no updates to existing rows). It is the targeted alternative to a
full reseed (which would wipe all project data).

Run with: cd backend && uv run python scripts/sync_seed_schedule_dependencies.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

# Allow importing app.* when run as a plain script.
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import async_session_maker, engine
from app.models.schemas.schedule_dependency import ScheduleDependencyCreate
from app.services.schedule_dependency_service import (
    DuplicateDependencyError,
    ScheduleDependencyService,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

SEED_FILE = backend_dir / "seed" / "seed_projects.json"

# Seeded admin user (matches the seeded ``created_by`` of the project WPs).
SEED_ACTOR_ID = UUID("00000000-0000-0000-0000-000000000001")


def _load_seed() -> dict[str, Any]:
    """Read the projects seed file."""
    with open(SEED_FILE) as f:
        return json.load(f)


async def sync_seed_schedule_dependencies(session: Any) -> dict[str, Any]:
    """Sync seed schedule dependencies and return a summary.

    The summary has keys: ``total``, ``created``, ``skipped_existing``.
    """
    data = _load_seed()
    dep_entries = data.get("schedule_dependencies", [])

    summary: dict[str, Any] = {
        "total": len(dep_entries),
        "created": 0,
        "skipped_existing": 0,
    }

    service = ScheduleDependencyService(session)

    for entry in dep_entries:
        create_schema = ScheduleDependencyCreate(
            predecessor_id=UUID(entry["predecessor_id"]),
            successor_id=UUID(entry["successor_id"]),
            dependency_type=entry.get("dependency_type", "FS"),
            lag_days=entry.get("lag_days", 0),
            project_id=UUID(entry["project_id"]),
            branch=entry.get("branch", "main"),
        )

        try:
            await service.create(create_schema, actor_id=SEED_ACTOR_ID)
        except DuplicateDependencyError:
            # Idempotency: an identical (predecessor, successor, type, branch)
            # link already exists — this is the expected re-run path.
            summary["skipped_existing"] += 1
            logger.info(
                "[skip] dependency %s -> %s (%s) already exists on '%s'",
                create_schema.predecessor_id,
                create_schema.successor_id,
                create_schema.dependency_type,
                create_schema.branch,
            )
            continue

        summary["created"] += 1
        logger.info(
            "[create] dependency %s -> %s (%s, lag=%d)",
            create_schema.predecessor_id,
            create_schema.successor_id,
            create_schema.dependency_type,
            create_schema.lag_days,
        )

    return summary


async def main() -> None:
    data = _load_seed()
    dep_entries = data.get("schedule_dependencies", [])
    print(f"=== seed Schedule Dependency sync ({len(dep_entries)} dependencies) ===\n")
    async with async_session_maker() as session:
        try:
            summary = await sync_seed_schedule_dependencies(session)
            await session.commit()
            print("\n=== committed ===")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    print("\n=== summary ===")
    print(f"  dependencies scanned   : {summary['total']}")
    print(f"  dependencies created   : {summary['created']}")
    print(f"  already existing (skip): {summary['skipped_existing']}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
