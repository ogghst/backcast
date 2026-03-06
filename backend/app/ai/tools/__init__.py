"""AI Tools for natural language queries.

Provides tools that can be used by LangGraph agents.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project import ProjectService

logger = logging.getLogger(__name__)


class ProjectListInput(BaseModel):
    """Input for list_projects tool."""

    search: str | None = Field(None, description="Search term for project code or name")
    status: str | None = Field(
        None, description="Filter by status code (e.g., 'ACT', 'PLN')"
    )
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        20, ge=1, le=100, description="Maximum number of records to return"
    )
    sort_field: str | None = Field(
        None, description="Field to sort by (e.g., 'name', 'code')"
    )
    sort_order: str = Field("asc", description="Sort order (asc or desc)")


class ProjectGetInput(BaseModel):
    """Input for get_project tool."""

    project_id: str = Field(..., description="Project ID as UUID string")


class ToolContext:
    """Context for tool execution with RBAC enforcement."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id
        self.project_service = ProjectService(session)

    async def check_permission(self, permission: str) -> bool:
        """Check if user has the permission."""
        # In a real implementation, this would check against the user's roles
        # For now, we'll just return True for authenticated users
        return True


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

    Returns project information including code, name, status, budget, and dates.
    Supports search, filtering by status, and pagination.

    Returns:
        Dictionary with projects list, total count, and pagination info
    """
    if context is None:
        return {"error": "Tool context not provided"}

    # Check permission
    if not await context.check_permission("project-read"):
        return {"error": "Permission denied: project-read required"}

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


async def get_project(
    project_id: str, context: ToolContext | None = None
) -> dict[str, Any]:
    """Get detailed information about a specific project.

    Args:
        project_id: Project ID as UUID string

    Returns:
        Dictionary with detailed project information
    """
    if context is None:
        return {"error": "Tool context not provided"}

    # Check permission
    if not await context.check_permission("project-read"):
        return {"error": "Permission denied: project-read required"}

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


# LangGraph StructuredTool instances
def create_project_tools(context: ToolContext) -> list[StructuredTool]:
    """Create LangGraph StructuredTool instances for project operations."""

    async def wrapped_list_projects(**kwargs: Any) -> str:
        """Wrapped list_projects that includes context."""
        result = await list_projects(context=context, **kwargs)
        import json

        return json.dumps(result)

    async def wrapped_get_project(**kwargs: Any) -> str:
        """Wrapped get_project that includes context."""
        result = await get_project(context=context, **kwargs)
        import json

        return json.dumps(result)

    return [
        StructuredTool.from_function(
            coroutine=wrapped_list_projects,
            name="list_projects",
            description="List all projects in the system with optional search, status filter, and pagination. "
            "Returns project code, name, status, budget, and dates.",
            args_schema=ProjectListInput,
        ),
        StructuredTool.from_function(
            coroutine=wrapped_get_project,
            name="get_project",
            description="Get detailed information about a specific project by its ID. "
            "Requires the project ID as a UUID string.",
            args_schema=ProjectGetInput,
        ),
    ]


# Export for use in agent
PROJECT_TOOLS: list[Any] = []  # Will be populated at runtime with context
