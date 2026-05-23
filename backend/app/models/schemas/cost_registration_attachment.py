"""Pydantic schemas for Cost Registration Attachments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CostRegistrationAttachmentRead(BaseModel):
    """Properties returned for an attachment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_registration_id: UUID
    filename: str
    content_type: str
    size: int
    created_at: datetime
