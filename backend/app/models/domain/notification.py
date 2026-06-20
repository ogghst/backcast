"""Notification domain model for in-app notifications.

Stores workflow event notifications for users (e.g. change order submitted,
approval required, SLA deadline approaching). Uses SimpleEntityBase since
notifications are transient data with no audit/versioning requirements.

Extended for the unified notification system: ``event_type`` widened to 64
chars to hold dotted codes (``co.submitted``), and actor/severity/project/
idempotency columns added. The partial unique index on idempotency_key
enforces per-user dedup while allowing NULL keys.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class Notification(SimpleEntityBase):
    """In-app notification for workflow events.

    Attributes:
        user_id: UUID of the user who should receive this notification.
        event_type: Dotted event code (e.g. 'co.submitted', 'agent.completed').
        title: Short headline for display in notification lists.
        message: Full notification body text.
        resource_type: Type of the related entity (e.g. 'change_order').
        resource_id: UUID of the related entity, if applicable.
        read_at: Timestamp when the user marked the notification as read.
        actor_type: Originator type ('user' | 'agent' | 'system'), if recorded.
        actor_id: UUID of the originating actor, if applicable.
        severity: Severity string ('info' | 'notice' | 'warning' | 'urgent').
        project_id: Optional project scope.
        idempotency_key: Optional dedup key (unique per user when not NULL).
    """

    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Unified-notification additions (additive; existing rows unaffected).
    actor_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    project_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
        # Partial unique index: at most one unread/any notification per
        # (user_id, idempotency_key) when a key is supplied. NULL keys are
        # exempt so non-idempotent notifications are unconstrained.
        Index(
            "ux_notifications_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )
