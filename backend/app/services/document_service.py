"""Document service - CRUD, versioning, search, and entity linking."""

import logging
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain.document import Document
from app.models.domain.document_entity_link import DocumentEntityLink
from app.models.domain.document_version import DocumentVersion
from app.models.schemas.document import DocumentUpdate, StorageStatsPublic
from app.services.document_processing_service import DocumentProcessingService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DocumentService:
    """Main service for document lifecycle management.

    Orchestrates storage, text extraction, versioning, and entity
    linking through StorageService and DocumentProcessingService.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._storage = StorageService()
        self._processing = DocumentProcessingService()

    # --- Upload / Versioning ---

    async def upload_document(
        self,
        project_id: UUID,
        folder_id: str | None,
        filename: str,
        content: bytes,
        content_type: str,
        user_id: UUID,
    ) -> Document:
        """Upload a new document with its first version.

        Steps:
        1. Validate file extension and size.
        2. Compute SHA-256 checksum.
        3. Extract text for search indexing.
        4. Create Document record.
        5. Upload binary content to S3.
        6. Create DocumentVersion record (version_number=1).
        7. Link current_version_id on Document.

        Args:
            project_id: Project the document belongs to.
            folder_id: Optional folder to place the document in.
            filename: Original filename with extension.
            content: Raw file bytes.
            content_type: MIME type.
            user_id: ID of the uploading user.

        Returns:
            The created document with current_version loaded.
        """
        self._processing.validate_file(filename, len(content))
        checksum = self._processing.compute_checksum(content)
        extracted_text = self._processing.extract_text(content, content_type)

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        name = filename.rsplit(".", 1)[0] if "." in filename else filename

        document_id = uuid4()
        document = Document(
            id=document_id,
            project_id=project_id,
            folder_id=folder_id,
            name=name,
            extension=ext,
            tags=[],
            is_locked=False,
            created_by=user_id,
            size_bytes=len(content),
        )
        self.db.add(document)

        storage_key = f"documents/{project_id}/{document_id}/v1/{filename}"
        await self._storage.upload_file(storage_key, content, content_type)

        version = DocumentVersion(
            document_id=str(document_id),
            version_number=1,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=len(content),
            checksum_sha256=checksum,
            extracted_text=extracted_text,
            uploaded_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()

        document.current_version_id = str(version.id)
        await self.db.flush()
        await self.db.refresh(document)

        # Eagerly load current_version for the response
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.current_version))
        )
        result = await self.db.execute(stmt)
        doc = result.scalar_one()
        logger.info(
            "Document uploaded: %s (%d bytes) in project %s",
            filename,
            len(content),
            project_id,
        )
        return doc

    async def upload_new_version(
        self,
        document_id: UUID,
        content: bytes,
        content_type: str,
        user_id: UUID,
        project_id: UUID | None = None,
    ) -> DocumentVersion:
        """Upload a new version of an existing document.

        Args:
            document_id: Primary key of the document.
            content: Raw file bytes.
            content_type: MIME type.
            user_id: ID of the uploading user.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            The new DocumentVersion record.

        Raises:
            ValueError: If the document does not exist or is locked by
                another user.
        """
        document = await self.get_document(document_id, project_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        if document.is_locked and str(document.locked_by) != str(user_id):
            raise ValueError(f"Document is locked by user {document.locked_by}")

        # Determine next version number
        max_ver_stmt = select(
            func.coalesce(func.max(DocumentVersion.version_number), 0)
        ).where(DocumentVersion.document_id == str(document_id))
        result = await self.db.execute(max_ver_stmt)
        current_max: int = result.scalar_one()
        new_version_number = current_max + 1

        checksum = self._processing.compute_checksum(content)
        extracted_text = self._processing.extract_text(content, content_type)

        filename = f"{document.name}.{document.extension}"
        storage_key = (
            f"documents/{document.project_id}/{document_id}"
            f"/v{new_version_number}/{filename}"
        )
        await self._storage.upload_file(storage_key, content, content_type)

        version = DocumentVersion(
            document_id=str(document_id),
            version_number=new_version_number,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=len(content),
            checksum_sha256=checksum,
            extracted_text=extracted_text,
            uploaded_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()

        document.current_version_id = str(version.id)
        document.size_bytes = len(content)
        await self.db.flush()

        logger.info(
            "New version v%d uploaded for document %s",
            new_version_number,
            document_id,
        )
        return version

    # --- Read operations ---

    async def download_document(
        self, document_id: UUID, project_id: UUID | None = None
    ) -> str:
        """Generate a presigned download URL for a document's current version.

        Args:
            document_id: Primary key of the document.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            Presigned S3 URL string.

        Raises:
            ValueError: If the document or its current version is not found.
        """
        document = await self.get_document(document_id, project_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        version = await self._get_version_by_id(document.current_version_id)
        if version is None:
            raise ValueError(f"Current version not found for document {document_id}")

        return await self._storage.generate_presigned_url(version.storage_key)

    async def get_document(
        self, document_id: UUID, project_id: UUID | None = None
    ) -> Document | None:
        """Fetch a document with its current version eagerly loaded.

        Args:
            document_id: Primary key of the document.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            The document with current_version, or None.
        """
        if project_id is not None:
            return await self._get_document_for_project(document_id, project_id)
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.current_version))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        project_id: UUID,
        folder_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        """List documents for a project, optionally filtered by folder.

        Args:
            project_id: Project to list documents for.
            folder_id: Optional folder filter.
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            List of documents ordered by creation time (newest first).
        """
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .options(selectinload(Document.current_version))
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if folder_id is not None:
            stmt = stmt.where(Document.folder_id == folder_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_documents(
        self,
        project_id: UUID,
        search_query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        """Search documents by name using ILIKE pattern matching.

        Args:
            project_id: Project to search within.
            search_query: Search term.
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Matching documents ordered by name.
        """
        stmt = (
            select(Document)
            .where(
                Document.project_id == project_id,
                text("name ILIKE :query").bindparams(query=f"%{search_query}%"),
            )
            .options(selectinload(Document.current_version))
            .order_by(Document.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # --- Metadata updates ---

    async def update_metadata(
        self,
        document_id: UUID,
        data: DocumentUpdate,
        project_id: UUID | None = None,
    ) -> Document:
        """Update document name, description, or tags.

        Args:
            document_id: Primary key of the document.
            data: Fields to update (only non-None values are applied).
            project_id: If provided, scopes the lookup to this project.

        Returns:
            The updated document.

        Raises:
            ValueError: If the document does not exist.
        """
        document = await self.get_document(document_id, project_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        if data.name is not None:
            document.name = data.name
        if data.description is not None:
            document.description = data.description
        if data.tags is not None:
            document.tags = data.tags

        await self.db.flush()
        # Scope the refresh to column attributes only. A bare refresh() would
        # expire the lazy='raise' current_version relationship, breaking
        # callers (add_document AI tool, the HTTP PUT/POST routes) that read
        # doc.current_version after a metadata update.
        await self.db.refresh(
            document,
            attribute_names=["name", "description", "tags", "updated_at"],
        )
        logger.info("Document metadata updated: %s", document_id)
        return document

    # --- Delete ---

    async def delete_document(
        self, document_id: UUID, project_id: UUID | None = None
    ) -> bool:
        """Delete a document and all its versions, links, and S3 objects.

        Args:
            document_id: Primary key of the document.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            True if deleted, False if not found.
        """
        document = await self.get_document(document_id, project_id)
        if document is None:
            return False

        # Collect S3 keys for cleanup
        ver_stmt = select(DocumentVersion.storage_key).where(
            DocumentVersion.document_id == str(document_id)
        )
        result = await self.db.execute(ver_stmt)
        storage_keys = [row[0] for row in result.all()]

        # Delete entity links
        await self.db.execute(
            delete(DocumentEntityLink).where(
                DocumentEntityLink.document_id == str(document_id)
            )
        )
        # Delete versions
        await self.db.execute(
            delete(DocumentVersion).where(
                DocumentVersion.document_id == str(document_id)
            )
        )
        # Delete document
        await self.db.execute(delete(Document).where(Document.id == document_id))
        await self.db.flush()

        # Schedule S3 cleanup (best-effort, do not block on failure)
        for key in storage_keys:
            try:
                await self._storage.delete_file(key)
            except Exception:
                logger.warning("Failed to delete S3 object: %s", key)

        logger.info("Document deleted: %s", document_id)
        return True

    # --- Locking ---

    async def lock_document(
        self,
        document_id: UUID,
        user_id: UUID,
        project_id: UUID | None = None,
    ) -> Document:
        """Lock a document for exclusive editing.

        Args:
            document_id: Primary key of the document.
            user_id: ID of the user acquiring the lock.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            The updated document.

        Raises:
            ValueError: If the document does not exist or is already
                locked by another user.
        """
        document = await self.get_document(document_id, project_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        if document.is_locked and str(document.locked_by) != str(user_id):
            raise ValueError(f"Document is locked by user {document.locked_by}")

        document.is_locked = True
        document.locked_by = str(user_id)
        await self.db.flush()
        await self.db.refresh(document)
        logger.info("Document locked: %s by user %s", document_id, user_id)
        return document

    async def unlock_document(
        self,
        document_id: UUID,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> Document:
        """Unlock a document.

        Args:
            document_id: Primary key of the document.
            user_id: If provided, only the user who locked the document
                (or an admin) can unlock it.
            project_id: If provided, scopes the lookup to this project.

        Returns:
            The updated document.

        Raises:
            ValueError: If the document does not exist or the user is
                not authorized to unlock it.
        """
        document = await self.get_document(document_id, project_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        if (
            user_id is not None
            and document.locked_by is not None
            and str(document.locked_by) != str(user_id)
        ):
            raise ValueError(
                f"Document is locked by user {document.locked_by}, "
                f"only that user can unlock it"
            )

        document.is_locked = False
        document.locked_by = None
        await self.db.flush()
        await self.db.refresh(document)
        logger.info("Document unlocked: %s", document_id)
        return document

    # --- Storage usage ---

    async def get_storage_usage(self, project_id: UUID) -> StorageStatsPublic:
        """Compute storage usage statistics for a project.

        Args:
            project_id: Project to compute stats for.

        Returns:
            Aggregated storage statistics.
        """
        doc_stats = select(
            func.count(Document.id).label("file_count"),
            func.coalesce(func.sum(Document.size_bytes), 0).label("total_bytes"),
        ).where(Document.project_id == project_id)
        result = await self.db.execute(doc_stats)
        row = result.one()

        ver_count_stmt = (
            select(func.count(DocumentVersion.id))
            .join(
                Document,
                DocumentVersion.document_id == Document.id,
            )
            .where(Document.project_id == project_id)
        )
        ver_result = await self.db.execute(ver_count_stmt)
        version_count: int = ver_result.scalar_one()

        return StorageStatsPublic(
            total_bytes=int(row.total_bytes),
            file_count=int(row.file_count),
            version_count=version_count,
        )

    # --- Entity linking ---

    async def link_document(
        self,
        document_id: UUID,
        entity_type: str,
        entity_id: str,
        note: str | None = None,
    ) -> DocumentEntityLink:
        """Create a link between a document and a domain entity.

        Args:
            document_id: Primary key of the document.
            entity_type: Type of the linked entity (wbe, cost_element, etc).
            entity_id: ID of the linked entity.
            note: Optional note about the link.

        Returns:
            The created link.
        """
        link = DocumentEntityLink(
            document_id=str(document_id),
            entity_type=entity_type,
            entity_id=entity_id,
            note=note,
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        logger.info(
            "Document %s linked to %s/%s",
            document_id,
            entity_type,
            entity_id,
        )
        return link

    async def unlink_document(
        self,
        document_id: UUID,
        entity_type: str,
        entity_id: str,
    ) -> bool:
        """Remove a link between a document and an entity.

        Args:
            document_id: Primary key of the document.
            entity_type: Type of the linked entity.
            entity_id: ID of the linked entity.

        Returns:
            True if a link was removed, False otherwise.
        """
        stmt = delete(DocumentEntityLink).where(
            DocumentEntityLink.document_id == str(document_id),
            DocumentEntityLink.entity_type == entity_type,
            DocumentEntityLink.entity_id == entity_id,
        )
        result = await self.db.execute(stmt)
        deleted: int = result.rowcount  # type: ignore[attr-defined]
        if deleted and deleted > 0:
            logger.info(
                "Document %s unlinked from %s/%s",
                document_id,
                entity_type,
                entity_id,
            )
            return True
        return False

    async def get_linked_documents(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[Document]:
        """Get all documents linked to a specific entity.

        Args:
            entity_type: Type of the entity.
            entity_id: ID of the entity.

        Returns:
            List of linked documents.
        """
        stmt = (
            select(Document)
            .join(
                DocumentEntityLink,
                DocumentEntityLink.document_id == Document.id,
            )
            .options(selectinload(Document.current_version))
            .where(
                DocumentEntityLink.entity_type == entity_type,
                DocumentEntityLink.entity_id == entity_id,
            )
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_linked_entities(self, document_id: UUID) -> list[DocumentEntityLink]:
        """Get all entity links for a specific document.

        Args:
            document_id: Primary key of the document.

        Returns:
            List of entity links.
        """
        stmt = (
            select(DocumentEntityLink)
            .where(DocumentEntityLink.document_id == str(document_id))
            .order_by(DocumentEntityLink.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_link_note(
        self,
        document_id: UUID,
        entity_type: str,
        entity_id: str,
        note: str,
    ) -> DocumentEntityLink | None:
        """Update the note on an existing document-entity link.

        Args:
            document_id: Primary key of the document.
            entity_type: Type of the linked entity.
            entity_id: ID of the linked entity.
            note: New note text.

        Returns:
            The updated link, or None if not found.
        """
        stmt = select(DocumentEntityLink).where(
            DocumentEntityLink.document_id == str(document_id),
            DocumentEntityLink.entity_type == entity_type,
            DocumentEntityLink.entity_id == entity_id,
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()
        if link is None:
            return None

        link.note = note
        await self.db.flush()
        await self.db.refresh(link)
        return link

    # --- Version history ---

    async def get_version_history(
        self, document_id: UUID, project_id: UUID | None = None
    ) -> list[DocumentVersion]:
        """Fetch all versions for a document, ordered by version number.

        Args:
            document_id: Primary key of the document.

        Returns:
            List of versions from oldest to newest.
        """
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == str(document_id))
            .order_by(DocumentVersion.version_number)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_version(
        self, document_id: UUID, version_number: int, project_id: UUID | None = None
    ) -> DocumentVersion | None:
        """Fetch a specific version of a document by version number.

        Args:
            document_id: Primary key of the document.
            version_number: The version number to retrieve.

        Returns:
            The matching version, or None if not found.
        """
        stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == str(document_id),
            DocumentVersion.version_number == version_number,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # --- Internal helpers ---

    async def _get_document_for_project(
        self, document_id: UUID, project_id: UUID
    ) -> Document | None:
        """Fetch a document scoped to a specific project.

        Returns None if the document does not exist or belongs to a
        different project.
        """
        stmt = (
            select(Document)
            .where(Document.id == document_id, Document.project_id == project_id)
            .options(selectinload(Document.current_version))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_document(self, document_id: UUID) -> Document | None:
        """Fetch a document by primary key with current_version eagerly loaded."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.current_version))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_version_by_id(
        self, version_id: str | None
    ) -> DocumentVersion | None:
        """Fetch a document version by primary key."""
        if version_id is None:
            return None
        stmt = select(DocumentVersion).where(DocumentVersion.id == version_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
