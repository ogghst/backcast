"""Shared validators for Pydantic schemas.

This module provides reusable type annotations for common validation patterns
across Pydantic models. Using Pydantic v2's Annotated types with AfterValidator
eliminates the need for duplicate @field_validator decorators.

These validators can be used as type annotations in Pydantic models:
    name: NotEmptyString  # Validates optional string is not empty/whitespace
    progress: ProgressPercentage  # Validates float is 0-100
"""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator


def validate_not_empty(v: str | None) -> str | None:
    """Validate that string is not empty or whitespace.

    This validator prevents empty strings from being accepted when a field
    is marked as optional but should not be empty/whitespace if provided.

    This is particularly important for AI tool calls that may pass empty
    strings instead of None, which would violate database NOT NULL constraints.

    Args:
        v: String value or None

    Returns:
        The validated string or None

    Raises:
        ValueError: If string is empty or contains only whitespace

    Examples:
        >>> validate_not_empty(None)
        None
        >>> validate_not_empty("valid")
        'valid'
        >>> validate_not_empty("   ")
        ValueError: Value cannot be empty or whitespace only
    """
    if v is not None and v.strip() == "":
        raise ValueError("Value cannot be empty or whitespace only")
    return v


def validate_progress_percentage(v: float) -> float:
    """Validate progress percentage is between 0 and 100.

    Ensures that progress percentage values fall within the valid range.
    This validator works with float values.

    Args:
        v: Progress percentage value

    Returns:
        The validated progress percentage

    Raises:
        ValueError: If percentage is not between 0 and 100

    Examples:
        >>> validate_progress_percentage(50.0)
        50.0
        >>> validate_progress_percentage(0.0)
        0.0
        >>> validate_progress_percentage(100.0)
        100.0
        >>> validate_progress_percentage(150.0)
        ValueError: Progress percentage must be between 0 and 100
    """
    if not 0 <= v <= 100:
        raise ValueError("Progress percentage must be between 0 and 100")
    return v


def validate_progress_percentage_decimal(v: Decimal) -> Decimal:
    """Validate progress percentage is between 0 and 100 (Decimal version).

    Ensures that progress percentage values fall within the valid range.
    This validator works with Decimal values for precise financial calculations.

    Args:
        v: Progress percentage value (Decimal)

    Returns:
        The validated progress percentage

    Raises:
        ValueError: If percentage is not between 0 and 100

    Examples:
        >>> validate_progress_percentage_decimal(Decimal("50.00"))
        Decimal('50.00')
        >>> validate_progress_percentage_decimal(Decimal("150.00"))
        ValueError: Progress percentage must be between 0 and 100
    """
    if v < Decimal("0.00") or v > Decimal("100.00"):
        raise ValueError("Progress percentage must be between 0 and 100")
    return v


# Type aliases for use in Pydantic models
NotEmptyString = Annotated[str | None, AfterValidator(validate_not_empty)]
"""Type alias for optional string fields that must not be empty/whitespace if provided."""

ProgressPercentage = Annotated[float, AfterValidator(validate_progress_percentage)]
"""Type alias for progress percentage fields (float, 0-100)."""

ProgressPercentageDecimal = Annotated[
    Decimal, AfterValidator(validate_progress_percentage_decimal)
]
"""Type alias for progress percentage fields (Decimal, 0-100).

Note: This requires importing Decimal from decimal in your model.
"""
