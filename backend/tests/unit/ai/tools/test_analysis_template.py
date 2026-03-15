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
        """Test that the Analysis template has all required example functions."""
        from app.ai.tools.templates import analysis_template

        # Check that all Analysis functions exist
        assert hasattr(analysis_template, "calculate_evm_metrics")
        assert hasattr(analysis_template, "get_evm_performance_summary")
        assert hasattr(analysis_template, "analyze_cost_variance")
        assert hasattr(analysis_template, "analyze_schedule_variance")
        assert hasattr(analysis_template, "generate_project_forecast")
        assert hasattr(analysis_template, "compare_forecast_scenarios")
        assert hasattr(analysis_template, "get_forecast_accuracy")
        assert hasattr(analysis_template, "get_project_kpis")

    def test_analysis_template_functions_have_decorators(self) -> None:
        """Test that Analysis template functions have @ai_tool decorators."""
        from app.ai.tools.templates import analysis_template

        # Check that functions have the _is_ai_tool attribute set by decorator
        functions = [
            "calculate_evm_metrics",
            "get_evm_performance_summary",
            "analyze_cost_variance",
            "analyze_schedule_variance",
            "generate_project_forecast",
            "compare_forecast_scenarios",
            "get_forecast_accuracy",
            "get_project_kpis",
        ]

        for func_name in functions:
            func = getattr(analysis_template, func_name)
            # All should have _is_ai_tool attribute from decorator
            assert hasattr(func, "_is_ai_tool"), f"{func_name} missing @ai_tool decorator"
            assert func._is_ai_tool is True, f"{func_name} decorator not properly applied"
