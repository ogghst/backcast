"""Integration tests for Notification lifecycle.

Verifies end-to-end notification behavior including:
- Create notification and read it back
- Mark as read and verify unread count drops to zero

These tests use real DB sessions with transaction rollback.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import NotificationService


class TestNotificationLifecycle:
    """Integration tests for notification create, read, mark-as-read cycle."""

    @pytest.mark.asyncio
    async def test_create_read_and_mark_as_read_lifecycle(
        self, db_session: AsyncSession
    ) -> None:
        """Full lifecycle: create notification, read it back, mark as read."""
        service = NotificationService(db_session)
        user_id = uuid4()
        resource_id = uuid4()

        # Step 1: Create a notification
        notification = await service.create_notification(
            user_id=user_id,
            event_type="co_submitted",
            title="Change Order Submitted",
            message="CO-001 has been submitted for approval.",
            resource_type="change_order",
            resource_id=resource_id,
        )

        assert notification.user_id == user_id
        assert notification.event_type == "co_submitted"
        assert notification.title == "Change Order Submitted"
        assert notification.read_at is None

        # Step 2: Read it back via get_user_notifications
        notifications, total = await service.get_user_notifications(user_id)

        assert total == 1
        assert len(notifications) == 1
        assert notifications[0].id == notification.id

        # Verify unread count is 1
        unread_count = await service.get_unread_count(user_id)
        assert unread_count == 1

        # Step 3: Mark as read
        marked = await service.mark_as_read(notification.id, user_id)
        assert marked is True

        # Step 4: Verify unread count is now 0
        unread_after = await service.get_unread_count(user_id)
        assert unread_after == 0
