"""Tests for Change Order Pydantic schemas.

Test module for change order request/response schemas.
"""

from app.models.schemas.change_order import ChangeOrderUpdate


class TestChangeOrderUpdateSchema:
    """Test suite for ChangeOrderUpdate schema."""

    def test_change_order_update_accepts_comment(self):
        """Test ChangeOrderUpdate accepts optional comment field."""
        data = {"status": "Submitted", "comment": "Ready for review"}

        update = ChangeOrderUpdate(**data)

        assert update.status == "Submitted"
        assert update.comment == "Ready for review"

    def test_change_order_update_comment_is_optional(self):
        """Test ChangeOrderUpdate works without comment field."""
        data = {"status": "Submitted"}

        update = ChangeOrderUpdate(**data)

        assert update.status == "Submitted"
        assert update.comment is None

    def test_change_order_update_comment_can_be_long_text(self):
        """Test ChangeOrderUpdate accepts long comment strings."""
        long_comment = (
            "This is a detailed explanation of the changes made. " * 10
        )  # ~700 chars

        data = {"status": "Approved", "comment": long_comment}

        update = ChangeOrderUpdate(**data)

        assert update.comment == long_comment
        assert len(update.comment) > 500

    def test_change_order_update_with_empty_comment(self):
        """Test ChangeOrderUpdate accepts empty string comment."""
        data = {"status": "Rejected", "comment": ""}

        update = ChangeOrderUpdate(**data)

        assert update.comment == ""

    def test_change_order_update_without_any_fields(self):
        """Test ChangeOrderUpdate accepts empty dict (all optional)."""
        update = ChangeOrderUpdate()

        assert update.status is None
        assert update.comment is None
        assert update.title is None

    def test_change_order_update_with_other_fields_and_comment(self):
        """Test ChangeOrderUpdate combines comment with other fields."""
        data = {
            "title": "Updated Title",
            "status": "Submitted",
            "comment": "Updated title for clarity",
        }

        update = ChangeOrderUpdate(**data)

        assert update.title == "Updated Title"
        assert update.status == "Submitted"
        assert update.comment == "Updated title for clarity"
