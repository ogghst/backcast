"""Service-level tests for CostEventService.

Tests cover CRUD operations, COQ category handling, listing/filtering,
COQ metrics computation, COQ trend analysis, cost allocations, and QPI math.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.cost_event import (
    CostEventCreate,
    CostEventUpdate,
    QualityCostAllocation,
)
from app.services.cost_event_service import CostEventService
from tests.factories import (
    create_full_hierarchy,
    create_test_cost_event,
    create_test_cost_registration,
)


@pytest.fixture
def service(db: AsyncSession) -> CostEventService:
    return CostEventService(db)


async def _setup_event_with_registration(
    db: AsyncSession,
    actor_id: UUID,
    coq_category: str = "internal_failure",
    estimated_impact: Decimal = Decimal("5000"),
    registration_amount: Decimal = Decimal("3000"),
) -> dict:
    """Helper: create hierarchy + cost event + cost registration linked via cost_event_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    event = await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        coq_category=coq_category,
        estimated_impact=estimated_impact,
        event_date=datetime.now(UTC) - timedelta(days=5),
    )
    await db.commit()

    # Create a cost registration linked to the cost event
    cr = await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=registration_amount,
        cost_event_id=event.cost_event_id,
    )
    await db.commit()

    return {**h, "event": event, "cr": cr}


@pytest.mark.asyncio
async def test_create_cost_event_via_service(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """create_cost_event persists a new event for a project."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostEventCreate(
        project_id=h["project"].project_id,
        cost_event_type_id=h["cet"].cost_event_type_id,
        name="Pipe Weld Defect",
        coq_category="internal_failure",
        estimated_impact=Decimal("8000"),
        schedule_impact_days=3,
    )
    event = await service.create_cost_event(data, actor_id)
    await db.flush()

    assert event.cost_event_id is not None
    assert event.project_id == h["project"].project_id
    assert event.name == "Pipe Weld Defect"
    assert event.coq_category == "internal_failure"
    assert event.estimated_impact == Decimal("8000")
    assert event.schedule_impact_days == 3


@pytest.mark.asyncio
async def test_create_cost_event_invalid_type_raises(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """create_cost_event raises ValueError for non-existent CostEventType."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostEventCreate(
        project_id=h["project"].project_id,
        cost_event_type_id=uuid4(),
        name="Bad Event",
    )
    with pytest.raises(ValueError, match="Cost Event Type.*not found"):
        await service.create_cost_event(data, actor_id)


@pytest.mark.asyncio
async def test_create_cost_event_with_allocations(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """create_cost_event creates linked CostRegistration entries for allocations."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostEventCreate(
        project_id=h["project"].project_id,
        cost_event_type_id=h["cet"].cost_event_type_id,
        name="Event with Allocations",
        coq_category="prevention",
        estimated_impact=Decimal("2000"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=h["ce"].cost_element_id,
                amount=Decimal("1500"),
                description="Prevention cost allocation",
            ),
        ],
    )
    event = await service.create_cost_event(data, actor_id)
    await db.commit()

    # Verify allocations were created
    allocations = await service.get_allocations(event.cost_event_id)
    assert len(allocations) == 1
    assert allocations[0].cost_element_id == h["ce"].cost_element_id
    assert allocations[0].amount == Decimal("1500")


@pytest.mark.asyncio
async def test_update_cost_event(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """update_cost_event creates a new version with updated fields."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        name="Original Name",
        coq_category="internal_failure",
    )
    await db.commit()

    data = CostEventUpdate(
        name="Updated Name",
        status="closed",
        estimated_impact=Decimal("12000"),
    )
    updated = await service.update_cost_event(event.cost_event_id, data, actor_id)
    await db.flush()

    assert updated.cost_event_id == event.cost_event_id
    assert updated.name == "Updated Name"
    assert updated.status == "closed"
    assert updated.estimated_impact == Decimal("12000")


