"""Pydantic schemas for Notification API.

Source of truth for Notification API contracts.
Frontend TypeScript types must match these schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.common import PaginatedResponse


class NotificationResponse(BaseModel):
    """Schema for Notification API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Notification primary key")
    user_id: UUID = Field(..., description="User who should receive this notification")
    event_type: str = Field(..., description="Event category (e.g. 'co_submitted')")
    title: str = Field(..., description="Short headline for display")
    message: str = Field(..., description="Full notification body text")
    resource_type: str | None = Field(None, description="Related entity type")
    resource_id: UUID | None = Field(None, description="Related entity UUID")
    read_at: datetime | None = Field(
        None, description="When the user marked it as read"
    )
    created_at: datetime = Field(..., description="When the notification was created")


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
