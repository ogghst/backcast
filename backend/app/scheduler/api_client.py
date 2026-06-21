"""HTTP client for the scheduler to call the backend trigger endpoint.

The scheduler mints a short-lived JWT with the shared ``SECRET_KEY``,
authenticated as the schedule's owner, and POSTs the trigger endpoint. The
backend owns the actual agent execution (in-memory lifecycle/event-bus
singletons live there).
"""

import logging
from datetime import timedelta
from uuid import UUID

import httpx

from app.core.config import settings
from app.core.security import create_access_token

logger = logging.getLogger(__name__)

# Short-lived JWT for the scheduler-as-owner. 5 min is plenty — the request
# itself has a 10s timeout, and the token only needs to survive one POST.
_TRIGGER_TOKEN_TTL_SECONDS = 300


async def trigger_schedule(
    client: httpx.AsyncClient, schedule_id: UUID, owner_user_id: UUID
) -> bool:
    """POST the backend trigger endpoint as the schedule owner.

    Returns ``True`` if the fire window is HANDLED (the caller may advance
    ``next_run_at``): a 2xx launch, or 409/403/404 (overlap / revoked role /
    schedule gone — retrying won't help). Returns ``False`` to RETRY (backend
    unreachable, timeout, or an unexpected 5xx) so the caller leaves
    ``next_run_at`` in the past for the next tick. Never raises.
    """
    token = create_access_token(
        subject=str(owner_user_id),
        expires_delta=timedelta(seconds=_TRIGGER_TOKEN_TTL_SECONDS),
    )
    url = (
        f"{settings.SCHEDULER_API_BASE_URL}"
        f"{settings.API_V1_STR}/ai/agent-schedules/{schedule_id}/trigger"
    )
    try:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        # Backend down / unreachable — retry on the next tick.
        logger.warning(
            "[scheduler] trigger POST failed for schedule %s: %s",
            schedule_id,
            exc,
        )
        return False

    if 200 <= resp.status_code < 300:
        logger.info(
            "[scheduler] triggered schedule %s (status=%s)",
            schedule_id,
            resp.status_code,
        )
        return True

    # 409 (overlap — previous run still active), 403 (owner role revoked),
    # 404 (schedule/config deleted): handled — no point retrying.
    if resp.status_code in (409, 403, 404):
        logger.info(
            "[scheduler] trigger for schedule %s returned %s (handled)",
            schedule_id,
            resp.status_code,
        )
        return True

    logger.warning(
        "[scheduler] trigger for schedule %s returned unexpected status %s: %s",
        schedule_id,
        resp.status_code,
        resp.text[:200],
    )
    return False
