"""Unit tests for NotificationService.

Tests cover creation, retrieval with filtering, and read-status management
for in-app notifications. All tests use mocked sessions (no database).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.notification_service import NotificationService


class TestCreateNotification:
    """Tests for create_notification method."""

    @pytest.mark.asyncio
    async def test_create_notification_stores_record(self) -> None:
        """create_notification adds Notification to session and flushes."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        service = NotificationService(session)

        user_id = uuid4()
        resource_id = uuid4()

        notification = await service.create_notification(
            user_id=user_id,
            event_type="co_submitted",
            title="Change Order Submitted",
            message="CO-001 has been submitted for approval.",
            resource_type="change_order",
            resource_id=resource_id,
        )

        session.add.assert_called_once()
        session.flush.assert_called_once()

        added_obj = session.add.call_args[0][0]
        assert added_obj.user_id == user_id
        assert added_obj.event_type == "co_submitted"
        assert added_obj.title == "Change Order Submitted"
        assert added_obj.message == "CO-001 has been submitted for approval."
        assert added_obj.resource_type == "change_order"
        assert added_obj.resource_id == resource_id
        assert added_obj.read_at is None

        # The returned object is the same one added to the session
        assert notification is added_obj

class TestGetUserNotifications:
    """Tests for get_user_notifications method."""

    @pytest.mark.asyncio
    async def test_get_user_notifications_returns_only_users_notifications(
        self,
    ) -> None:
        """Query filters by user_id and returns matching notifications."""
        session = AsyncMock()
        user_id = uuid4()

        notif_a = MagicMock()
        notif_a.user_id = user_id

        notif_b = MagicMock()
        notif_b.user_id = user_id

        # count query returns 2, data query returns the notifications
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [
            notif_a,
            notif_b,
        ]

        session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])

        service = NotificationService(session)
        notifications, total = await service.get_user_notifications(user_id)

        assert total == 2
        assert len(notifications) == 2
        assert notifications[0] is notif_a
        assert notifications[1] is notif_b
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_user_notifications_unread_only_filter(self) -> None:
        """When unread_only=True, query includes read_at IS NULL filter."""
        session = AsyncMock()
        user_id = uuid4()

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        unread_notif = MagicMock()
        unread_notif.read_at = None

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [unread_notif]

        session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])

        service = NotificationService(session)
        notifications, total = await service.get_user_notifications(
            user_id, unread_only=True
        )

        assert total == 1
        assert len(notifications) == 1

        # Verify both queries were executed (count + data)
        assert session.execute.call_count == 2

        # Verify the SQL text includes read_at IS NULL in both queries
        for call in session.execute.call_args_list:
            stmt_text = str(call[0][0])
            assert "read_at IS NULL" in stmt_text

class TestMarkAsRead:
    """Tests for mark_as_read method."""

    @pytest.mark.asyncio
    async def test_mark_as_read_sets_read_at_timestamp(self) -> None:
        """mark_as_read sets read_at on the notification and flushes."""
        session = AsyncMock()
        session.flush = AsyncMock()

        notification = MagicMock()
        notification.read_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notification
        session.execute = AsyncMock(return_value=mock_result)

        service = NotificationService(session)
        notification_id = uuid4()
        user_id = uuid4()

        result = await service.mark_as_read(notification_id, user_id)

        assert result is True
        assert notification.read_at is not None
        assert isinstance(notification.read_at, datetime)
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_as_read_wrong_user_returns_false(self) -> None:
        """mark_as_read returns False when notification belongs to another user."""
        session = AsyncMock()

        # Query returns None because user_id does not match
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = NotificationService(session)
        notification_id = uuid4()
        different_user_id = uuid4()

        result = await service.mark_as_read(notification_id, different_user_id)

        assert result is False
        session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_as_read_already_read_returns_false(self) -> None:
        """mark_as_read returns False when notification is already read."""
        session = AsyncMock()

        # Query returns None because read_at IS NULL condition excludes
        # already-read notifications
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = NotificationService(session)
        notification_id = uuid4()
        user_id = uuid4()

        result = await service.mark_as_read(notification_id, user_id)

        assert result is False
        session.flush.assert_not_called()

class TestMarkAllAsRead:
    """Tests for mark_all_as_read method."""

    @pytest.mark.asyncio
    async def test_mark_all_as_read_updates_all_unread(self) -> None:
        """mark_all_as_read sets read_at on all unread notifications."""
        session = AsyncMock()
        session.flush = AsyncMock()

        unread_notifs = []
        for _ in range(3):
            n = MagicMock()
            n.read_at = None
            unread_notifs.append(n)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = unread_notifs
        session.execute = AsyncMock(return_value=mock_result)

        service = NotificationService(session)
        user_id = uuid4()

        count = await service.mark_all_as_read(user_id)

        assert count == 3
        for n in unread_notifs:
            assert n.read_at is not None
            assert isinstance(n.read_at, datetime)
        session.flush.assert_called_once()

class TestGetUnreadCount:
    """Tests for get_unread_count method."""

    @pytest.mark.asyncio
    async def test_get_unread_count_excludes_read_notifications(self) -> None:
        """get_unread_count returns count of only unread notifications."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)

        service = NotificationService(session)
        user_id = uuid4()

        count = await service.get_unread_count(user_id)

        assert count == 5

        # Verify query filters by user_id and read_at IS NULL
        stmt_text = str(session.execute.call_args[0][0])
        assert "read_at IS NULL" in stmt_text
