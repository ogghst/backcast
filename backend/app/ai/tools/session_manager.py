"""Session lifecycle management for concurrent AI tool execution.

This module provides the ToolSessionManager class for managing commit/rollback
operations on task-local sessions created by async_scoped_session.
"""


from app.db.session import tool_scoped_session_factory


class ToolSessionManager:
    """Manages commit/rollback for task-local sessions.

    The ToolSessionManager provides static methods for committing or rolling
    back the current task's session. Each concurrent tool execution gets its
    own scoped session via async_scoped_session with asyncio.current_task,
    and this manager handles the lifecycle of those sessions.

    Example:
        ```python
        try:
            result = await graph.ainvoke(input_data)
            await ToolSessionManager.commit()
        except Exception:
            await ToolSessionManager.rollback()
            raise
        ```

    Note:
        After commit() or rollback(), the scoped session is removed from the
        current task context, allowing a new session to be created on the next
        get_tool_session() call.
    """

    @staticmethod
    async def commit() -> None:
        """Commit the current task's session.

        Commits the transaction if one is active, then removes the scoped
        session from the current task context. This ensures clean session
        lifecycle management for concurrent tool executions.

        Raises:
            SQLAlchemyError: If the commit operation fails
        """
        session = tool_scoped_session_factory()
        if session.in_transaction():
            await session.commit()
        await tool_scoped_session_factory.remove()

    @staticmethod
    async def rollback() -> None:
        """Rollback the current task's session.

        Rolls back the transaction if one is active, then removes the scoped
        session from the current task context. This ensures clean session
        lifecycle management when tool execution fails.

        Note:
            This is safe to call even if no transaction is active.
        """
        session = tool_scoped_session_factory()
        if session.in_transaction():
            await session.rollback()
        await tool_scoped_session_factory.remove()
