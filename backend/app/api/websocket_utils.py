"""WebSocket connection utilities.

Provides centralized helpers for WebSocket connection state checking
and safe close operations. Eliminates duplicated connection-check
logic across the codebase.
"""

from fastapi import WebSocket
from starlette.websockets import WebSocketState


def is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if the WebSocket is still connected.

    Args:
        websocket: WebSocket connection to check.

    Returns:
        True if the client state is not DISCONNECTED.
    """
    return websocket.client_state != WebSocketState.DISCONNECTED


async def close_websocket_safely(
    websocket: WebSocket,
    code: int,
    reason: str,
) -> None:
    """Close WebSocket connection with error handling.

    Suppresses RuntimeError raised when the connection is already closed,
    which is a normal race condition in async WebSocket handling.

    Args:
        websocket: WebSocket to close.
        code: Close status code (e.g., 1000 for normal, 1008 for policy violation).
        reason: Human-readable close reason.
    """
    try:
        await websocket.close(code=code, reason=reason)
    except RuntimeError:
        # Connection already closed -- normal during async disconnect
        pass
