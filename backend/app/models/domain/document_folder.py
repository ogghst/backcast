"""Document folder domain model - hierarchical folder structure for document organization."""

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class DocumentFolder(SimpleEntityBase):
    __tablename__ = "document_folders"

    project_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(PG_UUID, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_by: Mapped[str] = mapped_column(PG_UUID, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DocumentFolder(id={self.id}, "
            f"project_id={self.project_id}, "
            f"name={self.name}, path={self.path})>"
        )
