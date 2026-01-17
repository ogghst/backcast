"""Branch domain model - tracks branch metadata and locking state.

Branches are project-scoped: the same branch name can exist in different projects.
Composite primary key: (name, project_id)
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import Base


class Branch(Base):
    """Branch entity for tracking branch metadata and lock state.

    Attributes:
        name: Branch name (e.g., 'main' or 'co-CO-2026-001')
        project_id: Project this branch belongs to (references projects.project_id, not projects.id)
        type: Branch type ('main' or 'change_order')
        locked: Whether branch is locked (prevents writes)
        created_at: When branch was created
        created_by: User who created the branch
        deleted_at: Soft delete timestamp (for archiving)
        branch_metadata: Additional branch information (JSONB)
    """

    __tablename__ = "branches"

    # Composite primary key: (name, project_id)
    name: Mapped[str] = mapped_column(String(80), nullable=False, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        primary_key=True,
        # Note: No explicit ForeignKey here because project_id is not unique in projects table
        # (it's indexed but appears across multiple versions)
        # The FK is enforced at application level via service layer validation
    )

    # Branch metadata
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="main")
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Audit fields
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Additional metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    branch_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Branch(name={self.name}, project_id={self.project_id}, "
            f"type={self.type}, locked={self.locked})>"
        )
