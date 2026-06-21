"""Tests for the scheduler tick (WS-3).

Covers:
- skip-missed: a stale ``next_run_at`` (outside grace) is advanced without
  dispatch; a fresh one dispatches.
- ``next_run_at``-advance correctness: both fresh and stale rows get their
  ``next_run_at`` rewritten to a future cron fire.

No real HTTP/backend: ``trigger_schedule`` is monkeypatched to a spy. Uses the
running dev DB (same as the rest of the suite) to insert real schedule rows.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
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


@pytest.mark.asyncio
async def test_tick_fresh_due_schedule_dispatches_and_advances() -> None:
    """A schedule due within the grace window is dispatched and advanced."""
    tick_module._clear_in_flight_for_tests()
    now = datetime.now(UTC)
    # Due 10s ago — well inside the default 120s grace → fresh.
    sched_id = await _create_schedule(next_run_at=now - timedelta(seconds=10))

    client = httpx.AsyncClient()
    spy = AsyncMock()
    try:
        with patch.object(tick_module, "trigger_schedule", spy):
            await tick_module.tick(async_session_maker, client)

        # OUR schedule dispatched exactly once (assert on our id, not the global
        # count, so a leftover due schedule from another test can't flake this).
        my_calls = _calls_for(spy, sched_id)
        assert len(my_calls) == 1
        assert my_calls[0].args[0] is client
        # next_run_at advanced to a future fire.
        new_next = await _get_next_run_at(sched_id)
        assert new_next > now
    finally:
        await client.aclose()
        await _delete_schedule(sched_id)
        tick_module._clear_in_flight_for_tests()


@pytest.mark.asyncio
async def test_tick_stale_due_schedule_advances_without_dispatch() -> None:
    """A schedule due outside the grace window is advanced but NOT dispatched."""
    tick_module._clear_in_flight_for_tests()
    now = datetime.now(UTC)
    # Due well past the grace window → stale (scheduler-was-down case).
    stale_at = now - timedelta(seconds=settings.SCHEDULER_MISFIRE_GRACE_SECONDS + 300)
    sched_id = await _create_schedule(next_run_at=stale_at)

    client = httpx.AsyncClient()
    spy = AsyncMock()
    try:
        with patch.object(tick_module, "trigger_schedule", spy):
            await tick_module.tick(async_session_maker, client)

        # OUR schedule NOT dispatched (assert on our id; a leftover fresh
        # schedule from another test wouldn't make this flake).
        assert _calls_for(spy, sched_id) == []
        # Still advanced to a future fire.
        new_next = await _get_next_run_at(sched_id)
        assert new_next > now
    finally:
        await client.aclose()
        await _delete_schedule(sched_id)
        tick_module._clear_in_flight_for_tests()


@pytest.mark.asyncio
async def test_tick_failed_dispatch_does_not_advance() -> None:
    """A dispatch the backend can't handle (returns False) is retried: it is
    dispatched but next_run_at is NOT advanced (stays in the past for the next
    tick) rather than silently dropping the fire."""
    tick_module._clear_in_flight_for_tests()
    now = datetime.now(UTC)
    # Due 10s ago — fresh.
    sched_id = await _create_schedule(next_run_at=now - timedelta(seconds=10))

    client = httpx.AsyncClient()
    # trigger_schedule signals "retry" (backend down / 5xx).
    spy = AsyncMock(return_value=False)
    try:
        with patch.object(tick_module, "trigger_schedule", spy):
            await tick_module.tick(async_session_maker, client)

        # OUR schedule dispatched once ...
        assert len(_calls_for(spy, sched_id)) == 1
        # ... but next_run_at NOT advanced to the future (still in the past).
        new_next = await _get_next_run_at(sched_id)
        assert new_next < now
    finally:
        await client.aclose()
        await _delete_schedule(sched_id)
        tick_module._clear_in_flight_for_tests()


def _calls_for(spy: AsyncMock, schedule_id: UUID) -> list:
    """Return the spy's await calls whose schedule_id arg matches ours.

    Asserting on the per-schedule call count (rather than the global
    ``spy.await_count``) keeps these tests robust to any leftover due schedule
    from another test sharing the dev DB (trigger_schedule is called as
    ``(client, schedule_id, owner_user_id)``).
    """
    return [c for c in spy.await_args_list if str(c.args[1]) == str(schedule_id)]


async def _delete_schedule(schedule_id: UUID) -> None:
    async with async_session_maker() as db:
        await db.execute(
            AIAgentSchedule.__table__.delete().where(
                AIAgentSchedule.id == str(schedule_id)
            )
        )
        await db.commit()
