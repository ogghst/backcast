"""Channel protocol and delivery result.

A channel is an outbound transport (in-app WebSocket push, Telegram HTTP,
email, ...). The dispatcher owns channel instances and calls :meth:`Channel.send`
once per (notification, recipient) pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from app.core.notifications.event import NotificationEvent
from app.core.notifications.registry import ChannelKind

DeliveryStatus = Literal["sent", "failed", "skipped", "dropped"]


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of a single channel delivery attempt.

    Attributes:
        channel: Which channel produced this result.
        status: ``sent`` on success, ``failed`` on error, ``skipped`` when the
            channel intentionally did not send (e.g. no chat id), ``dropped``
            when suppressed by policy.
        error: Human-readable error text when ``status == "failed"``.
    """

    channel: ChannelKind
    status: DeliveryStatus
    error: str | None = None


@runtime_checkable
class Channel(Protocol):
    """Outbound notification transport.

    Implementations must expose :attr:`kind` and the two async methods below.
    """

    kind: ChannelKind

    async def send(
        self,
        event: NotificationEvent,
        recipient_user_id: UUID | None,
        chat_id: str | None,
    ) -> DeliveryResult:
        """Deliver *event* to *recipient_user_id*.

        Args:
            event: The notification event to deliver.
            recipient_user_id: Target user identifier, or ``None`` for
                broadcast/system events that have no per-user recipient.
            chat_id: Transport-specific address (e.g. Telegram chat id) when
                known, otherwise ``None``.

        Returns:
            A :class:`DeliveryResult` describing the attempt.
        """
        ...

    async def shutdown(self) -> None:
        """Release resources (HTTP clients, connections)."""
        ...


__all__ = [
    "Channel",
    "DeliveryResult",
    "DeliveryStatus",
]
