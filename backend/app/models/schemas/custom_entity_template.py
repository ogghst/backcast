"""Pydantic schemas for Custom Entity Template.

Mirrors `app/models/schemas/cost_element_type.py` structure-for-structure.
`target_entity_type` immutability is enforced in the service (reject on
update) rather than by omitting the field from Update, so the contract has
a single source of truth and the rejection surfaces a precise 400 error.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

#: Allowed target entity types for a custom template (analysis section 3).
TargetEntityType = Literal["PROJECT", "WBS_ELEMENT", "WORK_PACKAGE", "CHANGE_ORDER"]


class CustomEntityTemplateBase(BaseModel):
    """Shared properties for Custom Entity Template."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    target_entity_type: TargetEntityType
    field_definitions: dict[str, Any]


class CustomEntityTemplateCreate(CustomEntityTemplateBase):
    """Properties required for creating a Custom Entity Template."""

    custom_entity_template_id: UUID | None = Field(
        None,
        description="Root Custom Entity Template ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    organizational_unit_id: UUID
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class CustomEntityTemplateUpdate(BaseModel):
    """Properties that can be updated.

    `target_entity_type` is included so the service can reject it explicitly
    with a clear 400 message (immutability enforced in the service, not via
    schema omission). It defaults to None like the other optional fields.
    """

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    target_entity_type: TargetEntityType | None = None
    field_definitions: dict[str, Any] | None = None
    control_date: datetime | None = Field(
        None, description="Optional control date for the update (valid_time start)"
    )


class CustomEntityTemplateRead(CustomEntityTemplateBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    custom_entity_template_id: UUID
    organizational_unit_id: UUID
    created_by: UUID
    created_by_name: str | None = None
    valid_time: Any | None = None
    transaction_time: Any | None = None
