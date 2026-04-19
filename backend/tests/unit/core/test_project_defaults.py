"""Tests for project default configurations."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.project_defaults import (
    DEFAULT_BUDGET_WARNING_THRESHOLD,
    ProjectCreationDefaults,
    apply_project_creation_defaults,
    get_project_creation_defaults,
)
from app.models.schemas.project_budget_settings import ProjectBudgetSettingsBase


class TestConstants:
    """Test default constants."""

    def test_default_budget_warning_threshold(self) -> None:
        """Test that DEFAULT_BUDGET_WARNING_THRESHOLD is set correctly."""
        assert DEFAULT_BUDGET_WARNING_THRESHOLD == Decimal("80.0")


class TestProjectCreationDefaults:
    """Test ProjectCreationDefaults dataclass."""

    def test_default_budget_config(self) -> None:
        """Test that ProjectCreationDefaults includes budget config."""
        defaults = ProjectCreationDefaults()
        assert (
            defaults.budget.warning_threshold_percent
            == DEFAULT_BUDGET_WARNING_THRESHOLD
        )
        assert defaults.budget.allow_project_admin_override is True

    def test_custom_budget_config(self) -> None:
        """Test that ProjectCreationDefaults accepts custom budget config."""
        custom_budget = ProjectBudgetSettingsBase(
            warning_threshold_percent=Decimal("95.0"),
            allow_project_admin_override=False,
        )
        defaults = ProjectCreationDefaults(budget=custom_budget)
        assert defaults.budget.warning_threshold_percent == Decimal("95.0")
        assert defaults.budget.allow_project_admin_override is False

    def test_frozen_dataclass(self) -> None:
        """Test that ProjectCreationDefaults is frozen (immutable)."""
        from dataclasses import FrozenInstanceError

        defaults = ProjectCreationDefaults()
        with pytest.raises(FrozenInstanceError):
            defaults.budget = ProjectBudgetSettingsBase()  # type: ignore


class TestGetProjectCreationDefaults:
    """Test get_project_creation_defaults function."""

    def test_returns_defaults(self) -> None:
        """Test that function returns ProjectCreationDefaults."""
        defaults = get_project_creation_defaults()
        assert isinstance(defaults, ProjectCreationDefaults)

    def test_default_values(self) -> None:
        """Test that function returns correct default values."""
        defaults = get_project_creation_defaults()
        assert (
            defaults.budget.warning_threshold_percent
            == DEFAULT_BUDGET_WARNING_THRESHOLD
        )
        assert defaults.budget.allow_project_admin_override is True

    def test_custom_threshold(self) -> None:
        """Test that function accepts custom warning threshold."""
        defaults = get_project_creation_defaults(
            warning_threshold_percent=Decimal("85.0")
        )
        assert defaults.budget.warning_threshold_percent == Decimal("85.0")
        assert defaults.budget.allow_project_admin_override is True

    def test_custom_override(self) -> None:
        """Test that function accepts custom override setting."""
        defaults = get_project_creation_defaults(allow_project_admin_override=False)
        assert defaults.budget.allow_project_admin_override is False
        assert (
            defaults.budget.warning_threshold_percent
            == DEFAULT_BUDGET_WARNING_THRESHOLD
        )

    def test_both_custom(self) -> None:
        """Test that function accepts both custom values."""
        defaults = get_project_creation_defaults(
            warning_threshold_percent=Decimal("95.0"),
            allow_project_admin_override=False,
        )
        assert defaults.budget.warning_threshold_percent == Decimal("95.0")
        assert defaults.budget.allow_project_admin_override is False


class TestApplyProjectCreationDefaults:
    """Test apply_project_creation_defaults function."""

    @pytest.mark.asyncio
    async def test_creates_budget_settings(self, db_session, user_factory) -> None:
        """Test that function creates budget settings for project."""
        from app.services.project_budget_settings_service import (
            ProjectBudgetSettingsService,
        )

        project_id = uuid4()
        actor_id = uuid4()
        budget_service = ProjectBudgetSettingsService(db_session)

        await apply_project_creation_defaults(
            project_id=project_id,
            actor_id=actor_id,
            budget_settings_service=budget_service,
        )

        settings = await budget_service.get_settings_for_project(project_id)
        assert settings is not None
        assert settings.project_id == project_id
        assert settings.warning_threshold_percent == DEFAULT_BUDGET_WARNING_THRESHOLD
        assert settings.allow_project_admin_override is True

    @pytest.mark.asyncio
    async def test_applies_custom_defaults(self, db_session, user_factory) -> None:
        """Test that function applies custom default values."""
        from app.services.project_budget_settings_service import (
            ProjectBudgetSettingsService,
        )

        project_id = uuid4()
        actor_id = uuid4()
        budget_service = ProjectBudgetSettingsService(db_session)

        custom_defaults = get_project_creation_defaults(
            warning_threshold_percent=Decimal("90.0"),
            allow_project_admin_override=False,
        )

        await apply_project_creation_defaults(
            project_id=project_id,
            actor_id=actor_id,
            budget_settings_service=budget_service,
            defaults=custom_defaults,
        )

        settings = await budget_service.get_settings_for_project(project_id)
        assert settings is not None
        assert settings.warning_threshold_percent == Decimal("90.0")
        assert settings.allow_project_admin_override is False
