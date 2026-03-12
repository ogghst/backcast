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

        service = EVMService(context.session)

        # Parse date if provided
        as_of = datetime.fromisoformat(as_of_date) if as_of_date else None

        # Call service method to calculate EVM
        # Note: Using placeholder implementation for template
        # In production, this would call: evm_data = await service.calculate_evm_metrics(...)
        evm_data = await service.calculate_evm_metrics(
            project_id=UUID(project_id),
            as_of=as_of,
        )

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "as_of_date": as_of_date or datetime.now().isoformat(),
            "planned_value": float(evm_data.planned_value) if hasattr(evm_data, 'planned_value') and evm_data.planned_value else 0.0,
            "earned_value": float(evm_data.earned_value) if hasattr(evm_data, 'earned_value') and evm_data.earned_value else 0.0,
            "actual_cost": float(evm_data.actual_cost) if hasattr(evm_data, 'actual_cost') and evm_data.actual_cost else 0.0,
            "cost_variance": float(evm_data.cost_variance) if hasattr(evm_data, 'cost_variance') and evm_data.cost_variance else 0.0,
            "schedule_variance": float(evm_data.schedule_variance) if hasattr(evm_data, 'schedule_variance') and evm_data.schedule_variance else 0.0,
            "cost_performance_index": float(evm_data.cpi) if hasattr(evm_data, 'cpi') and evm_data.cpi else 0.0,
            "schedule_performance_index": float(evm_data.spi) if hasattr(evm_data, 'spi') and evm_data.spi else 0.0,
            "variance_at_completion": float(evm_data.vac) if hasattr(evm_data, 'vac') and evm_data.vac else 0.0,
            "estimate_to_complete": float(evm_data.etc) if hasattr(evm_data, 'etc') and evm_data.etc else 0.0,
            "estimate_at_completion": float(evm_data.eac) if hasattr(evm_data, 'eac') and evm_data.eac else 0.0,
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

        service = EVMService(context.session)

        # Get EVM metrics
        evm_data = await service.calculate_evm(project_id=UUID(project_id))  # type: ignore[attr-defined]

        # Determine performance status
        cpi = float(evm_data.cpi) if hasattr(evm_data, 'cpi') and evm_data.cpi else 0.0
        spi = float(evm_data.spi) if hasattr(evm_data, 'spi') and evm_data.spi else 0.0

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

        service = EVMService(context.session)

        # Get cost variance analysis
        variance_data = await service.analyze_cost_variance(project_id=UUID(project_id))  # type: ignore[attr-defined]

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "total_variance": float(variance_data.total_variance) if hasattr(variance_data, 'total_variance') and variance_data.total_variance else 0.0,
            "variance_percentage": variance_data.variance_percentage if hasattr(variance_data, 'variance_percentage') and variance_data.variance_percentage else 0.0,
            "variance_by_wbe": [
                {
                    "wbe_id": str(v.wbe_id),
                    "wbe_name": v.wbe_name,
                    "variance": float(v.variance) if hasattr(v, 'variance') and v.variance else 0.0,
                    "variance_percentage": v.variance_percentage if hasattr(v, 'variance_percentage') and v.variance_percentage else 0.0,
                }
                for v in variance_data.by_wbe
            ] if hasattr(variance_data, 'by_wbe') and variance_data.by_wbe else [],
            "root_causes": variance_data.root_causes if hasattr(variance_data, 'root_causes') and variance_data.root_causes else [],
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

        service = EVMService(context.session)

        # Get schedule variance analysis
        variance_data = await service.analyze_schedule_variance(project_id=UUID(project_id))  # type: ignore[attr-defined]

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "total_variance_days": variance_data.total_variance_days if hasattr(variance_data, 'total_variance_days') and variance_data.total_variance_days else 0,
            "critical_path_delay_days": variance_data.critical_path_delay_days if hasattr(variance_data, 'critical_path_delay_days') and variance_data.critical_path_delay_days else 0,
            "delayed_activities": [
                {
                    "activity_id": str(a.activity_id),
                    "activity_name": a.activity_name,
                    "delay_days": a.delay_days if hasattr(a, 'delay_days') and a.delay_days else 0,
                }
                for a in variance_data.delayed_activities
            ] if hasattr(variance_data, 'delayed_activities') and variance_data.delayed_activities else [],
            "schedule_risks": variance_data.schedule_risks if hasattr(variance_data, 'schedule_risks') and variance_data.schedule_risks else [],
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
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        # Generate forecast
        forecast = await service.generate_forecast(  # type: ignore[attr-defined]
            project_id=UUID(project_id),
            method=forecast_method,
        )

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "forecast_method": forecast_method,
            "estimated_final_cost": float(forecast.estimated_final_cost) if hasattr(forecast, 'estimated_final_cost') and forecast.estimated_final_cost else 0.0,
            "estimated_completion_date": forecast.estimated_completion_date.isoformat() if hasattr(forecast, 'estimated_completion_date') and forecast.estimated_completion_date else None,
            "cost_variance_at_completion": float(forecast.vac) if hasattr(forecast, 'vac') and forecast.vac else 0.0,
            "schedule_variance_days": forecast.schedule_variance_days if hasattr(forecast, 'schedule_variance_days') and forecast.schedule_variance_days else 0,
            "confidence_level": forecast.confidence_level if hasattr(forecast, 'confidence_level') and forecast.confidence_level else "Medium",
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
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        # Generate forecasts using different methods
        methods = ["linear", "logarithmic", "gaussian"]
        scenarios = []

        for method in methods:
            try:
                forecast = await service.generate_forecast(  # type: ignore[attr-defined]
                    project_id=UUID(project_id),
                    method=method,
                )
                scenarios.append({
                    "method": method,
                    "estimated_final_cost": float(forecast.estimated_final_cost) if hasattr(forecast, 'estimated_final_cost') and forecast.estimated_final_cost else 0.0,
                    "estimated_completion_date": forecast.estimated_completion_date.isoformat() if hasattr(forecast, 'estimated_completion_date') and forecast.estimated_completion_date else None,
                    "cost_variance_at_completion": float(forecast.vac) if hasattr(forecast, 'vac') and forecast.vac else 0.0,
                })
            except Exception:
                # Skip methods that don't work for this project
                pass

        return {
            "project_id": project_id,
            "scenarios": scenarios,
            "recommended_scenario": scenarios[0] if scenarios else None,
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
        from app.services.forecast_service import ForecastService

        service = ForecastService(context.session)

        # Get forecast accuracy metrics
        accuracy = await service.get_forecast_accuracy(project_id=UUID(project_id))  # type: ignore[attr-defined]

        # Convert to AI-friendly format
        return {
            "project_id": project_id,
            "mean_absolute_percentage_error": accuracy.mape if hasattr(accuracy, 'mape') and accuracy.mape else 0.0,
            "mean_absolute_error": float(accuracy.mae) if hasattr(accuracy, 'mae') and accuracy.mae else 0.0,
            "forecast_bias": accuracy.bias if hasattr(accuracy, 'bias') and accuracy.bias else 0.0,
            "recommendation": "Forecasts are reliable" if hasattr(accuracy, 'mape') and accuracy.mape and accuracy.mape < 10 else "Forecasts have high uncertainty",
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

        service = EVMService(context.session)

        # Get EVM metrics
        evm_data = await service.calculate_evm(project_id=UUID(project_id))  # type: ignore[attr-defined]

        # Calculate KPIs
        cpi = float(evm_data.cpi) if hasattr(evm_data, 'cpi') and evm_data.cpi else 0.0
        spi = float(evm_data.spi) if hasattr(evm_data, 'spi') and evm_data.spi else 0.0

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
                "cost_variance": round(float(evm_data.cost_variance) if hasattr(evm_data, 'cost_variance') and evm_data.cost_variance else 0.0, 2),
                "schedule_variance": round(float(evm_data.schedule_variance) if hasattr(evm_data, 'schedule_variance') and evm_data.schedule_variance else 0.0, 2),
            },
            "recommendations": [
                "Monitor CPI closely" if cpi < 0.95 else None,
                "Monitor SPI closely" if spi < 0.95 else None,
                "Performance is excellent" if cpi >= 0.95 and spi >= 0.95 else None,
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
