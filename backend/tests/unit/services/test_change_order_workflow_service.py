"""Unit tests for ChangeOrderWorkflowService."""

from unittest.mock import AsyncMock

import pytest

from app.core.enums import ChangeOrderStatus
from app.services.change_order_workflow_service import ChangeOrderWorkflowService


@pytest.mark.asyncio
async def test_get_available_transitions_draft():
    """Test getting available transitions from Draft status."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    transitions = await service.get_available_transitions(ChangeOrderStatus.DRAFT.value)

    # Assert
    assert transitions == [ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value]


@pytest.mark.asyncio
async def test_get_available_transitions_under_review():
    """Test getting available transitions from under_review (branching)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    transitions = await service.get_available_transitions(
        ChangeOrderStatus.UNDER_REVIEW.value
    )

    # Assert
    assert set(transitions) == {
        ChangeOrderStatus.APPROVED.value,
        ChangeOrderStatus.REJECTED.value,
    }


@pytest.mark.asyncio
async def test_get_next_status_linear():
    """Test getting next status when workflow is linear."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    next_status = await service.get_next_status(ChangeOrderStatus.DRAFT.value)

    # Assert
    assert next_status == ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value


@pytest.mark.asyncio
async def test_get_next_status_branching():
    """Test getting next status when workflow has multiple options."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    next_status = await service.get_next_status(ChangeOrderStatus.UNDER_REVIEW.value)

    # Assert
    assert next_status is None  # Multiple options available


@pytest.mark.asyncio
async def test_should_lock_on_transition_draft_to_submitted():
    """Test that Draft → submitted_for_approval locks branch."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    should_lock = await service.should_lock_on_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
    )

    # Assert
    assert should_lock is True


@pytest.mark.asyncio
async def test_should_lock_on_transition_submitted_to_under_review():
    """Test that submitted_for_approval → under_review does NOT lock branch."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    should_lock = await service.should_lock_on_transition(
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
        ChangeOrderStatus.UNDER_REVIEW.value,
    )

    # Assert
    assert should_lock is False


@pytest.mark.asyncio
async def test_should_unlock_on_transition_under_review_to_rejected():
    """Test that under_review → Rejected unlocks branch."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    should_unlock = await service.should_unlock_on_transition(
        ChangeOrderStatus.UNDER_REVIEW.value,
        ChangeOrderStatus.REJECTED.value,
    )

    # Assert
    assert should_unlock is True


@pytest.mark.asyncio
async def test_can_edit_on_status_draft():
    """Test that Draft status allows editing."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    can_edit = await service.can_edit_on_status(ChangeOrderStatus.DRAFT.value)

    # Assert
    assert can_edit is True


@pytest.mark.asyncio
async def test_can_edit_on_status_submitted():
    """Test that submitted_for_approval does NOT allow editing."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    can_edit = await service.can_edit_on_status(
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value
    )

    # Assert
    assert can_edit is False


@pytest.mark.asyncio
async def test_can_edit_on_status_rejected():
    """Test that Rejected status allows editing (for resubmission)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    can_edit = await service.can_edit_on_status(ChangeOrderStatus.REJECTED.value)

    # Assert
    assert can_edit is True


@pytest.mark.asyncio
async def test_is_valid_transition_draft_to_submitted():
    """Test that Draft → submitted_for_approval is valid."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    is_valid = await service.is_valid_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
    )

    # Assert
    assert is_valid is True


@pytest.mark.asyncio
async def test_is_valid_transition_draft_to_approved():
    """Test that Draft → Approved is INVALID (skips steps)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    is_valid = await service.is_valid_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.APPROVED.value,
    )

    # Assert
    assert is_valid is False


