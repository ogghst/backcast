"""Database utilities for safe session handling.

Provides helper functions to validate session state and handle transaction
errors to prevent InFailedSQLTransactionError.
"""

import logging
from collections.abc import Awaitable
from typing import TypeVar

from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

logger = logging.getLogger(__name__)


async def safe_db_execute[T](
    session: AsyncSession,
    coro: Awaitable[T],
    error_message: str = "Database operation failed",
    rollback_on_error: bool = True,
) -> T:
    """Execute a database coroutine with proper error handling.

    Wraps database operations with try-catch to prevent transaction abortion
    from causing InFailedSQLTransactionError in subsequent operations.

    Args:
        session: The database session
        coro: Coroutine to execute (e.g., session.execute(stmt))
        error_message: Custom error message for exceptions
        rollback_on_error: Whether to rollback transaction on error

    Returns:
        The result of the coroutine

    Raises:
        ValueError: If database operation fails
        SQLAlchemyError: If rollback_on_error is False and operation fails

    Examples:
        >>> result = await safe_db_execute(
        ...     session,
        ...     session.execute(select(User).where(User.id == user_id)),
        ...     "Failed to get user"
        ... )
    """
    try:
        return await coro
    except (DBAPIError, SQLAlchemyError) as e:
        if rollback_on_error:
            try:
                await session.rollback()
                logger.warning(f"Transaction rolled back due to error: {error_message}")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")

        # Provide more context in error message
        error_msg = f"{error_message}: {str(e)}"
        if "InFailedSQLTransactionError" in str(e):
            error_msg = (
                f"{error_message}: Transaction was in aborted state. "
                "This usually indicates a previous query failed. "
                f"Original error: {str(e)}"
            )

        raise ValueError(error_msg) from e


def is_transaction_aborted(error: Exception) -> bool:
    """Check if an error indicates a transaction is in aborted state.

    Args:
        error: The exception to check

    Returns:
        True if this is an InFailedSQLTransactionError or similar
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    return (
        "infailedsqltransactionerror" in error_str
        or "transaction is aborted" in error_str
        or "current transaction is aborted" in error_str
        or "infailedsqltransaction" in error_type
    )
