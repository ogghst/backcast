"""Notification domain model for in-app notifications.

Stores workflow event notifications for users (e.g. change order submitted,
approval required, SLA deadline approaching). Uses SimpleEntityBase since
notifications are transient data with no audit/versioning requirements.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class Notification(SimpleEntityBase):
    """In-app notification for workflow events.

    Attributes:
        user_id: UUID of the user who should receive this notification.
        event_type: Categorization of the event (e.g. 'co_submitted', 'co_approved').
        title: Short headline for display in notification lists.
        message: Full notification body text.
        resource_type: Type of the related entity (e.g. 'change_order').
        resource_id: UUID of the related entity, if applicable.
        read_at: Timestamp when the user marked the notification as read.
    """

    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_notifications_user_read", "user_id", "read_at"),)
