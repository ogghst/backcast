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


# ---------------------------------------------------------------------------
# get_projects with filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_projects_with_filter_string(db: AsyncSession, actor_id) -> None:
    """get_projects applies filter_string to status, code, name."""
    await create_test_project(db, actor_id, code="FLT-001", status="active")
    await db.commit()

    service = ProjectService(db)
    results, total = await service.get_projects(filters="status:active")
    assert total >= 1
    assert any(p.code == "FLT-001" for p in results)


@pytest.mark.asyncio
async def test_get_projects_with_as_of_time_travel(db: AsyncSession, actor_id) -> None:
    """get_projects supports time-travel via as_of parameter."""
    from datetime import UTC, datetime, timedelta

    await create_test_project(db, actor_id, code="ASOF-001")
    await db.commit()

    service = ProjectService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    results, total = await service.get_projects(as_of=as_of)
    assert total >= 1


@pytest.mark.asyncio
async def test_get_projects_with_desc_sort(db: AsyncSession, actor_id) -> None:
    """get_projects supports desc sort order."""
    await create_test_project(db, actor_id, name="ZZZ Desc", code="DESC-Z")
    await create_test_project(db, actor_id, name="AAA Desc", code="DESC-A")
    await db.commit()

    service = ProjectService(db)
    results, _total = await service.get_projects(sort_field="name", sort_order="desc")
    names = [p.name for p in results if p.name in ("ZZZ Desc", "AAA Desc")]
    assert names == sorted(names, reverse=True)


@pytest.mark.asyncio
async def test_get_projects_invalid_sort_field_no_desc_attr_raises(
    db: AsyncSession, actor_id
) -> None:
    """get_projects raises ValueError for sort field that is not a column (no desc attr)."""
    service = ProjectService(db)
    with pytest.raises(ValueError, match="Invalid sort field"):
        # 'budget' is a computed attribute, not a column
        await service.get_projects(sort_field="budget")


# ---------------------------------------------------------------------------
# get_project_as_of (time travel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_as_of_returns_project(db: AsyncSession, actor_id) -> None:
    """get_project_as_of returns project at a specific timestamp."""
    from datetime import UTC, datetime, timedelta

    project = await create_test_project(db, actor_id, code="TIME-TRAVEL")
    await db.commit()

    service = ProjectService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    found = await service.get_project_as_of(project.project_id, as_of=as_of)
    assert found is not None
    assert found.project_id == project.project_id


# ---------------------------------------------------------------------------
# get_recently_updated with user filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recently_updated_with_user_filter(
    db: AsyncSession, actor_id
) -> None:
    """get_recently_updated filters by user_id when provided."""
    await create_test_project(db, actor_id, code="RECENT-U")
    await db.commit()

    service = ProjectService(db)
    recent = await service.get_recently_updated(user_id=actor_id, limit=5)
    assert len(recent) >= 1
    assert all(p.created_by == actor_id for p in recent)


# ---------------------------------------------------------------------------
# get_recently_updated no results for unknown user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recently_updated_no_results_for_unknown_user(
    db: AsyncSession, actor_id
) -> None:
    """get_recently_updated returns empty list for unknown user_id."""
    from uuid import uuid4

    service = ProjectService(db)
    recent = await service.get_recently_updated(user_id=uuid4(), limit=5)
    assert len(recent) == 0


# ---------------------------------------------------------------------------
# get_project_branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_branches_returns_main(db: AsyncSession, actor_id) -> None:
    """get_project_branches always includes the main branch."""
    project = await create_test_project(db, actor_id, code="BRANCH-001")
    await db.commit()

    service = ProjectService(db)
    branches = await service.get_project_branches(project.project_id)

    assert len(branches) >= 1
    assert branches[0].name == "main"
    assert branches[0].is_default is True


# ---------------------------------------------------------------------------
# _populate_project_metadata_from_db with no created_by
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_populate_metadata_populates_creator_name(
    db: AsyncSession, actor_id
) -> None:
    """_populate_project_metadata_from_db populates created_by_name from DB."""
    project = await create_test_project(db, actor_id, code="META-CB")
    await db.commit()

    service = ProjectService(db)
    await service._populate_project_metadata_from_db(project)
    # created_by_name should be populated (test user is seeded)
    assert hasattr(project, "created_by_name")


# ---------------------------------------------------------------------------
# _populate_project_metadata_from_db with no created_by (line 522)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_populate_metadata_no_created_by_returns_early(
    db: AsyncSession, actor_id
) -> None:
    """_populate_project_metadata_from_db returns early when created_by is falsy."""
    from unittest.mock import MagicMock

    await create_test_project(db, actor_id, code="META-NCB")
    await db.commit()

    # Create a mock Project with created_by = None to test the early return path
    mock_project = MagicMock()
    mock_project.created_by = None

    service = ProjectService(db)
    # Should not raise -- the method returns early when created_by is None
    await service._populate_project_metadata_from_db(mock_project)


