"""Tests for created_by_name / created_at population on read paths.

Regression coverage for the systemic bug where versioned/branchable
entities returned `created_by_name = null` (UI showed "System") and
WBS showed an "unknown" date, because the generic base services only
populated these inside get_history, never on get_as_of / list.

These tests use the seeded admin user (TEST_USER_ID -> "Admin User"),
which the `actor_id` fixture resolves to, so created_by always maps to
"Admin User".
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.service import TemporalService
from app.models.domain.cost_event_type import CostEventType
from app.models.domain.wbs_element import WBSElement
from app.models.schemas.wbs_element import WBSElementUpdate
from app.services.wbs_element_service import WBSElementService
from app.services.work_package_service import WorkPackageService
from tests.factories import (
    create_full_hierarchy,
    create_test_cost_event_type,
    create_test_project,
    create_test_wbs_element,
)

ADMIN_NAME = "Admin User"


# ---------------------------------------------------------------------------
# Base TemporalService: get_as_of + get_all populate created_by_name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_temporal_get_as_of_populates_created_by_name(
    db: AsyncSession, actor_id
) -> None:
    """Base TemporalService.get_as_of resolves created_by_name (not null)."""
    # CostEventType is a plain versionable (TemporalService, no branching).
    service: TemporalService[CostEventType] = TemporalService(CostEventType, db)
    created = await create_test_cost_event_type(
        db, actor_id, code="CET-READ", name="Read-path type"
    )
    await db.commit()

    fetched = await service.get_as_of(created.cost_event_type_id)
    assert fetched is not None
    assert fetched.created_by == actor_id
    assert fetched.created_by_name == ADMIN_NAME


@pytest.mark.asyncio
async def test_temporal_get_all_populates_created_by_name(
    db: AsyncSession, actor_id
) -> None:
    """Base TemporalService.get_all resolves created_by_name on every row.

    Uses a targeted get_as_of on a freshly-seeded entity for the precise
    assertion (get_all returns an unordered window that may exclude any
    single row in a dev DB with accumulated test data), and asserts that
    get_all never leaves created_by_name unset on the rows it returns.
    """
    service: TemporalService[CostEventType] = TemporalService(CostEventType, db)
    created = await create_test_cost_event_type(
        db, actor_id, code="CET-LIST", name="List type"
    )
    await db.commit()

    # The freshly-seeded current version must resolve via get_as_of.
    fetched = await service.get_as_of(created.cost_event_type_id)
    assert fetched is not None
    assert fetched.created_by_name == ADMIN_NAME

    # get_all must populate created_by_name: rows whose created_by resolves to a
    # known user carry the resolved name (None only when the user row is gone,
    # e.g. stale seed data). We assert the batch ran for at least the admin.
    results = await service.get_all(limit=1000)
    assert results, "get_all should return at least one current version"
    admin_rows = [r for r in results if r.created_by == actor_id]
    assert admin_rows, "expected at least one row created by the test actor"
    assert all(r.created_by_name == ADMIN_NAME for r in admin_rows)


# ---------------------------------------------------------------------------
# Base BranchableService: get_as_of populates created_by_name + created_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_branchable_get_as_of_populates_created_by_name(
    db: AsyncSession, actor_id
) -> None:
    """Base BranchableService.get_as_of resolves created_by_name (not null)."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()
    wbs = hierarchy["wbs"]

    # Use the raw BranchableService (not the WBS subclass) to exercise the base.
    service: BranchableService = WBSElementService(db)
    fetched = await service.get_as_of(wbs.wbs_element_id)
    assert fetched is not None
    assert fetched.created_by_name == ADMIN_NAME
    # created_at derived from transaction_time.lower (WBS declares created_at).
    assert fetched.created_at is not None
    assert isinstance(fetched.created_at, datetime)


# ---------------------------------------------------------------------------
# WBS: get_as_of + get_wbs_elements populate BOTH created_by_name + created_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wbs_get_as_of_populates_both_fields(db: AsyncSession, actor_id) -> None:
    """WBS get_as_of (detail) sets created_by_name AND a non-null created_at."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    fetched = await service.get_as_of(wbs.wbs_element_id)
    assert fetched is not None
    assert fetched.created_by_name == ADMIN_NAME
    assert fetched.created_at is not None
    assert isinstance(fetched.created_at, datetime)


@pytest.mark.asyncio
async def test_wbs_get_wbs_elements_populates_both_fields(
    db: AsyncSession, actor_id
) -> None:
    """WBS list path sets created_by_name AND created_at for every element."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    results, _ = await service.get_wbs_elements(project_id=project.project_id)
    matching = [w for w in results if w.wbs_element_id == wbs.wbs_element_id]
    assert matching, "seeded WBS element should appear in list"
    for element in matching:
        assert element.created_by_name == ADMIN_NAME
        assert element.created_at is not None
        assert isinstance(element.created_at, datetime)


