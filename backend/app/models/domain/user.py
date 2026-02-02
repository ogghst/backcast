"""User domain model - single-table versioned entity.

Satisfies VersionableProtocol via structural subtyping (duck typing).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    pass


# from app.models.protocols import VersionableProtocol # Removed as per instruction


class User(EntityBase, VersionableMixin):  # Removed VersionableProtocol from bases
    """User entity - single table with bitemporal versioning.

    Satisfies VersionableProtocol through structural subtyping.

    Structure:
    - id: UUID (PK, version identifier)
    - user_id: UUID (root entity identifier - groups all versions)
    - Versioned fields: email, hashed_password, full_name, role, department, is_active
    - Temporal: valid_time, transaction_time, deleted_at (from VersionableMixin)
    """

    __tablename__ = "users"

    # Root ID (stable identity across versions)
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Identity (immutable within version)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Security
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Profile (versioned)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Preferences (stored as JSON)
    # Note: No default value at Python level to avoid serialization issues with asyncpg
    # When None, SQLAlchemy stores NULL in database; service layer handles empty dict semantics
    preferences: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None

    def __repr__(self) -> str:
        return f"<User(id={self.id}, user_id={self.user_id}, email={self.email}, full_name={self.full_name})>"
