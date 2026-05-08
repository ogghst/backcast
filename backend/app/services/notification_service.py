"""Notification service for in-app notification management.

Provides CRUD and read-status operations for the Notification domain model.
Notifications use SimpleEntityBase (no versioning/branching) since they are
transient user-facing data with no audit trail requirements.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.notification import Notification


class NotificationService:
    """Service for managing in-app notifications.

    Handles creation, retrieval, and read-status tracking of notifications
    for individual users.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries.
        """
        self._db = db_session

    async def create_notification(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
        message: str,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> Notification:
        """Create a new notification for a user.

        Args:
            user_id: UUID of the recipient user.
            event_type: Event category (e.g. 'co_submitted', 'co_approved').
            title: Short headline for notification lists.
            message: Full notification body text.
            resource_type: Type of related entity (e.g. 'change_order').
            resource_id: UUID of the related entity.

        Returns:
            The created Notification instance.
        """
        notification = Notification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def get_user_notifications(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """Get paginated notifications for a user.

        Args:
            user_id: UUID of the user whose notifications to fetch.
            page: 1-based page number.
            page_size: Number of items per page.
            unread_only: If True, return only unread notifications.

        Returns:
            A tuple of (notifications list, total count).
        """
        # Count query
        count_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
        )
        if unread_only:
            count_stmt = count_stmt.where(Notification.read_at.is_(None))

        count_result = await self._db.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Data query
        offset = (page - 1) * page_size
        data_stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        if unread_only:
            data_stmt = data_stmt.where(Notification.read_at.is_(None))

        data_result = await self._db.execute(data_stmt)
        notifications = list(data_result.scalars().all())

        return notifications, total_count

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a single notification as read.

        Verifies the notification belongs to the requesting user before
        updating.

        Args:
            notification_id: UUID of the notification to mark.
            user_id: UUID of the user (for ownership verification).

        Returns:
            True if the notification was found and updated, False otherwise.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        result = await self._db.execute(stmt)
        notification = result.scalar_one_or_none()

        if notification is None:
            return False

        notification.read_at = datetime.now(UTC)
        await self._db.flush()
        return True

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all unread notifications as read for a user.

        Args:
            user_id: UUID of the user.

        Returns:
            The number of notifications that were updated.
        """
        now = datetime.now(UTC)

        # Fetch all unread notifications for this user
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        result = await self._db.execute(stmt)
        notifications = result.scalars().all()

        count = 0
        for notification in notifications:
            notification.read_at = now
            count += 1

        await self._db.flush()
        return count

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user.

        Args:
            user_id: UUID of the user.

        Returns:
            Number of unread notifications.
        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()
