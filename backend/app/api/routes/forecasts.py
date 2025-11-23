"""Forecast API routes."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep, TimeMachineControlDate
from app.models import (
    CostElement,
    Forecast,
    ForecastCreate,
    ForecastPublic,
    ForecastType,
    ForecastUpdate,
    Message,
)

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


def validate_cost_element_exists(
    session: Session, cost_element_id: uuid.UUID
) -> CostElement:
    """
    Validate that cost element exists.
    Raises HTTPException(400) if cost element not found.

    Args:
        session: Database session
        cost_element_id: ID of the cost element to validate

    Returns:
        CostElement if found
    """
    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=400, detail="Cost element not found")
    return cost_element


def validate_forecast_date(forecast_date: date) -> dict[str, str] | None:
    """
    Validate forecast date is in the past.
    Returns warning dict if future date (not blocked).

    Args:
        forecast_date: Date to validate

    Returns:
        Warning dict if future date, None if past date
    """
    today = date.today()
    if forecast_date > today:
        return {
            "warning": f"Forecast date ({forecast_date}) is in the future. Forecasts should typically be dated in the past."
        }
    return None


def validate_forecast_type(forecast_type: ForecastType | str) -> None:
    """
    Validate forecast_type against ForecastType enum.
    Raises HTTPException(400) if invalid.

    Args:
        forecast_type: Forecast type to validate
    """
    if isinstance(forecast_type, str):
        try:
            ForecastType(forecast_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid forecast_type: {forecast_type}. Must be one of: {', '.join([ft.value for ft in ForecastType])}",
            )
    elif not isinstance(forecast_type, ForecastType):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid forecast_type. Must be one of: {', '.join([ft.value for ft in ForecastType])}",
        )


def validate_eac(estimate_at_completion: Decimal) -> None:
    """
    Validate EAC is positive (> 0).
    Raises HTTPException(400) if invalid.

    Args:
        estimate_at_completion: EAC value to validate
    """
    if estimate_at_completion <= Decimal("0.00"):
        raise HTTPException(
            status_code=400,
            detail="estimate_at_completion must be greater than zero",
        )


def validate_max_forecast_dates(
    session: Session, cost_element_id: uuid.UUID, new_forecast_date: date
) -> None:
    """
    Validate that cost element has maximum 3 unique forecast dates.
    Raises HTTPException(400) if limit exceeded.

    Args:
        session: Database session
        cost_element_id: ID of the cost element
        new_forecast_date: New forecast date being added
    """
    # Get all unique forecast dates for this cost element
    statement = (
        select(Forecast.forecast_date)  # type: ignore[call-overload]
        .where(Forecast.cost_element_id == cost_element_id)
        .distinct()
    )
    existing_dates = session.exec(statement).all()

    # Check if new date already exists
    if new_forecast_date not in existing_dates:
        # New unique date - check if we're at limit
        if len(existing_dates) >= 3:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum of 3 forecast dates per cost element exceeded. Current unique dates: {len(existing_dates)}",
            )


def ensure_single_current_forecast(
    session: Session,
    cost_element_id: uuid.UUID,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """
    Ensure only one forecast per cost element has is_current=True.
    Sets all other forecasts to is_current=False.
    Does NOT commit - caller must commit.

    Args:
        session: Database session
        cost_element_id: ID of the cost element
        exclude_id: Forecast ID to exclude from update (the one being set as current)
    """
    # Get all forecasts for this cost element
    statement = select(Forecast).where(Forecast.cost_element_id == cost_element_id)
    if exclude_id:
        statement = statement.where(Forecast.forecast_id != exclude_id)

    forecasts = session.exec(statement).all()

    # Set all other forecasts to is_current=False
    for forecast in forecasts:
        if forecast.is_current:
            forecast.is_current = False
            session.add(forecast)


def get_previous_forecast_for_promotion(
    session: Session, cost_element_id: uuid.UUID, exclude_id: uuid.UUID
) -> Forecast | None:
    """
    Get the previous forecast (by forecast_date DESC) for auto-promotion.
    Returns None if no previous forecast exists.

    Args:
        session: Database session
        cost_element_id: ID of the cost element
        exclude_id: Forecast ID to exclude (the one being deleted)

    Returns:
        Previous Forecast or None
    """
    statement = (
        select(Forecast)
        .where(Forecast.cost_element_id == cost_element_id)
        .where(Forecast.forecast_id != exclude_id)
        .order_by(Forecast.forecast_date.desc())  # type: ignore[attr-defined]
    )

    return session.exec(statement).first()


@router.get("/", response_model=list[ForecastPublic])
def read_forecasts(
    session: SessionDep,
    _current_user: CurrentUser,
    control_date: TimeMachineControlDate,
    cost_element_id: uuid.UUID | None = Query(
        default=None, description="Filter by cost element ID"
    ),
) -> Any:
    """
    Retrieve forecasts with optional filtering by cost element.
    Results ordered by forecast_date descending (newest first).
    Only forecasts where forecast_date <= control_date are returned.
    """
    statement = select(Forecast)

    if cost_element_id:
        statement = statement.where(Forecast.cost_element_id == cost_element_id)

    # Filter by control_date (forecast_date <= control_date)
    statement = statement.where(Forecast.forecast_date <= control_date)

    # Order by forecast_date descending (newest first)
    statement = statement.order_by(Forecast.forecast_date.desc())

    forecasts = session.exec(statement).all()

    return [ForecastPublic.model_validate(forecast) for forecast in forecasts]


@router.get("/{forecast_id}", response_model=ForecastPublic)
def read_forecast(
    session: SessionDep,
    _current_user: CurrentUser,
    forecast_id: uuid.UUID,
) -> Any:
    """
    Retrieve a single forecast by ID.
    """
    forecast = session.get(Forecast, forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return forecast


@router.post("/", response_model=ForecastPublic)
def create_forecast(
    *,
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    forecast_in: ForecastCreate,
) -> Any:
    """
    Create a new forecast.
    """
    # Validate cost element exists
    validate_cost_element_exists(session, forecast_in.cost_element_id)

    # Validate forecast date (returns warning if future, not blocked)
    warning = validate_forecast_date(forecast_in.forecast_date)

    # Validate forecast type
    validate_forecast_type(forecast_in.forecast_type)

    # Validate EAC
    validate_eac(forecast_in.estimate_at_completion)

    # Validate max forecast dates (3 unique dates per cost element)
    validate_max_forecast_dates(
        session, forecast_in.cost_element_id, forecast_in.forecast_date
    )

    # If is_current=True, ensure single current forecast
    if forecast_in.is_current:
        ensure_single_current_forecast(
            session, forecast_in.cost_element_id, exclude_id=None
        )

    # Create forecast
    forecast_data = forecast_in.model_dump()
    forecast = Forecast.model_validate(forecast_data)
    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    # Convert to public schema
    result = ForecastPublic.model_validate(forecast)

    # Add warning if forecast_date is future
    if warning:
        result_dict = result.model_dump(mode="json")
        result_dict["warning"] = warning["warning"]
        return JSONResponse(content=result_dict)

    return result


@router.put("/{forecast_id}", response_model=ForecastPublic)
def update_forecast(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    forecast_id: uuid.UUID,
    forecast_in: ForecastUpdate,
) -> Any:
    """
    Update an existing forecast.
    Only current forecast (is_current=True) can be updated.
    """
    forecast = session.get(Forecast, forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    # Only allow updating current forecast
    if not forecast.is_current:
        raise HTTPException(
            status_code=400,
            detail="Only the current forecast can be updated. Please set this forecast as current first.",
        )

    update_data = forecast_in.model_dump(exclude_unset=True)

    # Validate forecast_date if provided
    if "forecast_date" in update_data:
        warning = validate_forecast_date(update_data["forecast_date"])
        # Validate max forecast dates if date changed
        new_date = update_data["forecast_date"]
        if new_date != forecast.forecast_date:
            validate_max_forecast_dates(session, forecast.cost_element_id, new_date)
    else:
        warning = None

    # Validate forecast_type if provided
    if "forecast_type" in update_data:
        validate_forecast_type(update_data["forecast_type"])

    # Validate EAC if provided
    if "estimate_at_completion" in update_data:
        validate_eac(update_data["estimate_at_completion"])

    # If is_current=True in update, ensure single current forecast
    if update_data.get("is_current") is True:
        ensure_single_current_forecast(
            session, forecast.cost_element_id, exclude_id=forecast_id
        )

    # Update forecast
    forecast.sqlmodel_update(update_data)
    forecast.last_modified_at = datetime.now(timezone.utc)
    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    # Convert to public schema
    result = ForecastPublic.model_validate(forecast)

    # Add warning if forecast_date is future
    if warning:
        result_dict = result.model_dump(mode="json")
        result_dict["warning"] = warning["warning"]
        return JSONResponse(content=result_dict)

    return result


@router.delete("/{forecast_id}", response_model=Message)
def delete_forecast(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    forecast_id: uuid.UUID,
) -> Any:
    """
    Delete a forecast.
    If the deleted forecast was current, automatically promotes the previous forecast.
    """
    forecast = session.get(Forecast, forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    # Check if this is the current forecast
    was_current = forecast.is_current
    cost_element_id = forecast.cost_element_id

    # Delete the forecast
    session.delete(forecast)
    session.commit()

    # If deleted forecast was current, auto-promote previous forecast
    if was_current:
        previous_forecast = get_previous_forecast_for_promotion(
            session, cost_element_id, forecast_id
        )
        if previous_forecast:
            previous_forecast.is_current = True
            session.add(previous_forecast)
            session.commit()

    return Message(message="Forecast deleted successfully")
