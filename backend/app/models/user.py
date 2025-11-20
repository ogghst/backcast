"""User model and related schemas."""

import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import EmailStr
from sqlalchemy import Column, Date, DateTime
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User role enumeration."""

    admin = "admin"
    project_manager = "project_manager"
    department_manager = "department_manager"
    controller = "controller"
    executive_viewer = "executive_viewer"


# Shared properties
class UserBase(SQLModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(unique=True, index=True, max_length=200)
    is_active: bool = True
    role: UserRole = Field(default=UserRole.controller)
    department: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    time_machine_date: date | None = Field(default=None)
    openai_base_url: str | None = Field(default=None, max_length=500)
    openai_api_key_encrypted: str | None = Field(default=None)


# Properties to receive via API on creation
class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    """Schema for user registration."""

    email: EmailStr = Field(max_length=200)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    """Schema for updating a user."""

    email: EmailStr | None = Field(default=None, max_length=200)  # type: ignore
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    openai_api_key: str | None = Field(
        default=None, description="Plain text API key (will be encrypted)"
    )


class UserUpdateMe(SQLModel):
    """Schema for updating own user profile."""

    full_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = Field(default=None, max_length=200)
    openai_base_url: str | None = Field(default=None, max_length=500)
    openai_api_key: str | None = Field(
        default=None, description="Plain text API key (will be encrypted)"
    )


class UpdatePassword(SQLModel):
    """Schema for password update."""

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    """User database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    time_machine_date: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    # Note: openai_base_url and openai_api_key_encrypted are inherited from UserBase
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    """Public user schema for API responses."""

    id: uuid.UUID
    # Override to exclude from response
    openai_api_key_encrypted: None = Field(default=None, exclude=True)  # type: ignore


class UsersPublic(SQLModel):
    """Schema for list of users."""

    data: list[UserPublic]
    count: int


class TimeMachinePreference(SQLModel):
    """Represents a resolved time machine date for the current user."""

    time_machine_date: date


class TimeMachinePreferenceUpdate(SQLModel):
    """Payload to update or reset the stored time machine date."""

    time_machine_date: date | None = Field(default=None)
