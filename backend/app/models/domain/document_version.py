"""Document version domain model - individual version of an uploaded document."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class DocumentVersion(SimpleEntityBase):
    __tablename__ = "document_versions"

    document_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(PG_UUID, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DocumentVersion(id={self.id}, "
            f"document_id={self.document_id}, "
            f"version_number={self.version_number})>"
        )
