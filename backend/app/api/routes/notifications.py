"""Notification API routes.

Provides endpoints for managing in-app notifications:
- GET /notifications -- List current user's notifications (paginated, filterable)
- PUT /notifications/{notification_id}/read -- Mark single notification as read
- PUT /notifications/read-all -- Mark all notifications as read
- GET /notifications/unread-count -- Get unread count for badge display
- GET /notifications/preferences -- Merged default + override preferences
- PUT /notifications/preferences -- Bulk upsert preference cells
- POST /notifications/telegram/connect -- Create a Telegram deep-link URL
- GET /notifications/telegram/status -- Telegram linkage status
- DELETE /notifications/telegram -- Unlink Telegram
- POST /notifications/telegram/webhook -- Inbound Telegram updates (no JWT)
- WS /notifications/stream -- Real-time notification + badge push
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import UserIdentity, get_current_user
from app.core.config import settings
from app.core.jwt_utils import validate_jwt_token
from app.core.notifications import user_connection_manager
from app.core.notifications.channels.telegram import parse_start_command
from app.db.session import async_session_maker, get_db
from app.models.schemas.common import PaginatedResponse
from app.models.schemas.notification import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
    TelegramConnectResponse,
    TelegramStatusResponse,
    UnreadCountResponse,
)
from app.services.notification_preference_service import NotificationPreferenceService
from app.services.notification_service import NotificationService
from app.services.telegram_link_service import TelegramLinkService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_notification_service(
    session: AsyncSession = Depends(get_db),
) -> NotificationService:
    """Dependency to get NotificationService instance."""
    return NotificationService(session)


def get_preference_service(
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferenceService:
    """Dependency to get NotificationPreferenceService instance."""
    return NotificationPreferenceService(session)


def get_telegram_link_service(
    session: AsyncSession = Depends(get_db),
) -> TelegramLinkService:
    """Dependency to get TelegramLinkService instance."""
    return TelegramLinkService(session)


# ---------------------------------------------------------------------------
# Notification list / read-state
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=NotificationListResponse,
    operation_id="list_notifications",
)
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    category: Annotated[
        str | None, Query(description="Category prefix filter (e.g. 'co', 'agent')")
    ] = None,
    severity: Annotated[str | None, Query(description="Exact severity filter")] = None,
    current_user: UserIdentity = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> PaginatedResponse[NotificationResponse]:
    """List current user's notifications with pagination and filters.

    Supports filtering to unread only, by category (event_type prefix), and by
    severity. Results are ordered by creation date, newest first.
    """
    notifications, total_count = await service.get_user_notifications(
        user_id=current_user.user_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        category=category,
        severity=severity,
    )
    return PaginatedResponse[NotificationResponse](
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total_count,
        page=page,
        per_page=page_size,
    )


@router.put(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    operation_id="mark_notification_read",
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> MarkReadResponse:
    """Mark a single notification as read.

    Returns 404 if the notification does not exist or does not belong
    to the current user.
    """
    updated = await service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.user_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read.",
        )
    return MarkReadResponse(updated_count=1)


@router.put(
    "/read-all",
    response_model=MarkReadResponse,
    operation_id="mark_all_notifications_read",
)
async def mark_all_notifications_read(
    current_user: UserIdentity = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> MarkReadResponse:
    """Mark all unread notifications as read for the current user."""
    count = await service.mark_all_as_read(user_id=current_user.user_id)
    return MarkReadResponse(updated_count=count)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    operation_id="get_unread_notification_count",
)
async def get_unread_count(
    current_user: UserIdentity = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    """Get the count of unread notifications for the current user.

    Used by the frontend notification badge to display the unread count.
    """
    count = await service.get_unread_count(user_id=current_user.user_id)
    return UnreadCountResponse(count=count)


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    operation_id="get_notification_preferences",
)
async def get_notification_preferences(
    current_user: UserIdentity = Depends(get_current_user),
    service: NotificationPreferenceService = Depends(get_preference_service),
) -> NotificationPreferencesResponse:
    """Return merged default + override notification preferences."""
    return await service.get_for_user(user_id=current_user.user_id)


@router.put(
    "/preferences",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="update_notification_preferences",
)
async def update_notification_preferences(
    body: NotificationPreferenceUpdateRequest,
    current_user: UserIdentity = Depends(get_current_user),
    service: NotificationPreferenceService = Depends(get_preference_service),
) -> Response:
    """Upsert the current user's notification preference cells."""
    await service.update_for_user(user_id=current_user.user_id, changes=body.changes)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Telegram linking
# ---------------------------------------------------------------------------


