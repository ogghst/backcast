"""Global search API route - cross-entity search endpoint."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.search import GlobalSearchResponse
from app.services.global_search_service import GlobalSearchService

router = APIRouter()


def get_global_search_service(
    session: AsyncSession = Depends(get_db),
) -> GlobalSearchService:
    """Dependency to get GlobalSearchService instance."""
    return GlobalSearchService(session)


@router.get(
    "",
    response_model=GlobalSearchResponse,
    operation_id="global_search",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query string"),
    project_id: UUID | None = Query(None, description="Scope results to a specific project"),
    wbe_id: UUID | None = Query(None, description="Scope results to a specific WBE and descendants"),
    branch: str = Query("main", description="Branch name for branchable entities"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: search entities as of this timestamp (ISO 8601)",
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    service: GlobalSearchService = Depends(get_global_search_service),
) -> GlobalSearchResponse:
    """Search across all entity types with ranked results.

    Queries 12 entity types in parallel, applies RBAC project scoping,
    temporal/branch filters, and returns a flat relevance-ranked list.
    """
    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT

    return await service.search(
        q,
        user_id=current_user.user_id,
        user_role=current_user.role,
        project_id=project_id,
        wbe_id=wbe_id,
        branch=branch,
        branch_mode=branch_mode,
        as_of=as_of,
        limit=limit,
    )
