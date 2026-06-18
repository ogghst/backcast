"""Tests for the ``add_document`` AI tool.

The tool instantiates ``DocumentService(context.session)`` internally, so we
patch ``app.ai.tools.document_tools.DocumentService`` with a ``MagicMock``
whose ``upload_document`` / ``update_metadata`` are ``AsyncMock`` returning a
stub document. This keeps every test fully DB-free.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools.document_tools import add_document
from app.ai.tools.types import ToolContext

# ``@ai_tool`` replaces the module name ``add_document`` with a LangChain
# ``StructuredTool``. ``.coroutine`` is the decorator's session-managing
# wrapper, and ``__wrapped__`` is the original async function with no session
# side effects -- what we want for a pure unit test.
_add_document_raw = add_document.coroutine.__wrapped__  # type: ignore[attr-defined]

_USER_ID = "00000000-0000-0000-0000-000000000001"
_PROJECT_ID = "00000000-0000-0000-0000-0000000000aa"
_DOC_ID = uuid.UUID("00000000-0000-0000-0000-0000000000b1")


class _StubVersion:
    """Minimal stand-in for a DocumentVersion row."""

    def __init__(self, version_number: int = 1) -> None:
        self.version_number = version_number
        self.extracted_text = "stub text"


class _StubDocument:
    """Minimal stand-in for a Document ORM row.

    Only attributes read by ``add_document``'s result dict are set.
    """

    def __init__(
        self,
        *,
        doc_id: uuid.UUID = _DOC_ID,
        name: str = "report.md",
        extension: str = "md",
        folder_id: uuid.UUID | None = None,
        size_bytes: int = 42,
        description: str | None = None,
        tags: list[str] | None = None,
        version_number: int | None = 1,
    ) -> None:
        self.id = doc_id
        self.name = name
        self.extension = extension
        self.folder_id = folder_id
        self.size_bytes = size_bytes
        self.description = description
        self.tags = tags if tags is not None else []
        self.current_version = (
            _StubVersion(version_number) if version_number is not None else None
        )


def _make_context(project_id: str | None = _PROJECT_ID) -> ToolContext:
    return ToolContext(
        session=MagicMock(),
        user_id=_USER_ID,
        project_id=project_id,
    )


def _patch_document_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    upload_document_return: Any = None,
    upload_document_side_effect: Any = None,
    update_metadata_return: Any = None,
) -> MagicMock:
    """Patch ``DocumentService`` in the tool module with a controlled mock.

    Returns the mock service instance so tests can assert on call args.
    """
    service_instance = MagicMock()
    if upload_document_side_effect is not None:
        service_instance.upload_document = AsyncMock(
            side_effect=upload_document_side_effect
        )
    else:
        service_instance.upload_document = AsyncMock(
            return_value=upload_document_return or _StubDocument()
        )
    service_instance.update_metadata = AsyncMock(
        return_value=update_metadata_return or _StubDocument()
    )

    mock_service_cls = MagicMock(return_value=service_instance)
    monkeypatch.setattr("app.ai.tools.document_tools.DocumentService", mock_service_cls)
    return service_instance


@pytest.mark.asyncio
async def test_text_content_creates_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plain text content creates a document and returns id/name/version/message."""
    stub = _StubDocument(name="report.md", extension="md", version_number=1)
    _patch_document_service(monkeypatch, upload_document_return=stub)
    ctx = _make_context()

    result = await _add_document_raw(
        filename="report.md", content="# Hello", context=ctx
    )

    assert isinstance(result, dict)
    assert "error" not in result, f"unexpected error: {result.get('error')}"
    assert result["id"] == str(_DOC_ID)
    assert result["name"] == "report.md"
    assert result["extension"] == "md"
    assert result["version"] == 1
    assert result["message"] == "Document 'report.md' created successfully"


@pytest.mark.asyncio
async def test_base64_content_creates_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid base64_content creates a document (binary path)."""
    import base64

    stub = _StubDocument(name="slide.pptx", extension="pptx", version_number=1)
    service = _patch_document_service(monkeypatch, upload_document_return=stub)
    ctx = _make_context()

    payload = base64.b64encode(b"binary-pptx-bytes").decode("ascii")
    result = await _add_document_raw(
        filename="slide.pptx", base64_content=payload, context=ctx
    )

    assert "error" not in result
    assert result["extension"] == "pptx"
    # The decoded bytes must match what was encoded.
    sent_bytes = service.upload_document.call_args.args[3]
    assert sent_bytes == b"binary-pptx-bytes"


@pytest.mark.asyncio
async def test_both_content_sources_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Providing both content and base64_content is ambiguous -> error."""
    _patch_document_service(monkeypatch)
    ctx = _make_context()

    result = await _add_document_raw(
        filename="report.md",
        content="hello",
        base64_content="aGVsbG8=",
        context=ctx,
    )

    assert "error" in result
    assert "exactly one" in result["error"]


@pytest.mark.asyncio
async def test_neither_content_source_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Providing neither content nor base64_content -> error."""
    _patch_document_service(monkeypatch)
    ctx = _make_context()

    result = await _add_document_raw(filename="report.md", context=ctx)

    assert "error" in result
    assert "exactly one" in result["error"]


@pytest.mark.asyncio
async def test_no_project_context_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When project_id is None the tool returns the 'No project context' error."""
    _patch_document_service(monkeypatch)
    ctx = _make_context(project_id=None)

    result = await _add_document_raw(filename="report.md", content="hello", context=ctx)

    assert "error" in result
    assert "No project context" in result["error"]


@pytest.mark.asyncio
async def test_invalid_base64_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed base64_content -> error dict (not an exception)."""
    _patch_document_service(monkeypatch)
    ctx = _make_context()

    result = await _add_document_raw(
        filename="file.bin", base64_content="@@@not-base64@@@", context=ctx
    )

    assert "error" in result
    assert "Invalid base64_content" in result["error"]


@pytest.mark.asyncio
async def test_disallowed_extension_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ValueError from upload_document (e.g. disallowed ext) -> error dict."""
    _patch_document_service(
        monkeypatch,
        upload_document_side_effect=ValueError("File extension '.exe' is not allowed"),
    )
    ctx = _make_context()

    result = await _add_document_raw(filename="malware.exe", content="x", context=ctx)

    assert "error" in result
    assert "Invalid input" in result["error"]
    assert ".exe" in result["error"]


@pytest.mark.asyncio
async def test_description_and_tags_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When description/tags are given, update_metadata is called and reflected."""
    stub_after_update = _StubDocument(
        name="invoice.pdf",
        extension="pdf",
        description="May invoice",
        tags=["finance", "invoice"],
    )
    service = _patch_document_service(
        monkeypatch, update_metadata_return=stub_after_update
    )
    ctx = _make_context()

    result = await _add_document_raw(
        filename="invoice.pdf",
        content="hello",
        description="May invoice",
        tags=["finance", "invoice"],
        context=ctx,
    )

    assert "error" not in result
    assert service.update_metadata.await_count == 1
    assert result["description"] == "May invoice"
    assert result["tags"] == ["finance", "invoice"]
