"""Tests for temporal context tool accessibility in subagents.

Verifies that all subagents have access to the get_temporal_context tool,
which provides critical temporal context information (as_of date, branch_name, etc.).
"""

from app.ai.subagents import get_all_subagents


class TestSubagentTemporalContextAccess:
    """Verify get_temporal_context is available to all subagents."""

    def test_all_subagents_have_get_temporal_context(self):
        """Every subagent should have get_temporal_context in allowed_tools.

        For general-purpose agents with allowed_tools=None (meaning all tools),
        this is implicitly satisfied.
        """
        subagents = get_all_subagents()

        for subagent in subagents:
            subagent_name = subagent.get("name", "")
            allowed_tools = subagent.get("allowed_tools")

            # None means "all tools" — skip explicit check
            if allowed_tools is None:
                continue

            assert "get_temporal_context" in allowed_tools, (
                f"Subagent '{subagent_name}' is missing get_temporal_context in allowed_tools. "
                f"This tool provides critical temporal context (current date, branch, etc.) "
                f"and should be available to all agents."
            )

    def test_get_temporal_context_is_first_tool(self):
        """get_temporal_context should be the first tool in allowed_tools for consistency.

        For general-purpose agents with allowed_tools=None (meaning all tools),
        this is implicitly satisfied.
        """
        subagents = get_all_subagents()

        for subagent in subagents:
            subagent_name = subagent.get("name", "")
            allowed_tools = subagent.get("allowed_tools")

            # None means "all tools" — skip explicit check
            if allowed_tools is None:
                continue

            assert allowed_tools[0] == "get_temporal_context", (
                f"Subagent '{subagent_name}' should have get_temporal_context as the first tool. "
                f"Current first tool: {allowed_tools[0]}"
            )

    def test_all_subagent_names_present(self):
        """Verify all expected subagents are configured."""
        subagents = get_all_subagents()
        subagent_names = {sa.get("name") for sa in subagents}

        expected_names = {
            "project_manager",
            "evm_analyst",
            "change_order_manager",
            "user_admin",
            "visualization_specialist",
            "forecast_manager",
            "general_purpose",
        }

        assert subagent_names == expected_names, (
            f"Subagent names mismatch. Expected: {expected_names}, Got: {subagent_names}"
        )
