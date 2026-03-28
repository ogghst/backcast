"""RefreshToken domain model - non-versioned entity.

Stores refresh tokens for JWT token rotation mechanism.
Satisfies SimpleEntityProtocol via structural subtyping.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class RefreshToken(SimpleEntityBase):
    """Refresh token entity for JWT token rotation.

    Non-versioned entity that stores hashed refresh tokens with expiration
    and revocation tracking for secure authentication sessions.

    Structure:
    - id: UUID (PK)
    - user_id: UUID (FK to users.id - version-specific PK)
    - user_root_id: UUID (users.user_id - root entity identifier for queries)
    - token_hash: String (hashed refresh token)
    - expires_at: DateTime (token expiration)
    - created_at: DateTime (inherited from SimpleEntityBase)
    - updated_at: DateTime (inherited from SimpleEntityBase)
    - revoked_at: DateTime | None (revocation timestamp for logout)
    """

    __tablename__ = "refresh_tokens"

    # User relationship - references the primary key (id) of a user version
    # This ensures CASCADE delete works when the specific user version is deleted
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References users.id (version-specific PK)",
    )

    # Root user ID for querying across all user versions
    user_root_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        comment="Root user_id for querying across versions",
    )

    # Security (store only hashed tokens)
    token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Revocation (None = active, set = revoked)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_root_id={self.user_root_id}, expires_at={self.expires_at}, revoked_at={self.revoked_at})>"
