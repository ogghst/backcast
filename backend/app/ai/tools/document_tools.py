"""AI tools for document repository access."""

import logging
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


@ai_tool(
    name="search_documents",
    description="Search project documents by filename. Returns matching documents with metadata.",
    permissions=["project-documents-read"],
    category="documents",
    risk_level=RiskLevel.LOW,
)
async def search_documents(
    query: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Search documents in the current project by name.

    Args:
        query: Search term to match against document names
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
    results = await service.search_documents(UUID(context.project_id), query)

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
    description="Read the extracted text content of a specific document. Use search_documents first to find relevant documents.",
    permissions=["project-documents-read"],
    category="documents",
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
    name="list_documents",
    description="List documents in the current project, optionally filtered by folder. Returns document metadata.",
    permissions=["project-documents-read"],
    category="documents",
    risk_level=RiskLevel.LOW,
)
async def list_documents(
    folder_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List documents in the current project.

    Args:
        folder_id: Optional folder UUID to filter by
        skip: Number of records to skip for pagination (default 0)
        limit: Maximum records to return (default 20)
        context: Injected tool execution context

    Returns:
        Dictionary containing:
            - documents: List of documents with id, name, extension, size_bytes,
              description, tags, is_locked, created_at
            - count: Number of documents returned
    """
    if not context.project_id:
        return {"error": "No project context available. Open a project first."}

    service = DocumentService(context.session)
    docs = await service.list_documents(
        UUID(context.project_id),
        folder_id=folder_id,
        skip=skip,
        limit=limit,
    )

    documents = []
    for doc in docs:
        documents.append({
            "id": str(doc.id),
            "name": doc.name,
            "extension": doc.extension,
            "size_bytes": doc.size_bytes,
            "description": doc.description,
            "tags": doc.tags,
            "is_locked": doc.is_locked,
            "created_at": str(doc.created_at),
        })
    return {"documents": documents, "count": len(documents)}
