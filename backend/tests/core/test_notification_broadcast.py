"""Tests for broadcast / system event delivery (Phase E).

Broadcast events (``system.startup``, ``system.unhandled_exception``,
``system.user_login``) deliver to the admin Telegram chat WITHOUT creating any
per-user ``Notification`` rows. This preserves the retired ``notifier``'s
fire-and-forget semantics: no inbox entry, no ``NotificationDelivery`` rows.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.core.notifications.channels.base import DeliveryResult
from app.core.notifications.dispatcher import notification_dispatcher
from app.core.notifications.emitter import system_emitter
from app.core.notifications.registry import ChannelKind
from app.db.session import async_session_maker
from app.models.domain.notification import Notification


async def _drain_tasks(deadline: float = 5.0) -> None:
    """Yield control until all background tasks complete (or deadline)."""
    elapsed = 0.0
    step = 0.05
    while elapsed < deadline:
        await asyncio.sleep(step)
        elapsed += step
        if all(t.done() or t is asyncio.current_task() for t in asyncio.all_tasks()):
            break


@pytest.mark.asyncio
async def test_broadcast_delivers_to_admin_chat_without_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broadcast event hits the Telegram admin chat and persists zero rows."""
    admin_chat = "987654321"
    # _admin_chat_id() reads settings.TELEGRAM_CHAT_ID lazily.
    monkeypatch.setattr(
        "app.core.config.settings.TELEGRAM_CHAT_ID", admin_chat, raising=False
    )

    fake_channel = AsyncMock()
    fake_channel.send.return_value = DeliveryResult(ChannelKind.TELEGRAM, "sent")
    # configure() merges; restore the original channel set afterwards.
    original_channels = dict(notification_dispatcher._channels)
    notification_dispatcher.configure({ChannelKind.TELEGRAM: fake_channel})

    try:
        system_emitter.emit_fire_and_forget(
            "system.user_login",
            title="User login",
            message="admin@example.com",
            payload={"ip": "10.0.0.1", "user_agent": "pytest/1.0"},
        )

        await _drain_tasks()

        # The Telegram channel was called once, with the admin chat id and no
        # specific recipient (broadcast has no per-user target).
        fake_channel.send.assert_awaited_once()
        event_arg, recipient_arg, chat_arg = fake_channel.send.call_args.args
        assert event_arg.event_type == "system.user_login"
        assert recipient_arg is None
        assert chat_arg == admin_chat

        # Zero Notification rows were persisted (broadcast = no inbox).
        async with async_session_maker() as s:
            count = await s.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.event_type == "system.user_login")
            )
        assert count == 0, f"expected 0 Notification rows, got {count}"
    finally:
        notification_dispatcher._channels = original_channels
        await _drain_tasks(0.2)


@pytest.mark.asyncio
async def test_broadcast_skipped_when_admin_chat_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no admin chat configured, a broadcast event sends nothing."""
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_CHAT_ID", "", raising=False)

    fake_channel = AsyncMock()
    fake_channel.send.return_value = DeliveryResult(ChannelKind.TELEGRAM, "sent")
    original_channels = dict(notification_dispatcher._channels)
    notification_dispatcher.configure({ChannelKind.TELEGRAM: fake_channel})

    try:
        await system_emitter.emit(
            "system.startup",
            title="Backcast started",
            message="Started",
        )

        await _drain_tasks()

        fake_channel.send.assert_not_awaited()
    finally:
        notification_dispatcher._channels = original_channels
        await _drain_tasks(0.2)
