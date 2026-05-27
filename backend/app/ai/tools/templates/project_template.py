"""Project and WBS Element tool template for wrapping service methods.

This template provides AI tools that wrap existing service methods
using the @ai_tool decorator for Project and WBS Element CRUD operations.

Usage:
    1. Import the service methods you want to expose
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format

TEMPORAL CONTEXT PATTERN:
For temporal tools (those that work with versioned entities):
- Import temporal logging helpers: log_temporal_context, add_temporal_metadata
- Call log_temporal_context() at tool start for observability
- Call add_temporal_metadata() on return to include temporal context in results
- Update tool descriptions to mention temporal context enforcement
"""

import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.project import ProjectCreate, ProjectUpdate
from app.models.schemas.wbs_element import WBSElementCreate, WBSElementUpdate

logger = logging.getLogger(__name__)

BATCH_SIZE_LIMIT = 50

# =============================================================================
# PROJECT CRUD TOOLS
# =============================================================================


@ai_tool(
    name="create_project",
    description="Create a new project.",
    permissions=["project-create"],
    category="projects",
    risk_level=RiskLevel.HIGH,
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
        from datetime import datetime
        from uuid import UUID

        service = context.project_service

        # Dedup check: prevent creating duplicate projects with same code
        existing = await service.get_by_code(code)
        if existing:
            return {
                "error": f"A project with code '{code}' already exists "
                f"(ID: {existing.project_id}, name: '{existing.name}'). "
                "Use update_project instead if you want to modify it, "
                "or use a different code.",
                "existing_id": str(existing.project_id),
                "existing_name": existing.name,
            }

        # Create Pydantic schema for service call
        project_data = ProjectCreate(
            name=name,
            code=code,
            description=description,
            budget=budget,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None,
            branch=context.branch_name or "main",
        )

        # Call service method (Entity-specific method handles EVCS root_id)
        project = await service.create_project(
            project_data, actor_id=UUID(context.user_id)
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
    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_project",
    description="Update project fields. Provide all changes in one call.",
    permissions=["project-update"],
    category="projects",
    risk_level=RiskLevel.HIGH,
)
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing project.

    Context: Provides database session and project service for updating projects.

    Args:
        project_id: UUID of the project to update
        name: New project name (optional)
        description: New description (optional)
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
        >>> print(f"Updated project: {result['name']}")
    """
    try:
        from uuid import UUID

        service = context.project_service

        # Build update kwargs with only non-None values to prevent
        # passing null values to the database which violates NOT NULL constraints
        update_kwargs: dict[str, object] = {}
        if name is not None:
            update_kwargs["name"] = name
        if description is not None:
            update_kwargs["description"] = description
        if status is not None:
            update_kwargs["status"] = status

        if not update_kwargs:
            return {"error": "No fields provided for update"}

        # Create update schema with only provided fields
        update_data = ProjectUpdate(
            **update_kwargs, branch=context.branch_name or "main"
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


@ai_tool(
    name="delete_project",
    description="Soft-delete a project.",
    permissions=["project-delete"],
    category="projects",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a project.

    Context: Provides database session and project service for deletion.

    Args:
        project_id: UUID of the project to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If project_id is invalid
        KeyError: If project not found

    Example:
        >>> result = await delete_project("...")
        >>> print(f"Deleted project: {result['id']}")
    """
    try:
        from uuid import UUID

        service = context.project_service

        await service.delete_project(
            project_id=UUID(project_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": project_id,
            "message": "Project deleted",
        }
    except ValueError:
        return {"error": f"Invalid project ID: {project_id}"}
    except KeyError:
        return {"error": f"Project {project_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_project: {e}")
        return {"error": str(e)}


# =============================================================================
# WBS ELEMENT CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_wbs_elements",
    description="Find WBS Elements by ID or search/filter.",
    permissions=["wbs-element-read"],
    category="wbs-elements",
    risk_level=RiskLevel.LOW,
)
async def find_wbs_elements(
    wbs_element_id: str | None = None,
    project_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find WBS Elements by ID or search/filter.

    Context: Provides database session and WBS Element service for querying.

    Args:
        wbs_element_id: UUID of a specific WBS Element to retrieve (returns single)
        project_id: Optional project ID to filter WBS Elements
        search: Optional search term
        skip: Number of records to skip
        limit: Maximum records to return
        context: Injected tool execution context

    Returns:
        Dictionary with WBS Element details (if wbs_element_id) or list and total count

    Raises:
        ValueError: If invalid filter parameters

    Example:
        >>> result = await find_wbs_elements(project_id="...", limit=20)
        >>> print(f"Found {result['total']} WBS Elements")
    """
    try:
        from uuid import UUID

        from app.services.wbs_element_service import WBSElementService

        service = WBSElementService(context.session)

        # Single WBS Element lookup by ID
        if wbs_element_id:
            log_temporal_context("find_wbs_elements", context)

            wbs = await service.get_as_of(
                UUID(wbs_element_id),
                branch=context.branch_name or "main",
                as_of=context.as_of,
            )

            if not wbs:
                not_found_result = {"error": f"WBS Element {wbs_element_id} not found"}
                return add_temporal_metadata(not_found_result, context)

            result = {
                "id": str(wbs.wbs_element_id),
                "name": wbs.name,
                "code": wbs.code,
                "project_id": str(wbs.project_id),
                "budget_allocation": float(wbs.budget_allocation)
                if hasattr(wbs, "budget_allocation") and wbs.budget_allocation
                else None,
                "description": wbs.description if hasattr(wbs, "description") else None,
            }
            return add_temporal_metadata(result, context)

        # List WBS Elements with optional filtering
        project_uuid = UUID(project_id) if project_id else None

        wbs_elements, total = await service.get_wbs_elements(
            project_id=project_uuid,
            search=search,
            skip=skip,
            limit=limit,
            branch=context.branch_name or "main",
            as_of=context.as_of,
        )

        return {
            "wbs_elements": [
                {
                    "id": str(w.wbs_element_id),
                    "name": w.name,
                    "code": w.code,
                    "project_id": str(w.project_id),
                    "budget_allocation": float(w.budget_allocation)
                    if hasattr(w, "budget_allocation") and w.budget_allocation
                    else None,
                }
                for w in wbs_elements
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError:
        return {"error": f"Invalid WBS Element ID: {wbs_element_id}"}
    except KeyError:
        return {"error": f"WBS Element {wbs_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in find_wbs_elements: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_wbs_element",
    description="Create WBS Element under a project. Budget is computed from work packages.",
    permissions=["wbs-element-create"],
    category="wbs-elements",
    risk_level=RiskLevel.HIGH,
)
async def create_wbs_element(
    project_id: str,
    name: str,
    code: str,
    description: str | None = None,
    parent_wbs_element_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new WBS Element.

    Context: Provides database session and WBS Element service for creating.

    Args:
        project_id: UUID of the parent project
        name: WBS Element name
        code: Unique WBS Element code
        description: Optional description
        parent_wbs_element_id: Optional UUID of the parent WBS Element to create as a child
        context: Injected tool execution context

    Returns:
        Dictionary with created WBS Element details

    Raises:
        ValueError: If invalid input or duplicate code

    Example:
        >>> result = await create_wbs_element(
        ...     project_id="...",
        ...     name="Mechanical Assembly",
        ...     code="1.2",
        ... )
        >>> print(f"Created WBS Element with ID: {result['id']}")
    """
    try:
        from uuid import UUID

        from app.services.wbs_element_service import WBSElementService

        service = WBSElementService(context.session)

        # Dedup check: prevent creating duplicate WBS Elements with same code
        existing = await service.get_by_code(code, UUID(project_id))
        if existing:
            return {
                "error": f"A WBS Element with code '{code}' already exists in this project "
                f"(ID: {existing.wbs_element_id}, name: '{existing.name}'). "
                "Use a different code or update the existing WBS Element.",
                "existing_id": str(existing.wbs_element_id),
                "existing_name": existing.name,
            }

        # Create schema
        wbs_data = WBSElementCreate(
            project_id=UUID(project_id),
            name=name,
            code=code,
            description=description,
            parent_wbs_element_id=UUID(parent_wbs_element_id)
            if parent_wbs_element_id
            else None,
            branch=context.branch_name or "main",
        )

        # Call service method
        wbs = await service.create_wbe(wbs_data, actor_id=UUID(context.user_id))

        # Convert to AI-friendly format
        return {
            "id": str(wbs.wbs_element_id),
            "name": wbs.name,
            "code": wbs.code,
            "project_id": str(wbs.project_id),
            "description": wbs.description if hasattr(wbs, "description") else None,
            "parent_wbs_element_id": str(wbs.parent_wbs_element_id)
            if hasattr(wbs, "parent_wbs_element_id") and wbs.parent_wbs_element_id
            else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_wbs_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_wbs_element",
    description="Update WBS Element fields.",
    permissions=["wbs-element-update"],
    category="wbs-elements",
    risk_level=RiskLevel.HIGH,
)
async def update_wbs_element(
    wbs_element_id: str,
    name: str | None = None,
    description: str | None = None,
    revenue_allocation: float | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing WBS Element.

    Context: Provides database session and WBS Element service for updating.

    Args:
        wbs_element_id: UUID of the WBS Element to update
        name: New name (optional)
        description: New description (optional)
        revenue_allocation: New revenue allocation as a decimal value (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated WBS Element details

    Raises:
        ValueError: If wbs_element_id is invalid or no fields provided
        KeyError: If WBS Element not found

    Example:
        >>> result = await update_wbs_element(
        ...     wbs_element_id="123e4567-e89b-12d3-a456-426614174000",
        ...     name="Updated Name",
        ...     revenue_allocation=0.35
        ... )
        >>> print(f"Updated WBS Element: {result['name']}")
    """
    try:
        from decimal import Decimal
        from uuid import UUID

        from app.services.wbs_element_service import WBSElementService

        service = WBSElementService(context.session)

        # Build update kwargs with only non-None values
        update_kwargs: dict[str, object] = {}
        if name is not None:
            update_kwargs["name"] = name
        if description is not None:
            update_kwargs["description"] = description
        if revenue_allocation is not None:
            update_kwargs["revenue_allocation"] = Decimal(str(revenue_allocation))

        if not update_kwargs:
            return {"error": "No fields provided for update"}

        # Create update schema with only provided fields
        update_data = WBSElementUpdate(
            **update_kwargs, branch=context.branch_name or "main"
        )

        # Call service method
        wbs = await service.update_wbe(
            wbe_id=UUID(wbs_element_id),
            wbe_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(wbs.wbs_element_id),
            "name": wbs.name,
            "code": wbs.code,
            "project_id": str(wbs.project_id),
            "description": wbs.description if hasattr(wbs, "description") else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"WBS Element {wbs_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_wbs_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_wbs_element",
    description="Soft-delete WBS Element and its children.",
    permissions=["wbs-element-delete"],
    category="wbs-elements",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_wbs_element(
    wbs_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a WBS Element and all its children.

    Context: Provides database session and WBS Element service for deletion.

    Args:
        wbs_element_id: UUID of the WBS Element to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If wbs_element_id is invalid
        KeyError: If WBS Element not found

    Example:
        >>> result = await delete_wbs_element("...")
        >>> print(f"Deleted WBS Element: {result['id']}")
    """
    try:
        from uuid import UUID

        from app.services.wbs_element_service import WBSElementService

        service = WBSElementService(context.session)

        await service.delete_wbe(
            wbe_id=UUID(wbs_element_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": wbs_element_id,
            "message": "WBS Element deleted (including all child elements)",
        }
    except ValueError:
        return {"error": f"Invalid WBS Element ID: {wbs_element_id}"}
    except KeyError:
        return {"error": f"WBS Element {wbs_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_wbs_element: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH WBS ELEMENT TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_wbs_elements",
    description="Batch create multiple WBS Elements under the same project. "
    "All items share the parent project_id. Each item provides its own name, code, "
    "and optional description and parent_wbs_element_id. Pre-validates all codes for "
    "duplicates before creating any. Maximum 50 items per batch.",
    permissions=["wbs-element-create"],
    category="wbs-elements",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_wbs_elements(
    project_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create WBS Elements under the same project.

    Args:
        project_id: UUID of the parent project
        items: List of dicts, each with {name, code, description?, parent_wbs_element_id?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_wbs_elements", context)

    try:
        from uuid import UUID

        from app.models.schemas.wbs_element import WBSElementCreate
        from app.services.wbs_element_service import WBSElementService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("code"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'code'"},
                    context,
                )
            if not item.get("name"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'name'"},
                    context,
                )

        # Check for duplicate codes within the batch
        codes = [it["code"] for it in items]
        if len(codes) != len(set(codes)):
            dupes = {c for c in codes if codes.count(c) > 1}
            return add_temporal_metadata(
                {"error": f"Duplicate codes in batch: {dupes}"}, context
            )

        service = WBSElementService(context.session)
        project_uuid = UUID(project_id)

        # Pre-validate: check all codes against the database
        for code in codes:
            existing = await service.get_by_code(code, project_uuid)
            if existing:
                return add_temporal_metadata(
                    {
                        "error": f"A WBS Element with code '{code}' already exists in this project "
                        f"(ID: {existing.wbs_element_id}, name: '{existing.name}'). "
                        "Use a different code or update the existing WBS Element.",
                        "existing_id": str(existing.wbs_element_id),
                        "existing_code": code,
                    },
                    context,
                )

        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            wbs_data = WBSElementCreate(
                project_id=project_uuid,
                name=item["name"],
                code=item["code"],
                description=item.get("description"),
                parent_wbs_element_id=UUID(item["parent_wbs_element_id"])
                if item.get("parent_wbs_element_id")
                else None,
                branch=branch,
            )
            wbs = await service.create_wbe(wbs_data, actor_id=actor_id)
            results.append(
                {
                    "id": str(wbs.wbs_element_id),
                    "name": wbs.name,
                    "code": wbs.code,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} WBS Elements under project {project_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_create_wbs_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="batch_update_wbs_elements",
    description="Batch update multiple WBS Elements. Each item must include wbs_element_id "
    "and any fields to update (name, description, revenue_allocation). "
    "Maximum 50 items per batch.",
    permissions=["wbs-element-update"],
    category="wbs-elements",
    risk_level=RiskLevel.HIGH,
)
async def batch_update_wbs_elements(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch update WBS Elements.

    Args:
        items: List of dicts, each with {wbs_element_id, name?, description?, revenue_allocation?}
        context: Injected tool execution context

    Returns:
        Dictionary with updated items list, total count, and message
    """
    log_temporal_context("batch_update_wbs_elements", context)

    try:
        from decimal import Decimal
        from uuid import UUID

        from app.models.schemas.wbs_element import WBSElementUpdate
        from app.services.wbs_element_service import WBSElementService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate wbs_element_id on each item
        for i, item in enumerate(items):
            if not item.get("wbs_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'wbs_element_id'"
                    },
                    context,
                )

        service = WBSElementService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            update_kwargs: dict[str, Any] = {"branch": branch}
            if "name" in item and item["name"] is not None:
                update_kwargs["name"] = item["name"]
            if "description" in item and item["description"] is not None:
                update_kwargs["description"] = item["description"]
            if "revenue_allocation" in item and item["revenue_allocation"] is not None:
                update_kwargs["revenue_allocation"] = Decimal(
                    str(item["revenue_allocation"])
                )

            if len(update_kwargs) == 1:  # Only branch, no actual fields
                return add_temporal_metadata(
                    {
                        "error": f"Item with wbs_element_id '{item['wbs_element_id']}' has no fields to update"
                    },
                    context,
                )

            update_data = WBSElementUpdate(**update_kwargs)

            wbs = await service.update_wbe(
                wbe_id=UUID(item["wbs_element_id"]),
                wbe_in=update_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(wbs.wbs_element_id),
                    "name": wbs.name,
                    "code": wbs.code,
                }
            )

        result = {
            "updated": results,
            "total": len(results),
            "message": f"Updated {len(results)} WBS Elements",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"WBS Element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_update_wbs_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


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
