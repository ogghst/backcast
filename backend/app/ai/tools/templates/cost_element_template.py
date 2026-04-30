"""Cost Element and Schedule Baseline tool template for wrapping service methods.

This template shows how to create AI tools for cost element and schedule baseline management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Cost Elements in Backcast:
- Cost Elements represent budget line items under Work Breakdown Elements (WBEs)
- They require a WBE parent and Cost Element Type
- They have a 1:1 relationship with Schedule Baselines
- Full versioning and branch support

Schedule Baselines in Backcast:
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
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate,
)
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
    risk_level=RiskLevel.LOW,
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
                    "budget_amount": float(ce.budget_amount)
                    if ce.budget_amount
                    else None,
                    "description": ce.description,
                    "wbe_id": str(ce.wbe_id),
                    "wbe_name": getattr(ce, "wbe_name", None),
                    "cost_element_type_id": str(ce.cost_element_type_id),
                    "cost_element_type_name": getattr(
                        ce, "cost_element_type_name", None
                    ),
                    "cost_element_type_code": getattr(
                        ce, "cost_element_type_code", None
                    ),
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
    risk_level=RiskLevel.LOW,
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
            "budget_amount": float(cost_element.budget_amount)
            if cost_element.budget_amount
            else None,
            "description": cost_element.description,
            "wbe_id": str(cost_element.wbe_id),
            "wbe_name": getattr(cost_element, "wbe_name", None),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "cost_element_type_name": getattr(
                cost_element, "cost_element_type_name", None
            ),
            "cost_element_type_code": getattr(
                cost_element, "cost_element_type_code", None
            ),
            "branch": cost_element.branch,
            "schedule_baseline_id": str(cost_element.schedule_baseline_id)
            if cost_element.schedule_baseline_id
            else None,
            "forecast_id": str(cost_element.forecast_id)
            if cost_element.forecast_id
            else None,
        }
    except ValueError:
        return {"error": f"Invalid cost element ID: {cost_element_id}"}
    except Exception as e:
        logger.error(f"Error in get_cost_element: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_cost_element",
    description="Create a new cost element under a WBE with a specific type. "
    "Automatically creates a schedule baseline and forecast for the cost element. "
    "Use start_date and end_date to set the schedule baseline dates (should match the project's dates). "
    "Supports LINEAR, GAUSSIAN, and LOGARITHMIC progression types.",
    permissions=["cost-element-create"],
    category="cost-elements",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_element(
    wbe_id: str,
    cost_element_type_id: str,
    code: str,
    name: str,
    budget_amount: float,
    description: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    progression_type: str | None = None,
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
        start_date: Optional start date for the schedule baseline (ISO format, e.g. "2026-05-10")
        end_date: Optional end date for the schedule baseline (ISO format, e.g. "2026-05-30")
        progression_type: Optional progression type (LINEAR, GAUSSIAN, LOGARITHMIC). Defaults to LINEAR.
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
        ...     budget_amount=50000.00,
        ...     start_date="2026-05-01",
        ...     end_date="2026-09-30",
        ...     progression_type="LINEAR"
        ... )
        >>> print(f"Created cost element with ID: {result['id']}")
    """
    try:
        from datetime import datetime

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement as CostElementModel
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Dedup check: prevent creating duplicate cost elements with same code in same WBE
        from typing import cast

        dedup_stmt = (
            select(CostElementModel.cost_element_id, CostElementModel.name)
            .where(
                CostElementModel.code == code,
                CostElementModel.wbe_id == UUID(wbe_id),
                CostElementModel.branch == branch,
                func.upper(cast(Any, CostElementModel).valid_time).is_(None),
                cast(Any, CostElementModel).deleted_at.is_(None),
            )
            .limit(1)
        )
        dedup_result = await context.session.execute(dedup_stmt)
        existing_row = dedup_result.one_or_none()
        if existing_row:
            existing_id, existing_name = existing_row
            return {
                "error": f"A cost element with code '{code}' already exists under this WBE "
                f"(ID: {existing_id}, name: '{existing_name}'). "
                "Use a different code or update the existing cost element.",
                "existing_id": str(existing_id),
                "existing_name": existing_name,
            }

        # Parse optional schedule dates
        schedule_start = datetime.fromisoformat(start_date) if start_date else None
        schedule_end = datetime.fromisoformat(end_date) if end_date else None

        # Create Pydantic schema
        ce_data = CostElementCreate(
            wbe_id=UUID(wbe_id),
            cost_element_type_id=UUID(cost_element_type_id),
            code=code,
            name=name,
            budget_amount=budget_amount,
            description=description,
            branch=branch,
            schedule_start_date=schedule_start,
            schedule_end_date=schedule_end,
            schedule_progression_type=progression_type,
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
            "budget_amount": float(cost_element.budget_amount)
            if cost_element.budget_amount
            else None,
            "description": cost_element.description,
            "wbe_id": str(cost_element.wbe_id),
            "cost_element_type_id": str(cost_element.cost_element_type_id),
            "branch": cost_element.branch,
            "schedule_baseline_id": str(cost_element.schedule_baseline_id)
            if cost_element.schedule_baseline_id
            else None,
            "forecast_id": str(cost_element.forecast_id)
            if cost_element.forecast_id
            else None,
            "schedule_info": {
                "start_date": schedule_start.isoformat()
                if schedule_start
                else "default (creation date)",
                "end_date": schedule_end.isoformat()
                if schedule_end
                else "default (90 days from creation)",
                "progression_type": progression_type or "LINEAR",
            },
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
    risk_level=RiskLevel.HIGH,
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
            cost_element_type_id=UUID(cost_element_type_id)
            if cost_element_type_id
            else None,
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
            "budget_amount": float(cost_element.budget_amount)
            if cost_element.budget_amount
            else None,
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
    risk_level=RiskLevel.CRITICAL,
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
    risk_level=RiskLevel.LOW,
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
            return {
                "error": f"Schedule baseline for cost element {cost_element_id} not found"
            }

        # Convert to AI-friendly format
        return {
            "id": str(baseline.schedule_baseline_id),
            "name": baseline.name,
            "cost_element_id": str(baseline.cost_element_id)
            if baseline.cost_element_id
            else None,
            "start_date": baseline.start_date.isoformat()
            if baseline.start_date
            else None,
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
    risk_level=RiskLevel.HIGH,
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
            "cost_element_id": str(baseline.cost_element_id)
            if baseline.cost_element_id
            else None,
            "start_date": baseline.start_date.isoformat()
            if baseline.start_date
            else None,
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
    risk_level=RiskLevel.CRITICAL,
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
# COST ELEMENT TYPE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="list_cost_element_types",
    description="List all cost element types with optional department filter, "
    "search and pagination. Returns types with their codes and departments.",
    permissions=["cost-element-type-read"],
    category="cost-element-types",
    risk_level=RiskLevel.LOW,
)
async def list_cost_element_types(
    department_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List cost element types with optional filtering.

    Context: Provides database session and cost element type service for querying types.

    Args:
        department_id: Optional department ID to filter cost element types
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., "name", "code")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - cost_element_types: List of cost element type objects
        - total: Total number of types matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned

    Raises:
        ValueError: If invalid filter parameters

    Example:
        >>> result = await list_cost_element_types(
        ...     department_id="...",
        ...     search="Labor",
        ...     limit=10
        ... )
        >>> print(f"Found {result['total']} cost element types")
        >>> for cet in result['cost_element_types']:
        ...     print(f"- {cet['name']} ({cet['code']})")
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Build filters dict
        filters = {}
        if department_id:
            filters["department_id"] = UUID(department_id)

        # Call service method
        types, total = await service.get_cost_element_types(
            filters=filters if filters else None,
            search=search,
            skip=skip,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        # Convert to AI-friendly format
        return {
            "cost_element_types": [
                {
                    "id": str(t.cost_element_type_id),
                    "code": t.code,
                    "name": t.name,
                    "description": t.description,
                    "department_id": str(t.department_id),
                }
                for t in types
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error in list_cost_element_types: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_cost_element_type",
    description="Get detailed information about a specific cost element type by ID. "
    "Returns full type details including department information.",
    permissions=["cost-element-type-read"],
    category="cost-element-types",
    risk_level=RiskLevel.LOW,
)
async def get_cost_element_type(
    cost_element_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single cost element type by ID.

    Context: Provides database session and cost element type service for retrieving type data.

    Args:
        cost_element_type_id: UUID of the cost element type to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with cost element type details or error if not found

    Raises:
        ValueError: If cost_element_type_id is not a valid UUID format
        KeyError: If cost element type is not found

    Example:
        >>> result = await get_cost_element_type("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"Cost Element Type: {result['name']}")
        ...     print(f"Code: {result['code']}")
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Call service method
        cost_element_type = await service.get_as_of(UUID(cost_element_type_id))

        if not cost_element_type:
            return {"error": f"Cost element type {cost_element_type_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(cost_element_type.cost_element_type_id),
            "code": cost_element_type.code,
            "name": cost_element_type.name,
            "description": cost_element_type.description,
            "department_id": str(cost_element_type.department_id),
        }
    except ValueError:
        return {"error": f"Invalid cost element type ID: {cost_element_type_id}"}
    except Exception as e:
        logger.error(f"Error in get_cost_element_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_cost_element_type",
    description="Create a new cost element type under a department. "
    "Cost element types are standardized cost categories owned by departments.",
    permissions=["cost-element-type-create"],
    category="cost-element-types",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_element_type(
    code: str,
    name: str,
    department_id: str,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost element type.

    Context: Provides database session and cost element type service for creating types.

    Args:
        code: Unique cost element type code
        name: Cost element type name
        department_id: UUID of the owning department
        description: Optional description
        context: Injected tool execution context

    Returns:
        Dictionary with created cost element type details

    Raises:
        ValueError: If invalid input or duplicate code
        KeyError: If department not found

    Example:
        >>> result = await create_cost_element_type(
        ...     code="LABOR",
        ...     name="Labor",
        ...     department_id="...",
        ...     description="Labor costs"
        ... )
        >>> print(f"Created cost element type with ID: {result['id']}")
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Create Pydantic schema
        cet_data = CostElementTypeCreate(
            code=code,
            name=name,
            description=description,
            department_id=UUID(department_id),
        )

        # Call service method
        cost_element_type = await service.create(
            type_in=cet_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(cost_element_type.cost_element_type_id),
            "code": cost_element_type.code,
            "name": cost_element_type.name,
            "description": cost_element_type.description,
            "department_id": str(cost_element_type.department_id),
            "message": "Cost element type created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError as e:
        return {"error": f"Department not found: {e}"}
    except Exception as e:
        logger.error(f"Error in create_cost_element_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_cost_element_type",
    description="Update an existing cost element type with new information. "
    "Only updates fields that are provided.",
    permissions=["cost-element-type-update"],
    category="cost-element-types",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_element_type(
    cost_element_type_id: str,
    code: str | None = None,
    name: str | None = None,
    description: str | None = None,
    department_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost element type.

    Context: Provides database session and cost element type service for updating types.

    Args:
        cost_element_type_id: UUID of the cost element type to update
        code: New code (optional)
        name: New name (optional)
        description: New description (optional)
        department_id: New department UUID (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost element type details

    Raises:
        ValueError: If cost_element_type_id is invalid or no fields provided
        KeyError: If cost element type not found

    Example:
        >>> result = await update_cost_element_type(
        ...     cost_element_type_id="...",
        ...     name="Updated Name",
        ...     description="Updated description"
        ... )
        >>> print(f"Updated cost element type: {result['name']}")
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Build update data dict - only include non-None fields
        # This prevents setting optional fields to None when not provided
        update_kwargs: dict[str, str | UUID] = {}
        if code is not None:
            update_kwargs["code"] = code
        if name is not None:
            update_kwargs["name"] = name
        if description is not None:
            update_kwargs["description"] = description
        if department_id is not None:
            update_kwargs["department_id"] = UUID(department_id)

        # Create update schema with only provided fields
        update_data = CostElementTypeUpdate(**update_kwargs)

        # Call service method
        cost_element_type = await service.update(
            cost_element_type_id=UUID(cost_element_type_id),
            type_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(cost_element_type.cost_element_type_id),
            "code": cost_element_type.code,
            "name": cost_element_type.name,
            "description": cost_element_type.description,
            "department_id": str(cost_element_type.department_id),
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
    description="Soft delete a cost element type. "
    "The type is marked as deleted but remains in the system for audit purposes.",
    permissions=["cost-element-type-delete"],
    category="cost-element-types",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_element_type(
    cost_element_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost element type.

    Context: Provides database session and cost element type service for deletion.

    Args:
        cost_element_type_id: UUID of the cost element type to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If cost_element_type_id is invalid
        KeyError: If cost element type not found

    Example:
        >>> result = await delete_cost_element_type("...")
        >>> print(f"Deleted cost element type: {result['id']}")
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Call service method
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
