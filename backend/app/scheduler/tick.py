"""One scheduler poll cycle (runs in-process in the API server).

Claims due schedules from the DB, applies the skip-missed policy, then
**dispatches before advancing** so a transient failure is retried on the next
tick rather than silently dropping the fire. Dispatch calls
:func:`trigger_schedule_run` directly (same process — the run launches
fire-and-forget where the in-memory ExecutionLifecycle/event-bus live).

Flow (dispatch-then-advance):
1. Claim active due rows (``FOR UPDATE SKIP LOCKED``).
2. Deactivate rows whose cron became invalid (they can never fire).
3. STALE rows (older than the grace window — the scheduler was down) → advance
   to the next future cron fire WITHOUT dispatching (skip missed).
4. FRESH rows → captured but NOT advanced yet.
5. Commit (releases row locks).
6. Dispatch the fresh rows concurrently (bounded) via ``trigger_schedule_run``.
7. Advance ``next_run_at`` ONLY for rows whose dispatch was HANDLED. A failed
   dispatch (any unexpected error) leaves ``next_run_at`` in the past so the
   next tick retries it — until it ages past the grace window and is then
   treated as stale.

Skip-missed: a schedule fires only if its ``next_run_at`` is within the grace
window (``SCHEDULER_MISFIRE_GRACE_SECONDS``) of ``now``.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.models.schemas.ai_agent_schedule import compute_next_run
from app.services.agent_schedule_service import (
    ScheduleNotFoundError,
    ScheduleOverlapError,
    trigger_schedule_run,
)

logger = logging.getLogger(__name__)

# Bounded dispatch across one tick. Module-level so it persists across ticks
# (caps concurrent trigger_schedule_run calls process-wide).
_dispatch_semaphore = asyncio.Semaphore(settings.SCHEDULER_MAX_CONCURRENCY)


async def tick(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    """Run one scheduler poll cycle (see module docstring)."""
    now = datetime.now(UTC)
    grace = timedelta(seconds=settings.SCHEDULER_MISFIRE_GRACE_SECONDS)
    stale_cutoff = now - grace

    fresh_ids: list[UUID] = []

    async with sessionmaker() as session:
        # Claim all active due rows atomically with FOR UPDATE SKIP LOCKED.
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
                fresh_ids.append(row.id)

        await session.commit()

    if not fresh_ids:
        return

    # Dispatch fresh-due schedules concurrently (bounded). trigger_schedule_run
    # launches the run fire-and-forget and returns quickly; gather holds the
    # task refs.
    tasks = [asyncio.create_task(_dispatch(sid)) for sid in fresh_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Advance only rows whose dispatch was HANDLED (True). A failed dispatch
    # leaves next_run_at in the past → the next tick retries it.
    handled_ids = [
        sid for sid, result in zip(fresh_ids, results, strict=True) if result is True
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


async def _dispatch(schedule_id: UUID) -> bool:
    """Dispatch one schedule run, bounded by the semaphore.

    Returns ``True`` if the fire window is HANDLED (the caller should advance
    ``next_run_at``): a launch, or overlap/schedule-gone (window is covered).
    Returns ``False`` to RETRY on any other error.
    """
    try:
        async with _dispatch_semaphore:
            await trigger_schedule_run(schedule_id)
        logger.info("[scheduler] triggered schedule %s", schedule_id)
        return True
    except (ScheduleOverlapError, ScheduleNotFoundError):
        # overlap (a run is already active) or schedule deleted — the window is
        # covered; advance so we don't retry forever.
        logger.info("[scheduler] schedule %s overlap/gone — handled", schedule_id)
        return True
    except Exception:
        logger.exception(
            "[scheduler] unexpected error dispatching schedule %s", schedule_id
        )
        return False


def _aware_utc(dt: datetime | None) -> datetime:
    """Normalize a possibly-naive next_run_at to tz-aware UTC."""
    if dt is None:  # should not happen (claim query filters NULLs out)
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
