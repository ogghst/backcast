"""Document entity link domain model - polymorphic links between documents and domain entities."""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class DocumentEntityLink(SimpleEntityBase):
    __tablename__ = "document_entity_links"

    document_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(PG_UUID, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DocumentEntityLink(id={self.id}, "
            f"document_id={self.document_id}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id})>"
        )
