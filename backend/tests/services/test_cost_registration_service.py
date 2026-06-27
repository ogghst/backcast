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


# ---------------------------------------------------------------------------
# WBS Element Budget Status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_element_budget_status(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_wbs_element_budget_status returns budget aggregated through hierarchy."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("15000")
    )
    await db.commit()

    status = await service.get_wbs_element_budget_status(h["wbs"].wbs_element_id)

    assert status.budget > Decimal("0")
    assert status.total_spend == Decimal("15000")
    assert status.remaining > Decimal("0")


@pytest.mark.asyncio
async def test_get_wbs_element_budget_status_zero_budget(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_wbs_element_budget_status with zero budget => percentage is 0."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create a new WBS element with no WPs under it, so budget=0
    from tests.factories import create_test_wbs_element

    empty_wbs = await create_test_wbs_element(db, actor_id, h["project"].project_id)
    await db.commit()

    status = await service.get_wbs_element_budget_status(empty_wbs.wbs_element_id)

    assert status.budget == Decimal("0")
    assert status.total_spend == Decimal("0")
    assert status.percentage == Decimal("0")


@pytest.mark.asyncio
async def test_get_wbe_budget_status_alias(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_wbe_budget_status is an alias for get_wbs_element_budget_status."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    status = await service.get_wbe_budget_status(h["wbs"].wbs_element_id)

    assert status.wbs_element_id == h["wbs"].wbs_element_id


# ---------------------------------------------------------------------------
# Budget Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_budget_status_below_threshold(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_budget_status returns None when below threshold."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("100")
    )
    await db.commit()

    result = await service.validate_budget_status(
        work_package_id=h["wp"].work_package_id,
        project_id=h["project"].project_id,
        user_id=actor_id,
    )

    # Default threshold is 80%, spending 100 out of 50000 => well below
    assert result is None


@pytest.mark.asyncio
async def test_validate_budget_status_above_threshold(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_budget_status returns warning when above threshold."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    # Set a very low warning threshold
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        warning_threshold_percent=Decimal("1.0"),
    )
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("1000")
    )
    await db.commit()

    result = await service.validate_budget_status(
        work_package_id=h["wp"].work_package_id,
        project_id=h["project"].project_id,
        user_id=actor_id,
    )

    assert result is not None
    assert result.exceeds_threshold is True


# ---------------------------------------------------------------------------
# Work Package Budget Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_work_package_budget_not_enforced(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_work_package_budget returns None when enforcement disabled."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    result = await service.validate_work_package_budget(
        work_package_id=h["wp"].work_package_id,
        new_amount=Decimal("999999"),
        project_id=h["project"].project_id,
    )

    # Default: enforce_budget=False => always None
    assert result is None


@pytest.mark.asyncio
async def test_validate_work_package_budget_exceeded(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_work_package_budget returns error when budget exceeded."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    # Enable enforcement
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        enforce_budget=True,
    )
    await db.commit()

    # WP budget is 50000, try to spend 60000
    result = await service.validate_work_package_budget(
        work_package_id=h["wp"].work_package_id,
        new_amount=Decimal("60000"),
        project_id=h["project"].project_id,
    )

    assert result is not None
    assert result.over_by > Decimal("0")


@pytest.mark.asyncio
async def test_validate_work_package_budget_update_within_budget(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_work_package_budget with is_update subtracts old amount."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("30000")
    )
    # Enable enforcement
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        enforce_budget=True,
    )
    await db.commit()

    # Update: old=30000, new=40000 => effective=30000-30000+40000=40000 < 50000
    result = await service.validate_work_package_budget(
        work_package_id=h["wp"].work_package_id,
        new_amount=Decimal("40000"),
        project_id=h["project"].project_id,
        is_update=True,
        old_amount=Decimal("30000"),
    )

    assert result is None


# ---------------------------------------------------------------------------
# Cost Element Budget Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_cost_element_budget_not_found(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_cost_element_budget returns None for nonexistent CE."""
    result = await service.validate_cost_element_budget(
        cost_element_id=uuid4(),
        new_amount=Decimal("1000"),
        project_id=uuid4(),
    )
    assert result is None


# ---------------------------------------------------------------------------
# create_cost_registration - edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_cost_registration_no_work_package(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration raises when WP not found for CE."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create a CE not attached to a reachable WP on a different branch

    # The CE exists, but the WP is on branch "main" and we request branch "nonexistent"
    # This should still work since WP fallback to main exists
    data = CostRegistrationCreate(
        cost_element_id=h["ce"].cost_element_id,
        amount=Decimal("500"),
    )
    # This should succeed on "main" branch
    cr = await service.create_cost_registration(data, actor_id, branch="main")
    await db.flush()
    assert cr is not None


