"""Service-level tests for ProjectService.

Tests Project CRUD operations, budget computation, listing with filters,
and edge cases -- all via direct service calls without HTTP layer.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project import ProjectService
from tests.factories import (
    create_full_hierarchy,
    create_test_project,
)

# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_project_returns_entity_with_fields(
    db: AsyncSession, actor_id
) -> None:
    service = ProjectService(db)
    project_in = ProjectCreate(
        name="Service Test Project",
        code="SVC-001",
        contract_value=Decimal("500000"),
        currency="EUR",
    )
    project = await service.create_project(project_in, actor_id)
    await db.commit()

    assert project.project_id is not None
    assert project.name == "Service Test Project"
    assert project.code == "SVC-001"
    assert project.contract_value == Decimal("500000")
    assert project.currency == "EUR"
    assert project.branch == "main"
    assert project.budget == Decimal("0")


@pytest.mark.asyncio
async def test_create_project_with_custom_project_id(
    db: AsyncSession, actor_id
) -> None:
    service = ProjectService(db)
    custom_id = uuid4()
    project_in = ProjectCreate(
        name="Custom ID Project",
        code="SVC-CUSTOM",
        project_id=custom_id,
    )
    project = await service.create_project(project_in, actor_id)
    await db.commit()

    assert project.project_id == custom_id


# ---------------------------------------------------------------------------
# get_projects (list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_projects_returns_created_project(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id, code="LIST-001")
    await db.commit()

    service = ProjectService(db)
    results, total = await service.get_projects()
    assert total >= 1
    project_ids = [p.project_id for p in results]
    assert project.project_id in project_ids


@pytest.mark.asyncio
async def test_get_projects_with_search_filter(db: AsyncSession, actor_id) -> None:
    await create_test_project(db, actor_id, name="Alpha Unique", code="SEARCH-A")
    await create_test_project(db, actor_id, name="Beta Unique", code="SEARCH-B")
    await db.commit()

    service = ProjectService(db)
    results, total = await service.get_projects(search="Alpha Unique")
    assert total >= 1
    assert any(p.name == "Alpha Unique" for p in results)


@pytest.mark.asyncio
async def test_get_projects_with_sorting(db: AsyncSession, actor_id) -> None:
    await create_test_project(db, actor_id, name="ZZZ Last", code="SORT-Z")
    await create_test_project(db, actor_id, name="AAA First", code="SORT-A")
    await db.commit()

    service = ProjectService(db)
    results, _total = await service.get_projects(sort_field="name", sort_order="asc")
    names = [p.name for p in results if p.name in ("ZZZ Last", "AAA First")]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_get_projects_invalid_sort_field_raises(
    db: AsyncSession, actor_id
) -> None:
    service = ProjectService(db)
    with pytest.raises(ValueError, match="Invalid sort field"):
        await service.get_projects(sort_field="nonexistent_column")


@pytest.mark.asyncio
async def test_get_projects_pagination(db: AsyncSession, actor_id) -> None:
    service = ProjectService(db)
    results, total = await service.get_projects(skip=0, limit=1)
    assert len(results) <= 1


# ---------------------------------------------------------------------------
# get_by_code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_code_finds_project(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id, code="FIND-ME")
    await db.commit()

    service = ProjectService(db)
    found = await service.get_by_code("FIND-ME")
    assert found is not None
    assert found.project_id == project.project_id


@pytest.mark.asyncio
async def test_get_by_code_returns_none_for_missing(db: AsyncSession, actor_id) -> None:
    service = ProjectService(db)
    found = await service.get_by_code("DOES-NOT-EXIST")
    assert found is None


# ---------------------------------------------------------------------------
# update_project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_project_changes_name(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id, name="Original")
    await db.commit()

    service = ProjectService(db)
    update_in = ProjectUpdate(name="Updated Name")
    updated = await service.update_project(project.project_id, update_in, actor_id)
    await db.commit()

    assert updated.name == "Updated Name"
    assert updated.project_id == project.project_id


@pytest.mark.asyncio
async def test_update_project_contract_value(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectService(db)
    update_in = ProjectUpdate(contract_value=Decimal("750000"))
    updated = await service.update_project(project.project_id, update_in, actor_id)
    await db.commit()

    assert updated.contract_value == Decimal("750000")


# ---------------------------------------------------------------------------
# delete_project (soft delete)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_project_soft_deletes(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id, code="DEL-ME")
    await db.commit()

    service = ProjectService(db)
    deleted = await service.delete_project(project.project_id, actor_id)
    await db.commit()

    assert deleted.deleted_at is not None
    # After deletion, get_by_code should not find it on main
    found = await service.get_by_code("DEL-ME")
    assert found is None


# ---------------------------------------------------------------------------
# get_project_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_history_returns_versions(db: AsyncSession, actor_id) -> None:
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectService(db)
    update_in = ProjectUpdate(name="V2 Name")
    await service.update_project(project.project_id, update_in, actor_id)
    await db.commit()

    history = await service.get_project_history(project.project_id)
    assert len(history) >= 2


# ---------------------------------------------------------------------------
# budget computation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_budget_computed_from_work_packages(
    db: AsyncSession, actor_id
) -> None:
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = ProjectService(db)
    project = await service.get_as_of(hierarchy["project"].project_id)
    assert project is not None
    # create_full_hierarchy creates a work package with default budget_amount=50000
    assert project.budget == Decimal("50000")


@pytest.mark.asyncio
async def test_project_budget_zero_for_empty_project(
    db: AsyncSession, actor_id
) -> None:
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectService(db)
    fetched = await service.get_as_of(project.project_id)
    assert fetched is not None
    assert fetched.budget == Decimal("0")


@pytest.mark.asyncio
async def test_get_recently_updated_returns_projects(
    db: AsyncSession, actor_id
) -> None:
    await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectService(db)
    recent = await service.get_recently_updated(limit=5)
    assert len(recent) >= 1
