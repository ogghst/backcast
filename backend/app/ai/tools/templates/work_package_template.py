"""Work Package tool template for wrapping WorkPackageService methods.

This template provides AI tools for work package management and Cost of Quality
(COQ) queries. The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Work Packages in Backcast:
- Work Packages are project-scoped cost grouping mechanisms with multiple types
  (quality_impact, site_visit, production_phase, warranty_batch, commissioning)
- They are VERSIONABLE but NOT BRANCHABLE — financial facts are global
- Quality Impact packages support COQ category tracking and cost allocations
- COQ metrics complement standard EVM indicators (CPQ, CPIq, QPI)

Usage:
    1. Import WorkPackageService methods
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
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.work_package import (
    QualityCostAllocation,
    WorkPackageCreate,
    WorkPackageUpdate,
)

logger = logging.getLogger(__name__)

# =============================================================================
# WORK PACKAGE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="list_work_packages",
    description="List work packages for a project with optional filtering by "
    "package type, COQ category, or status. Supports types: quality_impact, "
    "site_visit, production_phase, warranty_batch, commissioning. "
    "Temporal context (as_of date) is enforced by the system.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def list_work_packages(
    project_id: str,
    package_type: str | None = None,
    coq_category: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List work packages for a project with optional filtering.

    Context: Provides database session and work package service for querying work packages.

    Args:
        project_id: UUID of the project to list work packages for
        package_type: Optional filter by package type (quality_impact, site_visit,
            production_phase, warranty_batch, commissioning)
        coq_category: Optional filter by COQ category (prevention, appraisal,
            internal_failure, external_failure)
        status: Optional filter by status (open, closed)
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - work_packages: List of work package objects
        - total: Total number of work packages matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned
        - _temporal_context: Temporal context metadata (as_of)

    Raises:
        ValueError: If project_id is not a valid UUID format

    Example:
        >>> result = await list_work_packages(project_id="...", package_type="quality_impact")
        >>> print(f"Found {result['total']} work packages")
        >>> for wp in result['work_packages']:
        ...     print(f"- {wp['name']}: {wp['package_type']}")
    """
    log_temporal_context("list_work_packages", context)

    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        work_packages, total = await service.get_work_packages(
            project_id=UUID(project_id),
            skip=skip,
            limit=limit,
            coq_category=coq_category,
            package_type=package_type,
            status=status,
            as_of=context.as_of,
        )

        result = {
            "work_packages": [
                {
                    "work_package_id": str(wp.work_package_id),
                    "name": wp.name,
                    "package_type": wp.package_type,
                    "description": wp.description,
                    "status": wp.status,
                    "external_event_id": wp.external_event_id,
                    "event_date": wp.event_date.isoformat() if wp.event_date else None,
                    "coq_category": wp.coq_category,
                    "cost_impact": float(wp.cost_impact) if wp.cost_impact else None,
                    "schedule_impact_days": wp.schedule_impact_days,
                    "project_id": str(wp.project_id),
                }
                for wp in work_packages
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
        logger.error(f"Error in list_work_packages: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_work_package",
    description="Get detailed information about a specific work package by ID.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def get_work_package(
    work_package_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single work package by ID with computed actual cost.

    Context: Provides database session and work package service for retrieving work package data.

    Args:
        work_package_id: UUID of the work package to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with work package details including actual cost, or error if not found

    Raises:
        ValueError: If work_package_id is not a valid UUID format

    Example:
        >>> result = await get_work_package("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"Work Package: {result['name']}")
        ...     print(f"Actual Cost: ${result['actual_cost']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        wp = await service.get_by_id(UUID(work_package_id))

        if not wp:
            return {"error": f"Work package {work_package_id} not found"}

        actual_cost = await service.compute_actual_cost(UUID(work_package_id))

        return {
            "work_package_id": str(wp.work_package_id),
            "name": wp.name,
            "package_type": wp.package_type,
            "description": wp.description,
            "status": wp.status,
            "external_event_id": wp.external_event_id,
            "event_date": wp.event_date.isoformat() if wp.event_date else None,
            "coq_category": wp.coq_category,
            "cost_impact": float(wp.cost_impact) if wp.cost_impact else None,
            "schedule_impact_days": wp.schedule_impact_days,
            "project_id": str(wp.project_id),
            "actual_cost": float(actual_cost) if actual_cost is not None else None,
        }
    except ValueError:
        return {"error": f"Invalid work package ID: {work_package_id}"}
    except Exception as e:
        logger.error(f"Error in get_work_package: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_work_package",
    description="Create a new work package under a project. Supports types: "
    "quality_impact, site_visit, production_phase, warranty_batch, commissioning. "
    "Quality impact packages can include COQ category and schedule impact. "
    "Optionally include cost allocations.",
    permissions=["work-package-create"],
    category="work-packages",
    risk_level=RiskLevel.HIGH,
)
async def create_work_package(
    project_id: str,
    name: str,
    package_type: str,
    description: str | None = None,
    status: str = "open",
    external_event_id: str | None = None,
    event_date: str | None = None,
    coq_category: str | None = None,
    cost_impact: float = 0.0,
    schedule_impact_days: int | None = None,
    control_date: str | None = None,
    cost_allocations: list[dict[str, Any]] | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new work package.

    Context: Provides database session and work package service for creating work packages.

    Args:
        project_id: UUID of the parent project
        name: Work package name
        package_type: Type of work package (quality_impact, site_visit,
            production_phase, warranty_batch, commissioning)
        description: Optional description
        status: Status (open or closed, defaults to "open")
        external_event_id: Optional external reference identifier (e.g., QMS ID)
        event_date: Optional event date in ISO format (e.g., "2026-05-10")
        coq_category: Optional COQ category (prevention, appraisal,
            internal_failure, external_failure)
        cost_impact: Estimated cost impact (defaults to 0.0)
        schedule_impact_days: Optional schedule impact in days
        control_date: Optional control date for valid_time start (ISO format)
        cost_allocations: Optional list of cost allocation dicts with keys:
            cost_element_id (str UUID), amount (float > 0), description (str, optional)
        context: Injected tool execution context

    Returns:
        Dictionary with created work package details

    Raises:
        ValueError: If invalid input or project not found

    Example:
        >>> result = await create_work_package(
        ...     project_id="...",
        ...     name="NCR-2026-001",
        ...     package_type="quality_impact",
        ...     coq_category="internal_failure",
        ...     cost_impact=15000.0,
        ...     cost_allocations=[
        ...         {"cost_element_id": "...", "amount": 10000.0},
        ...         {"cost_element_id": "...", "amount": 5000.0},
        ...     ]
        ... )
        >>> print(f"Created work package: {result['work_package_id']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        parsed_event_date = datetime.fromisoformat(event_date) if event_date else None
        parsed_control_date = (
            datetime.fromisoformat(control_date) if control_date else None
        )

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

        wp_data = WorkPackageCreate(
            project_id=UUID(project_id),
            name=name,
            package_type=package_type,
            description=description,
            status=status,
            external_event_id=external_event_id,
            event_date=parsed_event_date,
            coq_category=coq_category,
            cost_impact=Decimal(str(cost_impact)),
            schedule_impact_days=schedule_impact_days,
            control_date=parsed_control_date,
            cost_allocations=allocations,
        )

        wp = await service.create_work_package(
            data=wp_data,
            actor_id=UUID(context.user_id),
            control_date=parsed_control_date,
        )

        return {
            "work_package_id": str(wp.work_package_id),
            "name": wp.name,
            "package_type": wp.package_type,
            "description": wp.description,
            "status": wp.status,
            "external_event_id": wp.external_event_id,
            "event_date": wp.event_date.isoformat() if wp.event_date else None,
            "coq_category": wp.coq_category,
            "cost_impact": float(wp.cost_impact) if wp.cost_impact else None,
            "schedule_impact_days": wp.schedule_impact_days,
            "project_id": str(wp.project_id),
            "message": "Work package created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_work_package: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_work_package",
    description="Update an existing work package. Only updates fields that are provided.",
    permissions=["work-package-update"],
    category="work-packages",
    risk_level=RiskLevel.HIGH,
)
async def update_work_package(
    work_package_id: str,
    name: str | None = None,
    package_type: str | None = None,
    description: str | None = None,
    status: str | None = None,
    external_event_id: str | None = None,
    event_date: str | None = None,
    coq_category: str | None = None,
    cost_impact: float | None = None,
    schedule_impact_days: int | None = None,
    control_date: str | None = None,
    cost_allocations: list[dict[str, Any]] | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing work package.

    Context: Provides database session and work package service for updating work packages.

    Args:
        work_package_id: UUID of the work package to update
        name: New name (optional)
        package_type: New package type (optional)
        description: New description (optional)
        status: New status (optional)
        external_event_id: New external reference identifier (optional)
        event_date: New event date in ISO format (optional)
        coq_category: New COQ category (optional)
        cost_impact: New cost impact (optional)
        schedule_impact_days: New schedule impact in days (optional)
        control_date: Control date for valid_time start in ISO format (optional)
        cost_allocations: Replacement cost allocations list (optional, replaces all existing)
        context: Injected tool execution context

    Returns:
        Dictionary with updated work package details

    Raises:
        ValueError: If work_package_id is invalid
        KeyError: If work package not found

    Example:
        >>> result = await update_work_package(
        ...     work_package_id="...",
        ...     status="closed",
        ...     cost_impact=20000.0
        ... )
        >>> print(f"Updated work package status: {result['status']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        parsed_control_date = (
            datetime.fromisoformat(control_date) if control_date else None
        )

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
        if package_type is not None:
            update_kwargs["package_type"] = package_type
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
        if cost_impact is not None:
            update_kwargs["cost_impact"] = Decimal(str(cost_impact))
        if schedule_impact_days is not None:
            update_kwargs["schedule_impact_days"] = schedule_impact_days
        if parsed_control_date is not None:
            update_kwargs["control_date"] = parsed_control_date
        if allocations is not None:
            update_kwargs["cost_allocations"] = allocations

        update_data = WorkPackageUpdate(**update_kwargs)

        wp = await service.update_work_package(
            work_package_id=UUID(work_package_id),
            data=update_data,
            actor_id=UUID(context.user_id),
            control_date=parsed_control_date,
        )

        return {
            "work_package_id": str(wp.work_package_id),
            "name": wp.name,
            "package_type": wp.package_type,
            "description": wp.description,
            "status": wp.status,
            "external_event_id": wp.external_event_id,
            "event_date": wp.event_date.isoformat() if wp.event_date else None,
            "coq_category": wp.coq_category,
            "cost_impact": float(wp.cost_impact) if wp.cost_impact else None,
            "schedule_impact_days": wp.schedule_impact_days,
            "project_id": str(wp.project_id),
            "message": "Work package updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Work package {work_package_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_work_package: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_work_package",
    description="Soft delete a work package. The package is marked as deleted "
    "but remains for audit.",
    permissions=["work-package-delete"],
    category="work-packages",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_work_package(
    work_package_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a work package.

    Context: Provides database session and work package service for deletion.

    Args:
        work_package_id: UUID of the work package to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If work_package_id is invalid
        KeyError: If work package not found

    Example:
        >>> result = await delete_work_package("...")
        >>> print(f"Deleted work package: {result['id']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        await service.soft_delete(
            work_package_id=UUID(work_package_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": work_package_id,
            "message": "Work package deleted",
        }
    except ValueError:
        return {"error": f"Invalid work package ID: {work_package_id}"}
    except KeyError:
        return {"error": f"Work package {work_package_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_work_package: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_work_package_allocations",
    description="Get cost allocations (CostRegistration entries) for a work package. "
    "Returns how costs are distributed across cost elements.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def get_work_package_allocations(
    work_package_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get cost allocations for a work package.

    Context: Provides database session and work package service for retrieving allocation data.

    Args:
        work_package_id: UUID of the work package
        context: Injected tool execution context

    Returns:
        Dictionary with list of cost allocations or error if not found

    Raises:
        ValueError: If work_package_id is not a valid UUID format

    Example:
        >>> result = await get_work_package_allocations("...")
        >>> for alloc in result['allocations']:
        ...     print(f"- {alloc['cost_element_name']}: ${alloc['amount']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        allocations = await service.get_allocations(UUID(work_package_id))

        return {
            "work_package_id": work_package_id,
            "allocations": [
                {
                    "cost_registration_id": str(alloc.cost_registration_id),
                    "cost_element_id": str(alloc.cost_element_id),
                    "amount": float(alloc.amount),
                    "description": alloc.description,
                    "cost_element_name": alloc.cost_element_name,
                    "wbe_code": alloc.wbe_code,
                }
                for alloc in allocations
            ],
            "total_allocations": len(allocations),
        }
    except ValueError:
        return {"error": f"Invalid work package ID: {work_package_id}"}
    except Exception as e:
        logger.error(f"Error in get_work_package_allocations: {e}")
        return {"error": str(e)}


# =============================================================================
# COQ QUERY TOOLS
# =============================================================================


@ai_tool(
    name="get_coq_summary",
    description="Get Cost of Quality summary for a project. Only includes "
    "quality_impact-typed work packages. Returns total cost, "
    "4-category breakdown (prevention, appraisal, internal_failure, "
    "external_failure), COQ ratio.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def get_coq_summary(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get COQ summary for a project.

    Context: Provides database session and work package service for COQ aggregation.

    Args:
        project_id: UUID of the project
        context: Injected tool execution context

    Returns:
        Dictionary with COQ summary metrics:
        - total_cost: Total COQ cost
        - conformance_cost: Prevention + Appraisal cost
        - nonconformance_cost: Internal + External failure cost
        - prevention_cost: Prevention category cost
        - appraisal_cost: Appraisal category cost
        - internal_failure_cost: Internal failure category cost
        - external_failure_cost: External failure category cost
        - total_schedule_days: Total schedule impact days
        - impact_count: Number of quality impact work packages
        - coq_ratio: COQ cost as percentage of project budget
        - _temporal_context: Temporal context metadata (as_of)

    Raises:
        ValueError: If project_id is not a valid UUID format

    Example:
        >>> result = await get_coq_summary(project_id="...")
        >>> print(f"Total COQ: ${result['total_cost']}")
        >>> print(f"COQ Ratio: {result['coq_ratio']}%")
    """
    log_temporal_context("get_coq_summary", context)

    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        summary = await service.get_summary(
            project_id=UUID(project_id),
            as_of=context.as_of,
        )

        result = {
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
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_coq_summary: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_coq_metrics",
    description="Get Cost of Quality metrics complementing standard EVM indicators. "
    "Includes CPQ, CPIq, QPI, and COQ ratio. Only includes quality_impact-typed "
    "work packages.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def get_coq_metrics(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get COQ metrics for a project.

    Context: Provides database session and work package service for COQ metric computation.

    Args:
        project_id: UUID of the project
        context: Injected tool execution context

    Returns:
        Dictionary with COQ metrics:
        - total_coq: Total Cost of Quality
        - cpq: Cost of Poor Quality (nonconformance only)
        - cpq_percentage: CPQ as percentage of total actual cost
        - cpiq: CPQ / Actual Cost (quality's share of cost variance)
        - qpi: Quality Performance Index (normalized from CPQ%)
        - qpi_rating: Human-readable QPI rating
        - total_ac: Total Actual Cost for the project
        - coq_ratio: Total COQ as percentage of project budget
        - _temporal_context: Temporal context metadata (as_of)

    Raises:
        ValueError: If project_id is not a valid UUID format

    Example:
        >>> result = await get_coq_metrics(project_id="...")
        >>> print(f"QPI: {result['qpi']} ({result['qpi_rating']})")
        >>> print(f"CPQ: ${result['cpq']} ({result['cpq_percentage']}%)")
    """
    log_temporal_context("get_coq_metrics", context)

    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        metrics = await service.get_coq_metrics(
            project_id=UUID(project_id),
            as_of=context.as_of,
        )

        result = {
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
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_coq_metrics: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)
