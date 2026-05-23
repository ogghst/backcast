"""Cost Registration Attachment domain model - file attachments for cost registrations.

Stores uploaded files (invoices, receipts, etc.) associated with cost registrations.
Uses SimpleEntityBase pattern (non-versioned) since attachments are immutable blobs.
"""

from sqlalchemy import Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class CostRegistrationAttachment(SimpleEntityBase):
    """File attachment for a cost registration.

    Stores file metadata and content for documents attached to cost
    registrations (invoices, receipts, supporting documents).
    Content is stored as raw bytes (BYTEA).

    Attributes:
        cost_registration_id: Root ID of the parent cost registration.
        filename: Original filename of the uploaded file.
        content_type: MIME type of the file.
        content: Raw file bytes.
        size: File size in bytes.
    """

    __tablename__ = "cost_registration_attachments"

    cost_registration_id: Mapped[str] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level FK constraint on root ID.
        # References the stable root identity (cost_registration_id),
        # not a specific version's PK. Integrity enforced at application level.
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<CostRegistrationAttachment(id={self.id}, "
            f"cost_registration_id={self.cost_registration_id}, "
            f"filename={self.filename}, size={self.size})>"
        )
