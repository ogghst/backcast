"""Generic paginated response schema."""

from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse[T](BaseModel):
    """Generic paginated response with items and metadata.

    Used for list endpoints that support server-side pagination,
    filtering, and sorting.

    Attributes:
        items: List of items for current page
        total: Total count of items matching filters (across all pages)
        page: Current page number (1-indexed)
        per_page: Number of items per page
        pages: Total number of pages

    Examples:
        >>> response = PaginatedResponse[ProjectPublic](
        ...     items=[project1, project2],
        ...     total=42,
        ...     page=1,
        ...     per_page=20
        ... )
        >>> response.pages
        3
    """

    items: list[T] = Field(description="List of items for current page")
    total: int = Field(description="Total count of items matching filters")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(ge=1, description="Number of items per page")

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.per_page == 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    model_config = {"from_attributes": True}
