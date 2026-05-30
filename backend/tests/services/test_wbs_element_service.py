"""Service-level tests for WBSElementService.

Tests WBS Element CRUD, hierarchy (parent/child), budget computation,
listing with filters, and edge cases via direct service calls.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.wbs_element import WBSElement
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


# ---------------------------------------------------------------------------
# create_wbe with revenue allocation validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_wbe_revenue_allocation_exceeds_contract_raises(
    db: AsyncSession, actor_id
) -> None:
    """create_wbe raises ValueError when revenue allocation exceeds contract value."""
    from decimal import Decimal

    project = await create_test_project(db, actor_id, contract_value=Decimal("100000"))
    await db.commit()

    service = WBSElementService(db)
    wbe_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.0",
        name="Over-allocated WBS",
        revenue_allocation=Decimal("200000"),
    )
    with pytest.raises(ValueError, match="revenue allocation.*exceeds"):
        await service.create_wbe(wbe_in, actor_id)


# ---------------------------------------------------------------------------
# update_wbe with parent change to root (null parent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_wbe_reparenting_to_root_changes_level(
    db: AsyncSession, actor_id
) -> None:
    """update_wbe sets level=1 when parent_wbs_element_id is set to None."""
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    child = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        level=2,
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await db.commit()

    service = WBSElementService(db)
    update_in = WBSElementUpdate(parent_wbs_element_id=None)
    updated = await service.update_wbe(child.wbs_element_id, update_in, actor_id)
    await db.commit()

    assert updated.level == 1
    assert updated.parent_wbs_element_id is None


# ---------------------------------------------------------------------------
# update_wbe with new parent that is invalid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_wbe_invalid_new_parent_raises(db: AsyncSession, actor_id) -> None:
    """update_wbe raises ValueError when reparenting to a non-existent parent."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    update_in = WBSElementUpdate(parent_wbs_element_id=uuid4())
    with pytest.raises(ValueError, match="Parent WBS Element .* not found"):
        await service.update_wbe(wbs.wbs_element_id, update_in, actor_id)


# ---------------------------------------------------------------------------
# get_wbs_elements with filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_elements_with_filters(db: AsyncSession, actor_id) -> None:
    """get_wbs_elements applies filter_string to allowed fields."""
    project = await create_test_project(db, actor_id)
    await create_test_wbs_element(
        db, actor_id, project.project_id, code="FILT.0", name="Filter WBS"
    )
    await db.commit()

    service = WBSElementService(db)
    results, total = await service.get_wbs_elements(
        project_id=project.project_id, filters="code:FILT.0"
    )
    assert total >= 1
    assert any(w.code == "FILT.0" for w in results)


# ---------------------------------------------------------------------------
# get_wbs_elements with parent_id filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_elements_with_parent_filter(db: AsyncSession, actor_id) -> None:
    """get_wbs_elements filters by parent_id when apply_parent_filter=True."""
    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.1",
        name="Child For Filter",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await service.create_wbe(child_in, actor_id)
    await db.commit()

    results, total = await service.get_wbs_elements(
        project_id=project.project_id,
        parent_id=parent.wbs_element_id,
        apply_parent_filter=True,
    )
    assert total >= 1
    assert all(w.parent_wbs_element_id == parent.wbs_element_id for w in results)


# ---------------------------------------------------------------------------
# get_wbs_elements with as_of time travel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_elements_with_as_of(db: AsyncSession, actor_id) -> None:
    """get_wbs_elements supports time-travel via as_of parameter."""
    from datetime import UTC, datetime, timedelta

    project = await create_test_project(db, actor_id)
    await create_test_wbs_element(db, actor_id, project.project_id, code="ASOF.0")
    await db.commit()

    service = WBSElementService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    results, total = await service.get_wbs_elements(
        project_id=project.project_id, as_of=as_of
    )
    assert total >= 1


# ---------------------------------------------------------------------------
# get_wbe_as_of (time travel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbe_as_of(db: AsyncSession, actor_id) -> None:
    """get_wbe_as_of returns element at a specific timestamp."""
    from datetime import UTC, datetime, timedelta

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    found = await service.get_wbe_as_of(wbs.wbs_element_id, as_of=as_of)
    assert found is not None
    assert found.wbs_element_id == wbs.wbs_element_id


