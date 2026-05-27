"""Service-level tests for WorkPackageService.

Tests cover CRUD operations, listing with filters, budget status
computation, breadcrumb navigation, and batch time-travel queries.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.work_package import WorkPackageCreate, WorkPackageUpdate
from app.services.work_package_service import WorkPackageService
from tests.factories import (
    create_full_hierarchy,
    create_test_work_package,
)


@pytest.fixture
def service(db: AsyncSession) -> WorkPackageService:
    return WorkPackageService(db)


@pytest.mark.asyncio
async def test_create_work_package_via_service(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """create_work_package persists a new WP under a control account."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = WorkPackageCreate(
        control_account_id=h["ca"].control_account_id,
        name="Service Test WP",
        code="WP-SVC-001",
        budget_amount=Decimal("75000"),
        status="open",
    )
    wp = await service.create_work_package(data, actor_id)
    await db.flush()

    assert wp.work_package_id is not None
    assert wp.name == "Service Test WP"
    assert wp.code == "WP-SVC-001"
    assert wp.budget_amount == Decimal("75000")
    assert wp.control_account_id == h["ca"].control_account_id
    assert wp.status == "open"


@pytest.mark.asyncio
async def test_create_work_package_invalid_control_account_raises(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """create_work_package raises ValueError for non-existent control account."""
    data = WorkPackageCreate(
        control_account_id=uuid4(),
        name="Bad WP",
        code="WP-BAD",
        budget_amount=Decimal("1000"),
    )
    with pytest.raises(ValueError, match="Control Account.*not found"):
        await service.create_work_package(data, actor_id)


@pytest.mark.asyncio
async def test_create_root_work_package(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """create_root creates a WP using raw root_id and data kwargs."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    root_id = uuid4()
    wp = await service.create_root(
        root_id=root_id,
        actor_id=actor_id,
        control_account_id=h["ca"].control_account_id,
        name="Root WP",
        code="WP-ROOT",
        budget_amount=Decimal("10000"),
        status="open",
    )
    await db.commit()

    assert wp.work_package_id == root_id
    assert wp.name == "Root WP"


@pytest.mark.asyncio
async def test_update_work_package(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """update_work_package creates a new version with updated fields."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    original_id = h["wp"].work_package_id

    data = WorkPackageUpdate(
        name="Updated WP Name",
        budget_amount=Decimal("99999"),
        status="closed",
    )
    updated = await service.update_work_package(original_id, data, actor_id)
    await db.flush()

    assert updated.work_package_id == original_id
    assert updated.name == "Updated WP Name"
    assert updated.budget_amount == Decimal("99999")
    assert updated.status == "closed"


@pytest.mark.asyncio
async def test_get_work_packages_list(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_work_packages returns paginated list with total count."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    items, total = await service.get_work_packages()
    assert total >= 1
    assert any(wp.work_package_id == h["wp"].work_package_id for wp in items)


@pytest.mark.asyncio
async def test_get_work_packages_filter_by_control_account(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_work_packages filters by control_account_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    items, total = await service.get_work_packages(
        control_account_id=h["ca"].control_account_id
    )
    assert total >= 1
    assert all(wp.control_account_id == h["ca"].control_account_id for wp in items)

    # Filtering by a random UUID returns 0
    items2, total2 = await service.get_work_packages(control_account_id=uuid4())
    assert total2 == 0
    assert items2 == []


@pytest.mark.asyncio
async def test_get_work_packages_filter_by_status(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_work_packages filters by status."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    items, total = await service.get_work_packages(status="open")
    assert total >= 1
    assert all(wp.status == "open" for wp in items)

    # Filtering by "closed" should not include our open WP
    items2, total2 = await service.get_work_packages(status="closed")
    assert not any(wp.work_package_id == h["wp"].work_package_id for wp in items2)


@pytest.mark.asyncio
async def test_get_work_packages_pagination(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_work_packages respects skip and limit."""
    h = await create_full_hierarchy(db, actor_id)
    # Create a second WP
    await create_test_work_package(db, actor_id, h["ca"].control_account_id)
    await db.commit()

    items_all, total = await service.get_work_packages(limit=100)
    assert total >= 2

    items_first, _ = await service.get_work_packages(skip=0, limit=1)
    assert len(items_first) == 1

    items_second, _ = await service.get_work_packages(skip=1, limit=1)
    assert len(items_second) <= 1


@pytest.mark.asyncio
async def test_get_breadcrumb(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_breadcrumb returns full hierarchy Project -> WBS -> CA -> WP."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    bc = await service.get_breadcrumb(h["wp"].work_package_id)

    assert bc["project"]["project_id"] == h["project"].project_id
    assert bc["wbs_element"]["wbs_element_id"] == h["wbs"].wbs_element_id
    assert bc["control_account"]["control_account_id"] == h["ca"].control_account_id
    assert bc["work_package"]["work_package_id"] == h["wp"].work_package_id

    # Each level has required display fields
    assert bc["project"]["name"] is not None
    assert bc["wbs_element"]["code"] is not None
    assert bc["work_package"]["code"] is not None


@pytest.mark.asyncio
async def test_get_breadcrumb_not_found_raises(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_breadcrumb raises ValueError for unknown WP."""
    with pytest.raises(ValueError, match="Work Package.*not found"):
        await service.get_breadcrumb(uuid4())


@pytest.mark.asyncio
async def test_get_budget_status_no_registrations(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_budget_status returns budget=50000, used=0 for a WP with no cost registrations."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    status = await service.get_budget_status(h["wp"].work_package_id)

    assert status["budget"] == Decimal("50000")
    assert status["used"] == Decimal("0")
    assert status["remaining"] == Decimal("50000")
    assert status["percentage"] == Decimal("0")


@pytest.mark.asyncio
async def test_get_budget_status_with_registrations(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_budget_status sums CostRegistration amounts through CostElements."""
    from tests.factories import create_test_cost_registration

    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create cost registrations against the cost element
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("10000")
    )
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("15000")
    )
    await db.commit()

    status = await service.get_budget_status(h["wp"].work_package_id)

    assert status["budget"] == Decimal("50000")
    assert status["used"] == Decimal("25000")
    assert status["remaining"] == Decimal("25000")
    assert status["percentage"] == Decimal("50")


@pytest.mark.asyncio
async def test_get_budget_status_not_found_raises(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_budget_status raises ValueError for unknown WP."""
    with pytest.raises(ValueError, match="Work Package.*not found"):
        await service.get_budget_status(uuid4())


@pytest.mark.asyncio
async def test_get_as_of_batch(
    db: AsyncSession, actor_id: UUID, service: WorkPackageService
) -> None:
    """get_as_of_batch returns a dict keyed by work_package_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    result = await service.get_as_of_batch(
        entity_ids=[h["wp"].work_package_id, uuid4()]
    )
    assert h["wp"].work_package_id in result
    assert len(result) == 1

    # Empty list returns empty dict
    empty = await service.get_as_of_batch(entity_ids=[])
    assert empty == {}
