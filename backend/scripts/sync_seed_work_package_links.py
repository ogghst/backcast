#!/usr/bin/env python3
"""Non-destructive sync of seed Work Package schedule-baseline/forecast links.

Ensures the seed Work Packages (those defined in ``seed_projects.json``) are
linked to their seed ScheduleBaseline and Forecast rows on branch ``main``:

  A. For each seed Work Package, ensure the referenced ScheduleBaseline
     exists (current version on ``main``); create it from the matching
     ``schedule_baselines`` seed entry if missing.
  B. For each seed Work Package, ensure the referenced Forecast exists
     (current version on ``main``); create it from the matching ``forecasts``
     seed entry if missing.
  C. Load the Work Package's current version on ``main``; if its
     ``schedule_baseline_id`` / ``forecast_id`` differ from the seed values,
     run an ``UpdateCommand`` to create a new WP version with both links set
     to the seed values. If both already match, skip.

This is non-destructive and idempotent: it only touches the seed Work
Packages and the seed baseline/forecast rows they reference. All other data
(branches, change orders, cost registrations, ~470 other test WPs, etc.) is
left untouched. It is the targeted alternative to a full reseed (which would
wipe all project data).

Run with: cd backend && uv run python scripts/sync_seed_work_package_links.py
"""

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

# Allow importing app.* when run as a plain script.
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.branching.commands import UpdateCommand  # noqa: E402
from app.db.session import async_session_maker, engine  # noqa: E402
from app.models.domain.work_package import WorkPackage  # noqa: E402
from app.services.forecast_service import ForecastService  # noqa: E402
from app.services.schedule_baseline_service import ScheduleBaselineService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

SEED_FILE = backend_dir / "seed" / "seed_projects.json"


def _load_seed() -> dict[str, Any]:
    """Read the projects seed file."""
    with open(SEED_FILE) as f:
        return json.load(f)


def _index_by_root(
    items: list[dict[str, Any]], root_key: str
) -> dict[str, dict[str, Any]]:
    """Index a list of seed entries by their root-id key."""
    return {item[root_key]: item for item in items if item.get(root_key)}


def _parse_datetime(value: Any) -> datetime:
    """Parse an ISO datetime string from the seed into a datetime."""
    return datetime.fromisoformat(value)


def _seed_actor_id(wp_entry: dict[str, Any]) -> UUID:
    """Resolve the actor_id (created_by) for a seed WP entry."""
    return UUID(wp_entry["created_by"])


