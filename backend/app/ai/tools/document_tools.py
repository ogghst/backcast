"""AI tools for document repository access."""

import base64
import binascii
import logging
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.document import DocumentFolderCreate, DocumentUpdate
from app.services.document_folder_service import DocumentFolderService
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

# Filename extension -> MIME content type. Used to infer content_type when an
# AI specialist saves a document from raw text or base64 bytes. Default fallback
# is "application/octet-stream" for unknown extensions.
_CONTENT_TYPE_BY_EXTENSION: dict[str, str] = {
    "md": "text/markdown",
    "txt": "text/plain",
    "csv": "text/csv",
    "html": "text/html",
    "json": "application/json",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
}


@ai_tool(
    name="search_documents",
    description="Search project documents by filename.",
    permissions=["project-documents-read"],
    category="context",
    risk_level=RiskLevel.LOW,
)
async def search_documents(
    query: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Search documents in the current project by name.

    Args:
        query: Search term to match against document names. When None, returns all documents.
        context: Injected tool execution context

    Returns:
        Dictionary containing:
            - documents: List of matching documents with id, name, extension, size_bytes,
              description, tags, created_at
            - total: Number of results returned
    """
    if not context.project_id:
        return {"error": "No project context available. Open a project first."}

    service = DocumentService(context.session)

    if query:
        results = await service.search_documents(UUID(context.project_id), query)
    else:
        results = await service.list_documents(UUID(context.project_id))

    documents = []
    for doc in results[:20]:
        entry = {
            "id": str(doc.id),
            "name": doc.name,
            "extension": doc.extension,
            "size_bytes": doc.size_bytes,
            "description": doc.description,
            "tags": doc.tags,
            "created_at": str(doc.created_at),
        }
        if doc.current_version:
            entry["version"] = doc.current_version.version_number
        documents.append(entry)
    return {"documents": documents, "total": len(documents)}


@ai_tool(
    name="read_document",
    description="Read extracted text content of a document.",
    permissions=["project-documents-read"],
    category="context",
    risk_level=RiskLevel.LOW,
)
async def read_document(
    document_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get extracted text content for a document.

    Args:
        document_id: Document UUID string
        context: Injected tool execution context

    Returns:
        Dictionary containing:
            - id: Document ID
            - name: Document filename
            - extension: File extension
            - description: Document description
            - tags: Document tags
            - size_bytes: File size in bytes
            - content: Extracted text (truncated at 10000 chars if longer)
            - content_truncated: Whether content was truncated
    """
    service = DocumentService(context.session)
    doc = await service.get_document(UUID(document_id))
    if doc is None:
        return {"error": f"Document {document_id} not found"}

    result: dict[str, Any] = {
        "id": str(doc.id),
        "name": doc.name,
        "extension": doc.extension,
        "description": doc.description,
        "tags": doc.tags,
        "size_bytes": doc.size_bytes,
    }

    if doc.current_version and doc.current_version.extracted_text:
        text = doc.current_version.extracted_text
        max_chars = 10000
        result["content"] = text[:max_chars] + ("..." if len(text) > max_chars else "")
        result["content_truncated"] = len(text) > max_chars
    else:
        result["content"] = None
        result["note"] = "No text content available for this document type"

    return result


@ai_tool(
    name="add_document",
    description=(
        "Create and save a document in the current project's repository (invoice, "
        "markdown/text report, or binary file from an MCP tool). Provide contents as "
        "EITHER 'content' (plain text) OR 'base64_content' (base64 bytes) — exactly one. "
        "'filename' must end with an allowed extension (pdf, docx, xlsx, pptx, txt, csv, "
        "md, png, jpg, jpeg, gif, webp, svg, zip, ...); 'folder_id' optionally places it "
        "in an existing folder (None = project root)."
    ),
    permissions=["project-documents-write"],
    category="documents",
    risk_level=RiskLevel.HIGH,
)
async def add_document(
    filename: str,
    content: str | None = None,
    base64_content: str | None = None,
    folder_id: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a document in the current project's document repository.

    Args:
        filename: Filename including extension (e.g. "invoice_123.pdf", "report.md").
        content: Plain-text file contents (UTF-8). Use for markdown, txt, csv, etc.
        base64_content: Base64-encoded raw bytes. Use for binary files (pdf, pptx, docx, images).
        folder_id: Optional existing folder UUID to place the document in (None = project root).
        description: Optional human-readable description.
        tags: Optional list of tags.
        context: Injected tool execution context.

    Returns:
        Dictionary with id, name, extension, folder_id, version, size_bytes,
        description, tags, and a confirmation message. On error returns {"error": ...}.
    """
    if not context.project_id:
        return {"error": "No project context available. Open a project first."}

    # Exactly one content source (XOR)
    if (content is None) == (base64_content is None):
        return {
            "error": "Provide exactly one of 'content' (text) or 'base64_content' (binary)."
        }

    # Decode to raw bytes
    if content is not None:
        raw_bytes = content.encode("utf-8")
    else:
        try:
            assert base64_content is not None  # for type checker
            raw_bytes = base64.b64decode(base64_content, validate=True)
        except (ValueError, binascii.Error) as e:
            return {"error": f"Invalid base64_content: {e}"}

    # Infer content_type from extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_type = _CONTENT_TYPE_BY_EXTENSION.get(ext, "application/octet-stream")

    try:
        service = DocumentService(context.session)
        doc = await service.upload_document(
            UUID(context.project_id),
            folder_id,
            filename,
            raw_bytes,
            content_type,
            UUID(context.user_id),
        )

        if description is not None or tags is not None:
            doc = await service.update_metadata(
                doc.id,
                DocumentUpdate(description=description, tags=tags),
                UUID(context.project_id),
            )

        return {
            "id": str(doc.id),
            "name": doc.name,
            "extension": doc.extension,
            "folder_id": doc.folder_id,
            "version": doc.current_version.version_number
            if doc.current_version
            else None,
            "size_bytes": doc.size_bytes,
            "description": doc.description,
            "tags": doc.tags,
            "message": f"Document '{filename}' created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in add_document: {e}")
        return {"error": str(e)}


@ai_tool(
    name="list_folders",
    description=(
        "List all document folders in the current project as a tree. "
        "Returns each folder's id, name, path, and parent_id. Use this to discover a folder_id "
        "to pass to add_document or create_folder's parent_id."
    ),
    permissions=["project-documents-read"],
    category="documents",
    risk_level=RiskLevel.LOW,
)
async def list_folders(
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List all document folders in the current project.

    Args:
        context: Injected tool execution context.

    Returns:
        Dictionary with 'folders' (list of {id, name, path, parent_id}) and 'total'.
    """
    if not context.project_id:
        return {"error": "No project context available. Open a project first."}

    try:
        service = DocumentFolderService(context.session)
        folders = await service.get_folder_tree(UUID(context.project_id))
        folder_list = [
            {
                "id": str(f.id),
                "name": f.name,
                "path": f.path,
                "parent_id": str(f.parent_id) if f.parent_id else None,
            }
            for f in folders
        ]
        return {"folders": folder_list, "total": len(folder_list)}
    except Exception as e:
        logger.error(f"Error in list_folders: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_folder",
    description=(
        "Create a document folder in the current project's repository. "
        "Provide a folder name; optionally a parent_id to nest it under an existing folder "
        "(omit for a root-level folder). Returns the new folder id, name, and path."
    ),
    permissions=["project-documents-write"],
    category="documents",
    risk_level=RiskLevel.HIGH,
)
async def create_folder(
    name: str,
    parent_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a document folder in the current project.

    Args:
        name: Folder name.
        parent_id: Optional parent folder UUID to nest under (None = root).
        context: Injected tool execution context.

    Returns:
        Dictionary with id, name, path, parent_id, and a confirmation message.
    """
    if not context.project_id:
        return {"error": "No project context available. Open a project first."}

    try:
        data = DocumentFolderCreate(
            name=name, parent_id=UUID(parent_id) if parent_id else None
        )
        service = DocumentFolderService(context.session)
        folder = await service.create_folder(
            UUID(context.project_id), data, UUID(context.user_id)
        )
        return {
            "id": str(folder.id),
            "name": folder.name,
            "path": folder.path,
            "parent_id": str(folder.parent_id) if folder.parent_id else None,
            "message": f"Folder '{name}' created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_folder: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_folder",
    description=(
        "Delete a document folder and ALL its sub-folders in the current project. "
        "CRITICAL: requires expert execution mode. Documents inside the folder are NOT deleted "
        "(they are left unfiled with a cleared folder reference) — move or delete documents first if needed. "
        "Provide the folder id."
    ),
    permissions=["project-documents-delete"],
    category="documents",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_folder(
    folder_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Delete a document folder and its descendants in the current project.

    Args:
        folder_id: UUID of the folder to delete.
        context: Injected tool execution context.

    Returns:
        Dictionary with folder_id and a confirmation message, or an error.
    """
    if not context.project_id:
        return {"error": "No project context available. Open a project first."}

    try:
        service = DocumentFolderService(context.session)
        deleted = await service.delete_folder(UUID(folder_id), UUID(context.project_id))
        if not deleted:
            return {"error": f"Folder {folder_id} not found in this project"}
        return {
            "folder_id": folder_id,
            "message": f"Folder {folder_id} and its sub-folders deleted",
        }
    except Exception as e:
        logger.error(f"Error in delete_folder: {e}")
        return {"error": str(e)}
