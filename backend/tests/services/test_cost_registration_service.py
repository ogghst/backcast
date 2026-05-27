"""Service-level tests for CostRegistrationService.

Tests cover CRUD, listing with hierarchy filters, budget status at
project/WBS/work-package levels, totals, cumulative costs, and period aggregation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
    CostRegistrationUpdate,
)
from app.services.cost_registration_service import CostRegistrationService
from tests.factories import (
    create_full_hierarchy,
    create_test_cost_element,
    create_test_cost_registration,
)


@pytest.fixture
def service(db: AsyncSession) -> CostRegistrationService:
    return CostRegistrationService(db)


@pytest.mark.asyncio
async def test_create_cost_registration_via_service(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration persists a registration against a cost element."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostRegistrationCreate(
        cost_element_id=h["ce"].cost_element_id,
        amount=Decimal("5000"),
        description="Vendor invoice",
        invoice_number="INV-001",
    )
    cr = await service.create_cost_registration(data, actor_id)
    await db.flush()

    assert cr.cost_registration_id is not None
    assert cr.cost_element_id == h["ce"].cost_element_id
    assert cr.amount == Decimal("5000")
    assert cr.invoice_number == "INV-001"
    assert cr.description == "Vendor invoice"


@pytest.mark.asyncio
async def test_create_cost_registration_invalid_cost_element_raises(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration raises ValueError for non-existent cost element."""
    data = CostRegistrationCreate(
        cost_element_id=uuid4(),
        amount=Decimal("1000"),
    )
    with pytest.raises(ValueError, match="Cost Element.*not found"):
        await service.create_cost_registration(data, actor_id)


@pytest.mark.asyncio
async def test_create_cost_registration_sets_default_date(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration sets registration_date to now if not provided."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostRegistrationCreate(
        cost_element_id=h["ce"].cost_element_id,
        amount=Decimal("2000"),
    )
    cr = await service.create_cost_registration(data, actor_id)
    await db.commit()

    assert cr.registration_date is not None


