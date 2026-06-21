"""In-process scheduler loop — runs as a lifespan background task in the API
server (the same process that owns the in-memory ``ExecutionLifecycle`` /
event-bus). Polls the shared DB every ``SCHEDULER_POLL_INTERVAL_SECONDS`` and
fires due schedules via :func:`trigger_schedule_run` (a direct in-process call;
the run launches fire-and-forget in this process).

Start/stop is owned by the FastAPI lifespan in ``app/main.py`` — call
:func:`run_scheduler_loop` as an ``asyncio.create_task`` and set the ``stop``
event on shutdown.
"""

import asyncio
import logging

from app.core.config import settings
from app.scheduler.tick import tick

logger = logging.getLogger(__name__)


async def run_scheduler_loop(stop: asyncio.Event) -> None:
    """Tick every ``SCHEDULER_POLL_INTERVAL_SECONDS`` until ``stop`` is set.

    Uses the API server's shared DB engine (no separate pool). Each tick is
    wrapped so a failure never aborts the loop.
    """
    from app.db.session import async_session_maker

    logger.info(
        "[scheduler] started (poll=%ds, max_concurrency=%d, grace=%ds)",
        settings.SCHEDULER_POLL_INTERVAL_SECONDS,
        settings.SCHEDULER_MAX_CONCURRENCY,
        settings.SCHEDULER_MISFIRE_GRACE_SECONDS,
    )
    while not stop.is_set():
        try:
            await tick(async_session_maker)
        except Exception:
            logger.exception("[scheduler] tick failed")
        try:
            await asyncio.wait_for(
                stop.wait(), timeout=settings.SCHEDULER_POLL_INTERVAL_SECONDS
            )
        except TimeoutError:
            pass
    logger.info("[scheduler] stopped")
