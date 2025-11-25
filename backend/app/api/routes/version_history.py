"""Version history endpoints for retrieving entity version history."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.services.version_history_service import get_version_history

router = APIRouter(prefix="/version-history", tags=["version-history"])


@router.get("/{entity_type}/{entity_id}")
def get_entity_version_history(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    entity_type: str,
    entity_id: uuid.UUID,
    branch: str | None = Query(
        default=None, description="Branch name (required for branch-enabled entities)"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    """
    Get version history for an entity.

    Returns all versions of the entity ordered by version number (newest first).
    For branch-enabled entities (WBE, CostElement), branch parameter is required.
    """
    try:
        history = get_version_history(
            session=session,
            entity_type=entity_type,
            entity_id=entity_id,
            branch=branch,
            skip=skip,
            limit=limit,
        )
        return {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "branch": branch,
            "count": len(history),
            "versions": history,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
