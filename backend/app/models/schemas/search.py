"""Search schemas for global cross-entity search API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SearchResultItem(BaseModel):
    """A single search result from any entity type.

    Attributes:
        entity_type: Entity type label (e.g. "project", "wbe", "cost_element").
        id: Version PK (database row ID).
        root_id: Stable root ID (project_id, wbe_id, etc.).
        code: Business code if the entity has one.
        name: Display name if the entity has one.
        description: Description text if available.
        status: Status field if the entity has one.
        relevance_score: Computed relevance score (0.0 - 1.0).
        project_id: Owning project root ID for project-scoped entities.
        wbe_id: Owning WBE root ID for WBE-scoped entities.
    """

    entity_type: str
    id: UUID
    root_id: UUID
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    relevance_score: float
    project_id: UUID | None = None
    wbe_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class GlobalSearchResponse(BaseModel):
    """Response for the global search endpoint.

    Attributes:
        results: Ranked list of search results.
        total: Total number of results returned.
        query: Original search query string.
    """

    results: list[SearchResultItem]
    total: int
    query: str
