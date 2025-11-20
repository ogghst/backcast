"""App Configuration API endpoints (admin only)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import SessionDep, get_current_active_admin
from app.models import (
    AppConfiguration,
    AppConfigurationCreate,
    AppConfigurationPublic,
    AppConfigurationsPublic,
    AppConfigurationUpdate,
    Message,
)

router = APIRouter(prefix="/app-configuration", tags=["admin"])


def _get_app_configuration(session: Session, config_id: uuid.UUID) -> AppConfiguration:
    """Get app configuration by ID."""
    config = session.get(AppConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="App configuration not found")
    return config


@router.get("/", response_model=AppConfigurationsPublic)
def list_app_configurations(
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """List all app configurations (admin only)."""
    statement = select(AppConfiguration).order_by(
        AppConfiguration.config_key, AppConfiguration.is_active.desc()
    )
    configs = session.exec(statement).all()

    return AppConfigurationsPublic(data=configs, count=len(configs))


@router.get("/{config_id}", response_model=AppConfigurationPublic)
def get_app_configuration(
    config_id: uuid.UUID,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Get an app configuration by ID (admin only)."""
    config = _get_app_configuration(session, config_id)
    return config


@router.post("/", response_model=AppConfigurationPublic)
def create_app_configuration(
    config_in: AppConfigurationCreate,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Create a new app configuration (admin only)."""
    # Check if config_key already exists
    existing = session.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == config_in.config_key
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration with key '{config_in.config_key}' already exists",
        )

    # Create new configuration
    config = AppConfiguration.model_validate(config_in)
    session.add(config)
    session.commit()
    session.refresh(config)

    return config


@router.patch("/{config_id}", response_model=AppConfigurationPublic)
def update_app_configuration(
    config_id: uuid.UUID,
    config_update: AppConfigurationUpdate,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Update an app configuration (admin only)."""
    config = _get_app_configuration(session, config_id)

    # If updating config_key, check for uniqueness
    if (
        config_update.config_key is not None
        and config_update.config_key != config.config_key
    ):
        existing = session.exec(
            select(AppConfiguration).where(
                AppConfiguration.config_key == config_update.config_key,
                AppConfiguration.app_configuration_id != config_id,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Configuration with key '{config_update.config_key}' already exists",
            )

    # Update configuration
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    session.add(config)
    session.commit()
    session.refresh(config)

    return config


@router.delete("/{config_id}", response_model=Message)
def delete_app_configuration(
    config_id: uuid.UUID,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Delete an app configuration (admin only)."""
    config = _get_app_configuration(session, config_id)
    session.delete(config)
    session.commit()

    return Message(message="App configuration deleted successfully")