# ---------------------------------------------------------------------------
# get_by_parent with as_of time travel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_parent_with_as_of(db: AsyncSession, actor_id) -> None:
    """get_by_parent supports time-travel via as_of parameter."""
    from datetime import UTC, datetime, timedelta

    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(db, actor_id, project.project_id, level=1)
    await db.commit()

    service = WBSElementService(db)
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="1.1",
        name="AsOf Child",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await service.create_wbe(child_in, actor_id)
    await db.commit()

    as_of = datetime.now(UTC) + timedelta(hours=1)
    children = await service.get_by_parent(
        project_id=project.project_id,
        parent_wbe_id=parent.wbs_element_id,
        as_of=as_of,
    )
    assert len(children) >= 1


# ---------------------------------------------------------------------------
# get_breadcrumb
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_breadcrumb(db: AsyncSession, actor_id) -> None:
    """get_breadcrumb returns project and WBS path."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    bc = await service.get_breadcrumb(wbs.wbs_element_id)

    assert "project" in bc
    assert "wbe_path" in bc
    assert bc["project"]["project_id"] == project.project_id
    assert len(bc["wbe_path"]) >= 1
    assert bc["wbe_path"][0]["wbs_element_id"] == wbs.wbs_element_id


@pytest.mark.asyncio
async def test_get_breadcrumb_not_found_raises(db: AsyncSession, actor_id) -> None:
    """get_breadcrumb raises ValueError for unknown WBS Element."""
    service = WBSElementService(db)
    with pytest.raises(ValueError, match="WBS Element .* not found"):
        await service.get_breadcrumb(uuid4())


# ---------------------------------------------------------------------------
# get_wbes backward-compatible alias
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbes_alias(db: AsyncSession, actor_id) -> None:
    """get_wbes delegates to get_wbs_elements."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    results, total = await service.get_wbes(project_id=project.project_id)
    assert total >= 1
    assert any(w.wbs_element_id == wbs.wbs_element_id for w in results)


# ---------------------------------------------------------------------------
# delete_wbe nonexistent raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_wbe_nonexistent_raises(db: AsyncSession, actor_id) -> None:
    """delete_wbe raises ValueError for unknown WBS Element."""
    service = WBSElementService(db)
    with pytest.raises(ValueError, match="WBS Element .* not found"):
        await service.delete_wbe(uuid4(), actor_id)


# ---------------------------------------------------------------------------
# get_children_count with no children
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_children_count_zero(db: AsyncSession, actor_id) -> None:
    """get_children_count returns 0 for leaf WBS Element."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    count = await service.get_children_count(wbs.wbs_element_id)
    assert count == 0


# ---------------------------------------------------------------------------
# _validate_revenue_allocation with no contract value (line 73)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_revenue_allocation_no_contract_value(
    db: AsyncSession, actor_id
) -> None:
    """_validate_revenue_allocation returns early when project has no contract_value."""

    project = await create_test_project(db, actor_id, contract_value=None)
    await db.commit()

    service = WBSElementService(db)
    # Should not raise -- contract_value is None, validation is skipped
    await service._validate_revenue_allocation(
        project_id=project.project_id,
        branch="main",
    )


# ---------------------------------------------------------------------------
# _validate_revenue_allocation with exclude_wbs_id (line 84)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_revenue_allocation_excludes_wbs_id(
    db: AsyncSession, actor_id
) -> None:
    """_validate_revenue_allocation excludes specified WBS from sum."""
    from decimal import Decimal

    project = await create_test_project(db, actor_id, contract_value=Decimal("100000"))
    wbs = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        revenue_allocation=Decimal("80000"),
    )
    await db.commit()

    service = WBSElementService(db)
    # If we exclude the only WBS, total allocated is 0, so no error
    await service._validate_revenue_allocation(
        project_id=project.project_id,
        branch="main",
        exclude_wbs_id=wbs.wbs_element_id,
    )


# ---------------------------------------------------------------------------
# create_root (lines 222-232)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_root_creates_initial_version(db: AsyncSession, actor_id) -> None:
    """create_root creates the initial WBS Element version."""
    from uuid import uuid4

    project = await create_test_project(db, actor_id)
    await db.commit()

    root_id = uuid4()
    service = WBSElementService(db)
    element = await service.create_root(
        root_id=root_id,
        actor_id=actor_id,
        project_id=project.project_id,
        code="R.0",
        name="Root Created Element",
        level=1,
    )
    await db.commit()

    assert element.wbs_element_id == root_id
    assert element.code == "R.0"
    assert element.name == "Root Created Element"
    assert element.level == 1


# ---------------------------------------------------------------------------
# _resolve_parent_names edge cases (lines 246-251)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_parent_names_with_plain_items(
    db: AsyncSession, actor_id
) -> None:
    """_resolve_parent_names handles non-tuple items (plain scalars)."""
    service = WBSElementService(db)

    # Simulate a result that is a plain string (not iterable in the tuple sense)
    result = await service._resolve_parent_names(["plain_string"])
    assert result == ["plain_string"]


@pytest.mark.asyncio
async def test_resolve_parent_names_single_element_tuple(
    db: AsyncSession, actor_id
) -> None:
    """_resolve_parent_names handles tuples with exactly one element (line 246-247)."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)

    # Simulate a result list with a single-element tuple (no parent_name)
    result = await service._resolve_parent_names([(wbs,)])
    assert len(result) == 1
    assert result[0].wbs_element_id == wbs.wbs_element_id