@pytest.mark.asyncio
async def test_is_valid_transition_rejected_to_submitted():
    """Test that Rejected → submitted_for_approval is valid (resubmission)."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    is_valid = await service.is_valid_transition(
        ChangeOrderStatus.REJECTED.value,
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
    )

    # Assert
    assert is_valid is True


@pytest.mark.asyncio
async def test_get_available_transitions_implemented():
    """Test that Implemented is a terminal state with no transitions."""
    # Arrange
    service = ChangeOrderWorkflowService()

    # Act
    transitions = await service.get_available_transitions(
        ChangeOrderStatus.IMPLEMENTED.value
    )

    # Assert
    assert transitions == []


# ============================================================================
# Approval Workflow Tests
# ============================================================================
# NOTE: Approval workflow methods (submit_for_approval, approve_change_order,
# reject_change_order) are tested via integration tests rather than unit tests
# due to runtime imports to avoid circular dependencies with ChangeOrderService.
# See tests/integration/test_change_order_approval_workflow.py for comprehensive tests.


# ============================================================================
# Phase B: Config-driven Workflow Transitions Tests
# ============================================================================

CUSTOM_CONFIG = {
    "transitions": {
        ChangeOrderStatus.DRAFT.value: ["custom_step"],
        "custom_step": [
            ChangeOrderStatus.APPROVED.value,
            ChangeOrderStatus.REJECTED.value,
        ],
        ChangeOrderStatus.APPROVED.value: [ChangeOrderStatus.IMPLEMENTED.value],
        ChangeOrderStatus.REJECTED.value: [ChangeOrderStatus.DRAFT.value],
        ChangeOrderStatus.IMPLEMENTED.value: [],
    },
    "lock_transitions": [[ChangeOrderStatus.DRAFT.value, "custom_step"]],
    "unlock_transitions": [["custom_step", ChangeOrderStatus.REJECTED.value]],
    "editable_statuses": [ChangeOrderStatus.DRAFT.value],
}


@pytest.mark.asyncio
async def test_no_config_service_uses_hardcoded_defaults():
    """Service with no config_service uses class-level hardcoded defaults."""
    service = ChangeOrderWorkflowService()

    transitions = await service.get_available_transitions(ChangeOrderStatus.DRAFT.value)
    assert transitions == [ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value]

    assert await service.is_valid_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
    )
    assert not await service.is_valid_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.APPROVED.value,
    )


@pytest.mark.asyncio
async def test_config_overrides_transitions():
    """Service with config_service uses config transitions."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.return_value = CUSTOM_CONFIG

    service = ChangeOrderWorkflowService(config_service=config_service)

    transitions = await service.get_available_transitions(ChangeOrderStatus.DRAFT.value)
    assert transitions == ["custom_step"]
    assert await service.is_valid_transition(
        ChangeOrderStatus.DRAFT.value, "custom_step"
    )
    assert not await service.is_valid_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
    )


@pytest.mark.asyncio
async def test_config_null_transitions_falls_back():
    """Config returns None for transitions -> falls back to defaults."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.return_value = None

    service = ChangeOrderWorkflowService(config_service=config_service)

    transitions = await service.get_available_transitions(ChangeOrderStatus.DRAFT.value)
    assert transitions == [ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value]


@pytest.mark.asyncio
async def test_config_exception_falls_back():
    """Config service raises ConfigurationError -> falls back to defaults."""
    from app.services.change_order_config_service import ConfigurationError

    config_service = AsyncMock()
    config_service.get_workflow_transitions.side_effect = ConfigurationError(
        "No config"
    )

    service = ChangeOrderWorkflowService(config_service=config_service)

    transitions = await service.get_available_transitions(ChangeOrderStatus.DRAFT.value)
    assert transitions == [ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value]


@pytest.mark.asyncio
async def test_config_unexpected_error_propagates():
    """Non-ConfigurationError exceptions propagate instead of silent fallback."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.side_effect = RuntimeError("DB error")

    service = ChangeOrderWorkflowService(config_service=config_service)

    with pytest.raises(RuntimeError, match="DB error"):
        await service.get_available_transitions(ChangeOrderStatus.DRAFT.value)


@pytest.mark.asyncio
async def test_custom_lock_transitions():
    """Lock transitions from config override hardcoded."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.return_value = CUSTOM_CONFIG

    service = ChangeOrderWorkflowService(config_service=config_service)

    assert await service.should_lock_on_transition(
        ChangeOrderStatus.DRAFT.value, "custom_step"
    )
    assert not await service.should_lock_on_transition(
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
    )


@pytest.mark.asyncio
async def test_custom_unlock_transitions():
    """Unlock transitions from config override hardcoded."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.return_value = CUSTOM_CONFIG

    service = ChangeOrderWorkflowService(config_service=config_service)

    assert await service.should_unlock_on_transition(
        "custom_step", ChangeOrderStatus.REJECTED.value
    )
    assert not await service.should_unlock_on_transition(
        ChangeOrderStatus.UNDER_REVIEW.value,
        ChangeOrderStatus.REJECTED.value,
    )


@pytest.mark.asyncio
async def test_custom_editable_statuses():
    """Editable statuses from config override hardcoded."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.return_value = CUSTOM_CONFIG

    service = ChangeOrderWorkflowService(config_service=config_service)

    assert await service.can_edit_on_status(ChangeOrderStatus.DRAFT.value)
    assert not await service.can_edit_on_status(ChangeOrderStatus.REJECTED.value)


@pytest.mark.asyncio
async def test_transitions_cached_within_instance():
    """Transitions are loaded once and cached per instance."""
    config_service = AsyncMock()
    config_service.get_workflow_transitions.return_value = CUSTOM_CONFIG

    service = ChangeOrderWorkflowService(config_service=config_service)

    await service.get_available_transitions("draft")
    await service.get_available_transitions("draft")

    config_service.get_workflow_transitions.assert_called_once()
