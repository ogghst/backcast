"""One scheduler poll cycle.

Claims due schedules from the shared DB, applies the skip-missed policy, then
**dispatches before advancing** so a transient backend failure is retried on
the next tick rather than silently dropping the fire.

Flow (dispatch-then-advance):
1. Claim all active due rows atomically (``FOR UPDATE SKIP LOCKED``).
2. Deactivate rows whose cron became invalid (they can never fire).
3. STALE rows (``next_run_at`` older than the grace window — the scheduler was
   down) are advanced to the next future cron fire WITHOUT dispatching.
4. FRESH rows are captured but NOT advanced yet.
5. Commit (releases row locks).
6. Dispatch the fresh rows concurrently (bounded) to the backend trigger API.
7. Advance ``next_run_at`` ONLY for rows whose dispatch was handled. A failed
   dispatch (backend unreachable / 5xx) leaves ``next_run_at`` in the past so
   the next tick retries it — until it ages past the grace window and is then
   treated as stale (advanced without firing).

Skip-missed: a schedule fires only if its ``next_run_at`` is within the grace
window (``SCHEDULER_MISFIRE_GRACE_SECONDS``) of ``now``.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.models.schemas.ai_agent_schedule import compute_next_run
from app.scheduler.api_client import trigger_schedule

logger = logging.getLogger(__name__)

# Bounded dispatch across one tick. Module-level so it persists across ticks
# (caps concurrent in-flight trigger POSTs process-wide).
_dispatch_semaphore = asyncio.Semaphore(settings.SCHEDULER_MAX_CONCURRENCY)

# Schedule IDs with a trigger POST currently in flight (this process). Cleared
# as each task completes.
_in_flight: set[str] = set()


async def tick(
    sessionmaker: async_sessionmaker[AsyncSession], client: httpx.AsyncClient
) -> None:
    """Run one scheduler poll cycle (see module docstring)."""
    now = datetime.now(UTC)
    grace = timedelta(seconds=settings.SCHEDULER_MISFIRE_GRACE_SECONDS)
    stale_cutoff = now - grace

    fresh_payloads: list[tuple[str, str]] = []  # (schedule_id, owner_user_id)

    async with sessionmaker() as session:
        # Claim all active due rows atomically with FOR UPDATE SKIP LOCKED so a
        # second scheduler instance (if ever run) can't double-claim.
        stmt = (
            select(AIAgentSchedule)
            .where(
                AIAgentSchedule.is_active.is_(True),
                AIAgentSchedule.next_run_at.is_not(None),
                AIAgentSchedule.next_run_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
        claimed = list((await session.execute(stmt)).scalars().all())

        for row in claimed:
            # Validate cron; an invalid expression deactivates the schedule (it
            # could never fire again) rather than retrying forever.
            try:
                compute_next_run(row.cron_expr, row.timezone)
            except Exception:
                logger.error(
                    "[scheduler] invalid cron '%s' on schedule %s; deactivating "
                    "(is_active=False, next_run_at=None)",
                    row.cron_expr,
                    row.id,
                )
                row.is_active = False
                row.next_run_at = None
                continue

            if _aware_utc(row.next_run_at) < stale_cutoff:
                # stale (scheduler was down longer than grace): advance to the
                # next future cron fire WITHOUT dispatching (skip missed).
                row.next_run_at = compute_next_run(row.cron_expr, row.timezone)
            else:
                # fresh: do NOT advance here — advance only after a successful
                # dispatch (below) so a transient failure is retried next tick.
                fresh_payloads.append((str(row.id), str(row.owner_user_id)))

        await session.commit()

    if not fresh_payloads:
        return

    # Dispatch fresh-due schedules concurrently (bounded). The trigger endpoint
    # is fire-and-forget, so POSTs return fast; gather holds the task refs.
    tasks = [
        asyncio.create_task(_dispatch(client, sid, oid)) for sid, oid in fresh_payloads
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Advance only rows whose dispatch was HANDLED (truthy). A failed dispatch
    # leaves next_run_at in the past → the next tick retries it.
    handled_ids = [
        sid
        for (sid, _oid), result in zip(fresh_payloads, results, strict=True)
        if not isinstance(result, Exception) and result
    ]
    if not handled_ids:
        return

    async with sessionmaker() as session:
        rows = (
            (
                await session.execute(
                    select(AIAgentSchedule).where(AIAgentSchedule.id.in_(handled_ids))
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            try:
                row.next_run_at = compute_next_run(row.cron_expr, row.timezone)
            except Exception:
                logger.error(
                    "[scheduler] invalid cron '%s' on schedule %s during advance; "
                    "deactivating",
                    row.cron_expr,
                    row.id,
                )
                row.is_active = False
                row.next_run_at = None
        await session.commit()


async def _dispatch(
    client: httpx.AsyncClient, schedule_id: str, owner_user_id: str
) -> bool:
    """Dispatch one trigger POST, bounded by the semaphore + in-flight set.

    Returns ``True`` if the fire window is HANDLED (the caller should advance
    ``next_run_at``), or ``False`` to retry on the next tick.
    """
    if schedule_id in _in_flight:
        logger.info(
            "[scheduler] schedule %s already in flight; skipping dispatch",
            schedule_id,
        )
        return True
    _in_flight.add(schedule_id)
    try:
        async with _dispatch_semaphore:
            return await trigger_schedule(
                client, UUID(schedule_id), UUID(owner_user_id)
            )
    except Exception:
        logger.exception(
            "[scheduler] unexpected error dispatching schedule %s", schedule_id
        )
        return False
    finally:
        _in_flight.discard(schedule_id)


def _aware_utc(dt: datetime | None) -> datetime:
    """Normalize a possibly-naive next_run_at to tz-aware UTC."""
    if dt is None:  # should not happen (claim query filters NULLs out)
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _clear_in_flight_for_tests() -> None:
    """Reset the module-level in-flight set between tests."""
    _in_flight.clear()
