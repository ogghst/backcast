"""Cost Registration Attachment Service - file attachment management."""

import logging
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.domain.cost_registration_attachment import CostRegistrationAttachment
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class CostRegistrationAttachmentService:
    """Service for managing cost registration file attachments."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._storage = StorageService()

    async def list_attachments(
        self, cost_registration_id: UUID
    ) -> list[CostRegistrationAttachment]:
        """List all attachments for a cost registration (by root ID).

        Args:
            cost_registration_id: Root ID of the cost registration.

        Returns:
            List of attachments ordered by creation time.
        """
        stmt = (
            select(CostRegistrationAttachment)
            .where(
                CostRegistrationAttachment.cost_registration_id == cost_registration_id
            )
            .options(defer(CostRegistrationAttachment.content))
            .order_by(CostRegistrationAttachment.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_attachment(
        self, attachment_id: UUID
    ) -> CostRegistrationAttachment | None:
        """Get a single attachment by its PK.

        Args:
            attachment_id: Primary key of the attachment.

        Returns:
            The attachment if found, None otherwise.
        """
        stmt = select(CostRegistrationAttachment).where(
            CostRegistrationAttachment.id == attachment_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_attachment(
        self,
        cost_registration_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> CostRegistrationAttachment:
        """Add an attachment to a cost registration.

        Uploads file content to S3 via StorageService and stores a reference
        via storage_key. The BYTEA content column is set to empty bytes
        (new attachments do not duplicate data in PostgreSQL).

        Args:
            cost_registration_id: Root ID of the cost registration.
            filename: Original filename.
            content_type: MIME type of the file.
            content: Raw file bytes.

        Returns:
            The created attachment.
        """
        attachment = CostRegistrationAttachment(
            cost_registration_id=cost_registration_id,
            filename=filename,
            content_type=content_type,
            content=b"",
            size=len(content),
        )
        self.db.add(attachment)
        await self.db.flush()

        # Upload to S3 after flush so attachment.id is assigned
        storage_key = f"attachments/{cost_registration_id}/{attachment.id}/{filename}"
        await self._storage.upload_file(
            key=storage_key,
            content=content,
            content_type=content_type,
        )
        attachment.storage_key = storage_key
        await self.db.flush()

        logger.info(
            "Attachment added: %s (%d bytes) for cost registration %s [S3]",
            filename,
            len(content),
            cost_registration_id,
        )
        return attachment

    async def get_attachment_content(
        self,
        attachment: CostRegistrationAttachment,
    ) -> bytes:
        """Retrieve attachment content from S3 or legacy BYTEA.

        If storage_key is set, downloads from S3. Otherwise falls back to
        the BYTEA content column for legacy attachments.

        Args:
            attachment: The attachment record.

        Returns:
            Raw file bytes.
        """
        if attachment.storage_key:
            return await self._storage.download_file(attachment.storage_key)
        return attachment.content

    async def get_download_url(
        self,
        attachment: CostRegistrationAttachment,
    ) -> str | None:
        """Generate a presigned download URL if stored in S3.

        Returns None for legacy BYTEA attachments (caller must use
        get_attachment_content instead).

        Args:
            attachment: The attachment record.

        Returns:
            Presigned URL string, or None for legacy BYTEA attachments.
        """
        if attachment.storage_key:
            return await self._storage.generate_presigned_url(attachment.storage_key)
        return None

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        """Delete an attachment by its PK.

        Removes the object from S3 if storage_key is set, then deletes
        the database row.

        Args:
            attachment_id: Primary key of the attachment.

        Returns:
            True if deleted, False if not found.
        """
        # Fetch attachment to get storage_key before deleting
        attachment = await self.get_attachment(attachment_id)
        if attachment is None:
            return False

        if attachment.storage_key:
            try:
                await self._storage.delete_file(attachment.storage_key)
            except Exception:
                logger.warning(
                    "Failed to delete S3 object '%s', proceeding with DB delete",
                    attachment.storage_key,
                )

        stmt = delete(CostRegistrationAttachment).where(
            CostRegistrationAttachment.id == attachment_id
        )
        result = await self.db.execute(stmt)
        deleted: int = result.rowcount  # type: ignore[attr-defined]
        if deleted and deleted > 0:
            logger.info("Attachment deleted: %s", attachment_id)
            return True
        return False

    async def get_attachment_counts(
        self, cost_registration_ids: list[UUID]
    ) -> dict[UUID, int]:
        """Get attachment counts for multiple cost registrations.

        Args:
            cost_registration_ids: List of root IDs.

        Returns:
            Dict mapping cost_registration_id to attachment count.
        """
        if not cost_registration_ids:
            return {}
        stmt = (
            select(
                CostRegistrationAttachment.cost_registration_id,
                func.count().label("attachment_count"),
            )
            .where(
                CostRegistrationAttachment.cost_registration_id.in_(
                    cost_registration_ids
                )
            )
            .group_by(CostRegistrationAttachment.cost_registration_id)
        )
        result = await self.db.execute(stmt)
        counts = dict.fromkeys(cost_registration_ids, 0)
        for row in result.all():
            counts[row.cost_registration_id] = int(row.attachment_count)
        return counts