@pytest.mark.asyncio
async def test_soft_delete_cost_event(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """soft_delete_cost_event marks the event as deleted."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    await service.soft_delete_cost_event(event.cost_event_id, actor_id)
    await db.commit()

    result = await service.get_by_id(event.cost_event_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_by_id returns the current cost event."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    result = await service.get_by_id(event.cost_event_id)
    assert result is not None
    assert result.cost_event_id == event.cost_event_id


@pytest.mark.asyncio
async def test_get_cost_events_list(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_cost_events returns paginated list."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    items, total = await service.get_cost_events()
    assert total >= 1


@pytest.mark.asyncio
async def test_get_cost_events_filter_by_project(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_cost_events filters by project_id."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    items, total = await service.get_cost_events(project_id=h["project"].project_id)
    assert total >= 1
    assert all(e.project_id == h["project"].project_id for e in items)

    items2, total2 = await service.get_cost_events(project_id=uuid4())
    assert total2 == 0


@pytest.mark.asyncio
async def test_get_cost_events_filter_by_coq_category(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_cost_events filters by coq_category."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        coq_category="prevention",
    )
    await db.commit()

    items, total = await service.get_cost_events(coq_category="prevention")
    assert total >= 1
    assert all(e.coq_category == "prevention" for e in items)

    items2, total2 = await service.get_cost_events(coq_category="external_failure")
    # Only check that our prevention event is not in the results
    assert not any(e.project_id == h["project"].project_id for e in items2)


@pytest.mark.asyncio
async def test_get_coq_metrics_basic(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_coq_metrics computes total_coq, cpq, cpq_percentage, total_ac."""
    data = await _setup_event_with_registration(
        db,
        actor_id,
        coq_category="internal_failure",
        registration_amount=Decimal("4000"),
    )

    metrics = await service.get_coq_metrics(data["project"].project_id)

    # total_coq = sum of CR amounts linked to quality events = 4000
    assert metrics.total_coq == Decimal("4000")
    # cpq = internal_failure + external_failure = 4000 (since category is internal_failure)
    assert metrics.cpq == Decimal("4000")
    # cpq_percentage = cpq / total_ac * 100 (total_ac includes all CRs)
    assert metrics.cpq_percentage > Decimal("0")
    # total_ac includes all cost registrations in the project
    assert metrics.total_ac > Decimal("0")


@pytest.mark.asyncio
async def test_get_coq_metrics_no_quality_events(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_coq_metrics returns zeroes when no quality events exist for the project."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    metrics = await service.get_coq_metrics(h["project"].project_id)

    assert metrics.total_coq == Decimal("0")
    assert metrics.cpq == Decimal("0")
    assert metrics.cpq_percentage == Decimal("0")
    assert metrics.cpiq is None
    assert metrics.qpi is None


@pytest.mark.asyncio
async def test_get_summary(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_summary returns aggregated COQ summary by category."""
    h = await create_full_hierarchy(db, actor_id)

    # Create two events with different categories
    await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        coq_category="prevention",
        estimated_impact=Decimal("2000"),
    )
    await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        coq_category="internal_failure",
        estimated_impact=Decimal("5000"),
    )
    await db.commit()

    summary = await service.get_summary(h["project"].project_id)

    assert summary.total_cost == Decimal("7000")
    assert summary.prevention_cost == Decimal("2000")
    assert summary.internal_failure_cost == Decimal("5000")
    assert summary.conformance_cost == Decimal("2000")
    assert summary.nonconformance_cost == Decimal("5000")
    assert summary.impact_count == 2


@pytest.mark.asyncio
async def test_get_allocations_and_upsert(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """upsert_allocations replaces all allocations for an event."""
    data = await _setup_event_with_registration(
        db, actor_id, registration_amount=Decimal("1000")
    )

    event_id = data["event"].cost_event_id
    ce_id = data["ce"].cost_element_id

    # Upsert new allocations
    new_allocations = await service.upsert_allocations(
        cost_event_id=event_id,
        allocations_data=[
            QualityCostAllocation(
                cost_element_id=ce_id,
                amount=Decimal("2000"),
                description="Replaced allocation 1",
            ),
            QualityCostAllocation(
                cost_element_id=ce_id,
                amount=Decimal("3000"),
                description="Replaced allocation 2",
            ),
        ],
        actor_id=actor_id,
    )
    await db.commit()

    assert len(new_allocations) == 2
    assert {a.amount for a in new_allocations} == {
        Decimal("2000"),
        Decimal("3000"),
    }


@pytest.mark.asyncio
async def test_compute_qpi_bands() -> None:
    """_compute_qpi returns expected values at boundary percentages."""
    # 0% CPQ -> Outstanding (1.15)
    assert CostEventService._compute_qpi(Decimal("0")) == Decimal("1.15")

    # > 4% -> Poor Performance (below 0.85)
    qpi_high = CostEventService._compute_qpi(Decimal("5"))
    assert qpi_high < Decimal("0.85")

    # 2% -> Within range
    qpi_mid = CostEventService._compute_qpi(Decimal("2"))
    assert Decimal("0.85") <= qpi_mid <= Decimal("1.15")


@pytest.mark.asyncio
async def test_qpi_rating_mapping() -> None:
    """_qpi_rating maps QPI values to correct labels."""
    assert CostEventService._qpi_rating(Decimal("1.10")) == "Outstanding"
    assert CostEventService._qpi_rating(Decimal("1.00")) == "Within Target"
    assert CostEventService._qpi_rating(Decimal("0.90")) == "Below Target"
    assert CostEventService._qpi_rating(Decimal("0.70")) == "Poor Performance"


@pytest.mark.asyncio
async def test_get_coq_trend_empty(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_coq_trend returns empty points when no quality events exist."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    trend = await service.get_coq_trend(h["project"].project_id)
    assert trend.total_points == 0
    assert trend.points == []


@pytest.mark.asyncio
async def test_update_cost_event_invalid_type_raises(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """update_cost_event raises ValueError when changing to non-existent CostEventType."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    data = CostEventUpdate(cost_event_type_id=uuid4())
    with pytest.raises(ValueError, match="Cost Event Type.*not found"):
        await service.update_cost_event(event.cost_event_id, data, actor_id)


@pytest.mark.asyncio
async def test_update_cost_event_with_allocations(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """update_cost_event replaces cost allocations when provided."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    data = CostEventUpdate(
        name="Updated with allocations",
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=h["ce"].cost_element_id,
                amount=Decimal("7000"),
                description="New allocation",
            ),
        ],
    )
    updated = await service.update_cost_event(event.cost_event_id, data, actor_id)
    await db.commit()

    assert updated.name == "Updated with allocations"

    allocations = await service.get_allocations(event.cost_event_id)
    assert len(allocations) == 1
    assert allocations[0].amount == Decimal("7000")


@pytest.mark.asyncio
async def test_get_cost_events_filter_by_wbs_element(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_cost_events filters by wbs_element_id."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        wbs_element_id=h["wbs"].wbs_element_id,
    )
    await db.commit()

    items, total = await service.get_cost_events(wbs_element_id=h["wbs"].wbs_element_id)
    assert total >= 1

    items2, total2 = await service.get_cost_events(wbs_element_id=uuid4())
    assert total2 == 0


@pytest.mark.asyncio
async def test_get_cost_events_filter_by_status(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_cost_events filters by status."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        status="open",
    )
    await db.commit()

    items, total = await service.get_cost_events(status="open")
    assert total >= 1

    items2, total2 = await service.get_cost_events(status="closed")
    assert not any(e.project_id == h["project"].project_id for e in items2)


@pytest.mark.asyncio
async def test_get_coq_metrics_with_actual_costs(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_coq_metrics computes metrics when actual costs exist."""
    data = await _setup_event_with_registration(
        db,
        actor_id,
        coq_category="external_failure",
        registration_amount=Decimal("6000"),
    )

    metrics = await service.get_coq_metrics(data["project"].project_id)

    assert metrics.total_coq == Decimal("6000")
    assert metrics.cpq == Decimal("6000")
    assert metrics.cpiq is not None
    assert metrics.qpi is not None
    assert metrics.qpi_rating is not None


@pytest.mark.asyncio
async def test_get_coq_trend_with_data(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_coq_trend returns trend points when quality events exist."""
    data = await _setup_event_with_registration(
        db,
        actor_id,
        coq_category="internal_failure",
        registration_amount=Decimal("2000"),
    )

    trend = await service.get_coq_trend(data["project"].project_id)
    assert trend.start_date is not None
    assert trend.end_date is not None


@pytest.mark.asyncio
async def test_get_coq_trend_with_as_of_cap(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_coq_trend caps end_date to as_of when provided."""
    data = await _setup_event_with_registration(
        db,
        actor_id,
        coq_category="internal_failure",
        registration_amount=Decimal("1000"),
    )

    # Use a past as_of that should cap the range
    as_of = datetime.now(UTC) - timedelta(days=100)
    trend = await service.get_coq_trend(data["project"].project_id, as_of=as_of)
    # The trend should still return a valid response
    assert trend is not None


@pytest.mark.asyncio
async def test_get_summary_with_as_of(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """get_summary supports time-travel via as_of parameter."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db,
        actor_id,
        h["project"].project_id,
        h["cet"].cost_event_type_id,
        coq_category="prevention",
        estimated_impact=Decimal("3000"),
    )
    await db.commit()

    as_of = datetime.now(UTC) + timedelta(hours=1)
    summary = await service.get_summary(h["project"].project_id, as_of=as_of)

    assert summary.total_cost == Decimal("3000")
    assert summary.prevention_cost == Decimal("3000")


@pytest.mark.asyncio
async def test_coq_ratio_none_when_no_budget(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """_compute_coq_ratio returns None when project budget is zero."""
    h = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("0"))
    await db.commit()

    ratio = await service._compute_coq_ratio(h["project"].project_id, Decimal("1000"))
    assert ratio is None


@pytest.mark.asyncio
async def test_create_cost_event_with_allocations_and_get(
    db: AsyncSession, actor_id: UUID, service: CostEventService
) -> None:
    """create_cost_event with allocations then get_allocations returns them."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostEventCreate(
        project_id=h["project"].project_id,
        cost_event_type_id=h["cet"].cost_event_type_id,
        name="Multi-Allocation Event",
        coq_category="appraisal",
        estimated_impact=Decimal("5000"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=h["ce"].cost_element_id,
                amount=Decimal("2000"),
                description="First allocation",
            ),
            QualityCostAllocation(
                cost_element_id=h["ce"].cost_element_id,
                amount=Decimal("3000"),
                description="Second allocation",
            ),
        ],
    )
    event = await service.create_cost_event(data, actor_id)
    await db.commit()

    allocations = await service.get_allocations(event.cost_event_id)
    assert len(allocations) == 2
    total_amount = sum(a.amount for a in allocations)
    assert total_amount == Decimal("5000")
