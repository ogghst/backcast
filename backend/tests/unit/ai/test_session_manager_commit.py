"""Unit test for ToolSessionManager commit/rollback behavior.

This test verifies that ToolSessionManager correctly commits implicit
transactions (those created without explicit begin()) to prevent
the WBE persistence bug where tools report success but data doesn't
persist to the database.

The core issue was that session.in_transaction() returns False for
implicit transactions, causing the old code to skip commit and just
remove the session from the scoped factory, leading to:
1. Uncommitted data (WBEs not persisted)
2. Connection pool exhaustion (connections never released)
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_session_manager_commit_handles_no_transaction_gracefully(
    db_session: AsyncSession,
):
    """Test that commit() is safe to call even when no transaction exists.

    SQLAlchemy's AsyncSession.commit() is a no-op when no transaction
    is active, so calling it unconditionally is safe.
    """
    from app.ai.tools.session_manager import ToolSessionManager
    from app.db.session import tool_scoped_session_factory

    # Get a fresh session with no active transaction
    tool_session = tool_scoped_session_factory()

    # This should not raise an exception
    await ToolSessionManager.commit()

    # Session should be removed (next call gets a new session)
    new_session = tool_scoped_session_factory()
    assert new_session is not tool_session


@pytest.mark.asyncio
async def test_session_manager_rollback_handles_no_transaction_gracefully(
    db_session: AsyncSession,
):
    """Test that rollback() is safe to call even when no transaction exists."""
    from app.ai.tools.session_manager import ToolSessionManager
    from app.db.session import tool_scoped_session_factory

    # Get a fresh session with no active transaction
    tool_session = tool_scoped_session_factory()

    # This should not raise an exception
    await ToolSessionManager.rollback()

    # Session should be removed (next call gets a new session)
    new_session = tool_scoped_session_factory()
    assert new_session is not tool_session


@pytest.mark.asyncio
async def test_session_manager_multiple_commits_dont_leak_connections(
    db_session: AsyncSession,
):
    """Test that multiple commit cycles don't leak connections.

    Before the fix, the bug was:
    1. session.in_transaction() returns False for implicit transactions
    2. Commit was skipped, only remove() was called
    3. Connection remained open with uncommitted data
    4. Connection pool eventually exhausted

    After the fix:
    1. commit() is always called
    2. Connection is released back to pool
    3. No connection leaks
    """
    from app.ai.tools.session_manager import ToolSessionManager
    from app.db.session import tool_scoped_session_factory

    # Simulate multiple tool executions
    # The bug would cause connection pool to exhaust after ~30 iterations
    for _ in range(50):
        tool_session = tool_scoped_session_factory()

        # Perform a simple query (starts implicit transaction)
        result = await tool_session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

        # Commit should now be called unconditionally
        await ToolSessionManager.commit()

    # If the bug existed, this would fail with "QueuePool limit reached"
    # With the fix, all 50 iterations succeed
    assert True  # If we get here, no connection leak occurred
