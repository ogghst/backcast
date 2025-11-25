"""Hard delete endpoints for permanently removing soft-deleted entities."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep, get_current_active_admin
from app.models import WBE, CostElement, Project
from app.services.entity_versioning import hard_delete_entity

router = APIRouter(prefix="/hard-delete", tags=["hard-delete"])


@router.delete("/projects/{project_id}")
def hard_delete_project(
    *,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
    project_id: uuid.UUID,
) -> dict[str, str]:
    """
    Permanently delete a soft-deleted project (admin only).
    """
    try:
        hard_delete_entity(
            session=session,
            entity_class=Project,
            entity_id=project_id,
            entity_type="project",
        )
        session.commit()
        return {"message": "Project permanently deleted"}
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/wbes/{wbe_id}")
def hard_delete_wbe(
    *,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
    wbe_id: uuid.UUID,
    branch: str | None = Query(
        default=None, description="Branch name (defaults to 'main')"
    ),
) -> dict[str, str]:
    """
    Permanently delete a soft-deleted WBE (admin only).
    """
    branch_name = branch or "main"
    try:
        hard_delete_entity(
            session=session,
            entity_class=WBE,
            entity_id=wbe_id,
            entity_type="wbe",
            branch=branch_name,
        )
        session.commit()
        return {"message": "WBE permanently deleted"}
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/cost-elements/{cost_element_id}")
def hard_delete_cost_element(
    *,
    session: SessionDep,
    _current_user: Annotated[Any, Depends(get_current_active_admin)],
    cost_element_id: uuid.UUID,
    branch: str | None = Query(
        default=None, description="Branch name (defaults to 'main')"
    ),
) -> dict[str, str]:
    """
    Permanently delete a soft-deleted cost element (admin only).
    """
    branch_name = branch or "main"
    try:
        hard_delete_entity(
            session=session,
            entity_class=CostElement,
            entity_id=cost_element_id,
            entity_type="costelement",
            branch=branch_name,
        )
        session.commit()
        return {"message": "Cost element permanently deleted"}
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "not deleted" in str(exc).lower():
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
