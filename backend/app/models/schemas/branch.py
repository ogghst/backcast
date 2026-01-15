from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BranchPublic(BaseModel):
    """Schema for a branch option."""

    name: str = Field(..., description="Branch name (e.g. 'main' or 'co-CO-123')")
    type: Literal["main", "change_order"] = Field(..., description="Type of branch")
    is_default: bool = Field(False, description="Whether this is the default branch")

    # Change Order details (only if type is change_order)
    change_order_id: UUID | None = Field(None, description="Root ID of the associated change order")
    change_order_code: str | None = Field(None, description="Business code of the change order")
    change_order_status: str | None = Field(None, description="Status of the change order")
