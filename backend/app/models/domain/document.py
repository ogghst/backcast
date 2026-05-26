"""Document domain model - core document metadata and locking state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import SimpleEntityBase

if TYPE_CHECKING:
    from app.models.domain.document_version import DocumentVersion


class Document(SimpleEntityBase):
    __tablename__ = "documents"

    project_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    folder_id: Mapped[str | None] = mapped_column(PG_UUID, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    current_version_id: Mapped[str | None] = mapped_column(PG_UUID, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_by: Mapped[str | None] = mapped_column(PG_UUID, nullable=True)
    created_by: Mapped[str] = mapped_column(PG_UUID, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # ORM relationship to the current version (not a FK constraint, application-level)
    current_version: Mapped[DocumentVersion | None] = relationship(
        "DocumentVersion",
        primaryjoin="Document.current_version_id == DocumentVersion.id",
        foreign_keys=[current_version_id],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, "
            f"project_id={self.project_id}, "
            f"name={self.name}, extension={self.extension})>"
        )
