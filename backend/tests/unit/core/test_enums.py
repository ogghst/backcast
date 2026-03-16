"""Unit tests for core enumeration types."""

from app.core.enums import ChangeOrderStatus, ProjectStatus


class TestProjectStatus:
    """Test ProjectStatus enum functionality."""

    def test_status_values(self) -> None:
        """Test that ProjectStatus has correct string values."""
        assert ProjectStatus.DRAFT.value == "Draft"
        assert ProjectStatus.ACTIVE.value == "Active"
        assert ProjectStatus.ON_HOLD.value == "On Hold"
        assert ProjectStatus.COMPLETED.value == "Completed"
        assert ProjectStatus.CANCELLED.value == "Cancelled"

    def test_color_mapping(self) -> None:
        """Test that ProjectStatus has correct color mappings."""
        assert ProjectStatus.DRAFT.color == "default"
        assert ProjectStatus.ACTIVE.color == "success"
        assert ProjectStatus.ON_HOLD.color == "warning"
        assert ProjectStatus.COMPLETED.color == "default"
        assert ProjectStatus.CANCELLED.color == "error"

    def test_enum_is_string_enum(self) -> None:
        """Test that ProjectStatus is a string enum."""
        assert isinstance(ProjectStatus.DRAFT, str)
        assert ProjectStatus.ACTIVE.value == "Active"
        # String enums compare equal to their values
        assert ProjectStatus.ACTIVE == "Active"

    def test_enum_comparison(self) -> None:
        """Test that ProjectStatus enum values can be compared."""
        assert ProjectStatus.DRAFT == ProjectStatus.DRAFT
        assert ProjectStatus.DRAFT != ProjectStatus.ACTIVE
        assert ProjectStatus.DRAFT == "Draft"

    def test_all_statuses_have_colors(self) -> None:
        """Test that all ProjectStatus values have color mappings."""
        for status in ProjectStatus:
            assert hasattr(status, "color")
            assert isinstance(status.color, str)
            assert len(status.color) > 0


class TestChangeOrderStatus:
    """Test ChangeOrderStatus enum functionality."""

    def test_status_values(self) -> None:
        """Test that ChangeOrderStatus has correct string values."""
        assert ChangeOrderStatus.DRAFT.value == "Draft"
        assert ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value == "Submitted for Approval"
        assert ChangeOrderStatus.UNDER_REVIEW.value == "Under Review"
        assert ChangeOrderStatus.APPROVED.value == "Approved"
        assert ChangeOrderStatus.IMPLEMENTED.value == "Implemented"
        assert ChangeOrderStatus.REJECTED.value == "Rejected"

    def test_color_mapping(self) -> None:
        """Test that ChangeOrderStatus has correct color mappings."""
        assert ChangeOrderStatus.DRAFT.color == "default"
        assert ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.color == "processing"
        assert ChangeOrderStatus.UNDER_REVIEW.color == "blue"
        assert ChangeOrderStatus.APPROVED.color == "success"
        assert ChangeOrderStatus.IMPLEMENTED.color == "green"
        assert ChangeOrderStatus.REJECTED.color == "error"

    def test_enum_is_string_enum(self) -> None:
        """Test that ChangeOrderStatus is a string enum."""
        assert isinstance(ChangeOrderStatus.DRAFT, str)
        assert ChangeOrderStatus.APPROVED.value == "Approved"
        # String enums compare equal to their values
        assert ChangeOrderStatus.APPROVED == "Approved"

    def test_enum_comparison(self) -> None:
        """Test that ChangeOrderStatus enum values can be compared."""
        assert ChangeOrderStatus.DRAFT == ChangeOrderStatus.DRAFT
        assert ChangeOrderStatus.DRAFT != ChangeOrderStatus.APPROVED
        assert ChangeOrderStatus.DRAFT == "Draft"

    def test_all_statuses_have_colors(self) -> None:
        """Test that all ChangeOrderStatus values have color mappings."""
        for status in ChangeOrderStatus:
            assert hasattr(status, "color")
            assert isinstance(status.color, str)
            assert len(status.color) > 0

    def test_status_with_spaces(self) -> None:
        """Test that statuses with spaces work correctly."""
        assert ChangeOrderStatus.SUBMITTED_FOR_APPROVAL == "Submitted for Approval"
        assert ChangeOrderStatus.UNDER_REVIEW == "Under Review"
