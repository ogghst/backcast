"""Integration tests for ChangeOrderService with branch creation and workflow."""

from uuid import uuid4

import pytest

from app.models.domain.branch import Branch
from app.models.domain.project import Project
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.branch_service import BranchService
from app.services.change_order_service import ChangeOrderService


@pytest.mark.asyncio
async def test_create_change_order_creates_branch_in_transaction(db_session):
    """Test that creating a Change Order also creates a branch in same transaction."""
    # Arrange: Create a project
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-001",
        name="Test Project",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.commit()

    # Create ChangeOrderCreate schema
    co_in = ChangeOrderCreate(
        code="CO-2026-001",
        project_id=project.project_id,
        title="Test Change Order",
        description="Test Description",
        status="Draft",
    )

    # Act: Create Change Order
    co_service = ChangeOrderService(db_session)
    change_order = await co_service.create_change_order(
        change_order_in=co_in,
        actor_id=user_id,
    )

    await db_session.commit()  # Commit to ensure transaction completes

    # Assert: Change Order created
    assert change_order.change_order_id is not None
    assert change_order.code == "CO-2026-001"
    assert change_order.branch_name == "BR-CO-2026-001"

    # Assert: Branch created in same transaction
    from sqlalchemy import select

    stmt = select(Branch).where(
        Branch.name == "BR-CO-2026-001",
        Branch.project_id == project.project_id,
    )
    result = await db_session.execute(stmt)
    branch = result.scalar_one()

    assert branch is not None
    assert branch.name == "BR-CO-2026-001"
    assert branch.project_id == project.project_id
    assert branch.type == "change_order"
    assert branch.locked is False  # Draft status = unlocked


@pytest.mark.asyncio
async def test_status_change_draft_to_submitted_locks_branch(db_session):
    """Test that changing status from Draft to Submitted for Approval locks the branch."""
    # Arrange: Create a project and Change Order
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-002",
        name="Test Project 2",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.commit()

    co_in = ChangeOrderCreate(
        code="CO-2026-002",
        project_id=project.project_id,
        title="Test Change Order 2",
        description="Test Description",
        status="Draft",
    )

    co_service = ChangeOrderService(db_session)
    change_order = await co_service.create_change_order(
        change_order_in=co_in,
        actor_id=user_id,
    )
    await db_session.commit()

    # Act: Update status to "Submitted for Approval"
    co_update = ChangeOrderUpdate(status="Submitted for Approval")
    updated_co = await co_service.update_change_order(
        change_order_id=change_order.change_order_id,
        change_order_in=co_update,
        actor_id=user_id,
    )
    await db_session.commit()

    # Assert: Status updated
    assert updated_co.status == "Submitted for Approval"

    # Assert: Branch is locked
    branch_service = BranchService(db_session)
    branch = await branch_service.get_by_name_and_project(
        name="BR-CO-2026-002",
        project_id=project.project_id,
    )
    assert branch.locked is True


@pytest.mark.asyncio
async def test_status_change_under_review_to_rejected_unlocks_branch(db_session):
    """Test that changing status from Under Review to Rejected unlocks the branch."""
    # Arrange: Create a project and Change Order in locked state
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-003",
        name="Test Project 3",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.commit()

    # Create CO with "Submitted for Approval" status (which locks the branch)
    co_in = ChangeOrderCreate(
        code="CO-2026-003",
        project_id=project.project_id,
        title="Test Change Order 3",
        description="Test Description",
        status="Submitted for Approval",  # This will lock the branch
    )

    co_service = ChangeOrderService(db_session)
    change_order = await co_service.create_change_order(
        change_order_in=co_in,
        actor_id=user_id,
    )

    # Update to Under Review
    co_update = ChangeOrderUpdate(status="Under Review")
    change_order = await co_service.update_change_order(
        change_order_id=change_order.change_order_id,
        change_order_in=co_update,
        actor_id=user_id,
    )
    await db_session.commit()

    # Verify branch is locked
    branch_service = BranchService(db_session)
    branch = await branch_service.get_by_name_and_project(
        name="BR-CO-2026-003",
        project_id=project.project_id,
    )
    assert branch.locked is True

    # Act: Update status to Rejected
    co_update = ChangeOrderUpdate(status="Rejected")
    updated_co = await co_service.update_change_order(
        change_order_id=change_order.change_order_id,
        change_order_in=co_update,
        actor_id=user_id,
    )
    await db_session.commit()

    # Assert: Status updated
    assert updated_co.status == "Rejected"

    # Assert: Branch is unlocked (re-fetch to get current version)
    branch = await branch_service.get_by_name_and_project(
        name="BR-CO-2026-003",
        project_id=project.project_id,
    )
    assert branch.locked is False


@pytest.mark.asyncio
async def test_invalid_status_transition_raises_error(db_session):
    """Test that invalid status transitions are rejected."""
    # Arrange: Create a project and Change Order in Draft status
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-004",
        name="Test Project 4",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.commit()

    co_in = ChangeOrderCreate(
        code="CO-2026-004",
        project_id=project.project_id,
        title="Test Change Order 4",
        description="Test Description",
        status="Draft",
    )

    co_service = ChangeOrderService(db_session)
    change_order = await co_service.create_change_order(
        change_order_in=co_in,
        actor_id=user_id,
    )
    await db_session.commit()

    # Act & Assert: Try to skip directly to Approved (invalid)
    co_update = ChangeOrderUpdate(status="Approved")

    with pytest.raises(ValueError) as exc_info:
        await co_service.update_change_order(
            change_order_id=change_order.change_order_id,
            change_order_in=co_update,
            actor_id=user_id,
        )

    assert "Invalid status transition" in str(exc_info.value)