@pytest.mark.asyncio
async def test_resolve_parent_names_empty_tuple(db: AsyncSession, actor_id) -> None:
    """_resolve_parent_names handles empty tuples (line 248-249)."""
    service = WBSElementService(db)

    # Simulate an empty tuple result
    result = await service._resolve_parent_names([()])
    assert len(result) == 1
    assert result[0] == ()


# ---------------------------------------------------------------------------
# _get_descendants_merged (lines 744-791) - MERGED mode on non-main branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_descendants_isolated_on_branch(db: AsyncSession, actor_id) -> None:
    """_get_all_descendants with ISOLATED mode on branch returns descendants."""
    from app.core.branching.commands import CreateBranchCommand
    from app.core.versioning.enums import BranchMode

    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(
        db, actor_id, project.project_id, level=1, code="P.0", name="Parent WBS"
    )
    child = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        level=2,
        code="P.1",
        name="Child WBS",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await db.commit()

    branch_name = "BR-CO-TEST-001"

    # Branch both parent and child to a non-main branch
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=parent.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()

    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=child.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    # Use ISOLATED mode -- this exercises _get_descendants_isolated on branch
    descendants = await service._get_all_descendants(
        parent_wbe_id=parent.wbs_element_id,
        branch=branch_name,
        branch_mode=BranchMode.ISOLATED,
    )

    # Should find the child descendant on the branch
    descendant_ids = [d.wbs_element_id for d in descendants]
    assert child.wbs_element_id in descendant_ids


# ---------------------------------------------------------------------------
# get_breadcrumb with MERGED mode and non-main branch (lines 870-887)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_breadcrumb_merged_mode_on_branch(db: AsyncSession, actor_id) -> None:
    """get_breadcrumb with MERGED mode resolves project from main branch."""
    from app.core.branching.commands import CreateBranchCommand
    from app.core.versioning.enums import BranchMode

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(
        db, actor_id, project.project_id, code="BC.0", name="Breadcrumb WBS"
    )
    await db.commit()

    branch_name = "BR-BC-TEST-001"
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=wbs.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    bc = await service.get_breadcrumb(
        wbs.wbs_element_id,
        branch=branch_name,
        branch_mode=BranchMode.MERGED,
    )

    assert "project" in bc
    assert "wbe_path" in bc
    assert bc["project"]["project_id"] == project.project_id
    assert len(bc["wbe_path"]) >= 1


# ---------------------------------------------------------------------------
# get_breadcrumb with as_of time travel (lines 834, 894-895)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_breadcrumb_with_as_of(db: AsyncSession, actor_id) -> None:
    """get_breadcrumb supports as_of time-travel query."""
    from datetime import UTC, datetime, timedelta

    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(
        db, actor_id, project.project_id, code="BT.0", name="Breadcrumb Parent"
    )
    child = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        code="BT.1",
        name="Breadcrumb Child",
        level=2,
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await db.commit()

    service = WBSElementService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    bc = await service.get_breadcrumb(child.wbs_element_id, as_of=as_of)

    assert "project" in bc
    assert "wbe_path" in bc
    # Should have at least 2 items: parent and child
    assert len(bc["wbe_path"]) >= 2


