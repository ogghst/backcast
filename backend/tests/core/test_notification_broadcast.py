"""Tests for broadcast and opt-in system event delivery.

Behavior split:

- ``system.unhandled_exception`` is a true **broadcast** event: it fires to the
  admin Telegram chat WITHOUT creating any per-user ``Notification`` rows and
  ignores all user preferences (a crash alert must never be silenceable).
- ``system.startup`` and ``system.user_login`` are **opt-in** events: they
  deliver only to users who have explicitly enabled the event in their own
  notification preferences (default OFF). With no enabled preference rows they
  deliver to nobody; no role/group resolution is performed.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.core.notifications.channels.base import DeliveryResult
from app.core.notifications.dispatcher import notification_dispatcher
from app.core.notifications.emitter import system_emitter
from app.core.notifications.registry import ChannelKind, get_type_def
from app.db.session import async_session_maker
from app.models.domain.notification import Notification
from app.models.domain.notification_delivery import NotificationDelivery
from app.models.domain.notification_preference import UserNotificationPreference
from app.models.domain.user import User


async def _drain_tasks(deadline: float = 5.0) -> None:
    """Yield control until all background tasks complete (or deadline)."""
    elapsed = 0.0
    step = 0.05
    while elapsed < deadline:
        await asyncio.sleep(step)
        elapsed += step
        if all(t.done() or t is asyncio.current_task() for t in asyncio.all_tasks()):
            break


async def _seed_user(email: str) -> UUID:
    """Create a bare user (no role). Returns user_id."""
    async with async_session_maker() as session:
        user_id = uuid4()
        session.add(
            User(
                id=user_id,
                user_id=user_id,
                email=email,
                hashed_password="x",
                full_name=email,
                is_active=True,
                created_by=user_id,
            )
        )
        await session.commit()
    return user_id


async def _seed_pref(
    user_id: UUID, event_type: str, channel: str, enabled: bool
) -> None:
    """Insert a single UserNotificationPreference row."""
    async with async_session_maker() as s:
        s.add(
            UserNotificationPreference(
                user_id=user_id,
                event_type=event_type,
                channel=channel,
                enabled=enabled,
            )
        )
        await s.commit()


@pytest_asyncio.fixture(autouse=True)
async def _user_cleanup() -> AsyncGenerator[list[UUID], None]:
    """Collect and remove test users created by tests.

    Per the test-db-cleanup convention, persistent rows created here are deleted
    so junk does not accumulate in the dev DB across runs. Tests append created
    user ids to the yielded list; teardown deletes them (children first to
    satisfy FK constraints).
    """
    created: list[UUID] = []
    yield created

    if created:
        async with async_session_maker() as s:
            await s.execute(
                delete(NotificationDelivery).where(
                    NotificationDelivery.notification_id.in_(
                        select(Notification.id).where(Notification.user_id.in_(created))
                    )
                )
            )
            await s.execute(
                delete(Notification).where(
                    Notification.user_id.in_(created),
                    Notification.event_type.in_(
                        ["system.startup", "system.user_login"]
                    ),
                )
            )
            await s.execute(
                delete(UserNotificationPreference).where(
                    UserNotificationPreference.user_id.in_(created)
                )
            )
            await s.execute(delete(User).where(User.user_id.in_(created)))
            await s.commit()


# ---------------------------------------------------------------------------
# Broadcast: system.unhandled_exception (still broadcast=True, prefs ignored)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_exception_delivers_to_admin_chat_without_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broadcast exception event hits the admin chat and persists zero rows."""
    admin_chat = "987654321"
    monkeypatch.setattr(
        "app.core.config.settings.TELEGRAM_CHAT_ID", admin_chat, raising=False
    )

    fake_channel = AsyncMock()
    fake_channel.send.return_value = DeliveryResult(ChannelKind.TELEGRAM, "sent")
    original_channels = dict(notification_dispatcher._channels)
    notification_dispatcher.configure({ChannelKind.TELEGRAM: fake_channel})

    try:
        system_emitter.emit_fire_and_forget(
            "system.unhandled_exception",
            title="Unhandled exception",
            message="boom",
            payload={"exc": "RuntimeError"},
        )

        await _drain_tasks()

        fake_channel.send.assert_awaited_once()
        event_arg, recipient_arg, chat_arg = fake_channel.send.call_args.args
        assert event_arg.event_type == "system.unhandled_exception"
        assert recipient_arg is None  # broadcast has no per-user target
        assert chat_arg == admin_chat

        async with async_session_maker() as s:
            count = await s.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.event_type == "system.unhandled_exception")
            )
        assert count == 0
    finally:
        notification_dispatcher._channels = original_channels
        await _drain_tasks(0.2)


