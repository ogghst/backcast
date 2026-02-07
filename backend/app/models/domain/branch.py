"""Branch domain model - tracks branch metadata and locking state.

Branches are project-scoped: the same branch name can exist in different projects.
Composite primary key: (name, project_id)
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin


class Branch(EntityBase, VersionableMixin):
    """Branch entity for tracking branch metadata and lock state.

    Attributes:
        name: Branch name (e.g., 'main' or 'co-CO-2026-001')
        project_id: Project this branch belongs to (references projects.project_id, not projects.id)
        branch_id: Unique identifier for the branch (independent of name/project)
        type: Branch type ('main' or 'change_order')
        locked: Whether branch is locked (prevents writes)
        branch_metadata: Additional branch information (JSONB)
        
    Inherited from VersionableMixin:
        valid_time: When the data is/was effective
        transaction_time: When the record was created/modified
        created_by: User who created the branch
        deleted_at: Soft delete timestamp
        deleted_by: User who deleted the branch
    """

    __tablename__ = "branches"

    # Standard Primary Key
    # id is inherited from EntityBase

    # Composite unique identifier (business key)
    # Note: Enforced via business logic + index, not PK
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # Note: No explicit ForeignKey here because project_id is not unique in projects table
        # (it's indexed but appears across multiple versions)
        # The FK is enforced at application level via service layer validation
    )

    # Stable identifier
    branch_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True, default=func.gen_random_uuid()
    )

    # Branch metadata
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="main")
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Audit fields handled by VersionableMixin
    # created_by, deleted_at, valid_time, transaction_time are inherited

    # Additional metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    branch_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "branch_metadata_info", JSONB, nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Branch(name={self.name}, project_id={self.project_id}, "
            f"type={self.type}, locked={self.locked})>"
        )
