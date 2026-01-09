class FilterError(Exception):
    """Base exception for filter parsing errors."""
    pass


class FilterFieldNotAllowedError(FilterError):
    """Raised when a filter field is not allowed."""
    def __init__(self, field: str, allowed_fields: list[str] | None = None):
        msg = f"Filter field '{field}' is not allowed."
        if allowed_fields:
            msg += f" Allowed fields: {', '.join(allowed_fields)}"
        super().__init__(msg)


class FilterValueTypeError(FilterError):
    """Raised when a filter value cannot be cast to the expected type."""
    def __init__(self, field: str, value: str, expected_type: str):
        super().__init__(
            f"Invalid filter value for field '{field}': expected {expected_type}, got '{value}'"
        )
