"""Tests for the scheduler tick (in-process).

Covers:
- skip-missed: a stale ``next_run_at`` (outside grace) is advanced without
  dispatch; a fresh one dispatches.
- ``next_run_at``-advance correctness: both fresh and stale rows get their
  ``next_run_at`` rewritten to a future cron fire.
- dispatch-then-advance: a dispatch that raises (unexpected error) is retried —
  next_run_at is NOT advanced.

No real agent run: ``trigger_schedule_run`` is monkeypatched to a spy. Uses the
running dev DB (same as the rest of the suite) to insert real schedule rows.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.domain.ai import AIAssistantConfig
from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.scheduler import tick as tick_module


async def _assistant_config_id() -> UUID:
    """Return an existing assistant config id from the seeded DB."""
    async with async_session_maker() as db:
        row = (
            await db.execute(select(AIAssistantConfig.id).limit(1))
        ).scalar_one_or_none()
    assert row is not None, "test DB must have at least one AIAssistantConfig"
    return UUID(str(row))


async def _create_schedule(next_run_at: datetime | None) -> UUID:
    """Insert a schedule with a pinned next_run_at and return its id."""
    config_id = await _assistant_config_id()
    async with async_session_maker() as db:
        sched = AIAgentSchedule(
            name="tick-test",
            prompt="hi",
            assistant_config_id=str(config_id),
            execution_mode="standard",
            cron_expr="*/5 * * * *",
            timezone="UTC",
            is_active=True,
            owner_user_id="e03556f3-4385-5d68-a685-af307fc8af5c",
            next_run_at=next_run_at,
        )
        db.add(sched)
        await db.commit()
        return UUID(str(sched.id))


async def _get_next_run_at(schedule_id: UUID) -> datetime:
    async with async_session_maker() as db:
        row = (
            await db.execute(
                select(AIAgentSchedule.next_run_at).where(
                    AIAgentSchedule.id == str(schedule_id)
                )
            )
        ).scalar_one()
    assert row is not None
    if row.tzinfo is None:
        return row.replace(tzinfo=UTC)
    return row.astimezone(UTC)


def _calls_for(spy: AsyncMock, schedule_id: UUID) -> list:
    """Return the spy's await calls whose schedule_id arg matches ours.

    Asserting on the per-schedule call count (rather than a global count) keeps
    these tests robust to any leftover due schedule from another test sharing
    the dev DB (trigger_schedule_run is called as ``(schedule_id,)``).
    """
    return [c for c in spy.await_args_list if str(c.args[0]) == str(schedule_id)]


@pytest.mark.asyncio
async def test_tick_fresh_due_schedule_dispatches_and_advances() -> None:
    """A schedule due within the grace window is dispatched and advanced."""
    now = datetime.now(UTC)
    # Due 10s ago — well inside the default 120s grace → fresh.
    sched_id = await _create_schedule(next_run_at=now - timedelta(seconds=10))

    spy = AsyncMock()
    try:
        with patch.object(tick_module, "trigger_schedule_run", spy):
            await tick_module.tick(async_session_maker)

        # OUR schedule dispatched exactly once (assert on our id, not a global
        # count, so a leftover due schedule can't flake this).
        my_calls = _calls_for(spy, sched_id)
        assert len(my_calls) == 1
        # next_run_at advanced to a future fire.
        new_next = await _get_next_run_at(sched_id)
        assert new_next > now
    finally:
        await _delete_schedule(sched_id)


@pytest.mark.asyncio
async def test_tick_stale_due_schedule_advances_without_dispatch() -> None:
    """A schedule due outside the grace window is advanced but NOT dispatched."""
    now = datetime.now(UTC)
    # Due well past the grace window → stale (scheduler-was-down case).
    stale_at = now - timedelta(seconds=settings.SCHEDULER_MISFIRE_GRACE_SECONDS + 300)
    sched_id = await _create_schedule(next_run_at=stale_at)

    spy = AsyncMock()
    try:
        with patch.object(tick_module, "trigger_schedule_run", spy):
            await tick_module.tick(async_session_maker)

        # OUR schedule NOT dispatched; still advanced to a future fire.
        assert _calls_for(spy, sched_id) == []
        new_next = await _get_next_run_at(sched_id)
        assert new_next > now
    finally:
        await _delete_schedule(sched_id)


@pytest.mark.asyncio
async def test_tick_failed_dispatch_does_not_advance() -> None:
    """A dispatch that raises an unexpected error is retried: it is dispatched
    but next_run_at is NOT advanced (stays in the past for the next tick)
    rather than silently dropping the fire."""
    now = datetime.now(UTC)
    # Due 10s ago — fresh.
    sched_id = await _create_schedule(next_run_at=now - timedelta(seconds=10))

    # trigger_schedule_run raises (an unexpected error → retry, not overlap/gone).
    spy = AsyncMock(side_effect=RuntimeError("boom"))
    try:
        with patch.object(tick_module, "trigger_schedule_run", spy):
            await tick_module.tick(async_session_maker)

        # Dispatched once ...
        assert len(_calls_for(spy, sched_id)) == 1
        # ... but next_run_at NOT advanced to the future (still in the past).
        new_next = await _get_next_run_at(sched_id)
        assert new_next < now
    finally:
        await _delete_schedule(sched_id)


async def _delete_schedule(schedule_id: UUID) -> None:
    async with async_session_maker() as db:
        await db.execute(
            AIAgentSchedule.__table__.delete().where(
                AIAgentSchedule.id == str(schedule_id)
            )
        )
        await db.commit()
