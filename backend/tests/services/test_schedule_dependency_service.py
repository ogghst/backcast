"""Tests for ScheduleDependencyService and the seed dependency sync.

Covers the canonical create path, the duplicate-skip idempotency mechanism
(the service's ``_validate_no_duplicate``), and the non-destructive seed sync
function (``sync_seed_schedule_dependencies``) running twice without
duplicating rows.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.schedule_dependency import ScheduleDependency
from app.models.schemas.schedule_dependency import ScheduleDependencyCreate
from app.services.schedule_dependency_service import (
    DuplicateDependencyError,
    ScheduleDependencyService,
)
from scripts.sync_seed_schedule_dependencies import (
    sync_seed_schedule_dependencies,
)
from tests.factories import (
    create_full_hierarchy,
    create_test_schedule_baseline,
)


async def _link_wp_to_baseline(
    db: AsyncSession, wp_id: UUID, sb_id: UUID, actor_id: UUID
) -> None:
    """Set ``schedule_baseline_id`` on a work package's current version."""
    from app.core.branching.commands import UpdateCommand
    from app.models.domain.work_package import WorkPackage

    cmd = UpdateCommand(
        entity_class=WorkPackage,
        root_id=wp_id,
        actor_id=actor_id,
        branch="main",
        control_date=datetime.now(UTC),
        updates={"schedule_baseline_id": sb_id},
    )
    await cmd.execute(db)


@pytest.mark.asyncio
async def test_create_then_duplicate_raises(db: AsyncSession, actor_id: UUID) -> None:
    """Creating the same (pred, succ, type, branch) link twice must raise."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    project_id = hierarchy["project"].project_id
    service = ScheduleDependencyService(db)

    # Two WPs under the same project, each with a schedule baseline.
    wp1 = hierarchy["wp"]
    ca_id = wp1.control_account_id
    from tests.factories import create_test_work_package

    wp2 = await create_test_work_package(db, actor_id, ca_id)
    sb1 = await create_test_schedule_baseline(db, actor_id, wp1.work_package_id)
    sb2 = await create_test_schedule_baseline(db, actor_id, wp2.work_package_id)
    await _link_wp_to_baseline(
        db, wp1.work_package_id, sb1.schedule_baseline_id, actor_id
    )
    await _link_wp_to_baseline(
        db, wp2.work_package_id, sb2.schedule_baseline_id, actor_id
    )

    create_schema = ScheduleDependencyCreate(
        predecessor_id=wp1.work_package_id,
        successor_id=wp2.work_package_id,
        dependency_type="FS",
        lag_days=0,
        project_id=project_id,
        branch="main",
    )

    created = await service.create(create_schema, actor_id=actor_id)
    assert created.dependency_type == "FS"

    # Second create of the identical link must raise (idempotency guard).
    with pytest.raises(DuplicateDependencyError):
        await service.create(create_schema, actor_id=actor_id)

    # Cleanup created dependency (db fixture commits).
    await db.execute(
        delete(ScheduleDependency).where(
            ScheduleDependency.schedule_dependency_id == created.schedule_dependency_id
        )
    )


@pytest.mark.asyncio
async def test_sync_seed_dependencies_is_idempotent(
    db: AsyncSession, actor_id: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seed sync must create deps once and skip them on re-run.

    Uses a temporary in-memory seed referencing two WPs with linked baselines,
    and cleans up the created rows afterwards.
    """
    hierarchy = await create_full_hierarchy(db, actor_id)
    project_id = hierarchy["project"].project_id
    wp1 = hierarchy["wp"]
    ca_id = wp1.control_account_id
    from tests.factories import create_test_work_package

    wp2 = await create_test_work_package(db, actor_id, ca_id)
    sb1 = await create_test_schedule_baseline(db, actor_id, wp1.work_package_id)
    sb2 = await create_test_schedule_baseline(db, actor_id, wp2.work_package_id)
    await _link_wp_to_baseline(
        db, wp1.work_package_id, sb1.schedule_baseline_id, actor_id
    )
    await _link_wp_to_baseline(
        db, wp2.work_package_id, sb2.schedule_baseline_id, actor_id
    )

    fake_seed: dict[str, Any] = {
        "schedule_dependencies": [
            {
                "predecessor_id": str(wp1.work_package_id),
                "successor_id": str(wp2.work_package_id),
                "dependency_type": "FS",
                "lag_days": 0,
                "project_id": str(project_id),
                "branch": "main",
            },
            {
                "predecessor_id": str(wp1.work_package_id),
                "successor_id": str(wp2.work_package_id),
                "dependency_type": "SS",
                "lag_days": 5,
                "project_id": str(project_id),
                "branch": "main",
            },
        ]
    }
    monkeypatch.setattr(
        "scripts.sync_seed_schedule_dependencies._load_seed",
        lambda: fake_seed,
    )

    # First run: both dependencies created.
    summary1 = await sync_seed_schedule_dependencies(db)
    assert summary1["created"] == 2
    assert summary1["skipped_existing"] == 0

    # Second run: idempotent — both skipped, none created.
    summary2 = await sync_seed_schedule_dependencies(db)
    assert summary2["created"] == 0
    assert summary2["skipped_existing"] == 2

    # Verify exactly two rows exist in the DB for this project.
    rows = (
        (
            await db.execute(
                select(ScheduleDependency).where(
                    ScheduleDependency.project_id == project_id,
                    ScheduleDependency.branch == "main",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    types = sorted(r.dependency_type for r in rows)
    assert types == ["FS", "SS"]

    # Cleanup (db fixture commits).
    await db.execute(
        delete(ScheduleDependency).where(
            ScheduleDependency.project_id == project_id,
            ScheduleDependency.branch == "main",
        )
    )


@pytest.mark.asyncio
async def test_cycle_detection_blocks_circular_link(
    db: AsyncSession, actor_id: UUID
) -> None:
    """A dependency that closes a cycle must be rejected."""
    from app.services.schedule_dependency_service import CircularDependencyError

    hierarchy = await create_full_hierarchy(db, actor_id)
    project_id = hierarchy["project"].project_id
    wp1 = hierarchy["wp"]
    ca_id = wp1.control_account_id
    from tests.factories import create_test_work_package

    wp2 = await create_test_work_package(db, actor_id, ca_id)
    sb1 = await create_test_schedule_baseline(db, actor_id, wp1.work_package_id)
    sb2 = await create_test_schedule_baseline(db, actor_id, wp2.work_package_id)
    await _link_wp_to_baseline(
        db, wp1.work_package_id, sb1.schedule_baseline_id, actor_id
    )
    await _link_wp_to_baseline(
        db, wp2.work_package_id, sb2.schedule_baseline_id, actor_id
    )

    service = ScheduleDependencyService(db)
    await service.create(
        ScheduleDependencyCreate(
            predecessor_id=wp1.work_package_id,
            successor_id=wp2.work_package_id,
            dependency_type="FS",
            lag_days=0,
            project_id=project_id,
            branch="main",
        ),
        actor_id=actor_id,
    )

    # Reverse link would close the cycle wp1 -> wp2 -> wp1.
    with pytest.raises(CircularDependencyError):
        await service.create(
            ScheduleDependencyCreate(
                predecessor_id=wp2.work_package_id,
                successor_id=wp1.work_package_id,
                dependency_type="FS",
                lag_days=0,
                project_id=project_id,
                branch="main",
            ),
            actor_id=actor_id,
        )

    # Cleanup.
    await db.execute(
        delete(ScheduleDependency).where(
            ScheduleDependency.project_id == project_id,
            ScheduleDependency.branch == "main",
        )
    )
