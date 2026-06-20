"""Route + service tests for the unified notification system (Phase A2).

Covers:
- GET /preferences returns registry defaults grouped by category.
- PUT /preferences persists overrides and they re-appear on GET.
- POST /telegram/connect returns a t.me/<bot>?start=<token> URL (or 400 when
  the bot username is unset).
- POST /telegram/webhook with a valid secret + /start <token> payload verifies
  the pending Telegram account.
- GET /notifications supports a category (event_type prefix) filter.
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain.notification import Notification
from app.models.domain.notification_preference import UserNotificationPreference
from app.models.domain.telegram_account import TelegramAccount
from app.services.telegram_link_service import TelegramLinkService
from tests.conftest import TEST_USER_ID

PREFIX = "/notifications"


async def _clean_user_notification_state(db: AsyncSession) -> None:
    """Clear the test user's notification rows.

    The suite runs against a shared dev database with a fixed test user, so
    rows from prior runs would otherwise pollute count/total assertions.
    """
    await db.execute(
        delete(UserNotificationPreference).where(
            UserNotificationPreference.user_id == TEST_USER_ID
        )
    )
    await db.execute(delete(Notification).where(Notification.user_id == TEST_USER_ID))
    await db.execute(
        delete(TelegramAccount).where(TelegramAccount.user_id == TEST_USER_ID)
    )
    await db.commit()


@pytest.mark.asyncio
async def test_preferences_defaults_present(client: AsyncClient) -> None:
    """GET /preferences returns registry defaults grouped by category."""
    response = await client.get(f"{PREFIX}/preferences")
    assert response.status_code == 200
    data = response.json()
    categories = {c["category"] for c in data["categories"]}
    # All six registry categories should be present.
    assert {
        "change_order",
        "agent",
        "project",
        "document",
        "branch",
        "system",
    } <= categories

    # co.submitted default channels are in_app + telegram, both enabled.
    co_cat = next(c for c in data["categories"] if c["category"] == "change_order")
    co_submitted = [e for e in co_cat["entries"] if e["event_type"] == "co.submitted"]
    channels = {e["channel"]: e["enabled"] for e in co_submitted}
    assert channels.get("in_app") is True
    assert channels.get("telegram") is True


@pytest.mark.asyncio
async def test_preferences_put_overrides_persist(
    client: AsyncClient,
    db: AsyncSession,
) -> None:
    """PUT /preferences persists overrides and they re-appear on GET."""
    await _clean_user_notification_state(db)
    body = {
        "changes": [
            {"event_type": "co.submitted", "channel": "telegram", "enabled": False},
            {"event_type": "agent.completed", "channel": "in_app", "enabled": False},
        ]
    }
    response = await client.put(f"{PREFIX}/preferences", json=body)
    assert response.status_code == 204

    # Verify a row was written.
    stmt = select(UserNotificationPreference).where(
        UserNotificationPreference.event_type == "co.submitted",
        UserNotificationPreference.channel == "telegram",
    )
    row = (await db.execute(stmt)).scalar_one()
    assert row.enabled is False

    # GET reflects the override.
    response = await client.get(f"{PREFIX}/preferences")
    data = response.json()
    co_cat = next(c for c in data["categories"] if c["category"] == "change_order")
    cell = next(
        e
        for e in co_cat["entries"]
        if e["event_type"] == "co.submitted" and e["channel"] == "telegram"
    )
    assert cell["enabled"] is False

    # Re-upserting flips it back to True (on-conflict update path).
    response = await client.put(
        f"{PREFIX}/preferences",
        json={
            "changes": [
                {
                    "event_type": "co.submitted",
                    "channel": "telegram",
                    "enabled": True,
                }
            ]
        },
    )
    assert response.status_code == 204
    # Cleanup.
    await db.rollback()


@pytest.mark.asyncio
async def test_telegram_connect_returns_deep_link(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /telegram/connect returns a t.me/<bot>?start=<token> URL."""
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "backcast_bot")
    response = await client.post(f"{PREFIX}/telegram/connect")
    assert response.status_code == 200
    data = response.json()
    assert data["bot_username"] == "backcast_bot"
    assert data["connect_url"].startswith("https://t.me/backcast_bot?start=")
    token = data["connect_url"].split("start=", 1)[1]
    assert len(token) > 10  # token_urlsafe(32) yields a non-trivial string


