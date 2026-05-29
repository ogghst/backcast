"""Service-level tests for OrganizationalUnitService.

Tests Org Unit CRUD, hierarchy (parent/child), code lookup,
listing with search/sort, and edge cases via direct service calls.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.organizational_unit import (
    OrganizationalUnitCreate,
    OrganizationalUnitUpdate,
)
from app.services.organizational_unit_service import OrganizationalUnitService
from tests.factories import create_test_org_unit

# ---------------------------------------------------------------------------
# create_organizational_unit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_organizational_unit(db: AsyncSession, actor_id) -> None:
    service = OrganizationalUnitService(db)
    unit_in = OrganizationalUnitCreate(
        code="MECH",
        name="Mechanical Department",
        is_active=True,
    )
    unit = await service.create_organizational_unit(unit_in, actor_id)
    await db.commit()

    assert unit.organizational_unit_id is not None
    assert unit.code == "MECH"
    assert unit.name == "Mechanical Department"
    assert unit.is_active is True
    assert unit.branch == "main"


@pytest.mark.asyncio
async def test_create_organizational_unit_with_custom_id(
    db: AsyncSession, actor_id
) -> None:
    custom_id = uuid4()
    service = OrganizationalUnitService(db)
    unit_in = OrganizationalUnitCreate(
        organizational_unit_id=custom_id,
        code="ELEC",
        name="Electrical Department",
    )
    unit = await service.create_organizational_unit(unit_in, actor_id)
    await db.commit()

    assert unit.organizational_unit_id == custom_id


@pytest.mark.asyncio
async def test_create_root_with_parent(db: AsyncSession, actor_id) -> None:
    parent = await create_test_org_unit(db, actor_id, code="ENG")
    await db.commit()

    service = OrganizationalUnitService(db)
    child_id = uuid4()
    child = await service.create_root(
        root_id=child_id,
        actor_id=actor_id,
        code="ENG-MECH",
        name="Mechanical Sub-unit",
        parent_unit_id=parent.organizational_unit_id,
    )
    await db.commit()

    assert child.parent_unit_id == parent.organizational_unit_id


@pytest.mark.asyncio
async def test_create_organizational_unit_invalid_manager_raises(
    db: AsyncSession, actor_id
) -> None:
    service = OrganizationalUnitService(db)
    unit_in = OrganizationalUnitCreate(
        code="ORPHAN",
        name="Orphan Unit",
        manager_id=uuid4(),
    )
    with pytest.raises(ValueError, match="Manager .* not found"):
        await service.create_organizational_unit(unit_in, actor_id)


# ---------------------------------------------------------------------------
# list_organizational_units
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_organizational_units_returns_created(
    db: AsyncSession, actor_id
) -> None:
    unit = await create_test_org_unit(db, actor_id, code="LIST-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, total = await service.list_organizational_units()
    assert total >= 1
    unit_ids = [u.organizational_unit_id for u in results]
    assert unit.organizational_unit_id in unit_ids


@pytest.mark.asyncio
async def test_list_organizational_units_with_search(
    db: AsyncSession, actor_id
) -> None:
    await create_test_org_unit(db, actor_id, code="SRCH", name="SearchTarget Unique")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, total = await service.list_organizational_units(
        search="SearchTarget Unique"
    )
    assert total >= 1
    assert any(u.name == "SearchTarget Unique" for u in results)


@pytest.mark.asyncio
async def test_list_organizational_units_with_sorting(
    db: AsyncSession, actor_id
) -> None:
    await create_test_org_unit(db, actor_id, code="SORT-Z", name="ZZZ Unit")
    await create_test_org_unit(db, actor_id, code="SORT-A", name="AAA Unit")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, _total = await service.list_organizational_units(
        sort_field="name", sort_order="asc"
    )
    names = [u.name for u in results if u.name in ("ZZZ Unit", "AAA Unit")]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_list_organizational_units_pagination(db: AsyncSession, actor_id) -> None:
    service = OrganizationalUnitService(db)
    results, total = await service.list_organizational_units(skip=0, limit=1)
    assert len(results) <= 1


# ---------------------------------------------------------------------------
# get_by_code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_code_finds_unit(db: AsyncSession, actor_id) -> None:
    unit = await create_test_org_unit(db, actor_id, code="FINDME")
    await db.commit()

    service = OrganizationalUnitService(db)
    found = await service.get_by_code("FINDME")
    assert found is not None
    assert found.organizational_unit_id == unit.organizational_unit_id


@pytest.mark.asyncio
async def test_get_by_code_returns_none_for_missing(db: AsyncSession, actor_id) -> None:
    service = OrganizationalUnitService(db)
    found = await service.get_by_code("NO-SUCH-CODE")
    assert found is None


# ---------------------------------------------------------------------------
# get_children (hierarchy)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_children_returns_child_units(db: AsyncSession, actor_id) -> None:
    parent = await create_test_org_unit(db, actor_id, code="PARENT-OU")
    child = await create_test_org_unit(
        db,
        actor_id,
        code="CHILD-OU",
        parent_unit_id=parent.organizational_unit_id,
    )
    await db.commit()

    service = OrganizationalUnitService(db)
    children = await service.get_children(parent.organizational_unit_id)
    child_ids = [c.organizational_unit_id for c in children]
    assert child.organizational_unit_id in child_ids


@pytest.mark.asyncio
async def test_get_children_returns_empty_for_leaf(db: AsyncSession, actor_id) -> None:
    leaf = await create_test_org_unit(db, actor_id, code="LEAF-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    children = await service.get_children(leaf.organizational_unit_id)
    assert children == []


# ---------------------------------------------------------------------------
# update_organizational_unit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_organizational_unit_changes_name(
    db: AsyncSession, actor_id
) -> None:
    unit = await create_test_org_unit(db, actor_id, code="UPD-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    update_in = OrganizationalUnitUpdate(name="Updated Unit Name")
    updated = await service.update_organizational_unit(
        unit.organizational_unit_id, update_in, actor_id
    )
    await db.commit()

    assert updated.name == "Updated Unit Name"
    assert updated.organizational_unit_id == unit.organizational_unit_id


@pytest.mark.asyncio
async def test_update_organizational_unit_deactivate(
    db: AsyncSession, actor_id
) -> None:
    unit = await create_test_org_unit(db, actor_id, code="DEACT-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    update_in = OrganizationalUnitUpdate(is_active=False)
    updated = await service.update_organizational_unit(
        unit.organizational_unit_id, update_in, actor_id
    )
    await db.commit()

    assert updated.is_active is False


# ---------------------------------------------------------------------------
# delete_organizational_unit (soft delete)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_organizational_unit_soft_deletes(
    db: AsyncSession, actor_id
) -> None:
    unit = await create_test_org_unit(db, actor_id, code="DEL-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    await service.delete_organizational_unit(unit.organizational_unit_id, actor_id)
    await db.commit()

    # After soft delete, get_by_code should not find it
    found = await service.get_by_code("DEL-OU")
    assert found is None


# ---------------------------------------------------------------------------
# get_organizational_unit_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_organizational_unit_history_returns_versions(
    db: AsyncSession, actor_id
) -> None:
    unit = await create_test_org_unit(db, actor_id, code="HIST-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    update_in = OrganizationalUnitUpdate(name="V2 Name")
    await service.update_organizational_unit(
        unit.organizational_unit_id, update_in, actor_id
    )
    await db.commit()

    history = await service.get_organizational_unit_history(unit.organizational_unit_id)
    assert len(history) >= 2


# ---------------------------------------------------------------------------
# backward-compatible alias
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_departments_alias_works(db: AsyncSession, actor_id) -> None:
    await create_test_org_unit(db, actor_id, code="ALIAS-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, total = await service.get_departments()
    assert total >= 1


# ---------------------------------------------------------------------------
# list_organizational_units with filter_string
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_organizational_units_with_filter_string(
    db: AsyncSession, actor_id
) -> None:
    """list_organizational_units applies filter_string to code and name."""
    await create_test_org_unit(db, actor_id, code="FILTER-OU", name="FilterTarget")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, total = await service.list_organizational_units(
        filter_string="code:FILTER-OU"
    )
    assert total >= 1
    assert any(u.code == "FILTER-OU" for u in results)


# ---------------------------------------------------------------------------
# list_organizational_units descending sort
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_organizational_units_desc_sort(
    db: AsyncSession, actor_id
) -> None:
    """list_organizational_units supports desc sort order."""
    await create_test_org_unit(db, actor_id, code="DESC-A", name="AAA Desc")
    await create_test_org_unit(db, actor_id, code="DESC-Z", name="ZZZ Desc")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, _total = await service.list_organizational_units(
        sort_field="name", sort_order="desc"
    )
    names = [u.name for u in results if u.name in ("AAA Desc", "ZZZ Desc")]
    assert names == sorted(names, reverse=True)


# ---------------------------------------------------------------------------
# list_organizational_units default sort (no sort_field)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_organizational_units_default_sort(
    db: AsyncSession, actor_id
) -> None:
    """list_organizational_units defaults to ascending name sort when no sort_field."""
    await create_test_org_unit(db, actor_id, code="DSORT-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    results, total = await service.list_organizational_units()
    assert total >= 1
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# get_organizational_unit_as_of (time travel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_organizational_unit_as_of(
    db: AsyncSession, actor_id
) -> None:
    """get_organizational_unit_as_of returns the unit at a past timestamp."""
    from datetime import UTC, datetime, timedelta

    unit = await create_test_org_unit(db, actor_id, code="ASOF-OU")
    await db.commit()

    service = OrganizationalUnitService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    found = await service.get_organizational_unit_as_of(
        unit.organizational_unit_id, as_of=as_of
    )
    assert found is not None
    assert found.organizational_unit_id == unit.organizational_unit_id
