"""Notification tool for AI agents.

Exposes ``send_notification`` so the assistant can alert a user (the one it is
chatting with by default, or other users by UUID/email when authorized) via the
unified notification system. Delivery channels (in-app/Telegram) respect each
recipient's Profile preferences, so no frontend change is required.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.core.notifications import NotificationType, Severity, user_emitter
from app.services.user import UserService

logger = logging.getLogger(__name__)

# Hard cap on recipients per call to keep the fan-out bounded.
_MAX_RECIPIENTS = 20


@ai_tool(
    name="send_notification",
    description=(
        "Send a notification to the current user (default), or to other users "
        "by UUID or email. Use to alert about something the agent produced or "
        "noticed. By default notifies only the user you are chatting with. "
        "Notifying OTHER users requires authorization. Delivery channels "
        "(in-app/Telegram) respect each recipient's Profile preferences."
    ),
    permissions=[],  # RBAC enforced INSIDE the body so all roles can self-notify
    category="interaction",
    risk_level=RiskLevel.LOW,
)
async def send_notification(
    message: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
    *,
    title: str | None = None,
    recipients: list[str] | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    """Send a notification to one or more users.

    With no ``recipients`` (or only the current user) this always succeeds and
    needs no extra permission, so any role can self-notify. Notifying other
    users requires the ``notifications-send`` permission (checked at runtime).
    The emitter is fire-and-forget (it swallows dispatch errors), so success is
    reported even if a delivery channel fails silently.

    Args:
        message: Notification body text.
        context: Injected tool execution context (provides session + user).
        title: Optional headline; defaults to ``"Notification"``.
        recipients: Optional list of user UUIDs or emails. Defaults to the
            current user. Duplicate entries are de-duplicated (order preserved).
        severity: Optional severity override (``info``/``notice``/``warning``/
            ``urgent``); unknown values fall back to ``notice``.

    Returns:
        On success, ``{"sent": True, "count": N, "self_only": bool,
        "recipients": [{"user_id": "..."}, ...]}``. On any failure, an
        ``{"error": "..."}`` dict (which also rolls back the tool session).
    """
    try:
        current_user = UUID(context.user_id)
        user_service = UserService(context.session)

        # ---- Resolve recipients ----
        targets: list[UUID] = []
        unresolved: list[str] = []

        if not recipients:
            targets = [current_user]
        else:
            # De-duplicate while preserving first-seen order.
            seen: set[UUID] = set()
            for entry in recipients:
                resolved: UUID | None = None
                try:
                    candidate = UUID(entry)
                except (ValueError, TypeError, AttributeError):
                    # Not a UUID -> treat as an email lookup.
                    user = await user_service.get_by_email(entry)
                    if user is not None:
                        resolved = user.user_id
                else:
                    user = await user_service.get_user(candidate)
                    if user is not None:
                        resolved = candidate

                if resolved is None:
                    unresolved.append(entry)
                elif resolved not in seen:
                    seen.add(resolved)
                    targets.append(resolved)

            if unresolved:
                return {"error": f"Unresolved recipients: {unresolved}"}

            if len(targets) > _MAX_RECIPIENTS:
                return {"error": f"Too many recipients (max {_MAX_RECIPIENTS})"}

        self_only = targets == [current_user]

        # ---- Authorization for cross-user sends ----
        if not self_only:
            allowed = await context.check_permission("notifications-send")
            if not allowed:
                return {"error": "Not authorized to send notifications to other users"}

        # ---- Severity mapping ----
        try:
            sev = Severity((severity or "notice").lower())
        except (ValueError, KeyError):
            sev = Severity.NOTICE

        # ---- Emit (fire-and-forget; never raises into us) ----
        emitter = user_emitter(current_user, context.session)
        await emitter.emit(
            NotificationType.AGENT_NOTIFY,
            title=title or "Notification",
            message=message,
            target_user_ids=targets,
            project_id=(UUID(context.project_id) if context.project_id else None),
            severity=sev,
            payload={"via": "ai_tool"},
        )

        return {
            "sent": True,
            "count": len(targets),
            "self_only": self_only,
            "recipients": [{"user_id": str(t)} for t in targets],
        }
    except Exception as e:
        logger.error("Error in send_notification: %s", e, exc_info=True)
        return {"error": str(e)}
