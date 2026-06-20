"""Telegram account linking service.

Manages the deep-link handshake that connects a Backcast user to a Telegram
chat. A pending :class:`TelegramAccount` carries a ``link_token``; the user
runs ``/start <token>`` in Telegram (via webhook or the getUpdates poller),
which calls :meth:`TelegramLinkService.verify_by_token` to store the chat id
and mark the account verified.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain.telegram_account import TelegramAccount
from app.models.schemas.notification import TelegramStatusResponse


class TelegramLinkService:
    """Create/verify/unlink Telegram account linkages for users."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db_session: Async database session for queries.
        """
        self._db = db_session

    async def create_link(self, user_id: UUID) -> tuple[str, str]:
        """Create (or replace) a pending Telegram link for *user_id*.

        Generates a fresh ``link_token`` and returns the deep-link URL the user
        opens in Telegram.

        Args:
            user_id: UUID of the user requesting a link.

        Returns:
            A ``(bot_username, connect_url)`` tuple.

        Raises:
            ValueError: If ``TELEGRAM_BOT_USERNAME`` is not configured.
        """
        bot_username = settings.TELEGRAM_BOT_USERNAME
        if not bot_username:
            raise ValueError("Telegram bot username is not configured")

        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)

        existing = await self._get_account(user_id)
        if existing is None:
            account = TelegramAccount(
                user_id=user_id,
                telegram_chat_id="",  # placeholder until verified
                linked_at=now,
                link_token=token,
                is_verified=False,
            )
            self._db.add(account)
        else:
            existing.link_token = token
            existing.is_verified = False
            existing.linked_at = now
            account = existing
        await self._db.flush()

        connect_url = f"https://t.me/{bot_username}?start={token}"
        return bot_username, connect_url

    @staticmethod
    def _telegram_available() -> bool:
        """Whether Telegram is fully configured and enabled for user delivery."""
        return bool(
            settings.TELEGRAM_ENABLED
            and settings.TELEGRAM_BOT_TOKEN
            and settings.TELEGRAM_BOT_USERNAME
        )

    async def get_status(self, user_id: UUID) -> TelegramStatusResponse:
        """Return the current Telegram linkage status for *user_id*.

        Args:
            user_id: UUID of the user.

        Returns:
            A :class:`TelegramStatusResponse`.
        """
        available = self._telegram_available()
        account = await self._get_account(user_id)
        if account is None:
            return TelegramStatusResponse(
                linked=False, verified=False, chat_id=None, available=available
            )
        return TelegramStatusResponse(
            linked=True,
            verified=account.is_verified,
            chat_id=account.telegram_chat_id or None,
            available=available,
        )

    async def unlink(self, user_id: UUID) -> None:
        """Remove the Telegram linkage for *user_id*, if any.

        Args:
            user_id: UUID of the user.
        """
        account = await self._get_account(user_id)
        if account is not None:
            await self._db.delete(account)
            await self._db.flush()

    async def verify_by_token(self, token: str, chat_id: str, tg_user_id: str) -> bool:
        """Verify a pending link by its deep-link token.

        Finds the pending :class:`TelegramAccount` by ``link_token``, stores the
        Telegram chat/user ids, marks it verified, and clears the token. Safe to
        call repeatedly: a no-match (already-verified or unknown token) returns
        ``False`` without raising.

        Args:
            token: The deep-link token from the ``/start`` payload.
            chat_id: Telegram chat id of the user.
            tg_user_id: Telegram user id of the user.

        Returns:
            ``True`` if a pending account was verified, ``False`` otherwise.
        """
        stmt = select(TelegramAccount).where(
            TelegramAccount.link_token == token,
            TelegramAccount.is_verified.is_(False),
        )
        result = await self._db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            return False

        account.telegram_chat_id = chat_id
        account.telegram_user_id = tg_user_id
        account.is_verified = True
        account.link_token = None
        await self._db.flush()
        return True

    async def _get_account(self, user_id: UUID) -> TelegramAccount | None:
        """Return the user's TelegramAccount row, if any."""
        stmt = select(TelegramAccount).where(TelegramAccount.user_id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()


__all__ = ["TelegramLinkService"]
