"""Tests for task-local session isolation using async_scoped_session.

This test module verifies that:
1. Each concurrent asyncio task gets its own AsyncSession instance
2. Sessions are properly scoped to the current task
3. Session cleanup works correctly after task completion
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_tool_session, tool_scoped_session_factory


class TestTaskLocalSession:
    """Test task-local session isolation using async_scoped_session."""

    @pytest.mark.asyncio
    async def test_get_tool_session_returns_scoped_session(self) -> None:
        """Test that get_tool_session returns an AsyncSession instance."""
        session = get_tool_session()
        assert isinstance(session, AsyncSession)

        # Clean up the scoped session
        await tool_scoped_session_factory.remove()

    @pytest.mark.asyncio
    async def test_concurrent_tasks_get_different_sessions(self) -> None:
        """Test that concurrent tasks get different AsyncSession instances.

        This is the core fix for the "Session is already flushing" error.
        When LangGraph executes tools concurrently, each tool should get
        its own isolated session.
        """
        session_ids = []

        async def task_a() -> None:
            """First concurrent task."""
            session = get_tool_session()
            session_ids.append(id(session))
            # Simulate some async work
            await asyncio.sleep(0.01)

        async def task_b() -> None:
            """Second concurrent task."""
            session = get_tool_session()
            session_ids.append(id(session))
            # Simulate some async work
            await asyncio.sleep(0.01)

        async def task_c() -> None:
            """Third concurrent task."""
            session = get_tool_session()
            session_ids.append(id(session))
            # Simulate some async work
            await asyncio.sleep(0.01)

        # Execute tasks concurrently
        await asyncio.gather(task_a(), task_b(), task_c())

        # Verify all tasks got different session IDs
        assert len(session_ids) == 3
        assert len(set(session_ids)) == 3, "Each task should get a unique session"

    @pytest.mark.asyncio
    async def test_same_task_reuses_session(self) -> None:
        """Test that the same task reuses its session."""
        session_1 = get_tool_session()
        session_2 = get_tool_session()

        # Both calls in the same task should return the same session
        assert id(session_1) == id(session_2)

        # Clean up
        await tool_scoped_session_factory.remove()

    @pytest.mark.asyncio
    async def test_nested_tasks_get_different_sessions(self) -> None:
        """Test that tasks created with asyncio.create_task get different sessions."""
        outer_session = get_tool_session()
        outer_id = id(outer_session)

        async def inner_task() -> int:
            """Inner task that gets its own session."""
            inner_session = get_tool_session()
            inner_id = id(inner_session)
            await tool_scoped_session_factory.remove()
            return inner_id

        # Create a new task (this creates a new asyncio.current_task context)
        task = asyncio.create_task(inner_task())
        inner_id = await task

        # Sessions should be different because create_task creates a new task context
        assert outer_id != inner_id, "Created task should get a different session"

        # Clean up outer session
        await tool_scoped_session_factory.remove()

    @pytest.mark.asyncio
    async def test_session_cleanup_after_remove(self) -> None:
        """Test that remove() cleans up the scoped session."""
        # Get a session
        session_1 = get_tool_session()
        session_1_id = id(session_1)

        # Remove it
        await tool_scoped_session_factory.remove()

        # Get a new session - should be a different instance
        session_2 = get_tool_session()
        session_2_id = id(session_2)

        assert session_1_id != session_2_id, (
            "New session should be created after remove"
        )

        # Clean up
        await tool_scoped_session_factory.remove()

    @pytest.mark.asyncio
    async def test_concurrent_create_wbe_simulation(self) -> None:
        """Simulate concurrent create_wbe tool executions.

        This test simulates the scenario that was causing the
        "Session is already flushing" error - multiple tools creating
        WBEs concurrently.
        """
        created_wbes = []
        errors = []

        async def simulate_create_wbe(wbe_name: str, delay: float) -> None:
            """Simulate a create_wbe tool execution."""
            try:
                # Get task-local session for this tool execution
                session = get_tool_session()
                session_id = id(session)

                # Simulate database operation with flush
                await asyncio.sleep(delay)

                # Record the "created" WBE
                created_wbes.append({"name": wbe_name, "session_id": session_id})

                # Clean up session (simulates commit in decorator)
                await tool_scoped_session_factory.remove()
            except Exception as e:
                errors.append(e)

        # Execute 5 concurrent create_wbe operations
        # This mimics what happens when LangGraph executes tools in parallel
        await asyncio.gather(
            simulate_create_wbe("WBE-001", 0.01),
            simulate_create_wbe("WBE-002", 0.015),
            simulate_create_wbe("WBE-003", 0.02),
            simulate_create_wbe("WBE-004", 0.025),
            simulate_create_wbe("WBE-005", 0.03),
        )

        # Verify all WBEs were created successfully
        assert len(created_wbes) == 5, "All 5 WBEs should be created"
        assert len(errors) == 0, f"No errors should occur, got: {errors}"

        # Verify each WBE got its own session
        session_ids = {wbe["session_id"] for wbe in created_wbes}
        assert len(session_ids) == 5, "Each WBE should have its own unique session"

    @pytest.mark.asyncio
    async def test_scoped_session_factory_integration(self) -> None:
        """Test that tool_scoped_session_factory works with asyncio.current_task."""
        from app.db.session import get_tool_session, tool_scoped_session_factory

        # Get session in current task
        session_1 = tool_scoped_session_factory()
        session_2 = get_tool_session()

        # Should be the same session (same task)
        assert id(session_1) == id(session_2)

        # Clean up
        await tool_scoped_session_factory.remove()
