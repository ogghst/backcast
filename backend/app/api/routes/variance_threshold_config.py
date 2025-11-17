"""Variance Threshold Configuration API endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import SessionDep, get_current_active_admin
from app.models import (
    Message,
    VarianceThresholdConfig,
    VarianceThresholdConfigCreate,
    VarianceThresholdConfigPublic,
    VarianceThresholdConfigsPublic,
    VarianceThresholdConfigUpdate,
)

router = APIRouter(prefix="/variance-threshold-configs", tags=["admin"])


def _get_variance_threshold_config(
    session: Session, config_id: uuid.UUID
) -> VarianceThresholdConfig:
    """Get variance threshold configuration by ID."""
    config = session.get(VarianceThresholdConfig, config_id)
    if not config:
        raise HTTPException(
            status_code=404, detail="Variance threshold configuration not found"
        )
    return config


@router.get("/", response_model=VarianceThresholdConfigsPublic)
def list_variance_threshold_configs(
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """List all variance threshold configurations (admin only)."""
    statement = select(VarianceThresholdConfig).order_by(
        VarianceThresholdConfig.threshold_type, VarianceThresholdConfig.is_active.desc()
    )
    configs = session.exec(statement).all()

    return VarianceThresholdConfigsPublic(data=configs, count=len(configs))


@router.get("/{config_id}", response_model=VarianceThresholdConfigPublic)
def get_variance_threshold_config(
    config_id: uuid.UUID,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Get a variance threshold configuration by ID (admin only)."""
    config = _get_variance_threshold_config(session, config_id)
    return config


@router.post("/", response_model=VarianceThresholdConfigPublic)
def create_variance_threshold_config(
    config_in: VarianceThresholdConfigCreate,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Create a new variance threshold configuration (admin only).

    If creating an active threshold, any existing active threshold of the same type
    will be deactivated.
    """
    # If creating an active threshold, deactivate existing active one of same type
    if config_in.is_active:
        existing_active = session.exec(
            select(VarianceThresholdConfig).where(
                VarianceThresholdConfig.threshold_type == config_in.threshold_type,
                VarianceThresholdConfig.is_active == True,  # noqa: E712
            )
        ).first()
        if existing_active:
            existing_active.is_active = False
            session.add(existing_active)

    # Create new configuration
    config = VarianceThresholdConfig.model_validate(config_in)
    session.add(config)
    session.commit()
    session.refresh(config)

    return config


@router.put("/{config_id}", response_model=VarianceThresholdConfigPublic)
def update_variance_threshold_config(
    config_id: uuid.UUID,
    config_update: VarianceThresholdConfigUpdate,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Update a variance threshold configuration (admin only).

    If updating to active, any existing active threshold of the same type
    will be deactivated.
    """
    config = _get_variance_threshold_config(session, config_id)

    # If updating to active, deactivate existing active one of same type (if different)
    if config_update.is_active is True and config.is_active is False:
        existing_active = session.exec(
            select(VarianceThresholdConfig).where(
                VarianceThresholdConfig.threshold_type == config.threshold_type,
                VarianceThresholdConfig.is_active == True,  # noqa: E712
                VarianceThresholdConfig.variance_threshold_config_id != config_id,
            )
        ).first()
        if existing_active:
            existing_active.is_active = False
            session.add(existing_active)

    # Update configuration
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    session.add(config)
    session.commit()
    session.refresh(config)

    return config


@router.delete("/{config_id}", response_model=Message)
def delete_variance_threshold_config(
    config_id: uuid.UUID,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
) -> Any:
    """Delete a variance threshold configuration (admin only)."""
    config = _get_variance_threshold_config(session, config_id)
    session.delete(config)
    session.commit()

    return Message(message="Variance threshold configuration deleted successfully")
