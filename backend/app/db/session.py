import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    str(settings.ASYNC_DATABASE_URI),
    echo=settings.LOG_LEVEL.upper() == "DEBUG",
    pool_pre_ping=True,
    max_overflow=20,
    pool_size=10,
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
