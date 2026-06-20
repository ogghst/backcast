"""Event emitters - the entry point for any code that wants to notify.

Every domain service, agent execution, and lifespan handler emits through an
:class:`EventEmitter` (or a convenience helper) instead of touching the
dispatcher or persistence directly. Emitters are fire-and-forget-safe: any
error is logged and swallowed so notification failures can never break the
caller's business flow (matching the existing silent ``_send_notification``
semantics).

Helpers:
    - :func:`user_emitter` - construct an emitter for a user actor.
    - :func:`agent_emitter` - construct an emitter for an agent execution.
    - :data:`system_emitter` - module singleton for system/lifespan events.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications.dispatcher import notification_dispatcher
from app.core.notifications.event import NotificationEvent
from app.core.notifications.registry import ActorType, NotificationType, Severity

logger = logging.getLogger(__name__)


class EventEmitter:
    """Builds and dispatches :class:`NotificationEvent` objects.

    Args:
        actor_type: Originator type.
        actor_id: Originator identifier (user/agent id), if any.
        session: Caller's session. If ``None``, ``emit`` opens its own session
            (used by the system emitter, which has no request session).
    """

    def __init__(
        self,
        actor_type: ActorType,
        actor_id: UUID | None,
        session: AsyncSession | None,
    ) -> None:
        self._actor_type = actor_type
        self._actor_id = actor_id
        self._session = session

    async def emit(
        self,
        event_type: str | NotificationType,
        *,
        title: str,
        message: str,
        target_user_ids: list[UUID] | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        project_id: UUID | None = None,
        severity: Severity | None = None,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        """Dispatch a notification. Never raises into the caller.

        Args:
            event_type: Registered code or :class:`NotificationType` member.
            title: Short headline.
            message: Full body text.
            target_user_ids: Explicit recipients, else dispatcher resolves.
            resource_type: Related entity type, if any.
            resource_id: Related entity id, if any.
            project_id: Optional project scope.
            severity: Override; defaults to the registry type def severity.
            payload: Arbitrary structured context.
            idempotency_key: Optional dedup key.
        """
        try:
            code = (
                event_type.value
                if isinstance(event_type, NotificationType)
                else event_type
            )
            resolved_severity = severity or self._default_severity(code)

            event = NotificationEvent(
                event_type=code,
                actor_type=self._actor_type,
                actor_id=self._actor_id,
                target_user_ids=target_user_ids,
                resource_type=resource_type,
                resource_id=resource_id,
                project_id=project_id,
                title=title,
                message=message,
                severity=resolved_severity,
                payload=payload or {},
                idempotency_key=idempotency_key,
            )

            if self._session is not None:
                await notification_dispatcher.dispatch(event, self._session)
            else:
                # System emitter path: no request session, open our own.
                from app.db.session import async_session_maker

                async with async_session_maker() as session:
                    await notification_dispatcher.dispatch(event, session)
                    await session.commit()
        except Exception:
            logger.exception("Notification emission failed for event %r", event_type)

    def emit_fire_and_forget(
        self, event_type: str | NotificationType, **kwargs: Any
    ) -> None:
        """Schedule :meth:`emit` as a background task; never raises.

        Mirrors the retired ``notifier.send_fire_and_forget``. Used by callers
        that must not block on notification emission (the exception handler,
        the non-blocking login alert). Safe when no event loop is running
        (logs at debug and returns).

        Args:
            event_type: Registered code or :class:`NotificationType` member.
            **kwargs: Forwarded to :meth:`emit`.
        """
        try:
            asyncio.get_running_loop().create_task(self.emit(event_type, **kwargs))
        except RuntimeError:
            logger.debug("Cannot schedule notification emission: no running event loop")

    @staticmethod
    def _default_severity(code: str) -> Severity:
        """Return the registry severity for *code*, defaulting to INFO."""
        from app.core.notifications.registry import REGISTRY

        type_def = REGISTRY.get(code)
        return type_def.severity if type_def is not None else Severity.INFO


def user_emitter(actor_id: UUID, session: AsyncSession) -> EventEmitter:
    """Construct an emitter acting as a user."""
    return EventEmitter(ActorType.USER, actor_id, session)


def agent_emitter(execution_id: UUID | str, session: AsyncSession) -> EventEmitter:
    """Construct an emitter acting as an agent execution."""
    actor_id = (
        UUID(str(execution_id)) if isinstance(execution_id, str) else execution_id
    )
    return EventEmitter(ActorType.AGENT, actor_id, session)


# Module-level singleton for system events (lifespan, exception handler).
# Constructed with ``session=None`` so each ``emit`` opens its own short-lived
# session (system events fire outside any request context).
system_emitter: EventEmitter = EventEmitter(ActorType.SYSTEM, None, None)


__all__ = [
    "EventEmitter",
    "agent_emitter",
    "system_emitter",
    "user_emitter",
]
