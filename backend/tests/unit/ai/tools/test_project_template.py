"""Test project tool template functionality and validation.

NOTE: Tool templates are thin wrappers around service methods. Unit testing
them with extensive mocking tests mock behavior, not actual functionality.
Meaningful testing requires integration tests with real database and services.

These smoke tests verify templates are syntactically correct and discoverable.
For functional testing, see tests/integration/ai/tools/test_crud_tools_integration.py
"""

import pytest
from pydantic import ValidationError


class TestProjectUpdateValidation:
    """Test ProjectUpdate schema validation to prevent null/empty names."""

    def test_project_update_allows_none_for_optional_fields(self) -> None:
        """Test that ProjectUpdate allows None for optional fields (skip update)."""
        from app.models.schemas.project import ProjectUpdate

        # None means "don't update this field"
        update = ProjectUpdate(name=None, description=None)
        assert update.name is None
        assert update.description is None

    def test_project_update_rejects_empty_string_name(self) -> None:
        """Test that ProjectUpdate rejects empty string for name."""
        from app.models.schemas.project import ProjectUpdate

        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdate(name="")

        errors = exc_info.value.errors()
        assert any("cannot be empty" in err["msg"] for err in errors)

    def test_project_update_rejects_whitespace_only_name(self) -> None:
        """Test that ProjectUpdate rejects whitespace-only name."""
        from app.models.schemas.project import ProjectUpdate

        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdate(name="   ")

        errors = exc_info.value.errors()
        assert any("cannot be empty" in err["msg"] for err in errors)

    def test_project_update_accepts_valid_name(self) -> None:
        """Test that ProjectUpdate accepts valid name."""
        from app.models.schemas.project import ProjectUpdate

        update = ProjectUpdate(name="Valid Project Name")
        assert update.name == "Valid Project Name"


class TestProjectTemplateExisting:
    """Keep existing basic tests for template structure."""

    def test_project_template_can_be_imported(self) -> None:
        """Test that the project template can be imported without errors."""
        try:
            from app.ai.tools.templates import project_template

            assert project_template is not None
        except Exception as e:
            pytest.fail(f"Failed to import project template: {e}")

    def test_project_template_has_required_functions(self) -> None:
        """Test that the project template has all required functions."""
        from app.ai.tools.templates import project_template

        # Check that all functions exist
        assert hasattr(project_template, "create_project")
        assert hasattr(project_template, "update_project")
        assert hasattr(project_template, "delete_project")
        assert hasattr(project_template, "find_wbes")
        assert hasattr(project_template, "create_wbe")
        assert hasattr(project_template, "update_wbe")
        assert hasattr(project_template, "delete_wbe")

    def test_project_template_functions_have_decorators(self) -> None:
        """Test that project template functions have @ai_tool decorators."""
        from app.ai.tools.templates import project_template

        # Check that functions have the _is_ai_tool attribute set by decorator
        functions = [
            "create_project",
            "update_project",
            "delete_project",
            "find_wbes",
            "create_wbe",
            "update_wbe",
            "delete_wbe",
        ]

        for func_name in functions:
            func = getattr(project_template, func_name)
            # All should have _is_ai_tool attribute from decorator
            assert hasattr(func, "_is_ai_tool"), (
                f"{func_name} missing @ai_tool decorator"
            )
            assert func._is_ai_tool is True, (
                f"{func_name} decorator not properly applied"
            )
