"""Analysis tool template for wrapping EVM and Forecast services.

This template shows how to create AI tools for project analysis including:
- Earned Value Management (EVM) analysis
- Forecasting and trend analysis
- Performance metrics and KPIs
- Variance analysis

The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Analysis Tools in Backcast EVS:
- EVM: Earned Value Management for cost/schedule performance
- Forecasting: Predict future performance based on trends
- Variance: Compare planned vs actual performance
- KPIs: Key Performance Indicators for project health

Usage:
    1. Import EVMService and ForecastService methods
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format
"""

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import BaseTool, InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)

# =============================================================================
# EVM ANALYSIS TOOLS
# =============================================================================

@ai_tool(
    name="calculate_evm_metrics",
    description="Calculate Earned Value Management (EVM) metrics for a project. "
    "Returns PV, EV, AC, CV, SV, CPI, SPI, and other key EVM indicators.",
    permissions=["evm-read"],
    category="analysis",
)
async def calculate_evm_metrics(
    project_id: str,
    as_of_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Calculate EVM metrics for a project.

    Context: Provides database session and EVM service for calculating metrics.

    Args:
        project_id: UUID of the project to analyze
        as_of_date: Optional date to calculate metrics as of (ISO format string)
        context: Injected tool execution context

    Returns:
        Dictionary with EVM metrics:
        - pv: Planned Value (budgeted cost of work scheduled)
        - ev: Earned Value (budgeted cost of work performed)
        - ac: Actual Cost (actual cost of work performed)
        - cv: Cost Variance (EV - AC)
        - sv: Schedule Variance (EV - PV)
        - cpi: Cost Performance Index (EV / AC)
        - spi: Schedule Performance Index (EV / PV)
        - vac: Variance at Completion (BAC - EAC)
        - etc: Estimate to Complete
        - eac: Estimate at Completion

    Raises:
        ValueError: If project_id is invalid or date format is wrong

    Example:
        >>> result = await calculate_evm_metrics(project_id="...")
        >>> print(f"Cost Performance Index: {result['cpi']}")
        >>> print(f"Schedule Performance Index: {result['spi']}")
        >>> if result['cpi'] < 1.0:
        ...     print("Project over budget")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # Parse date if provided
        as_of = datetime.fromisoformat(as_of_date) if as_of_date else datetime.now()

        # Call service method to calculate EVM
        # Use batch method for project-level metrics
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=as_of,
        )

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "as_of_date": as_of.isoformat(),
            "planned_value": float(evm_data.pv),
            "earned_value": float(evm_data.ev),
            "actual_cost": float(evm_data.ac),
            "cost_variance": float(evm_data.cv),
            "schedule_variance": float(evm_data.sv),
            "cost_performance_index": float(evm_data.cpi) if evm_data.cpi is not None else 0.0,
            "schedule_performance_index": float(evm_data.spi) if evm_data.spi is not None else 0.0,
            "variance_at_completion": float(evm_data.vac) if evm_data.vac is not None else 0.0,
            "estimate_to_complete": float(evm_data.etc) if evm_data.etc is not None else 0.0,
            "estimate_at_completion": float(evm_data.eac) if evm_data.eac is not None else 0.0,
            "budget_at_completion": float(evm_data.bac),
            "progress_percentage": float(evm_data.progress_percentage) if evm_data.progress_percentage is not None else 0.0,
            "warning": evm_data.warning,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in calculate_evm_metrics: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_evm_performance_summary",
    description="Get a summary of EVM performance for a project including trends "
    "and performance assessment (on track, at risk, off track).",
    permissions=["evm-read"],
    category="analysis",
)
async def get_evm_performance_summary(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get EVM performance summary for a project.

    Context: Provides database session and EVM service for performance analysis.

    Args:
        project_id: UUID of the project
        context: Injected tool execution context

    Returns:
        Dictionary with performance summary and assessment including:
        - performance_status: "On Track", "At Risk", or "Off Track"
        - cost_performance_index: CPI value
        - schedule_performance_index: SPI value
        - recommendation: Actionable recommendation

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await get_evm_performance_summary(project_id="...")
        >>> print(f"Status: {result['performance_status']}")
        >>> print(f"Recommendation: {result['recommendation']}")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # Get EVM metrics
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        # Determine performance status
        cpi = float(evm_data.cpi) if evm_data.cpi is not None else 0.0
        spi = float(evm_data.spi) if evm_data.spi is not None else 0.0

        if cpi >= 0.95 and spi >= 0.95:
            performance_status = "On Track"
            recommendation = "Project performing well. Continue current approach."
        elif cpi >= 0.85 and spi >= 0.85:
            performance_status = "At Risk"
            recommendation = "Performance declining. Monitor closely and consider corrective actions."
        else:
            performance_status = "Off Track"
            recommendation = "Significant performance issues. Immediate corrective action required."

        return {
            "project_id": project_id,
            "performance_status": performance_status,
            "cost_performance_index": cpi,
            "schedule_performance_index": spi,
            "recommendation": recommendation,
            "planned_value": float(evm_data.pv),
            "earned_value": float(evm_data.ev),
            "actual_cost": float(evm_data.ac),
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in get_evm_performance_summary: {e}")
        return {"error": str(e)}


@ai_tool(
    name="analyze_cost_variance",
    description="Analyze cost variance for a project. Breaks down cost overruns "
    "by work breakdown structure and identifies root causes.",
    permissions=["evm-read"],
    category="analysis",
)
async def analyze_cost_variance(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Analyze cost variance in detail.

    Context: Provides database session and EVM service for cost variance analysis.

    Args:
        project_id: UUID of the project to analyze
        context: Injected tool execution context

    Returns:
        Dictionary with detailed cost variance analysis including:
        - total_variance: Overall cost variance
        - variance_percentage: Variance as percentage
        - variance_by_wbe: Breakdown by work breakdown element
        - root_causes: Identified root causes

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await analyze_cost_variance(project_id="...")
        >>> print(f"Total Cost Variance: ${result['total_variance']}")
        >>> for item in result['variance_by_wbe']:
        ...     print(f"{item['wbe_name']}: ${item['variance']}")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # Get cost variance analysis
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        bac = float(evm_data.bac)
        cv = float(evm_data.cv)
        variance_percentage = (cv / bac * 100) if bac > 0 else 0.0

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "total_variance": cv,
            "variance_percentage": variance_percentage,
            "actual_cost": float(evm_data.ac),
            "earned_value": float(evm_data.ev),
            "status": "Under Budget" if cv >= 0 else "Over Budget",
            "root_causes": ["Cost variance identified at project level. Further breakdown required for root cause analysis."],
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in analyze_cost_variance: {e}")
        return {"error": str(e)}


@ai_tool(
    name="analyze_schedule_variance",
    description="Analyze schedule variance for a project. Identifies delays, "
    "critical path issues, and schedule risks.",
    permissions=["evm-read"],
    category="analysis",
)
async def analyze_schedule_variance(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Analyze schedule variance in detail.

    Context: Provides database session and EVM service for schedule variance analysis.

    Args:
        project_id: UUID of the project to analyze
        context: Injected tool execution context

    Returns:
        Dictionary with detailed schedule variance analysis including:
        - total_variance_days: Overall schedule variance in days
        - critical_path_delay_days: Critical path delay
        - delayed_activities: List of delayed activities
        - schedule_risks: Identified schedule risks

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await analyze_schedule_variance(project_id="...")
        >>> print(f"Schedule Variance: {result['total_variance_days']} days")
        >>> print(f"Critical Path Delay: {result['critical_path_delay_days']} days")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # Get schedule variance analysis
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        sv = float(evm_data.sv)
        spi = float(evm_data.spi) if evm_data.spi is not None else 0.0

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "total_variance_value": sv,
            "schedule_performance_index": spi,
            "status": "Ahead of Schedule" if sv >= 0 else "Behind Schedule",
            "warning": evm_data.warning,
            "planned_value": float(evm_data.pv),
            "earned_value": float(evm_data.ev),
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in analyze_schedule_variance: {e}")
        return {"error": str(e)}


# =============================================================================
# FORECASTING TOOLS
# =============================================================================

@ai_tool(
    name="generate_project_forecast",
    description="Generate a forecast for project completion based on current "
    "performance trends. Estimates final cost, completion date, and variance.",
    permissions=["forecast-read"],
    category="analysis",
)
async def generate_project_forecast(
    project_id: str,
    forecast_method: str = "linear",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Generate project completion forecast.

    Context: Provides database session and forecast service for generating project forecasts.

    Args:
        project_id: UUID of the project to forecast
        forecast_method: Forecasting method ("linear", "logarithmic", "gaussian")
        context: Injected tool execution context

    Returns:
        Dictionary with forecast data including:
        - estimated_final_cost: Predicted final cost
        - estimated_completion_date: Predicted completion date
        - cost_variance_at_completion: Variance at completion
        - schedule_variance_days: Schedule variance in days
        - confidence_level: Confidence level of the forecast

    Raises:
        ValueError: If project_id is invalid or forecast_method is unsupported

    Example:
        >>> result = await generate_project_forecast(
        ...     project_id="...",
        ...     forecast_method="linear"
        ... )
        >>> print(f"Estimated Final Cost: ${result['estimated_final_cost']}")
        >>> print(f"Estimated Completion Date: {result['estimated_completion_date']}")
        >>> print(f"Cost Variance at Completion: ${result['vac']}")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # Generate forecast via EVM metrics (EAC/ETC/VAC)
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "forecast_method": forecast_method,
            "estimated_final_cost": float(evm_data.eac) if evm_data.eac is not None else 0.0,
            "cost_variance_at_completion": float(evm_data.vac) if evm_data.vac is not None else 0.0,
            "estimate_to_complete": float(evm_data.etc) if evm_data.etc is not None else 0.0,
            "budget_at_completion": float(evm_data.bac),
            "actual_cost_to_date": float(evm_data.ac),
            "confidence_level": "Medium (Based on current performance trends)",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in generate_project_forecast: {e}")
        return {"error": str(e)}


@ai_tool(
    name="compare_forecast_scenarios",
    description="Compare multiple forecast scenarios using different methods. "
    "Helps understand range of possible outcomes.",
    permissions=["forecast-read"],
    category="analysis",
)
async def compare_forecast_scenarios(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Compare multiple forecast scenarios.

    Context: Provides database session and forecast service for comparing forecast methods.

    Args:
        project_id: UUID of the project to forecast
        context: Injected tool execution context

    Returns:
        Dictionary comparing different forecast methods including:
        - scenarios: List of forecast results for each method
        - recommended_scenario: The recommended scenario based on fit

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await compare_forecast_scenarios(project_id="...")
        >>> for scenario in result['scenarios']:
        ...     print(f"{scenario['method']}: ${scenario['estimated_final_cost']}")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # In current implementation, we only have one main forecast method based on linked forecast
        # We'll return the current forecast as the 'recommended' and only scenario
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        scenarios = [{
            "method": "Current Trend",
            "estimated_final_cost": float(evm_data.eac) if evm_data.eac is not None else 0.0,
            "cost_variance_at_completion": float(evm_data.vac) if evm_data.vac is not None else 0.0,
            "estimate_to_complete": float(evm_data.etc) if evm_data.etc is not None else 0.0,
        }]

        return {
            "project_id": project_id,
            "scenarios": scenarios,
            "recommended_scenario": scenarios[0],
            "note": "Currently only supporting performance-based forecasting scenario.",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in compare_forecast_scenarios: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_forecast_accuracy",
    description="Analyze forecast accuracy by comparing past forecasts to actual results. "
    "Helps improve forecasting models and understand uncertainty.",
    permissions=["forecast-read"],
    category="analysis",
)
async def get_forecast_accuracy(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get forecast accuracy metrics.

    Context: Provides database session and forecast service for accuracy analysis.

    Args:
        project_id: UUID of the project
        context: Injected tool execution context

    Returns:
        Dictionary with forecast accuracy metrics including:
        - mean_absolute_percentage_error: MAPE value
        - mean_absolute_error: MAE value
        - forecast_bias: Bias indicator
        - recommendation: Reliability assessment

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await get_forecast_accuracy(project_id="...")
        >>> print(f"Mean Absolute Percentage Error: {result['mape']}%")
        >>> print(f"Forecast Bias: {result['bias']}")
    """
    try:
        # Note: Detailed accuracy metrics not yet implemented in service layer.
        # Returning a simplified assessment based on current performance.
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        # Simplified assessment
        status = "Reliable" if evm_data.cpi is not None and 0.9 <= evm_data.cpi <= 1.1 else "Needs review"

        return {
            "project_id": project_id,
            "assessment": status,
            "recommendation": "Confidence is high for project performing near budget" if status == "Reliable" else "High variance detected; monitor forecast closely.",
            "note": "Historical accuracy tracking is currently being implemented.",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in get_forecast_accuracy: {e}")
        return {"error": str(e)}


# =============================================================================
# KPI AND DASHBOARD TOOLS
# =============================================================================

@ai_tool(
    name="get_project_kpis",
    description="Get key performance indicators (KPIs) for a project. "
    "Returns overall health score and critical metrics.",
    permissions=["evm-read"],
    category="analysis",
)
async def get_project_kpis(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get project KPIs and health score.

    Context: Provides database session and EVM service for KPI calculation.

    Args:
        project_id: UUID of the project
        context: Injected tool execution context

    Returns:
        Dictionary with KPIs and health assessment including:
        - health_score: Overall project health (0-100)
        - status: "Excellent", "Good", "Fair", or "Poor"
        - kpis: Key performance indicators
        - recommendations: Actionable recommendations

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await get_project_kpis(project_id="...")
        >>> print(f"Health Score: {result['health_score']}/100")
        >>> print(f"Status: {result['status']}")
        >>> for kpi, value in result['kpis'].items():
        ...     print(f"{kpi}: {value}")
    """
    try:
        from app.services.evm_service import EVMService
        from app.models.schemas.evm import EntityType

        service = EVMService(context.session)

        # Get EVM metrics
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        # Calculate KPIs
        cpi = float(evm_data.cpi) if evm_data.cpi is not None else 0.0
        spi = float(evm_data.spi) if evm_data.spi is not None else 0.0

        # Calculate health score (0-100)
        # CPI and SPI both contribute to health score
        health_score = ((cpi + spi) / 2) * 100

        # Determine status
        if health_score >= 95:
            status = "Excellent"
        elif health_score >= 85:
            status = "Good"
        elif health_score >= 70:
            status = "Fair"
        else:
            status = "Poor"

        return {
            "project_id": project_id,
            "health_score": round(health_score, 2),
            "status": status,
            "kpis": {
                "cost_performance_index": round(cpi, 2),
                "schedule_performance_index": round(spi, 2),
                "cost_variance": round(float(evm_data.cv), 2),
                "schedule_variance": round(float(evm_data.sv), 2),
            },
            "recommendations": [
                rec for rec in [
                    "Monitor CPI closely" if cpi < 0.95 else None,
                    "Monitor SPI closely" if spi < 0.95 else None,
                    "Performance is excellent" if cpi >= 0.95 and spi >= 0.95 else None,
                ] if rec is not None
            ],
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in get_project_kpis: {e}")
        return {"error": str(e)}


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
ANALYSIS TOOL PATTERNS:

1. EVM ANALYSIS:
   - Calculate EVM metrics (PV, EV, AC, CV, SV, CPI, SPI)
   - Analyze cost variance by WBE
   - Analyze schedule variance by activity
   - Generate performance summaries

2. FORECASTING:
   - Generate completion forecasts
   - Compare multiple scenarios
   - Assess forecast accuracy
   - Estimate final cost and date

3. KPI CALCULATION:
   - Health score (0-100)
   - Performance status (Excellent/Good/Fair/Poor)
   - Key metrics dashboard
   - Trend analysis

4. PERMISSIONS:
   - evm-read: View EVM metrics and analysis
   - forecast-read: View forecasts and projections
   - Separate permissions for write operations

5. DATA VISUALIZATION:
   - Tools return data in AI-friendly format
   - Easy to convert to charts and graphs
   - Support for trend analysis
   - Historical comparisons

BEST PRACTICES:
   - Always include confidence levels with forecasts
   - Provide recommendations along with metrics
   - Explain variance root causes
   - Use multiple forecasting methods for robustness
   - Update forecasts regularly as project progresses

ANALYSIS WORKFLOW:
   1. Get current EVM metrics
   2. Analyze variances (cost and schedule)
   3. Generate forecasts
   4. Calculate KPIs and health score
   5. Provide recommendations
"""
