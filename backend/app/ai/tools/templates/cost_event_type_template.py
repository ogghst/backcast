"""Cost Event Type tool template for wrapping CostEventTypeService methods.

This template provides AI tools for cost event type management. The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Cost Event Types in Backcast:
- Cost Event Types are configurable event categories
- They are VERSIONABLE but NOT BRANCHABLE (organizational data, not project-specific)
- Admins can configure available types with code, name, color, and description
- Used for consistent cost event categorization across projects

Usage:
    1. Import CostEventTypeService methods
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format
"""

import logging
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.templates._pagination import (
    BATCH_SIZE_LIMIT,
    calc_page_count,
    get_page_limit,
)
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.cost_event_type import CostEventTypeCreate, CostEventTypeUpdate

logger = logging.getLogger(__name__)


# =============================================================================
# COST EVENT TYPE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_cost_event_types",
    description="Find cost event types by ID or search. Results are paginated; response includes total count, page, and page_count.",
    permissions=["cost-event-type-read"],
    category="cost-management",
    risk_level=RiskLevel.LOW,
)
async def find_cost_event_types(
    cost_event_type_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost event types by ID or search.

    Context: Provides database session and cost event type service for querying.

    Args:
        cost_event_type_id: UUID of a specific cost event type to retrieve (returns single)
        search: Optional search term for code or name
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        context: Injected tool execution context

    Returns:
        Single cost event type dict if cost_event_type_id provided, otherwise list result.

    Raises:
        ValueError: If cost_event_type_id is not a valid UUID format
    """
    limit = get_page_limit(limit)
    skip = (page - 1) * limit
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        service = CostEventTypeService(context.session)

        # Single cost event type lookup
        if cost_event_type_id:
            cost_event_type = await service.get_by_id(UUID(cost_event_type_id))

            if not cost_event_type:
                return {"error": f"Cost event type {cost_event_type_id} not found"}

            return {
                "id": str(cost_event_type.cost_event_type_id),
                "code": cost_event_type.code,
                "name": cost_event_type.name,
                "color": cost_event_type.color,
                "description": cost_event_type.description,
            }

        # List cost event types
        cost_event_types, total = await service.get_cost_event_types(
            search=search,
            skip=skip,
            limit=limit,
        )

        return {
            "cost_event_types": [
                {
                    "id": str(cet.cost_event_type_id),
                    "code": cet.code,
                    "name": cet.name,
                    "color": cet.color,
                    "description": cet.description,
                }
                for cet in cost_event_types
            ],
            "total": total,
            "page": page,
            "page_count": calc_page_count(total, limit),
            "limit": limit,
            "has_more": page < calc_page_count(total, limit),
        }
    except ValueError:
        return {"error": f"Invalid cost event type ID: {cost_event_type_id}"}
    except Exception as e:
        logger.error(f"Error in find_cost_event_types: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_cost_event_type",
    description="Create a new cost event type.",
    permissions=["cost-event-type-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_event_type(
    code: str,
    name: str,
    color: str = "blue",
    is_quality: bool = False,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost event type.

    Context: Provides database session and cost event type service for creating.

    Args:
        code: Unique type code (e.g., "quality_impact")
        name: Display name (e.g., "Quality Impact")
        color: Ant Design color name (e.g., "red", "blue")
        is_quality: Whether this type contributes to COQ metrics (default: False)
        description: Optional description
        context: Injected tool execution context

    Returns:
        Dictionary with created cost event type details

    Raises:
        ValueError: If invalid input or duplicate code

    Example:
        >>> result = await create_cost_event_type(
        ...     code="quality_impact",
        ...     name="Quality Impact",
        ...     color="red",
        ...     is_quality=True,
        ...     description="Quality-related cost events"
        ... )
        >>> print(f"Created cost event type with ID: {result['id']}")
    """
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        service = CostEventTypeService(context.session)

        # Create Pydantic schema
        type_data = CostEventTypeCreate(
            code=code,
            name=name,
            color=color,
            is_quality=is_quality,
            description=description,
        )

        # Call service method
        cost_event_type = await service.create(
            type_in=type_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(cost_event_type.cost_event_type_id),
            "code": cost_event_type.code,
            "name": cost_event_type.name,
            "color": cost_event_type.color,
            "description": cost_event_type.description,
            "message": "Cost event type created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_cost_event_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_cost_event_type",
    description="Update cost event type fields.",
    permissions=["cost-event-type-update"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_event_type(
    cost_event_type_id: str,
    code: str | None = None,
    name: str | None = None,
    color: str | None = None,
    is_quality: bool | None = None,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost event type.

    Context: Provides database session and cost event type service for updating.

    Args:
        cost_event_type_id: UUID of the cost event type to update
        code: New code (optional)
        name: New name (optional)
        color: New color (optional)
        is_quality: Whether this type contributes to COQ metrics (optional)
        description: New description (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost event type details

    Raises:
        ValueError: If cost_event_type_id is invalid or no fields provided
        KeyError: If cost event type not found

    Example:
        >>> result = await update_cost_event_type(
        ...     cost_event_type_id="...",
        ...     name="Updated Quality Impact",
        ...     color="orange",
        ...     is_quality=True
        ... )
        >>> print(f"Updated cost event type: {result['name']}")
    """
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        service = CostEventTypeService(context.session)

        # Create update schema with only provided fields
        update_data = CostEventTypeUpdate(
            code=code,
            name=name,
            color=color,
            is_quality=is_quality,
            description=description,
        )

        # Call service method
        cost_event_type = await service.update(
            cost_event_type_id=UUID(cost_event_type_id),
            type_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(cost_event_type.cost_event_type_id),
            "code": cost_event_type.code,
            "name": cost_event_type.name,
            "color": cost_event_type.color,
            "description": cost_event_type.description,
            "message": "Cost event type updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Cost event type {cost_event_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_cost_event_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_cost_event_type",
    description="Delete a cost event type.",
    permissions=["cost-event-type-delete"],
    category="cost-management",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_event_type(
    cost_event_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost event type.

    Context: Provides database session and cost event type service for deletion.

    Args:
        cost_event_type_id: UUID of the cost event type to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If cost_event_type_id is invalid
        KeyError: If cost event type not found

    Example:
        >>> result = await delete_cost_event_type("...")
        >>> print(f"Deleted cost event type: {result['id']}")
    """
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        service = CostEventTypeService(context.session)

        # Call service method
        await service.soft_delete(
            cost_event_type_id=UUID(cost_event_type_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": cost_event_type_id,
            "message": "Cost event type deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid cost event type ID: {cost_event_type_id}"}
    except KeyError:
        return {"error": f"Cost event type {cost_event_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_cost_event_type: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH COST EVENT TYPE TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_cost_element_types",
    description="Batch create cost event types. Max 50 items.",
    permissions=["cost-event-type-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_cost_element_types(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost event types.

    Args:
        items: List of dicts, each with {code, name, color?, is_quality?, description?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        if len(items) > BATCH_SIZE_LIMIT:
            return {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"}

        if not items:
            return {"error": "No items provided"}

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("code"):
                return {"error": f"Item at index {i} is missing required field 'code'"}
            if not item.get("name"):
                return {"error": f"Item at index {i} is missing required field 'name'"}

        service = CostEventTypeService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            type_data = CostEventTypeCreate(
                code=item["code"],
                name=item["name"],
                color=item.get("color", "blue"),
                is_quality=item.get("is_quality", False),
                description=item.get("description"),
            )

            cost_event_type = await service.create(
                type_in=type_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(cost_event_type.cost_event_type_id),
                    "code": cost_event_type.code,
                    "name": cost_event_type.name,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost event types",
        }
        return result
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in batch_create_cost_element_types: {e}")
        return {"error": str(e)}
