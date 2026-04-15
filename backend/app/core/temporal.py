"""Temporal data formatting utilities for PostgreSQL TSTZRANGE fields.

This module provides utilities to convert PostgreSQL TSTZRANGE database
values into display-ready formats for API responses. This keeps the
frontend decoupled from database-specific serialization details.
"""

from datetime import datetime
from typing import Any


def format_temporal_range_for_api(
    range_value: Any,
) -> dict[str, str | None]:
    """Convert PostgreSQL TSTZRANGE to display-ready format.

    Extracts temporal range information and returns both raw ISO timestamps
    and formatted display strings. This allows the frontend to simply
    display pre-formatted dates without parsing PostgreSQL range syntax.

    Args:
        range_value: TSTZRANGE value from database (can be range object,
                     pre-formatted string, or None)

    Returns:
        Dictionary with:
            - lower: ISO 8601 timestamp of lower bound or None
            - upper: ISO 8601 timestamp of upper bound or None (None if unbounded)
            - lower_formatted: Human-readable lower bound date (e.g., "Jan 15, 2026")
            - upper_formatted: "Present" if unbounded, or formatted upper date
            - is_currently_valid: True if the range is currently valid (unbounded upper)

    Examples:
        >>> format_temporal_range_for_api("[\\"2026-01-15 10:00:00+00\\",)")
        {
            "lower": "2026-01-15T10:00:00+00:00",
            "upper": None,
            "lower_formatted": "January 15, 2026",
            "upper_formatted": "Present",
            "is_currently_valid": True
        }

        >>> format_temporal_range_for_api("[\\"2026-01-15 10:00:00+00\\",\\"2026-02-15 10:00:00+00\\")]")
        {
            "lower": "2026-01-15T10:00:00+00:00",
            "upper": "2026-02-15T10:00:00+00:00",
            "lower_formatted": "January 15, 2026",
            "upper_formatted": "February 15, 2026",
            "is_currently_valid": False
        }
    """
    if not range_value:
        return _get_empty_range_dict()

    # Handle pre-formatted ISO string (from ProjectRead.convert_range_to_iso)
    if isinstance(range_value, str):
        # Check if it's already an ISO timestamp (not a range string)
        if range_value.startswith("20") and not range_value.startswith("["):
            try:
                dt = datetime.fromisoformat(range_value.replace("Z", "+00:00"))
                return {
                    "lower": range_value,
                    "upper": None,
                    "lower_formatted": _format_datetime(dt),
                    "upper_formatted": "Present",
                    "is_currently_valid": True,
                }
            except ValueError:
                return _get_empty_range_dict()

        # Handle PostgreSQL range string format: ["2026-01-15 10:00:00+00",)
        return _parse_postgresql_range_string(range_value)

    # Handle PostgreSQL range object (with .lower and .upper attributes)
    if hasattr(range_value, "lower") and range_value.lower:
        lower_dt = datetime.fromisoformat(
            range_value.lower.isoformat()
        ) if isinstance(range_value.lower, datetime) else range_value.lower

        upper_dt = None
        if hasattr(range_value, "upper") and range_value.upper:
            upper_dt = datetime.fromisoformat(
                range_value.upper.isoformat()
            ) if isinstance(range_value.upper, datetime) else range_value.upper

        return {
            "lower": lower_dt.isoformat(),
            "upper": upper_dt.isoformat() if upper_dt else None,
            "lower_formatted": _format_datetime(lower_dt),
            "upper_formatted": _format_datetime(upper_dt) if upper_dt else "Present",
            "is_currently_valid": upper_dt is None,
        }

    return _get_empty_range_dict()


def _parse_postgresql_range_string(range_str: str) -> dict[str, str | None]:
    """Parse PostgreSQL TSTZRANGE string format.

    Expected format: ["lower",upper") or ["lower",upper] etc.
    JSON serialization adds escaped quotes: [\\"lower\\",upper)

    Args:
        range_str: PostgreSQL range string (e.g., '[\\"2026-01-15 10:00:00+00\\",)')

    Returns:
        Dictionary with temporal range information
    """
    if not range_str or "," not in range_str:
        return _get_empty_range_dict()

    try:
        # Find comma and extract bounds
        comma_index = range_str.index(",")

        # Extract lower bound (after opening bracket, before comma)
        lower_str = range_str[1:comma_index].strip()

        # Remove escaped quotes if present (JSON serialization artifact)
        lower_str = lower_str.replace('\\"', "")

        # Extract upper bound (after comma, before closing bracket)
        # PostgreSQL ranges can end with ) for exclusive or ] for inclusive
        # Also handle case where range might be followed by ] (JSON array)
        upper_str = range_str[comma_index + 1:].strip()

        # Find the actual closing bracket (either ) or ])
        if upper_str.endswith(")]"):
            upper_str = upper_str[:-2]  # Remove )]
        elif upper_str.endswith(")") or upper_str.endswith("]"):
            upper_str = upper_str[:-1]  # Remove ) or ]

        upper_str = upper_str.strip()
        upper_str = upper_str.replace('\\"', "")

        # Check for unbounded (empty string or infinity)
        is_unbounded = not upper_str or upper_str in ("-infinity", "infinity")

        # Parse lower bound
        lower_dt = datetime.fromisoformat(lower_str) if lower_str else None

        # Parse upper bound if bounded
        upper_dt = None
        if not is_unbounded and upper_str:
            upper_dt = datetime.fromisoformat(upper_str)

        return {
            "lower": lower_dt.isoformat() if lower_dt else None,
            "upper": upper_dt.isoformat() if upper_dt else None,
            "lower_formatted": _format_datetime(lower_dt) if lower_dt else "Unknown",
            "upper_formatted": "Present" if is_unbounded else (
                _format_datetime(upper_dt) if upper_dt else "Unknown"
            ),
            "is_currently_valid": is_unbounded,
        }
    except (ValueError, IndexError):
        return _get_empty_range_dict()


def _format_datetime(dt: datetime | None) -> str:
    """Format datetime for display.

    Uses a consistent format across all API responses.
    Frontend can display this directly without further processing.

    Args:
        dt: datetime object or None

    Returns:
        Formatted date string (e.g., "January 15, 2026") or "Unknown"
    """
    if not dt:
        return "Unknown"

    # Format: "January 15, 2026"
    return dt.strftime("%B %d, %Y")


def _get_empty_range_dict() -> dict[str, str | None]:
    """Return dictionary for empty/invalid temporal ranges."""
    return {
        "lower": None,
        "upper": None,
        "lower_formatted": "Unknown",
        "upper_formatted": "Unknown",
        "is_currently_valid": False,
    }
