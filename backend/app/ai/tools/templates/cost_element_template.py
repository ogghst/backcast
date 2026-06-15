"""Cost Element and Cost Element Type tool template for wrapping service methods.

This template provides AI tools for cost element (EOC) and cost element type management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Cost Elements in Backcast (ANSI-748):
- Cost Elements are EOCs (Elements of Cost) under Work Packages
- They are categorization entities linking a Work Package to a Cost Element Type
- Budget is managed at WorkPackage.budget_amount (the BAC), not on CostElement
- They are VERSIONABLE but NOT BRANCHABLE -- financial facts are global

TEMPORAL CONTEXT PATTERN:
For temporal tools (those that work with versioned entities):
- Import temporal logging helpers: log_temporal_context, add_temporal_metadata
- Call log_temporal_context() at tool start for observability
- Call add_temporal_metadata() on return to include temporal context in results
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
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate,
)

logger = logging.getLogger(__name__)


# =============================================================================
# COST ELEMENT TOOLS (EOC under Work Package)
# =============================================================================


@ai_tool(
    name="find_cost_elements",
    description=(
        "Find cost elements (EOCs) by ID or filter. "
        "IMPORTANT: results are paginated — the returned list may be a SUBSET of all matching results. "
        "Always check 'total' and 'has_more' in the response: if has_more=true or total exceeds the returned count, "
        "more pages exist. Use the 'page' and 'limit' parameters to retrieve additional pages. "
        "Do NOT assume the first page contains all results — if you don't find what you need, page forward. "
        "Use 'search' to narrow results before paging."
    ),
    permissions=["cost-element-read"],
    category="cost-management",
    risk_level=RiskLevel.LOW,
)
async def find_cost_elements(
    cost_element_id: str | None = None,
    work_package_id: str | None = None,
    cost_element_type_id: str | None = None,
    page: int = 1,
    limit: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost elements (EOCs) by ID or filter.

    If cost_element_id is provided, returns a single cost element.
    Otherwise returns a filtered list.

    Args:
        cost_element_id: Optional UUID to fetch a single cost element
        work_package_id: Optional Work Package ID to filter cost elements
        cost_element_type_id: Optional cost element type ID to filter
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        context: Injected tool execution context

    Returns:
        Dictionary with cost element details or list with pagination info

    Raises:
        ValueError: If invalid filter parameters are provided
    """
    log_temporal_context("find_cost_elements", context)
    limit = get_page_limit(limit)
    skip = (page - 1) * limit

    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Single CE lookup by ID
        if cost_element_id:
            cost_element = await service.get_by_id(UUID(cost_element_id))

            if not cost_element:
                return add_temporal_metadata(
                    {"error": f"Cost element {cost_element_id} not found"},
                    context,
                )

            result: dict[str, Any] = {
                "id": str(cost_element.cost_element_id),
                "work_package_id": str(cost_element.work_package_id),
                "cost_element_type_id": str(cost_element.cost_element_type_id),
                "description": cost_element.description,
                "work_package_name": getattr(cost_element, "work_package_name", None),
                "work_package_code": getattr(cost_element, "work_package_code", None),
                "cost_element_type_name": getattr(
                    cost_element, "cost_element_type_name", None
                ),
                "cost_element_type_code": getattr(
                    cost_element, "cost_element_type_code", None
                ),
            }
            return add_temporal_metadata(result, context)

        # List mode with filters
        cost_elements, total = await service.get_cost_elements(
            work_package_id=UUID(work_package_id) if work_package_id else None,
            cost_element_type_id=UUID(cost_element_type_id)
            if cost_element_type_id
            else None,
            skip=skip,
            limit=limit,
            as_of=context.as_of,
        )

        result = {
            "cost_elements": [
                {
                    "id": str(ce.cost_element_id),
                    "work_package_id": str(ce.work_package_id),
                    "cost_element_type_id": str(ce.cost_element_type_id),
                    "description": ce.description,
                    "work_package_name": getattr(ce, "work_package_name", None),
                    "work_package_code": getattr(ce, "work_package_code", None),
                    "cost_element_type_name": getattr(
                        ce, "cost_element_type_name", None
                    ),
                    "cost_element_type_code": getattr(
                        ce, "cost_element_type_code", None
                    ),
                }
                for ce in cost_elements
            ],
            "total": total,
            "page": page,
            "page_count": calc_page_count(total, limit),
            "limit": limit,
            "has_more": page < calc_page_count(total, limit),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in find_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="create_cost_element",
    description="Create cost element (EOC) under a Work Package.",
    permissions=["cost-element-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_element(
    work_package_id: str,
    cost_element_type_id: str,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost element (EOC) under a Work Package.

    Args:
        work_package_id: UUID of the parent Work Package
        cost_element_type_id: UUID of the cost element type
        description: Optional description
        context: Injected tool execution context

    Returns:
        Dictionary with created cost element details

    Raises:
        ValueError: If invalid input or parent not found
        KeyError: If parent Work Package or type not found
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        ce_data = CostElementCreate(
            work_package_id=UUID(work_package_id),
            cost_element_type_id=UUID(cost_element_type_id),
            description=description,
        )

        cost_element = await service.create_cost_element(
            element_in=ce_data,
            actor_id=UUID(context.user_id),
        )

        return {
            "id": str(cost_element.cost_element_id),
            "work_package_id": str(cost_element.work_package_id),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "description": cost_element.description,
            "message": "Cost element created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError as e:
        return {"error": f"Parent entity not found: {e}"}
    except Exception as e:
        logger.error(f"Error in create_cost_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_cost_element",
    description="Update cost element (EOC).",
    permissions=["cost-element-update"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_element(
    cost_element_id: str,
    description: str | None = None,
    cost_element_type_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost element (EOC).

    Only updates fields that are provided.

    Args:
        cost_element_id: UUID of the cost element to update
        description: New description (optional)
        cost_element_type_id: New cost element type ID (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost element details

    Raises:
        ValueError: If cost_element_id is invalid or no fields provided
        KeyError: If cost element not found
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        update_data = CostElementUpdate(
            cost_element_type_id=UUID(cost_element_type_id)
            if cost_element_type_id
            else None,
            description=description,
        )

        cost_element = await service.update_cost_element(
            cost_element_id=UUID(cost_element_id),
            element_in=update_data,
            actor_id=UUID(context.user_id),
        )

        result: dict[str, Any] = {
            "id": str(cost_element.cost_element_id),
            "work_package_id": str(cost_element.work_package_id),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "description": cost_element.description,
        }

        return result
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Cost element {cost_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_cost_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_cost_element",
    description="Delete cost element (EOC).",
    permissions=["cost-element-delete"],
    category="cost-management",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_element(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost element (EOC).

    Args:
        cost_element_id: UUID of the cost element to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If cost_element_id is invalid
        KeyError: If cost element not found
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        await service.soft_delete_cost_element(
            cost_element_id=UUID(cost_element_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": cost_element_id,
            "message": "Cost element deleted",
        }
    except ValueError:
        return {"error": f"Invalid cost element ID: {cost_element_id}"}
    except KeyError:
        return {"error": f"Cost element {cost_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_cost_element: {e}")
        return {"error": str(e)}


# =============================================================================
# COST ELEMENT TYPE TOOLS
# =============================================================================


@ai_tool(
    name="find_cost_element_types",
    description=(
        "Find cost element types by ID or search/filter. "
        "IMPORTANT: results are paginated — the returned list may be a SUBSET of all matching results. "
        "Always check 'total' and 'has_more' in the response: if has_more=true or total exceeds the returned count, "
        "more pages exist. Use the 'page' and 'limit' parameters to retrieve additional pages. "
        "Do NOT assume the first page contains all results — if you don't find what you need, page forward. "
        "Use 'search' to narrow results before paging."
    ),
    permissions=["cost-element-type-read"],
    category="cost-management",
    risk_level=RiskLevel.LOW,
)
async def find_cost_element_types(
    cost_element_type_id: str | None = None,
    organizational_unit_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int | None = None,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost element types by ID or search/filter.

    If cost_element_type_id is provided, returns a single type. Otherwise
    returns a filtered list.

    Args:
        cost_element_type_id: Optional UUID to fetch a single cost element type
        organizational_unit_id: Optional organizational unit ID to filter
        search: Optional search term for code or name
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        sort_field: Field to sort by (e.g., "name", "code")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with cost element type details or list with pagination info

    Raises:
        ValueError: If invalid filter parameters
    """
    limit = get_page_limit(limit)
    skip = (page - 1) * limit
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Single type lookup by ID
        if cost_element_type_id:
            cost_element_type = await service.get_by_id(UUID(cost_element_type_id))

            if not cost_element_type:
                return {"error": f"Cost element type {cost_element_type_id} not found"}

            return {
                "id": str(cost_element_type.cost_element_type_id),
                "code": cost_element_type.code,
                "name": cost_element_type.name,
                "description": cost_element_type.description,
                "organizational_unit_id": str(cost_element_type.organizational_unit_id),
            }

        # List mode with filters
        filters: dict[str, Any] = {}
        if organizational_unit_id:
            filters["organizational_unit_id"] = UUID(organizational_unit_id)

        types, total = await service.get_cost_element_types(
            filters=filters if filters else None,
            search=search,
            skip=skip,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        return {
            "cost_element_types": [
                {
                    "id": str(t.cost_element_type_id),
                    "code": t.code,
                    "name": t.name,
                    "description": t.description,
                    "organizational_unit_id": str(t.organizational_unit_id),
                }
                for t in types
            ],
            "total": total,
            "page": page,
            "page_count": calc_page_count(total, limit),
            "limit": limit,
            "has_more": page < calc_page_count(total, limit),
        }
    except ValueError:
        return {"error": f"Invalid cost element type ID: {cost_element_type_id}"}
    except Exception as e:
        logger.error(f"Error in find_cost_element_types: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_cost_element_type",
    description="Create cost element type under an organizational unit.",
    permissions=["cost-element-type-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_element_type(
    code: str,
    name: str,
    organizational_unit_id: str,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost element type.

    Args:
        code: Unique cost element type code
        name: Cost element type name
        organizational_unit_id: UUID of the owning organizational unit
        description: Optional description
        context: Injected tool execution context

    Returns:
        Dictionary with created cost element type details

    Raises:
        ValueError: If invalid input or duplicate code
        KeyError: If organizational unit not found
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        cet_data = CostElementTypeCreate(
            code=code,
            name=name,
            description=description,
            organizational_unit_id=UUID(organizational_unit_id),
        )

        cost_element_type = await service.create(
            type_in=cet_data,
            actor_id=UUID(context.user_id),
        )

        return {
            "id": str(cost_element_type.cost_element_type_id),
            "code": cost_element_type.code,
            "name": cost_element_type.name,
            "description": cost_element_type.description,
            "organizational_unit_id": str(cost_element_type.organizational_unit_id),
            "message": "Cost element type created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError as e:
        return {"error": f"Organizational unit not found: {e}"}
    except Exception as e:
        logger.error(f"Error in create_cost_element_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_cost_element_type",
    description="Update cost element type.",
    permissions=["cost-element-type-update"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_element_type(
    cost_element_type_id: str,
    code: str | None = None,
    name: str | None = None,
    description: str | None = None,
    organizational_unit_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost element type.

    Only updates fields that are provided.

    Args:
        cost_element_type_id: UUID of the cost element type to update
        code: New code (optional)
        name: New name (optional)
        description: New description (optional)
        organizational_unit_id: New organizational unit UUID (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost element type details

    Raises:
        ValueError: If cost_element_type_id is invalid or no fields provided
        KeyError: If cost element type not found
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        update_kwargs: dict[str, str | UUID] = {}
        if code is not None:
            update_kwargs["code"] = code
        if name is not None:
            update_kwargs["name"] = name
        if description is not None:
            update_kwargs["description"] = description
        if organizational_unit_id is not None:
            update_kwargs["organizational_unit_id"] = UUID(organizational_unit_id)

        update_data = CostElementTypeUpdate(**update_kwargs)

        cost_element_type = await service.update(
            cost_element_type_id=UUID(cost_element_type_id),
            type_in=update_data,
            actor_id=UUID(context.user_id),
        )

        return {
            "id": str(cost_element_type.cost_element_type_id),
            "code": cost_element_type.code,
            "name": cost_element_type.name,
            "description": cost_element_type.description,
            "organizational_unit_id": str(cost_element_type.organizational_unit_id),
            "message": "Cost element type updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Cost element type {cost_element_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_cost_element_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_cost_element_type",
    description="Delete cost element type.",
    permissions=["cost-element-type-delete"],
    category="cost-management",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_element_type(
    cost_element_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost element type.

    Args:
        cost_element_type_id: UUID of the cost element type to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If cost_element_type_id is invalid
        KeyError: If cost element type not found
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        await service.soft_delete(
            cost_element_type_id=UUID(cost_element_type_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": cost_element_type_id,
            "message": "Cost element type deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid cost element type ID: {cost_element_type_id}"}
    except KeyError:
        return {"error": f"Cost element type {cost_element_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_cost_element_type: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH COST ELEMENT TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_cost_elements",
    description="Batch create cost elements under a Work Package. Max 50 items.",
    permissions=["cost-element-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_cost_elements(
    work_package_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost elements (EOCs) under the same Work Package.

    Args:
        work_package_id: UUID of the parent Work Package
        items: List of dicts, each with {cost_element_type_id, description?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_cost_elements", context)

    try:
        from uuid import UUID

        from app.services.cost_element_service import CostElementService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_type_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_type_id'"
                    },
                    context,
                )

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            ce_data = CostElementCreate(
                work_package_id=UUID(work_package_id),
                cost_element_type_id=UUID(item["cost_element_type_id"]),
                description=item.get("description"),
            )
            cost_element = await service.create_cost_element(
                element_in=ce_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(cost_element.cost_element_id),
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost elements under Work Package {work_package_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata(
            {"error": f"Parent entity not found: {e}"}, context
        )
    except Exception as e:
        logger.error(f"Error in batch_create_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="batch_delete_cost_elements",
    description="Batch soft delete cost elements. Max 50 items.",
    permissions=["cost-element-delete"],
    category="cost-management",
    risk_level=RiskLevel.CRITICAL,
)
async def batch_delete_cost_elements(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch soft delete cost elements (EOCs).

    Args:
        cost_element_ids: List of cost element UUIDs to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deleted IDs list, total count, and message
    """
    log_temporal_context("batch_delete_cost_elements", context)

    try:
        from uuid import UUID

        from app.services.cost_element_service import CostElementService

        if len(cost_element_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not cost_element_ids:
            return add_temporal_metadata(
                {"error": "No cost element IDs provided"}, context
            )

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        deleted_ids: list[str] = []

        for ce_id in cost_element_ids:
            await service.soft_delete_cost_element(
                cost_element_id=UUID(ce_id),
                actor_id=actor_id,
            )
            deleted_ids.append(ce_id)

        result = {
            "deleted": deleted_ids,
            "total": len(deleted_ids),
            "message": f"Soft deleted {len(deleted_ids)} cost elements",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_delete_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)