async def _current_wp(session: Any, work_package_id: UUID) -> WorkPackage | None:
    """Get the current (open valid_time, non-deleted) WP version on main."""
    from typing import cast

    stmt = (
        select(WorkPackage)
        .where(
            WorkPackage.work_package_id == work_package_id,
            WorkPackage.branch == "main",
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        .order_by(WorkPackage.valid_time.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _ensure_schedule_baseline(
    session: Any,
    schedule_baseline_id: UUID,
    sb_seed: dict[str, Any],
    actor_id: UUID,
) -> bool:
    """Ensure the referenced ScheduleBaseline exists on main; create if missing.

    Returns True if a new baseline was created, False if it already existed.
    """
    service = ScheduleBaselineService(session)
    existing = await service.get_by_id(schedule_baseline_id, branch="main")
    if existing is not None:
        return False

    await service.create_root(
        root_id=schedule_baseline_id,
        actor_id=actor_id,
        branch="main",
        name=sb_seed["name"],
        start_date=_parse_datetime(sb_seed["start_date"]),
        end_date=_parse_datetime(sb_seed["end_date"]),
        progression_type=sb_seed["progression_type"],
        description=sb_seed.get("description"),
    )
    return True


async def _ensure_forecast(
    session: Any,
    forecast_id: UUID,
    fc_seed: dict[str, Any],
    actor_id: UUID,
) -> bool:
    """Ensure the referenced Forecast exists on main; create if missing.

    Returns True if a new forecast was created, False if it already existed.
    """
    service = ForecastService(session)
    existing = await service.get_by_id(forecast_id, branch="main")
    if existing is not None:
        return False

    await service.create_root(
        root_id=forecast_id,
        actor_id=actor_id,
        branch="main",
        eac_amount=Decimal(str(fc_seed["eac_amount"])),
        basis_of_estimate=fc_seed.get("basis_of_estimate"),
    )
    return True


async def _link_work_package(
    session: Any,
    work_package_id: UUID,
    schedule_baseline_id: UUID | None,
    forecast_id: UUID | None,
    actor_id: UUID,
) -> bool:
    """Set both link columns on the WP's current version if they diverge.

    Returns True if a new WP version was created to carry the links,
    False if the current version already matched the seed values.
    """
    current = await _current_wp(session, work_package_id)
    if current is None:
        logger.warning(
            "Work Package %s has no current version on main; skipping link",
            work_package_id,
        )
        return False

    if (
        current.schedule_baseline_id == schedule_baseline_id
        and current.forecast_id == forecast_id
    ):
        return False

    cmd = UpdateCommand(
        entity_class=WorkPackage,
        root_id=work_package_id,
        actor_id=actor_id,
        branch="main",
        control_date=datetime.now(UTC),
        updates={
            "schedule_baseline_id": schedule_baseline_id,
            "forecast_id": forecast_id,
        },
    )
    await cmd.execute(session)
    return True


async def sync_seed_work_package_links(session: Any) -> dict[str, Any]:
    """Run the non-destructive sync and return a summary.

    The summary has keys: ``work_packages``, ``baselines_created``,
    ``forecasts_created``, ``links_updated``, ``skipped``.
    """
    data = _load_seed()
    wp_entries = data.get("work_packages", [])
    sb_index = _index_by_root(
        data.get("schedule_baselines", []), "schedule_baseline_id"
    )
    fc_index = _index_by_root(data.get("forecasts", []), "forecast_id")

    summary: dict[str, Any] = {
        "work_packages": len(wp_entries),
        "baselines_created": 0,
        "forecasts_created": 0,
        "links_updated": 0,
        "skipped": 0,
    }

    for wp_entry in wp_entries:
        wp_id = UUID(wp_entry["work_package_id"])
        actor_id = _seed_actor_id(wp_entry)
        seed_sb = wp_entry.get("schedule_baseline_id")
        seed_fc = wp_entry.get("forecast_id")
        sb_id = UUID(seed_sb) if seed_sb else None
        fc_id = UUID(seed_fc) if seed_fc else None

        # A. Ensure schedule baseline exists.
        if sb_id is not None:
            sb_seed = sb_index.get(str(sb_id))
            if sb_seed is None:
                logger.warning(
                    "Work Package %s references baseline %s not found in seed; "
                    "cannot create",
                    wp_id,
                    sb_id,
                )
            else:
                created = await _ensure_schedule_baseline(
                    session, sb_id, sb_seed, actor_id
                )
                if created:
                    summary["baselines_created"] += 1
                    logger.info("[A] created schedule baseline %s", sb_id)
                else:
                    logger.info("[A] schedule baseline %s exists", sb_id)

        # B. Ensure forecast exists.
        if fc_id is not None:
            fc_seed = fc_index.get(str(fc_id))
            if fc_seed is None:
                logger.warning(
                    "Work Package %s references forecast %s not found in seed; "
                    "cannot create",
                    wp_id,
                    fc_id,
                )
            else:
                created = await _ensure_forecast(session, fc_id, fc_seed, actor_id)
                if created:
                    summary["forecasts_created"] += 1
                    logger.info("[B] created forecast %s", fc_id)
                else:
                    logger.info("[B] forecast %s exists", fc_id)

        # C. Link the WP if needed.
        linked = await _link_work_package(session, wp_id, sb_id, fc_id, actor_id)
        if linked:
            summary["links_updated"] += 1
            logger.info(
                "[C] linked Work Package %s -> baseline=%s forecast=%s",
                wp_id,
                sb_id,
                fc_id,
            )
        else:
            summary["skipped"] += 1
            logger.info(
                "[C] Work Package %s already linked (baseline=%s forecast=%s)",
                wp_id,
                sb_id,
                fc_id,
            )

    return summary


async def main() -> None:
    data = _load_seed()
    wp_entries = data.get("work_packages", [])
    print(f"=== seed Work Package link sync ({len(wp_entries)} work packages) ===\n")
    async with async_session_maker() as session:
        try:
            summary = await sync_seed_work_package_links(session)
            await session.commit()
            print("\n=== committed ===")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    print("\n=== summary ===")
    print(f"  work packages scanned : {summary['work_packages']}")
    print(f"  schedule baselines created : {summary['baselines_created']}")
    print(f"  forecasts created          : {summary['forecasts_created']}")
    print(f"  work packages linked       : {summary['links_updated']}")
    print(f"  work packages already linked: {summary['skipped']}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
