"""Cost Element and Cost Element Type tool template for wrapping service methods.

This template provides AI tools for cost element and cost element type management.
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
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate,
)
from app.models.schemas.schedule_baseline import ScheduleBaselineUpdate

logger = logging.getLogger(__name__)

BATCH_SIZE_LIMIT = 50


# =============================================================================
# COST ELEMENT TOOLS
# =============================================================================


@ai_tool(
    name="find_cost_elements",
    description="Find cost elements by ID or search/filter.",
    permissions=["cost-element-read"],
    category="cost-elements",
    risk_level=RiskLevel.LOW,
)
async def find_cost_elements(
    cost_element_id: str | None = None,
    wbe_id: str | None = None,
    cost_element_type_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost elements by ID or search/filter.

    If cost_element_id is provided, returns a single cost element with schedule
    baseline data included. Otherwise returns a filtered list.

    Args:
        cost_element_id: Optional UUID to fetch a single cost element
        wbe_id: Optional WBE ID to filter cost elements
        cost_element_type_id: Optional cost element type ID to filter
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., "name", "code", "budget_amount")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with cost element details or list with pagination info

    Raises:
        ValueError: If invalid filter parameters are provided
    """
    log_temporal_context("find_cost_elements", context)

    try:
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Single CE lookup by ID
        if cost_element_id:
            if context.as_of is not None:
                # Temporal query: use list-mode path for as_of consistency
                cost_elements, _ = await service.get_cost_elements(
                    filters={"cost_element_id": UUID(cost_element_id)},
                    limit=1,
                    branch=context.branch_name or "main",
                    as_of=context.as_of,
                )
                cost_element = cost_elements[0] if cost_elements else None
            else:
                # Fast path: current version only
                cost_element = await service.get_by_id(
                    UUID(cost_element_id),
                    branch=context.branch_name or "main",
                )

            if not cost_element:
                return add_temporal_metadata(
                    {"error": f"Cost element {cost_element_id} not found"},
                    context,
                )

            result: dict[str, Any] = {
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

            # Include schedule baseline data for single CE
            try:
                from app.services.schedule_baseline_service import (
                    ScheduleBaselineService,
                )

                sb_service = ScheduleBaselineService(context.session)
                baseline = await sb_service.get_for_cost_element(
                    UUID(cost_element_id),
                    branch=context.branch_name or "main",
                )
                if baseline:
                    result["schedule_baseline"] = {
                        "id": str(baseline.schedule_baseline_id),
                        "name": baseline.name,
                        "start_date": baseline.start_date.isoformat()
                        if baseline.start_date
                        else None,
                        "end_date": baseline.end_date.isoformat()
                        if baseline.end_date
                        else None,
                        "progression_type": baseline.progression_type,
                        "description": baseline.description,
                        "branch": baseline.branch,
                    }
            except Exception:
                pass  # Non-fatal: schedule baseline is supplementary

            return add_temporal_metadata(result, context)

        # List mode with filters
        filters: dict[str, Any] = {}
        if wbe_id:
            filters["wbe_id"] = UUID(wbe_id)
        if cost_element_type_id:
            filters["cost_element_type_id"] = UUID(cost_element_type_id)

        cost_elements, total = await service.get_cost_elements(
            filters=filters if filters else None,
            search=search,
            skip=skip,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
            branch=context.branch_name or "main",
            as_of=context.as_of,
        )

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
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in find_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="create_cost_element",
    description="Create cost element with optional schedule baseline.",
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
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost element.

    Args:
        wbe_id: UUID of the parent WBE
        cost_element_type_id: UUID of the cost element type
        code: Unique cost element code
        name: Cost element name
        budget_amount: Budget amount for the cost element
        description: Optional description
        start_date: Optional start date for the schedule baseline (ISO format)
        end_date: Optional end date for the schedule baseline (ISO format)
        progression_type: Optional progression type (LINEAR, GAUSSIAN, LOGARITHMIC)
        context: Injected tool execution context

    Returns:
        Dictionary with created cost element details

    Raises:
        ValueError: If invalid input or duplicate code
        KeyError: If parent WBE or type not found
    """
    try:
        from datetime import datetime

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement as CostElementModel
        from app.services.cost_element_service import CostElementService

        service = CostElementService(context.session)

        # Dedup check: prevent duplicate code in same WBE
        from typing import cast

        dedup_stmt = (
            select(CostElementModel.cost_element_id, CostElementModel.name)
            .where(
                CostElementModel.code == code,
                CostElementModel.wbe_id == UUID(wbe_id),
                CostElementModel.branch == (context.branch_name or "main"),
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
            branch=context.branch_name or "main",
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
    description="Update cost element and/or its schedule baseline.",
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
    schedule_start_date: str | None = None,
    schedule_end_date: str | None = None,
    schedule_progression_type: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost element and optionally its schedule baseline.

    Only updates fields that are provided. If schedule_* params are provided,
    also updates the associated schedule baseline.

    Args:
        cost_element_id: UUID of the cost element to update
        code: New code (optional)
        name: New name (optional)
        budget_amount: New budget amount (optional)
        description: New description (optional)
        cost_element_type_id: New cost element type ID (optional)
        schedule_start_date: New schedule start date ISO format (optional)
        schedule_end_date: New schedule end date ISO format (optional)
        schedule_progression_type: New progression type (optional)
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

        # Create update schema with only provided fields
        update_data = CostElementUpdate(
            code=code,
            name=name,
            budget_amount=budget_amount,
            description=description,
            cost_element_type_id=UUID(cost_element_type_id)
            if cost_element_type_id
            else None,
            branch=context.branch_name or "main",
        )

        # Call service method
        cost_element = await service.update(
            cost_element_id=UUID(cost_element_id),
            element_in=update_data,
            actor_id=UUID(context.user_id),
        )

        result: dict[str, Any] = {
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

        # Optionally update schedule baseline
        if any([schedule_start_date, schedule_end_date, schedule_progression_type]):
            from datetime import datetime

            from app.services.schedule_baseline_service import (
                ScheduleBaselineService,
            )

            sb_service = ScheduleBaselineService(context.session)

            # Get the current schedule baseline for this cost element
            baseline = await sb_service.get_for_cost_element(
                UUID(cost_element_id),
                branch=context.branch_name or "main",
            )

            if baseline:
                sb_kwargs: dict[str, Any] = {
                    "progression_type": schedule_progression_type,
                    "branch": context.branch_name or "main",
                }
                if schedule_start_date:
                    sb_kwargs["start_date"] = datetime.fromisoformat(
                        schedule_start_date
                    )
                if schedule_end_date:
                    sb_kwargs["end_date"] = datetime.fromisoformat(schedule_end_date)
                sb_update_data = ScheduleBaselineUpdate(**sb_kwargs)

                updated_baseline = await sb_service.update_schedule_baseline(
                    root_id=baseline.schedule_baseline_id,
                    baseline_in=sb_update_data,
                    actor_id=UUID(context.user_id),
                    branch=context.branch_name or "main",
                )

                result["schedule_baseline"] = {
                    "id": str(updated_baseline.schedule_baseline_id),
                    "name": updated_baseline.name,
                    "start_date": updated_baseline.start_date.isoformat()
                    if updated_baseline.start_date
                    else None,
                    "end_date": updated_baseline.end_date.isoformat()
                    if updated_baseline.end_date
                    else None,
                    "progression_type": updated_baseline.progression_type,
                    "description": updated_baseline.description,
                    "branch": updated_baseline.branch,
                }
            else:
                result["schedule_baseline_warning"] = (
                    "Schedule baseline not found for this cost element; "
                    "schedule update skipped"
                )

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
    description="Delete cost element (cascades to schedule baseline and forecast).",
    permissions=["cost-element-delete"],
    category="cost-elements",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_element(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost element.

    Cascades the delete to the associated schedule baseline and forecast.

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

        # Call service method (cascades to schedule baseline and forecast)
        await service.soft_delete(
            cost_element_id=UUID(cost_element_id),
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
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
# COST ELEMENT TYPE TOOLS
# =============================================================================


@ai_tool(
    name="find_cost_element_types",
    description="Find cost element types by ID or search/filter.",
    permissions=["cost-element-type-read"],
    category="cost-element-types",
    risk_level=RiskLevel.LOW,
)
async def find_cost_element_types(
    cost_element_type_id: str | None = None,
    department_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost element types by ID or search/filter.

    If cost_element_type_id is provided, returns a single type. Otherwise
    returns a filtered list.

    Args:
        cost_element_type_id: Optional UUID to fetch a single cost element type
        department_id: Optional department ID to filter cost element types
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., "name", "code")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with cost element type details or list with pagination info

    Raises:
        ValueError: If invalid filter parameters
    """
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
                "department_id": str(cost_element_type.department_id),
            }

        # List mode with filters
        filters: dict[str, Any] = {}
        if department_id:
            filters["department_id"] = UUID(department_id)

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
                    "department_id": str(t.department_id),
                }
                for t in types
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError:
        return {"error": f"Invalid cost element type ID: {cost_element_type_id}"}
    except Exception as e:
        logger.error(f"Error in find_cost_element_types: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_cost_element_type",
    description="Create cost element type under a department.",
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
    description="Update cost element type.",
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

    Only updates fields that are provided.

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
    """
    try:
        from app.services.cost_element_type_service import CostElementTypeService

        service = CostElementTypeService(context.session)

        # Build update data dict - only include non-None fields
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
    description="Delete cost element type.",
    permissions=["cost-element-type-delete"],
    category="cost-element-types",
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
# BATCH COST ELEMENT TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_cost_elements",
    description="Batch create multiple cost elements under the same WBE. "
    "All items share the parent wbe_id and optional schedule dates/progression type. "
    "Each item provides its own code, name, budget_amount, cost_element_type_id, and "
    "optional description. Pre-validates all codes for duplicates before creating any. "
    "Maximum 50 items per batch.",
    permissions=["cost-element-create"],
    category="cost-elements",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_cost_elements(
    wbe_id: str,
    items: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
    progression_type: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost elements under the same WBE.

    Args:
        wbe_id: UUID of the parent WBE
        items: List of dicts, each with {code, name, budget_amount, cost_element_type_id, description?}
        start_date: Optional shared schedule start date (ISO format)
        end_date: Optional shared schedule end date (ISO format)
        progression_type: Optional shared progression type (LINEAR, GAUSSIAN, LOGARITHMIC)
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_cost_elements", context)

    try:
        from datetime import datetime
        from typing import cast
        from uuid import UUID

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement as CostElementModel
        from app.models.schemas.cost_element import CostElementCreate
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
            if item.get("budget_amount") is None:
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'budget_amount'"
                    },
                    context,
                )
            if not item.get("cost_element_type_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_type_id'"
                    },
                    context,
                )

        # Check for duplicate codes within the batch
        codes = [it["code"] for it in items]
        if len(codes) != len(set(codes)):
            dupes = {c for c in codes if codes.count(c) > 1}
            return add_temporal_metadata(
                {"error": f"Duplicate codes in batch: {dupes}"}, context
            )

        # Check for duplicates in the database (single query)
        branch = context.branch_name or "main"
        dedup_stmt = select(
            CostElementModel.cost_element_id, CostElementModel.code
        ).where(
            CostElementModel.code.in_(codes),
            CostElementModel.wbe_id == UUID(wbe_id),
            CostElementModel.branch == branch,
            func.upper(cast(Any, CostElementModel).valid_time).is_(None),
            cast(Any, CostElementModel).deleted_at.is_(None),
        )
        dedup_result = await context.session.execute(dedup_stmt)
        existing_rows = dedup_result.all()
        if existing_rows:
            existing_codes = {row.code for row in existing_rows}
            return add_temporal_metadata(
                {
                    "error": f"Cost elements with codes already exist under this WBE: {existing_codes}. "
                    "Use a different code or update the existing cost elements.",
                    "existing_codes": list(existing_codes),
                },
                context,
            )

        # Parse shared schedule dates
        schedule_start = datetime.fromisoformat(start_date) if start_date else None
        schedule_end = datetime.fromisoformat(end_date) if end_date else None

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            ce_data = CostElementCreate(
                wbe_id=UUID(wbe_id),
                cost_element_type_id=UUID(item["cost_element_type_id"]),
                code=item["code"],
                name=item["name"],
                budget_amount=item["budget_amount"],
                description=item.get("description"),
                branch=branch,
                schedule_start_date=schedule_start,
                schedule_end_date=schedule_end,
                schedule_progression_type=progression_type,
            )
            cost_element = await service.create_cost_element(
                element_in=ce_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(cost_element.cost_element_id),
                    "code": cost_element.code,
                    "name": cost_element.name,
                    "budget_amount": float(cost_element.budget_amount)
                    if cost_element.budget_amount
                    else None,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost elements under WBE {wbe_id}",
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
    name="batch_update_cost_elements",
    description="Batch update multiple cost elements. Each item must include cost_element_id "
    "and any fields to update (code, name, budget_amount, description, cost_element_type_id). "
    "Maximum 50 items per batch.",
    permissions=["cost-element-update"],
    category="cost-elements",
    risk_level=RiskLevel.HIGH,
)
async def batch_update_cost_elements(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch update cost elements.

    Args:
        items: List of dicts, each with {cost_element_id, code?, name?, budget_amount?, description?, cost_element_type_id?}
        context: Injected tool execution context

    Returns:
        Dictionary with updated items list, total count, and message
    """
    log_temporal_context("batch_update_cost_elements", context)

    try:
        from uuid import UUID

        from app.models.schemas.cost_element import CostElementUpdate
        from app.services.cost_element_service import CostElementService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate cost_element_id on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_id'"
                    },
                    context,
                )

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            update_kwargs: dict[str, Any] = {"branch": branch}
            if "code" in item and item["code"] is not None:
                update_kwargs["code"] = item["code"]
            if "name" in item and item["name"] is not None:
                update_kwargs["name"] = item["name"]
            if "budget_amount" in item and item["budget_amount"] is not None:
                update_kwargs["budget_amount"] = item["budget_amount"]
            if "description" in item and item["description"] is not None:
                update_kwargs["description"] = item["description"]
            if (
                "cost_element_type_id" in item
                and item["cost_element_type_id"] is not None
            ):
                update_kwargs["cost_element_type_id"] = UUID(
                    item["cost_element_type_id"]
                )

            update_data = CostElementUpdate(**update_kwargs)

            cost_element = await service.update(
                cost_element_id=UUID(item["cost_element_id"]),
                element_in=update_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(cost_element.cost_element_id),
                    "code": cost_element.code,
                    "name": cost_element.name,
                    "budget_amount": float(cost_element.budget_amount)
                    if cost_element.budget_amount
                    else None,
                }
            )

        result = {
            "updated": results,
            "total": len(results),
            "message": f"Updated {len(results)} cost elements",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_update_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="batch_delete_cost_elements",
    description="Batch soft delete multiple cost elements. "
    "Cascades the delete to associated schedule baselines and forecasts. "
    "This is a destructive operation requiring expert execution mode. "
    "Maximum 50 items per batch.",
    permissions=["cost-element-delete"],
    category="cost-elements",
    risk_level=RiskLevel.CRITICAL,
)
async def batch_delete_cost_elements(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch soft delete cost elements.

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
        branch = context.branch_name or "main"
        deleted_ids: list[str] = []

        for ce_id in cost_element_ids:
            await service.soft_delete(
                cost_element_id=UUID(ce_id),
                actor_id=actor_id,
                branch=branch,
            )
            deleted_ids.append(ce_id)

        result = {
            "deleted": deleted_ids,
            "total": len(deleted_ids),
            "message": f"Soft deleted {len(deleted_ids)} cost elements "
            "(schedule baselines and forecasts also deleted)",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_delete_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="get_budget_status_batch",
    description="Get budget status for multiple cost elements in a single call. "
    "Returns budget, used, remaining, and percentage for each cost element. "
    "Maximum 50 items per batch.",
    permissions=["cost-element-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def get_budget_status_batch(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch get budget status for cost elements.

    Args:
        cost_element_ids: List of cost element UUIDs
        context: Injected tool execution context

    Returns:
        Dictionary with budget statuses list and total count
    """
    log_temporal_context("get_budget_status_batch", context)

    try:
        from uuid import UUID

        from app.services.cost_registration_service import CostRegistrationService

        if len(cost_element_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not cost_element_ids:
            return add_temporal_metadata(
                {"error": "No cost element IDs provided"}, context
            )

        service = CostRegistrationService(context.session)
        branch = context.branch_name or "main"
        statuses: list[dict[str, Any]] = []

        for ce_id in cost_element_ids:
            status = await service.get_budget_status(
                cost_element_id=UUID(ce_id),
                as_of=context.as_of,
                branch=branch,
            )
            statuses.append(
                {
                    "cost_element_id": str(status.cost_element_id),
                    "budget": float(status.budget),
                    "used": float(status.used),
                    "remaining": float(status.remaining),
                    "percentage": float(status.percentage),
                }
            )

        result = {
            "statuses": statuses,
            "total": len(statuses),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in get_budget_status_batch: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="get_cost_element_summaries",
    description="Get comprehensive summaries for multiple cost elements in a single call. "
    "Each summary includes forecast data, budget status, and latest progress. "
    "Aggregates data from ForecastService, CostRegistrationService, and ProgressEntryService. "
    "Maximum 50 items per batch.",
    permissions=["forecast-read", "cost-registration-read", "progress-entry-read"],
    category="summary",
    risk_level=RiskLevel.LOW,
)
async def get_cost_element_summaries(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch get comprehensive summaries for cost elements.

    Args:
        cost_element_ids: List of cost element UUIDs
        context: Injected tool execution context

    Returns:
        Dictionary with summaries list and total count
    """
    log_temporal_context("get_cost_element_summaries", context)

    try:
        from uuid import UUID

        from app.services.cost_registration_service import CostRegistrationService
        from app.services.forecast_service import ForecastService
        from app.services.progress_entry_service import ProgressEntryService

        if len(cost_element_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not cost_element_ids:
            return add_temporal_metadata(
                {"error": "No cost element IDs provided"}, context
            )

        forecast_service = ForecastService(context.session)
        cost_service = CostRegistrationService(context.session)
        progress_service = ProgressEntryService(context.session)
        branch = context.branch_name or "main"

        summaries: list[dict[str, Any]] = []

        for ce_id in cost_element_ids:
            try:
                ce_uuid = UUID(ce_id)
            except ValueError:
                summaries.append({"cost_element_id": ce_id, "error": "Invalid UUID"})
                continue

            summary: dict[str, Any] = {"cost_element_id": ce_id}

            # Get forecast data
            try:
                forecast = await forecast_service.get_for_cost_element(
                    cost_element_id=ce_uuid,
                    branch=branch,
                )
                if forecast:
                    summary["forecast"] = {
                        "id": str(forecast.forecast_id),
                        "eac_amount": float(forecast.eac_amount)
                        if forecast.eac_amount
                        else None,
                        "basis_of_estimate": forecast.basis_of_estimate,
                        "branch": forecast.branch,
                    }
                else:
                    summary["forecast"] = None
            except Exception:
                summary["forecast"] = None

            # Get budget status
            try:
                budget_status = await cost_service.get_budget_status(
                    cost_element_id=ce_uuid,
                    as_of=context.as_of,
                    branch=branch,
                )
                summary["budget_status"] = {
                    "budget": float(budget_status.budget),
                    "used": float(budget_status.used),
                    "remaining": float(budget_status.remaining),
                    "percentage": float(budget_status.percentage),
                }
            except Exception:
                summary["budget_status"] = None

            # Get latest progress
            try:
                progress = await progress_service.get_latest_progress(
                    cost_element_id=ce_uuid,
                    as_of=context.as_of,
                )
                if progress:
                    summary["progress"] = {
                        "progress_entry_id": str(progress.progress_entry_id),
                        "progress_percentage": float(progress.progress_percentage)
                        if progress.progress_percentage
                        else None,
                        "notes": progress.notes,
                    }
                else:
                    summary["progress"] = None
            except Exception:
                summary["progress"] = None

            summaries.append(summary)

        result = {
            "summaries": summaries,
            "total": len(summaries),
            "message": f"Retrieved summaries for {len(summaries)} cost elements",
        }
        return add_temporal_metadata(result, context)
    except Exception as e:
        logger.error(f"Error in get_cost_element_summaries: {e}")
        return add_temporal_metadata({"error": str(e)}, context)
