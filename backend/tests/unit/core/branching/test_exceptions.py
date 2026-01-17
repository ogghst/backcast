"""Tests for branching exceptions.

Test module for MergeConflictError and related exceptions.
"""

import pytest

from app.core.branching.exceptions import MergeConflictError


class TestMergeConflictError:
    """Test suite for MergeConflictError exception."""

    def test_merge_conflict_error_with_conflicts(self):
        """Test MergeConflictError can be raised with conflict details."""
        conflicts = [
            {
                "entity_type": "Project",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "field": "name",
                "source_branch": "co-123",
                "target_branch": "main",
                "source_value": "Updated Name",
                "target_value": "Original Name",
            }
        ]

        with pytest.raises(MergeConflictError) as exc_info:
            raise MergeConflictError(conflicts=conflicts)

        assert exc_info.value.conflicts == conflicts
        assert "1 conflict" in str(exc_info.value)

    def test_merge_conflict_error_with_multiple_conflicts(self):
        """Test MergeConflictError handles multiple conflicts."""
        conflicts = [
            {
                "entity_type": "Project",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "field": "name",
                "source_branch": "co-123",
                "target_branch": "main",
                "source_value": "Updated Name",
                "target_value": "Original Name",
            },
            {
                "entity_type": "Project",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "field": "code",
                "source_branch": "co-123",
                "target_branch": "main",
                "source_value": "PROJ-UPDATED",
                "target_value": "PROJ-001",
            },
        ]

        with pytest.raises(MergeConflictError) as exc_info:
            raise MergeConflictError(conflicts=conflicts)

        assert len(exc_info.value.conflicts) == 2
        assert "2 conflicts" in str(exc_info.value)

    def test_merge_conflict_error_empty_list(self):
        """Test MergeConflictError with empty conflict list."""
        with pytest.raises(MergeConflictError) as exc_info:
            raise MergeConflictError(conflicts=[])

        assert exc_info.value.conflicts == []
        assert "No conflicts" in str(exc_info.value)

    def test_merge_conflict_error_message_format(self):
        """Test error message format contains branch information."""
        conflicts = [
            {
                "entity_type": "Project",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "field": "status",
                "source_branch": "feature-branch",
                "target_branch": "main",
                "source_value": "active",
                "target_value": "draft",
            }
        ]

        with pytest.raises(MergeConflictError) as exc_info:
            raise MergeConflictError(conflicts=conflicts)

        error_message = str(exc_info.value)
        assert "feature-branch" in error_message
        assert "main" in error_message
