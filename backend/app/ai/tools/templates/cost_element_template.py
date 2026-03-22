"""Cost Element and Schedule Baseline tool template for wrapping service methods.

This template shows how to create AI tools for cost element and schedule baseline management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Cost Elements in Backcast EVS:
- Cost Elements represent budget line items under Work Breakdown Elements (WBEs)
- They require a WBE parent and Cost Element Type
- They have a 1:1 relationship with Schedule Baselines
- Full versioning and branch support

Schedule Baselines in Backcast EVS:
- Schedule Baselines define the time-phased budget curve for Cost Elements
- They are used in EVM Planned Value (PV) calculations
- Each Cost Element has exactly one Schedule Baseline
- Support different progression types (LINEAR, GAUSSIAN, LOGARITHMIC)

Usage:
    1. Import CostElementService and ScheduleBaselineService methods
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
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import ToolContext
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate
from app.models.schemas.schedule_baseline import ScheduleBaselineUpdate

logger = logging.getLogger(__name__)

# =============================================================================
# COST ELEMENT CRUD TOOLS
# =============================================================================

@ai_tool(
    name="list_cost_elements",
    description="List all cost elements with optional filtering by WBE, type, "
    "or search. Returns cost elements with their budget amounts and related data. "
    "Temporal context (branch, as_of date) is enforced by the system.",
    permissions=["cost-element-read"],
    category="cost-elements",
)
async def list_cost_elements(
    wbe_id: str | None = None,
    cost_element_type_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List cost elements with optional filtering.

    Context: Provides database session and cost element service for querying cost elements.

    Args:
        wbe_id: Optional WBE ID to filter cost elements
        cost_element_type_id: Optional cost element type ID to filter
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., "name", "code", "budget_amount")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - cost_elements: List of cost element objects
        - total: Total number of cost elements matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned
        - _temporal_context: Temporal context metadata (branch, as_of)

    Raises:
        ValueError: If invalid filter parameters are provided

    Example:
        >>> result = await list_cost_elements(wbe_id="...", limit=10)
        >>> print(f"Found {result['total']} cost elements")
        >>> for ce in result['cost_elements']:
        ...     print(f"- {ce['name']}: ${ce['budget_amount']}")
    """
    # Log temporal context for observability
    log_temporal_context("list_cost_elements", context)

    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Build filters dict
        filters = {}
        if wbe_id:
            filters["wbe_id"] = UUID(wbe_id)
        if cost_element_type_id:
            filters["cost_element_type_id"] = UUID(cost_element_type_id)

        # Call service method
        cost_elements, total = await service.get_cost_elements(
            filters=filters if filters else None,
            search=search,
            skip=skip,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "cost_elements": [
                {
                    "id": str(ce.cost_element_id),
                    "code": ce.code,
                    "name": ce.name,
                    "budget_amount": float(ce.budget_amount) if ce.budget_amount else None,
                    "description": ce.description,
                    "wbe_id": str(ce.wbe_id),
                    "wbe_name": getattr(ce, 'wbe_name', None),
                    "cost_element_type_id": str(ce.cost_element_type_id),
                    "cost_element_type_name": getattr(ce, 'cost_element_type_name', None),
                    "cost_element_type_code": getattr(ce, 'cost_element_type_code', None),
                    "branch": ce.branch,
                }
                for ce in cost_elements
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in list_cost_elements: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_cost_element",
    description="Get detailed information about a specific cost element by ID. "
    "Returns full cost element details including budget, type, and WBE information.",
    permissions=["cost-element-read"],
    category="cost-elements",
)
async def get_cost_element(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single cost element by ID.

    Context: Provides database session and cost element service for retrieving cost element data.

    Args:
        cost_element_id: UUID of the cost element to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with cost element details or error if not found

    Raises:
        ValueError: If cost_element_id is not a valid UUID format
        KeyError: If cost element is not found

    Example:
        >>> result = await get_cost_element("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"Cost Element: {result['name']}")
        ...     print(f"Budget: ${result['budget_amount']}")
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Call service method
        cost_element = await service.get_by_id(UUID(cost_element_id))

        if not cost_element:
            return {"error": f"Cost element {cost_element_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(cost_element.cost_element_id),
            "code": cost_element.code,
            "name": cost_element.name,
            "budget_amount": float(cost_element.budget_amount) if cost_element.budget_amount else None,
            "description": cost_element.description,
            "wbe_id": str(cost_element.wbe_id),
            "wbe_name": getattr(cost_element, 'wbe_name', None),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "cost_element_type_name": getattr(cost_element, 'cost_element_type_name', None),
            "cost_element_type_code": getattr(cost_element, 'cost_element_type_code', None),
            "branch": cost_element.branch,
            "schedule_baseline_id": str(cost_element.schedule_baseline_id) if cost_element.schedule_baseline_id else None,
            "forecast_id": str(cost_element.forecast_id) if cost_element.forecast_id else None,
        }
    except ValueError:
        return {"error": f"Invalid cost element ID: {cost_element_id}"}
    except Exception as e:
        logger.error(f"Error in get_cost_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_cost_element",
    description="Create a new cost element under a WBE with a specific type. "
    "Automatically creates a default schedule baseline and forecast for the cost element.",
    permissions=["cost-element-create"],
    category="cost-elements",
)
async def create_cost_element(
    wbe_id: str,
    cost_element_type_id: str,
    code: str,
    name: str,
    budget_amount: float,
    description: str | None = None,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost element.

    Context: Provides database session and cost element service for creating cost elements.

    Args:
        wbe_id: UUID of the parent WBE
        cost_element_type_id: UUID of the cost element type
        code: Unique cost element code
        name: Cost element name
        budget_amount: Budget amount for the cost element
        description: Optional description
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with created cost element details

    Raises:
        ValueError: If invalid input or duplicate code
        KeyError: If parent WBE or type not found

    Example:
        >>> result = await create_cost_element(
        ...     wbe_id="...",
        ...     cost_element_type_id="...",
        ...     code="CE-001",
        ...     name="Mechanical Assembly",
        ...     budget_amount=50000.00
        ... )
        >>> print(f"Created cost element with ID: {result['id']}")
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Create Pydantic schema
        ce_data = CostElementCreate(
            wbe_id=UUID(wbe_id),
            cost_element_type_id=UUID(cost_element_type_id),
            code=code,
            name=name,
            budget_amount=budget_amount,
            description=description,
            branch=branch,
        )

        # Call service method
        cost_element = await service.create_cost_element(
            element_in=ce_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(cost_element.cost_element_id),
            "code": cost_element.code,
            "name": cost_element.name,
            "budget_amount": float(cost_element.budget_amount) if cost_element.budget_amount else None,
            "description": cost_element.description,
            "wbe_id": str(cost_element.wbe_id),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "branch": cost_element.branch,
            "schedule_baseline_id": str(cost_element.schedule_baseline_id) if cost_element.schedule_baseline_id else None,
            "forecast_id": str(cost_element.forecast_id) if cost_element.forecast_id else None,
            "message": "Cost element created with default schedule baseline and forecast",
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
    description="Update an existing cost element with new information. "
    "Only updates fields that are provided. Supports branch isolation.",
    permissions=["cost-element-update"],
    category="cost-elements",
)
async def update_cost_element(
    cost_element_id: str,
    code: str | None = None,
    name: str | None = None,
    budget_amount: float | None = None,
    description: str | None = None,
    cost_element_type_id: str | None = None,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost element.

    Context: Provides database session and cost element service for updating cost elements.

    Args:
        cost_element_id: UUID of the cost element to update
        code: New code (optional)
        name: New name (optional)
        budget_amount: New budget amount (optional)
        description: New description (optional)
        cost_element_type_id: New cost element type ID (optional)
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost element details

    Raises:
        ValueError: If cost_element_id is invalid or no fields provided
        KeyError: If cost element not found

    Example:
        >>> result = await update_cost_element(
        ...     cost_element_id="...",
        ...     budget_amount=60000.00,
        ...     name="Updated Name"
        ... )
        >>> print(f"Updated cost element budget to: ${result['budget_amount']}")
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Create update schema with only provided fields
        update_data = CostElementUpdate(
            code=code,
            name=name,
            budget_amount=budget_amount,
            description=description,
            cost_element_type_id=UUID(cost_element_type_id) if cost_element_type_id else None,
            branch=branch,
        )

        # Call service method
        cost_element = await service.update(
            cost_element_id=UUID(cost_element_id),
            element_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(cost_element.cost_element_id),
            "code": cost_element.code,
            "name": cost_element.name,
            "budget_amount": float(cost_element.budget_amount) if cost_element.budget_amount else None,
            "description": cost_element.description,
            "wbe_id": str(cost_element.wbe_id),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "branch": cost_element.branch,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Cost element {cost_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_cost_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_cost_element",
    description="Soft delete a cost element. "
    "Cascades the delete to the associated schedule baseline and forecast.",
    permissions=["cost-element-delete"],
    category="cost-elements",
)
async def delete_cost_element(
    cost_element_id: str,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost element.

    Context: Provides database session and cost element service for deletion.

    Args:
        cost_element_id: UUID of the cost element to delete
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If cost_element_id is invalid
        KeyError: If cost element not found

    Example:
        >>> result = await delete_cost_element("...")
        >>> print(f"Deleted cost element: {result['id']}")
    """
    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Call service method (cascades to schedule baseline and forecast)
        await service.soft_delete(
            cost_element_id=UUID(cost_element_id),
            actor_id=UUID(context.user_id),
            branch=branch,
        )

        return {
            "id": cost_element_id,
            "message": "Cost element deleted (schedule baseline and forecast also deleted)",
        }
    except ValueError:
        return {"error": f"Invalid cost element ID: {cost_element_id}"}
    except KeyError:
        return {"error": f"Cost element {cost_element_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_cost_element: {e}")
        return {"error": str(e)}


# =============================================================================
# SCHEDULE BASELINE CRUD TOOLS
# =============================================================================

@ai_tool(
    name="get_schedule_baseline",
    description="Get the schedule baseline for a specific cost element. "
    "Schedule baselines define the time-phased budget curve for EVM calculations.",
    permissions=["schedule-baseline-read"],
    category="schedule-baselines",
)
async def get_schedule_baseline(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get schedule baseline for a cost element.

    Context: Provides database session and schedule baseline service for retrieving baseline data.

    Args:
        cost_element_id: UUID of the cost element
        context: Injected tool execution context

    Returns:
        Dictionary with schedule baseline details or error if not found

    Raises:
        ValueError: If cost_element_id is not a valid UUID format

    Example:
        >>> result = await get_schedule_baseline("...")
        >>> if "error" not in result:
        ...     print(f"Baseline: {result['name']}")
        ...     print(f"Progression: {result['progression_type']}")
    """
    try:
        from app.services.schedule_baseline_service import ScheduleBaselineService

        service = ScheduleBaselineService(context.session)

        # Call service method to get baseline for cost element
        baseline = await service.get_for_cost_element(UUID(cost_element_id))

        if not baseline:
            return {"error": f"Schedule baseline for cost element {cost_element_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(baseline.schedule_baseline_id),
            "name": baseline.name,
            "cost_element_id": str(baseline.cost_element_id) if baseline.cost_element_id else None,
            "start_date": baseline.start_date.isoformat() if baseline.start_date else None,
            "end_date": baseline.end_date.isoformat() if baseline.end_date else None,
            "progression_type": baseline.progression_type,
            "description": baseline.description,
            "branch": baseline.branch,
        }
    except ValueError:
        return {"error": f"Invalid cost element ID: {cost_element_id}"}
    except Exception as e:
        logger.error(f"Error in get_schedule_baseline: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_schedule_baseline",
    description="Update an existing schedule baseline with new schedule information. "
    "Supports different progression types for budget distribution.",
    permissions=["schedule-baseline-update"],
    category="schedule-baselines",
)
async def update_schedule_baseline(
    schedule_baseline_id: str,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    progression_type: str | None = None,
    description: str | None = None,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing schedule baseline.

    Context: Provides database session and schedule baseline service for updating baselines.

    Args:
        schedule_baseline_id: UUID of the schedule baseline to update
        name: New name (optional)
        start_date: New start date ISO format (optional)
        end_date: New end date ISO format (optional)
        progression_type: New progression type (LINEAR, GAUSSIAN, LOGARITHMIC)
        description: New description (optional)
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with updated schedule baseline details

    Raises:
        ValueError: If schedule_baseline_id is invalid or date format is wrong
        KeyError: If schedule baseline not found

    Example:
        >>> result = await update_schedule_baseline(
        ...     schedule_baseline_id="...",
        ...     progression_type="GAUSSIAN",
        ...     end_date="2026-12-31T23:59:59"
        ... )
        >>> print(f"Updated baseline progression: {result['progression_type']}")
    """
    try:
        from datetime import datetime

        from app.services.schedule_baseline_service import ScheduleBaselineService

        service = ScheduleBaselineService(context.session)

        # Create update schema with only provided fields
        update_data = ScheduleBaselineUpdate(
            name=name,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None,
            progression_type=progression_type,
            description=description,
            branch=branch,
        )

        # Call service method
        baseline = await service.update_schedule_baseline(
            root_id=UUID(schedule_baseline_id),
            baseline_in=update_data,
            actor_id=UUID(context.user_id),
            branch=branch,
        )

        # Convert to AI-friendly format
        return {
            "id": str(baseline.schedule_baseline_id),
            "name": baseline.name,
            "cost_element_id": str(baseline.cost_element_id) if baseline.cost_element_id else None,
            "start_date": baseline.start_date.isoformat() if baseline.start_date else None,
            "end_date": baseline.end_date.isoformat() if baseline.end_date else None,
            "progression_type": baseline.progression_type,
            "description": baseline.description,
            "branch": baseline.branch,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Schedule baseline {schedule_baseline_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_schedule_baseline: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_schedule_baseline",
    description="Soft delete a schedule baseline. "
    "Note: This is usually called automatically when deleting the associated cost element.",
    permissions=["schedule-baseline-delete"],
    category="schedule-baselines",
)
async def delete_schedule_baseline(
    schedule_baseline_id: str,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a schedule baseline.

    Context: Provides database session and schedule baseline service for deletion.

    Args:
        schedule_baseline_id: UUID of the schedule baseline to delete
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If schedule_baseline_id is invalid
        KeyError: If schedule baseline not found

    Example:
        >>> result = await delete_schedule_baseline("...")
        >>> print(f"Deleted schedule baseline: {result['id']}")
    """
    try:
        from app.services.schedule_baseline_service import ScheduleBaselineService

        service = ScheduleBaselineService(context.session)

        # Call service method
        await service.soft_delete(
            root_id=UUID(schedule_baseline_id),
            actor_id=UUID(context.user_id),
            branch=branch,
        )

        return {
            "id": schedule_baseline_id,
            "message": "Schedule baseline deleted",
        }
    except ValueError:
        return {"error": f"Invalid schedule baseline ID: {schedule_baseline_id}"}
    except KeyError:
        return {"error": f"Schedule baseline {schedule_baseline_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_schedule_baseline: {e}")
        return {"error": str(e)}


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
COST ELEMENT TOOL PATTERNS:

1. CREATION FLOW:
   - Cost Elements require wbe_id and cost_element_type_id
   - Auto-creates Schedule Baseline (default schedule)
   - Auto-creates Forecast (default forecast)
   - All created in the same branch

2. UPDATE FLOW:
   - Supports branch isolation
   - Can fork from main if updating in different branch
   - Auto-creates new Schedule Baseline and Forecast for new branch

3. DELETE FLOW:
   - Soft delete (cascades to Schedule Baseline and Forecast)
   - Maintains audit trail
   - Branch-aware deletion

4. SCHEDULE BASELINE RELATIONSHIP:
   - 1:1 relationship with Cost Elements
   - Use get_for_cost_element() to retrieve baseline
   - Used in EVM Planned Value (PV) calculations
   - Supports different progression types

PERMISSIONS MODEL:
   - cost-element-read: View cost elements
   - cost-element-create: Create cost elements
   - cost-element-update: Update cost elements
   - cost-element-delete: Delete cost elements
   - schedule-baseline-read: View schedule baselines
   - schedule-baseline-update: Update schedule baselines
   - schedule-baseline-delete: Delete schedule baselines

BEST PRACTICES:
   - Always create cost elements under valid WBEs
   - Verify cost element type exists before creation
   - Use appropriate progression types for schedules
   - Schedule baselines are auto-managed with cost elements
"""
