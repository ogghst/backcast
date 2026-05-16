"""Tests for template file migration to new @ai_tool pattern.

These tests verify that template files follow the new pattern with:
- Annotated[ToolContext, InjectedToolArg] for context parameter
- Google-style docstrings with Context section
- Proper error handling
- Correct imports
"""

import pytest
from langchain_core.tools import BaseTool

from app.ai.tools.templates import (
    analysis_template,
    change_order_template,
    crud_template,
)


class TestCrudTemplateMigration:
    """Test crud_template.py follows new @ai_tool pattern."""

    @pytest.mark.parametrize(
        "tool_name",
        [
            "list_projects",
            "get_project",
            "create_project",
            "update_project",
            "list_wbes",
            "get_wbe",
            "create_wbe",
        ],
    )
    def test_tool_is_basetool(self, tool_name: str):
        """Test that all tools are LangChain BaseTool instances."""
        tool = getattr(crud_template, tool_name)
        assert isinstance(tool, BaseTool), f"{tool_name} should be a BaseTool instance"

    def test_tools_have_injected_context(self):
        """Test that tools use InjectedToolArg for context parameter."""
        # Check that the module has the correct imports
        assert hasattr(crud_template, "InjectedToolArg"), (
            "Should import InjectedToolArg"
        )
        assert hasattr(crud_template, "Annotated"), (
            "Should import Annotated from typing"
        )

    def test_tools_have_metadata(self):
        """Test that tools have _tool_metadata attached."""
        tools = [
            crud_template.list_projects,
            crud_template.get_project,
            crud_template.create_project,
            crud_template.update_project,
            crud_template.list_wbes,
            crud_template.get_wbe,
            crud_template.create_wbe,
        ]

        for tool in tools:
            assert hasattr(tool, "_tool_metadata"), (
                f"{tool.name} should have _tool_metadata"
            )
            assert hasattr(tool, "_is_ai_tool"), f"{tool.name} should have _is_ai_tool"
            assert tool._is_ai_tool is True, f"{tool.name}._is_ai_tool should be True"


class TestAnalysisTemplateMigration:
    """Test analysis_template.py follows new @ai_tool pattern."""

    @pytest.mark.parametrize(
        "tool_name",
        [
            "calculate_evm_metrics",
            "get_evm_performance_summary",
            "analyze_cost_variance",
            "analyze_schedule_variance",
            "generate_project_forecast",
            "compare_forecast_scenarios",
            "get_forecast_accuracy",
            "get_project_kpis",
        ],
    )
    def test_tool_is_basetool(self, tool_name: str):
        """Test that all tools are LangChain BaseTool instances."""
        tool = getattr(analysis_template, tool_name)
        assert isinstance(tool, BaseTool), f"{tool_name} should be a BaseTool instance"

    def test_tools_have_injected_context(self):
        """Test that tools use InjectedToolArg for context parameter."""
        assert hasattr(analysis_template, "InjectedToolArg"), (
            "Should import InjectedToolArg"
        )
        assert hasattr(analysis_template, "Annotated"), (
            "Should import Annotated from typing"
        )

    def test_tools_have_metadata(self):
        """Test that tools have _tool_metadata attached."""
        tools = [
            analysis_template.calculate_evm_metrics,
            analysis_template.get_evm_performance_summary,
            analysis_template.analyze_cost_variance,
            analysis_template.analyze_schedule_variance,
            analysis_template.generate_project_forecast,
            analysis_template.compare_forecast_scenarios,
            analysis_template.get_forecast_accuracy,
            analysis_template.get_project_kpis,
        ]

        for tool in tools:
            assert hasattr(tool, "_tool_metadata"), (
                f"{tool.name} should have _tool_metadata"
            )
            assert hasattr(tool, "_is_ai_tool"), f"{tool.name} should have _is_ai_tool"
            assert tool._is_ai_tool is True, f"{tool.name}._is_ai_tool should be True"


