"""Scheduler process entry point.

Owns its own small async engine + sessionmaker (NOT the API server's larger
pool) and a single long-lived ``httpx.AsyncClient``. Wakes every
``SCHEDULER_POLL_INTERVAL_SECONDS``, runs one ``tick()``, and shuts down
gracefully on SIGTERM/SIGINT.

Deliberately does NOT import ``app.main`` or run the FastAPI lifespan — the
scheduler is fully independent of the API server runtime.
"""

import asyncio
import logging
import signal

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import setup_logging
from app.scheduler.tick import tick

logger = logging.getLogger(__name__)


def main() -> None:
    """Configure logging and run the scheduler loop until interrupted."""
    setup_logging()
    asyncio.run(run_loop())


async def run_loop() -> None:
    """Poll loop: tick every ``SCHEDULER_POLL_INTERVAL_SECONDS`` until stopped."""
    engine = create_async_engine(
        str(settings.ASYNC_DATABASE_URI),
        pool_pre_ping=True,
        pool_size=settings.SCHEDULER_DB_POOL_SIZE,
        max_overflow=5,
        pool_recycle=300,
        pool_timeout=30,
    )
    sessionmaker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    client = httpx.AsyncClient()

    stop = asyncio.Event()
    _install_signal_handlers(stop)

    try:
        # Single-instance guard: a session-level advisory lock held for the
        # process lifetime via a checked-out connection. If another scheduler
        # already holds it, exit (prevents accidental multi-instance dispatch).
        # The lock auto-releases when this connection closes on shutdown.
        async with engine.connect() as guard_conn:
            acquired = (
                await guard_conn.execute(
                    text("SELECT pg_try_advisory_lock(hashtext(:k))"),
                    {"k": "backcast-scheduler"},
                )
            ).scalar()
            if not acquired:
                logger.error(
                    "[scheduler] another scheduler instance holds the lock; exiting"
                )
                return

            logger.info(
                "[scheduler] started (poll=%ds, max_concurrency=%d, grace=%ds, "
                "api_base=%s)",
                settings.SCHEDULER_POLL_INTERVAL_SECONDS,
                settings.SCHEDULER_MAX_CONCURRENCY,
                settings.SCHEDULER_MISFIRE_GRACE_SECONDS,
                settings.SCHEDULER_API_BASE_URL,
            )

            while not stop.is_set():
                try:
                    await tick(sessionmaker, client)
                except Exception:
                    logger.exception("[scheduler] tick failed")

                try:
                    await asyncio.wait_for(
                        stop.wait(), timeout=settings.SCHEDULER_POLL_INTERVAL_SECONDS
                    )
                except TimeoutError:
                    pass
    finally:
        logger.info("[scheduler] shutting down")
        await client.aclose()
        await engine.dispose()
        logger.info("[scheduler] stopped")


def _install_signal_handlers(stop: asyncio.Event) -> None:
    """Register SIGTERM/SIGINT to set the stop event (graceful shutdown)."""

    def _on_signal(name: str) -> None:
        logger.info("[scheduler] received %s; stopping after current tick", name)
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            # add_signal_handler takes a no-arg callable (preferred on Linux).
            loop.add_signal_handler(sig, _on_signal, sig.name)
        except NotImplementedError:
            # Unsupported on Windows/prohibited loops — fall back to stdlib.
            # Default-arg binds sig eagerly (avoids late-binding closure bug).
            def _stdlib_handler(
                _signum: int, _frame: object, *, name: str = sig.name
            ) -> None:
                _on_signal(name)

            signal.signal(sig, _stdlib_handler)
