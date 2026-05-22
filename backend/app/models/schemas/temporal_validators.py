"""Shared temporal validators for Pydantic schemas.

This module provides reusable type annotations for validating and converting
PostgreSQL TSTZRANGE range objects to string representations in Pydantic models.

Using Pydantic v2's Annotated types with BeforeValidator eliminates the need
for duplicate @field_validator decorators across multiple schema files.
"""

from typing import Annotated, Any

from pydantic import BeforeValidator


def convert_range_to_str(v: Any) -> str | None:
    """Convert PostgreSQL Range object to full range string representation.

    This validator handles TSTZRANGE objects from PostgreSQL and converts them
    to PostgreSQL range strings for API responses. It preserves both lower and
    upper bounds so that temporal computed fields can correctly determine validity.

    Args:
        v: TSTZRANGE range object, string, or None

    Returns:
        PostgreSQL range string (e.g., '["2026-01-15T10:00:00+00:00",)'),
        pre-formatted string, or None

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

    # Convert range object to full PostgreSQL range string
    if hasattr(v, "lower") and v.lower:
        lower = v.lower.isoformat() if hasattr(v.lower, "isoformat") else str(v.lower)
        if hasattr(v, "upper") and v.upper:
            upper = (
                v.upper.isoformat() if hasattr(v.upper, "isoformat") else str(v.upper)
            )
            return f'["{lower}","{upper}")'
        return f'["{lower}",)'

    return str(v)


def convert_range_to_iso(v: Any) -> str | None:
    """Convert TSTZRANGE to PostgreSQL range string.

    This validator preserves the full temporal range (both lower and upper bounds)
    as a PostgreSQL range string. Identical to convert_range_to_str — kept for
    backward compatibility with existing schema references.

    Args:
        v: TSTZRANGE range object, string, or None

    Returns:
        PostgreSQL range string or None

    Examples:
        >>> convert_range_to_iso(None)
        None
        >>> # With a bounded range object
        >>> convert_range_to_iso(range_obj)
        '["2026-01-15T10:00:00+00:00","2026-02-15T10:00:00+00:00")'
    """
    if v is None:
        return None

    if isinstance(v, str):
        return v

    # Extract full TSTZRANGE as PostgreSQL range string
    if hasattr(v, "lower") and v.lower:
        lower = v.lower.isoformat() if hasattr(v.lower, "isoformat") else str(v.lower)
        if hasattr(v, "upper") and v.upper:
            upper = (
                v.upper.isoformat() if hasattr(v.upper, "isoformat") else str(v.upper)
            )
            return f'["{lower}","{upper}")'
        return f'["{lower}",)'

    return str(v)


# Type aliases for use in Pydantic models
TemporalRange = Annotated[str | None, BeforeValidator(convert_range_to_str)]
"""Type alias for temporal range fields that converts range objects to strings."""

TemporalRangeISO = Annotated[str | None, BeforeValidator(convert_range_to_iso)]
"""Type alias for temporal range fields that extracts lower bound as ISO timestamp."""
