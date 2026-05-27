"""Forecast, Cost Registration, and Progress Entry tool template.

This template provides AI tools for three service layers:
1. Forecast Service - Branchable entity for cost element (EOC) forecasts
2. Cost Registration Service - Versionable entity for actual cost tracking
3. Progress Entry Service - Versionable entity for work progress tracking

The key principle is:
    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Service Layers:
- Forecast: Estimate at Complete (EAC) for cost elements / EOCs (branchable)
- Cost Registration: Actual costs incurred against budget (versionable)
- Progress Entry: Work completion percentage tracking (versionable)

TEMPORAL CONTEXT PATTERN:
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

logger = logging.getLogger(__name__)

BATCH_SIZE_LIMIT = 50


# =============================================================================
# FORECAST TOOLS (Branchable Entity)
# =============================================================================


@ai_tool(
    name="create_forecast",
    description="Create forecast for a cost element.",
    permissions=["forecast-create"],
    category="forecast",
    risk_level=RiskLevel.HIGH,
)
async def create_forecast(
    cost_element_id: str,
    eac_amount: float,
    basis_of_estimate: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new forecast for a cost element."""
    log_temporal_context("create_forecast", context)

    try:
        from app.services.forecast_service import (
            ForecastAlreadyExistsError,
            ForecastService,
        )

        service = ForecastService(context.session)

        forecast = await service.create_for_cost_element(
            cost_element_id=UUID(cost_element_id),
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
            control_date=context.as_of,
            eac_amount=Decimal(str(eac_amount)),
            basis_of_estimate=basis_of_estimate,
        )

        result = {
            "id": str(forecast.forecast_id),
            "cost_element_id": cost_element_id,
            "eac_amount": float(forecast.eac_amount) if forecast.eac_amount else None,
            "basis_of_estimate": forecast.basis_of_estimate,
            "branch": forecast.branch,
            "message": f"Forecast created for cost element {cost_element_id}",
        }
        return add_temporal_metadata(result, context)
    except ForecastAlreadyExistsError as e:
        return add_temporal_metadata({"error": str(e)}, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in create_forecast: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="update_forecast",
    description="Update forecast for a cost element.",
    permissions=["forecast-update"],
    category="forecast",
    risk_level=RiskLevel.HIGH,
)
async def update_forecast(
    forecast_id: str,
    eac_amount: float | None = None,
    basis_of_estimate: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing forecast."""
    log_temporal_context("update_forecast", context)

    try:
        from app.models.schemas.forecast import ForecastUpdate
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        update_data: dict[str, Any] = {"branch": context.branch_name or "main"}
        if eac_amount is not None:
            update_data["eac_amount"] = Decimal(str(eac_amount))
        if basis_of_estimate is not None:
            update_data["basis_of_estimate"] = basis_of_estimate

        forecast_in = ForecastUpdate(**update_data)

        forecast = await service.update_forecast(
            forecast_id=UUID(forecast_id),
            forecast_in=forecast_in,
            actor_id=UUID(context.user_id),
            control_date=context.as_of,
        )

        result = {
            "id": str(forecast.forecast_id),
            "eac_amount": float(forecast.eac_amount) if forecast.eac_amount else None,
            "basis_of_estimate": forecast.basis_of_estimate,
            "branch": forecast.branch,
        }
        return add_temporal_metadata(result, context)
    except ValueError:
        return add_temporal_metadata(
            {"error": f"Invalid forecast ID: {forecast_id}"}, context
        )
    except KeyError:
        return add_temporal_metadata(
            {"error": f"Forecast {forecast_id} not found"}, context
        )
    except Exception as e:
        logger.error(f"Error in update_forecast: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# COST REGISTRATION TOOLS (Versionable Entity)
# =============================================================================


@ai_tool(
    name="create_cost_registration",
    description="Record an actual cost against a cost element.",
    permissions=["cost-registration-create"],
    category="cost-registration",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_registration(
    cost_element_id: str,
    amount: float,
    description: str | None = None,
    invoice_number: str | None = None,
    vendor_reference: str | None = None,
    registration_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new cost registration."""
    log_temporal_context("create_cost_registration", context)

    try:
        from app.models.schemas.cost_registration import CostRegistrationCreate
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        reg_date = None
        if registration_date:
            reg_date = datetime.fromisoformat(registration_date)

        registration_in = CostRegistrationCreate(
            cost_element_id=UUID(cost_element_id),
            amount=Decimal(str(amount)),
            description=description,
            invoice_number=invoice_number,
            vendor_reference=vendor_reference,
            registration_date=reg_date,
        )

        registration = await service.create_cost_registration(
            registration_in=registration_in,
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        result = {
            "id": str(registration.cost_registration_id),
            "cost_element_id": str(registration.cost_element_id),
            "amount": float(registration.amount) if registration.amount else None,
            "description": registration.description,
            "invoice_number": registration.invoice_number,
            "vendor_reference": registration.vendor_reference,
            "registration_date": registration.registration_date.isoformat()
            if registration.registration_date
            else None,
            "message": "Cost registration created",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in create_cost_registration: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="update_cost_registration",
    description="Update a cost registration entry.",
    permissions=["cost-registration-update"],
    category="cost-registration",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_registration(
    cost_registration_id: str,
    amount: float | None = None,
    description: str | None = None,
    invoice_number: str | None = None,
    vendor_reference: str | None = None,
    registration_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing cost registration."""
    log_temporal_context("update_cost_registration", context)

    try:
        from app.models.schemas.cost_registration import CostRegistrationUpdate
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        reg_date = None
        if registration_date:
            reg_date = datetime.fromisoformat(registration_date)

        update_data: dict[str, Any] = {}
        if amount is not None:
            update_data["amount"] = Decimal(str(amount))
        if description is not None:
            update_data["description"] = description
        if invoice_number is not None:
            update_data["invoice_number"] = invoice_number
        if vendor_reference is not None:
            update_data["vendor_reference"] = vendor_reference
        if reg_date is not None:
            update_data["registration_date"] = reg_date

        if not update_data:
            return add_temporal_metadata(
                {"error": "No fields provided to update"}, context
            )

        registration_in = CostRegistrationUpdate(**update_data)

        registration = await service.update_cost_registration(
            cost_registration_id=UUID(cost_registration_id),
            registration_in=registration_in,
            actor_id=UUID(context.user_id),
            control_date=context.as_of,
        )

        result = {
            "id": str(registration.cost_registration_id),
            "cost_element_id": str(registration.cost_element_id),
            "amount": float(registration.amount) if registration.amount else None,
            "description": registration.description,
            "invoice_number": registration.invoice_number,
            "vendor_reference": registration.vendor_reference,
            "registration_date": registration.registration_date.isoformat()
            if registration.registration_date
            else None,
            "message": "Cost registration updated",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata(
            {"error": f"Cost registration not found: {e}"}, context
        )
    except Exception as e:
        logger.error(f"Error in update_cost_registration: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="delete_cost_registration",
    description="Delete a cost registration entry.",
    permissions=["cost-registration-delete"],
    category="cost-registration",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_registration(
    cost_registration_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost registration."""
    log_temporal_context("delete_cost_registration", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        await service.soft_delete(
            cost_registration_id=UUID(cost_registration_id),
            actor_id=UUID(context.user_id),
            control_date=context.as_of,
        )

        result = {
            "id": cost_registration_id,
            "message": "Cost registration soft deleted. "
            "The registration is marked as deleted but preserved for audit trail.",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata(
            {"error": f"Cost registration not found: {e}"}, context
        )
    except Exception as e:
        logger.error(f"Error in delete_cost_registration: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# PROGRESS ENTRY TOOLS (Versionable Entity)
# =============================================================================


@ai_tool(
    name="create_progress_entry",
    description="Record work progress for a cost element.",
    permissions=["progress-entry-create"],
    category="progress-entry",
    risk_level=RiskLevel.HIGH,
)
async def create_progress_entry(
    cost_element_id: str,
    progress_percentage: float,
    notes: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new progress entry."""
    log_temporal_context("create_progress_entry", context)

    try:
        from typing import Any, cast

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement
        from app.models.schemas.progress_entry import ProgressEntryCreate
        from app.services.progress_entry_service import ProgressEntryService

        # Resolve work_package_id from cost_element_id
        ce_stmt = (
            select(CostElement.work_package_id)
            .where(
                CostElement.cost_element_id == UUID(cost_element_id),
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        ce_result = await context.session.execute(ce_stmt)
        wp_id = ce_result.scalar_one_or_none()
        if wp_id is None:
            return add_temporal_metadata(
                {"error": f"Cost element {cost_element_id} not found"}, context
            )

        service = ProgressEntryService(context.session)

        progress_in = ProgressEntryCreate(
            work_package_id=wp_id,
            progress_percentage=Decimal(str(progress_percentage)),
            notes=notes,
        )

        progress = await service.create(
            actor_id=UUID(context.user_id),
            progress_in=progress_in,
            control_date=context.as_of,
        )

        result = {
            "progress_entry_id": str(progress.progress_entry_id),
            "work_package_id": str(progress.work_package_id),
            "progress_percentage": float(progress.progress_percentage)
            if progress.progress_percentage
            else None,
            "notes": progress.notes,
            "message": "Progress entry created",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in create_progress_entry: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# MERGED READ TOOLS
# =============================================================================


@ai_tool(
    name="get_cost_element_details",
    description="Get CE details: forecast EAC, budget status, costs, trends.",
    permissions=["forecast-read", "cost-registration-read"],
    category="forecast",
    risk_level=RiskLevel.LOW,
)
async def get_cost_element_details(
    cost_element_id: str,
    include_trends: bool = False,
    include_cumulative: bool = False,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get cost element details: forecast, budget status, cost registrations, and optional trends.

    Replaces: get_forecast, compare_forecast_to_budget, get_budget_status,
    list_cost_registrations, get_cost_registration, get_cost_trends,
    get_cumulative_costs, get_cost_element_summary.
    """
    log_temporal_context("get_cost_element_details", context)

    try:
        from typing import Any, cast

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement
        from app.services.cost_registration_service import CostRegistrationService
        from app.services.forecast_service import ForecastService

        # Resolve work_package_id from cost_element_id
        ce_stmt = (
            select(CostElement.work_package_id)
            .where(
                CostElement.cost_element_id == UUID(cost_element_id),
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        ce_result = await context.session.execute(ce_stmt)
        wp_id = ce_result.scalar_one_or_none()
        if wp_id is None:
            return add_temporal_metadata(
                {"error": f"Cost element {cost_element_id} not found"}, context
            )

        forecast_service = ForecastService(context.session)
        cost_service = CostRegistrationService(context.session)
        branch = context.branch_name or "main"

        # Get forecast data
        forecast_data = None
        try:
            forecast = await forecast_service.get_for_work_package(
                work_package_id=wp_id,
                branch=branch,
            )
            if forecast:
                forecast_data = {
                    "id": str(forecast.forecast_id),
                    "eac_amount": float(forecast.eac_amount)
                    if forecast.eac_amount
                    else None,
                    "basis_of_estimate": forecast.basis_of_estimate,
                    "approved_date": forecast.approved_date.isoformat()
                    if forecast.approved_date
                    else None,
                    "branch": forecast.branch,
                }
        except Exception:
            forecast_data = None

        # Get budget status
        budget_status = await cost_service.get_budget_status(
            work_package_id=wp_id,
            as_of=context.as_of,
            branch=branch,
        )

        budget_amount = float(budget_status.budget)
        used_amount = float(budget_status.used)
        eac_raw = forecast_data.get("eac_amount", 0.0) if forecast_data else 0.0
        eac_amount: float = float(eac_raw) if eac_raw is not None else 0.0
        variance = budget_amount - eac_amount
        percentage_used = float(budget_status.percentage)

        budget_status_data: dict[str, Any] = {
            "budget_amount": budget_amount,
            "eac_amount": eac_amount,
            "used": used_amount,
            "remaining": float(budget_status.remaining),
            "variance": variance,
            "percentage_used": percentage_used,
        }

        # Get recent cost registrations (limit 10)
        registrations, total, _wp_map = await cost_service.get_cost_registrations(
            filters={"cost_element_id": UUID(cost_element_id)},
            skip=0,
            limit=10,
            as_of=context.as_of,
        )

        cost_registrations_data = [
            {
                "id": str(reg.cost_registration_id),
                "cost_element_id": str(reg.cost_element_id),
                "amount": float(reg.amount) if reg.amount else None,
                "description": reg.description,
                "invoice_number": reg.invoice_number,
                "vendor_reference": reg.vendor_reference,
                "registration_date": reg.registration_date.isoformat()
                if reg.registration_date
                else None,
            }
            for reg in registrations
        ]

        result: dict[str, Any] = {
            "forecast": forecast_data,
            "budget_status": budget_status_data,
            "cost_registrations": cost_registrations_data,
        }

        # Optional: cost trends
        if include_trends:
            trends_data = None
            try:
                trends_data = await cost_service.get_costs_by_period(
                    cost_element_id=UUID(cost_element_id),
                    period="monthly",
                    start_date=datetime(2020, 1, 1),
                    end_date=None,
                    as_of=context.as_of,
                )
            except Exception:
                trends_data = None
            result["cost_trends"] = trends_data

        # Optional: cumulative costs
        if include_cumulative:
            cumulative_data = None
            try:
                cumulative_data = await cost_service.get_cumulative_costs(
                    cost_element_id=UUID(cost_element_id),
                    start_date=datetime(2020, 1, 1),
                    end_date=None,
                    as_of=context.as_of,
                )
            except Exception:
                cumulative_data = None
            result["cumulative_costs"] = cumulative_data

        return add_temporal_metadata(result, context)
    except ValueError:
        return add_temporal_metadata(
            {"error": f"Invalid cost element ID: {cost_element_id}"}, context
        )
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in get_cost_element_details: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="get_progress_data",
    description="Get progress data for a cost element.",
    permissions=["progress-entry-read"],
    category="progress",
    risk_level=RiskLevel.LOW,
)
async def get_progress_data(
    cost_element_id: str,
    progress_entry_id: str | None = None,
    include_history: bool = False,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get progress data for a cost element.

    Replaces: list_progress_entries, get_latest_progress, get_progress_entry,
    get_progress_history.
    """
    log_temporal_context("get_progress_data", context)

    try:
        from typing import Any, cast

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement
        from app.services.progress_entry_service import ProgressEntryService

        # Resolve work_package_id from cost_element_id
        ce_stmt = (
            select(CostElement.work_package_id)
            .where(
                CostElement.cost_element_id == UUID(cost_element_id),
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        ce_result = await context.session.execute(ce_stmt)
        wp_id = ce_result.scalar_one_or_none()
        if wp_id is None:
            return add_temporal_metadata(
                {"error": f"Cost element {cost_element_id} not found"}, context
            )

        service = ProgressEntryService(context.session)

        # If a specific entry ID is provided, return that single entry
        if progress_entry_id:
            progress = await service.get_as_of(
                UUID(progress_entry_id),
                branch=context.branch_name or "main",
                as_of=context.as_of,
            )

            if progress is None:
                return add_temporal_metadata(
                    {"error": f"Progress entry not found: {progress_entry_id}"}, context
                )

            single_result: dict[str, Any] = {
                "progress_entry_id": str(progress.progress_entry_id),
                "work_package_id": str(progress.work_package_id),
                "progress_percentage": float(progress.progress_percentage)
                if progress.progress_percentage
                else None,
                "notes": progress.notes,
            }
            return add_temporal_metadata(single_result, context)

        # If history is requested, return full paginated history
        if include_history:
            progress_entries, total = await service.get_progress_history(
                work_package_id=wp_id,
                skip=skip,
                limit=limit,
                as_of=context.as_of,
            )

            history_result: dict[str, Any] = {
                "progress_entries": [
                    {
                        "progress_entry_id": str(entry.progress_entry_id),
                        "work_package_id": str(entry.work_package_id),
                        "progress_percentage": float(entry.progress_percentage)
                        if entry.progress_percentage
                        else None,
                        "notes": entry.notes,
                    }
                    for entry in progress_entries
                ],
                "total": total,
                "skip": skip,
                "limit": limit,
            }
            return add_temporal_metadata(history_result, context)

        # Default: return latest progress + recent entries list
        latest_data = None
        try:
            progress = await service.get_latest_progress(
                work_package_id=wp_id,
                as_of=context.as_of,
            )
            if progress:
                latest_data = {
                    "progress_entry_id": str(progress.progress_entry_id),
                    "work_package_id": str(progress.work_package_id),
                    "progress_percentage": float(progress.progress_percentage)
                    if progress.progress_percentage
                    else None,
                    "notes": progress.notes,
                }
        except Exception:
            latest_data = None

        recent_entries, total = await service.get_progress_history(
            work_package_id=wp_id,
            skip=skip,
            limit=limit,
            as_of=context.as_of,
        )

        result: dict[str, Any] = {
            "latest_progress": latest_data,
            "progress_entries": [
                {
                    "progress_entry_id": str(entry.progress_entry_id),
                    "work_package_id": str(entry.work_package_id),
                    "progress_percentage": float(entry.progress_percentage)
                    if entry.progress_percentage
                    else None,
                    "notes": entry.notes,
                }
                for entry in recent_entries
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in get_progress_data: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# BATCH TOOLS (absorbed from batch_tools_template)
# =============================================================================


@ai_tool(
    name="batch_create_cost_registrations",
    description="Batch register actual costs for multiple cost elements.",
    permissions=["cost-registration-create"],
    category="cost-registration",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_cost_registrations(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost registrations.

    Args:
        items: List of dicts, each with {cost_element_id, amount, description?,
               invoice_number?, vendor_reference?, registration_date?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_cost_registrations", context)

    try:
        from decimal import Decimal as _Decimal

        from app.models.schemas.cost_registration import CostRegistrationCreate
        from app.services.cost_registration_service import CostRegistrationService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_id'"
                    },
                    context,
                )
            if item.get("amount") is None:
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'amount'"},
                    context,
                )

        service = CostRegistrationService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            reg_date = None
            if item.get("registration_date"):
                reg_date = datetime.fromisoformat(item["registration_date"])

            registration_in = CostRegistrationCreate(
                cost_element_id=UUID(item["cost_element_id"]),
                amount=_Decimal(str(item["amount"])),
                description=item.get("description"),
                invoice_number=item.get("invoice_number"),
                vendor_reference=item.get("vendor_reference"),
                registration_date=reg_date,
            )

            registration = await service.create_cost_registration(
                registration_in=registration_in,
                actor_id=actor_id,
                branch=branch,
            )
            results.append(
                {
                    "id": str(registration.cost_registration_id),
                    "cost_element_id": str(registration.cost_element_id),
                    "amount": float(registration.amount)
                    if registration.amount
                    else None,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost registrations",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_create_cost_registrations: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="batch_create_progress_entries",
    description="Batch create progress entries for multiple cost elements.",
    permissions=["progress-entry-create"],
    category="progress-entry",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_progress_entries(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create progress entries.

    Args:
        items: List of dicts, each with {cost_element_id, progress_percentage, notes?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_progress_entries", context)

    try:
        from decimal import Decimal as _Decimal

        from app.models.schemas.progress_entry import ProgressEntryCreate
        from app.services.progress_entry_service import ProgressEntryService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_id'"
                    },
                    context,
                )
            if item.get("progress_percentage") is None:
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'progress_percentage'"
                    },
                    context,
                )

        service = ProgressEntryService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            progress_in = ProgressEntryCreate(
                work_package_id=UUID(item["work_package_id"]),
                progress_percentage=_Decimal(str(item["progress_percentage"])),
                notes=item.get("notes"),
            )

            progress = await service.create(
                actor_id=actor_id,
                progress_in=progress_in,
                control_date=context.as_of,
            )
            results.append(
                {
                    "progress_entry_id": str(progress.progress_entry_id),
                    "work_package_id": str(progress.work_package_id),
                    "progress_percentage": float(progress.progress_percentage)
                    if progress.progress_percentage
                    else None,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} progress entries",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in batch_create_progress_entries: {e}")
        return add_temporal_metadata({"error": str(e)}, context)
