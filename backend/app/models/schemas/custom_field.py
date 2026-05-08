"""Pydantic schemas for custom field definitions and values."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CustomFieldType(StrEnum):
    """Supported custom field types."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"


class CustomFieldDefinition(BaseModel):
    """Definition of a single custom field on the workflow config."""

    name: str = Field(..., min_length=1, max_length=100, description="Field name")
    type: CustomFieldType = Field(..., description="Field type")
    required: bool = Field(False, description="Whether the field is required")
    options: list[str] = Field(
        default_factory=list,
        description="Options for select type fields",
    )

    @model_validator(mode="after")
    def validate_select_has_options(self) -> "CustomFieldDefinition":
        if self.type == CustomFieldType.SELECT and not self.options:
            raise ValueError("Select fields must have at least one option")
        return self


class CustomFieldValues(BaseModel):
    """Per-CO custom field values matching field definitions from config."""

    values: dict[str, Any] = Field(
        default_factory=dict,
        description="Map of field name to value",
    )
