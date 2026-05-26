"""Project and WBE tool template for wrapping service methods.

This template provides AI tools that wrap existing service methods
using the @ai_tool decorator for Project and WBE CRUD operations.

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
from app.models.schemas.wbe import WBECreate, WBEUpdate

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
# WBE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_wbes",
    description="Find WBEs by ID or search/filter.",
    permissions=["wbe-read"],
    category="wbe",
    risk_level=RiskLevel.LOW,
)
async def find_wbes(
    wbe_id: str | None = None,
    project_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find WBEs by ID or search/filter.

    Context: Provides database session and WBE service for querying WBEs.

    Args:
        wbe_id: UUID of a specific WBE to retrieve (returns single WBE)
        project_id: Optional project ID to filter WBEs
        search: Optional search term
        skip: Number of records to skip
        limit: Maximum records to return
        context: Injected tool execution context

    Returns:
        Dictionary with WBE details (if wbe_id) or WBE list and total count

    Raises:
        ValueError: If invalid filter parameters

    Example:
        >>> result = await find_wbes(project_id="...", limit=20)
        >>> print(f"Found {result['total']} WBEs")
    """
    try:
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        # Single WBE lookup by ID
        if wbe_id:
            log_temporal_context("find_wbes", context)

            wbe = await service.get_as_of(
                UUID(wbe_id),
                branch=context.branch_name or "main",
                as_of=context.as_of,
            )

            if not wbe:
                not_found_result = {"error": f"WBE {wbe_id} not found"}
                return add_temporal_metadata(not_found_result, context)

            result = {
                "id": str(wbe.wbe_id),
                "name": wbe.name,
                "code": wbe.code,
                "project_id": str(wbe.project_id),
                "budget": float(wbe.budget)
                if hasattr(wbe, "budget") and wbe.budget
                else None,
                "description": wbe.description
                if hasattr(wbe, "description")
                else None,
            }
            return add_temporal_metadata(result, context)

        # List WBEs with optional filtering
        project_uuid = UUID(project_id) if project_id else None

        wbes, total = await service.get_wbes(
            project_id=project_uuid,
            search=search,
            skip=skip,
            limit=limit,
            branch=context.branch_name or "main",
            as_of=context.as_of,
        )

        return {
            "wbes": [
                {
                    "id": str(w.wbe_id),
                    "name": w.name,
                    "code": w.code,
                    "project_id": str(w.project_id),
                    "budget": float(w.budget)
                    if hasattr(w, "budget") and w.budget
                    else None,
                }
                for w in wbes
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError:
        return {"error": f"Invalid WBE ID: {wbe_id}"}
    except KeyError:
        return {"error": f"WBE {wbe_id} not found"}
    except Exception as e:
        logger.error(f"Error in find_wbes: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_wbe",
    description="Create WBE under a project. Budget is set via cost elements.",
    permissions=["wbe-create"],
    category="wbe",
    risk_level=RiskLevel.HIGH,
)
async def create_wbe(
    project_id: str,
    name: str,
    code: str,
    description: str | None = None,
    parent_wbe_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new WBE.

    Context: Provides database session and WBE service for creating WBEs.

    Args:
        project_id: UUID of the parent project
        name: WBE name
        code: Unique WBE code
        description: Optional description
        parent_wbe_id: Optional UUID of the parent WBE to create as a child
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
        ... )
        >>> print(f"Created WBE with ID: {result['id']}")
    """
    try:
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        # Dedup check: prevent creating duplicate WBEs with same code in same project
        existing = await service.get_by_code(code, UUID(project_id))
        if existing:
            return {
                "error": f"A WBE with code '{code}' already exists in this project "
                f"(ID: {existing.wbe_id}, name: '{existing.name}'). "
                "Use a different code or update the existing WBE.",
                "existing_id": str(existing.wbe_id),
                "existing_name": existing.name,
            }

        # Create schema
        wbe_data = WBECreate(
            project_id=UUID(project_id),
            name=name,
            code=code,
            description=description,
            parent_wbe_id=UUID(parent_wbe_id) if parent_wbe_id else None,
            branch=context.branch_name or "main",
        )

        # Call service method (Use specialized create_wbe method)
        wbe = await service.create_wbe(wbe_data, actor_id=UUID(context.user_id))

        # Convert to AI-friendly format
        return {
            "id": str(wbe.wbe_id),
            "name": wbe.name,
            "code": wbe.code,
            "project_id": str(wbe.project_id),
            "description": wbe.description if hasattr(wbe, "description") else None,
            "parent_wbe_id": str(wbe.parent_wbe_id)
            if hasattr(wbe, "parent_wbe_id") and wbe.parent_wbe_id
            else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_wbe: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_wbe",
    description="Update WBE fields.",
    permissions=["wbe-update"],
    category="wbe",
    risk_level=RiskLevel.HIGH,
)
async def update_wbe(
    wbe_id: str,
    name: str | None = None,
    description: str | None = None,
    revenue_allocation: float | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing WBE.

    Context: Provides database session and WBE service for updating WBEs.

    Args:
        wbe_id: UUID of the WBE to update
        name: New WBE name (optional)
        description: New description (optional)
        revenue_allocation: New revenue allocation as a decimal value (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated WBE details

    Raises:
        ValueError: If wbe_id is invalid or no fields provided
        KeyError: If WBE not found

    Example:
        >>> result = await update_wbe(
        ...     wbe_id="123e4567-e89b-12d3-a456-426614174000",
        ...     name="Updated WBE Name",
        ...     revenue_allocation=0.35
        ... )
        >>> print(f"Updated WBE: {result['name']}")
    """
    try:
        from decimal import Decimal
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        # Build update kwargs with only non-None values to prevent
        # passing null values to the database which violates NOT NULL constraints
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
        update_data = WBEUpdate(**update_kwargs, branch=context.branch_name or "main")

        # Call service method
        wbe = await service.update_wbe(
            wbe_id=UUID(wbe_id),
            wbe_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(wbe.wbe_id),
            "name": wbe.name,
            "code": wbe.code,
            "project_id": str(wbe.project_id),
            "description": wbe.description if hasattr(wbe, "description") else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"WBE {wbe_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_wbe: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_wbe",
    description="Soft-delete WBE and its children.",
    permissions=["wbe-delete"],
    category="wbe",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_wbe(
    wbe_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a WBE and all its children.

    Context: Provides database session and WBE service for deletion.

    Args:
        wbe_id: UUID of the WBE to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If wbe_id is invalid
        KeyError: If WBE not found

    Example:
        >>> result = await delete_wbe("...")
        >>> print(f"Deleted WBE: {result['id']}")
    """
    try:
        from uuid import UUID

        from app.services.wbe import WBEService

        service = WBEService(context.session)

        await service.delete_wbe(
            wbe_id=UUID(wbe_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": wbe_id,
            "message": "WBE deleted (including all child WBEs)",
        }
    except ValueError:
        return {"error": f"Invalid WBE ID: {wbe_id}"}
    except KeyError:
        return {"error": f"WBE {wbe_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_wbe: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH WBE TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_wbes",
    description="Batch create multiple WBEs under the same project. "
    "All items share the parent project_id. Each item provides its own name, code, "
    "and optional description and parent_wbe_id. Pre-validates all codes for duplicates "
    "before creating any. Maximum 50 items per batch.",
    permissions=["wbe-create"],
    category="wbe",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_wbes(
    project_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create WBEs under the same project.

    Args:
        project_id: UUID of the parent project
        items: List of dicts, each with {name, code, description?, parent_wbe_id?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_wbes", context)

    try:
        from uuid import UUID

        from app.models.schemas.wbe import WBECreate
        from app.services.wbe import WBEService

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

        service = WBEService(context.session)
        project_uuid = UUID(project_id)

        # Pre-validate: check all codes against the database
        for code in codes:
            existing = await service.get_by_code(code, project_uuid)
            if existing:
                return add_temporal_metadata(
                    {
                        "error": f"A WBE with code '{code}' already exists in this project "
                        f"(ID: {existing.wbe_id}, name: '{existing.name}'). "
                        "Use a different code or update the existing WBE.",
                        "existing_id": str(existing.wbe_id),
                        "existing_code": code,
                    },
                    context,
                )

        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            wbe_data = WBECreate(
                project_id=project_uuid,
                name=item["name"],
                code=item["code"],
                description=item.get("description"),
                parent_wbe_id=UUID(item["parent_wbe_id"])
                if item.get("parent_wbe_id")
                else None,
                branch=branch,
            )
            wbe = await service.create_wbe(wbe_data, actor_id=actor_id)
            results.append(
                {
                    "id": str(wbe.wbe_id),
                    "name": wbe.name,
                    "code": wbe.code,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} WBEs under project {project_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_create_wbes: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="batch_update_wbes",
    description="Batch update multiple WBEs. Each item must include wbe_id and any "
    "fields to update (name, description, revenue_allocation). "
    "Maximum 50 items per batch.",
    permissions=["wbe-update"],
    category="wbe",
    risk_level=RiskLevel.HIGH,
)
async def batch_update_wbes(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch update WBEs.

    Args:
        items: List of dicts, each with {wbe_id, name?, description?, revenue_allocation?}
        context: Injected tool execution context

    Returns:
        Dictionary with updated items list, total count, and message
    """
    log_temporal_context("batch_update_wbes", context)

    try:
        from decimal import Decimal
        from uuid import UUID

        from app.models.schemas.wbe import WBEUpdate
        from app.services.wbe import WBEService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate wbe_id on each item
        for i, item in enumerate(items):
            if not item.get("wbe_id"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'wbe_id'"},
                    context,
                )

        service = WBEService(context.session)
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
                        "error": f"Item with wbe_id '{item['wbe_id']}' has no fields to update"
                    },
                    context,
                )

            update_data = WBEUpdate(**update_kwargs)

            wbe = await service.update_wbe(
                wbe_id=UUID(item["wbe_id"]),
                wbe_in=update_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(wbe.wbe_id),
                    "name": wbe.name,
                    "code": wbe.code,
                }
            )

        result = {
            "updated": results,
            "total": len(results),
            "message": f"Updated {len(results)} WBEs",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"WBE not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_update_wbes: {e}")
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
