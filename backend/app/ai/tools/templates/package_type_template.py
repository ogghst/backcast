"""Cost Event Type tool template for wrapping CostEventTypeService methods.

This template provides AI tools for cost event type management. The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Cost Event Types in Backcast:
- Cost Event Types are configurable event categories (replaces old PackageType)
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
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.cost_event_type import CostEventTypeCreate, CostEventTypeUpdate

logger = logging.getLogger(__name__)


# =============================================================================
# COST EVENT TYPE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_package_types",
    description="Find cost event types by ID or search.",
    permissions=["package-type-read"],
    category="package_types",
    risk_level=RiskLevel.LOW,
)
async def find_package_types(
    package_type_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost event types by ID or search.

    Context: Provides database session and cost event type service for querying.

    Args:
        package_type_id: UUID of a specific cost event type to retrieve (returns single)
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Single cost event type dict if package_type_id provided, otherwise list result.

    Raises:
        ValueError: If package_type_id is not a valid UUID format
    """
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        service = CostEventTypeService(context.session)

        # Single cost event type lookup
        if package_type_id:
            cost_event_type = await service.get_by_id(UUID(package_type_id))

            if not cost_event_type:
                return {"error": f"Cost event type {package_type_id} not found"}

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
            "package_types": [
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
            "skip": skip,
            "limit": limit,
        }
    except ValueError:
        return {"error": f"Invalid cost event type ID: {package_type_id}"}
    except Exception as e:
        logger.error(f"Error in find_package_types: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_package_type",
    description="Create a new cost event type.",
    permissions=["package-type-create"],
    category="package_types",
    risk_level=RiskLevel.HIGH,
)
async def create_package_type(
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
        >>> result = await create_package_type(
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
        logger.error(f"Error in create_package_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_package_type",
    description="Update cost event type fields.",
    permissions=["package-type-update"],
    category="package_types",
    risk_level=RiskLevel.HIGH,
)
async def update_package_type(
    package_type_id: str,
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
        package_type_id: UUID of the cost event type to update
        code: New code (optional)
        name: New name (optional)
        color: New color (optional)
        is_quality: Whether this type contributes to COQ metrics (optional)
        description: New description (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost event type details

    Raises:
        ValueError: If package_type_id is invalid or no fields provided
        KeyError: If cost event type not found

    Example:
        >>> result = await update_package_type(
        ...     package_type_id="...",
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
            cost_event_type_id=UUID(package_type_id),
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
        return {"error": f"Cost event type {package_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_package_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_package_type",
    description="Delete a cost event type.",
    permissions=["package-type-delete"],
    category="package_types",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_package_type(
    package_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost event type.

    Context: Provides database session and cost event type service for deletion.

    Args:
        package_type_id: UUID of the cost event type to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If package_type_id is invalid
        KeyError: If cost event type not found

    Example:
        >>> result = await delete_package_type("...")
        >>> print(f"Deleted cost event type: {result['id']}")
    """
    try:
        from app.services.cost_event_type_service import CostEventTypeService

        service = CostEventTypeService(context.session)

        # Call service method
        await service.soft_delete(
            cost_event_type_id=UUID(package_type_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": package_type_id,
            "message": "Cost event type deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid cost event type ID: {package_type_id}"}
    except KeyError:
        return {"error": f"Cost event type {package_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_package_type: {e}")
        return {"error": str(e)}