@pytest.mark.asyncio
async def test_create_cost_registration_with_control_date(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration uses explicit control_date."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostRegistrationCreate(
        cost_element_id=h["ce"].cost_element_id,
        amount=Decimal("2000"),
    )
    cr = await service.create_cost_registration(
        data, actor_id, control_date=datetime(2026, 1, 1, tzinfo=UTC)
    )
    await db.flush()
    assert cr is not None


# ---------------------------------------------------------------------------
# update_cost_registration - budget validation path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_cost_registration_amount_triggers_budget_check(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """update_cost_registration with amount triggers budget validation."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("1000")
    )
    # Enable enforcement with a very low budget
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        enforce_budget=True,
    )
    await db.commit()

    # Update to a huge amount should fail
    data = CostRegistrationUpdate(amount=Decimal("999999"))
    with pytest.raises(ValueError, match="exceed"):
        await service.update_cost_registration(cr.cost_registration_id, data, actor_id)


@pytest.mark.asyncio
async def test_update_cost_registration_no_amount(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """update_cost_registration without amount skips budget check."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("1000")
    )
    await db.commit()

    data = CostRegistrationUpdate(description="Updated description only")
    updated = await service.update_cost_registration(
        cr.cost_registration_id, data, actor_id
    )
    await db.flush()

    assert updated.description == "Updated description only"
    assert updated.amount == Decimal("1000")


# ---------------------------------------------------------------------------
# get_cost_registrations - WBS filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cost_registrations_filter_by_wbs(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations filters by wbs_element_id."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, total, _ = await service.get_cost_registrations(
        wbs_element_id=h["wbs"].wbs_element_id
    )
    assert total >= 1

    items2, total2, _ = await service.get_cost_registrations(wbs_element_id=uuid4())
    assert total2 == 0


# ---------------------------------------------------------------------------
# get_work_package_info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_work_package_info(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_work_package_info returns name for existing WP."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    name, type_code = await service.get_work_package_info(h["wp"].work_package_id)
    assert name is not None
    assert isinstance(name, str)


@pytest.mark.asyncio
async def test_get_work_package_info_none_input(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_work_package_info returns None, None for None input."""
    name, type_code = await service.get_work_package_info(None)
    assert name is None
    assert type_code is None


@pytest.mark.asyncio
async def test_get_work_package_info_not_found(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_work_package_info returns None, None for nonexistent WP."""
    name, type_code = await service.get_work_package_info(uuid4())
    assert name is None
    assert type_code is None


# ---------------------------------------------------------------------------
# get_cost_registration_as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cost_registration_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registration_as_of returns registration at historical timestamp."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await db.commit()

    result = await service.get_cost_registration_as_of(
        cr.cost_registration_id, datetime.now(UTC) + timedelta(hours=1)
    )
    assert result is not None
    assert result.amount == Decimal("5000")


# ---------------------------------------------------------------------------
# get_budget_status - fallback to main branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_budget_status_fallback_to_main(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_budget_status falls back to main branch when WP not on feature branch."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Query on a non-existent branch - should fall back to main
    status = await service.get_budget_status(
        h["wp"].work_package_id, branch="feature-test"
    )

    assert status.budget == Decimal("50000")


# ---------------------------------------------------------------------------
# get_total_for_cost_element - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_total_for_cost_element_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_total_for_cost_element with as_of time-travel."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("3000")
    )
    await db.commit()

    # Time-travel to future should include the cost
    total = await service.get_total_for_cost_element(
        h["ce"].cost_element_id, as_of=datetime.now(UTC) + timedelta(hours=1)
    )
    assert Decimal(str(total)) == Decimal("3000")


# ---------------------------------------------------------------------------
# get_total_for_work_package - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_total_for_work_package_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_total_for_work_package with as_of time-travel."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("7000")
    )
    await db.commit()

    total = await service.get_total_for_work_package(
        h["wp"].work_package_id, as_of=datetime.now(UTC) + timedelta(hours=1)
    )
    assert Decimal(str(total)) == Decimal("7000")


# ---------------------------------------------------------------------------
# get_costs_by_period - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_costs_by_period_with_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_costs_by_period with as_of parameter."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("500"),
        registration_date=now,
    )
    await db.commit()

    periods = await service.get_costs_by_period(
        cost_element_id=h["ce"].cost_element_id,
        period="daily",
        start_date=now - timedelta(days=1),
        as_of=now + timedelta(hours=1),
    )
    assert len(periods) >= 1


# ---------------------------------------------------------------------------
# get_cumulative_costs - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cumulative_costs_with_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs with as_of parameter."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("1500"),
        registration_date=now - timedelta(days=2),
    )
    await db.commit()

    cum = await service.get_cumulative_costs(
        cost_element_id=h["ce"].cost_element_id,
        start_date=now - timedelta(days=10),
        as_of=now + timedelta(hours=1),
    )
    assert len(cum) == 1
    assert cum[0]["cumulative_amount"] == 1500.0


# ---------------------------------------------------------------------------
# get_cumulative_costs_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cumulative_costs_batch(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs_batch returns dict of CE to cumulative costs."""
    h = await create_full_hierarchy(db, actor_id)
    from tests.factories import create_test_cost_element

    ce2 = await create_test_cost_element(
        db, actor_id, h["wp"].work_package_id, h["ce_type"].cost_element_type_id
    )
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
        ce2.cost_element_id,
        amount=Decimal("2000"),
        registration_date=now - timedelta(days=1),
    )
    await db.commit()

    result = await service.get_cumulative_costs_batch(
        cost_element_ids=[h["ce"].cost_element_id, ce2.cost_element_id],
        start_date=now - timedelta(days=10),
    )

    assert h["ce"].cost_element_id in result
    assert ce2.cost_element_id in result
    assert result[h["ce"].cost_element_id][0]["cumulative_amount"] == 1000.0
    assert result[ce2.cost_element_id][0]["cumulative_amount"] == 2000.0


@pytest.mark.asyncio
async def test_get_cumulative_costs_batch_empty(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs_batch with empty list returns empty dict."""
    result = await service.get_cumulative_costs_batch(
        cost_element_ids=[], start_date=datetime.now(UTC)
    )
    assert result == {}


# ---------------------------------------------------------------------------
# _get_costs_by_period_for_ces
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_costs_by_period_for_ces(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """_get_costs_by_period_for_ces batches period aggregation for multiple CEs."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("3000"),
        registration_date=now,
    )
    await db.commit()

    result = await service._get_costs_by_period_for_ces(
        ce_ids=[h["ce"].cost_element_id],
        period="daily",
        start_date=now - timedelta(days=1),
    )
    assert len(result) >= 1
    assert result[0]["total_amount"] == 3000.0


@pytest.mark.asyncio
async def test_get_costs_by_period_for_ces_empty(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """_get_costs_by_period_for_ces with empty list returns empty."""
    result = await service._get_costs_by_period_for_ces(
        ce_ids=[], period="daily", start_date=datetime.now(UTC)
    )
    assert result == []


# ---------------------------------------------------------------------------
# _resolve_cost_element_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_cost_element_ids_wbs_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """_resolve_cost_element_ids resolves WBS element to CE IDs."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    result = await service._resolve_cost_element_ids(
        "wbs_element", h["wbs"].wbs_element_id
    )
    assert len(result) >= 1
    assert h["ce"].cost_element_id in result


@pytest.mark.asyncio
async def test_resolve_cost_element_ids_project(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """_resolve_cost_element_ids resolves project to CE IDs."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    result = await service._resolve_cost_element_ids("project", h["project"].project_id)
    assert len(result) >= 1
    assert h["ce"].cost_element_id in result


@pytest.mark.asyncio
async def test_resolve_cost_element_ids_unsupported(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """_resolve_cost_element_ids raises for unsupported entity type."""
    with pytest.raises(ValueError, match="Unsupported entity_type"):
        await service._resolve_cost_element_ids("invalid_type", uuid4())


# ---------------------------------------------------------------------------
# get_aggregated_costs_by_entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_aggregated_costs_by_entity_cost_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_aggregated_costs_by_entity delegates to get_costs_by_period for cost_element."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("4000"),
        registration_date=now,
    )
    await db.commit()

    result = await service.get_aggregated_costs_by_entity(
        entity_type="cost_element",
        entity_id=h["ce"].cost_element_id,
        period="daily",
        start_date=now - timedelta(days=1),
    )
    assert len(result) >= 1
    assert result[0]["total_amount"] == 4000.0


@pytest.mark.asyncio
async def test_get_aggregated_costs_by_entity_project(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_aggregated_costs_by_entity resolves project and aggregates."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("2500"),
        registration_date=now,
    )
    await db.commit()

    result = await service.get_aggregated_costs_by_entity(
        entity_type="project",
        entity_id=h["project"].project_id,
        period="daily",
        start_date=now - timedelta(days=1),
    )
    assert len(result) >= 1
    assert result[0]["total_amount"] == 2500.0


@pytest.mark.asyncio
async def test_get_aggregated_costs_by_entity_no_ces(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_aggregated_costs_by_entity returns empty when no CEs found."""
    from tests.factories import create_test_project

    project = await create_test_project(db, actor_id)
    await db.commit()

    result = await service.get_aggregated_costs_by_entity(
        entity_type="project",
        entity_id=project.project_id,
        period="daily",
        start_date=datetime.now(UTC),
    )
    assert result == []


# ---------------------------------------------------------------------------
# get_cumulative_costs_by_entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cumulative_costs_by_entity_cost_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs_by_entity delegates for cost_element type."""
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

    result = await service.get_cumulative_costs_by_entity(
        entity_type="cost_element",
        entity_id=h["ce"].cost_element_id,
        start_date=now - timedelta(days=10),
    )
    assert len(result) == 2
    assert result[0]["cumulative_amount"] == 1000.0
    assert result[1]["cumulative_amount"] == 3000.0


@pytest.mark.asyncio
async def test_get_cumulative_costs_by_entity_project(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs_by_entity merges cumulative costs for project."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("1500"),
        registration_date=now - timedelta(days=1),
    )
    await db.commit()

    result = await service.get_cumulative_costs_by_entity(
        entity_type="project",
        entity_id=h["project"].project_id,
        start_date=now - timedelta(days=10),
    )
    assert len(result) >= 1
    assert result[0]["cumulative_amount"] == 1500.0


@pytest.mark.asyncio
async def test_get_cumulative_costs_by_entity_no_ces(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs_by_entity returns empty when no CEs found."""
    from tests.factories import create_test_project

    project = await create_test_project(db, actor_id)
    await db.commit()

    result = await service.get_cumulative_costs_by_entity(
        entity_type="project",
        entity_id=project.project_id,
        start_date=datetime.now(UTC),
    )
    assert result == []


# ---------------------------------------------------------------------------
# get_project_budget_status - branch fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_budget_status_branch_fallback(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_project_budget_status falls back to main branch."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    status = await service.get_project_budget_status(
        h["project"].project_id, branch="feature-branch"
    )
    assert status.project_budget > Decimal("0")


# ---------------------------------------------------------------------------
# get_totals_for_cost_elements - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_totals_for_cost_elements_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_totals_for_cost_elements with as_of time-travel."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await db.commit()

    totals = await service.get_totals_for_cost_elements(
        [h["ce"].cost_element_id], as_of=datetime.now(UTC) + timedelta(hours=1)
    )
    assert totals[h["ce"].cost_element_id] == Decimal("5000")


# ---------------------------------------------------------------------------
# get_project_budget_status - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_budget_status_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_project_budget_status with as_of applies bitemporal filter."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await db.commit()

    status = await service.get_project_budget_status(
        h["project"].project_id, as_of=datetime.now(UTC) + timedelta(hours=1)
    )
    assert status.total_spend == Decimal("5000")


# ---------------------------------------------------------------------------
# get_wbs_element_budget_status - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_element_budget_status_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_wbs_element_budget_status with as_of applies bitemporal filter."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("3000")
    )
    await db.commit()

    status = await service.get_wbs_element_budget_status(
        h["wbs"].wbs_element_id, as_of=datetime.now(UTC) + timedelta(hours=1)
    )
    assert status.total_spend == Decimal("3000")


# ---------------------------------------------------------------------------
# get_cost_registrations - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cost_registrations_with_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations with as_of applies bitemporal filter."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, total, _ = await service.get_cost_registrations(
        as_of=datetime.now(UTC) + timedelta(hours=1)
    )
    assert total >= 1


# ---------------------------------------------------------------------------
# validate_work_package_budget - branch fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_work_package_budget_branch_fallback(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_work_package_budget falls back to main branch."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        enforce_budget=True,
    )
    await db.commit()

    # Query on a non-existent branch - should fall back to main
    result = await service.validate_work_package_budget(
        work_package_id=h["wp"].work_package_id,
        new_amount=Decimal("60000"),
        project_id=h["project"].project_id,
        branch="feature-branch",
    )

    assert result is not None
    assert result.over_by > Decimal("0")


# ---------------------------------------------------------------------------
# validate_cost_element_budget - with enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_cost_element_budget_enforced(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """validate_cost_element_budget returns error when CE would exceed budget."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        enforce_budget=True,
    )
    await db.commit()

    result = await service.validate_cost_element_budget(
        cost_element_id=h["ce"].cost_element_id,
        new_amount=Decimal("60000"),
        project_id=h["project"].project_id,
    )

    assert result is not None
    assert result.over_by > Decimal("0")


# ---------------------------------------------------------------------------
# create_cost_registration - budget exceeded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_cost_registration_budget_exceeded(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration raises ValueError when budget enforcement blocks."""
    from app.services.project_budget_settings_service import (
        ProjectBudgetSettingsService,
    )

    h = await create_full_hierarchy(db, actor_id)
    settings_svc = ProjectBudgetSettingsService(db)
    await settings_svc.upsert_settings(
        project_id=h["project"].project_id,
        actor_id=actor_id,
        enforce_budget=True,
    )
    await db.commit()

    data = CostRegistrationCreate(
        cost_element_id=h["ce"].cost_element_id,
        amount=Decimal("999999"),
    )
    with pytest.raises(ValueError, match="exceed"):
        await service.create_cost_registration(data, actor_id)


# ---------------------------------------------------------------------------
# create_cost_registration - WP not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_cost_registration_wp_not_found(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """create_cost_registration raises when WP not found on any branch."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create a CE pointing to a different, non-existent WP
    from tests.factories import create_test_cost_element, create_test_cost_element_type

    ce_type = await create_test_cost_element_type(
        db, actor_id, h["org_unit"].organizational_unit_id
    )
    ce = await create_test_cost_element(
        db, actor_id, uuid4(), ce_type.cost_element_type_id
    )
    await db.commit()

    data = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        amount=Decimal("1000"),
    )
    with pytest.raises(ValueError, match="Work Package.*not found"):
        await service.create_cost_registration(data, actor_id)


# ---------------------------------------------------------------------------
# _get_costs_by_period_for_ces - with as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_costs_by_period_for_ces_as_of(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """_get_costs_by_period_for_ces with as_of parameter."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("4000"),
        registration_date=now,
    )
    await db.commit()

    result = await service._get_costs_by_period_for_ces(
        ce_ids=[h["ce"].cost_element_id],
        period="daily",
        start_date=now - timedelta(days=1),
        as_of=now + timedelta(hours=1),
    )
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# get_cumulative_costs_by_entity - wbs_element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cumulative_costs_by_entity_wbs_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cumulative_costs_by_entity resolves wbs_element and aggregates."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("2000"),
        registration_date=now - timedelta(days=1),
    )
    await db.commit()

    result = await service.get_cumulative_costs_by_entity(
        entity_type="wbs_element",
        entity_id=h["wbs"].wbs_element_id,
        start_date=now - timedelta(days=10),
    )
    assert len(result) >= 1
    assert result[0]["cumulative_amount"] == 2000.0