@pytest.mark.asyncio
async def test_telegram_connect_no_bot_username_400(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /telegram/connect returns 400 when no bot username is configured."""
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "")
    response = await client.post(f"{PREFIX}/telegram/connect")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_telegram_webhook_verifies_account(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /telegram/webhook with a valid secret + /start verifies the link.

    Uses the service directly to mint a pending link token (the connect route
    writes via its own session), then posts the inbound /start payload to the
    webhook.
    """
    await _clean_user_notification_state(db)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "backcast_bot")
    bot, url = await TelegramLinkService(db).create_link(actor_id)
    await db.commit()
    token = url.split("start=", 1)[1]

    secret = "test-webhook-secret"
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", secret)
    payload = {
        "message": {
            "text": f"/start {token}",
            "chat": {"id": 424242},
            "from": {"id": 111111},
        }
    }
    response = await client.post(
        f"{PREFIX}/telegram/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
    )
    assert response.status_code == 200

    # The pending account should now be verified with the chat id stored.
    stmt = select(TelegramAccount).where(TelegramAccount.user_id == actor_id)
    account = (await db.execute(stmt)).scalar_one()
    assert account.is_verified is True
    assert account.telegram_chat_id == "424242"
    assert account.link_token is None


@pytest.mark.asyncio
async def test_telegram_webhook_rejects_bad_secret(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /telegram/webhook returns 403 when the secret header mismatches."""
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "real-secret")
    response = await client.post(
        f"{PREFIX}/telegram/webhook",
        json={"message": {"text": "/start abc", "chat": {"id": 1}, "from": {"id": 2}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_telegram_webhook_handles_malformed_body(client: AsyncClient) -> None:
    """POST /telegram/webhook returns 200 on a malformed (non-JSON) body."""
    response = await client.post(
        f"{PREFIX}/telegram/webhook",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_notifications_category_filter(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: Any,
) -> None:
    """GET /notifications?category=co filters by event_type prefix."""
    await _clean_user_notification_state(db)
    db.add_all(
        [
            Notification(
                user_id=actor_id,
                event_type="co.submitted",
                title="CO",
                message="submitted",
                severity="notice",
            ),
            Notification(
                user_id=actor_id,
                event_type="agent.completed",
                title="Agent",
                message="done",
                severity="notice",
            ),
        ]
    )
    await db.commit()

    response = await client.get(PREFIX, params={"category": "co"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "co.submitted"
    # category is derived on the response.
    assert data["items"][0]["category"] == "change_order"


@pytest.mark.asyncio
async def test_list_notifications_severity_filter(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: Any,
) -> None:
    """GET /notifications?severity=urgent filters by severity."""
    await _clean_user_notification_state(db)
    db.add_all(
        [
            Notification(
                user_id=actor_id,
                event_type="co.escalated",
                title="Escalated",
                message="up",
                severity="urgent",
            ),
            Notification(
                user_id=actor_id,
                event_type="agent.message",
                title="Msg",
                message="hi",
                severity="info",
            ),
        ]
    )
    await db.commit()

    response = await client.get(PREFIX, params={"severity": "urgent"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["severity"] == "urgent"


@pytest.mark.asyncio
async def test_telegram_status_and_unlink(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /telegram/status then DELETE /telegram reflects linkage lifecycle."""
    await _clean_user_notification_state(db)
    # `available` reflects server-side Telegram config (deterministic).
    monkeypatch.setattr(settings, "TELEGRAM_ENABLED", False)
    response = await client.get(f"{PREFIX}/telegram/status")
    assert response.status_code == 200
    body = response.json()
    assert body["linked"] is False
    assert body["verified"] is False
    assert body["chat_id"] is None
    assert body["available"] is False

    # Fully configured → available True.
    monkeypatch.setattr(settings, "TELEGRAM_ENABLED", True)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "backcast_bot")

    # Create a pending link via the service (its own session).
    await TelegramLinkService(db).create_link(actor_id)
    await db.commit()

    # Now linked but unverified, and available True.
    response = await client.get(f"{PREFIX}/telegram/status")
    assert response.status_code == 200
    body = response.json()
    assert body["linked"] is True
    assert body["verified"] is False
    assert body["available"] is True

    # Unlink.
    response = await client.delete(f"{PREFIX}/telegram")
    assert response.status_code == 204

    response = await client.get(f"{PREFIX}/telegram/status")
    assert response.json()["linked"] is False
