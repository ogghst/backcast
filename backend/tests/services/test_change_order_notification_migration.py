"""Tests for the change-order notification migration to the dispatcher.

Verifies that ``ChangeOrderService._send_notification`` and
``ChangeOrderWorkflowService._send_notification`` route through the unified
dispatcher (``user_emitter``) instead of the legacy direct
``NotificationService.create_notification`` path. The proof that the row went
through the dispatcher is the populated ``actor_type``/``actor_id``/``severity``
columns (which the legacy path never set) plus the dotted ``event_type`` code.

These tests exercise the emit seam directly rather than driving a full
change-order submission (which would require RBAC approver wiring), per the
plan's "test at the seam" guidance.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.db.session import async_session_maker
from app.models.domain.notification import Notification
from app.models.domain.notification_delivery import NotificationDelivery
from app.services.change_order_service import ChangeOrderService
from app.services.change_order_workflow_service import ChangeOrderWorkflowService


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
    """Return all notifications targeting *user_id* (detached copies)."""
    async with async_session_maker() as s:
        result = await s.execute(
            select(Notification).where(Notification.user_id == user_id)
        )
        rows = result.scalars().all()
        # Detach: read attributes while the session is still open.
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
async def test_co_service_send_notification_routes_through_dispatcher() -> None:
    """``co_submitted`` emits a dispatcher row with actor_type/severity set."""
    actor_id = uuid4()
    recipient = uuid4()
    resource_id = uuid4()

    try:
        async with async_session_maker() as session:
            service = ChangeOrderService(session)
            await service._send_notification(
                user_id=recipient,
                actor_id=actor_id,
                event_type="co_submitted",
                title="Change Order Submitted for Approval",
                message="Change order CO-001 requires your approval.",
                resource_type="change_order",
                resource_id=resource_id,
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(recipient)
        assert len(notifs) == 1
        n = notifs[0]
        # Dotted registry code (legacy path wrote the raw "co_submitted").
        assert n.event_type == "co.submitted"
        # Dispatcher-only columns: legacy path left these NULL/default.
        assert n.actor_type == "user"
        assert n.actor_id == actor_id
        assert n.severity == "notice"  # registry default for co.submitted
        assert n.resource_type == "change_order"
        assert n.resource_id == resource_id
        assert n.idempotency_key == f"co:{resource_id}:co.submitted"
    finally:
        await _cleanup(recipient)


@pytest.mark.asyncio
async def test_co_service_send_notification_dedupes_via_idempotency() -> None:
    """Re-emitting the same CO event with the same resource_id dedupes."""
    actor_id = uuid4()
    recipient = uuid4()
    resource_id = uuid4()

    try:
        for _ in range(2):
            async with async_session_maker() as session:
                service = ChangeOrderService(session)
                await service._send_notification(
                    user_id=recipient,
                    actor_id=actor_id,
                    event_type="co_approved",
                    title="Change Order Approved",
                    message="approved",
                    resource_type="change_order",
                    resource_id=resource_id,
                )
                await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(recipient)
        assert len(notifs) == 1  # second emit suppressed by idempotency_key
        assert notifs[0].event_type == "co.approved"
        assert notifs[0].actor_type == "user"
        assert notifs[0].severity == "notice"
    finally:
        await _cleanup(recipient)


@pytest.mark.asyncio
async def test_co_service_send_notification_rejected_severity() -> None:
    """``co_rejected`` carries the registry notice severity."""
    actor_id = uuid4()
    recipient = uuid4()
    resource_id = uuid4()

    try:
        async with async_session_maker() as session:
            service = ChangeOrderService(session)
            await service._send_notification(
                user_id=recipient,
                actor_id=actor_id,
                event_type="co_rejected",
                title="Change Order Rejected",
                message="rejected",
                resource_type="change_order",
                resource_id=resource_id,
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(recipient)
        assert len(notifs) == 1
        assert notifs[0].event_type == "co.rejected"
        assert notifs[0].severity == "notice"
    finally:
        await _cleanup(recipient)


@pytest.mark.asyncio
async def test_workflow_service_send_notification_routes_through_dispatcher() -> None:
    """The duplicate workflow-service path also routes through the dispatcher."""
    actor_id = uuid4()
    recipient = uuid4()
    resource_id = uuid4()
    workflow = ChangeOrderWorkflowService()

    try:
        async with async_session_maker() as session:
            await workflow._send_notification(
                db_session=session,
                user_id=recipient,
                actor_id=actor_id,
                event_type="co_submitted",
                title="Change Order Submitted for Approval",
                message="requires approval",
                resource_type="change_order",
                resource_id=resource_id,
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(recipient)
        assert len(notifs) == 1
        n = notifs[0]
        assert n.event_type == "co.submitted"
        assert n.actor_type == "user"
        assert n.actor_id == actor_id
        assert n.severity == "notice"
    finally:
        await _cleanup(recipient)


@pytest.mark.asyncio
async def test_unknown_event_type_is_skipped_silently() -> None:
    """An unmapped event_type logs and returns without raising or persisting."""
    recipient = uuid4()

    try:
        async with async_session_maker() as session:
            service = ChangeOrderService(session)
            # Should not raise.
            await service._send_notification(
                user_id=recipient,
                actor_id=uuid4(),
                event_type="not_a_real_event",
                title="x",
                message="y",
                resource_id=uuid4(),
            )
            await session.commit()
        await _drain_delivery_loops()

        notifs = await _notifications_for(recipient)
        assert notifs == []
    finally:
        await _cleanup(recipient)
