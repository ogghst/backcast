"""Project tools for AI agent.

Migrated from backend/app/ai/tools/__init__.py to use @ai_tool decorator.
"""

import logging
from typing import Any
from uuid import UUID

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


@ai_tool(
    name="list_projects",
    description="List all projects in the system with optional search, status filter, and pagination. "
                "Returns project code, name, status, budget, and dates.",
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
    context: ToolContext | None = None,
) -> dict[str, Any]:
    """List all projects in the system.

    Args:
        search: Search term for project code or name
        status: Filter by status code (e.g., 'ACT', 'PLN')
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., 'name', 'code')
        sort_order: Sort order (asc or desc)
        context: Injected tool execution context

    Returns:
        Dictionary with projects list, total count, skip, and limit
    """
    # Context is validated by decorator
    assert context is not None

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
    description="Get detailed information about a specific project by its ID. "
                "Requires the project ID as a UUID string.",
    permissions=["project-read"],
    category="projects"
)
async def get_project(
    project_id: str,
    context: ToolContext | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific project.

    Args:
        project_id: Project ID as UUID string
        context: Injected tool execution context

    Returns:
        Dictionary with detailed project information
    """
    # Context is validated by decorator
    assert context is not None

    try:
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
