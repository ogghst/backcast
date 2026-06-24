"""Tests for ChangeOrderConfigService.

Covers created_by_name population on read paths (get_project_config).
Uses a project-scoped override to avoid colliding with the seeded global config.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_config import ChangeOrderWorkflowConfig
from app.services.change_order_config_service import ChangeOrderConfigService
from tests.factories import create_test_project


async def _seed_project_config(
    db: AsyncSession, actor_id: UUID, project_id: UUID
) -> ChangeOrderWorkflowConfig:
    """Insert a minimal active project-scoped config for read-path tests."""
    config = ChangeOrderWorkflowConfig(
        config_id=uuid4(),
        project_id=project_id,
        is_active=True,
        version=1,
        created_by=actor_id,
        impact_weights={},
        score_boundaries={},
    )
    db.add(config)
    await db.commit()
    return config


@pytest.mark.asyncio
async def test_get_project_config_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_project_config should populate created_by_name from the creator."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    await _seed_project_config(db, actor_id, project.project_id)

    service = ChangeOrderConfigService(db)
    config = await service.get_project_config(project.project_id)
    assert config is not None
    assert config.created_by_name == "Admin User"
