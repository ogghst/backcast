"""Exceptions for hierarchy operations.

Defines exceptions raised during organizational unit hierarchy validation,
such as circular reference detection.
"""


class CircularReferenceError(ValueError):
    """Raised when a circular or self-referencing parent_unit_id is detected."""