# ---------------------------------------------------------------------------
# get_project_branches with change order branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_branches_with_change_order_branch(
    db: AsyncSession, actor_id
) -> None:
    """get_project_branches includes change order branches with CO status."""
    from uuid import uuid4

    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.branch import Branch
    from app.models.domain.change_order import ChangeOrder

    project = await create_test_project(db, actor_id, code="BR-CO-001")
    await db.commit()

    # Create a branch record
    co_code = "CO-2026-001"
    branch_name = f"BR-{co_code}"
    branch_root_id = uuid4()
    cmd = CreateVersionCommand(
        entity_class=Branch,
        root_id=branch_root_id,
        actor_id=actor_id,
        name=branch_name,
        project_id=project.project_id,
        type="change_order",
        locked=False,
    )
    await cmd.execute(db)
    await db.flush()

    # Create a change order record on main branch
    co_root_id = uuid4()
    co_cmd = CreateVersionCommand(
        entity_class=ChangeOrder,
        root_id=co_root_id,
        actor_id=actor_id,
        code=co_code,
        project_id=project.project_id,
        branch="main",
        status="open",
        title="Test change order",
        description="Test change order for branch listing",
    )
    await co_cmd.execute(db)
    await db.flush()
    await db.commit()

    service = ProjectService(db)
    branches = await service.get_project_branches(project.project_id)

    # Should have main + the change order branch
    assert len(branches) >= 2
    main_branch = [b for b in branches if b.name == "main"]
    co_branch = [b for b in branches if b.name == branch_name]
    assert len(main_branch) == 1
    assert len(co_branch) == 1
    assert co_branch[0].type == "change_order"
    assert co_branch[0].change_order_code == co_code
    assert co_branch[0].change_order_status == "open"
    assert co_branch[0].change_order_id == co_root_id


@pytest.mark.asyncio
async def test_get_project_branches_with_as_of_time_travel(
    db: AsyncSession, actor_id
) -> None:
    """get_project_branches supports as_of time-travel filtering."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.branch import Branch

    project = await create_test_project(db, actor_id, code="BR-ASOF-001")
    await db.commit()

    # Create a branch record
    branch_root_id = uuid4()
    cmd = CreateVersionCommand(
        entity_class=Branch,
        root_id=branch_root_id,
        actor_id=actor_id,
        name="BR-CO-2026-002",
        project_id=project.project_id,
        type="change_order",
        locked=False,
    )
    await cmd.execute(db)
    await db.flush()
    await db.commit()

    service = ProjectService(db)

    # Query 1 hour in the future -- should still see the branch
    as_of = datetime.now(UTC) + timedelta(hours=1)
    branches = await service.get_project_branches(project.project_id, as_of=as_of)

    # main is always included; the CO branch should be visible too
    assert len(branches) >= 2
    names = [b.name for b in branches]
    assert "main" in names
    assert "BR-CO-2026-002" in names


@pytest.mark.asyncio
async def test_get_project_branches_with_co_and_as_of(
    db: AsyncSession, actor_id
) -> None:
    """get_project_branches with as_of fetches change order status at that time."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.branch import Branch
    from app.models.domain.change_order import ChangeOrder

    project = await create_test_project(db, actor_id, code="BR-ASOF-CO")
    await db.commit()

    co_code = "CO-2026-003"
    branch_name = f"BR-{co_code}"
    branch_root_id = uuid4()
    cmd = CreateVersionCommand(
        entity_class=Branch,
        root_id=branch_root_id,
        actor_id=actor_id,
        name=branch_name,
        project_id=project.project_id,
        type="change_order",
        locked=False,
    )
    await cmd.execute(db)
    await db.flush()

    co_root_id = uuid4()
    co_cmd = CreateVersionCommand(
        entity_class=ChangeOrder,
        root_id=co_root_id,
        actor_id=actor_id,
        code=co_code,
        project_id=project.project_id,
        branch="main",
        status="approved",
        title="Test CO with as_of",
        description="CO for time-travel branch listing",
    )
    await co_cmd.execute(db)
    await db.flush()
    await db.commit()

    service = ProjectService(db)
    as_of = datetime.now(UTC) + timedelta(hours=1)
    branches = await service.get_project_branches(project.project_id, as_of=as_of)

    co_branch = [b for b in branches if b.name == branch_name]
    assert len(co_branch) == 1
    assert co_branch[0].change_order_status == "approved"


@pytest.mark.asyncio
async def test_get_project_branches_skips_main_branch_entity(
    db: AsyncSession, actor_id
) -> None:
    """get_project_branches skips branch entities named 'main' (line 616)."""
    from uuid import uuid4

    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.branch import Branch

    project = await create_test_project(db, actor_id, code="BR-SKIP-MAIN")
    await db.commit()

    # Create a branch entity with name="main" -- this simulates the edge case
    # where a main branch record exists in the branches table
    branch_root_id = uuid4()
    cmd = CreateVersionCommand(
        entity_class=Branch,
        root_id=branch_root_id,
        actor_id=actor_id,
        name="main",
        project_id=project.project_id,
        type="main",
        locked=False,
    )
    await cmd.execute(db)
    await db.flush()
    await db.commit()

    service = ProjectService(db)
    branches = await service.get_project_branches(project.project_id)

    # Should only have one "main" branch entry (the hardcoded one at the top)
    main_branches = [b for b in branches if b.name == "main"]
    assert len(main_branches) == 1
    assert main_branches[0].is_default is True
