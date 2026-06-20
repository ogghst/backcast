"""In-app notification channel.

Pushes a ``{"type":"notification", ...}`` frame to the recipient's open
WebSocket connections via :data:`user_connection_manager`. The badge-update
frame is pushed separately by the dispatcher (it needs the live unread count).

If the user is offline the send is a no-op (the notification is already
persisted and will appear on the next poll/refresh); the result is still
``sent`` because the in-app inbox write is the source of truth.
"""

from __future__ import annotations

from uuid import UUID

from app.core.notifications.channels.base import DeliveryResult
from app.core.notifications.connection_manager import user_connection_manager
from app.core.notifications.event import NotificationEvent
from app.core.notifications.registry import ChannelKind


class InAppChannel:
    """Pushes notification frames over the user's WebSocket connections."""

    kind = ChannelKind.IN_APP

    async def send(
        self,
        event: NotificationEvent,
        recipient_user_id: UUID | None,
        chat_id: str | None,  # noqa: ARG002 - unused by in-app
    ) -> DeliveryResult:
        """Deliver *event* as a WebSocket notification frame.

        Args:
            event: The notification event to deliver.
            recipient_user_id: Target user identifier, or ``None`` for
                broadcast/system events (in-app broadcasts are skipped by the
                dispatcher, so this channel is never invoked with ``None``).
            chat_id: Unused by the in-app channel.

        Returns:
            A ``sent`` :class:`DeliveryResult`.
        """
        # Broadcast/system events have no per-user recipient and are skipped
        # by the dispatcher's broadcast path; assert the invariant here for
        # type-narrowing (this channel always has a concrete recipient).
        assert recipient_user_id is not None
        payload = {
            "type": "notification",
            "notification": {
                # id/created_at come from the persisted Notification row; on the
                # bare event envelope they are unknown, so send what we have.
                "id": None,
                "title": event.title,
                "message": event.message,
                "event_type": event.event_type,
                "resource_type": event.resource_type,
                "resource_id": str(event.resource_id) if event.resource_id else None,
                "severity": event.severity.value,
                "created_at": None,
            },
        }
        await user_connection_manager.send_to_user(recipient_user_id, payload)
        return DeliveryResult(ChannelKind.IN_APP, "sent")

    async def shutdown(self) -> None:
        """No resources to release."""
        return None


__all__ = ["InAppChannel"]
