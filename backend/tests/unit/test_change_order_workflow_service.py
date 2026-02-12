"""Unit tests for ChangeOrderWorkflowService."""

import pytest

from app.services.change_order_workflow_service import ChangeOrderWorkflowService


@pytest.mark.asyncio
async def test_get_available_transitions_draft():
    """Test getting available transitions from Draft status."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    transitions = await service.get_available_transitions("Draft")

    # Assert
    assert transitions == ["Submitted for Approval"]


@pytest.mark.asyncio
async def test_get_available_transitions_under_review():
    """Test getting available transitions from Under Review (branching)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    transitions = await service.get_available_transitions("Under Review")

    # Assert
    assert set(transitions) == {"Approved", "Rejected"}


@pytest.mark.asyncio
async def test_get_next_status_linear():
    """Test getting next status when workflow is linear."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    next_status = await service.get_next_status("Draft")

    # Assert
    assert next_status == "Submitted for Approval"


@pytest.mark.asyncio
async def test_get_next_status_branching():
    """Test getting next status when workflow has multiple options."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    next_status = await service.get_next_status("Under Review")

    # Assert
    assert next_status is None  # Multiple options available


@pytest.mark.asyncio
async def test_should_lock_on_transition_draft_to_submitted():
    """Test that Draft → Submitted for Approval locks branch."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    should_lock = await service.should_lock_on_transition(
        "Draft", "Submitted for Approval"
    )

    # Assert
    assert should_lock is True


@pytest.mark.asyncio
async def test_should_lock_on_transition_submitted_to_under_review():
    """Test that Submitted for Approval → Under Review does NOT lock branch."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    should_lock = await service.should_lock_on_transition(
        "Submitted for Approval", "Under Review"
    )

    # Assert
    assert should_lock is False


@pytest.mark.asyncio
async def test_should_unlock_on_transition_under_review_to_rejected():
    """Test that Under Review → Rejected unlocks branch."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    should_unlock = await service.should_unlock_on_transition(
        "Under Review", "Rejected"
    )

    # Assert
    assert should_unlock is True


@pytest.mark.asyncio
async def test_can_edit_on_status_draft():
    """Test that Draft status allows editing."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    can_edit = await service.can_edit_on_status("Draft")

    # Assert
    assert can_edit is True


@pytest.mark.asyncio
async def test_can_edit_on_status_submitted():
    """Test that Submitted for Approval does NOT allow editing."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    can_edit = await service.can_edit_on_status("Submitted for Approval")

    # Assert
    assert can_edit is False


@pytest.mark.asyncio
async def test_can_edit_on_status_rejected():
    """Test that Rejected status allows editing (for resubmission)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    can_edit = await service.can_edit_on_status("Rejected")

    # Assert
    assert can_edit is True


@pytest.mark.asyncio
async def test_is_valid_transition_draft_to_submitted():
    """Test that Draft → Submitted for Approval is valid."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    is_valid = await service.is_valid_transition("Draft", "Submitted for Approval")

    # Assert
    assert is_valid is True


@pytest.mark.asyncio
async def test_is_valid_transition_draft_to_approved():
    """Test that Draft → Approved is INVALID (skips steps)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    is_valid = await service.is_valid_transition("Draft", "Approved")

    # Assert
    assert is_valid is False


@pytest.mark.asyncio
async def test_is_valid_transition_rejected_to_submitted():
    """Test that Rejected → Submitted for Approval is valid (resubmission)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    is_valid = await service.is_valid_transition("Rejected", "Submitted for Approval")

    # Assert
    assert is_valid is True


@pytest.mark.asyncio
async def test_get_available_transitions_implemented():
    """Test that Implemented is a terminal state with no transitions."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    transitions = await service.get_available_transitions("Implemented")

    # Assert
    assert transitions == []


# ============================================================================
# Approval Workflow Tests
# ============================================================================
# NOTE: Approval workflow methods (submit_for_approval, approve_change_order,
# reject_change_order) are tested via integration tests rather than unit tests
# due to runtime imports to avoid circular dependencies with ChangeOrderService.
# See tests/integration/test_change_order_approval_workflow.py for comprehensive tests.


