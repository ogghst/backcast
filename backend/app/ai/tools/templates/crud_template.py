"""CRUD tool template for wrapping service methods.

This template shows how to create AI tools that wrap existing service methods
using the @ai_tool decorator. The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

This ensures:
- Single source of truth for business logic
- Consistent behavior across REST API and AI tools
- Automatic RBAC enforcement
- Centralized error handling

NOTE: This is a TEMPLATE with simplified examples for documentation purposes.
The examples use type: ignore comments to avoid MyPy errors because they are
simplified patterns, not production-ready implementations. When creating actual
tools, you should match the exact signatures of your service methods.

Usage:
    1. Import the service methods you want to expose
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format
"""

import logging
from typing import Annotated, Any

from langchain_core.tools import BaseTool, InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext
from app.models.schemas.project import ProjectCreate, ProjectUpdate
from app.models.schemas.wbe import WBECreate

logger = logging.getLogger(__name__)

# =============================================================================
# PROJECT CRUD TOOLS
# =============================================================================

@ai_tool(
    name="list_projects",
    description="List all projects with optional search, filtering, and pagination. "
    "Returns a list of projects with their IDs, names, codes, and metadata.",
    permissions=["project-read"],
    category="projects",
)
async def list_projects(
    search: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List and search projects.

    Context: Provides database session and project service for querying projects.

    Args:
        search: Optional search term to filter projects by name or code
        status: Optional status filter (e.g., "Active", "On Hold")
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., "name", "code", "budget")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - projects: List of project objects
        - total: Total number of projects matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned

    Raises:
        ValueError: If invalid filter parameters are provided

    Example:
        >>> result = await list_projects(search="Alpha", limit=10)
        >>> print(f"Found {result['total']} projects")
        >>> for project in result['projects']:
        ...     print(f"- {project['name']} ({project['code']})")
    """
    try:
        # Use ProjectService from context
        service = context.project_service

        # Call service method (business logic is in the service)
        projects, total = await service.get_projects(
            search=search,
            skip=skip,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        # Convert to AI-friendly format
        return {
            "projects": [
                {
                    "id": str(p.project_id),
                    "name": p.name,
                    "code": p.code,
                    "description": p.description,
                    "status": p.status,
                    "budget": float(p.budget) if p.budget else None,
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
    description="Get detailed information about a specific project by ID. "
    "Returns full project details including budget, status, and metadata.",
    permissions=["project-read"],
    category="projects",
)
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single project by ID.

    Context: Provides database session and project service for retrieving project data.

    Args:
        project_id: UUID of the project to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with project details or error if not found

    Raises:
        ValueError: If project_id is not a valid UUID format
        KeyError: If project is not found

    Example:
        >>> result = await get_project("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"Project: {result['name']}")
        ...     print(f"Budget: ${result['budget']}")
    """
    try:
        from uuid import UUID

        service = context.project_service

        # Call service method
        project = await service.get_by_id(UUID(project_id))

        if not project:
            return {"error": f"Project {project_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(project.project_id),
            "name": project.name,
            "code": project.code,
            "description": project.description,
            "status": project.status,
            "budget": float(project.budget) if project.budget else None,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
        }
    except ValueError:
        return {"error": f"Invalid project ID: {project_id}"}
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_project",
    description="Create a new project with the provided details. "
    "Returns the created project with its assigned ID.",
    permissions=["project-create"],
    category="projects",
)
async def create_project(
    name: str,
    code: str,
    description: str | None = None,
    budget: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new project.

    Context: Provides database session and project service for creating projects.

    Args:
        name: Project name
        code: Unique project code
        description: Optional project description
        budget: Optional project budget
        start_date: Optional start date (ISO format string)
        end_date: Optional end date (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with created project details

    Raises:
        ValueError: If invalid date format or duplicate code

    Example:
        >>> result = await create_project(
        ...     name="Automation Line 1",
        ...     code="AL-001",
        ...     budget=500000.00
        ... )
        >>> print(f"Created project with ID: {result['id']}")
    """
    try:
        from uuid import UUID
        from datetime import datetime

        service = context.project_service

        # Create Pydantic schema for service call
        project_data = ProjectCreate(
            name=name,
            code=code,
            description=description,
            budget=budget,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None,
        )

        # Call service method (Entity-specific method handles EVCS root_id)
        project = await service.create_project(project_data, actor_id=UUID(context.user_id))

        # Convert to AI-friendly format
        return {
            "id": str(project.project_id),
            "name": project.name,
            "code": project.code,
            "description": project.description,
            "status": project.status,
            "budget": float(project.budget) if project.budget else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_project",
    description="Update an existing project with new information. "
    "Only updates fields that are provided.",
    permissions=["project-update"],
    category="projects",
)
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    budget: float | None = None,
    status: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing project.

    Context: Provides database session and project service for updating projects.

    Args:
        project_id: UUID of the project to update
        name: New project name (optional)
        description: New description (optional)
        budget: New budget (optional)
        status: New status (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated project details

    Raises:
        ValueError: If project_id is invalid or no fields provided
        KeyError: If project not found

    Example:
        >>> result = await update_project(
        ...     project_id="123e4567-e89b-12d3-a456-426614174000",
        ...     budget=600000.00,
        ...     status="Active"
        ... )
        >>> print(f"Updated project budget to: ${result['budget']}")
    """
    try:
        from uuid import UUID

        service = context.project_service

        # Create update schema with only provided fields
        update_data = ProjectUpdate(
            name=name,
            description=description,
            budget=budget,
            status=status,
        )

        # Call service method
        project = await service.update_project(
            project_id=UUID(project_id),
            project_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(project.project_id),
            "name": project.name,
            "code": project.code,
            "description": project.description,
            "status": project.status,
            "budget": float(project.budget) if project.budget else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Project {project_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_project: {e}")
        return {"error": str(e)}


# =============================================================================
# WBE CRUD TOOLS
# =============================================================================

@ai_tool(
    name="list_wbes",
    description="List all Work Breakdown Elements (WBEs) with optional filtering. "
    "WBEs represent the hierarchical breakdown of project work.",
    permissions=["wbe-read"],
    category="wbe",
)
async def list_wbes(
    project_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List WBEs with optional filtering.

    Context: Provides database session and WBE service for querying WBEs.

    Args:
        project_id: Optional project ID to filter WBEs
        search: Optional search term
        skip: Number of records to skip
        limit: Maximum records to return
        context: Injected tool execution context

    Returns:
        Dictionary with WBE list and total count

    Raises:
        ValueError: If invalid filter parameters

    Example:
        >>> result = await list_wbes(project_id="...", limit=20)
        >>> print(f"Found {result['total']} WBEs")
    """
    try:
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        # Convert project_id to UUID if provided
        project_uuid = UUID(project_id) if project_id else None

        # Call service method
        wbes, total = await service.get_wbes(
            project_id=project_uuid,
            search=search,
            skip=skip,
            limit=limit,
        )

        # Convert to AI-friendly format
        return {
            "wbes": [
                {
                    "id": str(w.wbe_id),
                    "name": w.name,
                    "code": w.code,
                    "project_id": str(w.project_id),
                    "budget": float(w.budget) if hasattr(w, 'budget') and w.budget else None,
                }
                for w in wbes
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in list_wbes: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_wbe",
    description="Get detailed information about a specific Work Breakdown Element (WBE).",
    permissions=["wbe-read"],
    category="wbe",
)
async def get_wbe(
    wbe_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single WBE by ID.

    Context: Provides database session and WBE service for retrieving WBE data.

    Args:
        wbe_id: UUID of the WBE to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with WBE details

    Raises:
        ValueError: If wbe_id is not a valid UUID format
        KeyError: If WBE not found

    Example:
        >>> result = await get_wbe("123e4567-e89b-12d3-a456-426614174000")
        >>> print(f"WBE: {result['name']} - Budget: ${result['budget']}")
    """
    try:
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        # Call service method
        wbe = await service.get_by_id(UUID(wbe_id))

        if not wbe:
            return {"error": f"WBE {wbe_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(wbe.wbe_id),
            "name": wbe.name,
            "code": wbe.code,
            "project_id": str(wbe.project_id),
            "budget": float(wbe.budget) if hasattr(wbe, 'budget') and wbe.budget else None,
            "description": wbe.description if hasattr(wbe, 'description') else None,
        }
    except ValueError:
        return {"error": f"Invalid WBE ID: {wbe_id}"}
    except KeyError:
        return {"error": f"WBE {wbe_id} not found"}
    except Exception as e:
        logger.error(f"Error in get_wbe: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_wbe",
    description="Create a new Work Breakdown Element (WBE) under a project.",
    permissions=["wbe-create"],
    category="wbe",
)
async def create_wbe(
    project_id: str,
    name: str,
    code: str,
    budget: float | None = None,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new WBE.

    Context: Provides database session and WBE service for creating WBEs.

    Args:
        project_id: UUID of the parent project
        name: WBE name
        code: Unique WBE code
        budget: Optional budget allocation
        description: Optional description
        context: Injected tool execution context

    Returns:
        Dictionary with created WBE details

    Raises:
        ValueError: If invalid input or duplicate code

    Example:
        >>> result = await create_wbe(
        ...     project_id="...",
        ...     name="Mechanical Assembly",
        ...     code="WBE-001",
        ...     budget=100000.00
        ... )
        >>> print(f"Created WBE with ID: {result['id']}")
    """
    try:
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        # Create schema
        wbe_data = WBECreate(
            project_id=UUID(project_id),
            name=name,
            code=code,
            budget=budget,
            description=description,
        )

        # Call service method (Use specialized create_wbe method)
        wbe = await service.create_wbe(wbe_data, actor_id=UUID(context.user_id))

        # Convert to AI-friendly format
        return {
            "id": str(wbe.wbe_id),
            "name": wbe.name,
            "code": wbe.code,
            "project_id": str(wbe.project_id),
            "budget": float(wbe.budget) if hasattr(wbe, 'budget') and wbe.budget else None,
            "description": wbe.description if hasattr(wbe, 'description') else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_wbe: {e}")
        return {"error": str(e)}


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
KEY PRINCIPLES FOR CREATING AI TOOLS:

1. WRAP, DON'T DUPLICATE:
   - Always wrap existing service methods
   - Never duplicate business logic
   - Service methods are the single source of truth

2. USE @ai_tool DECORATOR:
   - Provides automatic RBAC checking
   - Handles errors consistently
   - Logs tool execution
   - Generates tool metadata

3. INJECT DEPENDENCIES:
   - Use ToolContext for database session
   - Access services through context
   - Don't create new service instances

4. AI-FRIENDLY OUTPUT:
   - Convert domain objects to dictionaries
   - Use simple types (str, int, float, bool)
   - Include human-readable error messages
   - Provide clear examples in docstrings

5. PROPER PERMISSIONS:
   - Map tool permissions to service permissions
   - Use specific permissions (e.g., "project-read", "project-create")
   - Document permission requirements

6. CATEGORIZATION:
   - Group related tools by category
   - Use descriptive tool names
   - Provide clear descriptions for LLM

EXAMPLE WORKFLOW:
    1. Identify service method to wrap
    2. Determine required permissions
    3. Create tool with @ai_tool decorator
    4. Implement wrapper that calls service
    5. Convert result to AI-friendly format
    6. Test with example calls

TESTING:
    - Test tool with mock context
    - Verify service method is called
    - Check RBAC enforcement
    - Validate output format
    - Test error handling
"""
