"""Integration test for concurrent AI tool execution.

This test verifies that the task-local session fix resolves the
"Session is already flushing" error when LangGraph executes
multiple AI tools concurrently.
"""

import asyncio
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools import ToolContext
from app.ai.tools.decorator import ai_tool
from app.db.session import get_tool_session, tool_scoped_session_factory
from app.models.schemas.project import ProjectCreate
from app.services.project import ProjectService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_create_wbe_tools(db_session: AsyncSession) -> None:
    """Test that concurrent create_wbe tool executions work correctly.

    This test simulates the exact scenario that was causing the
    "Session is already flushing" error - multiple tools creating
    WBEs concurrently in response to a single AI chat message.

    The fix uses async_scoped_session with asyncio.current_task
    to ensure each concurrent tool gets its own isolated session.

    NOTE: This test uses a simplified tool that directly creates WBE objects
    in the database rather than using the full create_wbe tool, which requires
    a committed project to be visible across sessions (not possible in the
    test's wrapped transaction).
    """
    # Track created WBE IDs and any errors
    created_wbe_ids = []
    errors = []

    # Define a simple test tool that creates a WBE-like entity
    # This simulates the concurrent tool execution pattern
    @ai_tool(
        name="test_create_wbe",
        description="Test tool for creating WBE",
        permissions=["wbe-create"],
    )
    async def test_create_wbe(
        name: str,
        code: str,
        context: ToolContext,
    ) -> dict[str, Any]:
        """Create a test WBE entity.

        This is a simplified version of create_wbe that directly
        inserts into the database to test concurrent session isolation.

        Args:
            name: The WBE name
            code: The WBE code
            context: Tool execution context

        Returns:
            A dictionary with the created WBE's ID and session ID
        """
        try:
            from app.models.domain.wbe import WBE

            # Get task-local session
            session = get_tool_session()

            # Create a new WBE entity
            wbe_id = uuid4()
            project_id = UUID(context.project_id) if context.project_id else uuid4()

            wbe = WBE(
                id=uuid4(),
                wbe_id=wbe_id,
                project_id=project_id,
                name=name,
                code=code,
                level=1,
                branch="main",
                created_by=UUID(context.user_id),
            )

            session.add(wbe)

            # Flush to make it visible in this session's transaction
            await session.flush()

            return {
                "id": str(wbe_id),
                "name": name,
                "code": code,
                "session_id": id(session),
            }
        except Exception as e:
            import traceback

            return {"error": f"{str(e)}\n{traceback.format_exc()}"}

    async def simulate_concurrent_tool_execution(wbe_name: str, index: int) -> None:
        """Simulate a concurrent tool execution.

        Each execution is wrapped in an asyncio task to simulate
        LangGraph's concurrent tool execution.
        """
        try:
            # Use a shared project_id for all WBEs
            project_id = str(uuid4())

            # Create a ToolContext for this execution
            _tool_context = ToolContext(
                session=db_session,  # Used as _root_session
                user_id=str(uuid4()),
                user_role="admin",
                project_id=project_id,
            )

            # The tool will use the task-local session via ToolContext.session
            result = await test_create_wbe.ainvoke(
                {
                    "name": wbe_name,
                    "code": f"WBE-{index:03d}",
                    "context": _tool_context,
                }
            )

            # Check for errors in result
            if isinstance(result, dict) and "error" in result:
                errors.append(f"{wbe_name}: {result['error']}")
            else:
                created_wbe_ids.append(result.get("id"))
                print(f"Created {wbe_name}: session_id={result.get('session_id')}")

        except Exception as e:
            import traceback

            errors.append(f"{wbe_name}: {str(e)}\n{traceback.format_exc()}")
        finally:
            # Clean up task-local session
            await tool_scoped_session_factory.remove()

    # Execute 5 concurrent create_wbe operations
    # This is exactly what was happening in the production error
    await asyncio.gather(
        simulate_concurrent_tool_execution("WBE-001", 1),
        simulate_concurrent_tool_execution("WBE-002", 2),
        simulate_concurrent_tool_execution("WBE-003", 3),
        simulate_concurrent_tool_execution("WBE-004", 4),
        simulate_concurrent_tool_execution("WBE-005", 5),
    )

    # Verify no "Session is already flushing" errors occurred
    assert len(errors) == 0, f"No errors should occur, got: {errors}"

    # Verify all WBEs were created successfully
    assert len(created_wbe_ids) == 5, (
        f"All 5 WBEs should be created, got {len(created_wbe_ids)}"
    )

    # The key verification: we executed 5 concurrent tools without
    # the "Session is already flushing" error that would occur with
    # a shared session. Each tool got its own task-local session.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_session_isolation(db_session: AsyncSession) -> None:
    """Test that each tool execution gets its own session.

    This verifies that the async_scoped_session is working correctly
    by checking that session IDs differ between concurrent executions.
    """
    # Create a project
    project_service = ProjectService(db_session)
    project = await project_service.create_project(
        ProjectCreate(
            name=f"Test Project {uuid4()}",
            code="TEST-SESSION",
            description="Test project for session isolation",
            budget=Decimal("1000000.00"),
        ),
        actor_id=uuid4(),
    )

    _tool_context = ToolContext(
        session=db_session,
        user_id=str(uuid4()),
        user_role="admin",
        project_id=str(project.project_id),
    )

    # Track session IDs used by each tool execution
    session_ids = []

    async def track_tool_session(wbe_name: str, index: int) -> None:
        """Execute tool and track the session ID it uses."""
        from app.db.session import get_tool_session, tool_scoped_session_factory

        # Get the task-local session
        session = get_tool_session()
        session_ids.append(id(session))

        # Simulate tool work
        await asyncio.sleep(0.01)

        # Clean up
        await tool_scoped_session_factory.remove()

    # Execute tasks concurrently
    await asyncio.gather(
        track_tool_session("WBE-001", 1),
        track_tool_session("WBE-002", 2),
        track_tool_session("WBE-003", 3),
    )

    # Verify each task got a unique session
    assert len(set(session_ids)) == 3, (
        "Each concurrent execution should get a unique session"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_cleanup_after_tool_execution(db_session: AsyncSession) -> None:
    """Test that sessions are properly cleaned up after tool execution.

    This verifies that ToolSessionManager.commit() and .rollback()
    properly clean up the scoped session.
    """
    from app.ai.tools.session_manager import ToolSessionManager
    from app.db.session import tool_scoped_session_factory

    # Create a tool context
    _tool_context = ToolContext(
        session=db_session,
        user_id=str(uuid4()),
        user_role="admin",
    )

    # Execute a tool-like operation
    session_1 = tool_scoped_session_factory()
    session_1_id = id(session_1)

    # Commit (simulating successful tool execution)
    await ToolSessionManager.commit()

    # Get a new session - should be different
    session_2 = tool_scoped_session_factory()
    session_2_id = id(session_2)

    assert session_1_id != session_2_id, "New session should be created after commit"

    # Clean up
    await ToolSessionManager.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_with_scoped_sessions(db_session: AsyncSession) -> None:
    """Test that errors in tool execution properly roll back scoped sessions.

    This verifies that the ToolSessionManager.rollback() works correctly.
    """
    from app.ai.tools.session_manager import ToolSessionManager
    from app.db.session import tool_scoped_session_factory

    _tool_context = ToolContext(
        session=db_session,
        user_id=str(uuid4()),
        user_role="admin",
    )

    # Simulate tool execution with error
    session = tool_scoped_session_factory()
    session_id_before = id(session)

    # Rollback (simulating error)
    await ToolSessionManager.rollback()

    # Get a new session after rollback
    session_after = tool_scoped_session_factory()
    session_id_after = id(session_after)

    assert session_id_before != session_id_after, (
        "New session should be created after rollback"
    )

    # Clean up
    await ToolSessionManager.rollback()
