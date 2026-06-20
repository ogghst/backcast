"""Unified notification dispatcher.

The dispatcher is the single funnel every notification passes through. It:

1. Validates the event type against the registry.
2. Resolves target users (explicit list, broadcast, or resource-owner fallback).
3. Persists one ``Notification`` row per target inside the caller's session
   (so it commits with the business change), honoring idempotency.
4. Schedules background delivery to each enabled channel in its own session,
   writing a ``NotificationDelivery`` row per attempt.

The module exposes :data:`notification_dispatcher`, a process singleton.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import event as sa_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications.channels.base import Channel, DeliveryResult
from app.core.notifications.channels.in_app import InAppChannel
from app.core.notifications.connection_manager import user_connection_manager
from app.core.notifications.event import NotificationEvent
from app.core.notifications.registry import ChannelKind, get_type_def
from app.db.session import async_session_maker
from app.models.domain.notification import Notification
from app.models.domain.notification_delivery import NotificationDelivery
from app.models.domain.notification_preference import UserNotificationPreference
from app.models.domain.telegram_account import TelegramAccount
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Central dispatcher owning the channel registry and delivery fan-out.

    Always registers an :class:`InAppChannel`; extra channels (e.g. Telegram)
    are merged in via :meth:`configure`, called from the app lifespan in a
    later phase.
    """

    def __init__(self) -> None:
        self._channels: dict[ChannelKind, Channel] = {
            ChannelKind.IN_APP: InAppChannel()
        }
        self._lock = asyncio.Lock()

    def configure(self, channels: dict[ChannelKind, Channel]) -> None:
        """Merge extra channels into the registry.

        Safe to call multiple times (e.g. on lifespan reload).

        Args:
            channels: Mapping of channel kind to channel instance.
        """
        self._channels.update(channels)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self, event: NotificationEvent, session: AsyncSession
    ) -> list[Notification]:
        """Persist and fan out *event*.

        Args:
            event: The notification event.
            session: Caller's session; persistence happens here so it commits
                with the surrounding business change.

        Returns:
            The list of created :class:`Notification` rows (one per target).
        """
        try:
            type_def = get_type_def(event.event_type)
        except ValueError:
            logger.warning(
                "Dispatch of unknown notification type %r ignored",
                event.event_type,
            )
            return []

        # Broadcast / system events (system.startup, system.unhandled_exception,
        # system.user_login) deliver to the broadcast channels (admin Telegram
        # chat) WITHOUT creating per-user Notification rows. This preserves the
        # retired notifier's fire-and-forget semantics: no inbox entry, no
        # NotificationDelivery rows, just an admin alert.
        if type_def.broadcast:
            self._schedule_broadcast_delivery(event)
            return []

        targets = await self._resolve_targets(event, session)
        if not targets:
            logger.debug("Notification %s had no resolved targets", event.event_type)
            return []

        service = NotificationService(session)
        created: list[Notification] = []
        for user_id in targets:
            if event.idempotency_key and await service.get_user_idempotency_exists(
                user_id, event.idempotency_key
            ):
                logger.debug(
                    "Skipping duplicate notification %s for user %s (idempotency)",
                    event.event_type,
                    user_id,
                )
                continue

            notification = await service.create_notification(
                user_id=user_id,
                event_type=event.event_type,
                title=event.title,
                message=event.message,
                resource_type=event.resource_type or type_def.resource_type,
                resource_id=event.resource_id,
                actor_type=event.actor_type.value,
                actor_id=event.actor_id,
                severity=event.severity.value,
                project_id=event.project_id,
                idempotency_key=event.idempotency_key,
            )
            created.append(notification)

        # Defer delivery scheduling until the caller's session commits.
        # The background _deliver coroutine opens its OWN session and writes
        # NotificationDelivery rows whose FK references the notification we
        # just flushed here. If we scheduled before commit, that fresh session
        # would either FK-violate (notification row not yet visible) or see a
        # stale unread count. Registering an after_commit hook guarantees the
        # notification row is durable before any delivery runs — and that a
        # rollback silently drops the whole delivery (a change that didn't
        # persist must not notify).
        if created:
            self._defer_delivery(session, created, event)

        return created

    # ------------------------------------------------------------------
    # Commit-deferred delivery scheduling
    # ------------------------------------------------------------------

    _PENDING_KEY = "_pending_notification_deliveries"
    _HOOK_KEY = "_notification_after_commit_registered"

    def _defer_delivery(
        self,
        session: AsyncSession,
        notifications: list[Notification],
        event: NotificationEvent,
    ) -> None:
        """Accumulate deliveries on *session* and schedule them on commit.

        Multiple dispatches within one session all queue onto the same list.
        The ``after_commit`` listener is registered at most once per session.
        """
        info = session.info
        pending: list[tuple[UUID, NotificationEvent, UUID]] = info.setdefault(
            self._PENDING_KEY, []
        )
        for notification in notifications:
            pending.append((notification.id, event, notification.user_id))

        if info.get(self._HOOK_KEY):
            return
        info[self._HOOK_KEY] = True

        dispatcher = self

        def _on_commit(sync_session: object) -> None:  # noqa: ARG001
            """after_commit hook: schedule every queued delivery, then clear.

            Fires synchronously inside ``commit()``. We are in an async context
            (dispatch was awaited on a running loop), so ``create_task`` is
            valid. No DB work is done on the committing session here — only
            task scheduling.
            """
            queued = info.pop(dispatcher._PENDING_KEY, None)
            if not queued:
                return
            for notification_id, evt, user_id in queued:
                dispatcher._schedule_delivery(notification_id, evt, user_id)

        def _on_rollback(sync_session: object) -> None:  # noqa: ARG001
            """after_rollback hook: drop every queued delivery.

            A notification must not fire for a change that didn't persist.
            Clearing here (not just relying on after_commit not firing) makes
            the no-deliver-on-rollback guarantee robust to a later commit on
            the same session (e.g. an outer fixture's teardown commit), which
            would otherwise reschedule the discarded deliveries.
            """
            info.pop(dispatcher._PENDING_KEY, None)

        sa_event.listen(session.sync_session, "after_commit", _on_commit)
        sa_event.listen(session.sync_session, "after_rollback", _on_rollback)

    def _schedule_delivery(
        self, notification_id: UUID, event: NotificationEvent, user_id: UUID
    ) -> None:
        """Fire-and-forget delivery task; safe when no loop is running."""
        try:
            asyncio.get_running_loop().create_task(
                self._deliver(notification_id, event, user_id)
            )
        except RuntimeError:
            logger.debug("Cannot schedule notification delivery: no running event loop")

    def _schedule_broadcast_delivery(self, event: NotificationEvent) -> None:
        """Fire-and-forget broadcast delivery; safe when no loop is running.

        Broadcast events have no per-user targets, so they bypass the normal
        persist-then-deliver path entirely.
        """
        try:
            asyncio.get_running_loop().create_task(self._deliver_broadcast(event))
        except RuntimeError:
            logger.debug(
                "Cannot schedule broadcast notification delivery: no running event loop"
            )

    async def _deliver_broadcast(self, event: NotificationEvent) -> None:
        """Deliver a broadcast event to each broadcast channel.

        Opens its own session (no persistence happens — broadcast events create
        no Notification rows) and fans out to every channel kind listed in the
        type def's ``default_channels`` that is actually registered. Per-channel
        failures are isolated and logged.

        - ``ChannelKind.TELEGRAM`` resolves to the admin chat id; skipped when
          the admin chat is not configured.
        - ``ChannelKind.IN_APP`` is skipped (a broadcast has no per-user inbox).
        - No ``NotificationDelivery`` rows are written (there is no
          ``notification_id`` to reference).
        """
        type_def = get_type_def(event.event_type)
        for channel_kind in type_def.default_channels:
            if channel_kind is ChannelKind.IN_APP:
                # Broadcasts have no per-user inbox.
                continue
            channel = self._channels.get(channel_kind)
            if channel is None:
                continue

            if channel_kind is ChannelKind.TELEGRAM:
                chat_id = self._admin_chat_id()
                if not chat_id:
                    logger.debug(
                        "Broadcast notification %s skipped: admin chat not configured",
                        event.event_type,
                    )
                    continue
            else:
                chat_id = None

            try:
                await channel.send(event, None, chat_id)
            except Exception:
                logger.exception(
                    "Channel %s raised while delivering broadcast %s",
                    channel_kind.value,
                    event.event_type,
                )

    # ------------------------------------------------------------------
    # Target resolution (overridable hooks)
    # ------------------------------------------------------------------

    async def _resolve_targets(
        self,
        event: NotificationEvent,
        session: AsyncSession,  # noqa: ARG002
    ) -> list[UUID]:
        """Determine the recipient user list.

        - Explicit ``target_user_ids`` wins (deduped).
        - Broadcast types expand via :meth:`_expand_broadcast`.
        - Otherwise fall back to resource-owner resolution.

        Args:
            event: The notification event.
            session: Caller's session (unused in this default impl).

        Returns:
            Deduplicated list of target user ids.
        """
        if event.target_user_ids:
            # Dedupe while preserving order.
            seen: set[UUID] = set()
            targets: list[UUID] = []
            for uid in event.target_user_ids:
                if uid not in seen:
                    seen.add(uid)
                    targets.append(uid)
            return targets

        try:
            type_def = get_type_def(event.event_type)
        except ValueError:
            return []

        if type_def.broadcast:
            return await self._expand_broadcast(event, session)

        return await self._resolve_resource_owner(event, session)

    async def _expand_broadcast(
        self,
        event: NotificationEvent,  # noqa: ARG002
        session: AsyncSession,  # noqa: ARG002
    ) -> list[UUID]:
        """Broadcast expansion. Returns ``[]`` by default.

        Full RBAC-aware expansion is a later phase. For now, broadcast/system
        events deliver only through channels that ignore the user list (e.g.
        the Telegram admin chat), so returning an empty list still lets those
        channels fire via the broadcast path.
        """
        return []

    async def _resolve_resource_owner(
        self,
        event: NotificationEvent,  # noqa: ARG002
        session: AsyncSession,  # noqa: ARG002
    ) -> list[UUID]:
        """Resource-owner fallback. Returns ``[]`` by default.

        Real owner resolution is added when existing emitters are migrated
        (Phase B/C). Returning ``[]`` is safe: explicit ``target_user_ids``
        is the primary path.
        """
        return []

    # ------------------------------------------------------------------
    # Background delivery
    # ------------------------------------------------------------------

    async def _deliver(
        self,
        notification_id: UUID,
        event: NotificationEvent,
        user_id: UUID,
    ) -> None:
        """Deliver *event* to each enabled channel in a fresh session.

        Opens its own session so delivery cannot roll back the caller's
        business transaction. Per-channel failures are isolated.
        """
        type_def = get_type_def(event.event_type)
        is_broadcast = type_def.broadcast

        async with async_session_maker() as session:
            enabled_channels = await self._resolve_channels(
                user_id, event.event_type, type_def.default_channels, session
            )

            for channel_kind in enabled_channels:
                channel = self._channels.get(channel_kind)
                if channel is None:
                    continue
                chat_id = await self._resolve_chat_id(
                    channel_kind, user_id, event, is_broadcast, session
                )
                try:
                    result = await channel.send(event, user_id, chat_id)
                except Exception:
                    logger.exception(
                        "Channel %s raised while delivering notification %s",
                        channel_kind.value,
                        notification_id,
                    )
                    result = DeliveryResult(channel_kind, "failed", "exception")

                await self._record_delivery(
                    session, notification_id, channel_kind, result.status, result.error
                )

                # In-app: also push a badge-update frame with the live count.
                if channel_kind is ChannelKind.IN_APP and result.status == "sent":
                    await self._push_badge_update(session, user_id)

            await session.commit()

    async def _resolve_channels(
        self,
        user_id: UUID,
        event_type: str,
        default_channels: tuple[ChannelKind, ...],
        session: AsyncSession,
    ) -> list[ChannelKind]:
        """Resolve the effective channel list from preferences or defaults.

        A preference row with ``enabled=False`` disables that channel; a row
        with ``enabled=True`` enables it. Channels not covered by any
        preference fall back to the registry defaults. Broadcast events bypass
        user preferences (admin/system scope).

        Args:
            user_id: Recipient user id.
            event_type: Dotted event code.
            default_channels: Registry default channels.
            session: The background delivery session (no extra session opened).
        """
        try:
            type_def = get_type_def(event_type)
        except ValueError:
            return list(default_channels)

        if type_def.broadcast:
            # Broadcasts go to all default channels regardless of prefs.
            return list(default_channels)

        overrides = await self._load_channel_overrides(user_id, event_type, session)
        # Start from defaults, then apply any explicit (wildcard or exact) overrides.
        effective: dict[ChannelKind, bool] = {
            ch: (ch in default_channels) for ch in ChannelKind
        }
        for kind, enabled in overrides.items():
            effective[kind] = enabled
        return [kind for kind, on in effective.items() if on]

    async def _load_channel_overrides(
        self, user_id: UUID, event_type: str, session: AsyncSession
    ) -> dict[ChannelKind, bool]:
        """Load user preference overrides for *event_type* (exact + wildcard).

        Runs in the provided background delivery session (no extra session).
        """
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.event_type.in_([event_type, "*"]),
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        overrides: dict[ChannelKind, bool] = {}
        for row in rows:
            try:
                kind = ChannelKind(row.channel)
            except ValueError:
                continue
            # Exact event_type overrides win over wildcard.
            if row.event_type == event_type:
                overrides[kind] = row.enabled
            elif kind not in overrides:
                overrides[kind] = row.enabled
        return overrides

    async def _resolve_chat_id(
        self,
        channel_kind: ChannelKind,
        user_id: UUID,
        event: NotificationEvent,  # noqa: ARG002
        is_broadcast: bool,
        session: AsyncSession,
    ) -> str | None:
        """Resolve the transport address for *channel_kind*.

        Telegram: the user's verified ``telegram_accounts.telegram_chat_id``,
        or the admin chat id for broadcast/system events.
        """
        if channel_kind is not ChannelKind.TELEGRAM:
            return None

        if is_broadcast:
            return self._admin_chat_id()

        stmt = select(TelegramAccount).where(
            TelegramAccount.user_id == user_id,
            TelegramAccount.is_verified.is_(True),
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            return None
        return account.telegram_chat_id

    def _admin_chat_id(self) -> str | None:
        """Return the admin Telegram chat id from settings (lazy import)."""
        from app.core.config import settings

        chat_id = settings.TELEGRAM_CHAT_ID
        return chat_id or None

    async def _record_delivery(
        self,
        session: AsyncSession,
        notification_id: UUID,
        channel_kind: ChannelKind,
        status: str,
        error: str | None,
    ) -> None:
        """Write a :class:`NotificationDelivery` row."""
        delivery = NotificationDelivery(
            notification_id=notification_id,
            channel=channel_kind.value,
            status=status,
            error=error,
            attempted_at=datetime.now(UTC),
        )
        session.add(delivery)
        await session.flush()

    async def _push_badge_update(self, session: AsyncSession, user_id: UUID) -> None:
        """Push a ``badge_update`` frame with the live unread count."""
        count = await NotificationService(session).get_unread_count(user_id)
        await user_connection_manager.send_to_user(
            user_id, {"type": "badge_update", "unread_count": count}
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        """Shut down every registered channel (close HTTP clients, etc.)."""
        for channel in self._channels.values():
            try:
                await channel.shutdown()
            except Exception:
                logger.exception("Channel shutdown failed")


# Module-level singleton.
notification_dispatcher = NotificationDispatcher()


__all__ = ["NotificationDispatcher", "notification_dispatcher"]
