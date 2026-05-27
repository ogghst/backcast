"""Service-level tests for ControlAccountService.

Tests Control Account CRUD, WBS x OrgUnit intersection,
listing by WBS / OrgUnit, budget computation, and edge cases
via direct service calls.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.control_account_service import ControlAccountService
from tests.factories import (
    create_full_hierarchy,
    create_test_control_account,
    create_test_org_unit,
    create_test_project,
    create_test_wbs_element,
    create_test_work_package,
)

# ---------------------------------------------------------------------------
# create_root
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_control_account_root(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id, code="CA-ORG1")
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = ControlAccountService(db)
    root_id = uuid4()
    ca = await service.create_root(
        root_id=root_id,
        actor_id=actor_id,
        wbs_element_id=wbs.wbs_element_id,
        organizational_unit_id=org.organizational_unit_id,
        name="Test Control Account",
    )
    await db.commit()

    assert ca.control_account_id == root_id
    assert ca.wbs_element_id == wbs.wbs_element_id
    assert ca.organizational_unit_id == org.organizational_unit_id
    assert ca.name == "Test Control Account"
    assert ca.branch == "main"


# ---------------------------------------------------------------------------
# get_control_accounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_control_accounts_returns_created(db: AsyncSession, actor_id) -> None:
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = ControlAccountService(db)
    results, total = await service.get_control_accounts()
    assert total >= 1
    ca_ids = [ca.control_account_id for ca in results]
    assert hierarchy["ca"].control_account_id in ca_ids


@pytest.mark.asyncio
async def test_get_control_accounts_filter_by_wbs(db: AsyncSession, actor_id) -> None:
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = ControlAccountService(db)
    results, total = await service.get_control_accounts(
        wbs_element_id=hierarchy["wbs"].wbs_element_id
    )
    assert total >= 1
    for ca in results:
        assert ca.wbs_element_id == hierarchy["wbs"].wbs_element_id


@pytest.mark.asyncio
async def test_get_control_accounts_filter_by_org_unit(
    db: AsyncSession, actor_id
) -> None:
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = ControlAccountService(db)
    results, total = await service.get_control_accounts(
        organizational_unit_id=hierarchy["org_unit"].organizational_unit_id
    )
    assert total >= 1
    for ca in results:
        assert ca.organizational_unit_id == hierarchy["org_unit"].organizational_unit_id


@pytest.mark.asyncio
async def test_get_control_accounts_filter_by_both(db: AsyncSession, actor_id) -> None:
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = ControlAccountService(db)
    results, total = await service.get_control_accounts(
        wbs_element_id=hierarchy["wbs"].wbs_element_id,
        organizational_unit_id=hierarchy["org_unit"].organizational_unit_id,
    )
    assert total >= 1
    for ca in results:
        assert ca.wbs_element_id == hierarchy["wbs"].wbs_element_id
        assert ca.organizational_unit_id == hierarchy["org_unit"].organizational_unit_id


@pytest.mark.asyncio
async def test_get_control_accounts_nonexistent_wbs_returns_empty(
    db: AsyncSession, actor_id
) -> None:
    service = ControlAccountService(db)
    results, total = await service.get_control_accounts(wbs_element_id=uuid4())
    assert total == 0
    assert results == []


@pytest.mark.asyncio
async def test_get_control_accounts_pagination(db: AsyncSession, actor_id) -> None:
    service = ControlAccountService(db)
    results, total = await service.get_control_accounts(skip=0, limit=1)
    assert len(results) <= 1


# ---------------------------------------------------------------------------
# get_or_create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_creates_new(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id, code="GOC-ORG")
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = ControlAccountService(db)
    ca = await service.get_or_create(
        wbs_element_id=wbs.wbs_element_id,
        organizational_unit_id=org.organizational_unit_id,
        name="New CA",
        actor_id=actor_id,
    )
    await db.commit()

    assert ca is not None
    assert ca.wbs_element_id == wbs.wbs_element_id
    assert ca.organizational_unit_id == org.organizational_unit_id


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id, code="GOC-EORG")
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = ControlAccountService(db)
    ca1 = await service.get_or_create(
        wbs_element_id=wbs.wbs_element_id,
        organizational_unit_id=org.organizational_unit_id,
        name="First CA",
        actor_id=actor_id,
    )
    await db.commit()

    ca2 = await service.get_or_create(
        wbs_element_id=wbs.wbs_element_id,
        organizational_unit_id=org.organizational_unit_id,
        name="Second CA",
        actor_id=actor_id,
    )
    await db.commit()

    # Should return the same control account (same root ID)
    assert ca1.control_account_id == ca2.control_account_id


# ---------------------------------------------------------------------------
# compute_budget
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_budget_with_work_packages(db: AsyncSession, actor_id) -> None:
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = ControlAccountService(db)
    budget = await service.compute_budget(hierarchy["ca"].control_account_id)
    assert budget == Decimal("50000")  # default budget_amount from factory


@pytest.mark.asyncio
async def test_compute_budget_zero_without_work_packages(
    db: AsyncSession, actor_id
) -> None:
    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id, code="BUD-ORG")
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    await db.commit()

    service = ControlAccountService(db)
    budget = await service.compute_budget(ca.control_account_id)
    assert budget == Decimal("0")


@pytest.mark.asyncio
async def test_compute_budget_sums_multiple_work_packages(
    db: AsyncSession, actor_id
) -> None:
    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id, code="BUD2-ORG")
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    await create_test_work_package(
        db, actor_id, ca.control_account_id, budget_amount=Decimal("30000")
    )
    await create_test_work_package(
        db, actor_id, ca.control_account_id, budget_amount=Decimal("20000")
    )
    await db.commit()

    service = ControlAccountService(db)
    budget = await service.compute_budget(ca.control_account_id)
    assert budget == Decimal("50000")


@pytest.mark.asyncio
async def test_compute_budget_nonexistent_ca_returns_zero(
    db: AsyncSession, actor_id
) -> None:
    service = ControlAccountService(db)
    budget = await service.compute_budget(uuid4())
    assert budget == Decimal("0")
