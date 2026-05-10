"""Integration tests for Change Order resubmission temporal correctness.

Tests the bug fix for bitemporal data corruption on Change Order resubmission
(Rejected -> Submitted for Approval). Verifies that:

1. The previous version's valid_time and transaction_time are properly closed.
2. get_as_of() returns the new Submitted version, not the stale Rejected one.
3. Empty valid_time ranges are excluded from current version queries.
4. The full lifecycle Draft -> Submitted -> Rejected -> Submitted works.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.change_order_service import ChangeOrderService
from app.services.project import ProjectService


@pytest.fixture
def _setup_project():
    """Provide setup constants for tests."""
    return {
        "T0": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    }


@pytest.mark.asyncio
async def test_resubmission_closes_previous_version_temporal_ranges(
    db_session: AsyncSession,
) -> None:
    """Verify that resubmission properly closes the Rejected version's temporal ranges.

    Scenario:
    - T0: Create project
    - T1: Create CO in Draft status
    - T2: Submit for Approval (Draft -> Submitted)
    - T3: Reject (Submitted -> Rejected)
    - T4: Resubmit (Rejected -> Submitted for Approval)

    After resubmission, the Rejected version must have closed valid_time
    and transaction_time, and get_as_of() must return the Submitted version.
    """
    project_service = ProjectService(db_session)
    co_service = ChangeOrderService(db_session)
    actor_id = uuid4()

    T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    T1 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    T2 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    T3 = datetime(2026, 1, 20, 12, 0, 0, tzinfo=UTC)
    T4 = datetime(2026, 1, 25, 12, 0, 0, tzinfo=UTC)

    # Create project
    project_id = uuid4()
    await project_service.create(
        root_id=project_id,
        actor_id=actor_id,
        control_date=T0,
        code="PROJ-RESUB",
        name="Resubmission Test Project",
        budget=Decimal("500000.00"),
    )

    # T1: Create CO in Draft
    co = await co_service.create_change_order(
        change_order_in=ChangeOrderCreate(
            code="CO-RESUB-001",
            title="Resubmission Test CO",
            description="Testing resubmission temporal correctness",
            project_id=project_id,
            status="Draft",
        ),
        actor_id=actor_id,
        control_date=T1,
    )
    co_id = co.change_order_id

    # T2: Submit for Approval
    co_submitted = await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(
            status="Submitted for Approval",
            comment="Initial submission",
        ),
        actor_id=actor_id,
        control_date=T2,
        branch="main",
    )
    assert co_submitted.status == "Submitted for Approval"

    # T3: Reject
    co_rejected = await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(
            status="Rejected",
            comment="Needs revision",
        ),
        actor_id=actor_id,
        control_date=T3,
        branch="main",
    )
    assert co_rejected.status == "Rejected"

    # Verify we see the Rejected version before resubmission
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None
    assert current.status == "Rejected"

    # T4: Resubmit (Rejected -> Submitted for Approval)
    co_resubmitted = await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(
            status="Submitted for Approval",
            comment="Resubmission after revision",
        ),
        actor_id=actor_id,
        control_date=T4,
        branch="main",
    )
    assert co_resubmitted.status == "Submitted for Approval"

    # CORE ASSERTION: get_as_of() must return the Submitted version, not Rejected
    current_after = await co_service.get_as_of(co_id, branch="main")
    assert current_after is not None, "get_as_of() should find the current version"
    assert current_after.status == "Submitted for Approval", (
        f"Expected 'Submitted for Approval' but got '{current_after.status}'. "
        "The Rejected version's temporal ranges were not properly closed."
    )

    # Verify only ONE version has open-ended valid_time on main branch
    open_ended_stmt = select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
        func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
        cast(Any, ChangeOrder).deleted_at.is_(None),
        func.not_(func.isempty(ChangeOrder.valid_time)),
    )
    result = await db_session.execute(open_ended_stmt)
    open_versions = list(result.scalars().all())
    assert len(open_versions) == 1, (
        f"Expected exactly 1 open-ended version on main, found {len(open_versions)}: "
        f"{[v.status for v in open_versions]}"
    )
    assert open_versions[0].status == "Submitted for Approval"


@pytest.mark.asyncio
async def test_resubmission_with_same_control_date_closes_previous(
    db_session: AsyncSession,
) -> None:
    """Verify resubmission works even when control_date equals the Rejected version's lower bound.

    This tests the specific bug case where control_date == current_lower,
    which previously left the old version open because the closing condition
    was strictly greater-than (>) instead of greater-than-or-equal (>=).
    """
    project_service = ProjectService(db_session)
    co_service = ChangeOrderService(db_session)
    actor_id = uuid4()

    T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    T1 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    # Use the SAME control_date for rejection and resubmission
    T_reject_resubmit = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Create project
    project_id = uuid4()
    await project_service.create(
        root_id=project_id,
        actor_id=actor_id,
        control_date=T0,
        code="PROJ-SAME",
        name="Same Control Date Test",
        budget=Decimal("500000.00"),
    )

    # Create CO in Draft
    co = await co_service.create_change_order(
        change_order_in=ChangeOrderCreate(
            code="CO-SAME-001",
            title="Same Control Date Resubmission",
            project_id=project_id,
            status="Draft",
        ),
        actor_id=actor_id,
        control_date=T1,
    )
    co_id = co.change_order_id

    # Submit at T1
    await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
        actor_id=actor_id,
        control_date=T1 + timedelta(seconds=1),
        branch="main",
    )

    # Reject at T_reject_resubmit
    await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Rejected"),
        actor_id=actor_id,
        control_date=T_reject_resubmit,
        branch="main",
    )

    # Resubmit at the SAME T_reject_resubmit
    co_resubmitted = await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
        actor_id=actor_id,
        control_date=T_reject_resubmit,
        branch="main",
    )
    assert co_resubmitted.status == "Submitted for Approval"

    # Verify get_as_of returns Submitted, not Rejected
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None
    assert current.status == "Submitted for Approval", (
        f"Expected 'Submitted for Approval' but got '{current.status}'. "
        "The Rejected version was not closed when control_date == current_lower."
    )


@pytest.mark.asyncio
async def test_empty_valid_time_ranges_excluded_from_current_query(
    db_session: AsyncSession,
) -> None:
    """Verify that BranchableService.get_as_of() excludes empty valid_time ranges.

    The isempty() check prevents versions with empty ranges (where lower == upper)
    from being returned as current versions. This was missing from
    BranchableService.get_as_of() but present in TemporalService.get_as_of().
    """
    project_service = ProjectService(db_session)
    co_service = ChangeOrderService(db_session)
    actor_id = uuid4()

    T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    T1 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    T2 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Create project
    project_id = uuid4()
    await project_service.create(
        root_id=project_id,
        actor_id=actor_id,
        control_date=T0,
        code="PROJ-EMPTY",
        name="Empty Range Test",
        budget=Decimal("500000.00"),
    )

    # Create CO
    co = await co_service.create_change_order(
        change_order_in=ChangeOrderCreate(
            code="CO-EMPTY-001",
            title="Empty Range Test CO",
            project_id=project_id,
            status="Draft",
        ),
        actor_id=actor_id,
        control_date=T1,
    )
    co_id = co.change_order_id

    # Manually create a version with an empty valid_time range to simulate corruption
    # This mimics what could happen if closing logic produced [t, t) ranges
    from uuid import uuid4 as new_uuid

    empty_range_id = new_uuid()
    empty_version = co.clone(
        branch="main",
        status="Corrupted",
        parent_id=co.id,
    )
    empty_version.id = empty_range_id
    db_session.add(empty_version)
    await db_session.flush()

    # Set the version's valid_time to an empty range [T2, T2)
    from sqlalchemy import text as sql_text

    await db_session.execute(
        sql_text(
            """
            UPDATE change_orders
            SET valid_time = tstzrange(:lower, :upper, '[)')
            WHERE id = :version_id
            """
        ),
        {"lower": T2, "upper": T2, "version_id": empty_range_id},
    )
    await db_session.flush()

    # get_as_of should NOT return the empty-range version
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None
    assert current.status != "Corrupted", (
        "get_as_of() should not return a version with empty valid_time range"
    )
    assert current.status == "Draft"


@pytest.mark.asyncio
async def test_full_lifecycle_draft_submit_reject_resubmit(
    db_session: AsyncSession,
) -> None:
    """Full lifecycle: Draft -> Submitted -> Rejected -> Submitted -> Approved.

    Verifies that every transition properly closes the previous version's
    temporal ranges, and get_as_of() always returns the expected status.
    """
    project_service = ProjectService(db_session)
    co_service = ChangeOrderService(db_session)
    actor_id = uuid4()

    T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    T1 = datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC)
    T2 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    T3 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    T4 = datetime(2026, 1, 20, 12, 0, 0, tzinfo=UTC)
    T5 = datetime(2026, 1, 25, 12, 0, 0, tzinfo=UTC)

    # Create project
    project_id = uuid4()
    await project_service.create(
        root_id=project_id,
        actor_id=actor_id,
        control_date=T0,
        code="PROJ-LIFE",
        name="Full Lifecycle Test",
        budget=Decimal("500000.00"),
    )

    # Step 1: Create CO in Draft
    co = await co_service.create_change_order(
        change_order_in=ChangeOrderCreate(
            code="CO-LIFE-001",
            title="Full Lifecycle CO",
            project_id=project_id,
            status="Draft",
        ),
        actor_id=actor_id,
        control_date=T1,
    )
    co_id = co.change_order_id

    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None and current.status == "Draft"

    # Step 2: Submit for Approval
    await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
        actor_id=actor_id,
        control_date=T2,
        branch="main",
    )
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None and current.status == "Submitted for Approval"

    # Step 3: Reject
    await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Rejected"),
        actor_id=actor_id,
        control_date=T3,
        branch="main",
    )
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None and current.status == "Rejected"

    # Step 4: Resubmit
    await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
        actor_id=actor_id,
        control_date=T4,
        branch="main",
    )
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None and current.status == "Submitted for Approval"

    # Step 5: Approve (skip Under Review for simplicity via update_change_order)
    await co_service.update_change_order(
        change_order_id=co_id,
        change_order_in=ChangeOrderUpdate(status="Approved"),
        actor_id=actor_id,
        control_date=T5,
        branch="main",
    )
    current = await co_service.get_as_of(co_id, branch="main")
    assert current is not None and current.status == "Approved"

    # Verify history has no empty ranges
    history = await co_service.get_history(co_id)
    for version in history:
        if version.valid_time.upper is not None:
            assert version.valid_time.lower < version.valid_time.upper, (
                f"Version {version.id} (status={version.status}) has empty valid_time range: "
                f"[{version.valid_time.lower}, {version.valid_time.upper})"
            )

    # Verify time-travel queries return correct statuses at each point
    assert (
        await co_service.get_as_of(co_id, as_of=T1, branch="main")
    ).status == "Draft"
    assert (
        await co_service.get_as_of(co_id, as_of=T2, branch="main")
    ).status == "Submitted for Approval"
    assert (
        await co_service.get_as_of(co_id, as_of=T3, branch="main")
    ).status == "Rejected"
    assert (
        await co_service.get_as_of(co_id, as_of=T4, branch="main")
    ).status == "Submitted for Approval"
    assert (
        await co_service.get_as_of(co_id, as_of=T5, branch="main")
    ).status == "Approved"
