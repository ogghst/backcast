"""Tests for the commit-ordering fix in NotificationDispatcher.

The background ``_deliver`` coroutine opens its own session and writes
``NotificationDelivery`` rows whose FK references the notification flushed in
the caller's session. Delivery must therefore be deferred until the caller's
session actually commits, and dropped entirely on rollback.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.core.notifications.emitter import user_emitter
from app.db.session import async_session_maker
from app.models.domain.notification import Notification
from app.models.domain.notification_delivery import NotificationDelivery


async def _drain_delivery_loops(extra: float = 0.0) -> None:
    """Yield control so any scheduled ``_deliver`` tasks can run to completion."""
    deadline = 5.0
    elapsed = 0.0
    step = 0.05
    # Background delivery runs in its own session; yield until the loop is idle
    # or the deadline expires.
    while elapsed < deadline:
        await asyncio.sleep(step)
        elapsed += step
        # asyncio.all_tasks captures everything pending on this loop, including
        # _deliver coroutines. When only the test task remains, delivery is done.
        if all(t.done() or t is asyncio.current_task() for t in asyncio.all_tasks()):
            break
    if extra:
        await asyncio.sleep(extra)


async def _unread_count_for(user_id: UUID) -> int:
    """Count NotificationDelivery rows that reference notifications for *user_id*."""
    async with async_session_maker() as s:
        result = await s.execute(
            select(NotificationDelivery)
            .join(
                Notification,
                NotificationDelivery.notification_id == Notification.id,
            )
            .where(Notification.user_id == user_id)
        )
        return len(result.scalars().all())


async def _cleanup(user_id: UUID) -> None:
    """Remove any notifications + deliveries created for *user_id*."""
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
async def test_dispatch_delivers_after_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A committed dispatch produces a NotificationDelivery + correct badge."""
    user_id = uuid4()
    sent: list[tuple[UUID, dict[str, Any]]] = []

    async def _record_send(uid: UUID, payload: dict[str, Any]) -> None:
        sent.append((uid, payload))

    monkeypatch.setattr(
        "app.core.notifications.dispatcher.user_connection_manager.send_to_user",
        _record_send,
    )

    try:
        async with async_session_maker() as session:
            emitter = user_emitter(actor_id=user_id, session=session)
            await emitter.emit(
                "co.submitted",
                title="CO submitted",
                message="Change order 42 was submitted",
                target_user_ids=[user_id],
            )
            await session.commit()

        await _drain_delivery_loops()

        # 1. Exactly one delivery row exists (IN_APP channel; TELEGRAM not
        #    registered by default so it's skipped).
        count = await _unread_count_for(user_id)
        assert count == 1, f"expected 1 delivery row, got {count}"

        # 2. A badge_update frame was pushed reflecting the new notification.
        badges = [p for _, p in sent if p.get("type") == "badge_update"]
        assert badges, f"no badge_update frame sent; got {sent!r}"
        assert badges[-1]["unread_count"] == 1, badges[-1]
    finally:
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_dispatch_no_delivery_on_rollback() -> None:
    """A rolled-back dispatch must never produce a NotificationDelivery."""
    user_id = uuid4()

    try:
        async with async_session_maker() as session:
            emitter = user_emitter(actor_id=user_id, session=session)
            await emitter.emit(
                "co.submitted",
                title="CO submitted",
                message="This change will be rolled back",
                target_user_ids=[user_id],
            )
            await session.rollback()

        # Let any stray task run.
        await _drain_delivery_loops(extra=0.1)

        count = await _unread_count_for(user_id)
        assert count == 0, f"expected 0 delivery rows after rollback, got {count}"
    finally:
        await _cleanup(user_id)
