"""Tests for database utility functions."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import is_transaction_aborted, safe_db_execute


@pytest.mark.asyncio
async def test_safe_db_execute_success(db_session: AsyncSession):
    """Test safe_db_execute with successful query."""

    async def mock_query():
        return await db_session.execute(text("SELECT 1"))

    result = await safe_db_execute(db_session, mock_query(), "Test query")
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_safe_db_execute_with_error(db_session: AsyncSession):
    """Test safe_db_execute handles errors and rolls back."""

    # Create a query that will fail
    async def failing_query():
        return await db_session.execute(text("SELECT * FROM nonexistent_table"))

    with pytest.raises(ValueError, match="Failed query"):
        await safe_db_execute(db_session, failing_query(), "Failed query")

    # Verify session is still usable after error
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


def test_is_transaction_aborted_with_transaction_error():
    """Test is_transaction_aborted detects transaction errors."""

    # Create a mock error that mimics InFailedSQLTransactionError
    class MockTransactionError(Exception):
        pass

    error = MockTransactionError(
        "InFailedSQLTransactionError: current transaction is aborted"
    )
    assert is_transaction_aborted(error) is True


def test_is_transaction_aborted_with_other_error():
    """Test is_transaction_aborted returns False for other errors."""
    error = Exception("Some other error")
    assert is_transaction_aborted(error) is False

    error = SQLAlchemyError("Connection failed")
    assert is_transaction_aborted(error) is False
