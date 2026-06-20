"""Notification event payload.

A :class:`NotificationEvent` is the value object every emitter constructs and
hands to the dispatcher. It is deliberately a plain dataclass (no DB coupling)
so it can flow through services, tools, and lifespan code without a session.

``Notification.created_at`` remains the source of truth for timestamps; no
timestamp is carried on the event itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.notifications.registry import (
    ActorType,
    ChannelKind,
    Severity,
)


@dataclass(frozen=True)
class NotificationEvent:
    """Immutable description of one notification to dispatch.

    Attributes:
        event_type: Registered dotted code (e.g. ``co.submitted``).
        actor_type: Who emitted the event.
        actor_id: Identifier of the actor (user/agent id), if applicable.
        target_user_ids: Explicit recipient list; ``None`` lets the dispatcher
            resolve targets (broadcast or resource-owner fallback).
        resource_type: Type of the related domain entity, if any.
        resource_id: Identifier of the related entity, if any.
        project_id: Optional project scope for grouping/filtering.
        title: Short headline.
        message: Full body text.
        severity: Severity (defaults to INFO; emitter may override).
        payload: Arbitrary structured context for channels/UI.
        idempotency_key: Optional key; an unread notification with the same
            ``(user_id, idempotency_key)`` suppresses a duplicate persist.
    """

    event_type: str
    actor_type: ActorType
    actor_id: UUID | None
    target_user_ids: list[UUID] | None
    resource_type: str | None
    resource_id: UUID | None
    project_id: UUID | None
    title: str
    message: str
    severity: Severity = Severity.INFO
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None


__all__ = [
    "ChannelKind",
    "NotificationEvent",
]
