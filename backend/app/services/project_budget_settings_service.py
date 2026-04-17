"""Project Budget Settings Service - budget validation configuration management."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.project_budget_settings import ProjectBudgetSettings

if TYPE_CHECKING:
    pass


class ProjectBudgetSettingsService(TemporalService[ProjectBudgetSettings]):  # type: ignore[type-var,unused-ignore]
    """Service for Project Budget Settings management (versionable, not branchable).

    Project Budget Settings control cost registration validation behavior,
    including warning thresholds and admin override permissions.
    They are versionable (NOT branchable) - settings apply across all branches.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(ProjectBudgetSettings, db)

    async def get_settings_for_project(
        self, project_id: UUID
    ) -> ProjectBudgetSettings | None:
        """Get current budget settings for a project.

        Args:
            project_id: The project to get settings for

        Returns:
            ProjectBudgetSettings if found, None otherwise
        """
        stmt = (
            select(ProjectBudgetSettings)
            .where(
                ProjectBudgetSettings.project_id == project_id,
                func.upper(ProjectBudgetSettings.valid_time).is_(None),
                ProjectBudgetSettings.deleted_at.is_(None),
            )
            .order_by(ProjectBudgetSettings.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_settings(
        self,
        project_id: UUID,
        actor_id: UUID,
        warning_threshold_percent: Decimal | None = None,
        allow_project_admin_override: bool | None = None,
        enforce_budget: bool | None = None,
    ) -> ProjectBudgetSettings:
        """Create or update budget settings for a project.

        If settings exist, updates them (creates new version).
        If settings don't exist, creates new settings.

        Args:
            project_id: The project to create/update settings for
            actor_id: The user making the change
            warning_threshold_percent: Warning threshold (optional, uses default if not provided)
            allow_project_admin_override: Allow admin override (optional, uses default if not provided)
            enforce_budget: Block over-budget registrations (optional, defaults to False)

        Returns:
            The created or updated ProjectBudgetSettings
        """
        # Check if settings exist
        existing = await self.get_settings_for_project(project_id)

        # Prepare field data
        fields: dict[str, Any] = {"project_id": project_id}

        if warning_threshold_percent is not None:
            fields["warning_threshold_percent"] = warning_threshold_percent
        else:
            # Use default if not provided
            fields["warning_threshold_percent"] = Decimal("80.0")

        if allow_project_admin_override is not None:
            fields["allow_project_admin_override"] = allow_project_admin_override
        else:
            # Use default if not provided
            fields["allow_project_admin_override"] = True

        if enforce_budget is not None:
            fields["enforce_budget"] = enforce_budget
        else:
            fields["enforce_budget"] = False

        if existing:
            # Update existing settings
            class ProjectBudgetSettingsUpdateCommand(UpdateVersionCommand[ProjectBudgetSettings]):  # type: ignore[type-var,unused-ignore]
                def _root_field_name(self) -> str:
                    return "project_budget_settings_id"

            cmd = ProjectBudgetSettingsUpdateCommand(
                entity_class=ProjectBudgetSettings,  # type: ignore[type-var,unused-ignore]
                root_id=existing.project_budget_settings_id,
                actor_id=actor_id,
                control_date=None,
                **fields,
            )
            return await cmd.execute(self.session)
        else:
            # Create new settings
            root_id = uuid4()
            fields["project_budget_settings_id"] = root_id

            create_cmd = CreateVersionCommand(
                entity_class=ProjectBudgetSettings,  # type: ignore[type-var,unused-ignore]
                root_id=root_id,
                actor_id=actor_id,
                control_date=None,
                **fields,
            )
            return await create_cmd.execute(self.session)

    async def get_warning_threshold(self, project_id: UUID) -> Decimal:
        """Get the warning threshold for a project.

        Returns the default threshold (80.0) if no custom settings exist.

        Args:
            project_id: The project to get the threshold for

        Returns:
            Warning threshold percentage (Decimal)
        """
        settings = await self.get_settings_for_project(project_id)
        if settings:
            return settings.warning_threshold_percent
        return Decimal("80.0")

    async def can_admin_override(self, project_id: UUID) -> bool:
        """Check if project admin override is allowed for a project.

        Returns True (default) if no custom settings exist.

        Args:
            project_id: The project to check

        Returns:
            True if admin override is allowed, False otherwise
        """
        settings = await self.get_settings_for_project(project_id)
        if settings:
            return settings.allow_project_admin_override
        return True

    async def is_budget_enforced(self, project_id: UUID) -> bool:
        """Check if budget enforcement is enabled for a project.

        Returns False (default) if no custom settings exist.

        Args:
            project_id: The project to check

        Returns:
            True if budget enforcement is enabled, False otherwise
        """
        settings = await self.get_settings_for_project(project_id)
        if settings:
            return settings.enforce_budget
        return False
