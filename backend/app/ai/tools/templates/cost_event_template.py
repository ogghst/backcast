"""Cost Event tool template for wrapping CostEventService methods.

This template provides AI tools for cost event management and Cost of Quality
(COQ) queries. The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Cost Events in Backcast (ANSI-748):
- Cost Events track quality events and cost impacts for projects
- They are VERSIONABLE but NOT BRANCHABLE -- events are global facts
- They support COQ tracking with categories (prevention, appraisal, etc.)
- Cost allocations distribute event costs across Cost Elements (EOCs)
- COQ metrics complement standard EVM indicators (CPQ, CPIq, QPI)

Usage:
    1. Import CostEventService methods
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format

TEMPORAL CONTEXT PATTERN:
For read tools (those that query versioned entities):
- Import temporal logging helpers: log_temporal_context, add_temporal_metadata
- Call log_temporal_context() at tool start for observability
- Call add_temporal_metadata() on return to include temporal context in results
"""

import logging
from datetime import datetime
from decimal import Decimal
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
from app.models.schemas.cost_event import (
    CostEventCreate,
    CostEventUpdate,
    QualityCostAllocation,
)

logger = logging.getLogger(__name__)


# =============================================================================
# COST EVENT CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_cost_events",
    description=(
        "Find cost events by ID or search/filter (project_id required for lists; "
        "filter by wbs_element_id, coq_category, status). "
        "Paginated — check 'total'/'has_more' and page forward with 'page'/'limit', "
        "narrow with 'search' first."
    ),
    permissions=["cost-event-read"],
    category="cost-management",
    risk_level=RiskLevel.LOW,
)
async def find_cost_events(
    cost_event_id: str | None = None,
    project_id: str | None = None,
    wbs_element_id: str | None = None,
    coq_category: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find cost events by ID or search/filter.

    Args:
        cost_event_id: UUID of a specific cost event to retrieve (returns single)
        project_id: UUID of the project to list cost events for
        wbs_element_id: Optional WBS Element ID to filter
        coq_category: Optional COQ category filter
        status: Optional status filter (open/closed)
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        context: Injected tool execution context

    Returns:
        Single cost event dict if cost_event_id provided, otherwise list result.

    Raises:
        ValueError: If IDs are not valid UUID format
    """
    log_temporal_context("find_cost_events", context)
    limit = get_page_limit(limit)
    skip = (page - 1) * limit

    try:
        from app.services.cost_event_service import CostEventService

        service = CostEventService(context.session)

        # Single cost event lookup
        if cost_event_id:
            event = await service.get_by_id(UUID(cost_event_id))

            if not event:
                return add_temporal_metadata(
                    {"error": f"Cost event {cost_event_id} not found"}, context
                )

            result: dict[str, Any] = {
                "cost_event_id": str(event.cost_event_id),
                "name": event.name,
                "cost_event_type_id": str(event.cost_event_type_id),
                "cost_event_type_code": getattr(event, "cost_event_type_code", None),
                "cost_event_type_name": getattr(event, "cost_event_type_name", None),
                "description": event.description,
                "status": event.status,
                "external_event_id": event.external_event_id,
                "event_date": event.event_date.isoformat()
                if event.event_date
                else None,
                "coq_category": event.coq_category,
                "estimated_impact": float(event.estimated_impact)
                if event.estimated_impact is not None
                else None,
                "schedule_impact_days": event.schedule_impact_days,
                "project_id": str(event.project_id),
                "wbs_element_id": str(event.wbs_element_id)
                if event.wbs_element_id
                else None,
            }
            return add_temporal_metadata(result, context)

        # List cost events
        if not project_id:
            return add_temporal_metadata(
                {"error": "project_id is required when cost_event_id is not provided"},
                context,
            )

        events, total = await service.get_cost_events(
            project_id=UUID(project_id),
            wbs_element_id=UUID(wbs_element_id) if wbs_element_id else None,
            coq_category=coq_category,
            status=status,
            skip=skip,
            limit=limit,
            as_of=context.as_of,
        )

        list_result: dict[str, Any] = {
            "cost_events": [
                {
                    "cost_event_id": str(ev.cost_event_id),
                    "name": ev.name,
                    "cost_event_type_id": str(ev.cost_event_type_id),
                    "cost_event_type_code": getattr(ev, "cost_event_type_code", None),
                    "cost_event_type_name": getattr(ev, "cost_event_type_name", None),
                    "description": ev.description,
                    "status": ev.status,
                    "external_event_id": ev.external_event_id,
                    "event_date": ev.event_date.isoformat() if ev.event_date else None,
                    "coq_category": ev.coq_category,
                    "estimated_impact": float(ev.estimated_impact)
                    if ev.estimated_impact is not None
                    else None,
                    "schedule_impact_days": ev.schedule_impact_days,
                    "project_id": str(ev.project_id),
                    "wbs_element_id": str(ev.wbs_element_id)
                    if ev.wbs_element_id
                    else None,
                }
                for ev in events
            ],
            "total": total,
            "page": page,
            "page_count": calc_page_count(total, limit),
            "limit": limit,
            "has_more": page < calc_page_count(total, limit),
        }
        return add_temporal_metadata(list_result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in find_cost_events: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_cost_event",
    description="Create cost event under a project.",
    permissions=["cost-event-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_event(
    project_id: str,
    name: str,
    cost_event_type_id: str,
    description: str | None = None,
    status: str = "open",
    external_event_id: str | None = None,
    event_date: str | None = None,
    coq_category: str | None = None,
    estimated_impact: float = 0.0,
    schedule_impact_days: int | None = None,
    wbs_element_id: str | None = None,
    cost_allocations: list[dict[str, Any]] | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost event.

    Args:
        project_id: UUID of the parent project
        name: Cost event name
        cost_event_type_id: UUID of the cost event type
        description: Optional description
        status: Status (open or closed, defaults to "open")
        external_event_id: Optional external reference identifier (e.g., QMS ID)
        event_date: Optional event date in ISO format
        coq_category: Optional COQ category (prevention, appraisal,
            internal_failure, external_failure)
        estimated_impact: Estimated cost impact (defaults to 0.0)
        schedule_impact_days: Optional schedule impact in days
        wbs_element_id: Optional WBS Element root ID where the event occurred
        cost_allocations: Optional list of cost allocation dicts with keys:
            cost_element_id (str UUID), amount (float > 0), description (str, optional)
        context: Injected tool execution context

    Returns:
        Dictionary with created cost event details

    Raises:
        ValueError: If invalid input or project not found

    Example:
        >>> result = await create_cost_event(
        ...     project_id="...",
        ...     name="NCR-2026-001",
        ...     cost_event_type_id="...",
        ...     coq_category="internal_failure",
        ...     estimated_impact=15000.0,
        ... )
        >>> print(f"Created cost event: {result['cost_event_id']}")
    """
    try:
        from app.services.cost_event_service import CostEventService

        service = CostEventService(context.session)

        parsed_event_date = datetime.fromisoformat(event_date) if event_date else None

        allocations: list[QualityCostAllocation] | None = None
        if cost_allocations:
            allocations = [
                QualityCostAllocation(
                    cost_element_id=UUID(alloc["cost_element_id"]),
                    amount=Decimal(str(alloc["amount"])),
                    description=alloc.get("description"),
                )
                for alloc in cost_allocations
            ]

        event_data = CostEventCreate(
            project_id=UUID(project_id),
            name=name,
            cost_event_type_id=UUID(cost_event_type_id),
            description=description,
            status=status,
            external_event_id=external_event_id,
            event_date=parsed_event_date,
            coq_category=coq_category,
            estimated_impact=Decimal(str(estimated_impact)),
            schedule_impact_days=schedule_impact_days,
            wbs_element_id=UUID(wbs_element_id) if wbs_element_id else None,
            cost_allocations=allocations,
        )

        event = await service.create_cost_event(
            data=event_data,
            actor_id=UUID(context.user_id),
        )

        return {
            "cost_event_id": str(event.cost_event_id),
            "name": event.name,
            "cost_event_type_id": str(event.cost_event_type_id),
            "description": event.description,
            "status": event.status,
            "external_event_id": event.external_event_id,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "coq_category": event.coq_category,
            "estimated_impact": float(event.estimated_impact)
            if event.estimated_impact is not None
            else None,
            "schedule_impact_days": event.schedule_impact_days,
            "project_id": str(event.project_id),
            "wbs_element_id": str(event.wbs_element_id)
            if event.wbs_element_id
            else None,
            "message": "Cost event created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_cost_event: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_cost_event",
    description="Update cost event fields.",
    permissions=["cost-event-update"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_event(
    cost_event_id: str,
    name: str | None = None,
    cost_event_type_id: str | None = None,
    description: str | None = None,
    status: str | None = None,
    external_event_id: str | None = None,
    event_date: str | None = None,
    coq_category: str | None = None,
    estimated_impact: float | None = None,
    schedule_impact_days: int | None = None,
    cost_allocations: list[dict[str, Any]] | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost event.

    Args:
        cost_event_id: UUID of the cost event to update
        name: New name (optional)
        cost_event_type_id: New cost event type ID (optional)
        description: New description (optional)
        status: New status (optional)
        external_event_id: New external reference (optional)
        event_date: New event date in ISO format (optional)
        coq_category: New COQ category (optional)
        estimated_impact: New estimated impact (optional)
        schedule_impact_days: New schedule impact (optional)
        cost_allocations: Replacement cost allocations (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost event details

    Raises:
        ValueError: If cost_event_id is invalid
        KeyError: If cost event not found
    """
    try:
        from app.services.cost_event_service import CostEventService

        service = CostEventService(context.session)

        allocations: list[QualityCostAllocation] | None = None
        if cost_allocations is not None:
            allocations = [
                QualityCostAllocation(
                    cost_element_id=UUID(alloc["cost_element_id"]),
                    amount=Decimal(str(alloc["amount"])),
                    description=alloc.get("description"),
                )
                for alloc in cost_allocations
            ]

        update_kwargs: dict[str, Any] = {}
        if name is not None:
            update_kwargs["name"] = name
        if cost_event_type_id is not None:
            update_kwargs["cost_event_type_id"] = UUID(cost_event_type_id)
        if description is not None:
            update_kwargs["description"] = description
        if status is not None:
            update_kwargs["status"] = status
        if external_event_id is not None:
            update_kwargs["external_event_id"] = external_event_id
        if event_date is not None:
            update_kwargs["event_date"] = datetime.fromisoformat(event_date)
        if coq_category is not None:
            update_kwargs["coq_category"] = coq_category
        if estimated_impact is not None:
            update_kwargs["estimated_impact"] = Decimal(str(estimated_impact))
        if schedule_impact_days is not None:
            update_kwargs["schedule_impact_days"] = schedule_impact_days
        if allocations is not None:
            update_kwargs["cost_allocations"] = allocations

        update_data = CostEventUpdate(**update_kwargs)

        event = await service.update_cost_event(
            cost_event_id=UUID(cost_event_id),
            data=update_data,
            actor_id=UUID(context.user_id),
        )

        return {
            "cost_event_id": str(event.cost_event_id),
            "name": event.name,
            "cost_event_type_id": str(event.cost_event_type_id),
            "description": event.description,
            "status": event.status,
            "external_event_id": event.external_event_id,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "coq_category": event.coq_category,
            "estimated_impact": float(event.estimated_impact)
            if event.estimated_impact is not None
            else None,
            "schedule_impact_days": event.schedule_impact_days,
            "project_id": str(event.project_id),
            "message": "Cost event updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Cost event {cost_event_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_cost_event: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_cost_event",
    description="Delete cost event.",
    permissions=["cost-event-delete"],
    category="cost-management",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_event(
    cost_event_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost event.

    Args:
        cost_event_id: UUID of the cost event to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If cost_event_id is invalid
        KeyError: If cost event not found
    """
    try:
        from app.services.cost_event_service import CostEventService

        service = CostEventService(context.session)

        await service.soft_delete_cost_event(
            cost_event_id=UUID(cost_event_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": cost_event_id,
            "message": "Cost event deleted",
        }
    except ValueError:
        return {"error": f"Invalid cost event ID: {cost_event_id}"}
    except KeyError:
        return {"error": f"Cost event {cost_event_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_cost_event: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_coq_data",
    description="Get Cost of Quality summary and metrics.",
    permissions=["cost-event-read"],
    category="cost-management",
    risk_level=RiskLevel.LOW,
)
async def get_coq_data(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get Cost of Quality summary, metrics, and allocations for a project.

    Args:
        project_id: UUID of the project
        context: Injected tool execution context

    Returns:
        Dictionary with coq_summary, coq_metrics, and allocations.

    Raises:
        ValueError: If project_id is not a valid UUID format
    """
    log_temporal_context("get_coq_data", context)

    try:
        from app.services.cost_event_service import CostEventService

        service = CostEventService(context.session)

        # Fetch summary
        summary = await service.get_summary(
            project_id=UUID(project_id),
            as_of=context.as_of,
        )

        # Fetch metrics
        metrics = await service.get_coq_metrics(
            project_id=UUID(project_id),
            as_of=context.as_of,
        )

        # Fetch allocations for all quality cost events
        events, _ = await service.get_cost_events(
            project_id=UUID(project_id),
            skip=0,
            limit=1000,
            as_of=context.as_of,
        )

        all_allocations: list[dict[str, Any]] = []
        for ev in events:
            try:
                ev_allocations = await service.get_allocations(
                    UUID(str(ev.cost_event_id))
                )
                all_allocations.extend(
                    {
                        "cost_event_id": str(ev.cost_event_id),
                        "cost_registration_id": str(alloc.cost_registration_id),
                        "cost_element_id": str(alloc.cost_element_id),
                        "amount": float(alloc.amount),
                        "description": alloc.description,
                        "cost_element_name": getattr(alloc, "cost_element_name", None),
                        "wbs_element_code": getattr(alloc, "wbs_element_code", None),
                    }
                    for alloc in ev_allocations
                )
            except Exception:
                pass  # Skip allocations for events that may not have any

        result: dict[str, Any] = {
            "coq_summary": {
                "total_cost": float(summary.total_cost),
                "conformance_cost": float(summary.conformance_cost),
                "nonconformance_cost": float(summary.nonconformance_cost),
                "prevention_cost": float(summary.prevention_cost),
                "appraisal_cost": float(summary.appraisal_cost),
                "internal_failure_cost": float(summary.internal_failure_cost),
                "external_failure_cost": float(summary.external_failure_cost),
                "total_schedule_days": summary.total_schedule_days,
                "impact_count": summary.impact_count,
                "coq_ratio": float(summary.coq_ratio)
                if summary.coq_ratio is not None
                else None,
            },
            "coq_metrics": {
                "total_coq": float(metrics.total_coq),
                "cpq": float(metrics.cpq),
                "cpq_percentage": float(metrics.cpq_percentage),
                "cpiq": float(metrics.cpiq) if metrics.cpiq is not None else None,
                "qpi": float(metrics.qpi) if metrics.qpi is not None else None,
                "qpi_rating": metrics.qpi_rating,
                "total_ac": float(metrics.total_ac),
                "coq_ratio": float(metrics.coq_ratio)
                if metrics.coq_ratio is not None
                else None,
            },
            "allocations": all_allocations,
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_coq_data: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


# =============================================================================
# BATCH COST EVENT TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_cost_events",
    description="Batch create cost events under a project. Max 50 items.",
    permissions=["cost-event-create"],
    category="cost-management",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_cost_events(
    project_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost events under the same project.

    Args:
        project_id: UUID of the parent project
        items: List of dicts, each with {name, cost_event_type_id, description?,
               status?, external_event_id?, event_date?, coq_category?,
               estimated_impact?, schedule_impact_days?, wbs_element_id?,
               cost_allocations?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_cost_events", context)

    try:
        from app.services.cost_event_service import CostEventService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("name"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'name'"},
                    context,
                )
            if not item.get("cost_event_type_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_event_type_id'"
                    },
                    context,
                )

        service = CostEventService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            parsed_event_date = (
                datetime.fromisoformat(item["event_date"])
                if item.get("event_date")
                else None
            )

            allocations: list[QualityCostAllocation] | None = None
            if item.get("cost_allocations"):
                allocations = [
                    QualityCostAllocation(
                        cost_element_id=UUID(alloc["cost_element_id"]),
                        amount=Decimal(str(alloc["amount"])),
                        description=alloc.get("description"),
                    )
                    for alloc in item["cost_allocations"]
                ]

            event_data = CostEventCreate(
                project_id=UUID(project_id),
                name=item["name"],
                cost_event_type_id=UUID(item["cost_event_type_id"]),
                description=item.get("description"),
                status=item.get("status", "open"),
                external_event_id=item.get("external_event_id"),
                event_date=parsed_event_date,
                coq_category=item.get("coq_category"),
                estimated_impact=Decimal(str(item.get("estimated_impact", 0.0))),
                schedule_impact_days=item.get("schedule_impact_days"),
                wbs_element_id=UUID(item["wbs_element_id"])
                if item.get("wbs_element_id")
                else None,
                cost_allocations=allocations,
            )

            event = await service.create_cost_event(
                data=event_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "cost_event_id": str(event.cost_event_id),
                    "name": event.name,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost events under project {project_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_create_cost_events: {e}")
        return add_temporal_metadata({"error": str(e)}, context)