# ---------------------------------------------------------------------------
# get_breadcrumb with MERGED mode and as_of time travel (lines 870-895)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_breadcrumb_merged_with_as_of(db: AsyncSession, actor_id) -> None:
    """get_breadcrumb with MERGED mode and as_of resolves project from main."""
    from datetime import UTC, datetime, timedelta

    from app.core.branching.commands import CreateBranchCommand
    from app.core.versioning.enums import BranchMode

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(
        db, actor_id, project.project_id, code="BM.0", name="Merged BC WBS"
    )
    await db.commit()

    branch_name = "BR-BM-TEST-001"
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=wbs.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    bc = await service.get_breadcrumb(
        wbs.wbs_element_id,
        branch=branch_name,
        branch_mode=BranchMode.MERGED,
        as_of=as_of,
    )

    assert "project" in bc
    assert bc["project"]["project_id"] == project.project_id


# ---------------------------------------------------------------------------
# get_wbs_elements with desc sort order (line 373)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_elements_desc_sort(db: AsyncSession, actor_id) -> None:
    """get_wbs_elements supports desc sort order."""
    project = await create_test_project(db, actor_id)
    await create_test_wbs_element(
        db, actor_id, project.project_id, name="ZZZ Desc WBS", code="ZD.0"
    )
    await create_test_wbs_element(
        db, actor_id, project.project_id, name="AAA Desc WBS", code="AD.0"
    )
    await db.commit()

    service = WBSElementService(db)
    results, _total = await service.get_wbs_elements(
        project_id=project.project_id, sort_field="name", sort_order="desc"
    )
    names = [w.name for w in results if w.name in ("ZZZ Desc WBS", "AAA Desc WBS")]
    assert names == sorted(names, reverse=True)


# ---------------------------------------------------------------------------
# create_wbe with parent on non-main branch falling back to main (line 548)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_wbe_parent_fallback_to_main(db: AsyncSession, actor_id) -> None:
    """create_wbe falls back to main branch when parent not on current branch."""

    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(
        db, actor_id, project.project_id, level=1, code="PF.0", name="Fallback Parent"
    )
    await db.commit()

    # Create child on a branch -- parent exists only on main, so it falls back
    branch_name = "BR-PF-TEST-001"
    child_in = WBSElementCreate(
        project_id=project.project_id,
        code="PF.1",
        name="Branch Child",
        parent_wbs_element_id=parent.wbs_element_id,
        branch=branch_name,
    )

    service = WBSElementService(db)
    # Parent does not exist on branch, so it should fall back to main
    child = await service.create_wbe(child_in, actor_id)
    await db.commit()

    assert child.level == 2
    assert child.parent_wbs_element_id == parent.wbs_element_id
    assert child.branch == branch_name


