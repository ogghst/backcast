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
