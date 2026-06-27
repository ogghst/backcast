"""Global search API route - cross-entity search endpoint."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
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
    q: str = Query(
        ..., min_length=1, max_length=200, description="Search query string"
    ),
    project_id: UUID | None = Query(
        None, description="Scope results to a specific project"
    ),
    wbs_element_id: UUID | None = Query(
        None, description="Scope results to a specific WBSElement and descendants"
    ),
    branch: str = Query("main", description="Branch name for branchable entities"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: search entities as of this timestamp (ISO 8601)",
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    current_user: UserIdentity = Depends(get_current_user),
    service: GlobalSearchService = Depends(get_global_search_service),
) -> GlobalSearchResponse:
    """Search across all entity types with ranked results.

    Queries 13 entity types sequentially, applies RBAC project scoping,
    temporal/branch filters, and returns a flat relevance-ranked list.
    """

    return await service.search(
        q,
        user_id=current_user.user_id,
        project_id=project_id,
        wbe_id=wbs_element_id,
        branch=branch,
        branch_mode=branch_mode,
        as_of=as_of,
        limit=limit,
        search_mode="ui",
    )
