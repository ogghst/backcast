"""Document repository API routes - upload, versioning, search, linking."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import ProjectRoleChecker, UserIdentity
from app.db.session import get_db
from app.models.schemas.document import (
    DocumentFolderCreate,
    DocumentFolderPublic,
    DocumentFolderUpdate,
    DocumentLinkCreate,
    DocumentLinkPublic,
    DocumentLinkUpdate,
    DocumentPublic,
    DocumentUpdate,
    DocumentVersionPublic,
    StorageStatsPublic,
)
from app.services.document_folder_service import DocumentFolderService
from app.services.document_service import DocumentService

router = APIRouter()


# ---------------------------------------------------------------------------
# Folder endpoints
# ---------------------------------------------------------------------------


@router.post("/{project_id}/documents/folders", response_model=DocumentFolderPublic, status_code=201)
async def create_folder(
    project_id: UUID,
    data: DocumentFolderCreate,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentFolderPublic:
    """Create a new folder in the project document tree."""
    service = DocumentFolderService(db)
    folder = await service.create_folder(project_id, data, current_user.user_id)
    return folder  # type: ignore[return-value]


@router.get("/{project_id}/documents/folders", response_model=list[DocumentFolderPublic])
async def list_folders(
    project_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentFolderPublic]:
    """Return the full folder tree for a project, ordered by path."""
    service = DocumentFolderService(db)
    return await service.get_folder_tree(project_id)  # type: ignore[return-value]


@router.put("/{project_id}/documents/folders/{folder_id}", response_model=DocumentFolderPublic)
async def update_folder(
    project_id: UUID,
    folder_id: UUID,
    data: DocumentFolderUpdate,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentFolderPublic:
    """Rename or move a folder. At least one field must be provided."""
    service = DocumentFolderService(db)
    if data.name is not None:
        return await service.rename_folder(folder_id, data.name)  # type: ignore[return-value]
    if data.parent_id is not None:
        return await service.move_folder(folder_id, data.parent_id)  # type: ignore[return-value]
    raise HTTPException(status_code=400, detail="No update fields provided")


@router.delete("/{project_id}/documents/folders/{folder_id}", status_code=204)
async def delete_folder(
    project_id: UUID,
    folder_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-delete")
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a folder and all its descendants."""
    service = DocumentFolderService(db)
    await service.delete_folder(folder_id, project_id)


# ---------------------------------------------------------------------------
# Document upload (multipart)
# ---------------------------------------------------------------------------


@router.post("/{project_id}/documents/upload", response_model=DocumentPublic, status_code=201)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    folder_id: str | None = Form(None),
    description: str | None = Form(None),
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublic:
    """Upload a new document with its first version."""
    content = await file.read()
    service = DocumentService(db)
    document = await service.upload_document(
        project_id=project_id,
        folder_id=folder_id,
        filename=file.filename or "untitled",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        user_id=current_user.user_id,
    )
    if description:
        document = await service.update_metadata(
            document.id, DocumentUpdate(description=description)
        )
    return document  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------


@router.get("/{project_id}/documents/", response_model=list[DocumentPublic])
async def list_documents(
    project_id: UUID,
    folder_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentPublic]:
    """List documents for a project, optionally filtered by folder."""
    service = DocumentService(db)
    return await service.list_documents(project_id, str(folder_id) if folder_id else None, skip, limit)  # type: ignore[return-value]


@router.get("/{project_id}/documents/search", response_model=list[DocumentPublic])
async def search_documents(
    project_id: UUID,
    query: str = Query(..., min_length=1),
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentPublic]:
    """Search documents by name within a project."""
    service = DocumentService(db)
    return await service.search_documents(project_id, query)  # type: ignore[return-value]


