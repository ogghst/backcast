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
        actor_type: str | None = None,
        actor_id: UUID | None = None,
        severity: str = "info",
        project_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> Notification:
        """Create a new notification for a user.

        Args:
            user_id: UUID of the recipient user.
            event_type: Dotted event code (e.g. 'co.submitted').
            title: Short headline for notification lists.
            message: Full notification body text.
            resource_type: Type of related entity (e.g. 'change_order').
            resource_id: UUID of the related entity.
            actor_type: Originator type ('user' | 'agent' | 'system').
            actor_id: UUID of the originating actor.
            severity: Severity string ('info' | 'notice' | 'warning' | 'urgent').
            project_id: Optional project scope.
            idempotency_key: Optional dedup key (unique per user when set).

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
            actor_type=actor_type,
            actor_id=actor_id,
            severity=severity,
            project_id=project_id,
            idempotency_key=idempotency_key,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def get_user_idempotency_exists(
        self, user_id: UUID, idempotency_key: str
    ) -> bool:
        """Return True if a notification already exists for this key+user.

        Used by the dispatcher to skip duplicate persists when an emitter
        supplies an ``idempotency_key``.

        Args:
            user_id: UUID of the recipient user.
            idempotency_key: Dedup key to check.

        Returns:
            ``True`` if a matching notification row exists.
        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.idempotency_key == idempotency_key,
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one() > 0

    async def get_user_notifications(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        category: str | None = None,
        severity: str | None = None,
    ) -> tuple[list[Notification], int]:
        """Get paginated notifications for a user.

        Args:
            user_id: UUID of the user whose notifications to fetch.
            page: 1-based page number.
            page_size: Number of items per page.
            unread_only: If True, return only unread notifications.
            category: Optional category filter (matched against the
                ``event_type`` prefix, e.g. ``"co"`` -> ``co.*``).
            severity: Optional exact severity filter (``info``/``notice``/...).

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
        if category:
            count_stmt = count_stmt.where(Notification.event_type.like(f"{category}.%"))
        if severity:
            count_stmt = count_stmt.where(Notification.severity == severity)

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
        if category:
            data_stmt = data_stmt.where(Notification.event_type.like(f"{category}.%"))
        if severity:
            data_stmt = data_stmt.where(Notification.severity == severity)

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
