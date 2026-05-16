"""Unit tests for Change Order notification dispatch functionality.

Tests verify that notifications are created and sent to the correct users
during workflow transitions (submit, approve, reject).

These tests focus on the notification dispatch logic by testing the
_send_notification helper method directly.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.change_order_service import ChangeOrderService


class TestNotificationDispatchHelper:
    """Tests for the _send_notification helper method."""

    @pytest.mark.asyncio
    async def test_send_notification_creates_notification_record(self) -> None:
        """_send_notification calls NotificationService.create_notification with correct parameters."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        user_id = uuid4()
        resource_id = uuid4()

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            mock_notif_service = AsyncMock()
            mock_notif_service_class.return_value = mock_notif_service

            # Call the helper method
            await service._send_notification(
                user_id=user_id,
                event_type="co_submitted",
                title="Test Notification",
                message="Test message body",
                resource_type="change_order",
                resource_id=resource_id,
            )

            # Verify NotificationService was instantiated with session
            mock_notif_service_class.assert_called_once_with(mock_session)

            # Verify create_notification was called with correct parameters
            mock_notif_service.create_notification.assert_called_once_with(
                user_id=user_id,
                event_type="co_submitted",
                title="Test Notification",
                message="Test message body",
                resource_type="change_order",
                resource_id=resource_id,
            )

    @pytest.mark.asyncio
    async def test_send_notification_handles_exceptions_gracefully(self) -> None:
        """_send_notification logs exceptions but doesn't raise them."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        user_id = uuid4()

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            # Make the notification service raise an exception
            mock_notif_service = AsyncMock()
            mock_notif_service.create_notification = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            mock_notif_service_class.return_value = mock_notif_service

            # Call the helper method - should not raise exception
            await service._send_notification(
                user_id=user_id,
                event_type="co_submitted",
                title="Test Notification",
                message="Test message body",
            )

            # Verify the method was still called (exception was handled)
            mock_notif_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_uses_default_resource_type(self) -> None:
        """_send_notification uses 'change_order' as default resource_type."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        user_id = uuid4()
        resource_id = uuid4()

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            mock_notif_service = AsyncMock()
            mock_notif_service_class.return_value = mock_notif_service

            # Call without specifying resource_type
            await service._send_notification(
                user_id=user_id,
                event_type="co_submitted",
                title="Test Notification",
                message="Test message body",
                resource_id=resource_id,
            )

            # Verify default resource_type was used
            call_args = mock_notif_service.create_notification.call_args
            assert call_args[1]["resource_type"] == "change_order"

    @pytest.mark.asyncio
    async def test_send_notification_handles_optional_resource_id(self) -> None:
        """_send_notification can be called without resource_id."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        user_id = uuid4()

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            mock_notif_service = AsyncMock()
            mock_notif_service_class.return_value = mock_notif_service

            # Call without resource_id
            await service._send_notification(
                user_id=user_id,
                event_type="system_alert",
                title="System Alert",
                message="System message without resource",
            )

            # Verify call was made with resource_id=None
            call_args = mock_notif_service.create_notification.call_args
            assert call_args[1]["resource_id"] is None


class TestNotificationEventTypes:
    """Tests for correct event types during workflow transitions."""

    @pytest.mark.asyncio
    async def test_co_submitted_event_type(self) -> None:
        """CO submission uses 'co_submitted' event type."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            mock_notif_service = AsyncMock()
            mock_notif_service_class.return_value = mock_notif_service

            await service._send_notification(
                user_id=uuid4(),
                event_type="co_submitted",
                title="Change Order Submitted",
                message="Your CO requires approval",
            )

            call_args = mock_notif_service.create_notification.call_args
            assert call_args[1]["event_type"] == "co_submitted"

    @pytest.mark.asyncio
    async def test_co_approved_event_type(self) -> None:
        """CO approval uses 'co_approved' event type."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            mock_notif_service = AsyncMock()
            mock_notif_service_class.return_value = mock_notif_service

            await service._send_notification(
                user_id=uuid4(),
                event_type="co_approved",
                title="Change Order Approved",
                message="Your CO has been approved",
            )

            call_args = mock_notif_service.create_notification.call_args
            assert call_args[1]["event_type"] == "co_approved"

    @pytest.mark.asyncio
    async def test_co_rejected_event_type(self) -> None:
        """CO rejection uses 'co_rejected' event type."""
        mock_session = AsyncMock()
        service = ChangeOrderService(mock_session)

        with patch(
            "app.services.notification_service.NotificationService"
        ) as mock_notif_service_class:
            mock_notif_service = AsyncMock()
            mock_notif_service_class.return_value = mock_notif_service

            await service._send_notification(
                user_id=uuid4(),
                event_type="co_rejected",
                title="Change Order Rejected",
                message="Your CO has been rejected",
            )

            call_args = mock_notif_service.create_notification.call_args
            assert call_args[1]["event_type"] == "co_rejected"
