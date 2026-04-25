"""Error response construction utilities for WebSocket messages.

Provides centralized builders for WSErrorMessage to ensure consistent
error formatting across the AI chat WebSocket protocol.
"""

from typing import Any

from app.models.schemas.ai import WSErrorMessage


def build_ws_error(
    message: str,
    code: int = 500,
    details: dict[str, Any] | None = None,
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


def build_permission_denied_error(
    permission: str,
    user_role: str,
    tool_name: str | None = None,
) -> WSErrorMessage:
    """Build a permission denied error message.

    Args:
        permission: Required permission string.
        user_role: Current user's role.
        tool_name: Optional tool name for context.

    Returns:
        WSErrorMessage with code 403.
    """
    message = f"Permission denied: {permission} required (user_role: {user_role}"
    if tool_name:
        message += f", tool: {tool_name}"
    message += ")"

    return build_ws_error(message, code=403)


def build_project_access_error(
    project_id: str,
    permission: str,
    user_role: str,
) -> WSErrorMessage:
    """Build a project access denied error message.

    Args:
        project_id: Project identifier that was accessed.
        permission: Required permission string.
        user_role: Current user's role.

    Returns:
        WSErrorMessage with code 403.
    """
    return build_ws_error(
        f"Insufficient permissions for project {project_id} "
        f"(user_role: {user_role}, permission: {permission})",
        code=403,
    )
