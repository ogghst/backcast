"""Test Analysis tool template functionality and validation.

NOTE: Tool templates are thin wrappers around service methods. Unit testing
them with extensive mocking tests mock behavior, not actual functionality.
Meaningful testing requires integration tests with real database and services.

These smoke tests verify templates are syntactically correct and discoverable.
For functional testing, see tests/integration/ai/tools/test_analysis_tools_integration.py
"""

import pytest


class TestAnalysisTemplateExisting:
    """Keep existing basic tests for template structure."""

    def test_analysis_template_can_be_imported(self) -> None:
        """Test that the Analysis template can be imported without errors."""
        try:
            from app.ai.tools.templates import analysis_template

            assert analysis_template is not None
        except Exception as e:
            pytest.fail(f"Failed to import Analysis template: {e}")

    def test_analysis_template_has_required_functions(self) -> None:
        """Test that the Analysis template has all required functions."""
        from app.ai.tools.templates import analysis_template

        assert hasattr(analysis_template, "get_project_analysis")

    def test_analysis_template_functions_have_decorators(self) -> None:
        """Test that Analysis template functions have @ai_tool decorators."""
        from app.ai.tools.templates import analysis_template

        func = getattr(analysis_template, "get_project_analysis")
        assert hasattr(func, "_is_ai_tool"), (
            "get_project_analysis missing @ai_tool decorator"
        )
        assert func._is_ai_tool is True, (
            "get_project_analysis decorator not properly applied"
        )
