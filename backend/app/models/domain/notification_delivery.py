"""NotificationDelivery domain model - non-versioned entity.

One row per attempted channel delivery of a notification. Used for audit,
retry, and dead-letter diagnostics.

Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class NotificationDelivery(SimpleEntityBase):
    """Record of a single notification channel delivery attempt.

    Attributes:
        notification_id: FK to ``notifications.id``.
        channel: Channel the attempt was made on.
        status: ``sent`` | ``failed`` | ``skipped`` | ``dropped``.
        error: Error text when ``status == "failed"``.
        attempted_at: When the attempt occurred.
    """

    __tablename__ = "notification_deliveries"

    notification_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("notifications.id"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationDelivery(notification_id={self.notification_id}, "
            f"channel={self.channel!r}, status={self.status!r})>"
        )
