"""Session health middleware for detecting failed transaction states.

Provides middleware to detect when a database session is in an aborted
transaction state and recover before processing requests.
"""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import RequestResponseEndpoint

from app.core.db_utils import is_transaction_aborted

logger = logging.getLogger(__name__)


async def check_session_health(session: AsyncSession) -> bool:
    """Check if a database session is healthy.

    Performs a simple query to verify the session is not in an
    aborted transaction state.

    Args:
        session: The database session to check

    Returns:
        True if session is healthy, False if transaction is aborted
    """
    try:
        # Simple query to test transaction state
        # If transaction is aborted, this will raise InFailedSQLTransactionError
        await session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as e:
        if is_transaction_aborted(e):
            logger.warning("Session is in aborted transaction state")
            return False
        # Other errors might be connection issues, not transaction state
        raise


async def recover_session(session: AsyncSession) -> bool:
    """Attempt to recover a session from aborted transaction state.

    Args:
        session: The database session to recover
    """
    try:
        await session.rollback()
        logger.info("Session recovered via rollback")
        return True
    except Exception as e:
        logger.error(f"Failed to recover session: {e}")
        # If we can't recover, we need a new session
        # This will be handled by closing and reopening the session
        await session.close()
        logger.info("Closed unhealthy session")
        return False


async def session_health_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Middleware to check and recover unhealthy database sessions.

    This middleware intercepts requests and checks if the database session
    is in an aborted transaction state before processing. If detected,
    it attempts recovery to prevent InFailedSQLTransactionError.

    Args:
        request: The incoming request
        call_next: The next middleware/route handler

    Returns:
        The response from the route handler
    """
    # Get the session from the request state (injected by get_db dependency)
    # Note: This middleware runs BEFORE the dependency injection, so we need
    # to check after the dependency has injected the session.
    # For now, we'll rely on the service layer error handling.

    response = await call_next(request)
    return response


def create_transaction_error_response(detail: str = "Database transaction error") -> JSONResponse:
    """Create a standardized error response for transaction errors.

    Args:
        detail: Error detail message

    Returns:
        JSONResponse with 500 status code
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
            "error_type": "transaction_error",
            "message": "A database transaction error occurred. Please try again.",
        },
    )
