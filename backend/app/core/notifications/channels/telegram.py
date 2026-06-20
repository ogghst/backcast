"""Telegram notification channel.

Ports the fire-and-forget HTTP+HTML approach from ``_telegram.py`` into a
:class:`Channel` implementation with per-user delivery, retry/backoff, and a
getUpdates long-polling receiver for dev (webhook is used in prod).
"""

from __future__ import annotations

import asyncio
import html
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import httpx

from app.core.notifications.channels.base import DeliveryResult
from app.core.notifications.event import NotificationEvent
from app.core.notifications.registry import ChannelKind, Severity

logger = logging.getLogger(__name__)

_TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
_TELEGRAM_GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"

_SEVERITY_EMOJI: dict[Severity, str] = {
    Severity.INFO: "\U0001f514",  # bell
    Severity.NOTICE: "\U0001f4cb",  # clipboard
    Severity.WARNING: "⚠️",  # warning
    Severity.URGENT: "\U0001f6a8",  # rotating light
}

_MAX_429_SLEEP = 10.0  # cap on Telegram's retry_after


class TelegramChannel:
    """Per-user Telegram delivery channel.

    Args:
        bot_token: Telegram bot API token.
        admin_chat_id: Fallback chat for system/broadcast events.
        bot_username: Bot username (for deep-link URL construction, if needed).
    """

    kind = ChannelKind.TELEGRAM

    def __init__(
        self,
        bot_token: str,
        admin_chat_id: str,
        bot_username: str | None = None,
    ) -> None:
        self._token = bot_token
        self._admin_chat_id = admin_chat_id
        self._bot_username = bot_username
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazily create (or reuse) the shared httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def send(
        self,
        event: NotificationEvent,
        recipient_user_id: UUID | None,  # noqa: ARG002 - chat_id is the address here
        chat_id: str | None,
    ) -> DeliveryResult:
        """Deliver *event* to Telegram chat *chat_id*.

        Args:
            event: The notification event to deliver.
            recipient_user_id: Target user, or ``None`` for broadcast/system
                events (unused; chat_id is the address).
            chat_id: Telegram chat id. ``None`` -> ``skipped``.

        Returns:
            A :class:`DeliveryResult`.
        """
        if not chat_id:
            return DeliveryResult(ChannelKind.TELEGRAM, "skipped", "no chat_id")

        text = self.render(event)
        url = _TELEGRAM_API_URL.format(token=self._token)
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

        client = self._get_client()
        backoff = 1.0
        for attempt in range(3):
            try:
                resp = await client.post(url, data=data)
            except Exception as exc:
                if attempt < 2:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                return DeliveryResult(ChannelKind.TELEGRAM, "failed", str(exc))

            if resp.status_code == 200:
                return DeliveryResult(ChannelKind.TELEGRAM, "sent")

            # Rate limited: honor retry_after, then retry.
            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp)
                await asyncio.sleep(min(retry_after, _MAX_429_SLEEP))
                continue

            # Server error: exponential backoff, then retry.
            if 500 <= resp.status_code < 600:
                if attempt < 2:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

            # Non-retryable error (4xx other than 429).
            return DeliveryResult(
                ChannelKind.TELEGRAM,
                "failed",
                f"{resp.status_code}: {resp.text[:200]}",
            )

        return DeliveryResult(ChannelKind.TELEGRAM, "failed", "exhausted retries")

    async def shutdown(self) -> None:
        """Close the shared httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Rendering & parsing
    # ------------------------------------------------------------------

    @staticmethod
    def render(event: NotificationEvent) -> str:
        """Render *event* as an HTML message for Telegram.

        User-controlled fields (title, message) are HTML-escaped.
        """
        emoji = _SEVERITY_EMOJI.get(event.severity, "\U0001f514")
        title = html.escape(event.title)
        message = html.escape(event.message)
        lines: list[str] = [f"<b>{emoji} {title}</b>", "", message]

        if event.resource_type:
            resource = event.resource_type
            if event.resource_id:
                resource = f"{resource}: {event.resource_id}"
            lines += ["", f"<i>{html.escape(resource)}</i>"]

        if event.actor_type:
            lines += ["", f"<i>by {html.escape(str(event.actor_type.value))}</i>"]

        if event.payload:
            detail_lines = [
                f"<code>{html.escape(str(k))}</code>: {html.escape(str(v))}"
                for k, v in event.payload.items()
            ]
            lines += ["", "\n".join(detail_lines)]

        return "\n".join(lines)

    @property
    def admin_chat_id(self) -> str:
        """Admin chat id used for broadcast/system events."""
        return self._admin_chat_id

    @property
    def bot_username(self) -> str | None:
        """Bot username, if configured."""
        return self._bot_username


def _parse_retry_after(resp: httpx.Response) -> float:
    """Extract ``retry_after`` (seconds) from a Telegram 429 response."""
    try:
        payload = resp.json()
        return float(payload.get("parameters", {}).get("retry_after", 1))
    except (ValueError, TypeError):
        return 1.0


def parse_start_command(update: dict[str, Any]) -> tuple[str, str, str] | None:
    """Extract ``(token, chat_id, tg_user_id)`` from a Telegram ``/start`` update.

    A valid update has ``message.text`` starting with ``/start <token>``. The
    bot is addressed via the bot token (caller-provided context), the chat is
    ``message.chat.id``, and the Telegram user is ``message.from.id``.

    Returns:
        ``(token, chat_id, tg_user_id)`` or ``None`` if the update is not a
        ``/start <token>`` message.
    """
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    text = message.get("text")
    if not isinstance(text, str):
        return None
    parts = text.split(maxsplit=1)
    if len(parts) != 2 or parts[0] != "/start":
        return None
    token = parts[1].strip()
    if not token:
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or "id" not in chat:
        return None
    chat_id = str(chat["id"])
    from_user = message.get("from")
    if not isinstance(from_user, dict) or "id" not in from_user:
        return None
    tg_user_id = str(from_user["id"])
    return token, chat_id, tg_user_id


class TelegramUpdatePoller:
    """getUpdates long-poll receiver (dev fallback for the webhook).

    Args:
        bot_token: Telegram bot API token.
        on_update: Async callback invoked once per inbound update dict.
    """

    def __init__(
        self,
        bot_token: str,
        on_update: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._token = bot_token
        self._on_update = on_update
        self._offset: int | None = None
        self._stopped = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the polling loop as a background task."""
        self._stopped.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Signal the polling loop to stop and await it."""
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        url = _TELEGRAM_GET_UPDATES_URL.format(token=self._token)
        client = httpx.AsyncClient(timeout=35.0)
        try:
            while not self._stopped.is_set():
                params: dict[str, Any] = {"timeout": 30}
                if self._offset is not None:
                    params["offset"] = self._offset
                try:
                    resp = await client.post(url, data=params)
                    if resp.status_code != 200:
                        logger.warning(
                            "Telegram getUpdates returned %s: %s",
                            resp.status_code,
                            resp.text[:200],
                        )
                        await asyncio.sleep(5)
                        continue
                    payload = resp.json()
                    if not payload.get("ok"):
                        logger.warning("Telegram getUpdates not ok: %s", payload)
                        await asyncio.sleep(5)
                        continue
                    for update in payload.get("result", []):
                        self._offset = int(update["update_id"]) + 1
                        try:
                            await self._on_update(update)
                        except Exception:
                            logger.exception("Telegram poller on_update handler failed")
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Telegram getUpdates loop error")
                    await asyncio.sleep(5)
        finally:
            await client.aclose()


__all__ = [
    "TelegramChannel",
    "TelegramUpdatePoller",
    "parse_start_command",
]