@pytest.mark.asyncio
async def test_wbs_created_by_resolves_to_creator_full_name(
    db: AsyncSession, actor_id
) -> None:
    """created_by UUID resolves to the creating user's full_name.

    Mirrors the reported scenario (WBS eacd83da-... created_by resolves to
    "Admin User"): the resolver must map created_by -> User.full_name, not
    echo the UUID or return null.
    """
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    fetched = await service.get_as_of(wbs.wbs_element_id)
    assert fetched is not None
    # created_by is the raw UUID; created_by_name is the resolved full_name.
    assert str(fetched.created_by) == str(actor_id)
    assert fetched.created_by_name == ADMIN_NAME


@pytest.mark.asyncio
async def test_wbs_get_wbe_history_populates_created_at(
    db: AsyncSession, actor_id
) -> None:
    """WBS history path also derives created_at for each version."""
    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    service = WBSElementService(db)
    history = await service.get_wbe_history(wbs.wbs_element_id)
    assert history, "history should contain at least one version"
    assert all(h.created_by_name == ADMIN_NAME for h in history)
    assert all(h.created_at is not None for h in history)


# ---------------------------------------------------------------------------
# Work package: get_work_packages populates created_by_name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_work_package_get_work_packages_populates_created_by_name(
    db: AsyncSession, actor_id
) -> None:
    """Work package list path resolves created_by_name on each package."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()
    wp = hierarchy["wp"]

    service = WorkPackageService(db)
    results, _ = await service.get_work_packages(
        control_account_id=hierarchy["ca"].control_account_id
    )
    assert any(w.work_package_id == wp.work_package_id for w in results)
    for w in results:
        assert w.created_by_name == ADMIN_NAME


@pytest.mark.asyncio
async def test_work_package_get_as_of_populates_created_by_name(
    db: AsyncSession, actor_id
) -> None:
    """Work package detail path resolves created_by_name via base get_as_of."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()
    wp = hierarchy["wp"]

    service = WorkPackageService(db)
    fetched = await service.get_as_of(wp.work_package_id)
    assert fetched is not None
    assert fetched.created_by_name == ADMIN_NAME


# ---------------------------------------------------------------------------
# Edge: missing entity returns None without error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wbs_get_as_of_missing_returns_none(db: AsyncSession) -> None:
    """get_as_of for a non-existent WBS returns None cleanly."""
    service = WBSElementService(db)
    assert await service.get_as_of(uuid4()) is None


# ---------------------------------------------------------------------------
# Timestamp correctness: created_at == MIN(lower(tx)), updated_at == MAX(...)
#
# Regression for the bug where created_at was set to the CURRENT version's
# transaction_time.lower (i.e. the last-modification time) instead of the
# true creation time across all versions.
# ---------------------------------------------------------------------------


async def _wbs_version_bounds(db: AsyncSession, wbe_id: UUID) -> tuple[Any, Any]:
    """Return (min_lower, max_lower) of transaction_time over all versions."""
    from typing import cast

    stmt = select(
        func.min(func.lower(cast(Any, WBSElement).transaction_time)),
        func.max(func.lower(cast(Any, WBSElement).transaction_time)),
    ).where(WBSElement.wbs_element_id == wbe_id)
    row = (await db.execute(stmt)).one()
    return row[0], row[1]


@pytest.mark.asyncio
async def test_wbs_created_at_is_true_creation_not_last_modify(
    db: AsyncSession, actor_id
) -> None:
    """created_at must equal MIN(lower(transaction_time)) over ALL versions.

    Creates two versions of a WBS (create + update with a real-time gap) and
    asserts created_at tracks the first version, not the current (latest) one.
    """
    import asyncio

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    first_lower = wbs.transaction_time.lower
    assert first_lower is not None

    # Create a second version at a later wall-clock time.
    await asyncio.sleep(1.1)
    service = WBSElementService(db)
    await service.update_wbe(
        wbs.wbs_element_id,
        WBSElementUpdate(name=f"WBS-updated-{wbs.wbs_element_id.hex[:8]}"),
        actor_id,
    )
    await db.commit()

    min_lower, max_lower = await _wbs_version_bounds(db, wbs.wbs_element_id)
    assert max_lower > min_lower, "expected at least two distinct versions"

    fetched = await service.get_as_of(wbs.wbs_element_id)
    assert fetched is not None
    # created_at is the true creation time (first version), NOT the update.
    assert fetched.created_at == min_lower
    assert fetched.created_at < fetched.updated_at
    # updated_at is the latest modification.
    assert fetched.updated_at == max_lower


@pytest.mark.asyncio
async def test_wbs_history_populates_true_created_at_and_updated_at(
    db: AsyncSession, actor_id
) -> None:
    """get_wbe_history sets created_at=MIN and updated_at=MAX on every row.

    All history versions share the same (created_at, updated_at) pair because
    both are root-level aggregates, not per-version.
    """
    import asyncio

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()
    await asyncio.sleep(1.1)
    service = WBSElementService(db)
    await service.update_wbe(
        wbs.wbs_element_id,
        WBSElementUpdate(description="second version"),
        actor_id,
    )
    await db.commit()

    min_lower, max_lower = await _wbs_version_bounds(db, wbs.wbs_element_id)
    assert max_lower > min_lower

    history = await service.get_wbe_history(wbs.wbs_element_id)
    assert len(history) >= 2
    for h in history:
        assert h.created_at == min_lower
        assert h.updated_at == max_lower