@pytest.mark.asyncio
async def test_update_cost_registration(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """update_cost_registration creates a new version with updated amount."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("1000")
    )
    await db.commit()

    data = CostRegistrationUpdate(amount=Decimal("2500"), description="Updated amount")
    updated = await service.update_cost_registration(
        cr.cost_registration_id, data, actor_id
    )
    await db.flush()

    assert updated.cost_registration_id == cr.cost_registration_id
    assert updated.amount == Decimal("2500")
    assert updated.description == "Updated amount"


@pytest.mark.asyncio
async def test_soft_delete_cost_registration(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """soft_delete marks the registration as deleted."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    await service.soft_delete(cr.cost_registration_id, actor_id)
    await db.commit()

    result = await service.get_by_id(cr.cost_registration_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_by_id returns the current version of a cost registration."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("7500")
    )
    await db.commit()

    result = await service.get_by_id(cr.cost_registration_id)
    assert result is not None
    assert result.cost_registration_id == cr.cost_registration_id
    assert result.amount == Decimal("7500")


@pytest.mark.asyncio
async def test_get_by_id_not_found(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_by_id returns None for unknown registration."""
    result = await service.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_cost_registrations_list(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations returns paginated list with total."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, total, wp_map = await service.get_cost_registrations()
    assert total >= 1


@pytest.mark.asyncio
async def test_get_cost_registrations_filter_by_cost_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations filters by cost_element_id via filters dict."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, total, _ = await service.get_cost_registrations(
        filters={"cost_element_id": h["ce"].cost_element_id}
    )
    assert total >= 1
    assert all(cr.cost_element_id == h["ce"].cost_element_id for cr in items)

    items2, total2, _ = await service.get_cost_registrations(
        filters={"cost_element_id": uuid4()}
    )
    assert total2 == 0


@pytest.mark.asyncio
async def test_get_cost_registrations_filter_by_project(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations filters by project_id through hierarchy."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, total, _ = await service.get_cost_registrations(
        project_id=h["project"].project_id
    )
    assert total >= 1

    items2, total2, _ = await service.get_cost_registrations(project_id=uuid4())
    assert total2 == 0


@pytest.mark.asyncio
async def test_get_cost_registrations_filter_by_work_package(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations filters by work_package_id through CostElement."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, total, _ = await service.get_cost_registrations(
        work_package_id=h["wp"].work_package_id
    )
    assert total >= 1

    items2, total2, _ = await service.get_cost_registrations(work_package_id=uuid4())
    assert total2 == 0


@pytest.mark.asyncio
async def test_get_total_for_cost_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_total_for_cost_element sums registrations for a single CE."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("3000")
    )
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("2000")
    )
    await db.commit()

    total = await service.get_total_for_cost_element(h["ce"].cost_element_id)
    assert Decimal(str(total)) == Decimal("5000")


@pytest.mark.asyncio
async def test_get_total_for_work_package(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_total_for_work_package sums registrations through all CEs under a WP."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("8000")
    )
    await db.commit()

    total = await service.get_total_for_work_package(h["wp"].work_package_id)
    assert Decimal(str(total)) == Decimal("8000")


@pytest.mark.asyncio
async def test_get_totals_for_cost_elements_batch(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_totals_for_cost_elements returns dict of CE ID to total."""
    h = await create_full_hierarchy(db, actor_id)
    # Create a second cost element
    ce2 = await create_test_cost_element(
        db,
        actor_id,
        h["wp"].work_package_id,
        h["ce_type"].cost_element_type_id,
    )
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("1500")
    )
    await create_test_cost_registration(
        db, actor_id, ce2.cost_element_id, amount=Decimal("2500")
    )
    await db.commit()

    totals = await service.get_totals_for_cost_elements(
        [h["ce"].cost_element_id, ce2.cost_element_id]
    )
    assert totals[h["ce"].cost_element_id] == Decimal("1500")
    assert totals[ce2.cost_element_id] == Decimal("2500")

    # Empty list returns empty dict
    empty = await service.get_totals_for_cost_elements([])
    assert empty == {}


@pytest.mark.asyncio
async def test_get_budget_status_for_work_package(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_budget_status returns budget, used, remaining for a work package."""
    h = await create_full_hierarchy(db, actor_id)
    # WP budget is 50000 from factory default
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("20000")
    )
    await db.commit()

    status = await service.get_budget_status(h["wp"].work_package_id)

    assert status.budget == Decimal("50000")
    assert status.used == Decimal("20000")
    assert status.remaining == Decimal("30000")
    assert status.percentage == Decimal("40")


@pytest.mark.asyncio
async def test_get_budget_status_not_found_raises(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_budget_status raises ValueError for unknown WP."""
    with pytest.raises(ValueError, match="Work package.*not found"):
        await service.get_budget_status(uuid4())


@pytest.mark.asyncio
async def test_get_project_budget_status(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_project_budget_status aggregates budget and spend at project level."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("10000")
    )
    await db.commit()

    status = await service.get_project_budget_status(h["project"].project_id)

    assert status.project_budget > Decimal("0")
    assert status.total_spend == Decimal("10000")
    assert status.remaining > Decimal("0")
    assert status.percentage > Decimal("0")


@pytest.mark.asyncio
async def test_get_project_budget_status_not_found_raises(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_project_budget_status raises ValueError for unknown project."""
    with pytest.raises(ValueError, match="Project.*not found"):
        await service.get_project_budget_status(uuid4())


@pytest.mark.asyncio
async def test_get_costs_by_period(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_costs_by_period aggregates costs into time buckets."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("1000"),
        registration_date=now,
    )
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("2000"),
        registration_date=now,
    )
    await db.commit()

    periods = await service.get_costs_by_period(
        cost_element_id=h["ce"].cost_element_id,
        period="daily",
        start_date=now - timedelta(days=1),
    )
    assert len(periods) >= 1
    assert any(p["total_amount"] == 3000.0 for p in periods)


@pytest.mark.asyncio
async def test_get_cumulative_costs(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs returns running total over time."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("1000"),
        registration_date=now - timedelta(days=2),
    )
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("2000"),
        registration_date=now - timedelta(days=1),
    )
    await db.commit()

    cum = await service.get_cumulative_costs(
        cost_element_id=h["ce"].cost_element_id,
        start_date=now - timedelta(days=10),
    )
    assert len(cum) == 2
    assert cum[0]["cumulative_amount"] == 1000.0
    assert cum[1]["cumulative_amount"] == 3000.0