# ---------------------------------------------------------------------------
# update_wbe on non-main branch falling back to main (lines 605-617)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_wbe_fallback_to_main_for_current(
    db: AsyncSession, actor_id
) -> None:
    """update_wbe falls back to main when element not found on specified branch."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(
        db, actor_id, project.project_id, code="UF.0", name="Update Fallback"
    )
    await db.commit()

    service = WBSElementService(db)
    # Update specifying a non-main branch where the element doesn't exist
    # -- should fall back to finding it on main
    update_in = WBSElementUpdate(
        name="Updated via fallback",
        branch="BR-UF-TEST-001",
    )
    updated = await service.update_wbe(wbs.wbs_element_id, update_in, actor_id)
    await db.commit()

    assert updated.name == "Updated via fallback"


@pytest.mark.asyncio
async def test_update_wbe_reparenting_fallback_to_main(
    db: AsyncSession, actor_id
) -> None:
    """update_wbe falls back to main when new parent not found on branch."""
    from app.core.branching.commands import CreateBranchCommand

    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(
        db, actor_id, project.project_id, level=1, code="RP.0", name="Reparent Parent"
    )
    child = await create_test_wbs_element(
        db, actor_id, project.project_id, level=1, code="RP.1", name="Reparent Child"
    )
    await db.commit()

    # Branch the child to a non-main branch
    branch_name = "BR-RP-TEST-001"
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=child.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    # Update child on branch, reparenting to parent that only exists on main
    update_in = WBSElementUpdate(
        parent_wbs_element_id=parent.wbs_element_id,
        branch=branch_name,
    )
    updated = await service.update_wbe(child.wbs_element_id, update_in, actor_id)
    await db.commit()

    assert updated.level == 2
    assert updated.parent_wbs_element_id == parent.wbs_element_id


# ---------------------------------------------------------------------------
# get_breadcrumb with MERGED mode and ancestor resolution (lines 900-915)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_breadcrumb_merged_ancestor_from_main(
    db: AsyncSession, actor_id
) -> None:
    """get_breadcrumb MERGED mode resolves ancestors from both branch and main."""
    from app.core.branching.commands import CreateBranchCommand
    from app.core.versioning.enums import BranchMode

    project = await create_test_project(db, actor_id)
    grandparent = await create_test_wbs_element(
        db, actor_id, project.project_id, code="MG.0", name="GP WBS", level=1
    )
    parent = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        code="MG.1",
        name="P WBS",
        level=2,
        parent_wbs_element_id=grandparent.wbs_element_id,
    )
    child = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        code="MG.2",
        name="C WBS",
        level=3,
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await db.commit()

    # Branch only the child -- ancestors remain on main
    branch_name = "BR-MG-TEST-001"
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=child.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    bc = await service.get_breadcrumb(
        child.wbs_element_id,
        branch=branch_name,
        branch_mode=BranchMode.MERGED,
    )

    # Should resolve all ancestors via MERGED fallback to main
    assert "wbe_path" in bc
    assert len(bc["wbe_path"]) >= 3
    path_ids = [p["wbs_element_id"] for p in bc["wbe_path"]]
    assert grandparent.wbs_element_id in path_ids
    assert parent.wbs_element_id in path_ids
    assert child.wbs_element_id in path_ids


# ---------------------------------------------------------------------------
# get_by_parent with MERGED mode on non-main branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_parent_merged_mode(db: AsyncSession, actor_id) -> None:
    """get_by_parent with MERGED mode returns children from branch and main."""
    from app.core.branching.commands import CreateBranchCommand
    from app.core.versioning.enums import BranchMode

    project = await create_test_project(db, actor_id)
    parent = await create_test_wbs_element(
        db, actor_id, project.project_id, level=1, code="MP.0", name="Merged Parent"
    )
    child_main = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        level=2,
        code="MP.1",
        name="Child on Main",
        parent_wbs_element_id=parent.wbs_element_id,
    )
    await db.commit()

    branch_name = "BR-MP-TEST-001"

    # Branch the parent to create a non-main branch version
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=parent.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    children = await service.get_by_parent(
        project_id=project.project_id,
        parent_wbe_id=parent.wbs_element_id,
        branch=branch_name,
        branch_mode=BranchMode.MERGED,
    )

    # Should find child from main via MERGED mode
    child_ids = [c.wbs_element_id for c in children]
    assert child_main.wbs_element_id in child_ids


# ---------------------------------------------------------------------------
# get_wbs_elements with MERGED mode on non-main branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_elements_merged_mode(db: AsyncSession, actor_id) -> None:
    """get_wbs_elements with MERGED mode merges branch and main results."""
    from app.core.branching.commands import CreateBranchCommand
    from app.core.versioning.enums import BranchMode

    project = await create_test_project(db, actor_id)
    wbs_main = await create_test_wbs_element(
        db, actor_id, project.project_id, code="ME.0", name="Main Only WBS"
    )
    await db.commit()

    branch_name = "BR-ME-TEST-001"

    # Branch the WBS element to a non-main branch
    await CreateBranchCommand(
        entity_class=WBSElement,
        root_id=wbs_main.wbs_element_id,
        actor_id=actor_id,
        new_branch=branch_name,
        from_branch="main",
    ).execute(db)
    await db.flush()
    await db.commit()

    service = WBSElementService(db)
    results, total = await service.get_wbs_elements(
        project_id=project.project_id,
        branch=branch_name,
        branch_mode=BranchMode.MERGED,
    )

    # Should find at least one result (the branched version, or main fallback)
    assert total >= 1
    ids = [r.wbs_element_id for r in results]
    assert wbs_main.wbs_element_id in ids