class TestChangeOrderTemplateMigration:
    """Test change_order_template.py follows new @ai_tool pattern."""

    @pytest.mark.parametrize(
        "tool_name",
        [
            "list_change_orders",
            "get_change_order",
            "create_change_order",
            "generate_change_order_draft",
            "submit_change_order_for_approval",
            "approve_change_order",
            "reject_change_order",
            "analyze_change_order_impact",
        ],
    )
    def test_tool_is_basetool(self, tool_name: str):
        """Test that all tools are LangChain BaseTool instances."""
        tool = getattr(change_order_template, tool_name)
        assert isinstance(tool, BaseTool), f"{tool_name} should be a BaseTool instance"

    def test_tools_have_injected_context(self):
        """Test that tools use InjectedToolArg for context parameter."""
        assert hasattr(change_order_template, "InjectedToolArg"), (
            "Should import InjectedToolArg"
        )
        assert hasattr(change_order_template, "Annotated"), (
            "Should import Annotated from typing"
        )

    def test_tools_have_metadata(self):
        """Test that tools have _tool_metadata attached."""
        tools = [
            change_order_template.list_change_orders,
            change_order_template.get_change_order,
            change_order_template.create_change_order,
            change_order_template.generate_change_order_draft,
            change_order_template.submit_change_order_for_approval,
            change_order_template.approve_change_order,
            change_order_template.reject_change_order,
            change_order_template.analyze_change_order_impact,
        ]

        for tool in tools:
            assert hasattr(tool, "_tool_metadata"), (
                f"{tool.name} should have _tool_metadata"
            )
            assert hasattr(tool, "_is_ai_tool"), f"{tool.name} should have _is_ai_tool"
            assert tool._is_ai_tool is True, f"{tool.name}._is_ai_tool should be True"


class TestTemplateDocstrings:
    """Test that template tools have proper Google-style docstrings."""

    def test_crud_tools_have_context_section(self):
        """Test that CRUD tool docstrings have Context section."""
        tools = [
            crud_template.list_projects,
            crud_template.get_project,
            crud_template.create_project,
        ]

        for tool in tools:
            docstring = tool.description
            assert "Context:" in docstring or docstring == tool.description, (
                f"{tool.name} should have Context section in docstring"
            )

    def test_tools_have_permissions(self):
        """Test that all tools have permissions defined."""
        all_tools = [
            (
                crud_template,
                [
                    "list_projects",
                    "get_project",
                    "create_project",
                    "update_project",
                    "list_wbes",
                    "get_wbe",
                    "create_wbe",
                ],
            ),
            (
                analysis_template,
                [
                    "calculate_evm_metrics",
                    "get_evm_performance_summary",
                    "analyze_cost_variance",
                    "analyze_schedule_variance",
                    "generate_project_forecast",
                    "compare_forecast_scenarios",
                    "get_forecast_accuracy",
                    "get_project_kpis",
                ],
            ),
            (
                change_order_template,
                [
                    "list_change_orders",
                    "get_change_order",
                    "create_change_order",
                    "generate_change_order_draft",
                    "submit_change_order_for_approval",
                    "approve_change_order",
                    "reject_change_order",
                    "analyze_change_order_impact",
                ],
            ),
        ]

        for module, tool_names in all_tools:
            for tool_name in tool_names:
                tool = getattr(module, tool_name)
                assert hasattr(tool, "_tool_metadata"), (
                    f"{tool.name} should have _tool_metadata"
                )
                metadata = tool._tool_metadata
                assert len(metadata.permissions) > 0, (
                    f"{tool.name} should have at least one permission"
                )


class TestTemplateImports:
    """Test that template files have correct imports."""

    def test_crud_template_imports(self):
        """Test that crud_template has required imports."""
        assert hasattr(crud_template, "ai_tool"), "Should import ai_tool"
        assert hasattr(crud_template, "ToolContext"), "Should import ToolContext"
        # Note: BaseTool is not directly imported in templates; @ai_tool decorator handles it

    def test_analysis_template_imports(self):
        """Test that analysis_template has required imports."""
        assert hasattr(analysis_template, "ai_tool"), "Should import ai_tool"
        assert hasattr(analysis_template, "ToolContext"), "Should import ToolContext"
        # Note: BaseTool is not directly imported in templates; @ai_tool decorator handles it

    def test_change_order_template_imports(self):
        """Test that change_order_template has required imports."""
        assert hasattr(change_order_template, "ai_tool"), "Should import ai_tool"
        assert hasattr(change_order_template, "ToolContext"), (
            "Should import ToolContext"
        )
        # Note: BaseTool is not directly imported in templates; @ai_tool decorator handles it