@router.get("/{project_id}/documents/storage-stats", response_model=StorageStatsPublic)
async def get_storage_stats(
    project_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> StorageStatsPublic:
    """Compute storage usage statistics for a project."""
    service = DocumentService(db)
    return await service.get_storage_usage(project_id)


@router.get("/{project_id}/documents/{document_id}", response_model=DocumentPublic)
async def get_document(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublic:
    """Fetch a single document with its current version."""
    service = DocumentService(db)
    doc = await service.get_document(document_id, project_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc  # type: ignore[return-value]


@router.put("/{project_id}/documents/{document_id}", response_model=DocumentPublic)
async def update_document(
    project_id: UUID,
    document_id: UUID,
    data: DocumentUpdate,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublic:
    """Update document metadata (name, description, tags)."""
    service = DocumentService(db)
    return await service.update_metadata(document_id, data, project_id)  # type: ignore[return-value]


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
async def delete_document(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-delete")
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document and all its versions, links, and stored files."""
    service = DocumentService(db)
    await service.delete_document(document_id, project_id)


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


@router.post("/{project_id}/documents/upload-version/{document_id}", response_model=DocumentVersionPublic, status_code=201)
async def upload_new_version(
    project_id: UUID,
    document_id: UUID,
    file: UploadFile = File(...),
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentVersionPublic:
    """Upload a new version of an existing document."""
    content = await file.read()
    service = DocumentService(db)
    return await service.upload_new_version(  # type: ignore[return-value]
        document_id,
        content,
        file.content_type or "application/octet-stream",
        current_user.user_id,
        project_id,
    )


@router.get("/{project_id}/documents/{document_id}/download")
async def download_document(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Generate a presigned download URL for the document's current version."""
    service = DocumentService(db)
    url = await service.download_document(document_id, project_id)
    return {"url": url}


@router.get("/{project_id}/documents/{document_id}/versions", response_model=list[DocumentVersionPublic])
async def get_version_history(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentVersionPublic]:
    """Fetch all versions for a document, ordered by version number."""
    service = DocumentService(db)
    return await service.get_version_history(document_id, project_id)  # type: ignore[return-value]


@router.get("/{project_id}/documents/{document_id}/versions/{version_number}", response_model=DocumentVersionPublic)
async def get_version(
    project_id: UUID,
    document_id: UUID,
    version_number: int,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentVersionPublic:
    """Fetch a specific version of a document by version number."""
    service = DocumentService(db)
    version = await service.get_version(document_id, version_number, project_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------


@router.put("/{project_id}/documents/{document_id}/lock", response_model=DocumentPublic)
async def lock_document(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublic:
    """Lock a document for exclusive editing."""
    service = DocumentService(db)
    return await service.lock_document(document_id, current_user.user_id, project_id)  # type: ignore[return-value]


@router.delete("/{project_id}/documents/{document_id}/lock", response_model=DocumentPublic)
async def unlock_document(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublic:
    """Unlock a document."""
    service = DocumentService(db)
    return await service.unlock_document(document_id, current_user.user_id, project_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Entity linking
# ---------------------------------------------------------------------------


@router.post("/{project_id}/documents/{document_id}/links", response_model=DocumentLinkPublic, status_code=201)
async def link_document(
    project_id: UUID,
    document_id: UUID,
    data: DocumentLinkCreate,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentLinkPublic:
    """Link a document to a domain entity (WBE, cost element, etc.)."""
    service = DocumentService(db)
    return await service.link_document(  # type: ignore[return-value]
        document_id, data.entity_type.value, str(data.entity_id), data.note
    )


@router.delete("/{project_id}/documents/{document_id}/links/{entity_type}/{entity_id}", status_code=204)
async def unlink_document(
    project_id: UUID,
    document_id: UUID,
    entity_type: str,
    entity_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a link between a document and an entity."""
    service = DocumentService(db)
    await service.unlink_document(document_id, entity_type, str(entity_id))


@router.put("/{project_id}/documents/{document_id}/links/{entity_type}/{entity_id}", response_model=DocumentLinkPublic)
async def update_link_note(
    project_id: UUID,
    document_id: UUID,
    entity_type: str,
    entity_id: UUID,
    data: DocumentLinkUpdate,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-write")
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentLinkPublic:
    """Update the note on a document-entity link."""
    service = DocumentService(db)
    link = await service.update_link_note(
        document_id, entity_type, str(entity_id), data.note
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return link  # type: ignore[return-value]


@router.get("/{project_id}/documents/{document_id}/links", response_model=list[DocumentLinkPublic])
async def get_linked_entities(
    project_id: UUID,
    document_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentLinkPublic]:
    """Fetch all entity links for a specific document."""
    service = DocumentService(db)
    return await service.get_linked_entities(document_id)  # type: ignore[return-value]


@router.get("/{project_id}/documents/linked/{entity_type}/{entity_id}", response_model=list[DocumentPublic])
async def get_linked_documents(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    current_user: UserIdentity = Depends(
        ProjectRoleChecker(required_permission="project-documents-read")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentPublic]:
    """Fetch all documents linked to a specific domain entity."""
    service = DocumentService(db)
    return await service.get_linked_documents(entity_type, str(entity_id))  # type: ignore[return-value]
