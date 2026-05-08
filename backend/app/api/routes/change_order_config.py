"""Change Order Workflow Configuration API routes.

Provides endpoints for managing change order workflow configuration:
- Global config: GET/PUT /change-order-config/global
- Per-project config: GET/PUT/DELETE /change-order-config/projects/{project_id}
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.change_order_config import (
    WorkflowConfigResponse,
    WorkflowConfigUpdateRequest,
)
from app.services.change_order_config_service import (
    ChangeOrderConfigService,
    ConfigurationConflictError,
    ConfigurationError,
)

router = APIRouter()


def get_config_service(
    session: AsyncSession = Depends(get_db),
) -> ChangeOrderConfigService:
    """Dependency to get ChangeOrderConfigService instance."""
    return ChangeOrderConfigService(session)


@router.get(
    "/global",
    response_model=WorkflowConfigResponse,
    operation_id="get_global_workflow_config",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_global_config(
    service: ChangeOrderConfigService = Depends(get_config_service),
) -> object:
    """Get the global workflow configuration.

    Returns the global default configuration used by all projects
    that don't have a per-project override.
    """
    config = await service.get_global_config()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No global workflow configuration found. "
            "Use PUT to create the global configuration.",
        )
    return config


@router.put(
    "/global",
    response_model=WorkflowConfigResponse,
    operation_id="upsert_global_workflow_config",
    dependencies=[
        Depends(RoleChecker(required_permission="change-order-workflow-config-manage"))
    ],
)
async def upsert_global_config(
    config_in: WorkflowConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderConfigService = Depends(get_config_service),
) -> object:
    """Create or update the global workflow configuration.

    Requires the change-order-workflow-config-manage permission.
    Uses optimistic locking via the version field.
    """
    try:
        existing = await service.get_global_config()
        if existing is None:
            config = await service.create_global_config(
                actor_id=current_user.user_id,
                impact_levels=[level.model_dump() for level in config_in.impact_levels],
                approval_rules=[rule.model_dump() for rule in config_in.approval_rules],
                sla_rules=[rule.model_dump() for rule in config_in.sla_rules],
                impact_weights=config_in.impact_weights.model_dump(mode="json"),
                score_boundaries=config_in.score_boundaries.model_dump(mode="json"),
                workflow_transitions=(
                    config_in.workflow_transitions.model_dump(mode="json")
                    if config_in.workflow_transitions
                    else None
                ),
                holiday_country_code=config_in.holiday_country_code,
                custom_fields=(
                    [f.model_dump() for f in config_in.custom_fields]
                    if config_in.custom_fields
                    else None
                ),
            )
        else:
            config = await service.update_config(
                config_id=existing.config_id,
                actor_id=current_user.user_id,
                version=existing.version,
                impact_levels=[level.model_dump() for level in config_in.impact_levels],
                approval_rules=[rule.model_dump() for rule in config_in.approval_rules],
                sla_rules=[rule.model_dump() for rule in config_in.sla_rules],
                impact_weights=config_in.impact_weights.model_dump(mode="json"),
                score_boundaries=config_in.score_boundaries.model_dump(mode="json"),
                workflow_transitions=(
                    config_in.workflow_transitions.model_dump(mode="json")
                    if config_in.workflow_transitions
                    else None
                ),
                holiday_country_code=config_in.holiday_country_code,
                custom_fields=(
                    [f.model_dump() for f in config_in.custom_fields]
                    if config_in.custom_fields
                    else None
                ),
            )
        return config
    except ConfigurationConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/projects/{project_id}",
    response_model=WorkflowConfigResponse,
    operation_id="get_project_workflow_config",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_project_config(
    project_id: UUID,
    service: ChangeOrderConfigService = Depends(get_config_service),
) -> object:
    """Get the project-specific workflow configuration override.

    Returns the per-project config if it exists, or 404 if the project
    uses global defaults.
    """
    config = await service.get_project_config(project_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configuration override found for project {project_id}. "
            f"This project uses the global default configuration.",
        )
    return config


@router.put(
    "/projects/{project_id}",
    response_model=WorkflowConfigResponse,
    operation_id="upsert_project_workflow_config",
    dependencies=[
        Depends(
            RoleChecker(required_permission="change-order-workflow-config-override")
        )
    ],
)
async def upsert_project_config(
    project_id: UUID,
    config_in: WorkflowConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderConfigService = Depends(get_config_service),
) -> object:
    """Create or update a project-specific workflow configuration override.

    Requires the change-order-workflow-config-override permission.
    When active, this project will use these settings instead of the global defaults.
    """
    try:
        existing = await service.get_project_config(project_id)
        if existing is None:
            config = await service.create_project_override(
                project_id=project_id,
                actor_id=current_user.user_id,
                impact_levels=[level.model_dump() for level in config_in.impact_levels],
                approval_rules=[rule.model_dump() for rule in config_in.approval_rules],
                sla_rules=[rule.model_dump() for rule in config_in.sla_rules],
                impact_weights=config_in.impact_weights.model_dump(mode="json"),
                score_boundaries=config_in.score_boundaries.model_dump(mode="json"),
                workflow_transitions=(
                    config_in.workflow_transitions.model_dump(mode="json")
                    if config_in.workflow_transitions
                    else None
                ),
                holiday_country_code=config_in.holiday_country_code,
                custom_fields=(
                    [f.model_dump() for f in config_in.custom_fields]
                    if config_in.custom_fields
                    else None
                ),
            )
        else:
            config = await service.update_config(
                config_id=existing.config_id,
                actor_id=current_user.user_id,
                version=existing.version,
                impact_levels=[level.model_dump() for level in config_in.impact_levels],
                approval_rules=[rule.model_dump() for rule in config_in.approval_rules],
                sla_rules=[rule.model_dump() for rule in config_in.sla_rules],
                impact_weights=config_in.impact_weights.model_dump(mode="json"),
                score_boundaries=config_in.score_boundaries.model_dump(mode="json"),
                workflow_transitions=(
                    config_in.workflow_transitions.model_dump(mode="json")
                    if config_in.workflow_transitions
                    else None
                ),
                holiday_country_code=config_in.holiday_country_code,
                custom_fields=(
                    [f.model_dump() for f in config_in.custom_fields]
                    if config_in.custom_fields
                    else None
                ),
            )
        return config
    except ConfigurationConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_project_workflow_config",
    dependencies=[
        Depends(
            RoleChecker(required_permission="change-order-workflow-config-override")
        )
    ],
)
async def delete_project_config(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderConfigService = Depends(get_config_service),
) -> None:
    """Delete a project-specific workflow configuration override.

    Resets the project to use the global default configuration.
    Requires the change-order-workflow-config-override permission.
    """
    try:
        await service.delete_project_override(project_id, current_user.user_id)
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
