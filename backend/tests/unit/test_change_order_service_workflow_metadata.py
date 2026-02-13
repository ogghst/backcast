"""Tests for ChangeOrderService workflow metadata in public schema."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.branch import Branch
from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order import ChangeOrderPublic
from app.services.change_order_service import ChangeOrderService


@pytest.mark.asyncio
async def test_to_public_includes_available_transitions(db_session: AsyncSession):
    """Verify that _to_public() adds available_transitions field from workflow service.

    Acceptance Criteria:
    - Backend ChangeOrderPublic schema includes available_transitions field
    - Field is populated by calling workflow_service.get_available_transitions()

    This test ensures the frontend can receive valid workflow transitions
    to dynamically filter the status dropdown.
    """
    # Arrange
    co_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    co = ChangeOrder(
        id=co_id,
        change_order_id=uuid4(),
        code="CO-001",
        project_id=project_id,
        title="Test Change Order",
        status="Draft",
        branch="main",
        created_by=user_id,
        parent_id=None,
        deleted_at=None,
    )

    # Create service with mocked workflow service
    service = ChangeOrderService(db_session)

    # Mock workflow service async methods to return specific values
    service.workflow.get_available_transitions = AsyncMock(
        return_value=["Submitted for Approval"]
    )
    service.workflow.can_edit_on_status = AsyncMock(return_value=True)

    # Mock branch service for branch_locked check (no branch for this test)
    service.branch_service.get_by_name_and_project = AsyncMock(
        side_effect=Exception("Branch not found")
    )

    # Act
    result = await service._to_public(co)

    # Assert
    assert isinstance(result, ChangeOrderPublic), (
        "Result should be ChangeOrderPublic schema"
    )
    assert result.available_transitions == ["Submitted for Approval"], (
        "available_transitions should match workflow service response"
    )
    assert result.can_edit_status is True, "Draft status should be editable"
    assert result.branch_locked is False, "No branch means not locked"
    (
        service.workflow.get_available_transitions.assert_called_once_with("Draft"),
        ("Workflow service should be called with current status"),
    )
    service.workflow.can_edit_on_status.assert_called_once_with("Draft")


@pytest.mark.asyncio
async def test_to_public_submitted_status_cannot_edit(db_session: AsyncSession):
    """Verify that _to_public() sets can_edit_status False for non-editable statuses.

    Acceptance Criteria:
    - can_edit_status field reflects workflow rules
    - Submitted for Approval status should not allow editing
    """
    # Arrange
    co_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    co = ChangeOrder(
        id=co_id,
        change_order_id=uuid4(),
        code="CO-002",
        project_id=project_id,
        title="Submitted CO",
        status="Submitted for Approval",
        branch="main",
        created_by=user_id,
        parent_id=None,
        deleted_at=None,
    )

    service = ChangeOrderService(db_session)

    # Mock workflow: Submitted status cannot be edited
    service.workflow.get_available_transitions = AsyncMock(
        return_value=["Under Review"]
    )
    service.workflow.can_edit_on_status = AsyncMock(return_value=False)

    service.branch_service.get_by_name_and_project = AsyncMock(
        side_effect=Exception("Branch not found")
    )

    # Act
    result = await service._to_public(co)

    # Assert
    assert result.can_edit_status is False, "Submitted status should not be editable"
    assert result.available_transitions == ["Under Review"]


@pytest.mark.asyncio
async def test_to_public_branch_locked_true_when_branch_locked(
    db_session: AsyncSession,
):
    """Verify that _to_public() correctly reports locked branch status.

    Acceptance Criteria:
    - branch_locked field reflects actual Branch.locked state
    - Frontend uses this to disable status field
    """
    # Arrange
    co_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    co = ChangeOrder(
        id=co_id,
        change_order_id=uuid4(),
        code="CO-003",
        project_id=project_id,
        title="Locked CO",
        status="Under Review",
        branch="main",
        branch_name="BR-CO-003",
        created_by=user_id,
        parent_id=None,
        deleted_at=None,
    )

    service = ChangeOrderService(db_session)

    service.workflow.get_available_transitions = AsyncMock(
        return_value=["Approved", "Rejected"]
    )
    service.workflow.can_edit_on_status = AsyncMock(return_value=False)

    # Mock branch service to return a locked branch
    locked_branch = Branch(
        name="BR-CO-003",
        project_id=project_id,
        type="change_order",
        locked=True,
        created_by=user_id,
        deleted_at=None,
    )
    service.branch_service.get_by_name_and_project = AsyncMock(
        return_value=locked_branch
    )

    # Act
    result = await service._to_public(co)

    # Assert
    assert result.branch_locked is True, "Branch should be reported as locked"
    service.branch_service.get_by_name_and_project.assert_called_once_with(
        name="BR-CO-003",
        project_id=project_id,
    )


@pytest.mark.asyncio
async def test_to_public_branch_locked_false_when_branch_unlocked(
    db_session: AsyncSession,
):
    """Verify that _to_public() correctly reports unlocked branch status.

    Acceptance Criteria:
    - branch_locked field reflects actual Branch.locked state
    - Frontend uses this to enable status field
    """
    # Arrange
    co_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    co = ChangeOrder(
        id=co_id,
        change_order_id=uuid4(),
        code="CO-004",
        project_id=project_id,
        title="Unlocked CO",
        status="Draft",
        branch="main",
        branch_name="BR-CO-004",
        created_by=user_id,
        parent_id=None,
        deleted_at=None,
    )

    service = ChangeOrderService(db_session)

    service.workflow.get_available_transitions = AsyncMock(
        return_value=["Submitted for Approval"]
    )
    service.workflow.can_edit_on_status = AsyncMock(return_value=True)

    # Mock branch service to return an unlocked branch
    unlocked_branch = Branch(
        name="BR-CO-004",
        project_id=project_id,
        type="change_order",
        locked=False,
        created_by=user_id,
        deleted_at=None,
    )
    service.branch_service.get_by_name_and_project = AsyncMock(
        return_value=unlocked_branch
    )

    # Act
    result = await service._to_public(co)

    # Assert
    assert result.branch_locked is False, "Branch should be reported as unlocked"


@pytest.mark.asyncio
async def test_to_public_rejected_status_allows_resubmission(db_session: AsyncSession):
    """Verify that Rejected status allows resubmission to Submitted for Approval.

    Acceptance Criteria:
    - Rejected Change Orders can be resubmitted
    - available_transitions includes "Submitted for Approval"
    """
    # Arrange
    co_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    co = ChangeOrder(
        id=co_id,
        change_order_id=uuid4(),
        code="CO-005",
        project_id=project_id,
        title="Rejected CO",
        status="Rejected",
        branch="main",
        branch_name="BR-CO-005",
        created_by=user_id,
        parent_id=None,
        deleted_at=None,
    )

    service = ChangeOrderService(db_session)

    # Rejected status allows resubmission
    service.workflow.get_available_transitions = AsyncMock(
        return_value=["Submitted for Approval"]
    )
    service.workflow.can_edit_on_status = AsyncMock(
        return_value=True
    )  # Rejected is editable

    service.branch_service.get_by_name_and_project = AsyncMock(
        side_effect=Exception("Branch not found")
    )

    # Act
    result = await service._to_public(co)

    # Assert
    assert result.available_transitions == ["Submitted for Approval"]
    assert result.can_edit_status is True, (
        "Rejected status should allow editing for resubmission"
    )


@pytest.mark.asyncio
async def test_to_public_approved_status_allows_implemented_only(
    db_session: AsyncSession,
):
    """Verify that Approved status only allows transition to Implemented.

    Acceptance Criteria:
    - Approved Change Orders can only move to Implemented
    - No other transitions available
    """
    # Arrange
    co_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    co = ChangeOrder(
        id=co_id,
        change_order_id=uuid4(),
        code="CO-006",
        project_id=project_id,
        title="Approved CO",
        status="Approved",
        branch="main",
        branch_name="BR-CO-006",
        created_by=user_id,
        parent_id=None,
        deleted_at=None,
    )

    service = ChangeOrderService(db_session)

    service.workflow.get_available_transitions = AsyncMock(return_value=["Implemented"])
    service.workflow.can_edit_on_status = AsyncMock(return_value=False)

    service.branch_service.get_by_name_and_project = AsyncMock(
        side_effect=Exception("Branch not found")
    )

    # Act
    result = await service._to_public(co)

    # Assert
    assert result.available_transitions == ["Implemented"]
    assert result.can_edit_status is False, "Approved status should not allow editing"
