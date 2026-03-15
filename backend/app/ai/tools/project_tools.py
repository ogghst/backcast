"""Project tools for AI agent.

Migrated from backend/app/ai/tools/__init__.py to use @ai_tool decorator
with LangChain's native docstring parsing for parameter descriptions.
"""

import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


@ai_tool(
    name="list_projects",
    description="List all projects in the system with optional search, status filter, and pagination.",
    permissions=["project-read"],
    category="projects"
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

    Raises:
        ValueError: If invalid filter parameters are provided
    """
    # Context is injected by decorator
    try:
        # Build filter string if status is provided
        filters = f"status:{status}" if status else None

        projects, total = await context.project_service.get_projects(
            skip=skip,
            limit=limit,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            branch="main",
        )

        return {
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
                for p in projects
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error in list_projects: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_project",
    description="Get detailed information about a specific project by its ID.",
    permissions=["project-read"],
    category="projects"
)
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get detailed information about a specific project.

    Context: Provides database session and user context for retrieving project data.

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

    Raises:
        ValueError: If project_id is not a valid UUID format
        KeyError: If project is not found
    """
    # Context is injected by decorator
    try:
        from uuid import UUID

        project = await context.project_service.get_by_id(UUID(project_id))

        if not project:
            return {"error": f"Project {project_id} not found"}

        return {
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
    except ValueError:
        return {"error": f"Invalid project ID: {project_id}"}
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return {"error": str(e)}