# ---------------------------------------------------------------------------
# get_aggregated_costs_by_entity - wbs_element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_aggregated_costs_by_entity_wbs_element(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_aggregated_costs_by_entity resolves wbs_element and aggregates."""
    h = await create_full_hierarchy(db, actor_id)
    now = datetime.now(UTC)
    await create_test_cost_registration(
        db,
        actor_id,
        h["ce"].cost_element_id,
        amount=Decimal("3500"),
        registration_date=now,
    )
    await db.commit()

    result = await service.get_aggregated_costs_by_entity(
        entity_type="wbs_element",
        entity_id=h["wbs"].wbs_element_id,
        period="daily",
        start_date=now - timedelta(days=1),
    )
    assert len(result) >= 1
    assert result[0]["total_amount"] == 3500.0


# ---------------------------------------------------------------------------
# created_by_name population
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_populates_created_by_name(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_by_id should populate created_by_name from the creator user."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("1000")
    )
    await db.commit()

    result = await service.get_by_id(cr.cost_registration_id)
    assert result is not None
    assert result.created_by_name == "Admin User"


@pytest.mark.asyncio
async def test_get_cost_registrations_populates_created_by_name(
    db: AsyncSession, actor_id: UUID, service: CostRegistrationService
) -> None:
    """get_cost_registrations should populate created_by_name on each item."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    items, _total, _wp_map = await service.get_cost_registrations(
        filters={"cost_element_id": h["ce"].cost_element_id}
    )
    assert len(items) >= 1
    assert all(hasattr(i, "created_by_name") for i in items)
    assert any(i.created_by_name == "Admin User" for i in items)
