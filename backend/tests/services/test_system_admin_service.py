"""Tests for SystemAdminService.

Covers the database dump path, specifically the change-order workflow
config export: the ``co_workflow_config`` table supports multiple rows
(one global default plus optional per-project overrides), but the dump
format round-trips a single global config. ``scalar_one_or_none`` raised
``MultipleResultsFound`` whenever more than one global config existed.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_config import (
    ChangeOrderImpactLevelConfig,
    ChangeOrderWorkflowConfig,
)
from app.services.system_admin_service import SystemAdminService

# SYSTEM_ACTOR used by the seed (see seed_system_config.json).
SYSTEM_ACTOR = UUID("00000000-0000-0000-0000-000000000001")


async def _seed_empty_global_config(db: AsyncSession) -> ChangeOrderWorkflowConfig:
    """Insert an empty (no child rules) global config row."""
    config = ChangeOrderWorkflowConfig(
        config_id=uuid4(),
        project_id=None,
        is_active=False,
        version=1,
        created_by=SYSTEM_ACTOR,
        impact_weights={},
        score_boundaries={},
    )
    db.add(config)
    await db.commit()
    return config


async def _seed_populated_global_config(
    db: AsyncSession,
) -> ChangeOrderWorkflowConfig:
    """Insert a global config row with a single impact-level child rule."""
    config = ChangeOrderWorkflowConfig(
        config_id=uuid4(),
        project_id=None,
        is_active=True,
        version=1,
        created_by=SYSTEM_ACTOR,
        impact_weights={"budget": 1.0},
        score_boundaries={"LOW": 10},
    )
    db.add(config)
    await db.commit()

    impact_level = ChangeOrderImpactLevelConfig(
        level_name="LOW",
        level_order=1,
        threshold_amount=10000,
        score_threshold_min=0,
        score_threshold_max=10,
        is_active=True,
        config_id=config.id,
    )
    db.add(impact_level)
    await db.commit()
    return config


@pytest.mark.asyncio
async def test_dump_change_order_workflow_picks_populated_global_config(
    db: AsyncSession,
) -> None:
    """dump_database must not crash and must export the populated global config.

    Reproduces the ``MultipleResultsFound`` crash that occurred when more
    than one global (project_id IS NULL) ``co_workflow_config`` row existed,
    and proves the populated global (the one with child rules) is exported
    rather than an empty duplicate.
    """
    # Seed two global configs: one populated, one empty. ``scalar_one_or_none``
    # would have raised MultipleResultsFound on this state.
    populated = await _seed_populated_global_config(db)
    empty = await _seed_empty_global_config(db)

    service = SystemAdminService(db)
    try:
        result = await service.dump_database()
    finally:
        # Clean up rows this test created (db fixture commits) so the dev DB
        # is not polluted (cascades remove child rule rows).
        rows = (
            (
                await db.execute(
                    select(ChangeOrderWorkflowConfig).where(
                        ChangeOrderWorkflowConfig.id.in_([populated.id, empty.id])
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            await db.delete(row)
        await db.commit()

    co_workflow = result["system_config"]["change_order_workflow"]
    exported_config = co_workflow["config"]
    # The empty duplicate must NEVER shadow a populated config. The exported
    # config must be a populated global (one with child rules) — either the
    # seeded one or the one this test inserted, never the empty duplicate.
    assert exported_config["id"] != str(empty.id)
    assert exported_config["project_id"] is None
    assert len(co_workflow["impact_levels"]) >= 1
    # The populated config seeded by this test is exported if no older
    # populated global exists (otherwise the seeded global is preferred).
    exported_ids = {exported_config["id"]}
    assert str(empty.id) not in exported_ids


@pytest.mark.asyncio
async def test_dump_change_order_workflow_excludes_per_project_override(
    db: AsyncSession,
) -> None:
    """Per-project overrides (project_id != NULL) must not appear in the dump.

    A single global config plus a per-project override is the normal runtime
    state; the dump must export only the global config.
    """
    global_config = ChangeOrderWorkflowConfig(
        config_id=uuid4(),
        project_id=None,
        is_active=True,
        version=1,
        created_by=SYSTEM_ACTOR,
        impact_weights={},
        score_boundaries={},
    )
    project_override = ChangeOrderWorkflowConfig(
        config_id=uuid4(),
        project_id=uuid4(),
        is_active=True,
        version=1,
        created_by=SYSTEM_ACTOR,
        impact_weights={"budget": 0.5},
        score_boundaries={},
    )
    db.add_all([global_config, project_override])
    await db.commit()

    service = SystemAdminService(db)
    try:
        result = await service.dump_database()
    finally:
        rows = (
            (
                await db.execute(
                    select(ChangeOrderWorkflowConfig).where(
                        ChangeOrderWorkflowConfig.id.in_(
                            [
                                global_config.id,
                                project_override.id,
                            ]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            await db.delete(row)
        await db.commit()

    exported_config = result["system_config"]["change_order_workflow"]["config"]
    # The per-project override must never be exported by the global dump.
    assert exported_config["id"] != str(project_override.id)
    assert exported_config["project_id"] is None
