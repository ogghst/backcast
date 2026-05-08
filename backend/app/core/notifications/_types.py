"""Notification event types and payload structure."""

from enum import StrEnum
from typing import Any


class NotificationEvent(StrEnum):
    """Events that trigger admin notifications.

    Extend by adding new members.
    """

    SYSTEM_STARTUP = "system_startup"
    UNHANDLED_EXCEPTION = "unhandled_exception"
    USER_LOGIN = "user_login"

    # CO workflow events
    CO_SUBMITTED = "co_submitted"
    CO_APPROVED = "co_approved"
    CO_REJECTED = "co_rejected"
    CO_ESCALATED = "co_escalated"
    CO_STATUS_CHANGED = "co_status_changed"


class NotificationPayload:
    """Lightweight payload passed to the notifier."""

    __slots__ = ("event", "message", "details")

    def __init__(
        self,
        event: NotificationEvent,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.event = event
        self.message = message
        self.details = details or {}
