"""Tests for ProjectBudgetSettingsService.

Covers upsert (create and update paths), default values,
warning threshold retrieval, admin override check, and budget enforcement.
"""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project_budget_settings_service import (
    ProjectBudgetSettingsService,
)
from tests.factories import create_test_project


@pytest.mark.asyncio
async def test_upsert_creates_new_settings_with_defaults(
    db: AsyncSession, actor_id: UUID
) -> None:
    """upsert_settings creates settings with default values when none exist."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    settings = await service.upsert_settings(project.project_id, actor_id)
    await db.commit()

    assert settings is not None
    assert settings.project_id == project.project_id
    assert settings.warning_threshold_percent == Decimal("80.0")
    assert settings.allow_project_admin_override is True
    assert settings.enforce_budget is False


@pytest.mark.asyncio
async def test_upsert_creates_with_custom_values(
    db: AsyncSession, actor_id: UUID
) -> None:
    """upsert_settings creates settings with custom values."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    settings = await service.upsert_settings(
        project.project_id,
        actor_id,
        warning_threshold_percent=Decimal("90.0"),
        allow_project_admin_override=False,
        enforce_budget=True,
    )
    await db.commit()

    assert settings.warning_threshold_percent == Decimal("90.0")
    assert settings.allow_project_admin_override is False
    assert settings.enforce_budget is True


@pytest.mark.asyncio
async def test_upsert_updates_existing_settings(
    db: AsyncSession, actor_id: UUID
) -> None:
    """upsert_settings creates a new version when settings already exist."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)

    # Create initial settings
    await service.upsert_settings(
        project.project_id,
        actor_id,
        warning_threshold_percent=Decimal("70.0"),
    )
    await db.commit()

    # Update them
    updated = await service.upsert_settings(
        project.project_id,
        actor_id,
        warning_threshold_percent=Decimal("60.0"),
    )
    await db.commit()

    assert updated.warning_threshold_percent == Decimal("60.0")

    # Verify get_settings_for_project returns updated version
    current = await service.get_settings_for_project(project.project_id)
    assert current is not None
    assert current.warning_threshold_percent == Decimal("60.0")


@pytest.mark.asyncio
async def test_get_warning_threshold_returns_default_without_settings(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_warning_threshold returns 80.0 when no settings exist."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    threshold = await service.get_warning_threshold(project.project_id)

    assert threshold == Decimal("80.0")


@pytest.mark.asyncio
async def test_get_warning_threshold_returns_custom_value(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_warning_threshold returns the configured threshold."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    await service.upsert_settings(
        project.project_id,
        actor_id,
        warning_threshold_percent=Decimal("95.0"),
    )
    await db.commit()

    threshold = await service.get_warning_threshold(project.project_id)
    assert threshold == Decimal("95.0")


@pytest.mark.asyncio
async def test_can_admin_override_defaults_to_true(
    db: AsyncSession, actor_id: UUID
) -> None:
    """can_admin_override returns True when no settings exist."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    result = await service.can_admin_override(project.project_id)
    assert result is True


@pytest.mark.asyncio
async def test_can_admin_override_returns_configured_value(
    db: AsyncSession, actor_id: UUID
) -> None:
    """can_admin_override returns False when explicitly disabled."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    await service.upsert_settings(
        project.project_id,
        actor_id,
        allow_project_admin_override=False,
    )
    await db.commit()

    result = await service.can_admin_override(project.project_id)
    assert result is False


@pytest.mark.asyncio
async def test_is_budget_enforced_defaults_to_false(
    db: AsyncSession, actor_id: UUID
) -> None:
    """is_budget_enforced returns False when no settings exist."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    result = await service.is_budget_enforced(project.project_id)
    assert result is False


@pytest.mark.asyncio
async def test_is_budget_enforced_returns_configured_value(
    db: AsyncSession, actor_id: UUID
) -> None:
    """is_budget_enforced returns True when explicitly enabled."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    await service.upsert_settings(
        project.project_id,
        actor_id,
        enforce_budget=True,
    )
    await db.commit()

    result = await service.is_budget_enforced(project.project_id)
    assert result is True


@pytest.mark.asyncio
async def test_get_settings_for_project_returns_none_without_settings(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_settings_for_project returns None when no settings exist."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    settings = await service.get_settings_for_project(project.project_id)
    assert settings is None


@pytest.mark.asyncio
async def test_get_settings_for_project_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_settings_for_project should populate created_by_name from the creator."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ProjectBudgetSettingsService(db)
    await service.upsert_settings(project.project_id, actor_id)
    await db.commit()

    settings = await service.get_settings_for_project(project.project_id)
    assert settings is not None
    assert settings.created_by_name == "Admin User"
