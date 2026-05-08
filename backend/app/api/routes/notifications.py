"""Notification API routes.

Provides endpoints for managing in-app notifications:
- GET /notifications -- List current user's notifications (paginated)
- PUT /notifications/{notification_id}/read -- Mark single notification as read
- PUT /notifications/read-all -- Mark all notifications as read
- GET /notifications/unread-count -- Get unread count for badge display
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.common import PaginatedResponse
from app.models.schemas.notification import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


def get_notification_service(
    session: AsyncSession = Depends(get_db),
) -> NotificationService:
    """Dependency to get NotificationService instance."""
    return NotificationService(session)


@router.get(
    "",
    response_model=NotificationListResponse,
    operation_id="list_notifications",
)
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service),
) -> PaginatedResponse[NotificationResponse]:
    """List current user's notifications with pagination.

    Supports filtering to show only unread notifications.
    Results are ordered by creation date, newest first.
    """
    notifications, total_count = await service.get_user_notifications(
        user_id=current_user.user_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    """Get the count of unread notifications for the current user.

    Used by the frontend notification badge to display the unread count.
    """
    count = await service.get_unread_count(user_id=current_user.user_id)
    return UnreadCountResponse(count=count)
