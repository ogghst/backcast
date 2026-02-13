"""Generic EVM (Earned Value Management) API routes.

Provides generic endpoints for EVM metrics that work with any entity type:
- GET /api/v1/evm/{entity_type}/{entity_id}/metrics
- GET /api/v1/evm/{entity_type}/{entity_id}/timeseries
- POST /api/v1/evm/batch

These endpoints consolidate EVM calculations for cost_element, wbe, and project entities.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
from app.models.schemas.evm import (
    EntityType,
    EVMMetricsResponse,
    EVMTimeSeriesGranularity,
    EVMTimeSeriesResponse,
)
from app.services.evm_service import EVMService

router = APIRouter()


def get_evm_service(
    session: AsyncSession = Depends(get_db),
) -> EVMService:
    """Dependency to get EVMService instance."""
    return EVMService(session)


@router.get(
    "/{entity_type}/{entity_id}/metrics",
    response_model=EVMMetricsResponse,
    operation_id="get_generic_evm_metrics",
    dependencies=[Depends(RoleChecker(required_permission="evm-read"))],
)
async def get_evm_metrics(
    entity_type: EntityType,
    entity_id: UUID,
    control_date: datetime | None = Query(
        None,
        description="Control date for time-travel query (ISO 8601, defaults to now). "
        "All entities are fetched as they were at this valid_time.",
    ),
    branch: str = Query("main", description="Branch to query"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGE,
        description="Branch mode: STRICT (only this branch) or MERGE (fall back to parent branches)",
    ),
    service: EVMService = Depends(get_evm_service),
) -> dict[str, Any]:
    """Get EVM metrics for any entity type.

    Returns comprehensive EVM analysis including:
    - BAC: Budget at Completion (total planned budget)
    - PV: Planned Value (budgeted cost of work scheduled)
    - AC: Actual Cost (cost incurred to date)
    - EV: Earned Value (budgeted cost of work performed)
    - CV: Cost Variance (EV - AC, negative = over budget)
    - SV: Schedule Variance (EV - PV, negative = behind schedule)
    - CPI: Cost Performance Index (EV / AC, < 1.0 = over budget)
    - SPI: Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
    - EAC: Estimate at Completion (from forecast)
    - VAC: Variance at Completion (BAC - EAC)
    - ETC: Estimate to Complete (EAC - AC)

    Time-Travel & Branching:
    - All metrics respect time-travel: entities are fetched as they were at control_date
    - Branch mode (STRICT/MERGE) controls parent branch fallback behavior
    - Cost registrations and progress entries are global facts (not branchable)

    Supports entity types:
    - cost_element: Individual cost element metrics
    - wbe: Work Breakdown Element (aggregated from child cost elements)
    - project: Project-level metrics (aggregated from all child elements)

    Warning: Returns EV = 0 with warning message if no progress has been reported.
    """
    if control_date is None:
        control_date = datetime.now(tz=UTC)

    try:
        # Handle cost_element entity type (single entity calculation)
        if entity_type == EntityType.COST_ELEMENT:
            # Calculate EVM metrics for cost element
            metrics = await service.calculate_evm_metrics(
                cost_element_id=entity_id,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )
            # Convert to generic response format
            from app.models.schemas.evm import EVMMetricsResponse

            response = EVMMetricsResponse(
                entity_type=entity_type,
                entity_id=entity_id,
                bac=metrics.bac,
                pv=metrics.pv,
                ac=metrics.ac,
                ev=metrics.ev,
                cv=metrics.cv,
                sv=metrics.sv,
                cpi=metrics.cpi,
                spi=metrics.spi,
                eac=metrics.eac,
                vac=metrics.vac,
                etc=metrics.etc,
                control_date=metrics.control_date,
                branch=metrics.branch,
                branch_mode=metrics.branch_mode,
                progress_percentage=metrics.progress_percentage,
                warning=metrics.warning,
            )
            # FastAPI will serialize the Pydantic model to JSON
            return response  # type: ignore[return-value]

        # Handle WBE and Project entity types (batch aggregation)
        elif entity_type in (EntityType.WBE, EntityType.PROJECT):
            # Validate entity exists before calculating metrics
            if entity_type == EntityType.WBE:
                wbe = await service.wbe_service.get_by_root_id(
                    root_id=entity_id,
                    branch=branch,
                )
                if wbe is None:
                    raise ValueError(f"WBE with ID {entity_id} not found")
            elif entity_type == EntityType.PROJECT:
                project = await service.project_service.get_by_root_id(
                    root_id=entity_id,
                    branch=branch,
                )
                if project is None:
                    raise ValueError(f"Project with ID {entity_id} not found")

            # Use batch calculation for aggregation
            response = await service.calculate_evm_metrics_batch(
                entity_type=entity_type,
                entity_ids=[entity_id],
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )
            # FastAPI will serialize the Pydantic model to JSON
            return response  # type: ignore[return-value]

        else:
            raise ValueError(
                f"Entity type {entity_type} not supported. "
                "Supported types: cost_element, wbe, project"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{entity_type}/{entity_id}/timeseries",
    response_model=EVMTimeSeriesResponse,
    operation_id="get_generic_evm_timeseries",
    dependencies=[Depends(RoleChecker(required_permission="evm-read"))],
)
async def get_evm_timeseries(
    entity_type: EntityType,
    entity_id: UUID,
    granularity: EVMTimeSeriesGranularity = Query(
        EVMTimeSeriesGranularity.WEEK,
        description="Time granularity for aggregation (day, week, month)",
    ),
    control_date: datetime | None = Query(
        None,
        description="Control date for time-travel query (ISO 8601, defaults to now).",
    ),
    branch: str = Query("main", description="Branch to query"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGE,
        description="Branch mode: STRICT (only this branch) or MERGE (fall back to parent branches)",
    ),
    service: EVMService = Depends(get_evm_service),
) -> dict[str, Any]:
    """Get historical EVM metrics as time-series data for charts.

    Generates a time-series of EVM metrics (PV, EV, AC) over a date range
    with server-side aggregation at the specified granularity (day, week, month).

    The date range is context-dependent:
    - Cost element: Uses its schedule baseline date range
    - Project: From project start to max(project end, control_date)

    Time-Travel & Branching:
    - All metrics respect time-travel: entities are fetched as they were at control_date
    - Branch mode (ISOLATED/MERGE) controls parent branch fallback behavior

    Supports entity types:
    - cost_element: Individual cost element time-series
    - wbe: Work Breakdown Element (aggregated from children)
    - project: Project-level time-series

    Returns:
        EVMTimeSeriesResponse with aggregated time-series data
    """
    if control_date is None:
        control_date = datetime.now(tz=UTC)

    try:
        # For now, only support cost_element entity_type
        # The service layer will validate and raise ValueError for unsupported types
        timeseries = await service.get_evm_timeseries(
            entity_type=entity_type,
            entity_id=entity_id,
            granularity=granularity,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )
        # FastAPI will serialize the Pydantic model to JSON
        return timeseries  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/batch",
    response_model=EVMMetricsResponse,
    operation_id="get_evm_batch_metrics",
    dependencies=[Depends(RoleChecker(required_permission="evm-read"))],
)
async def get_evm_batch(
    request_data: dict[str, Any],
    service: EVMService = Depends(get_evm_service),
) -> dict[str, Any]:
    """Get aggregated EVM metrics for multiple entities.

    Calculates EVM metrics for each entity individually, then aggregates them:
    - Sums amount fields (BAC, PV, AC, EV, CV, SV, EAC, VAC, ETC)
    - Calculates BAC-weighted average for indices (CPI, SPI)

    Request body:
        entity_type: Type of entities (cost_element, wbe, project)
        entity_ids: List of entity IDs to calculate metrics for
        control_date: Optional control date for time-travel (defaults to now)
        branch: Branch name (defaults to "main")
        branch_mode: Branch isolation mode (defaults to "merge")

    Supports entity types:
    - cost_element: Aggregate multiple cost elements
    - wbe: Aggregate multiple WBEs (not yet implemented)
    - project: Aggregate multiple projects (not yet implemented)

    Returns:
        EVMMetricsResponse with aggregated metrics
    """
    # Parse request body
    try:
        entity_type_str = request_data.get("entity_type")
        entity_ids_str = request_data.get("entity_ids", [])
        control_date_str = request_data.get("control_date")
        branch = request_data.get("branch", "main")
        branch_mode_str = request_data.get("branch_mode", "merge")

        # Validate entity_type
        if entity_type_str == EntityType.COST_ELEMENT:
            entity_type = EntityType.COST_ELEMENT
        elif entity_type_str == EntityType.WBE:
            entity_type = EntityType.WBE
        elif entity_type_str == EntityType.PROJECT:
            entity_type = EntityType.PROJECT
        else:
            raise ValueError(f"Invalid entity_type: {entity_type_str}")

        # Parse entity_ids
        entity_ids = [UUID(str(id)) for id in entity_ids_str]

        # Parse control_date
        if control_date_str:
            if isinstance(control_date_str, str):
                control_date = datetime.fromisoformat(
                    control_date_str.replace("Z", "+00:00")
                )
            else:
                control_date = control_date_str
        else:
            control_date = datetime.now(tz=UTC)

        # Parse branch_mode
        if branch_mode_str == "isolated" or branch_mode_str == "strict":
            branch_mode = BranchMode.STRICT
        else:
            branch_mode = BranchMode.MERGE

    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request body: {str(e)}",
        ) from e

    try:
        # Calculate aggregated metrics
        response = await service.calculate_evm_metrics_batch(
            entity_type=entity_type,
            entity_ids=entity_ids,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )
        # FastAPI will serialize the Pydantic model to JSON
        return response  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
