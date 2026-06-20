"""TelegramAccount domain model - non-versioned entity.

Stores the linkage between a Backcast user and a Telegram chat so that
per-user notifications can be delivered. A pending account has a ``link_token``
(the deep-link payload in ``/start <token>``); once the user runs the command
in Telegram, ``telegram_chat_id`` is stored and ``is_verified`` flips true.

Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class TelegramAccount(SimpleEntityBase):
    """Telegram account linkage for a user.

    Attributes:
        user_id: Owning Backcast user (one Telegram account per user).
        telegram_chat_id: Telegram chat id to send messages to.
        telegram_user_id: Telegram user id, if known.
        linked_at: When the linkage was first created.
        link_token: Pending deep-link token (cleared once verified).
        is_verified: Whether the user completed the ``/start`` handshake.
    """

    __tablename__ = "telegram_accounts"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, unique=True, index=True
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    telegram_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    link_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return (
            f"<TelegramAccount(user_id={self.user_id}, "
            f"telegram_chat_id={self.telegram_chat_id!r}, "
            f"is_verified={self.is_verified})>"
        )
