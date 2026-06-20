"""UserNotificationPreference domain model - non-versioned entity.

Per-user delivery preferences keyed by ``(event_type, channel)``. An
``event_type`` of ``"*"`` acts as a wildcard. Defaults are seeded from the
notification registry; this table holds overrides.

Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from uuid import UUID

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class UserNotificationPreference(SimpleEntityBase):
    """User notification delivery preference.

    Attributes:
        user_id: Owner of the preference.
        event_type: Registered event code or ``"*"`` wildcard.
        channel: Delivery channel (e.g. ``in_app``, ``telegram``).
        enabled: Whether delivery on this channel is enabled for this event.
    """

    __tablename__ = "user_notification_preferences"

    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_type",
            "channel",
            name="uq_notif_pref_user_type_channel",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserNotificationPreference(user_id={self.user_id}, "
            f"event_type={self.event_type!r}, channel={self.channel!r}, "
            f"enabled={self.enabled})>"
        )
