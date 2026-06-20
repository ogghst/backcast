"""Pydantic schemas for Notification API.

Source of truth for Notification API contracts.
Frontend TypeScript types must match these schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.notifications.registry import category_for_code
from app.models.schemas.common import PaginatedResponse


class NotificationResponse(BaseModel):
    """Schema for Notification API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Notification primary key")
    user_id: UUID = Field(..., description="User who should receive this notification")
    event_type: str = Field(
        ..., description="Dotted event code (e.g. 'co.submitted', up to 64 chars)"
    )
    title: str = Field(..., description="Short headline for display")
    message: str = Field(..., description="Full notification body text")
    resource_type: str | None = Field(None, description="Related entity type")
    resource_id: UUID | None = Field(None, description="Related entity UUID")
    severity: str = Field(
        "info", description="Severity ('info'|'notice'|'warning'|'urgent')"
    )
    actor_type: str | None = Field(
        None, description="Originator type ('user'|'agent'|'system')"
    )
    actor_id: UUID | None = Field(None, description="Originating actor UUID")
    project_id: UUID | None = Field(None, description="Optional project scope UUID")
    category: str | None = Field(
        None, description="Bell-tab category derived from event_type"
    )
    read_at: datetime | None = Field(
        None, description="When the user marked it as read"
    )
    created_at: datetime = Field(..., description="When the notification was created")

    @model_validator(mode="after")
    def _derive_category(self) -> NotificationResponse:
        """Derive ``category`` from ``event_type`` when not explicitly provided."""
        if self.category is None and self.event_type:
            self.category = category_for_code(self.event_type).value
        return self


NotificationListResponse = PaginatedResponse[NotificationResponse]


class UnreadCountResponse(BaseModel):
    """Schema for unread notification count (bell badge)."""

    model_config = ConfigDict(from_attributes=True)

    count: int = Field(..., description="Number of unread notifications")


class MarkReadResponse(BaseModel):
    """Schema for mark-read confirmation."""

    model_config = ConfigDict(from_attributes=True)

    updated_count: int = Field(
        ..., description="Number of notifications marked as read"
    )


# ---------------------------------------------------------------------------
# Notification preferences
# ---------------------------------------------------------------------------


class NotificationPreferenceEntry(BaseModel):
    """A single per-user (event_type, channel, enabled) preference cell."""

    model_config = ConfigDict(from_attributes=True)

    event_type: str = Field(..., description="Registered event code or '*' wildcard")
    channel: str = Field(
        ..., description="Delivery channel (e.g. 'in_app', 'telegram')"
    )
    enabled: bool = Field(
        ..., description="Whether delivery on this channel is enabled"
    )


class NotificationCategoryPreferences(BaseModel):
    """Preferences grouped under a single bell-tab category."""

    category: str = Field(..., description="Category identifier (e.g. 'change_order')")
    label: str = Field(..., description="Human-readable category label")
    entries: list[NotificationPreferenceEntry] = Field(
        default_factory=list, description="Per-(event_type, channel) entries"
    )


class NotificationPreferencesResponse(BaseModel):
    """Merged default + override preferences for the current user."""

    model_config = ConfigDict(from_attributes=True)

    categories: list[NotificationCategoryPreferences] = Field(
        default_factory=list, description="Preferences grouped by category"
    )


class NotificationPreferenceUpdateRequest(BaseModel):
    """Bulk upsert of preference cells for the current user."""

    changes: list[NotificationPreferenceEntry] = Field(
        ..., description="Cells to upsert (insert or update enabled flag)"
    )


# ---------------------------------------------------------------------------
# Telegram linking
# ---------------------------------------------------------------------------


class TelegramConnectResponse(BaseModel):
    """Deep-link URL the user opens in Telegram to connect their account."""

    model_config = ConfigDict(from_attributes=True)

    bot_username: str = Field(..., description="Telegram bot username")
    connect_url: str = Field(..., description="https://t.me/<bot>?start=<token> URL")


class TelegramStatusResponse(BaseModel):
    """Current Telegram linkage status for the user."""

    model_config = ConfigDict(from_attributes=True)

    linked: bool = Field(..., description="Whether a TelegramAccount row exists")
    verified: bool = Field(..., description="Whether the /start handshake completed")
    chat_id: str | None = Field(None, description="Telegram chat id once verified")
    available: bool = Field(
        ..., description="Whether Telegram is configured and enabled server-side"
    )
