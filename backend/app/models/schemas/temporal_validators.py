"""Shared temporal validators for Pydantic schemas.

This module provides reusable type annotations for validating and converting
PostgreSQL TSTZRANGE range objects to string representations in Pydantic models.

Using Pydantic v2's Annotated types with BeforeValidator eliminates the need
for duplicate @field_validator decorators across multiple schema files.
"""

from typing import Annotated, Any

from pydantic import BeforeValidator


def convert_range_to_str(v: Any) -> str | None:
    """Convert PostgreSQL Range object to string representation.

    This validator handles TSTZRANGE objects from PostgreSQL and converts them
    to strings for API responses. It handles both range objects (with .lower/.upper)
    and pre-formatted strings.

    Args:
        v: TSTZRANGE range object, string, or None

    Returns:
        String representation of the range, ISO timestamp of lower bound,
        or None if input is None

    Examples:
        >>> convert_range_to_str(None)
        None
        >>> convert_range_to_str("[\\"2026-01-15 10:00:00+00\\",)")
        '["2026-01-15 10:00:00+00",)'
        >>> convert_range_to_str("2026-01-15T10:00:00+00:00")
        '2026-01-15T10:00:00+00:00'
    """
    if v is None:
        return None

    # If already a string, return as-is
    if isinstance(v, str):
        return v

    # Convert range object to string
    # Extract lower bound as ISO timestamp if available
    if hasattr(v, "lower") and v.lower:
        # Return ISO timestamp of lower bound (more useful for frontend)
        return v.lower.isoformat() if hasattr(v.lower, "isoformat") else str(v.lower)

    return str(v)


def convert_range_to_iso(v: Any) -> str | None:
    """Convert TSTZRANGE to ISO 8601 timestamp string (lower bound).

    This is a specialized variant that extracts only the lower bound as an
    ISO 8601 formatted timestamp, which is more useful for frontend consumption.

    Args:
        v: TSTZRANGE range object, string, or None

    Returns:
        ISO 8601 formatted timestamp string or None

    Examples:
        >>> convert_range_to_iso(None)
        None
        >>> # With a range object with lower bound
        >>> convert_range_to_iso(range_obj)
        '2026-01-15T10:00:00+00:00'
    """
    if v is None:
        return None

    if isinstance(v, str):
        return v

    # Extract lower bound from TSTZRANGE and format as ISO 8601
    if hasattr(v, "lower") and v.lower:
        return v.lower.isoformat() if hasattr(v.lower, "isoformat") else str(v.lower)

    return str(v)


# Type aliases for use in Pydantic models
TemporalRange = Annotated[str | None, BeforeValidator(convert_range_to_str)]
"""Type alias for temporal range fields that converts range objects to strings."""

TemporalRangeISO = Annotated[str | None, BeforeValidator(convert_range_to_iso)]
"""Type alias for temporal range fields that extracts lower bound as ISO timestamp."""
