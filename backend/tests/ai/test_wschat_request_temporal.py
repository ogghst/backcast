"""Tests for WSChatRequest temporal parameters."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.models.schemas.ai import WSChatRequest, FileAttachment


class TestWSChatRequestTemporalParams:
    """Test WSChatRequest temporal parameter functionality."""

    def test_wschatrequest_with_temporal_params_accepts_values(self):
        """Test that WSChatRequest accepts and stores temporal parameters."""
        # Arrange
        as_of = datetime(2024, 1, 1, 12, 0, 0)
        branch_name = "BR-001"
        branch_mode = "isolated"

        # Act
        request = WSChatRequest(
            message="Hello",
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
        )

        # Assert
        assert request.as_of == as_of
        assert request.branch_name == branch_name
        assert request.branch_mode == branch_mode

    def test_wschatrequest_defaults_to_main_and_merged(self):
        """Test that WSChatRequest defaults to main/merged when temporal params not provided."""
        # Arrange & Act
        request = WSChatRequest(message="Hello")

        # Assert
        assert request.as_of is None
        assert request.branch_name == "main"
        assert request.branch_mode == "merged"

    def test_wschatrequest_with_partial_temporal_params(self):
        """Test that WSChatRequest accepts partial temporal parameters."""
        # Arrange
        as_of = datetime(2024, 1, 1, 12, 0, 0)

        # Act
        request = WSChatRequest(
            message="Hello",
            as_of=as_of,
        )

        # Assert
        assert request.as_of == as_of
        assert request.branch_name == "main"  # Should use default
        assert request.branch_mode == "merged"  # Should use default