@router.post(
    "/telegram/connect",
    response_model=TelegramConnectResponse,
    operation_id="connect_telegram",
)
async def connect_telegram(
    current_user: UserIdentity = Depends(get_current_user),
    service: TelegramLinkService = Depends(get_telegram_link_service),
) -> TelegramConnectResponse:
    """Create a Telegram deep-link URL for the current user.

    Returns 400 if no Telegram bot username is configured.
    """
    try:
        bot_username, connect_url = await service.create_link(
            user_id=current_user.user_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return TelegramConnectResponse(bot_username=bot_username, connect_url=connect_url)


@router.get(
    "/telegram/status",
    response_model=TelegramStatusResponse,
    operation_id="get_telegram_status",
)
async def get_telegram_status(
    current_user: UserIdentity = Depends(get_current_user),
    service: TelegramLinkService = Depends(get_telegram_link_service),
) -> TelegramStatusResponse:
    """Return the current user's Telegram linkage status."""
    return await service.get_status(user_id=current_user.user_id)


@router.delete(
    "/telegram",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="unlink_telegram",
)
async def unlink_telegram(
    current_user: UserIdentity = Depends(get_current_user),
    service: TelegramLinkService = Depends(get_telegram_link_service),
) -> Response:
    """Remove the current user's Telegram linkage."""
    await service.unlink(user_id=current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/telegram/webhook",
    status_code=status.HTTP_200_OK,
    operation_id="telegram_webhook",
    include_in_schema=False,
)
async def telegram_webhook(
    request: Request,
    service: TelegramLinkService = Depends(get_telegram_link_service),
) -> Response:
    """Inbound Telegram update webhook (no JWT auth).

    If ``TELEGRAM_WEBHOOK_SECRET`` is set, the
    ``X-Telegram-Bot-Api-Secret-Token`` header must match (else 403). Parses a
    ``/start <token>`` message and verifies the pending Telegram account. Always
    returns 200 so Telegram does not retry on parse/verification failures.
    """
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if secret:
        provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if provided != secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Telegram webhook secret.",
            )

    try:
        update = await request.json()
    except Exception:
        logger.debug("Telegram webhook received non-JSON body")
        return Response(status_code=status.HTTP_200_OK)

    if not isinstance(update, dict):
        return Response(status_code=status.HTTP_200_OK)

    parsed = parse_start_command(update)
    if parsed is not None:
        token, chat_id, tg_user_id = parsed
        try:
            await service.verify_by_token(token, chat_id, tg_user_id)
        except Exception:
            logger.exception("Telegram webhook verify_by_token failed")

    return Response(status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# WebSocket: real-time notification + badge stream
# ---------------------------------------------------------------------------


@router.websocket("/stream")
async def notification_stream(
    websocket: WebSocket,
    token: Annotated[str, Query()],
) -> None:
    """Real-time notification stream for the authenticated user.

    Authentication:
        - JWT token via ``?token=`` query parameter, validated BEFORE accept.
        - Expired tokens receive 4008 (client should refresh, not reconnect).
        - Other failures receive 1008 (policy violation).

    Lifecycle:
        1. Validate JWT, resolve user_id from subject.
        2. Accept the connection, register in ``user_connection_manager``.
        3. Push an initial ``badge_update`` with the current unread count.
        4. Receive loop: handle ``mark_read`` client messages (re-push badge);
           ignore unknown types.
        5. On disconnect: unregister from the connection manager.

    Client messages:
        - ``{"type":"mark_read","notification_id":"<uuid>"}`` -- mark a single
          notification read and re-broadcast the updated badge count.
    """
    jwt_result = validate_jwt_token(token)
    if not jwt_result.is_valid:
        close_code = jwt_result.close_code or 1008
        await websocket.close(
            code=close_code, reason=jwt_result.error_detail or "Authentication failed"
        )
        return

    subject = jwt_result.subject
    if subject is None:
        await websocket.close(code=1008, reason="Invalid token: missing subject")
        return

    try:
        user_id = UUID(subject)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid token subject")
        return

    await websocket.accept()
    await user_connection_manager.connect(user_id, websocket)

    try:
        # Initial badge push.
        await _push_badge(websocket, user_id)

        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            await _handle_client_message(message, user_id, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        await user_connection_manager.disconnect(user_id, websocket)


async def _push_badge(websocket: WebSocket, user_id: UUID) -> None:
    """Send a ``badge_update`` frame with the current unread count."""
    try:
        async with async_session_maker() as session:
            count = await NotificationService(session).get_unread_count(user_id)
            await session.commit()
        await websocket.send_json({"type": "badge_update", "unread_count": count})
    except Exception:
        logger.exception("Failed to push initial badge_update to user %s", user_id)


async def _handle_client_message(
    message: object, user_id: UUID, websocket: WebSocket
) -> None:
    """Dispatch a single inbound client JSON message."""
    if not isinstance(message, dict):
        return
    msg_type = message.get("type")
    if msg_type == "mark_read":
        raw_id = message.get("notification_id")
        if not isinstance(raw_id, str):
            return
        try:
            notification_id = UUID(raw_id)
        except ValueError:
            return
        try:
            async with async_session_maker() as session:
                await NotificationService(session).mark_as_read(
                    notification_id, user_id
                )
                await session.commit()
        except Exception:
            logger.exception("mark_read via WS failed for user %s", user_id)
            return
        await _push_badge(websocket, user_id)
    # Unknown types are intentionally ignored.
