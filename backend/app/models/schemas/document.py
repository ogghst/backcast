"""Pydantic schemas for Document Repository."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- Enums ---


class EntityType(str, Enum):
    """Entity types that documents can be linked to."""

    WBE = "wbe"
    COST_ELEMENT = "cost_element"
    CHANGE_ORDER = "change_order"
    PROJECT = "project"


# --- Folder schemas ---


class DocumentFolderCreate(BaseModel):
    """Properties required for creating a folder."""

    name: str
    parent_id: UUID | None = None


class DocumentFolderUpdate(BaseModel):
    """Properties that can be updated on a folder."""

    name: str | None = None
    parent_id: UUID | None = None


class DocumentFolderPublic(BaseModel):
    """Folder representation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    parent_id: UUID | None
    name: str
    path: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# --- Version schemas ---


class DocumentVersionPublic(BaseModel):
    """Document version representation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version_number: int
    content_type: str
    size_bytes: int
    checksum_sha256: str
    uploaded_by: UUID
    created_at: datetime


# --- Document schemas ---


class DocumentUpdate(BaseModel):
    """Properties that can be updated on a document."""

    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class DocumentPublic(BaseModel):
    """Document representation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    folder_id: UUID | None
    name: str
    extension: str
    description: str | None
    tags: list[str]
    current_version: DocumentVersionPublic | None = None
    is_locked: bool
    locked_by: UUID | None
    created_by: UUID
    size_bytes: int
    created_at: datetime
    updated_at: datetime


# --- Entity link schemas ---


class DocumentLinkCreate(BaseModel):
    """Properties required for linking a document to an entity."""

    entity_type: EntityType
    entity_id: UUID
    note: str | None = None


class DocumentLinkUpdate(BaseModel):
    """Properties that can be updated on a document link."""

    note: str


class DocumentLinkPublic(BaseModel):
    """Document entity link representation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    entity_type: str
    entity_id: UUID
    note: str | None
    created_at: datetime


# --- Search ---


class DocumentSearchQuery(BaseModel):
    """Parameters for searching documents."""

    query: str
    folder_id: UUID | None = None
    tags: list[str] | None = None
    extension: str | None = None
    skip: int = 0
    limit: int = 50


# --- Storage stats ---


class StorageStatsPublic(BaseModel):
    """Storage usage statistics for a project."""

    total_bytes: int
    file_count: int
    version_count: int
