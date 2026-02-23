"""Unit tests for ChangeOrderService temporal behavior."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.domain.project import Project
from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService


@pytest.mark.asyncio
async def test_create_change_order_temporal_branch_creation(db_session):
    """Test that create_change_order respects control_date for Branch creation."""
    # Arrange: Setup service and project
    service = ChangeOrderService(db_session)
    actor_id = uuid4()

    project = Project(
        project_id=uuid4(),
        code="PROJ-TEMP",
        name="Temporal Test Project",
        branch="main",
        created_by=actor_id,
    )
    db_session.add(project)
    await db_session.flush()
    # Need to commit to make project visible to service queries if distinct transactions,
    # but here share session.

    # Define a control date in the past
    control_date = datetime.now(UTC) - timedelta(days=5)

    # Act: Create Change Order with control_date
    co_in = ChangeOrderCreate(
        project_id=project.project_id,
        code="CO-TEMP-001",
        title="Temporal CO",
        status="Draft"
    )

    co = await service.create_change_order(
        change_order_in=co_in,
        actor_id=actor_id,
        control_date=control_date
    )

    # Assert: Change Order created correctly
    assert co.change_order_id is not None
    assert co.code == "CO-TEMP-001"
    # Verify CO valid_time lower bound is control_date
    assert co.valid_time.lower == control_date

    # Assert: Branch created correctly
    branch_name = f"BR-{co.code}"
    branch_service = service.branch_service

    # Fetch branch using standard lookup (should find it as it's current)
    branch = await branch_service.get_by_name_and_project(branch_name, project.project_id)

    assert branch is not None
    assert branch.name == branch_name
    assert branch.type == "change_order"

    # VERIFY: Branch valid_time lower bound MUST match control_date
    # This confirms that CreateVersionCommand was used for Branch creation
    assert branch.valid_time.lower == control_date


@pytest.mark.asyncio
async def test_change_order_workflow_locking_temporal(db_session):
    """Test that workflow transitions trigger versioned branch locking."""
    # Arrange
    service = ChangeOrderService(db_session)
    actor_id = uuid4()

    project = Project(
        project_id=uuid4(),
        code="PROJ-LOCK",
        name="Lock Test Project",
        branch="main",
        created_by=actor_id,
    )
    db_session.add(project)
    await db_session.flush()

    # Create CO in Draft (unlocked)
    co_in = ChangeOrderCreate(
        project_id=project.project_id,
        code="CO-LOCK-001",
        title="Lock Test CO",
        status="Draft"
    )
    co = await service.create_change_order(co_in, actor_id)

    branch_name = f"BR-{co.code}"

    # Verify initial state
    branch_v1 = await service.branch_service.get_by_name_and_project(branch_name, project.project_id)
    assert branch_v1.locked is False

    # Act: Move to Submitted (should LOCK)
    # We use update_change_order which triggers lock logic
    from app.models.schemas.change_order import ChangeOrderUpdate

    # Need to mock/bypass workflow validation or ensure transition is valid?
    # ChangeOrderWorkflowService defaults usually allow Draft -> Submitted for Approval
    # Assuming standard workflow is active.

    # We might need to ensure workflow service returns valid for this transition.
    # The default workflow usually requires 'Submitted for Approval' exact string?
    # Let's assume standard status names.

    # Note: If workflow validation fails, we might need to mock it.
    # But integration test usually wants real workflow.
    # Check simple transition.

    update_in = ChangeOrderUpdate(status="Submitted for Approval")

    # Move time forward
    update_time = datetime.now(UTC) + timedelta(minutes=10)

    updated_co = await service.update_change_order(
        change_order_id=co.change_order_id,
        change_order_in=update_in,
        actor_id=actor_id,
        control_date=update_time
    )

    assert updated_co.status == "Submitted for Approval"

    # Verify Branch is now LOCKED
    # And it should be a NEW VERSION
    branch_v2 = await service.branch_service.get_by_name_and_project(branch_name, project.project_id)
    assert branch_v2.locked is True
    assert branch_v2.id != branch_v1.id # Must be new version
    # The valid_time.lower is the actual time when the branch lock operation happens,
    # not the control_date used for time-travel queries
    assert branch_v2.valid_time.lower < update_time
    # Verify v2 was created after v1
    assert branch_v2.valid_time.lower > branch_v1.valid_time.lower
