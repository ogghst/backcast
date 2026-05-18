"""Unit tests for CustomFieldService validation logic."""

from app.models.schemas.custom_field import CustomFieldDefinition, CustomFieldType
from app.services.custom_field_service import CustomFieldService

service = CustomFieldService()

# ---------------------------------------------------------------------------
# TEXT field
# ---------------------------------------------------------------------------


def test_validate_passes_valid_text_field() -> None:
    """Text field with string value produces no errors."""
    defs = [
        CustomFieldDefinition(name="notes", type=CustomFieldType.TEXT),
    ]
    errors = service.validate_field_values(defs, {"notes": "some text"})
    assert errors == []


# ---------------------------------------------------------------------------
# NUMBER field
# ---------------------------------------------------------------------------


def test_validate_passes_valid_number_field() -> None:
    """Number field accepts int and float values."""
    defs = [
        CustomFieldDefinition(name="quantity", type=CustomFieldType.NUMBER),
    ]
    assert service.validate_field_values(defs, {"quantity": 42}) == []
    assert service.validate_field_values(defs, {"quantity": 3.14}) == []


# ---------------------------------------------------------------------------
# DATE field
# ---------------------------------------------------------------------------


def test_validate_passes_valid_date_field() -> None:
    """Date field with ISO date string produces no errors."""
    defs = [
        CustomFieldDefinition(name="deadline", type=CustomFieldType.DATE),
    ]
    errors = service.validate_field_values(defs, {"deadline": "2025-06-15"})
    assert errors == []


# ---------------------------------------------------------------------------
# SELECT field
# ---------------------------------------------------------------------------


def test_validate_passes_valid_select_field() -> None:
    """Select field with value from options list produces no errors."""
    defs = [
        CustomFieldDefinition(
            name="priority",
            type=CustomFieldType.SELECT,
            options=["low", "medium", "high"],
        ),
    ]
    errors = service.validate_field_values(defs, {"priority": "medium"})
    assert errors == []


# ---------------------------------------------------------------------------
# Required field missing
# ---------------------------------------------------------------------------


def test_validate_rejects_missing_required_field() -> None:
    """Required field with value=None returns an error."""
    defs = [
        CustomFieldDefinition(name="title", type=CustomFieldType.TEXT, required=True),
    ]
    errors = service.validate_field_values(defs, {"title": None})
    assert len(errors) == 1
    assert "title" in errors[0]
    assert "required" in errors[0]


# ---------------------------------------------------------------------------
# Optional field missing
# ---------------------------------------------------------------------------


def test_validate_allows_optional_field_missing() -> None:
    """Optional field not present in values dict produces no errors."""
    defs = [
        CustomFieldDefinition(name="nickname", type=CustomFieldType.TEXT),
    ]
    errors = service.validate_field_values(defs, {})
    assert errors == []


# ---------------------------------------------------------------------------
# Wrong type: number field with string
# ---------------------------------------------------------------------------


def test_validate_rejects_wrong_type_number() -> None:
    """Number field given a string value returns a type error."""
    defs = [
        CustomFieldDefinition(name="amount", type=CustomFieldType.NUMBER),
    ]
    errors = service.validate_field_values(defs, {"amount": "one hundred"})
    assert len(errors) == 1
    assert "amount" in errors[0]
    assert "number" in errors[0].lower()


# ---------------------------------------------------------------------------
# Invalid select option
# ---------------------------------------------------------------------------


def test_validate_rejects_invalid_select_option() -> None:
    """Select field with value not in options returns an error."""
    defs = [
        CustomFieldDefinition(
            name="color",
            type=CustomFieldType.SELECT,
            options=["red", "green", "blue"],
        ),
    ]
    errors = service.validate_field_values(defs, {"color": "yellow"})
    assert len(errors) == 1
    assert "color" in errors[0]


# ---------------------------------------------------------------------------
# Invalid date format
# ---------------------------------------------------------------------------


def test_validate_rejects_invalid_date_format() -> None:
    """Date field with non-ISO string returns an error."""
    defs = [
        CustomFieldDefinition(name="start_date", type=CustomFieldType.DATE),
    ]
    errors = service.validate_field_values(defs, {"start_date": "not-a-date"})
    assert len(errors) == 1
    assert "start_date" in errors[0]
    assert "ISO" in errors[0]


# ---------------------------------------------------------------------------
# Multiple errors at once
# ---------------------------------------------------------------------------


def test_validate_multiple_errors() -> None:
    """Multiple invalid fields produce multiple error messages."""
    defs = [
        CustomFieldDefinition(name="title", type=CustomFieldType.TEXT, required=True),
        CustomFieldDefinition(name="amount", type=CustomFieldType.NUMBER),
        CustomFieldDefinition(
            name="priority",
            type=CustomFieldType.SELECT,
            options=["low", "high"],
        ),
    ]
    errors = service.validate_field_values(
        defs,
        {"title": None, "amount": "abc", "priority": "medium"},
    )
    assert len(errors) == 3
