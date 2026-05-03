"""TypeAdapter-based response builder for paginated API responses.

This module provides a reusable builder for constructing paginated responses
using Pydantic v2's TypeAdapter for efficient validation and serialization.

Using TypeAdapter is more efficient than manual model_dump() calls for lists
of items, as it provides proper validation and type coercion while maintaining
good performance.

Example:
    >>> from app.models.schemas.project import ProjectRead
    >>> builder = PaginatedResponseBuilder(ProjectRead)
    >>> response = builder.build(items=[...], total=42, page=1, per_page=20)
"""

from typing import Any

from pydantic import TypeAdapter

from app.models.schemas.common import PaginatedResponse


class PaginatedResponseBuilder:
    """Reusable TypeAdapter-based response builder for paginated API responses.

    This builder uses Pydantic v2's TypeAdapter to efficiently validate and
    serialize lists of items for paginated responses. It eliminates the need
    to duplicate validation logic across multiple API endpoints.

    TypeAdapter is more efficient than calling model_dump() on each item
    individually, as it performs validation in a single pass.

    Attributes:
        _type_adapter_str: String representation of the model type for TypeAdapter

    Example:
        >>> from app.models.schemas.project import ProjectRead
        >>> builder = PaginatedResponseBuilder(ProjectRead)
        >>>
        >>> # Build paginated response from database results
        >>> response = builder.build(
        ...     items=db_projects,  # List of SQLAlchemy models or dicts
        ...     total=42,
        ...     page=1,
        ...     per_page=20
        ... )
        >>>
        >>> # Returns dict ready for JSONResponse
        >>> {
        ...     "items": [...],  # Validated and serialized ProjectRead objects
        ...     "total": 42,
        ...     "page": 1,
        ...     "per_page": 20
        ... }
    """

    def __init__(self, model_class: type) -> None:
        """Initialize the builder with a Pydantic model class.

        Args:
            model_class: Pydantic model class (e.g., ProjectRead, WBERead)

        Example:
            >>> builder = PaginatedResponseBuilder(ProjectRead)
        """
        self._model_class = model_class
        self._type_adapter_str = f"list[{model_class.__name__}]"

    def build(
        self,
        items: list[Any],
        total: int,
        page: int,
        per_page: int,
    ) -> dict[str, Any]:
        """Build paginated response with validated items.

        This method validates and serializes the input items using the
        TypeAdapter, then constructs a complete paginated response.

        Args:
            items: List of items to validate and serialize
                          (SQLAlchemy models, dicts, or Pydantic models)
            total: Total count of items matching filters (across all pages)
            page: Current page number (1-indexed)
            per_page: Number of items per page

        Returns:
            Dictionary with paginated response data

        Raises:
            ValidationError: If items fail validation against the model type

        Example:
            >>> builder = PaginatedResponseBuilder(ProjectRead)
            >>> response = builder.build(
            ...     items=db_projects,
            ...     total=42,
            ...     page=1,
            ...     per_page=20
            ... )
        """
        # Create TypeAdapter for the model class at runtime
        # We need to construct this dynamically to work with any model type
        # This is a known limitation of mypy with runtime type construction
        model_cls = self._model_class
        type_adapter = TypeAdapter(list[model_cls])  # type: ignore[valid-type]

        # Validate and serialize items using TypeAdapter
        # This is more efficient than calling model_dump() on each item
        validated_items = type_adapter.validate_python(items)

        # Build paginated response
        response = PaginatedResponse[Any](
            items=validated_items,
            total=total,
            page=page,
            per_page=per_page,
        )

        # Return as dict for JSONResponse
        return response.model_dump()
