"""Telegram-based admin notifier."""

import asyncio
import logging
import platform
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.notifications._types import NotificationEvent, NotificationPayload

logger = logging.getLogger(__name__)

_TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

_EVENT_EMOJI: dict[NotificationEvent, str] = {
    NotificationEvent.SYSTEM_STARTUP: "\U0001f680",
    NotificationEvent.UNHANDLED_EXCEPTION: "\U0001f525",
    NotificationEvent.USER_LOGIN: "\U0001f511",
}

_HTML_TEMPLATE = (
    "<b>[{emoji}] {event_label}</b>\n\n"
    "{message}\n\n"
    "<i>{timestamp} | {hostname}</i>"
    "{details_block}"
)


class TelegramNotifier:
    """Sends admin notifications to a Telegram chat.

    Configuration via environment variables:
      - TELEGRAM_ENABLED: bool (default False)
      - TELEGRAM_BOT_TOKEN: str
      - TELEGRAM_CHAT_ID: str
    """

    def __init__(self) -> None:
        self._enabled: bool = settings.TELEGRAM_ENABLED
        self._token: str = settings.TELEGRAM_BOT_TOKEN
        self._chat_id: str = settings.TELEGRAM_CHAT_ID
        self._client: httpx.AsyncClient | None = None

    def send_fire_and_forget(self, payload: NotificationPayload) -> None:
        """Enqueue a notification as a background task."""
        if not self._enabled:
            return
        try:
            asyncio.get_running_loop().create_task(self._send(payload))
        except RuntimeError:
            logger.debug("Cannot schedule Telegram notification: no event loop")

    async def send(self, payload: NotificationPayload) -> None:
        """Send a notification (awaitable). Errors are caught and logged."""
        if not self._enabled:
            return
        await self._send(payload)

    async def shutdown(self) -> None:
        """Close the httpx client. Call during app shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def _send(self, payload: NotificationPayload) -> None:
        text = self._format_message(payload)
        url = _TELEGRAM_API_URL.format(token=self._token)
        try:
            client = self._get_client()
            resp = await client.post(
                url,
                data={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "Telegram API returned %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception:
            logger.warning("Failed to send Telegram notification", exc_info=True)

    @staticmethod
    def _format_message(payload: NotificationPayload) -> str:
        emoji = _EVENT_EMOJI.get(payload.event, "\U0001f514")
        label = payload.event.replace("_", " ").title()
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        hostname = platform.node()

        details_block = ""
        if payload.details:
            lines = "\n".join(
                f"  <code>{k}</code>: {v}" for k, v in payload.details.items()
            )
            details_block = f"\n\n{lines}"

        return _HTML_TEMPLATE.format(
            emoji=emoji,
            event_label=label,
            message=payload.message,
            timestamp=ts,
            hostname=hostname,
            details_block=details_block,
        )


notifier = TelegramNotifier()
