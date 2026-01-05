from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserPreferenceBase(BaseModel):
    """Base preference schema with hybrid validation.

    Known fields are validated with specific types.
    Additional fields are allowed for extensibility.
    """

    # Known, validated fields (optional to support partial updates)
    theme: Literal["light", "dark"] | None = Field(
        default="light", description="UI theme preference"
    )

    # Allow additional preference fields for future extensibility
    model_config = ConfigDict(extra="allow")


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preferences."""

    # Override to make theme required on creation
    theme: Literal["light", "dark"] = Field(
        default="light", description="UI theme preference"
    )


class UserPreferenceUpdate(UserPreferenceBase):
    """Schema for updating user preferences.

    All fields are optional to support partial updates.
    """

    pass


class UserPreferenceResponse(UserPreferenceBase):
    """Schema for preference API responses."""

    # Override to make theme required in responses
    theme: Literal["light", "dark"] = Field(
        default="light", description="UI theme preference"
    )
