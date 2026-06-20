"""Unified notification system.

Public API: the dispatcher (single funnel every notification passes through),
event emitters (user/agent/system entry points), the event/type enums, and the
user WebSocket connection manager.
"""

from app.core.notifications.connection_manager import (
    UserConnectionManager,
    user_connection_manager,
)
from app.core.notifications.dispatcher import (
    NotificationDispatcher,
    notification_dispatcher,
)
from app.core.notifications.emitter import (
    EventEmitter,
    agent_emitter,
    system_emitter,
    user_emitter,
)
from app.core.notifications.event import NotificationEvent
from app.core.notifications.registry import (
    ActorType,
    ChannelKind,
    NotificationCategory,
    NotificationType,
    Severity,
    category_for_code,
)

__all__ = [
    # Dispatcher.
    "NotificationDispatcher",
    "notification_dispatcher",
    # Emitters.
    "EventEmitter",
    "agent_emitter",
    "system_emitter",
    "user_emitter",
    # Event / enums.
    "NotificationEvent",
    "NotificationType",
    "Severity",
    "ActorType",
    "ChannelKind",
    "NotificationCategory",
    "category_for_code",
    # Connection manager.
    "UserConnectionManager",
    "user_connection_manager",
]
