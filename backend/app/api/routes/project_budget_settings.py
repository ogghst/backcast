"""Project Budget Settings API routes - budget validation configuration."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.project_budget_settings import ProjectBudgetSettings
from app.models.domain.user import User
from app.models.schemas.project_budget_settings import (
    ProjectBudgetSettingsCreate,
    ProjectBudgetSettingsRead,
)
from app.services.project_budget_settings_service import (
    ProjectBudgetSettingsService,
)

router = APIRouter()


def get_project_budget_settings_service(
    session: AsyncSession = Depends(get_db),
) -> ProjectBudgetSettingsService:
    """Dependency to get ProjectBudgetSettingsService instance."""
    return ProjectBudgetSettingsService(session)


@router.get(
    "/{project_id}/budget-settings",
    response_model=ProjectBudgetSettingsRead,
    operation_id="get_project_budget_settings",
    dependencies=[
        Depends(RoleChecker(required_permission="project-budget-settings-read"))
    ],
)
async def get_project_budget_settings(
    project_id: UUID,
    service: ProjectBudgetSettingsService = Depends(
        get_project_budget_settings_service
    ),
) -> ProjectBudgetSettings:
    """Get budget settings for a project.

    Returns the project's budget warning threshold and admin override settings.
    If no custom settings exist, returns default values (80% threshold, override allowed).
    """
    settings = await service.get_settings_for_project(project_id)

    if settings is None:
        # Return default settings if none exist
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No budget settings found for project {project_id}. Use PUT to create settings.",
        )

    return settings


@router.put(
    "/{project_id}/budget-settings",
    response_model=ProjectBudgetSettingsRead,
    status_code=status.HTTP_200_OK,
    operation_id="update_project_budget_settings",
    dependencies=[
        Depends(RoleChecker(required_permission="project-budget-settings-write"))
    ],
)
async def update_project_budget_settings(
    project_id: UUID,
    settings_in: ProjectBudgetSettingsCreate,
    current_user: User = Depends(get_current_active_user),
    service: ProjectBudgetSettingsService = Depends(
        get_project_budget_settings_service
    ),
) -> ProjectBudgetSettings:
    """Create or update budget settings for a project.

    Creates new settings if none exist, or updates existing settings.
    Only users with project-budget-settings-write permission can modify settings.
    """
    try:
        return await service.upsert_settings(
            project_id=project_id,
            actor_id=current_user.user_id,
            warning_threshold_percent=settings_in.warning_threshold_percent,
            allow_project_admin_override=settings_in.allow_project_admin_override,
            enforce_budget=settings_in.enforce_budget,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
