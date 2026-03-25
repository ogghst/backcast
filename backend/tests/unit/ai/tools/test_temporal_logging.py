"""Tests for temporal logging helper functions.

Tests verify that temporal context is correctly logged and metadata is added
to tool results for observability and debugging.
"""

from datetime import datetime

import pytest

from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import ToolContext


@pytest.mark.asyncio
class TestLogTemporalContext:
    """Test log_temporal_context helper function."""

    async def test_log_temporal_context_with_all_fields(self):
        """Verify temporal context logging with all fields populated.

        Given: ToolContext with all temporal fields set
        When: log_temporal_context() is called
        Then: Function executes without error (logging is side effect)
        """
        context = ToolContext(
            session=None,  # Not used for logging
            user_id="user-123",
            user_role="admin",
            as_of=datetime(2025, 6, 15, 12, 0, 0),
            branch_name="feature-1",
            branch_mode="isolated",
        )

        # Should not raise any errors
        log_temporal_context("list_projects", context)

    async def test_log_temporal_context_with_none_values(self):
        """Verify temporal context logging with None values uses defaults.

        Given: ToolContext with None temporal values
        When: log_temporal_context() is called
        Then: Function executes without error
        """
        context = ToolContext(
            session=None,  # Not used for logging
            user_id="user-123",
            user_role="admin",
            as_of=None,
            branch_name=None,
            branch_mode=None,
        )

        # Should not raise any errors
        log_temporal_context("get_project", context)

    async def test_log_temporal_context_with_branch_only(self):
        """Verify temporal context logging with only branch set.

        Given: ToolContext with only branch_name set
        When: log_temporal_context() is called
        Then: Function executes without error
        """
        context = ToolContext(
            session=None,
            user_id="user-123",
            user_role="viewer",
            as_of=None,
            branch_name="change-order-1",
            branch_mode=None,
        )

        # Should not raise any errors
        log_temporal_context("create_change_order", context)


@pytest.mark.asyncio
class TestAddTemporalMetadata:
    """Test add_temporal_metadata helper function."""

    async def test_add_temporal_metadata_to_result(self):
        """Verify temporal metadata is added to tool result.

        Given: Tool result dict and ToolContext with temporal values
        When: add_temporal_metadata() is called
        Then: Result dict contains _temporal_context field with correct values
        """
        result = {"projects": [{"id": "1", "name": "Project A"}], "total": 1}

        context = ToolContext(
            session=None,
            user_id="user-123",
            user_role="admin",
            as_of=datetime(2025, 12, 31, 23, 59, 59),
            branch_name="feature-budget",
            branch_mode="merged",
        )

        enhanced_result = add_temporal_metadata(result, context)

        # Verify original fields preserved
        assert enhanced_result["projects"] == result["projects"]
        assert enhanced_result["total"] == result["total"]

        # Verify temporal metadata added
        assert "_temporal_context" in enhanced_result
        temporal = enhanced_result["_temporal_context"]
        assert temporal["as_of"] == "2025-12-31T23:59:59"
        assert temporal["branch_name"] == "feature-budget"
        assert temporal["branch_mode"] == "merged"

    async def test_add_temporal_metadata_with_none_values(self):
        """Verify temporal metadata uses defaults when context values are None.

        Given: Tool result dict and ToolContext with None temporal values
        When: add_temporal_metadata() is called
        Then: _temporal_context field shows default values
        """
        result = {"success": True}

        context = ToolContext(
            session=None,
            user_id="user-123",
            user_role="viewer",
            as_of=None,
            branch_name=None,
            branch_mode=None,
        )

        enhanced_result = add_temporal_metadata(result, context)

        # Verify temporal metadata with defaults
        assert "_temporal_context" in enhanced_result
        temporal = enhanced_result["_temporal_context"]
        assert temporal["as_of"] is None
        assert temporal["branch_name"] == "main"
        assert temporal["branch_mode"] == "merged"

    async def test_add_temporal_metadata_preserves_existing_fields(self):
        """Verify existing result fields are not modified.

        Given: Tool result with multiple fields including nested structures
        When: add_temporal_metadata() is called
        Then: All existing fields preserved unchanged, only _temporal_context added
        """
        result = {
            "projects": [
                {"id": "1", "name": "Project A", "budget": 100000},
                {"id": "2", "name": "Project B", "budget": 200000},
            ],
            "total": 2,
            "skip": 0,
            "limit": 20,
            "_custom_field": "should_be_preserved",
        }

        context = ToolContext(
            session=None,
            user_id="user-123",
            user_role="admin",
            as_of=datetime(2025, 1, 1),
            branch_name="main",
            branch_mode="isolated",
        )

        enhanced_result = add_temporal_metadata(result, context)

        # Verify all original fields preserved
        assert len(enhanced_result["projects"]) == 2
        assert enhanced_result["total"] == 2
        assert enhanced_result["skip"] == 0
        assert enhanced_result["limit"] == 20
        assert enhanced_result["_custom_field"] == "should_be_preserved"

        # Verify temporal metadata added
        assert "_temporal_context" in enhanced_result
        assert enhanced_result["_temporal_context"]["as_of"] == "2025-01-01T00:00:00"
