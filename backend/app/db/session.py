import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    str(settings.ASYNC_DATABASE_URI),
    echo=settings.LOG_LEVEL.upper() == "DEBUG",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_timeout=10,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Scoped session factory for concurrent AI tool execution
# Uses asyncio.current_task() as scopefunc to create task-local sessions
# This prevents "Session is already flushing" errors when LangGraph
# executes multiple tools concurrently
tool_scoped_session_factory = async_scoped_session(
    async_session_maker,
    scopefunc=asyncio.current_task,
)


def get_tool_session() -> AsyncSession:
    """Get or create a task-local session for AI tool execution.

    Uses async_scoped_session with asyncio.current_task as the scope function,
    ensuring each concurrent task gets its own AsyncSession instance.

    Returns:
        AsyncSession: Task-local session for the current asyncio task

    Note:
        The session is automatically scoped to the current task and will
        be reused within the same task. Call tool_scoped_session_factory.remove()
        to clean up the session when done.

        The session will start a transaction automatically on first use,
        so we don't need to explicitly begin one here.
    """
    return tool_scoped_session_factory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_pool_status() -> dict[str, int]:
    """Return connection pool utilization metrics.

    Returns:
        Dict with pool_size, checked_in, checked_out, overflow, and
        utilization_pct (checked_out / (pool_size + max_overflow) * 100).
    """
    from sqlalchemy.pool import QueuePool

    pool = engine.pool
    if not isinstance(pool, QueuePool):
        return {
            "pool_size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "max_capacity": 0,
            "utilization_pct": 0,
        }
    size = pool.size()
    checked_in = pool.checkedin()
    checked_out = pool.checkedout()
    overflow = pool.overflow()
    max_overflow = getattr(pool, "_max_overflow", 20)
    max_cap = size + max_overflow
    utilization_pct = round(checked_out / max_cap * 100) if max_cap else 0
    return {
        "pool_size": size,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "overflow": overflow,
        "max_capacity": max_cap,
        "utilization_pct": utilization_pct,
    }


def log_pool_status(context: str = "") -> None:
    """Log connection pool status with optional context label."""
    status = get_pool_status()
    if status["utilization_pct"] > 70:
        logger.warning(
            "[POOL_HIGH] %s | checked_out=%d/%d | overflow=%d | pct=%d%%",
            context,
            status["checked_out"],
            status["max_capacity"],
            status["overflow"],
            status["utilization_pct"],
        )
    else:
        logger.debug(
            "[POOL] %s | checked_out=%d/%d | overflow=%d",
            context,
            status["checked_out"],
            status["max_capacity"],
            status["overflow"],
        )


# --- Connection pool event listeners for diagnostics ---


@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(
    dbapi_conn: object, connection_record: object, connection_proxy: object
) -> None:
    logger.debug("[DB_CONN_CHECKOUT] conn_id=%d", id(connection_proxy))


@event.listens_for(engine.sync_engine, "checkin")
def _on_checkin(dbapi_conn: object, connection_record: object) -> None:
    logger.debug("[DB_CONN_CHECKIN]")


_query_start_times: dict[int, float] = {}


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(
    conn: object,
    cursor: object,
    statement: str,
    parameters: object,
    context: object,
    executemany: bool,
) -> None:
    if len(_query_start_times) > 500:
        _query_start_times.clear()
    _query_start_times[id(cursor)] = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(
    conn: object,
    cursor: object,
    statement: str,
    parameters: object,
    context: object,
    executemany: bool,
) -> None:
    cursor_id = id(cursor)
    start = _query_start_times.pop(cursor_id, None)
    if start is None:
        return
    duration_ms = (time.time() - start) * 1000
    stmt_short = statement[:120].replace("\n", " ")
    if duration_ms > 100:
        logger.warning(
            "[DB_SLOW_QUERY] %.0fms | %s",
            duration_ms,
            stmt_short,
        )
    elif duration_ms > 20:
        logger.info(
            "[DB_QUERY] %.0fms | %s",
            duration_ms,
            stmt_short,
        )
    else:
        logger.debug(
            "[DB_QUERY] %.0fms | %s",
            duration_ms,
            stmt_short,
        )
