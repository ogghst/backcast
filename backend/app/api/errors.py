"""Error response construction utilities for WebSocket messages.

Provides centralized builders for WSErrorMessage to ensure consistent
error formatting across the AI chat WebSocket protocol.
"""

from app.models.schemas.ai import WSErrorMessage


def build_ws_error(
    message: str,
    code: int = 500,
) -> WSErrorMessage:
    """Build a standardized WebSocket error message.

    Args:
        message: Human-readable error description.
        code: HTTP-style error code (default: 500).
        details: Optional additional error context (reserved for future use).

    Returns:
        WSErrorMessage ready to send via WebSocket.
    """
    return WSErrorMessage(
        type="error",
        message=message,
        code=code,
    )
