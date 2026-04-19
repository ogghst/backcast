"""Project tools for AI agent.

Migrated from backend/app/ai/tools/__init__.py to use @ai_tool decorator
with LangChain's native docstring parsing for parameter descriptions.
"""

import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import (
    add_project_metadata,
    add_temporal_metadata,
    log_project_context,
    log_temporal_context,
)
from app.ai.tools.types import RiskLevel, ToolContext
from app.core.rbac import inject_rbac_session

logger = logging.getLogger(__name__)


@ai_tool(
    name="list_projects",
    description="List all projects in the system with optional search, status filter, and pagination. Respects temporal context (as_of date, branch, branch_mode) for versioned queries.",
    permissions=["project-read"],
    category="projects",
    risk_level=RiskLevel.LOW,
)
async def list_projects(
    search: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List all projects in the system with filtering and pagination.

    Context: Provides database session and user context for executing the query.
    Filters projects based on user's access level - non-admin users only see
    projects they are members of. Respects temporal context for versioned queries.

    Args:
        search: Optional search term for project code or name
        status: Optional status filter (e.g., 'ACT' for active, 'PLN' for planned)
        skip: Number of records to skip for pagination (default 0)
        limit: Maximum number of records to return (default 20)
        sort_field: Optional field to sort by (e.g., 'name', 'code')
        sort_order: Sort order, either 'asc' or 'desc' (default 'asc')
        context: Injected tool execution context

    Returns:
        Dictionary containing:
            - projects: List of project objects with id, code, name, status, budget, dates
            - total: Total count of projects matching filters
            - skip: Pagination skip value
            - limit: Pagination limit value
            - _temporal_context: Temporal parameters used for the query

    Raises:
        ValueError: If invalid filter parameters are provided
    """
    # Log temporal and project context for observability
    log_temporal_context("list_projects", context)
    log_project_context("list_projects", context)

    # Context is injected by decorator
    try:
        from uuid import UUID

        from app.core.rbac import get_rbac_service

        # Get user's accessible projects
        rbac_service = get_rbac_service()

        # Inject session for project-level access checks
        inject_rbac_session(rbac_service, context.session)

        user_uuid = UUID(context.user_id)

        # Get projects user has access to
        accessible_project_ids = await rbac_service.get_user_projects(
            user_id=user_uuid,
            user_role=context.user_role,
        )

        # Build filter string if status is provided
        filters = f"status:{status}" if status else None

        # Use temporal parameters from context
        from app.core.versioning.enums import BranchMode

        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGE if context.branch_mode == "merged" else BranchMode.STRICT
        )

        # Auto-scope to project if project_id is set in context
        # When in project-scoped chat, automatically filter to that project
        if context.project_id:
            from uuid import UUID

            # Add project_id filter to restrict to current project
            project_uuid = UUID(context.project_id)
            # Only include the specified project in accessible projects
            if project_uuid in accessible_project_ids:
                accessible_project_ids = [project_uuid]
            else:
                # User doesn't have access to the scoped project
                accessible_project_ids = []

        projects, total = await context.project_service.get_projects(
            skip=skip,
            limit=limit,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            branch=branch,
            branch_mode=branch_mode,
            as_of=context.as_of,
        )

        # Filter projects to only include accessible ones
        accessible_projects = [
            p for p in projects if p.project_id in accessible_project_ids
        ]

        # Recalculate total for filtered results
        filtered_total = len(accessible_projects)

        result = {
            "projects": [
                {
                    "id": str(p.project_id),
                    "code": p.code,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "budget": float(p.budget) if p.budget else None,
                    "start_date": p.start_date.isoformat() if p.start_date else None,
                    "end_date": p.end_date.isoformat() if p.end_date else None,
                }
                for p in accessible_projects
            ],
            "total": filtered_total,
            "skip": skip,
            "limit": limit,
        }

        # Add temporal and project metadata to result
        with_project_metadata = add_project_metadata(result, context)
        return add_temporal_metadata(with_project_metadata, context)
    except Exception as e:
        logger.error(f"Error in list_projects: {e}")
        # Add temporal and project metadata even to error responses
        with_project_metadata = add_project_metadata({"error": str(e)}, context)
        return add_temporal_metadata(with_project_metadata, context)


@ai_tool(
    name="get_project",
    description="Get detailed information about a specific project by its ID. Respects temporal context (as_of date, branch, branch_mode) for versioned queries.",
    permissions=["project-read"],
    category="projects",
    risk_level=RiskLevel.LOW,
)
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get detailed information about a specific project.

    Context: Provides database session and user context for retrieving project data.
    Respects temporal context for versioned queries.

    Args:
        project_id: Project ID as UUID string
        context: Injected tool execution context

    Returns:
        Dictionary containing detailed project information:
            - id: Project ID
            - code: Project code
            - name: Project name
            - description: Project description
            - status: Project status code
            - budget: Project budget amount
            - start_date: Project start date (ISO format)
            - end_date: Project end date (ISO format)
            - branch: Git branch for the project
            - _temporal_context: Temporal parameters used for the query

    Raises:
        ValueError: If project_id is not a valid UUID format
        KeyError: If project is not found
    """
    # Log temporal context for observability
    log_temporal_context("get_project", context)

    # Context is injected by decorator
    try:
        from uuid import UUID

        from app.core.versioning.enums import BranchMode

        # Use temporal parameters from context
        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGE if context.branch_mode == "merged" else BranchMode.STRICT
        )

        # Use get_as_of to support temporal queries
        project = await context.project_service.get_as_of(
            entity_id=UUID(project_id),
            as_of=context.as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not project:
            return add_temporal_metadata(
                {"error": f"Project {project_id} not found"}, context
            )

        result = {
            "id": str(project.project_id),
            "code": project.code,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "budget": float(project.budget) if project.budget else None,
            "start_date": project.start_date.isoformat()
            if project.start_date
            else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "branch": project.branch,
        }

        return add_temporal_metadata(result, context)
    except ValueError:
        return add_temporal_metadata(
            {"error": f"Invalid project ID: {project_id}"}, context
        )
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="global_search",
    description="Search across all entity types (projects, WBEs, cost elements, change orders, etc.) for a given query. Returns a flat ranked list with entity type labels. Respects project scoping from session context.",
    permissions=["project-read"],
    category="search",
    risk_level=RiskLevel.LOW,
)
async def global_search(
    query: str,
    project_id: str | None = None,
    wbe_id: str | None = None,
    limit: int = 20,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Search across all entity types for a given query string.

    Returns a flat ranked list of results with entity type labels and relevance
    scores. Respects project scoping from the session context and user RBAC
    permissions.

    Args:
        query: Search string to match against entity codes, names, descriptions, etc.
        project_id: Optional project UUID to scope results to a single project.
        wbe_id: Optional WBE UUID to scope results to a WBE and its descendants.
        limit: Maximum number of results to return (default 20).
        context: Injected tool execution context.

    Returns:
        Dictionary containing:
            - results: List of search result objects with entity_type, id, code, name,
              description, status, relevance_score, project_id, wbe_id
            - total: Number of results returned
            - query: Original query string
            - _temporal_context: Temporal parameters used for the query
    """
    log_temporal_context("global_search", context)
    log_project_context("global_search", context)

    try:
        from uuid import UUID

        from app.core.versioning.enums import BranchMode
        from app.services.global_search_service import GlobalSearchService

        service = GlobalSearchService(context.session)

        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGE if context.branch_mode == "merged" else BranchMode.STRICT
        )

        # Auto-scope to session project if available
        effective_project_id = UUID(project_id) if project_id else None
        if context.project_id and not effective_project_id:
            effective_project_id = UUID(context.project_id)

        effective_wbe_id = UUID(wbe_id) if wbe_id else None

        response = await service.search(
            query,
            user_id=UUID(context.user_id),
            user_role=context.user_role,
            project_id=effective_project_id,
            wbe_id=effective_wbe_id,
            branch=branch,
            branch_mode=branch_mode,
            as_of=context.as_of,
            limit=limit,
        )

        result = response.model_dump()

        with_project_metadata = add_project_metadata(result, context)
        return add_temporal_metadata(with_project_metadata, context)
    except Exception as e:
        logger.error(f"Error in global_search: {e}")
        with_project_metadata = add_project_metadata({"error": str(e)}, context)
        return add_temporal_metadata(with_project_metadata, context)
