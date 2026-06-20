"""Tests for the agent-execution notification bridge (Phase C).

Validates that ``agent_emitter`` persists ``agent.completed``/``agent.ask_user``
notifications targeting the owner with the correct severity and that the
idempotency key suppresses duplicates — i.e. the contract the
``_notify_agent_owner`` helper in ``agent_service.py`` and the
``_notify_owner_ask``/``_notify_owner_approval`` helpers in the tools rely on.

We test at the emitter seam (the helper's exact emit call) rather than driving
a full LangGraph run, per the plan's guidance that a full graph run is too
heavy for a unit test.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.core.notifications import NotificationType, agent_emitter
from app.db.session import async_session_maker
from app.models.domain.notification import Notification
from app.models.domain.notification_delivery import NotificationDelivery


async def _drain_delivery_loops() -> None:
    """Yield control so any scheduled ``_deliver`` tasks can run."""
    deadline = 5.0
    elapsed = 0.0
    while elapsed < deadline:
        await asyncio.sleep(0.05)
        elapsed += 0.05
        if all(t.done() or t is asyncio.current_task() for t in asyncio.all_tasks()):
            break


async def _notifications_for(user_id: UUID) -> list[Notification]:
    async with async_session_maker() as s:
        result = await s.execute(
            select(Notification).where(Notification.user_id == user_id)
        )
        rows = result.scalars().all()
        return [
            Notification(
                user_id=r.user_id,
                event_type=r.event_type,
                title=r.title,
                message=r.message,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                actor_type=r.actor_type,
                actor_id=r.actor_id,
                severity=r.severity,
                idempotency_key=r.idempotency_key,
            )
            for r in rows
        ]


async def _cleanup(user_id: UUID) -> None:
    """Remove deliveries + notifications for *user_id* (deliveries first, FK)."""
    async with async_session_maker() as s:
        await s.execute(
            delete(NotificationDelivery).where(
                NotificationDelivery.notification_id.in_(
                    select(Notification.id).where(Notification.user_id == user_id)
                )
            )
        )
        await s.execute(delete(Notification).where(Notification.user_id == user_id))
        await s.commit()


@pytest.mark.asyncio
async def test_agent_completed_persists_targeting_owner() -> None:
    """agent.completed emits a notice-severity notification to the owner."""
    execution_id = uuid4()
    owner = uuid4()

    try:
        async with async_session_maker() as session:
            await agent_emitter(execution_id, session).emit(
                NotificationType.AGENT_COMPLETED,
                title="Agent completed",
                message="Agent run completed.",
                target_user_ids=[owner],
                resource_type="agent_execution",
                resource_id=execution_id,
                idempotency_key=f"agent:{execution_id}:completed",
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(owner)
        assert len(notifs) == 1
        n = notifs[0]
        assert n.event_type == "agent.completed"
        assert n.actor_type == "agent"
        assert n.actor_id == execution_id
        assert n.severity == "notice"  # registry default for agent.completed
        assert n.resource_type == "agent_execution"
        assert n.resource_id == execution_id
        assert n.idempotency_key == f"agent:{execution_id}:completed"
    finally:
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_agent_failed_is_urgent_severity() -> None:
    """agent.failed carries the registry URGENT severity."""
    execution_id = uuid4()
    owner = uuid4()

    try:
        async with async_session_maker() as session:
            await agent_emitter(execution_id, session).emit(
                NotificationType.AGENT_FAILED,
                title="Agent failed",
                message="boom",
                target_user_ids=[owner],
                resource_type="agent_execution",
                resource_id=execution_id,
                idempotency_key=f"agent:{execution_id}:failed",
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(owner)
        assert len(notifs) == 1
        assert notifs[0].event_type == "agent.failed"
        assert notifs[0].severity == "urgent"
        assert notifs[0].actor_type == "agent"
    finally:
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_agent_completed_dedupes_via_idempotency() -> None:
    """Re-emitting the same terminal event dedupes to one row."""
    execution_id = uuid4()
    owner = uuid4()
    key = f"agent:{execution_id}:completed"

    try:
        for _ in range(2):
            async with async_session_maker() as session:
                await agent_emitter(execution_id, session).emit(
                    NotificationType.AGENT_COMPLETED,
                    title="Agent completed",
                    message="done",
                    target_user_ids=[owner],
                    resource_type="agent_execution",
                    resource_id=execution_id,
                    idempotency_key=key,
                )
                await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(owner)
        assert len(notifs) == 1
    finally:
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_agent_ask_user_dedupes_per_step_not_per_run() -> None:
    """Different ask ids produce distinct notifications; same ask id dedupes."""
    execution_id = uuid4()
    owner = uuid4()
    ask_a = uuid4()
    ask_b = uuid4()

    try:
        async with async_session_maker() as session:
            # Same ask twice -> 1 row.
            for _ in range(2):
                await agent_emitter(execution_id, session).emit(
                    NotificationType.AGENT_ASK_USER,
                    title="Agent needs your input",
                    message="q",
                    target_user_ids=[owner],
                    resource_type="agent_execution",
                    resource_id=execution_id,
                    idempotency_key=f"agent:{execution_id}:ask:{ask_a}",
                )
            # Different ask -> another row.
            await agent_emitter(execution_id, session).emit(
                NotificationType.AGENT_ASK_USER,
                title="Agent needs your input",
                message="q2",
                target_user_ids=[owner],
                resource_type="agent_execution",
                resource_id=execution_id,
                idempotency_key=f"agent:{execution_id}:ask:{ask_b}",
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(owner)
        assert len(notifs) == 2
        assert all(n.event_type == "agent.ask_user" for n in notifs)
        assert all(n.severity == "notice" for n in notifs)
    finally:
        await _cleanup(owner)


def test_notify_agent_owner_helper_is_importable_and_callable() -> None:
    """The bridge helper exists and has the expected signature shape.

    A pure-import smoke test: confirms ``_notify_agent_owner`` is wired and
    accepts the terminal-event arguments without importing a graph.
    """
    from app.ai.agent_service import _notify_agent_owner

    assert callable(_notify_agent_owner)

    # Inspect that it accepts the documented keyword-only args (best-effort).
    import inspect

    params = inspect.signature(_notify_agent_owner).parameters
    for required in ("execution_id", "user_id", "code", "title", "message"):
        assert required in params
    # title/message/idempotency_key must be keyword-only.
    for kw_only in ("title", "message", "idempotency_key"):
        assert params[kw_only].kind == inspect.Parameter.KEYWORD_ONLY


def test_tool_bridge_helpers_exist() -> None:
    """The ask_user / approval bridge helpers are importable."""
    from app.ai.tools.ask_user import _notify_owner_ask  # noqa: F401
    from app.ai.tools.interrupt_node import _notify_owner_approval  # noqa: F401


@pytest.mark.asyncio
async def test_notify_agent_owner_emits_via_short_lived_session() -> None:
    """``_notify_agent_owner`` opens its own session and persists a row.

    This exercises the actual helper end-to-end (the same call made by the
    agent terminal paths), confirming the resource_id equals the execution id
    so the bell can deep-link back to the run. The InAppChannel delivery runs
    in its own task; with no live WebSocket for the test user, ``send_to_user``
    is a graceful no-op, so no monkeypatch is needed.
    """
    from app.ai.agent_service import _notify_agent_owner

    execution_id = uuid4()
    owner = uuid4()

    try:
        await _notify_agent_owner(
            str(execution_id),
            owner,
            NotificationType.AGENT_COMPLETED,
            title="Agent completed",
            message="summary",
            idempotency_key=f"agent:{execution_id}:completed",
        )
        await _drain_delivery_loops()

        notifs = await _notifications_for(owner)
        assert len(notifs) == 1
        n = notifs[0]
        assert n.event_type == "agent.completed"
        assert n.actor_type == "agent"
        assert n.actor_id == execution_id  # bus key == resource id (deep-link)
        assert n.resource_id == execution_id
    finally:
        await _cleanup(owner)
