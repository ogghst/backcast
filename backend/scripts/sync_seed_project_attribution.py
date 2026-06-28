#!/usr/bin/env python3
"""Non-destructive backfill of seed project attribution columns.

Ensures the ~130 synthetic ``P-XXXXX`` seed projects (and any other
current-version project rows) carry portfolio attribution defaults so the
portfolio view has data to slice by:

  - ``organizational_unit_id`` <- GLOBAL root id
    (``00000000-0000-4000-8000-00000000fffd`` — a DISTINCT id reserved for the
    portfolio root, deliberately not colliding with the seed_projects.json
    Engineering unit at ...0001) when NULL.
  - ``project_manager_id`` <- ``created_by`` (best proxy for ownership) when
    NULL.
  - ``customer_id`` is left NULL (unknown for synthetic projects).

Only current-version rows on branch ``main`` (open ``valid_time``, non-deleted)
where the respective column is NULL are touched — already-attributed rows are
left alone, so the script is idempotent and safe to re-run. It does not touch
branches, change orders, cost registrations, or any other entity.

This mirrors the migration ``44d00c4e21f7`` backfill (which only ran once, at
upgrade time) and exists as a standalone operational tool for dev DBs that were
seeded after the migration or that gained new synthetic projects.

Run with: cd backend && uv run python scripts/sync_seed_project_attribution.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, text, update

# Allow importing app.* when run as a plain script.
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import async_session_maker, engine  # noqa: E402
from app.models.domain.project import Project  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

#: Root id of the GLOBAL organizational unit (mirrors the
#: ``44d00c4e21f7`` migration and ``app/db/seed_custom_templates.py``).
#: DISTINCT from the seed_projects.json Engineering unit (...0001).
GLOBAL_ORG_UNIT_ROOT_ID = "00000000-0000-4000-8000-00000000fffd"


async def _count_current_projects(session: Any) -> int:
    """Count current-version project rows on main (for the summary)."""
    stmt = (
        select(func.count())
        .select_from(Project)
        .where(
            Project.branch == "main",
            func.upper(cast(Any, Project).valid_time).is_(None),
            cast(Any, Project).deleted_at.is_(None),
        )
    )
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _backfill_column(
    session: Any, column_name: str, source_sql: str, global_value: str | None = None
) -> int:
    """Backfill a single nullable attribution column on current-version rows.

    Args:
        session: Async DB session.
        column_name: One of ``organizational_unit_id`` / ``project_manager_id``.
        source_sql: SQL expression for the value to set (e.g. ``created_by``),
            ignored when ``global_value`` is provided.
        global_value: When set, assigns this literal UUID (used for the GLOBAL
            org unit).

    Returns:
        Number of rows updated.
    """
    if global_value is not None:
        # global_value is a hard-coded constant UUID (GLOBAL_ORG_UNIT_ROOT_ID),
        # so f-string interpolation is safe (no untrusted input). It is cast
        # ::uuid inline because asyncpg binds UUID columns as text and the
        # target column is uuid-typed (operator uuid = varchar would otherwise
        # fail) — same justification as the 44d00c4e21f7 migration.
        set_expr = text(f"'{global_value}'::uuid")
    else:
        set_expr = text(source_sql)

    stmt = (
        update(Project)
        .where(
            Project.branch == "main",
            func.upper(cast(Any, Project).valid_time).is_(None),
            cast(Any, Project).deleted_at.is_(None),
            getattr(Project, column_name).is_(None),
        )
        .values(**{column_name: set_expr})
    )
    result = await session.execute(stmt)
    return int(result.rowcount or 0)


async def sync_seed_project_attribution(session: Any) -> dict[str, Any]:
    """Run the non-destructive attribution backfill and return a summary.

    Summary keys: ``current_projects``, ``org_unit_set``,
    ``project_manager_set``, ``customer_left_null``.
    """
    total = await _count_current_projects(session)
    org_set = await _backfill_column(
        session,
        "organizational_unit_id",
        source_sql="",
        global_value=GLOBAL_ORG_UNIT_ROOT_ID,
    )
    pm_set = await _backfill_column(
        session,
        "project_manager_id",
        source_sql="created_by",
    )

    return {
        "current_projects": total,
        "org_unit_set": org_set,
        "project_manager_set": pm_set,
        "customer_left_null": None,  # intentionally never touched
    }


async def main() -> None:
    """Entry point: run the backfill, commit, print a summary."""
    print("=== seed project attribution backfill ===\n")
    async with async_session_maker() as session:
        try:
            summary = await sync_seed_project_attribution(session)
            await session.commit()
            print("\n=== committed ===")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    print("\n=== summary ===")
    print(f"  current-version projects (main) : {summary['current_projects']}")
    print(
        f"  organizational_unit_id set      : {summary['org_unit_set']} "
        f"(-> GLOBAL {UUID(GLOBAL_ORG_UNIT_ROOT_ID)})"
    )
    print(
        f"  project_manager_id set          : {summary['project_manager_set']} "
        f"(-> created_by)"
    )
    print("  customer_id                     : left NULL (unknown for seed)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
