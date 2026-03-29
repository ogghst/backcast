"""Forecast, Cost Registration, and Progress Entry tool template.

This template provides AI tools for three service layers:
1. Forecast Service - Branchable entity for cost element forecasts
2. Cost Registration Service - Versionable entity for actual cost tracking
3. Progress Entry Service - Versionable entity for work progress tracking

The key principle is:
    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Service Layers:
- Forecast: Estimate at Complete (EAC) for cost elements (branchable)
- Cost Registration: Actual costs incurred against budget (versionable)
- Progress Entry: Work completion percentage tracking (versionable)

Usage:
    1. Import service methods from ForecastService, CostRegistrationService, ProgressEntryService
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
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext

logger = logging.getLogger(__name__)


# =============================================================================
# FORECAST TOOLS (Branchable Entity)
# =============================================================================


@ai_tool(
    name="get_forecast",
    description="Get the forecast for a specific cost element. "
    "Returns the Estimate at Complete (EAC), basis of estimate, and approval status. "
    "Temporal context (branch, as_of date) is enforced by the system.",
    permissions=["forecast-read"],
    category="forecast",
    risk_level=RiskLevel.LOW,
)
async def get_forecast(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get forecast for a cost element.

    Context: Provides database session and forecast service for retrieving forecasts.

    Args:
        cost_element_id: UUID of the cost element to get forecast for
        context: Injected tool execution context

    Returns:
        Dictionary with forecast details:
        - id: Forecast UUID
        - eac_amount: Estimate at Complete amount
        - basis_of_estimate: Basis for the estimate
        - approved_date: Approval date if approved
        - branch: Branch name
        - _temporal_context: Temporal context metadata

    Raises:
        ValueError: If cost_element_id is not a valid UUID format
        KeyError: If forecast is not found

    Example:
        >>> result = await get_forecast(cost_element_id="...")
        >>> if "error" not in result:
        ...     print(f"EAC: ${result['eac_amount']}")
        ...     print(f"Basis: {result['basis_of_estimate']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_forecast", context)

    try:
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        # Call service method
        forecast = await service.get_for_cost_element(
            cost_element_id=UUID(cost_element_id),
            branch=context.branch_name or "main",
        )

        if not forecast:
            return add_temporal_metadata(
                {"error": f"Forecast not found for cost element {cost_element_id}"},
                context,
            )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "id": str(forecast.forecast_id),
            "eac_amount": float(forecast.eac_amount) if forecast.eac_amount else None,
            "basis_of_estimate": forecast.basis_of_estimate,
            "approved_date": forecast.approved_date.isoformat() if forecast.approved_date else None,
            "approved_by": str(forecast.approved_by) if forecast.approved_by else None,
            "branch": forecast.branch,
        }
        return add_temporal_metadata(result, context)
    except ValueError:
        error_result = {"error": f"Invalid cost element ID: {cost_element_id}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_forecast: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_forecast",
    description="Create a new forecast for a cost element. "
    "Each cost element can have only one forecast per branch. "
    "Requires EAC amount and basis of estimate.",
    permissions=["forecast-create"],
    category="forecast",
    risk_level=RiskLevel.HIGH,
)
async def create_forecast(
    cost_element_id: str,
    eac_amount: float,
    basis_of_estimate: str,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new forecast for a cost element.

    Context: Provides database session and forecast service for creating forecasts.

    Args:
        cost_element_id: UUID of the cost element
        eac_amount: Estimate at Complete amount (must be non-negative)
        basis_of_estimate: Explanation for the forecast estimate
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with created forecast details

    Raises:
        ValueError: If cost_element_id is invalid or eac_amount is negative
        KeyError: If cost element not found
        Exception: If forecast already exists for this cost element

    Example:
        >>> result = await create_forecast(
        ...     cost_element_id="...",
        ...     eac_amount=105000.00,
        ...     basis_of_estimate="Based on historical trends"
        ... )
        >>> print(f"Created forecast: {result['id']}")
    """
    # Log temporal context for observability
    log_temporal_context("create_forecast", context)

    try:
        from app.models.schemas.forecast import ForecastCreate
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        # Create Pydantic schema
        forecast_in = ForecastCreate(
            eac_amount=Decimal(str(eac_amount)),
            basis_of_estimate=basis_of_estimate,
            branch=branch,
        )

        # Call service method
        forecast = await service.create_forecast(
            forecast_in=forecast_in,
            actor_id=UUID(context.user_id),
            branch=branch,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "id": str(forecast.forecast_id),
            "eac_amount": float(forecast.eac_amount) if forecast.eac_amount else None,
            "basis_of_estimate": forecast.basis_of_estimate,
            "branch": forecast.branch,
            "message": f"Forecast created for cost element {cost_element_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost element not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in create_forecast: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="update_forecast",
    description="Update an existing forecast with new EAC amount or basis of estimate. "
    "Supports branch isolation for change order workflows.",
    permissions=["forecast-update"],
    category="forecast",
    risk_level=RiskLevel.HIGH,
)
async def update_forecast(
    forecast_id: str,
    eac_amount: float | None = None,
    basis_of_estimate: str | None = None,
    branch: str = "main",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing forecast.

    Context: Provides database session and forecast service for updating forecasts.

    Args:
        forecast_id: UUID of the forecast to update
        eac_amount: New EAC amount (optional)
        basis_of_estimate: New basis of estimate (optional)
        branch: Branch name (default: "main")
        context: Injected tool execution context

    Returns:
        Dictionary with updated forecast details

    Raises:
        ValueError: If forecast_id is invalid
        KeyError: If forecast not found

    Example:
        >>> result = await update_forecast(
        ...     forecast_id="...",
        ...     eac_amount=107000.00,
        ...     basis_of_estimate="Updated after review"
        ... )
        >>> print(f"Updated forecast EAC: ${result['eac_amount']}")
    """
    # Log temporal context for observability
    log_temporal_context("update_forecast", context)

    try:
        from app.models.schemas.forecast import ForecastUpdate
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        # Create update schema with only provided fields
        update_data: dict[str, Any] = {"branch": branch}
        if eac_amount is not None:
            update_data["eac_amount"] = Decimal(str(eac_amount))
        if basis_of_estimate is not None:
            update_data["basis_of_estimate"] = basis_of_estimate

        forecast_in = ForecastUpdate(**update_data)

        # Call service method
        forecast = await service.update_forecast(
            forecast_id=UUID(forecast_id),
            forecast_in=forecast_in,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "id": str(forecast.forecast_id),
            "eac_amount": float(forecast.eac_amount) if forecast.eac_amount else None,
            "basis_of_estimate": forecast.basis_of_estimate,
            "branch": forecast.branch,
        }
        return add_temporal_metadata(result, context)
    except ValueError:
        error_result = {"error": f"Invalid forecast ID: {forecast_id}"}
        return add_temporal_metadata(error_result, context)
    except KeyError:
        error_result = {"error": f"Forecast {forecast_id} not found"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in update_forecast: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="compare_forecast_to_budget",
    description="Compare forecast EAC to budget for a cost element. "
    "Returns Variance at Completion (VAC), percentage over/under budget, and budget status. "
    "Use this to assess if a cost element is forecast to exceed its budget.",
    permissions=["forecast-read", "cost-registration-read"],
    category="forecast",
    risk_level=RiskLevel.LOW,
)
async def compare_forecast_to_budget(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Compare forecast to budget for a cost element.

    Context: Provides database session and services for forecast and budget data.

    Args:
        cost_element_id: UUID of the cost element to compare
        context: Injected tool execution context

    Returns:
        Dictionary with comparison data:
        - budget: Budget amount from cost element
        - forecast_eac: Forecast Estimate at Complete
        - vac: Variance at Completion (budget - forecast_eac)
        - vac_percentage: VAC as percentage of budget
        - status: "Over Budget", "Under Budget", or "On Budget"
        - _temporal_context: Temporal context metadata

    Raises:
        ValueError: If cost_element_id is invalid
        KeyError: If forecast or cost element not found

    Example:
        >>> result = await compare_forecast_to_budget(cost_element_id="...")
        >>> print(f"Budget: ${result['budget']}")
        >>> print(f"Forecast: ${result['forecast_eac']}")
        >>> print(f"Variance: ${result['vac']} ({result['vac_percentage']:.1f}%)")
    """
    # Log temporal context for observability
    log_temporal_context("compare_forecast_to_budget", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService
        from app.services.forecast_service import ForecastService

        forecast_service = ForecastService(context.session)
        cost_service = CostRegistrationService(context.session)

        # Get forecast
        forecast = await forecast_service.get_for_cost_element(
            cost_element_id=UUID(cost_element_id),
            branch=context.branch_name or "main",
        )

        if not forecast:
            return add_temporal_metadata(
                {"error": f"Forecast not found for cost element {cost_element_id}"},
                context,
            )

        # Get budget status (includes budget and used amounts)
        budget_status = await cost_service.get_budget_status(
            cost_element_id=UUID(cost_element_id),
            as_of=context.as_of,
            branch=context.branch_name or "main",
        )

        # Calculate variance
        budget = float(budget_status.budget)
        forecast_eac = float(forecast.eac_amount) if forecast.eac_amount else 0.0
        vac = budget - forecast_eac
        vac_percentage = (vac / budget * 100) if budget > 0 else 0.0

        # Determine status
        if abs(vac_percentage) < 1.0:  # Within 1%
            status = "On Budget"
        elif vac > 0:
            status = "Under Budget"
        else:
            status = "Over Budget"

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "budget": budget,
            "forecast_eac": forecast_eac,
            "vac": vac,
            "vac_percentage": vac_percentage,
            "status": status,
            "used": float(budget_status.used),
            "remaining": float(budget_status.remaining),
        }
        return add_temporal_metadata(result, context)
    except ValueError:
        error_result = {"error": f"Invalid cost element ID: {cost_element_id}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost element not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in compare_forecast_to_budget: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


# =============================================================================
# COST REGISTRATION TOOLS (Versionable Entity)
# =============================================================================


@ai_tool(
    name="get_budget_status",
    description="Get budget status for a cost element including budget amount, "
    "total costs registered to date, remaining budget, and percentage used. "
    "Supports time-travel queries via as_of parameter.",
    permissions=["cost-registration-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def get_budget_status(
    cost_element_id: str,
    as_of_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get budget status for a cost element.

    Context: Provides database session and cost registration service for budget status.

    Args:
        cost_element_id: UUID of the cost element
        as_of_date: Optional date to get status as of (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with budget status:
        - cost_element_id: Cost element UUID
        - budget: Budget amount
        - used: Total costs registered
        - remaining: Remaining budget
        - percentage: Percentage of budget used
        - _temporal_context: Temporal context metadata

    Raises:
        ValueError: If cost_element_id is invalid or date format is wrong
        KeyError: If cost element not found

    Example:
        >>> result = await get_budget_status(cost_element_id="...")
        >>> print(f"Budget: ${result['budget']}")
        >>> print(f"Used: ${result['used']} ({result['percentage']:.1f}%)")
        >>> print(f"Remaining: ${result['remaining']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_budget_status", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Parse as_of date if provided
        as_of = None
        if as_of_date:
            as_of = datetime.fromisoformat(as_of_date)

        # Call service method
        status = await service.get_budget_status(
            cost_element_id=UUID(cost_element_id),
            as_of=as_of,
            branch=context.branch_name or "main",
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "cost_element_id": str(status.cost_element_id),
            "budget": float(status.budget),
            "used": float(status.used),
            "remaining": float(status.remaining),
            "percentage": float(status.percentage),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost element not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_budget_status: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_cost_registration",
    description="Register an actual cost against a cost element. "
    "Requires amount (positive) and cost element ID. "
    "Optionally includes description, invoice number, and vendor reference.",
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
    """Create a new cost registration.

    Context: Provides database session and cost registration service for creating registrations.

    Args:
        cost_element_id: UUID of the cost element to charge
        amount: Cost amount (must be positive)
        description: Optional description of the cost
        invoice_number: Optional invoice reference
        vendor_reference: Optional vendor/supplier reference
        registration_date: Optional date of registration (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with created cost registration details

    Raises:
        ValueError: If cost_element_id is invalid or amount is not positive
        KeyError: If cost element not found

    Example:
        >>> result = await create_cost_registration(
        ...     cost_element_id="...",
        ...     amount=1500.00,
        ...     description="Material purchase"
        ... )
        >>> print(f"Registered cost: {result['id']}")
    """
    # Log temporal context for observability
    log_temporal_context("create_cost_registration", context)

    try:
        from app.models.schemas.cost_registration import CostRegistrationCreate
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Parse registration date if provided
        reg_date = None
        if registration_date:
            reg_date = datetime.fromisoformat(registration_date)

        # Create Pydantic schema
        registration_in = CostRegistrationCreate(
            cost_element_id=UUID(cost_element_id),
            amount=Decimal(str(amount)),
            description=description,
            invoice_number=invoice_number,
            vendor_reference=vendor_reference,
            registration_date=reg_date,
        )

        # Call service method
        registration = await service.create_cost_registration(
            registration_in=registration_in,
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        # Convert to AI-friendly format and add temporal metadata
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
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost element not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in create_cost_registration: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="list_cost_registrations",
    description="List cost registrations for a cost element with pagination. "
    "Returns registrations in descending order by date.",
    permissions=["cost-registration-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def list_cost_registrations(
    cost_element_id: str,
    skip: int = 0,
    limit: int = 100,
    as_of_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List cost registrations for a cost element.

    Context: Provides database session and cost registration service for listing registrations.

    Args:
        cost_element_id: UUID of the cost element to list registrations for
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        as_of_date: Optional date for time-travel query (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with list of cost registrations and total count

    Raises:
        ValueError: If cost_element_id is invalid or date format is wrong

    Example:
        >>> result = await list_cost_registrations(
        ...     cost_element_id="...",
        ...     limit=10
        ... )
        >>> print(f"Found {result['total']} registrations")
        >>> for reg in result['registrations']:
        ...     print(f"- {reg['registration_date']}: ${reg['amount']}")
    """
    # Log temporal context for observability
    log_temporal_context("list_cost_registrations", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Parse as_of date if provided
        as_of = None
        if as_of_date:
            as_of = datetime.fromisoformat(as_of_date)

        # Call service method
        registrations, total = await service.get_cost_registrations(
            filters={"cost_element_id": UUID(cost_element_id)},
            skip=skip,
            limit=limit,
            as_of=as_of,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "registrations": [
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
        logger.error(f"Error in list_cost_registrations: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_cost_registration",
    description="Get a single cost registration by its ID. "
    "Returns amount, description, invoice number, vendor reference, and registration date.",
    permissions=["cost-registration-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def get_cost_registration(
    cost_registration_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single cost registration by its ID.

    Context: Provides database session and cost registration service for retrieving a registration.

    Args:
        cost_registration_id: UUID of the cost registration to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with cost registration details

    Raises:
        ValueError: If cost_registration_id is invalid
        KeyError: If cost registration not found

    Example:
        >>> result = await get_cost_registration(
        ...     cost_registration_id="..."
        ... )
        >>> print(f"Amount: ${result['amount']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_cost_registration", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Call service method
        registration = await service.get_by_id(UUID(cost_registration_id))

        if registration is None:
            error_result = {"error": f"Cost registration not found: {cost_registration_id}"}
            return add_temporal_metadata(error_result, context)

        # Convert to AI-friendly format and add temporal metadata
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
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost registration not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_cost_registration: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="update_cost_registration",
    description="Update an existing cost registration. "
    "Creates a new version preserving history. "
    "Supports updating amount, description, invoice number, vendor reference, and registration date.",
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
    """Update an existing cost registration.

    Context: Provides database session and cost registration service for updating registrations.

    Args:
        cost_registration_id: UUID of the cost registration to update
        amount: New cost amount (must be positive if provided)
        description: New description
        invoice_number: New invoice reference
        vendor_reference: New vendor/supplier reference
        registration_date: New registration date (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with updated cost registration details

    Raises:
        ValueError: If cost_registration_id is invalid or no fields to update
        KeyError: If cost registration not found

    Example:
        >>> result = await update_cost_registration(
        ...     cost_registration_id="...",
        ...     amount=2000.00,
        ...     description="Updated material cost"
        ... )
        >>> print(f"Updated registration: {result['id']}")
    """
    # Log temporal context for observability
    log_temporal_context("update_cost_registration", context)

    try:
        from app.models.schemas.cost_registration import CostRegistrationUpdate
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Parse registration date if provided
        reg_date = None
        if registration_date:
            reg_date = datetime.fromisoformat(registration_date)

        # Build update schema with only provided fields
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
            error_result = {"error": "No fields provided to update"}
            return add_temporal_metadata(error_result, context)

        registration_in = CostRegistrationUpdate(**update_data)

        # Call service method
        registration = await service.update_cost_registration(
            cost_registration_id=UUID(cost_registration_id),
            registration_in=registration_in,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format and add temporal metadata
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
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost registration not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in update_cost_registration: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="delete_cost_registration",
    description="Soft delete a cost registration. "
    "The registration is marked as deleted but preserved for audit trail. "
    "This action cannot be undone.",
    permissions=["cost-registration-delete"],
    category="cost-registration",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_registration(
    cost_registration_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a cost registration.

    Context: Provides database session and cost registration service for deleting registrations.

    Args:
        cost_registration_id: UUID of the cost registration to delete
        context: Injected tool execution context

    Returns:
        Dictionary with confirmation message

    Raises:
        ValueError: If cost_registration_id is invalid
        KeyError: If cost registration not found

    Example:
        >>> result = await delete_cost_registration(
        ...     cost_registration_id="..."
        ... )
        >>> print(result['message'])
    """
    # Log temporal context for observability
    log_temporal_context("delete_cost_registration", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Call service method
        await service.soft_delete(
            cost_registration_id=UUID(cost_registration_id),
            actor_id=UUID(context.user_id),
        )

        # Return confirmation
        result = {
            "id": cost_registration_id,
            "message": "Cost registration soft deleted. "
            "The registration is marked as deleted but preserved for audit trail.",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost registration not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in delete_cost_registration: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_cost_trends",
    description="Get cost trends by time period (daily, weekly, monthly) for a cost element. "
    "Returns aggregated costs grouped by period for trend analysis.",
    permissions=["cost-registration-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def get_cost_trends(
    cost_element_id: str,
    period: str,  # "daily", "weekly", or "monthly"
    start_date: str,
    end_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get cost trends by time period.

    Context: Provides database session and cost registration service for trend analysis.

    Args:
        cost_element_id: UUID of the cost element to analyze
        period: Time period for grouping ("daily", "weekly", or "monthly")
        start_date: Start date for analysis (ISO format string)
        end_date: Optional end date (ISO format string, defaults to now)
        context: Injected tool execution context

    Returns:
        Dictionary with cost trends by period

    Raises:
        ValueError: If parameters are invalid or date format is wrong

    Example:
        >>> result = await get_cost_trends(
        ...     cost_element_id="...",
        ...     period="weekly",
        ...     start_date="2026-01-01"
        ... )
        >>> for trend in result['trends']:
        ...     print(f"{trend['period_start']}: ${trend['total_amount']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_cost_trends", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Parse dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Call service method
        trends = await service.get_costs_by_period(
            cost_element_id=UUID(cost_element_id),
            period=period,
            start_date=start_dt,
            end_date=end_dt,
            as_of=context.as_of,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "trends": trends,
            "period": period,
            "start_date": start_date,
            "end_date": end_date or "now",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_cost_trends: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_cumulative_costs",
    description="Get cumulative costs over time for a cost element. "
    "Returns running total of costs with registration dates for S-curve analysis.",
    permissions=["cost-registration-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def get_cumulative_costs(
    cost_element_id: str,
    start_date: str,
    end_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get cumulative costs over time.

    Context: Provides database session and cost registration service for cumulative analysis.

    Args:
        cost_element_id: UUID of the cost element to analyze
        start_date: Start date for analysis (ISO format string)
        end_date: Optional end date (ISO format string, defaults to now)
        context: Injected tool execution context

    Returns:
        Dictionary with cumulative costs over time

    Raises:
        ValueError: If parameters are invalid or date format is wrong

    Example:
        >>> result = await get_cumulative_costs(
        ...     cost_element_id="...",
        ...     start_date="2026-01-01"
        ... )
        >>> for item in result['cumulative_costs']:
        ...     print(f"{item['registration_date']}: ${item['cumulative_amount']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_cumulative_costs", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService

        service = CostRegistrationService(context.session)

        # Parse dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Call service method
        cumulative = await service.get_cumulative_costs(
            cost_element_id=UUID(cost_element_id),
            start_date=start_dt,
            end_date=end_dt,
            as_of=context.as_of,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "cumulative_costs": cumulative,
            "start_date": start_date,
            "end_date": end_date or "now",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_cumulative_costs: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


# =============================================================================
# PROGRESS ENTRY TOOLS (Versionable Entity)
# =============================================================================


@ai_tool(
    name="get_latest_progress",
    description="Get the latest progress entry for a cost element. "
    "Returns the most recent progress percentage and notes. "
    "Supports time-travel queries via as_of parameter.",
    permissions=["progress-entry-read"],
    category="progress-entry",
    risk_level=RiskLevel.LOW,
)
async def get_latest_progress(
    cost_element_id: str,
    as_of_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get the latest progress entry for a cost element.

    Context: Provides database session and progress entry service for retrieving progress.

    Args:
        cost_element_id: UUID of the cost element to get progress for
        as_of_date: Optional date for time-travel query (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with latest progress details or error if not found

    Raises:
        ValueError: If cost_element_id is invalid or date format is wrong

    Example:
        >>> result = await get_latest_progress(cost_element_id="...")
        >>> if "error" not in result:
        ...     print(f"Progress: {result['progress_percentage']}%")
        ...     print(f"Notes: {result['notes']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_latest_progress", context)

    try:
        from app.services.progress_entry_service import ProgressEntryService

        service = ProgressEntryService(context.session)

        # Parse as_of date if provided
        as_of = None
        if as_of_date:
            as_of = datetime.fromisoformat(as_of_date)

        # Call service method
        progress = await service.get_latest_progress(
            cost_element_id=UUID(cost_element_id),
            as_of=as_of,
        )

        if not progress:
            return add_temporal_metadata(
                {"error": f"No progress found for cost element {cost_element_id}"},
                context,
            )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "progress_entry_id": str(progress.progress_entry_id),
            "cost_element_id": str(progress.cost_element_id),
            "progress_percentage": float(progress.progress_percentage)
            if progress.progress_percentage
            else None,
            "notes": progress.notes,
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_latest_progress: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_progress_entry",
    description="Create a new progress entry for a cost element. "
    "Requires progress percentage (0-100) and cost element ID. "
    "Optionally includes notes explaining the progress.",
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
    """Create a new progress entry.

    Context: Provides database session and progress entry service for creating progress entries.

    Args:
        cost_element_id: UUID of the cost element to track progress for
        progress_percentage: Work completion percentage (0.00 to 100.00)
        notes: Optional notes about the progress
        context: Injected tool execution context

    Returns:
        Dictionary with created progress entry details

    Raises:
        ValueError: If cost_element_id is invalid or percentage is out of range
        KeyError: If cost element not found

    Example:
        >>> result = await create_progress_entry(
        ...     cost_element_id="...",
        ...     progress_percentage=50.0,
        ...     notes="Halfway complete"
        ... )
        >>> print(f"Created progress entry: {result['progress_entry_id']}")
    """
    # Log temporal context for observability
    log_temporal_context("create_progress_entry", context)

    try:
        from app.models.schemas.progress_entry import ProgressEntryCreate
        from app.services.progress_entry_service import ProgressEntryService

        service = ProgressEntryService(context.session)

        # Create Pydantic schema
        progress_in = ProgressEntryCreate(
            cost_element_id=UUID(cost_element_id),
            progress_percentage=Decimal(str(progress_percentage)),
            notes=notes,
        )

        # Call service method
        progress = await service.create(
            actor_id=UUID(context.user_id),
            progress_in=progress_in,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "progress_entry_id": str(progress.progress_entry_id),
            "cost_element_id": str(progress.cost_element_id),
            "progress_percentage": float(progress.progress_percentage)
            if progress.progress_percentage
            else None,
            "notes": progress.notes,
            "message": "Progress entry created",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost element not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in create_progress_entry: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="get_progress_history",
    description="Get progress entry history for a cost element with pagination. "
    "Returns all progress entries in descending order by date for trend analysis.",
    permissions=["progress-entry-read"],
    category="progress-entry",
    risk_level=RiskLevel.LOW,
)
async def get_progress_history(
    cost_element_id: str,
    skip: int = 0,
    limit: int = 100,
    as_of_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get progress entry history for a cost element.

    Context: Provides database session and progress entry service for history.

    Args:
        cost_element_id: UUID of the cost element to get history for
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        as_of_date: Optional date for time-travel query (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with list of progress entries and total count

    Raises:
        ValueError: If cost_element_id is invalid or date format is wrong

    Example:
        >>> result = await get_progress_history(
        ...     cost_element_id="...",
        ...     limit=10
        ... )
        >>> print(f"Found {result['total']} progress entries")
        >>> for entry in result['progress_entries']:
        ...     print(f"- {entry['progress_percentage']}%: {entry['notes']}")
    """
    # Log temporal context for observability
    log_temporal_context("get_progress_history", context)

    try:
        from app.services.progress_entry_service import ProgressEntryService

        service = ProgressEntryService(context.session)

        # Parse as_of date if provided
        as_of = None
        if as_of_date:
            as_of = datetime.fromisoformat(as_of_date)

        # Call service method
        progress_entries, total = await service.get_progress_history(
            cost_element_id=UUID(cost_element_id),
            skip=skip,
            limit=limit,
            as_of=as_of,
        )

        # Convert to AI-friendly format and add temporal metadata
        result = {
            "progress_entries": [
                {
                    "progress_entry_id": str(entry.progress_entry_id),
                    "cost_element_id": str(entry.cost_element_id),
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
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_progress_history: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


# =============================================================================
# SUMMARY TOOL
# =============================================================================


@ai_tool(
    name="get_cost_element_summary",
    description="Get comprehensive summary of a cost element including forecast, "
    "budget status, and latest progress. Aggregates data from multiple services "
    "for a complete cost element view.",
    permissions=["forecast-read", "cost-registration-read", "progress-entry-read"],
    category="summary",
    risk_level=RiskLevel.LOW,
)
async def get_cost_element_summary(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get comprehensive summary of a cost element.

    Context: Provides database session and access to forecast, cost, and progress services.

    Args:
        cost_element_id: UUID of the cost element to summarize
        context: Injected tool execution context

    Returns:
        Dictionary with comprehensive summary including:
        - cost_element_id: Cost element UUID
        - forecast: Forecast data (if exists)
        - budget_status: Budget and cost data
        - progress: Latest progress data (if exists)
        - _temporal_context: Temporal context metadata

    Raises:
        ValueError: If cost_element_id is invalid
        KeyError: If cost element not found

    Example:
        >>> result = await get_cost_element_summary(cost_element_id="...")
        >>> print(f"Forecast EAC: ${result['forecast']['eac_amount']}")
        >>> print(f"Budget Used: {result['budget_status']['percentage']:.1f}%")
        >>> print(f"Progress: {result['progress']['progress_percentage']}%")
    """
    # Log temporal context for observability
    log_temporal_context("get_cost_element_summary", context)

    try:
        from app.services.cost_registration_service import CostRegistrationService
        from app.services.forecast_service import ForecastService
        from app.services.progress_entry_service import ProgressEntryService

        forecast_service = ForecastService(context.session)
        cost_service = CostRegistrationService(context.session)
        progress_service = ProgressEntryService(context.session)

        # Get forecast data
        forecast_data = None
        try:
            forecast = await forecast_service.get_for_cost_element(
                cost_element_id=UUID(cost_element_id),
                branch=context.branch_name or "main",
            )
            if forecast:
                forecast_data = {
                    "id": str(forecast.forecast_id),
                    "eac_amount": float(forecast.eac_amount) if forecast.eac_amount else None,
                    "basis_of_estimate": forecast.basis_of_estimate,
                    "branch": forecast.branch,
                }
        except Exception:
            forecast_data = None

        # Get budget status
        budget_status = await cost_service.get_budget_status(
            cost_element_id=UUID(cost_element_id),
            as_of=context.as_of,
            branch=context.branch_name or "main",
        )

        budget_status_data = {
            "budget": float(budget_status.budget),
            "used": float(budget_status.used),
            "remaining": float(budget_status.remaining),
            "percentage": float(budget_status.percentage),
        }

        # Get latest progress
        progress_data = None
        try:
            progress = await progress_service.get_latest_progress(
                cost_element_id=UUID(cost_element_id),
                as_of=context.as_of,
            )
            if progress:
                progress_data = {
                    "progress_entry_id": str(progress.progress_entry_id),
                    "progress_percentage": float(progress.progress_percentage)
                    if progress.progress_percentage
                    else None,
                    "notes": progress.notes,
                }
        except Exception:
            progress_data = None

        # Aggregate results
        result = {
            "cost_element_id": cost_element_id,
            "forecast": forecast_data,
            "budget_status": budget_status_data,
            "progress": progress_data,
        }
        return add_temporal_metadata(result, context)
    except ValueError:
        error_result = {"error": f"Invalid cost element ID: {cost_element_id}"}
        return add_temporal_metadata(error_result, context)
    except KeyError as e:
        error_result = {"error": f"Cost element not found: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_cost_element_summary: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
FORECAST, COST REGISTRATION, AND PROGRESS ENTRY TOOL PATTERNS:

1. FORECAST TOOLS (Branchable Entity):
   - get_forecast: Get forecast for cost element
   - create_forecast: Create new forecast (one per cost element per branch)
   - update_forecast: Update existing forecast
   - compare_forecast_to_budget: Compare forecast EAC to budget

2. COST REGISTRATION TOOLS (Versionable Entity):
   - get_budget_status: Get budget, used, remaining, percentage
   - create_cost_registration: Register actual cost
   - list_cost_registrations: List registrations with pagination
   - get_cost_trends: Get costs grouped by period (daily/weekly/monthly)
   - get_cumulative_costs: Get running total over time

3. PROGRESS ENTRY TOOLS (Versionable Entity):
   - get_latest_progress: Get most recent progress entry
   - create_progress_entry: Create new progress entry
   - get_progress_history: Get all progress entries with pagination

4. SUMMARY TOOL:
   - get_cost_element_summary: Comprehensive view (forecast + budget + progress)

PERMISSIONS MODEL:
   - forecast-read: View forecasts
   - forecast-create: Create forecasts
   - forecast-update: Update forecasts
   - cost-registration-read: View cost registrations
   - cost-registration-create: Create cost registrations
   - progress-entry-read: View progress entries
   - progress-entry-create: Create progress entries

TEMPORAL CONTEXT:
   - All tools use log_temporal_context() for observability
   - All tools use add_temporal_metadata() for result transparency
   - Branchable entities (Forecast) use full temporal context
   - Non-branchable entities (Cost, Progress) still log temporal context for consistency

BEST PRACTICES:
   - All tools wrap service methods, no business logic in tools
   - Return AI-friendly format (dicts, UUIDs→strings, Decimals→floats)
   - Error handling returns error dictionaries
   - Include _temporal_context in all results
   - Validate inputs (UUIDs, date formats, numeric ranges)
"""
