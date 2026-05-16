"""Unit tests for ProjectBudgetSettingsService."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.user import User
from app.services.project_budget_settings_service import ProjectBudgetSettingsService


@pytest.mark.asyncio
async def test_get_settings_for_project_when_none_exist(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test getting settings when none exist returns None."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    settings = await service.get_settings_for_project(project_id)
    assert settings is None


@pytest.mark.asyncio
async def test_upsert_settings_creates_new_settings(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test creating new settings via upsert."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    # Create new settings
    settings = await service.upsert_settings(
        project_id=project_id,
        actor_id=test_user.user_id,
        warning_threshold_percent=Decimal("75.0"),
        allow_project_admin_override=False,
    )

    assert settings is not None
    assert settings.project_id == project_id
    assert settings.warning_threshold_percent == Decimal("75.0")
    assert settings.allow_project_admin_override is False
    assert settings.created_by == test_user.user_id


@pytest.mark.asyncio
async def test_upsert_settings_updates_existing(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test updating existing settings via upsert."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    # Create initial settings
    initial = await service.upsert_settings(
        project_id=project_id,
        actor_id=test_user.user_id,
        warning_threshold_percent=Decimal("80.0"),
        allow_project_admin_override=True,
    )

    # Update settings
    updated = await service.upsert_settings(
        project_id=project_id,
        actor_id=test_user.user_id,
        warning_threshold_percent=Decimal("90.0"),
        allow_project_admin_override=False,
    )

    assert updated is not None
    assert updated.project_id == project_id
    assert updated.warning_threshold_percent == Decimal("90.0")
    assert updated.allow_project_admin_override is False
    # Should have different ID (new version)
    assert updated.id != initial.id
    # Same root ID
    assert updated.project_budget_settings_id == initial.project_budget_settings_id


@pytest.mark.asyncio
async def test_upsert_settings_uses_defaults(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test that upsert uses default values when not provided."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    # Create settings without providing values
    settings = await service.upsert_settings(
        project_id=project_id,
        actor_id=test_user.user_id,
    )

    assert settings is not None
    assert settings.warning_threshold_percent == Decimal("80.0")
    assert settings.allow_project_admin_override is True


@pytest.mark.asyncio
async def test_get_warning_threshold_uses_default(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test getting warning threshold when no settings exist returns default."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    threshold = await service.get_warning_threshold(project_id)
    assert threshold == Decimal("80.0")


@pytest.mark.asyncio
async def test_get_warning_threshold_returns_custom_value(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test getting custom warning threshold."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    # Create custom settings
    await service.upsert_settings(
        project_id=project_id,
        actor_id=test_user.user_id,
        warning_threshold_percent=Decimal("85.0"),
    )

    threshold = await service.get_warning_threshold(project_id)
    assert threshold == Decimal("85.0")


@pytest.mark.asyncio
async def test_can_admin_override_uses_default(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test checking admin override when no settings exist returns default True."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    can_override = await service.can_admin_override(project_id)
    assert can_override is True


@pytest.mark.asyncio
async def test_can_admin_override_returns_custom_value(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test checking custom admin override setting."""
    service = ProjectBudgetSettingsService(db_session)
    project_id = uuid4()

    # Create custom settings
    await service.upsert_settings(
        project_id=project_id,
        actor_id=test_user.user_id,
        allow_project_admin_override=False,
    )

    can_override = await service.can_admin_override(project_id)
    assert can_override is False


@pytest.mark.asyncio
async def test_settings_are_project_isolated(
    db_session: AsyncSession, test_user: User
) -> None:
    """Test that settings are properly isolated per project."""
    service = ProjectBudgetSettingsService(db_session)
    project1_id = uuid4()
    project2_id = uuid4()

    # Create different settings for each project
    await service.upsert_settings(
        project_id=project1_id,
        actor_id=test_user.user_id,
        warning_threshold_percent=Decimal("70.0"),
    )

    await service.upsert_settings(
        project_id=project2_id,
        actor_id=test_user.user_id,
        warning_threshold_percent=Decimal("95.0"),
    )

    # Verify isolation
    threshold1 = await service.get_warning_threshold(project1_id)
    threshold2 = await service.get_warning_threshold(project2_id)

    assert threshold1 == Decimal("70.0")
    assert threshold2 == Decimal("95.0")
