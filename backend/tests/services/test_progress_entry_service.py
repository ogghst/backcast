"""Tests for ProgressEntryService.

Covers creation, retrieval, progress tracking, history queries,
and batch operations for work packages.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.progress_entry_service import ProgressEntryService
from tests.factories import (
    create_full_hierarchy,
    create_test_progress_entry,
)


@pytest.mark.asyncio
async def test_create_progress_entry(db: AsyncSession, actor_id: UUID) -> None:
    """create should persist a progress entry linked to a work package."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    service = ProgressEntryService(db)

    entry = await service.create(
        actor_id=actor_id,
        work_package_id=hierarchy["wp"].work_package_id,
        progress_percentage=Decimal("25.00"),
        notes="First progress report",
    )

    assert entry.progress_entry_id is not None
    assert entry.work_package_id == hierarchy["wp"].work_package_id
    assert entry.progress_percentage == Decimal("25.00")


@pytest.mark.asyncio
async def test_create_progress_entry_rejects_invalid_percentage(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create should reject progress_percentage outside 0-100 range."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    service = ProgressEntryService(db)

    with pytest.raises(ValueError, match="between 0 and 100"):
        await service.create(
            actor_id=actor_id,
            work_package_id=hierarchy["wp"].work_package_id,
            progress_percentage=Decimal("150.00"),
        )

    with pytest.raises(ValueError, match="between 0 and 100"):
        await service.create(
            actor_id=actor_id,
            work_package_id=hierarchy["wp"].work_package_id,
            progress_percentage=Decimal("-5.00"),
        )


@pytest.mark.asyncio
async def test_create_requires_work_package_id(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create should raise ValueError when work_package_id is missing."""
    service = ProgressEntryService(db)

    with pytest.raises(ValueError, match="work_package_id is required"):
        await service.create(
            actor_id=actor_id,
            progress_percentage=Decimal("50.00"),
        )


@pytest.mark.asyncio
async def test_create_rejects_nonexistent_work_package(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create should raise ValueError when the work package does not exist."""
    service = ProgressEntryService(db)

    with pytest.raises(ValueError, match="not found"):
        await service.create(
            actor_id=actor_id,
            work_package_id=uuid4(),
            progress_percentage=Decimal("50.00"),
        )


@pytest.mark.asyncio
async def test_get_by_id_returns_entry(db: AsyncSession, actor_id: UUID) -> None:
    """get_by_id should retrieve a progress entry by root ID."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    entry = await create_test_progress_entry(
        db,
        actor_id,
        hierarchy["wp"].work_package_id,
        progress_percentage=Decimal("40.00"),
    )
    service = ProgressEntryService(db)

    found = await service.get_by_id(entry.progress_entry_id)

    assert found is not None
    assert found.progress_percentage == Decimal("40.00")


@pytest.mark.asyncio
async def test_get_latest_progress_returns_most_recent(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_latest_progress should return the newest entry for a work package."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp_id = hierarchy["wp"].work_package_id

    # Create first entry
    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("20.00")
    )

    # Create second entry (more recent due to later control_date)
    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("60.00")
    )

    service = ProgressEntryService(db)
    latest = await service.get_latest_progress(wp_id)

    assert latest is not None
    assert latest.progress_percentage == Decimal("60.00")


@pytest.mark.asyncio
async def test_get_latest_progress_returns_none_for_no_entries(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_latest_progress should return None when no entries exist."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    service = ProgressEntryService(db)

    result = await service.get_latest_progress(hierarchy["wp"].work_package_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_progress_history_by_work_package(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_progress_history should list entries for a work package."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp_id = hierarchy["wp"].work_package_id

    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("10.00")
    )
    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("30.00")
    )

    service = ProgressEntryService(db)
    entries, total = await service.get_progress_history(work_package_id=wp_id)

    assert total == 2
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_get_progress_history_by_project(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_progress_history should filter by project_id through the hierarchy."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp_id = hierarchy["wp"].work_package_id
    project_id = hierarchy["project"].project_id

    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("50.00")
    )

    service = ProgressEntryService(db)
    entries, total = await service.get_progress_history(project_id=project_id)

    assert total >= 1
    assert any(e.work_package_id == wp_id for e in entries)


@pytest.mark.asyncio
async def test_get_progress_history_pagination(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_progress_history should support skip/limit pagination."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp_id = hierarchy["wp"].work_package_id

    for pct in (Decimal("10.00"), Decimal("20.00"), Decimal("30.00")):
        await create_test_progress_entry(db, actor_id, wp_id, progress_percentage=pct)

    service = ProgressEntryService(db)
    page1, total = await service.get_progress_history(
        work_package_id=wp_id, skip=0, limit=2
    )
    page2, _ = await service.get_progress_history(
        work_package_id=wp_id, skip=2, limit=2
    )

    assert total == 3
    assert len(page1) == 2
    assert len(page2) == 1


@pytest.mark.asyncio
async def test_get_latest_progress_for_work_packages_batch(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_latest_progress_for_work_packages should map WP IDs to latest entries."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp_id = hierarchy["wp"].work_package_id

    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("75.00")
    )

    service = ProgressEntryService(db)
    result = await service.get_latest_progress_for_work_packages([wp_id])

    assert wp_id in result
    assert result[wp_id].progress_percentage == Decimal("75.00")


@pytest.mark.asyncio
async def test_get_latest_progress_for_work_packages_empty_input(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_latest_progress_for_work_packages should return empty dict for empty input."""
    service = ProgressEntryService(db)

    result = await service.get_latest_progress_for_work_packages([])
    assert result == {}


@pytest.mark.asyncio
async def test_get_progress_history_batch_groups_by_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_progress_history_batch should group entries by work package ID."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp_id = hierarchy["wp"].work_package_id

    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("10.00")
    )
    await create_test_progress_entry(
        db, actor_id, wp_id, progress_percentage=Decimal("40.00")
    )

    service = ProgressEntryService(db)
    grouped = await service.get_progress_history_batch([wp_id])

    assert wp_id in grouped
    assert len(grouped[wp_id]) == 2