@pytest.mark.asyncio
async def test_broadcast_exception_skipped_when_admin_chat_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no admin chat configured, a broadcast exception event sends nothing."""
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_CHAT_ID", "", raising=False)

    fake_channel = AsyncMock()
    fake_channel.send.return_value = DeliveryResult(ChannelKind.TELEGRAM, "sent")
    original_channels = dict(notification_dispatcher._channels)
    notification_dispatcher.configure({ChannelKind.TELEGRAM: fake_channel})

    try:
        await system_emitter.emit(
            "system.unhandled_exception",
            title="Unhandled exception",
            message="boom",
        )

        await _drain_tasks()

        fake_channel.send.assert_not_awaited()
    finally:
        notification_dispatcher._channels = original_channels
        await _drain_tasks(0.2)


# ---------------------------------------------------------------------------
# Opt-in: system.startup / system.user_login (preferences honored, default OFF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_opt_in_default_off_delivers_to_nobody(
    _user_cleanup: list[UUID],
) -> None:
    """With no enabled preference rows, system.startup creates zero new rows.

    Uses a before/after count delta (rather than absolute count) so historical
    rows left in the dev DB by prior runs don't pollute the assertion.
    """
    async with async_session_maker() as s:
        before = await s.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.event_type == "system.startup")
        )

    await system_emitter.emit(
        "system.startup",
        title="Backcast started",
        message="Started",
    )
    await _drain_tasks()

    async with async_session_maker() as s:
        after = await s.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.event_type == "system.startup")
        )
    assert after == before, (
        f"expected 0 new Notification rows by default, "
        f"got {after - before} new (before={before}, after={after})"
    )


@pytest.mark.asyncio
async def test_opt_in_single_channel_creates_row_for_opted_user(
    _user_cleanup: list[UUID],
) -> None:
    """A user with an enabled telegram pref for system.startup becomes a recipient."""
    uid = await _seed_user("notif-optin-tg@example.com")
    _user_cleanup.append(uid)
    await _seed_pref(uid, "system.startup", ChannelKind.TELEGRAM.value, True)

    await system_emitter.emit(
        "system.startup",
        title="Backcast started",
        message="Started",
    )
    await _drain_tasks()

    async with async_session_maker() as s:
        rows = (
            await s.scalars(
                select(Notification).where(
                    Notification.user_id == uid,
                    Notification.event_type == "system.startup",
                )
            )
        ).all()
    assert len(rows) == 1, f"expected 1 row for opted-in user, got {len(rows)}"


@pytest.mark.asyncio
async def test_opt_in_respects_enabled_channels(
    _user_cleanup: list[UUID],
) -> None:
    """A user opted in via in_app only is delivered on IN_APP, not TELEGRAM."""
    uid = await _seed_user("notif-optin-inapp@example.com")
    _user_cleanup.append(uid)
    await _seed_pref(uid, "system.startup", ChannelKind.IN_APP.value, True)
    await _seed_pref(uid, "system.startup", ChannelKind.TELEGRAM.value, False)

    await system_emitter.emit(
        "system.startup",
        title="Backcast started",
        message="Started",
    )
    await _drain_tasks()

    async with async_session_maker() as s:
        notif = (
            await s.scalars(
                select(Notification).where(
                    Notification.user_id == uid,
                    Notification.event_type == "system.startup",
                )
            )
        ).one_or_none()
        assert notif is not None

        deliveries = (
            await s.scalars(
                select(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notif.id
                )
            )
        ).all()
    channels = {d.channel for d in deliveries}
    assert channels == {ChannelKind.IN_APP.value}, (
        f"expected only in_app delivery, got {channels}"
    )


@pytest.mark.asyncio
async def test_opt_in_explicitly_disabled_not_a_recipient(
    _user_cleanup: list[UUID],
) -> None:
    """A user with both channels enabled=False is not a recipient (0 rows)."""
    uid = await _seed_user("notif-optin-disabled@example.com")
    _user_cleanup.append(uid)
    await _seed_pref(uid, "system.startup", ChannelKind.IN_APP.value, False)
    await _seed_pref(uid, "system.startup", ChannelKind.TELEGRAM.value, False)

    await system_emitter.emit(
        "system.startup",
        title="Backcast started",
        message="Started",
    )
    await _drain_tasks()

    async with async_session_maker() as s:
        count = await s.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == uid,
                Notification.event_type == "system.startup",
            )
        )
    assert count == 0, f"expected 0 rows for fully-disabled user, got {count}"


@pytest.mark.asyncio
async def test_opt_in_wildcard_pref_makes_recipient(
    _user_cleanup: list[UUID],
) -> None:
    """A user with an enabled '*' / telegram pref is a recipient of system.startup."""
    uid = await _seed_user("notif-optin-wild@example.com")
    _user_cleanup.append(uid)
    await _seed_pref(uid, "*", ChannelKind.TELEGRAM.value, True)

    await system_emitter.emit(
        "system.startup",
        title="Backcast started",
        message="Started",
    )
    await _drain_tasks()

    async with async_session_maker() as s:
        rows = (
            await s.scalars(
                select(Notification).where(
                    Notification.user_id == uid,
                    Notification.event_type == "system.startup",
                )
            )
        ).all()
    assert len(rows) == 1, f"expected 1 row via wildcard pref, got {len(rows)}"


@pytest.mark.asyncio
async def test_opt_in_registry_flags() -> None:
    """system.startup/user_login are opt-in, non-broadcast, with both channels."""
    startup = get_type_def("system.startup")
    assert startup.opt_in is True
    assert startup.broadcast is False
    assert startup.default_channels == (ChannelKind.IN_APP, ChannelKind.TELEGRAM)

    login = get_type_def("system.user_login")
    assert login.opt_in is True
    assert login.broadcast is False
    assert login.default_channels == (ChannelKind.IN_APP, ChannelKind.TELEGRAM)


@pytest.mark.asyncio
async def test_unhandled_exception_still_broadcast() -> None:
    """system.unhandled_exception remains a broadcast, non-opt-in event."""
    type_def = get_type_def("system.unhandled_exception")
    assert type_def.broadcast is True
    assert type_def.opt_in is False
