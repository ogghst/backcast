"""Custom field validation service."""

from typing import Any

from app.models.schemas.custom_field import CustomFieldDefinition, CustomFieldType


class CustomFieldService:
    """Validates custom field values against field definitions."""

    def validate_field_values(
        self,
        definitions: list[CustomFieldDefinition],
        values: dict[str, Any],
    ) -> list[str]:
        """Validate custom field values against definitions.

        Args:
            definitions: Field definitions from config
            values: Per-CO custom field values

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        for field_def in definitions:
            value = values.get(field_def.name)

            # Check required fields
            if field_def.required and value is None:
                errors.append(f"Field '{field_def.name}' is required")
                continue

            # Skip validation for missing optional fields
            if value is None:
                continue

            # Type-specific validation
            if field_def.type == CustomFieldType.NUMBER:
                if not isinstance(value, (int, float)):
                    errors.append(
                        f"Field '{field_def.name}' must be a number, got {type(value).__name__}"
                    )

            elif field_def.type == CustomFieldType.DATE:
                if not isinstance(value, str):
                    errors.append(f"Field '{field_def.name}' must be a date string")
                else:
                    from datetime import datetime as dt

                    try:
                        dt.fromisoformat(value)
                    except ValueError:
                        errors.append(
                            f"Field '{field_def.name}' must be a valid ISO date"
                        )

            elif field_def.type == CustomFieldType.SELECT:
                if value not in field_def.options:
                    errors.append(
                        f"Field '{field_def.name}' value '{value}' is not in options: {field_def.options}"
                    )

            # TEXT type: any string is valid, no extra validation

        return errors
