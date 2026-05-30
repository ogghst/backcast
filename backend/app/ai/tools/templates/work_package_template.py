"""Work Package tool template for wrapping WorkPackageService methods.

This template provides AI tools for PMI Work Package management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Work Packages in Backcast (ANSI-748):
- Work Packages are the lowest WBS level where budget is allocated and tracked
- They belong to Control Accounts (WBS Element x Organizational Unit intersection)
- They hold budget_amount and have 1:1 relationships with Schedule Baselines and Forecasts
- They are BRANCHABLE (supports change orders) and VERSIONABLE (tracks changes)

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
from app.models.schemas.work_package import WorkPackageCreate, WorkPackageUpdate

logger = logging.getLogger(__name__)

BATCH_SIZE_LIMIT = 50

# =============================================================================
# WORK PACKAGE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_work_packages",
    description="Find work packages by ID or search/filter.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def find_work_packages(
    work_package_id: str | None = None,
    control_account_id: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find work packages by ID or search/filter.

    Context: Provides database session and work package service for querying work packages.

    Args:
        work_package_id: UUID of a specific work package to retrieve (returns single)
        control_account_id: UUID of the control account to list work packages for
        project_id: UUID of the project to list work packages for
        status: Optional filter by status (open/closed)
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Single work package dict if work_package_id provided, otherwise list result.

    Raises:
        ValueError: If IDs are not valid UUID format
    """
    log_temporal_context("find_work_packages", context)

    try:
        from app.core.versioning.enums import BranchMode
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)
        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGED
            if context.branch_mode == "merged"
            else BranchMode.ISOLATED
        )

        # Single work package lookup
        if work_package_id:
            wp = await service.get_as_of(
                entity_id=UUID(work_package_id),
                as_of=context.as_of,
                branch=branch,
                branch_mode=branch_mode,
            )

            if not wp:
                return add_temporal_metadata(
                    {"error": f"Work package {work_package_id} not found"}, context
                )

            wp_result: dict[str, Any] = {
                "work_package_id": str(wp.work_package_id),
                "name": wp.name,
                "code": wp.code,
                "budget_amount": float(wp.budget_amount)
                if wp.budget_amount is not None
                else None,
                "description": wp.description,
                "status": wp.status,
                "control_account_id": str(wp.control_account_id),
                "schedule_baseline_id": str(wp.schedule_baseline_id)
                if wp.schedule_baseline_id
                else None,
                "forecast_id": str(wp.forecast_id) if wp.forecast_id else None,
                "branch": wp.branch,
            }
            return add_temporal_metadata(wp_result, context)

        # List work packages
        ca_filter = UUID(control_account_id) if control_account_id else None

        work_packages, total = await service.get_work_packages(
            control_account_id=ca_filter,
            status=status,
            skip=skip,
            limit=limit,
            branch=branch,
            branch_mode=branch_mode,
            as_of=context.as_of,
        )

        result: dict[str, Any] = {
            "work_packages": [
                {
                    "work_package_id": str(wp.work_package_id),
                    "name": wp.name,
                    "code": wp.code,
                    "budget_amount": float(wp.budget_amount)
                    if wp.budget_amount is not None
                    else None,
                    "description": wp.description,
                    "status": wp.status,
                    "control_account_id": str(wp.control_account_id),
                    "branch": wp.branch,
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
        logger.error(f"Error in find_work_packages: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_work_package",
    description="Create PMI work package under a control account with budget.",
    permissions=["work-package-create"],
    category="work-packages",
    risk_level=RiskLevel.HIGH,
)
async def create_work_package(
    control_account_id: str,
    name: str,
    code: str,
    budget_amount: float = 0.0,
    description: str | None = None,
    status: str = "open",
    start_date: str | None = None,
    end_date: str | None = None,
    progression_type: str | None = None,
    eac_amount: float | None = None,
    basis_of_estimate: str | None = None,
    control_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new PMI Work Package under a Control Account.

    Context: Provides database session and work package service for creating work packages.

    Args:
        control_account_id: UUID of the parent Control Account
        name: Work package name
        code: Work package code (e.g., "WP-001")
        budget_amount: Allocated budget amount (defaults to 0.0)
        description: Optional description
        status: Status (open or closed, defaults to "open")
        start_date: Optional start date for the schedule baseline (ISO format)
        end_date: Optional end date for the schedule baseline (ISO format)
        progression_type: Optional progression type (LINEAR, GAUSSIAN, LOGARITHMIC)
        eac_amount: Optional EAC amount for auto-created forecast (defaults to budget_amount)
        basis_of_estimate: Optional basis of estimate for forecast (defaults to "Initial forecast")
        control_date: Optional control date for valid_time start (ISO format)
        context: Injected tool execution context

    Returns:
        Dictionary with created work package details

    Raises:
        ValueError: If invalid input or control account not found

    Example:
        >>> result = await create_work_package(
        ...     control_account_id="...",
        ...     name="Mechanical Assembly WP",
        ...     code="WP-001",
        ...     budget_amount=50000.0,
        ... )
        >>> print(f"Created work package: {result['work_package_id']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        parsed_control_date = (
            datetime.fromisoformat(control_date) if control_date else None
        )
        schedule_start = datetime.fromisoformat(start_date) if start_date else None
        schedule_end = datetime.fromisoformat(end_date) if end_date else None

        wp_data = WorkPackageCreate(
            control_account_id=UUID(control_account_id),
            name=name,
            code=code,
            budget_amount=Decimal(str(budget_amount)),
            description=description,
            status=status,
            branch=context.branch_name or "main",
            control_date=parsed_control_date,
            schedule_start_date=schedule_start,
            schedule_end_date=schedule_end,
            schedule_progression_type=progression_type,
            eac_amount=Decimal(str(eac_amount)) if eac_amount is not None else None,
            basis_of_estimate=basis_of_estimate,
        )

        wp = await service.create_work_package(
            data=wp_data,
            actor_id=UUID(context.user_id),
            control_date=parsed_control_date,
        )

        return {
            "work_package_id": str(wp.work_package_id),
            "name": wp.name,
            "code": wp.code,
            "budget_amount": float(wp.budget_amount)
            if wp.budget_amount is not None
            else None,
            "description": wp.description,
            "status": wp.status,
            "control_account_id": str(wp.control_account_id),
            "branch": wp.branch,
            "schedule_baseline_id": str(wp.schedule_baseline_id)
            if wp.schedule_baseline_id
            else None,
            "forecast_id": str(wp.forecast_id) if wp.forecast_id else None,
            "message": "Work package created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_work_package: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_work_package",
    description="Update work package fields.",
    permissions=["work-package-update"],
    category="work-packages",
    risk_level=RiskLevel.HIGH,
)
async def update_work_package(
    work_package_id: str,
    name: str | None = None,
    code: str | None = None,
    budget_amount: float | None = None,
    description: str | None = None,
    status: str | None = None,
    schedule_start_date: str | None = None,
    schedule_end_date: str | None = None,
    schedule_progression_type: str | None = None,
    eac_amount: float | None = None,
    basis_of_estimate: str | None = None,
    control_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing work package.

    Context: Provides database session and work package service for updating work packages.
    Schedule baseline and forecast fields are propagated to their respective entities.

    Args:
        work_package_id: UUID of the work package to update
        name: New name (optional)
        code: New code (optional)
        budget_amount: New budget amount (optional)
        description: New description (optional)
        status: New status (optional)
        schedule_start_date: New schedule start date in ISO format (optional)
        schedule_end_date: New schedule end date in ISO format (optional)
        schedule_progression_type: New progression type (optional)
        eac_amount: New EAC amount for the forecast (optional)
        basis_of_estimate: New basis of estimate for the forecast (optional)
        control_date: Control date for valid_time start in ISO format (optional)
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
        ...     budget_amount=20000.0
        ... )
        >>> print(f"Updated work package status: {result['status']}")
    """
    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)

        parsed_control_date = (
            datetime.fromisoformat(control_date) if control_date else None
        )

        update_kwargs: dict[str, Any] = {}
        if name is not None:
            update_kwargs["name"] = name
        if code is not None:
            update_kwargs["code"] = code
        if budget_amount is not None:
            update_kwargs["budget_amount"] = Decimal(str(budget_amount))
        if description is not None:
            update_kwargs["description"] = description
        if status is not None:
            update_kwargs["status"] = status
        if parsed_control_date is not None:
            update_kwargs["control_date"] = parsed_control_date
        # Schedule baseline update params
        if schedule_start_date is not None:
            update_kwargs["schedule_start_date"] = datetime.fromisoformat(
                schedule_start_date
            )
        if schedule_end_date is not None:
            update_kwargs["schedule_end_date"] = datetime.fromisoformat(
                schedule_end_date
            )
        if schedule_progression_type is not None:
            update_kwargs["schedule_progression_type"] = schedule_progression_type
        # Forecast update params
        if eac_amount is not None:
            update_kwargs["eac_amount"] = Decimal(str(eac_amount))
        if basis_of_estimate is not None:
            update_kwargs["basis_of_estimate"] = basis_of_estimate
        update_kwargs["branch"] = context.branch_name or "main"

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
            "code": wp.code,
            "budget_amount": float(wp.budget_amount)
            if wp.budget_amount is not None
            else None,
            "description": wp.description,
            "status": wp.status,
            "control_account_id": str(wp.control_account_id),
            "branch": wp.branch,
            "schedule_baseline_id": str(wp.schedule_baseline_id)
            if wp.schedule_baseline_id
            else None,
            "forecast_id": str(wp.forecast_id) if wp.forecast_id else None,
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
    description="Delete work package.",
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
            root_id=UUID(work_package_id),
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
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
    name="get_work_package_budget_status",
    description="Get budget status for a work package (budget vs actual).",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def get_work_package_budget_status(
    work_package_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get budget status for a Work Package.

    Compares budget_amount against actual costs from Cost Registrations
    through Cost Elements (EOC) under this Work Package.

    Args:
        work_package_id: UUID of the work package
        context: Injected tool execution context

    Returns:
        Dictionary with budget, used, remaining, and percentage.

    Raises:
        ValueError: If work_package_id is not a valid UUID format
    """
    log_temporal_context("get_work_package_budget_status", context)

    try:
        from app.services.work_package_service import WorkPackageService

        service = WorkPackageService(context.session)
        branch = context.branch_name or "main"

        budget_status = await service.get_budget_status(
            work_package_id=UUID(work_package_id),
            as_of=context.as_of,
            branch=branch,
        )

        result: dict[str, Any] = {
            "work_package_id": str(budget_status["work_package_id"]),
            "budget": float(budget_status["budget"]),
            "used": float(budget_status["used"]),
            "remaining": float(budget_status["remaining"]),
            "percentage": float(budget_status["percentage"]),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_work_package_budget_status: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="batch_get_work_package_budget_status",
    description="Get budget status (budget vs actual) for multiple work packages at once. "
    "Returns budget, used, remaining, and percentage for each. "
    "Use this instead of calling get_work_package_budget_status repeatedly.",
    permissions=["work-package-read"],
    category="work-packages",
    risk_level=RiskLevel.LOW,
)
async def batch_get_work_package_budget_status(
    work_package_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get budget status for multiple Work Packages in a single call.

    Compares budget_amount against actual costs from Cost Registrations
    through Cost Elements (EOC) for each Work Package. This is far more
    efficient than calling get_work_package_budget_status N times.

    Args:
        work_package_ids: List of UUID strings for the work packages
        context: Injected tool execution context

    Returns:
        Dictionary with results list, total count, and message.

    Raises:
        ValueError: If any work_package_id is not a valid UUID format
    """
    log_temporal_context("batch_get_work_package_budget_status", context)

    try:
        from app.services.work_package_service import WorkPackageService

        if not work_package_ids:
            return add_temporal_metadata(
                {"error": "No work_package_ids provided"}, context
            )

        if len(work_package_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {
                    "error": f"Batch size ({len(work_package_ids)}) exceeds maximum "
                    f"of {BATCH_SIZE_LIMIT}"
                },
                context,
            )

        service = WorkPackageService(context.session)
        branch = context.branch_name or "main"

        parsed_ids = [UUID(wpid) for wpid in work_package_ids]

        batch_results = await service.get_budget_status_batch(
            work_package_ids=parsed_ids,
            as_of=context.as_of,
            branch=branch,
        )

        results: list[dict[str, Any]] = []
        for wp_id in parsed_ids:
            status = batch_results.get(wp_id)
            if status is not None:
                results.append(
                    {
                        "work_package_id": str(status["work_package_id"]),
                        "budget": float(status["budget"]),
                        "used": float(status["used"]),
                        "remaining": float(status["remaining"]),
                        "percentage": float(status["percentage"]),
                    }
                )

        not_found_count = len(parsed_ids) - len(results)
        message = f"Retrieved budget status for {len(results)} work packages"
        if not_found_count > 0:
            message += f" ({not_found_count} not found)"

        result: dict[str, Any] = {
            "results": results,
            "total": len(results),
            "message": message,
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in batch_get_work_package_budget_status: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)
