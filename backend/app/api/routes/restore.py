"""Restore endpoints for soft-deleted entities."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    ChangeOrder,
    ChangeOrderPublic,
    CostElement,
    CostElementPublic,
    Project,
    ProjectPublic,
    WBEPublic,
)
from app.services.entity_versioning import restore_entity

router = APIRouter(prefix="/restore", tags=["restore"])


@router.post("/projects/{project_id}", response_model=ProjectPublic)
def restore_project(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
) -> Any:
    """
    Restore a soft-deleted project.
    """
    try:
        restored_project = restore_entity(
            session=session,
            entity_class=Project,
            entity_id=project_id,
            entity_type="project",
        )
        session.commit()
        session.refresh(restored_project)
        return restored_project
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/wbes/{wbe_id}", response_model=WBEPublic)
def restore_wbe(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    wbe_id: uuid.UUID,
    branch: str | None = Query(
        default=None, description="Branch name (defaults to 'main')"
    ),
) -> Any:
    """
    Restore a soft-deleted WBE.
    """
    branch_name = branch or "main"
    try:
        restored_wbe = restore_entity(
            session=session,
            entity_class=WBE,
            entity_id=wbe_id,
            entity_type="wbe",
            branch=branch_name,
        )
        session.commit()
        session.refresh(restored_wbe)
        return restored_wbe
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cost-elements/{cost_element_id}", response_model=CostElementPublic)
def restore_cost_element(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: uuid.UUID,
    branch: str | None = Query(
        default=None, description="Branch name (defaults to 'main')"
    ),
) -> Any:
    """
    Restore a soft-deleted cost element.
    """
    branch_name = branch or "main"
    try:
        restored_ce = restore_entity(
            session=session,
            entity_class=CostElement,
            entity_id=cost_element_id,
            entity_type="costelement",
            branch=branch_name,
        )
        session.commit()
        session.refresh(restored_ce)
        return restored_ce
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/change-orders/{change_order_id}", response_model=ChangeOrderPublic)
def restore_change_order(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    change_order_id: uuid.UUID,
) -> Any:
    """
    Restore a soft-deleted change order.
    """
    try:
        restored_co = restore_entity(
            session=session,
            entity_class=ChangeOrder,
            entity_id=change_order_id,
            entity_type="changeorder",
        )
        session.commit()
        session.refresh(restored_co)
        return restored_co
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
