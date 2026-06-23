"""Notification type registry.

Defines the catalog of notification event codes, their categories, severity,
allowed actor types, default delivery channels, and broadcast flags. Every
event emitted through the dispatcher must resolve to a registered
:class:`NotificationTypeDef`.

Adding a new notification type means appending an entry to :data:`REGISTRY`;
the :class:`NotificationType` enum is generated from the registry keys so it
stays in sync automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Severity of a notification, drives UI color and routing priority."""

    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    URGENT = "urgent"


class ChannelKind(StrEnum):
    """Delivery channel identifier."""

    IN_APP = "in_app"
    TELEGRAM = "telegram"
    EMAIL = "email"


class NotificationCategory(StrEnum):
    """Top-level grouping shown as tabs in the notification bell."""

    CHANGE_ORDER = "change_order"
    AGENT = "agent"
    PROJECT = "project"
    DOCUMENT = "document"
    BRANCH = "branch"
    SYSTEM = "system"


class ActorType(StrEnum):
    """Who originated a notification event."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass(frozen=True)
class NotificationTypeDef:
    """Static definition of a notification event code.

    Attributes:
        code: Dotted event code (e.g. ``co.submitted``).
        label: Human-readable label for display.
        category: Bell tab grouping.
        severity: Default severity.
        actors: Actor types permitted to emit this code.
        default_channels: Channels used when a user has no explicit preference.
        resource_type: Resource type this event relates to, if any.
        broadcast: Whether the event fans out to all users (admin/system scope).
            Broadcast events bypass per-user preferences entirely.
        opt_in: Whether the event delivers only to users who have explicitly
            enabled it via their own notification preferences (default OFF).
            Opt-in events do no role/group resolution -- purely individual
            profile configuration. With default prefs (no enabled preference
            rows), an opt-in event delivers to nobody.
    """

    code: str
    label: str
    category: NotificationCategory
    severity: Severity
    actors: frozenset[ActorType]
    default_channels: tuple[ChannelKind, ...]
    resource_type: str | None = None
    broadcast: bool = False
    opt_in: bool = False


# Actor-type frozensets reused across definitions.
_USER_AGENT: frozenset[ActorType] = frozenset({ActorType.USER, ActorType.AGENT})
_SYSTEM: frozenset[ActorType] = frozenset({ActorType.SYSTEM})
_AGENT: frozenset[ActorType] = frozenset({ActorType.AGENT})
_USER: frozenset[ActorType] = frozenset({ActorType.USER})


def _def(
    code: str,
    label: str,
    category: NotificationCategory,
    severity: Severity,
    actors: frozenset[ActorType],
    default_channels: tuple[ChannelKind, ...],
    resource_type: str | None = None,
    broadcast: bool = False,
    opt_in: bool = False,
) -> NotificationTypeDef:
    """Build a :class:`NotificationTypeDef` (keeps the table below compact)."""
    return NotificationTypeDef(
        code=code,
        label=label,
        category=category,
        severity=severity,
        actors=actors,
        default_channels=default_channels,
        resource_type=resource_type,
        broadcast=broadcast,
        opt_in=opt_in,
    )


REGISTRY: dict[str, NotificationTypeDef] = {
    # ---- Change order ----
    "co.submitted": _def(
        "co.submitted",
        "Change order submitted",
        NotificationCategory.CHANGE_ORDER,
        Severity.NOTICE,
        _USER_AGENT,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "change_order",
    ),
    "co.approved": _def(
        "co.approved",
        "Change order approved",
        NotificationCategory.CHANGE_ORDER,
        Severity.NOTICE,
        _USER_AGENT,
        (ChannelKind.IN_APP,),
        "change_order",
    ),
    "co.rejected": _def(
        "co.rejected",
        "Change order rejected",
        NotificationCategory.CHANGE_ORDER,
        Severity.NOTICE,
        _USER_AGENT,
        (ChannelKind.IN_APP,),
        "change_order",
    ),
    "co.escalated": _def(
        "co.escalated",
        "Change order escalated",
        NotificationCategory.CHANGE_ORDER,
        Severity.URGENT,
        _SYSTEM,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "change_order",
    ),
    "co.sla_breach": _def(
        "co.sla_breach",
        "Change order SLA breach",
        NotificationCategory.CHANGE_ORDER,
        Severity.URGENT,
        _SYSTEM,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "change_order",
    ),
    "co.merged": _def(
        "co.merged",
        "Change order merged",
        NotificationCategory.CHANGE_ORDER,
        Severity.INFO,
        _USER_AGENT,
        (ChannelKind.IN_APP,),
        "change_order",
    ),
    # ---- Agent ----
    "agent.started": _def(
        "agent.started",
        "Agent started",
        NotificationCategory.AGENT,
        Severity.INFO,
        _AGENT,
        (ChannelKind.IN_APP,),
        "agent_execution",
    ),
    "agent.completed": _def(
        "agent.completed",
        "Agent completed",
        NotificationCategory.AGENT,
        Severity.NOTICE,
        _AGENT,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "agent_execution",
    ),
    "agent.failed": _def(
        "agent.failed",
        "Agent failed",
        NotificationCategory.AGENT,
        Severity.URGENT,
        _AGENT,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "agent_execution",
    ),
    "agent.ask_user": _def(
        "agent.ask_user",
        "Agent needs input",
        NotificationCategory.AGENT,
        Severity.NOTICE,
        _AGENT,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "agent_execution",
    ),
    "agent.approval_req": _def(
        "agent.approval_req",
        "Agent approval required",
        NotificationCategory.AGENT,
        Severity.URGENT,
        _AGENT,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "agent_execution",
    ),
    "agent.stopped": _def(
        "agent.stopped",
        "Agent stopped",
        NotificationCategory.AGENT,
        Severity.INFO,
        _USER_AGENT,
        (ChannelKind.IN_APP,),
        "agent_execution",
    ),
    "agent.message": _def(
        "agent.message",
        "Agent message",
        NotificationCategory.AGENT,
        Severity.INFO,
        _AGENT,
        (ChannelKind.IN_APP,),
        "agent_execution",
    ),
    "agent.notify": _def(
        "agent.notify",
        "Agent notification",
        NotificationCategory.AGENT,
        Severity.NOTICE,
        _USER_AGENT,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        None,
    ),
    # ---- Project / budget ----
    "budget.threshold": _def(
        "budget.threshold",
        "Budget threshold exceeded",
        NotificationCategory.PROJECT,
        Severity.URGENT,
        _SYSTEM,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        "project",
    ),
    # ---- Document ----
    "document.locked": _def(
        "document.locked",
        "Document locked",
        NotificationCategory.DOCUMENT,
        Severity.INFO,
        _USER,
        (ChannelKind.IN_APP,),
        "document",
    ),
    # ---- Branch ----
    "branch.merge_conflict": _def(
        "branch.merge_conflict",
        "Branch merge conflict",
        NotificationCategory.BRANCH,
        Severity.WARNING,
        _USER_AGENT,
        (ChannelKind.IN_APP,),
        "branch",
    ),
    # ---- System events ----
    # system.startup and system.user_login are opt-in: their recipients are
    # users who have explicitly enabled the event in their own notification
    # preferences (default OFF). No role/group resolution -- purely individual
    # profile configuration. default_channels stays (in_app, telegram) so both
    # channels remain configurable/shown in the preference UI for opting in.
    # system.unhandled_exception stays broadcast=True: a crash alert must never
    # be silenceable, so it always fires to the admin Telegram chat regardless
    # of any user preference.
    "system.startup": _def(
        "system.startup",
        "System startup",
        NotificationCategory.SYSTEM,
        Severity.INFO,
        _SYSTEM,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        None,
        opt_in=True,
    ),
    "system.unhandled_exception": _def(
        "system.unhandled_exception",
        "Unhandled exception",
        NotificationCategory.SYSTEM,
        Severity.URGENT,
        _SYSTEM,
        (ChannelKind.TELEGRAM,),
        None,
        broadcast=True,
    ),
    "system.user_login": _def(
        "system.user_login",
        "User login",
        NotificationCategory.SYSTEM,
        Severity.INFO,
        _SYSTEM,
        (ChannelKind.IN_APP, ChannelKind.TELEGRAM),
        None,
        opt_in=True,
    ),
}


class NotificationType(StrEnum):
    """Enumeration of every registered notification code.

    Members mirror the keys of :data:`REGISTRY` (member name = code upper-cased
    with dots replaced by underscores, e.g. ``co.submitted`` -> ``CO_SUBMITTED``).
    Defined explicitly for static type-safety; a runtime guard below asserts it
    stays in sync with the registry.
    """

    CO_SUBMITTED = "co.submitted"
    CO_APPROVED = "co.approved"
    CO_REJECTED = "co.rejected"
    CO_ESCALATED = "co.escalated"
    CO_SLA_BREACH = "co.sla_breach"
    CO_MERGED = "co.merged"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_ASK_USER = "agent.ask_user"
    AGENT_APPROVAL_REQ = "agent.approval_req"
    AGENT_STOPPED = "agent.stopped"
    AGENT_MESSAGE = "agent.message"
    AGENT_NOTIFY = "agent.notify"
    BUDGET_THRESHOLD = "budget.threshold"
    DOCUMENT_LOCKED = "document.locked"
    BRANCH_MERGE_CONFLICT = "branch.merge_conflict"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_UNHANDLED_EXCEPTION = "system.unhandled_exception"
    SYSTEM_USER_LOGIN = "system.user_login"


# Runtime guard: keep the explicit enum in lock-step with REGISTRY. If a code
# is added to REGISTRY without a matching enum member (or vice versa), this
# raises at import time so the drift is caught immediately.
_expected_codes = {member.value for member in NotificationType}
if _expected_codes != set(REGISTRY):
    _missing = set(REGISTRY) - _expected_codes
    _extra = _expected_codes - set(REGISTRY)
    raise RuntimeError(
        "NotificationType enum out of sync with REGISTRY "
        f"(missing members: {_missing}, unknown members: {_extra})"
    )


# Prefix -> category mapping for codes that may not be in the registry
# (e.g. legacy rows or future codes). Used by the preference/response layers
# to bucket an event code into a bell tab without a hard registry dependency.
_CATEGORY_PREFIXES: dict[str, NotificationCategory] = {
    "co": NotificationCategory.CHANGE_ORDER,
    "agent": NotificationCategory.AGENT,
    "budget": NotificationCategory.PROJECT,
    "document": NotificationCategory.DOCUMENT,
    "branch": NotificationCategory.BRANCH,
    "system": NotificationCategory.SYSTEM,
}


def category_for_code(code: str) -> NotificationCategory:
    """Return the bell-tab category for a dotted event *code*.

    Prefers the registry definition; falls back to a prefix match; defaults to
    :attr:`NotificationCategory.SYSTEM` for unknown codes.

    Args:
        code: Dotted event code (e.g. ``"co.submitted"``).

    Returns:
        The resolved :class:`NotificationCategory`.
    """
    type_def = REGISTRY.get(code)
    if type_def is not None:
        return type_def.category
    prefix = code.split(".", 1)[0]
    return _CATEGORY_PREFIXES.get(prefix, NotificationCategory.SYSTEM)


def get_type_def(code: str) -> NotificationTypeDef:
    """Return the :class:`NotificationTypeDef` for *code*.

    Args:
        code: Registered dotted event code.

    Returns:
        The matching type definition.

    Raises:
        ValueError: If *code* is not a registered notification type.
    """
    type_def = REGISTRY.get(code)
    if type_def is None:
        raise ValueError(f"Unknown notification type: {code!r}")
    return type_def


__all__ = [
    "REGISTRY",
    "ActorType",
    "ChannelKind",
    "NotificationCategory",
    "NotificationType",
    "NotificationTypeDef",
    "Severity",
    "category_for_code",
    "get_type_def",
]
