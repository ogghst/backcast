"""Service-level tests for WBSElementService.

Tests WBS Element CRUD, hierarchy (parent/child), budget computation,
listing with filters, and edge cases via direct service calls.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.wbs_element import WBSElementCreate, WBSElementUpdate
from app.services.wbs_element_service import WBSElementService
from tests.factories import (
    create_test_org_unit,
    create_test_project,
    create_test_wbs_element,
)

# ---------------------------------------------------------------------------
# create_wbe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_wbs_element_root_level(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = WBSElementService(db)
    wbe_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.0",
        name="Root WBS",
    )
    element = await service.create_wbe(wbe_in, actor_id)
    await db.commit()

    assert element.wbs_element_id is not None
    assert element.project_id == project.project_id
    assert element.code == "1.0"
    assert element.level == 1
    assert element.branch == "main"


@pytest.mark.asyncio
async def test_create_wbs_element_child_inherits_level(
    db: AsyncSession, actor_id
) -> None:
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.1",
        name="Child WBS",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    child = await service.create_wbe(child_in, actor_id)
    await db.commit()

    assert child.level == 2
    assert child.parent_wbs_element_id == parent.wbs_element_id


@pytest.mark.asyncio
async def test_create_wbs_element_invalid_project_raises(
    db: AsyncSession, actor_id
) -> None:
    service = WBSElementService(db)
    wbe_in = WBSElementCreate(
        project_id=uuid4(),
        code="1.0",
        name="Orphan WBS",
    )
    with pytest.raises(ValueError, match="Project .* not found"):
        await service.create_wbe(wbe_in, actor_id)


@pytest.mark.asyncio
async def test_create_wbs_element_invalid_parent_raises(
    db: AsyncSession, actor_id
) -> None:
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = WBSElementService(db)
    wbe_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.0",
        name="Bad Parent WBS",
        parent_wbs_element_id=uuid4(),
    )
    with pytest.raises(ValueError, match="Parent WBS Element .* not found"):
        await service.create_wbe(wbe_in, actor_id)


# ---------------------------------------------------------------------------
# get_wbs_elements (list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_elements_by_project(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    results, total = await service.get_wbs_elements(project_id=project.project_id)
    assert total >= 1
    wbs_ids = [w.wbs_element_id for w in results]
    assert wbs.wbs_element_id in wbs_ids


@pytest.mark.asyncio
async def test_get_wbs_elements_with_search(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    await create_test_wbs_element(
        db, actor_id, project.project_id, name="UniqueSearchName"
    )
    await db.commit()

    service = WBSElementService(db)
    results, total = await service.get_wbs_elements(
        project_id=project.project_id, search="UniqueSearchName"
    )
    assert total >= 1
    assert any(w.name == "UniqueSearchName" for w in results)


@pytest.mark.asyncio
async def test_get_wbs_elements_with_sorting(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    await create_test_wbs_element(
        db, actor_id, project.project_id, name="ZZZ Element", code="Z.0"
    )
    await create_test_wbs_element(
        db, actor_id, project.project_id, name="AAA Element", code="A.0"
    )
    await db.commit()

    service = WBSElementService(db)
    results, _total = await service.get_wbs_elements(
        project_id=project.project_id, sort_field="name", sort_order="asc"
    )
    names = [w.name for w in results if w.name in ("ZZZ Element", "AAA Element")]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_get_wbs_elements_invalid_sort_raises(db: AsyncSession, actor_id) -> None:
    service = WBSElementService(db)
    with pytest.raises(ValueError, match="Invalid sort field"):
        await service.get_wbs_elements(sort_field="bogus_field")


# ---------------------------------------------------------------------------
# get_by_project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_project_returns_elements(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    elements = await service.get_by_project(project.project_id)
    wbs_ids = [w.wbs_element_id for w in elements]
    assert wbs.wbs_element_id in wbs_ids


# ---------------------------------------------------------------------------
# get_by_parent / hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_parent_returns_children(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.1",
        name="Child Under Parent",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    child = await service.create_wbe(child_in, actor_id)
    await db.commit()

    children = await service.get_by_parent(
        project_id=project.project_id,
        parent_wbe_id=parent.wbs_element_id,
    )
    child_ids = [c.wbs_element_id for c in children]
    assert child.wbs_element_id in child_ids


@pytest.mark.asyncio
async def test_get_by_parent_root_level(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    root = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    roots = await service.get_by_parent(
        project_id=project.project_id,
        parent_wbe_id=None,
    )
    root_ids = [r.wbs_element_id for r in roots]
    assert root.wbs_element_id in root_ids


# ---------------------------------------------------------------------------
# get_by_code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_code_finds_element(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id, code="3.2.1")
    await db.commit()

    service = WBSElementService(db)
    found = await service.get_by_code("3.2.1", project.project_id)
    assert found is not None
    assert found.wbs_element_id == wbs.wbs_element_id


@pytest.mark.asyncio
async def test_get_by_code_returns_none_for_missing(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = WBSElementService(db)
    found = await service.get_by_code("9.9.9", project.project_id)
    assert found is None


# ---------------------------------------------------------------------------
# update_wbe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_wbe_changes_name(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    update_in = WBSElementUpdate(name="Updated WBS Name")
    updated = await service.update_wbe(wbs.wbs_element_id, update_in, actor_id)
    await db.commit()

    assert updated.name == "Updated WBS Name"
    assert updated.wbs_element_id == wbs.wbs_element_id


@pytest.mark.asyncio
async def test_update_wbe_reparenting_changes_level(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    child = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    update_in = WBSElementUpdate(parent_wbs_element_id=parent.wbs_element_id)
    updated = await service.update_wbe(child.wbs_element_id, update_in, actor_id)
    await db.commit()

    assert updated.level == 2
    assert updated.parent_wbs_element_id == parent.wbs_element_id


@pytest.mark.asyncio
async def test_update_wbe_nonexistent_raises(db: AsyncSession, actor_id) -> None:
    service = WBSElementService(db)
    update_in = WBSElementUpdate(name="Ghost")
    with pytest.raises(ValueError, match="WBS Element .* not found"):
        await service.update_wbe(uuid4(), update_in, actor_id)


# ---------------------------------------------------------------------------
# delete_wbe (soft delete with cascade)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_wbs_element_soft_deletes(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    deleted = await service.delete_wbe(wbs.wbs_element_id, actor_id)
    await db.commit()

    assert deleted.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_wbs_element_cascades_to_children(
    db: AsyncSession, actor_id
) -> None:
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.1",
        name="Child To Cascade",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    child = await service.create_wbe(child_in, actor_id)
    await db.commit()

    await service.delete_wbe(parent.wbs_element_id, actor_id)
    await db.commit()

    # Both parent and child should be soft-deleted
    parent_check = await service.get_as_of(parent.wbs_element_id)
    child_check = await service.get_as_of(child.wbs_element_id)
    assert parent_check is None
    assert child_check is None


@pytest.mark.asyncio
async def test_delete_wbs_element_nonexistent_raises(
    db: AsyncSession, actor_id
) -> None:
    service = WBSElementService(db)
    with pytest.raises(ValueError, match="WBS Element .* not found"):
        await service.delete_wbe(uuid4(), actor_id)


# ---------------------------------------------------------------------------
# get_children_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_children_count(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.1",
        name="Child 1",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await service.create_wbe(child_in, actor_id)
    await db.commit()

    count = await service.get_children_count(parent.wbs_element_id)
    assert count >= 1


# ---------------------------------------------------------------------------
# get_wbe_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbe_history_returns_versions(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    update_in = WBSElementUpdate(name="V2 Name")
    await service.update_wbe(wbs.wbs_element_id, update_in, actor_id)
    await db.commit()

    history = await service.get_wbe_history(wbs.wbs_element_id)
    assert len(history) >= 2


# ---------------------------------------------------------------------------
# budget allocation (computed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_budget_allocation_with_work_packages(
    db: AsyncSession, actor_id
) -> None:
    from tests.factories import (
        create_test_control_account,
        create_test_work_package,
    )

    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    await create_test_work_package(
        db, actor_id, ca.control_account_id, budget_amount=Decimal("100000")
    )
    await db.commit()

    service = WBSElementService(db)
    budget = await service.compute_budget_allocation(wbs.wbs_element_id)
    assert budget == Decimal("100000")
