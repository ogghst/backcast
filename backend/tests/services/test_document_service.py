"""Service-level tests for DocumentService.

These tests use a real database session so SQLAlchemy relationship loading
behavior — including ``lazy="raise"`` — is exercised faithfully. Storage
(S3) and text-extraction are stubbed only where a method actually calls
them; ``update_metadata`` touches neither.
"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.document import DocumentUpdate
from app.services.document_service import DocumentService
from tests.factories import create_test_project


def _stub_storage(service: DocumentService) -> None:
    """Avoid real S3 during upload_document in tests."""
    service._storage.upload_file = AsyncMock(return_value=None)  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_update_metadata_keeps_current_version_loadable(
    db: AsyncSession, actor_id: UUID
) -> None:
    """update_metadata must not expire the lazy='raise' current_version rel.

    Regression: a bare ``Session.refresh(document)`` expires *all* attributes
    including ``current_version`` (declared ``lazy="raise"``). Any subsequent
    access — e.g. by the add_document AI tool or the HTTP PUT/POST routes
    returning DocumentPublic — raised
    ``'Document.current_version' is not available due to lazy='raise'``.
    """
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = DocumentService(db)
    _stub_storage(service)
    created = await service.upload_document(
        project_id=project.project_id,
        folder_id=None,
        filename="spec.txt",
        content=b"hello",
        content_type="text/plain",
        user_id=actor_id,
    )
    await db.commit()

    updated = await service.update_metadata(
        created.id,
        DocumentUpdate(description="Updated description", tags=["a", "b"]),
        project_id=project.project_id,
    )

    # This access is the regression trigger — must not raise.
    assert updated.current_version is not None
    assert updated.current_version.version_number == 1

    # Mutated fields were applied.
    assert updated.description == "Updated description"
    assert updated.tags == ["a", "b"]


@pytest.mark.asyncio
async def test_get_document_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_document should populate created_by_name from the creator user."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = DocumentService(db)
    _stub_storage(service)
    created = await service.upload_document(
        project_id=project.project_id,
        folder_id=None,
        filename="report.txt",
        content=b"content",
        content_type="text/plain",
        user_id=actor_id,
    )
    await db.commit()

    found = await service.get_document(created.id, project_id=project.project_id)
    assert found is not None
    assert found.created_by_name == "Admin User"


@pytest.mark.asyncio
async def test_list_documents_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """list_documents should populate created_by_name on each document."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = DocumentService(db)
    _stub_storage(service)
    await service.upload_document(
        project_id=project.project_id,
        folder_id=None,
        filename="a.txt",
        content=b"a",
        content_type="text/plain",
        user_id=actor_id,
    )
    await db.commit()

    documents = await service.list_documents(project_id=project.project_id)
    assert len(documents) >= 1
    assert all(hasattr(d, "created_by_name") for d in documents)
    assert any(d.created_by_name == "Admin User" for d in documents)
