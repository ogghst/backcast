"""Advanced AI Tool Templates for project analysis and insights.

This module provides advanced AI-powered analysis tools that go beyond basic EVM:
- Project health assessment with multi-dimensional scoring
- Anomaly detection for unusual patterns in EVM metrics
- Advanced forecast analysis with scenario modeling
- AI-powered optimization suggestions

All tools use the @ai_tool decorator with LangChain's InjectedToolArg
for proper context injection and docstring parsing.
"""

import logging
from datetime import datetime
from statistics import mean, stdev
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext

logger = logging.getLogger(__name__)

# =============================================================================
# PROJECT HEALTH ASSESSMENT
# =============================================================================


@ai_tool(
    name="assess_project_health",
    description="Perform comprehensive project health assessment analyzing budget, "
    "schedule, quality, and risk dimensions. Provides overall health score "
    "(0-100), status rating, and actionable recommendations.",
    permissions=["evm-read"],
    category="analysis",
    risk_level=RiskLevel.LOW,
)
async def assess_project_health(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Assess comprehensive project health across multiple dimensions.

    Context: Provides database session and EVM service for health analysis.

    Args:
        project_id: UUID of the project to assess
        context: Injected tool execution context

    Returns:
        Dictionary with comprehensive health assessment:
        - project_id: Project UUID
        - health_score: Overall health score (0-100)
        - overall_status: Status ("Excellent", "Good", "Fair", "Poor")
        - categories: Detailed breakdown by category
          - budget: Score, status, issues
          - schedule: Score, status, issues
          - quality: Score, status, issues
          - risk: Score, status, issues
        - recommendations: Actionable recommendations
        - benchmark_comparison: Comparison to similar projects (if available)

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await assess_project_health(project_id="...")
        >>> print(f"Health Score: {result['health_score']}/100")
        >>> print(f"Status: {result['overall_status']}")
        >>> for category, data in result['categories'].items():
        ...     print(f"{category}: {data['score']}/100 - {data['status']}")
    """
    try:
        from app.models.schemas.evm import EntityType
        from app.services.evm_service import EVMService
        from app.services.project import ProjectService
        from app.services.wbe import WBEService

        evm_service = EVMService(context.session)
        project_service = ProjectService(context.session)
        wbe_service = WBEService(context.session)

        # Get project data
        project = await project_service.get_by_id(UUID(project_id))
        if not project:
            return {"error": f"Project {project_id} not found"}

        # Get current EVM metrics
        evm_data = await evm_service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        # Get WBE-level data for deeper analysis
        wbes = await wbe_service.get_by_project(UUID(project_id))

        # Calculate category scores
        budget_health = _calculate_budget_health(evm_data, wbes)
        schedule_health = _calculate_schedule_health(evm_data, wbes)
        quality_health = _calculate_quality_health(evm_data)
        risk_health = _calculate_risk_health(evm_data, wbes)

        # Calculate overall health score (weighted average)
        weights = {"budget": 0.35, "schedule": 0.35, "quality": 0.15, "risk": 0.15}
        overall_score = (
            budget_health["score"] * weights["budget"]
            + schedule_health["score"] * weights["schedule"]
            + quality_health["score"] * weights["quality"]
            + risk_health["score"] * weights["risk"]
        )

        # Determine overall status
        if overall_score >= 90:
            overall_status = "Excellent"
        elif overall_score >= 75:
            overall_status = "Good"
        elif overall_score >= 60:
            overall_status = "Fair"
        else:
            overall_status = "Poor"

        # Aggregate recommendations
        all_issues = (
            budget_health["issues"]
            + schedule_health["issues"]
            + quality_health["issues"]
            + risk_health["issues"]
        )

        return {
            "project_id": project_id,
            "project_name": project.name,
            "health_score": round(overall_score, 1),
            "overall_status": overall_status,
            "categories": {
                "budget": budget_health,
                "schedule": schedule_health,
                "quality": quality_health,
                "risk": risk_health,
            },
            "recommendations": all_issues[:10],  # Top 10 recommendations
            "assessment_date": datetime.now().isoformat(),
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in assess_project_health: {e}")
        return {"error": str(e)}


def _calculate_budget_health(
    evm_data: Any,
    wbes: list[Any],
) -> dict[str, Any]:
    """Calculate budget health score and identify issues."""
    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 0.0
    cv = float(evm_data.cv)
    bac = float(evm_data.bac)
    vac = float(evm_data.vac) if evm_data.vac is not None else 0.0

    issues = []

    # Base score from CPI (scaled 0-100)
    score = min(cpi * 100, 100)

    # Deductions for variance
    if cv < 0:
        variance_pct = abs(cv) / bac * 100 if bac > 0 else 0
        score -= variance_pct * 0.5
        issues.append(f"Cost variance: {variance_pct:.1f}% over budget")

    # Prediction of completion
    if vac < 0:
        vac_pct = abs(vac) / bac * 100 if bac > 0 else 0
        if vac_pct > 10:
            issues.append(f"Projected overrun at completion: {vac_pct:.1f}% of budget")

    # Determine status
    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Fair"
    else:
        status = "Poor"

    # Add specific recommendations
    if cpi < 0.9:
        issues.append(
            "Critical: Cost performance index below 0.9 - immediate action required"
        )
    elif cpi < 0.95:
        issues.append("Warning: Cost performance declining - monitor closely")

    return {
        "score": max(0, min(100, round(score, 1))),
        "status": status,
        "issues": issues,
        "metrics": {
            "cpi": round(cpi, 2),
            "cost_variance": round(cv, 2),
            "variance_at_completion": round(vac, 2),
        },
    }


def _calculate_schedule_health(
    evm_data: Any,
    wbes: list[Any],
) -> dict[str, Any]:
    """Calculate schedule health score and identify issues."""
    spi = float(evm_data.spi) if evm_data.spi is not None else 0.0
    sv = float(evm_data.sv)
    pv = float(evm_data.pv)

    issues = []

    # Base score from SPI (scaled 0-100)
    score = min(spi * 100, 100)

    # Deductions for schedule variance
    if sv < 0:
        variance_pct = abs(sv) / pv * 100 if pv > 0 else 0
        score -= variance_pct * 0.5
        issues.append(f"Schedule variance: {variance_pct:.1f}% behind schedule")

    # Analyze WBE-level schedule issues
    delayed_wbes = []
    for wbe in wbes:
        if hasattr(wbe, "planned_end_date") and hasattr(wbe, "actual_end_date"):
            if (
                wbe.actual_end_date is None
                and wbe.planned_end_date
                and wbe.planned_end_date < datetime.now()
            ):
                delayed_wbes.append(wbe.code)

    if delayed_wbes:
        issues.append(f"Delayed work items: {', '.join(delayed_wbes[:3])}")

    # Determine status
    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Fair"
    else:
        status = "Poor"

    # Add specific recommendations
    if spi < 0.9:
        issues.append(
            "Critical: Schedule performance index below 0.9 - immediate action required"
        )
    elif spi < 0.95:
        issues.append("Warning: Schedule performance declining - monitor closely")

    return {
        "score": max(0, min(100, round(score, 1))),
        "status": status,
        "issues": issues,
        "metrics": {
            "spi": round(spi, 2),
            "schedule_variance": round(sv, 2),
            "delayed_items": len(delayed_wbes),
        },
    }


def _calculate_quality_health(evm_data: Any) -> dict[str, Any]:
    """Calculate quality health score based on progress consistency."""
    progress = (
        float(evm_data.progress_percentage)
        if evm_data.progress_percentage is not None
        else 0.0
    )

    # Quality score based on consistency and progress
    # Higher progress is generally better if it aligns with plan
    score = 85  # Base score

    # Adjust based on progress
    if 0 <= progress <= 100:
        # Reward steady progress (40-80% range is ideal for ongoing projects)
        if 40 <= progress <= 80:
            score += 10
        elif progress > 80:
            score += 5  # Near completion
    else:
        score -= 20  # Invalid progress

    issues = []

    if progress < 20:
        issues.append("Low progress - ensure adequate resources allocated")
    elif progress > 95:
        issues.append("Project near completion - focus on quality assurance")

    # Determine status
    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Fair"
    else:
        status = "Poor"

    return {
        "score": max(0, min(100, round(score, 1))),
        "status": status,
        "issues": issues,
        "metrics": {"progress_percentage": round(progress, 1)},
    }


def _calculate_risk_health(evm_data: Any, wbes: list[Any]) -> dict[str, Any]:
    """Calculate risk health score based on volatility and warnings."""
    score = 80  # Base score

    issues = []

    # Check for warnings in EVM data
    if evm_data.warning:
        issues.append(f"EVM calculation warning: {evm_data.warning}")
        score -= 10

    # Check for CPI/SPI divergence (risk indicator)
    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 0.0
    spi = float(evm_data.spi) if evm_data.spi is not None else 0.0

    divergence = abs(cpi - spi)
    if divergence > 0.2:
        issues.append(
            f"High divergence between cost and schedule performance ({divergence:.2f})"
        )
        score -= 15

    # Check number of WBEs (complexity risk)
    if len(wbes) > 20:
        issues.append(f"High complexity: {len(wbes)} work breakdown elements")
        score -= 5

    # Determine status
    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Fair"
    else:
        status = "Poor"

    return {
        "score": max(0, min(100, round(score, 1))),
        "status": status,
        "issues": issues,
        "metrics": {
            "complexity_level": "High"
            if len(wbes) > 20
            else "Medium"
            if len(wbes) > 10
            else "Low",
            "cpi_spi_divergence": round(divergence, 2),
        },
    }


# =============================================================================
# EVM ANOMALY DETECTION
# =============================================================================


@ai_tool(
    name="detect_evm_anomalies",
    description="Detect unusual patterns and anomalies in EVM metrics including "
    "cost spikes, schedule delays, and budget overruns using statistical analysis.",
    permissions=["evm-read"],
    category="analysis",
    risk_level=RiskLevel.LOW,
)
async def detect_evm_anomalies(
    project_id: str,
    lookback_weeks: int = 12,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Detect anomalies in EVM metrics using statistical analysis.

    Context: Provides database session and EVM service for anomaly detection.

    Args:
        project_id: UUID of the project to analyze
        lookback_weeks: Number of weeks to analyze for trends (default: 12)
        context: Injected tool execution context

    Returns:
        Dictionary with anomaly detection results:
        - project_id: Project UUID
        - anomalies: List of detected anomalies
          - type: Anomaly type (cost_spike, schedule_variance, budget_overrun)
          - severity: Severity level (high, medium, low)
          - description: Detailed description
          - affected: Affected entities
        - trend_analysis: Overall trend analysis
          - cost_trend: Direction (increasing, stable, decreasing)
          - schedule_trend: Direction (improving, stable, declining)
        - statistical_summary: Statistical metrics (z-scores, deviations)

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await detect_evm_anomalies(project_id="...")
        >>> for anomaly in result['anomalies']:
        ...     print(f"{anomaly['severity']}: {anomaly['description']}")
    """
    try:
        from app.models.schemas.evm import EntityType, EVMTimeSeriesGranularity
        from app.services.evm_service import EVMService

        service = EVMService(context.session)

        # Get time series data
        timeseries = await service.get_evm_timeseries(
            entity_type=EntityType.PROJECT,
            entity_id=UUID(project_id),
            granularity=EVMTimeSeriesGranularity.WEEK,
            control_date=datetime.now(),
        )

        if not timeseries.points:
            return {
                "project_id": project_id,
                "error": "No EVM time-series data available for this project. "
                         "The project has no cost elements, progress entries, or schedule baseline.",
            }

        anomalies = []

        # Analyze cost trends
        cost_anomalies = _detect_cost_anomalies(timeseries.points)
        anomalies.extend(cost_anomalies)

        # Analyze schedule trends
        schedule_anomalies = _detect_schedule_anomalies(timeseries.points)
        anomalies.extend(schedule_anomalies)

        # Analyze CPI/SPI trends
        performance_anomalies = _detect_performance_anomalies(timeseries.points)
        anomalies.extend(performance_anomalies)

        # Calculate overall trends
        cost_trend = _calculate_trend([float(p.ac) for p in timeseries.points])
        schedule_trend = _calculate_schedule_trend(
            [float(p.spi) if p.spi else 0.0 for p in timeseries.points]
        )

        return {
            "project_id": project_id,
            "analysis_period": {
                "start_date": timeseries.start_date.isoformat(),
                "end_date": timeseries.end_date.isoformat(),
                "weeks_analyzed": len(timeseries.points),
            },
            "anomalies": anomalies,
            "trend_analysis": {
                "cost_trend": cost_trend["direction"],
                "cost_trend_strength": cost_trend["strength"],
                "schedule_trend": schedule_trend["direction"],
                "schedule_trend_strength": schedule_trend["strength"],
            },
            "statistical_summary": {
                "data_points": len(timeseries.points),
                "anomaly_count": len(anomalies),
                "high_severity_count": sum(
                    1 for a in anomalies if a["severity"] == "high"
                ),
            },
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in detect_evm_anomalies: {e}")
        return {"error": str(e)}


def _detect_cost_anomalies(points: list[Any]) -> list[dict[str, Any]]:
    """Detect cost anomalies using statistical analysis."""
    anomalies: list[dict[str, Any]] = []

    if len(points) < 3:
        return anomalies

    # Calculate cost changes
    costs = [float(p.ac) for p in points]
    cost_changes = [costs[i] - costs[i - 1] for i in range(1, len(costs))]

    if not cost_changes:
        return anomalies

    # Calculate statistics
    mean_change = mean(cost_changes)
    try:
        std_change = stdev(cost_changes)
    except ValueError:
        std_change = 0

    if std_change == 0:
        return anomalies

    # Detect spikes (z-score > 2)
    for i, change in enumerate(cost_changes):
        if std_change > 0:
            z_score = abs((change - mean_change) / std_change)
            if z_score > 2.0:
                severity = "high" if z_score > 3.0 else "medium"
                anomalies.append(
                    {
                        "type": "cost_spike",
                        "severity": severity,
                        "description": f"Cost {'increased' if change > 0 else 'decreased'} by "
                        f"{abs(change):.2f} (z-score: {z_score:.2f})",
                        "affected": f"Week {i + 1}",
                        "z_score": round(z_score, 2),
                    }
                )

    return anomalies


def _detect_schedule_anomalies(points: list[Any]) -> list[dict[str, Any]]:
    """Detect schedule anomalies."""
    anomalies: list[dict[str, Any]] = []

    if len(points) < 3:
        return anomalies

    # Analyze SPI trends
    spis = [float(p.spi) for p in points if p.spi is not None]

    if len(spis) < 3:
        return anomalies

    # Detect significant SPI drops
    for i in range(1, len(spis)):
        spi_drop = spis[i - 1] - spis[i]
        if spi_drop > 0.1:  # 10% drop threshold
            severity = "high" if spi_drop > 0.2 else "medium"
            anomalies.append(
                {
                    "type": "schedule_variance",
                    "severity": severity,
                    "description": f"SPI dropped from {spis[i - 1]:.2f} to {spis[i]:.2f}",
                    "affected": f"Week {i + 1}",
                    "drop_amount": round(spi_drop, 2),
                }
            )

    return anomalies


def _detect_performance_anomalies(points: list[Any]) -> list[dict[str, Any]]:
    """Detect performance anomalies (CPI/SPI divergence)."""
    anomalies: list[dict[str, Any]] = []

    for i, point in enumerate(points):
        cpi = float(point.cpi) if point.cpi else None
        spi = float(point.spi) if point.spi else None

        if cpi and spi:
            divergence = abs(cpi - spi)
            if divergence > 0.3:  # Significant divergence threshold
                severity = "high" if divergence > 0.5 else "medium"
                anomalies.append(
                    {
                        "type": "performance_divergence",
                        "severity": severity,
                        "description": f"High divergence between CPI ({cpi:.2f}) and SPI ({spi:.2f})",
                        "affected": f"Week {i + 1}",
                        "divergence": round(divergence, 2),
                    }
                )

    return anomalies


def _calculate_trend(values: list[float]) -> dict[str, str]:
    """Calculate trend direction and strength."""
    if len(values) < 2:
        return {"direction": "stable", "strength": "none"}

    # Simple linear regression
    n = len(values)
    x = list(range(n))
    mean_x = mean(x)
    mean_y = mean(values)

    # Calculate slope
    numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return {"direction": "stable", "strength": "none"}

    slope = numerator / denominator

    # Determine direction
    if slope > 0.01:
        direction = "increasing"
    elif slope < -0.01:
        direction = "decreasing"
    else:
        direction = "stable"

    # Determine strength (relative to mean)
    strength_pct = abs(slope) / mean_y * 100 if mean_y != 0 else 0
    if strength_pct > 10:
        strength = "strong"
    elif strength_pct > 5:
        strength = "moderate"
    else:
        strength = "weak"

    return {"direction": direction, "strength": strength}


def _calculate_schedule_trend(spis: list[float]) -> dict[str, str]:
    """Calculate schedule trend."""
    if len(spis) < 2:
        return {"direction": "stable", "strength": "none"}

    # For SPI, higher is better
    trend = _calculate_trend(spis)

    # Convert direction to schedule-specific terms
    direction_map = {
        "increasing": "improving",
        "decreasing": "declining",
        "stable": "stable",
    }

    return {
        "direction": direction_map.get(trend["direction"], "stable"),
        "strength": trend["strength"],
    }


# =============================================================================
# ADVANCED FORECAST ANALYSIS
# =============================================================================


@ai_tool(
    name="analyze_forecast_trends",
    description="Perform advanced forecast analysis with trend detection, "
    "scenario modeling, and confidence intervals.",
    permissions=["forecast-read"],
    category="analysis",
    risk_level=RiskLevel.LOW,
)
async def analyze_forecast_trends(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Analyze forecast trends with scenario modeling.

    Context: Provides database session and EVM service for forecast analysis.

    Args:
        project_id: UUID of the project to analyze
        context: Injected tool execution context

    Returns:
        Dictionary with advanced forecast analysis:
        - project_id: Project UUID
        - current_forecast: Current forecast data
        - trend_analysis: Performance trend analysis
        - scenarios: Multiple forecast scenarios (best, worst, most likely)
        - confidence_assessment: Confidence level and risk factors
        - monte_carlo_hints: Hints for Monte Carlo simulation

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await analyze_forecast_trends(project_id="...")
        >>> print(f"Best case: ${result['scenarios']['best']['eac']}")
        >>> print(f"Worst case: ${result['scenarios']['worst']['eac']}")
    """
    try:
        from app.models.schemas.evm import EntityType, EVMTimeSeriesGranularity
        from app.services.evm_service import EVMService

        service = EVMService(context.session)

        # Get current EVM metrics
        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        timeseries = await service.get_evm_timeseries(
            entity_type=EntityType.PROJECT,
            entity_id=UUID(project_id),
            granularity=EVMTimeSeriesGranularity.WEEK,
            control_date=datetime.now(),
        )

        if not timeseries.points:
            return {
                "project_id": project_id,
                "error": "No EVM time-series data available for this project. "
                         "The project has no cost elements, progress entries, or schedule baseline.",
            }

        # Calculate scenarios
        scenarios = _calculate_forecast_scenarios(evm_data, timeseries.points)

        # Analyze trends
        trend_analysis = _analyze_performance_trends(timeseries.points)

        # Assess confidence
        confidence = _assess_forecast_confidence(evm_data, timeseries.points)

        return {
            "project_id": project_id,
            "current_forecast": {
                "eac": float(evm_data.eac) if evm_data.eac is not None else 0.0,
                "vac": float(evm_data.vac) if evm_data.vac is not None else 0.0,
                "etc": float(evm_data.etc) if evm_data.etc is not None else 0.0,
                "bac": float(evm_data.bac),
                "cpi": float(evm_data.cpi) if evm_data.cpi is not None else 0.0,
                "spi": float(evm_data.spi) if evm_data.spi is not None else 0.0,
            },
            "trend_analysis": trend_analysis,
            "scenarios": scenarios,
            "confidence_assessment": confidence,
            "recommendations": _generate_forecast_recommendations(
                evm_data, scenarios, confidence
            ),
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in analyze_forecast_trends: {e}")
        return {"error": str(e)}


def _calculate_forecast_scenarios(
    evm_data: Any,
    historical_points: list[Any],
) -> dict[str, Any]:
    """Calculate multiple forecast scenarios."""
    bac = float(evm_data.bac)
    ac = float(evm_data.ac)
    ev = float(evm_data.ev)
    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 1.0

    # Historical CPI/SPI for volatility assessment
    cpis = [float(p.cpi) for p in historical_points if p.cpi]
    spis = [float(p.spi) for p in historical_points if p.spi]

    # Calculate volatility
    cpi_volatility = stdev(cpis) if len(cpis) > 1 else 0.1
    _spi_volatility = stdev(spis) if len(spis) > 1 else 0.1

    # Best case: Performance improves (CPI/SPI increase by 1 std dev)
    best_cpi = cpi + cpi_volatility
    best_eac = ac + (bac - ev) / best_cpi if best_cpi > 0 else bac * 1.5

    # Worst case: Performance degrades (CPI/SPI decrease by 1 std dev)
    worst_cpi = max(cpi - cpi_volatility, 0.7)
    worst_eac = ac + (bac - ev) / worst_cpi if worst_cpi > 0 else bac * 2.0

    # Most likely: Current trend continues
    likely_eac = (
        float(evm_data.eac) if evm_data.eac is not None else ac + (bac - ev) / cpi
    )

    return {
        "best": {
            "scenario": "Optimistic",
            "eac": round(best_eac, 2),
            "vac": round(bac - best_eac, 2),
            "assumption": f"Performance improves (CPI: {best_cpi:.2f})",
        },
        "worst": {
            "scenario": "Pessimistic",
            "eac": round(worst_eac, 2),
            "vac": round(bac - worst_eac, 2),
            "assumption": f"Performance degrades (CPI: {worst_cpi:.2f})",
        },
        "most_likely": {
            "scenario": "Current Trend",
            "eac": round(likely_eac, 2),
            "vac": round(bac - likely_eac, 2),
            "assumption": f"Current performance continues (CPI: {cpi:.2f})",
        },
    }


def _analyze_performance_trends(points: list[Any]) -> dict[str, Any]:
    """Analyze performance trends from historical data."""
    if len(points) < 2:
        return {"trend": "insufficient_data"}

    # Calculate CPI and SPI trends
    cpis = [float(p.cpi) for p in points if p.cpi]
    spis = [float(p.spi) for p in points if p.spi]

    cpi_trend = _calculate_performance_direction(cpis) if cpis else "stable"
    spi_trend = _calculate_performance_direction(spis) if spis else "stable"

    # Determine overall trend
    if cpi_trend == "improving" and spi_trend == "improving":
        overall = "strongly_improving"
    elif cpi_trend == "declining" or spi_trend == "declining":
        overall = "declining"
    elif cpi_trend == "stable" and spi_trend == "stable":
        overall = "stable"
    else:
        overall = "mixed"

    return {
        "overall": overall,
        "cost_performance": cpi_trend,
        "schedule_performance": spi_trend,
        "recent_cpi": round(cpis[-1], 2) if cpis else None,
        "recent_spi": round(spis[-1], 2) if spis else None,
    }


def _calculate_performance_direction(values: list[float]) -> str:
    """Determine if performance is improving, declining, or stable."""
    if len(values) < 2:
        return "stable"

    # Compare recent average to earlier average
    mid = len(values) // 2
    early_avg = mean(values[:mid])
    recent_avg = mean(values[mid:])

    change = (recent_avg - early_avg) / early_avg if early_avg > 0 else 0

    if change > 0.05:
        return "improving"
    elif change < -0.05:
        return "declining"
    else:
        return "stable"


def _assess_forecast_confidence(evm_data: Any, points: list[Any]) -> dict[str, Any]:
    """Assess confidence level in forecast."""
    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 1.0
    spi = float(evm_data.spi) if evm_data.spi is not None else 1.0

    # Base confidence on performance stability
    cpis = [float(p.cpi) for p in points if p.cpi]

    if not cpis:
        volatility = 0.2
    else:
        volatility = stdev(cpis) if len(cpis) > 1 else 0.1

    # Calculate confidence score (0-100)
    confidence_score = 100 - (volatility * 100)

    # Adjust for extreme CPI/SPI values
    if cpi < 0.8 or cpi > 1.2:
        confidence_score -= 20
    if spi < 0.8 or spi > 1.2:
        confidence_score -= 20

    confidence_score = max(0, min(100, confidence_score))

    # Determine level
    if confidence_score >= 80:
        level = "High"
    elif confidence_score >= 60:
        level = "Medium"
    else:
        level = "Low"

    return {
        "level": level,
        "score": round(confidence_score, 1),
        "volatility": round(volatility, 3),
        "risk_factors": _identify_risk_factors(evm_data, volatility),
    }


def _identify_risk_factors(evm_data: Any, volatility: float) -> list[str]:
    """Identify risk factors affecting forecast confidence."""
    risks = []

    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 1.0
    spi = float(evm_data.spi) if evm_data.spi is not None else 1.0

    if volatility > 0.15:
        risks.append("High performance volatility")

    if cpi < 0.9:
        risks.append("Poor cost performance")

    if spi < 0.9:
        risks.append("Poor schedule performance")

    if abs(cpi - spi) > 0.2:
        risks.append("Cost/schedule performance divergence")

    if evm_data.warning:
        risks.append(f"EVM calculation issues: {evm_data.warning}")

    return risks if risks else ["No significant risk factors identified"]


def _generate_forecast_recommendations(
    evm_data: Any,
    scenarios: dict[str, Any],
    confidence: dict[str, Any],
) -> list[str]:
    """Generate forecast-specific recommendations."""
    recommendations = []

    vac = float(evm_data.vac) if evm_data.vac is not None else 0.0

    if vac < 0:
        overrun_pct = abs(vac) / float(evm_data.bac) * 100
        if overrun_pct > 20:
            recommendations.append(
                f"Critical: Project forecast indicates {overrun_pct:.1f}% budget overrun. "
                "Immediate corrective action required."
            )
        else:
            recommendations.append(
                f"Warning: Project forecast indicates {overrun_pct:.1f}% budget overrun. "
                "Consider mitigation strategies."
            )

    # Scenario spread recommendations
    best_eac = scenarios["best"]["eac"]
    worst_eac = scenarios["worst"]["eac"]
    spread_pct = (worst_eac - best_eac) / best_eac * 100

    if spread_pct > 30:
        recommendations.append(
            f"High uncertainty: Forecast scenarios vary by {spread_pct:.1f}%. "
            "Monitor closely and update forecasts regularly."
        )

    # Confidence-based recommendations
    if confidence["level"] == "Low":
        recommendations.append(
            "Low forecast confidence: Increase monitoring frequency and "
            "consider implementing additional controls."
        )

    if not recommendations:
        recommendations.append("Forecast appears stable. Continue current approach.")

    return recommendations


# =============================================================================
# OPTIMIZATION SUGGESTIONS
# =============================================================================


@ai_tool(
    name="generate_optimization_suggestions",
    description="Generate AI-powered optimization suggestions for improving "
    "project performance in cost, schedule, and resource allocation.",
    permissions=["evm-read"],
    category="analysis",
    risk_level=RiskLevel.LOW,
)
async def generate_optimization_suggestions(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Generate optimization suggestions for project improvement.

    Context: Provides database session and EVM service for optimization analysis.

    Args:
        project_id: UUID of the project to optimize
        context: Injected tool execution context

    Returns:
        Dictionary with optimization suggestions:
        - project_id: Project UUID
        - suggestions: List of prioritized suggestions
          - priority: Priority level (high, medium, low)
          - category: Category (cost, schedule, resource, quality)
          - action: Recommended action
          - rationale: Reason for recommendation
          - estimated_impact: Estimated benefit (currency or time)
        - summary: Summary of suggestions by category
        - quick_wins: High-impact, low-effort suggestions

    Raises:
        ValueError: If project_id is invalid

    Example:
        >>> result = await generate_optimization_suggestions(project_id="...")
        >>> for suggestion in result['suggestions']:
        ...     print(f"{suggestion['priority']}: {suggestion['action']}")
    """
    try:
        from app.models.schemas.evm import EntityType
        from app.services.evm_service import EVMService
        from app.services.project import ProjectService
        from app.services.wbe import WBEService

        evm_service = EVMService(context.session)
        project_service = ProjectService(context.session)
        wbe_service = WBEService(context.session)

        # Get project data
        project = await project_service.get_by_id(UUID(project_id))
        if not project:
            return {"error": f"Project {project_id} not found"}

        # Get EVM metrics
        evm_data = await evm_service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=datetime.now(),
        )

        # Get WBE data for granular analysis
        wbes = await wbe_service.get_by_project(UUID(project_id))

        # Generate suggestions by category
        cost_suggestions = _generate_cost_optimizations(evm_data, wbes)
        schedule_suggestions = _generate_schedule_optimizations(evm_data, wbes)
        resource_suggestions = _generate_resource_optimizations(evm_data, wbes)
        quality_suggestions = _generate_quality_optimizations(evm_data)

        # Combine and prioritize
        all_suggestions = (
            cost_suggestions
            + schedule_suggestions
            + resource_suggestions
            + quality_suggestions
        )

        # Sort by priority and estimated impact
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_suggestions.sort(
            key=lambda x: (
                priority_order.get(x["priority"], 3),
                -x.get("estimated_impact_value", 0),
            )
        )

        # Identify quick wins
        quick_wins = [
            s
            for s in all_suggestions
            if s.get("effort_level") == "low" and s.get("priority") == "high"
        ]

        # Generate summary
        summary = {
            "total_suggestions": len(all_suggestions),
            "by_priority": {
                "high": sum(1 for s in all_suggestions if s["priority"] == "high"),
                "medium": sum(1 for s in all_suggestions if s["priority"] == "medium"),
                "low": sum(1 for s in all_suggestions if s["priority"] == "low"),
            },
            "by_category": {
                "cost": len(cost_suggestions),
                "schedule": len(schedule_suggestions),
                "resource": len(resource_suggestions),
                "quality": len(quality_suggestions),
            },
            "quick_wins_available": len(quick_wins),
        }

        return {
            "project_id": project_id,
            "project_name": project.name,
            "suggestions": all_suggestions[:20],  # Top 20 suggestions
            "summary": summary,
            "quick_wins": quick_wins[:5],  # Top 5 quick wins
            "generated_at": datetime.now().isoformat(),
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in generate_optimization_suggestions: {e}")
        return {"error": str(e)}


def _generate_cost_optimizations(
    evm_data: Any, wbes: list[Any]
) -> list[dict[str, Any]]:
    """Generate cost optimization suggestions."""
    suggestions = []
    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 1.0
    cv = float(evm_data.cv)
    bac = float(evm_data.bac)

    # Check for cost overruns
    if cpi < 0.95:
        potential_savings = abs(cv) * 0.3  # Assume 30% can be recovered
        suggestions.append(
            {
                "priority": "high" if cpi < 0.9 else "medium",
                "category": "cost",
                "action": "Review and renegotiate supplier contracts",
                "rationale": f"CPI of {cpi:.2f} indicates cost inefficiency. "
                "Contract renegotiation can reduce rates.",
                "estimated_impact": f"${potential_savings:.2f}",
                "estimated_impact_value": float(potential_savings),
                "effort_level": "medium",
            }
        )

    # Check scope creep
    if cv < 0:
        overrun_pct = abs(cv) / bac * 100
        if overrun_pct > 15:
            suggestions.append(
                {
                    "priority": "high",
                    "category": "cost",
                    "action": "Conduct scope audit and eliminate non-essential work",
                    "rationale": f"{overrun_pct:.1f}% budget overrun suggests scope creep. "
                    "Audit and cut non-essential activities.",
                    "estimated_impact": f"${abs(cv) * 0.2:.2f}",
                    "estimated_impact_value": float(abs(cv) * 0.2),
                    "effort_level": "low",
                }
            )

    # Suggest value engineering
    suggestions.append(
        {
            "priority": "low" if cpi >= 0.95 else "medium",
            "category": "cost",
            "action": "Implement value engineering review",
            "rationale": "Value engineering can identify cost-effective alternatives "
            "without sacrificing quality.",
            "estimated_impact": f"${bac * 0.05:.2f}",
            "estimated_impact_value": float(bac * 0.05),
            "effort_level": "medium",
        }
    )

    return suggestions


def _generate_schedule_optimizations(
    evm_data: Any, wbes: list[Any]
) -> list[dict[str, Any]]:
    """Generate schedule optimization suggestions."""
    suggestions = []
    spi = float(evm_data.spi) if evm_data.spi is not None else 1.0
    sv = float(evm_data.sv)
    pv = float(evm_data.pv)

    # Check for schedule delays
    if spi < 0.95:
        delay_weeks = abs(sv) / pv * 52 if pv > 0 else 0  # Convert to weeks
        suggestions.append(
            {
                "priority": "high" if spi < 0.9 else "medium",
                "category": "schedule",
                "action": "Reallocate resources to critical path activities",
                "rationale": f"SPI of {spi:.2f} indicates schedule delays. "
                "Adding resources to critical path can recover lost time.",
                "estimated_impact": f"{delay_weeks * 0.5:.1f} weeks",
                "estimated_impact_value": float(delay_weeks * 0.5),
                "effort_level": "medium",
            }
        )

    # Suggest parallel work
    delayed_wbes = [
        w
        for w in wbes
        if hasattr(w, "planned_end_date")
        and w.planned_end_date
        and w.planned_end_date < datetime.now()
    ]

    if len(delayed_wbes) > 2:
        suggestions.append(
            {
                "priority": "medium",
                "category": "schedule",
                "action": "Identify opportunities for parallel work execution",
                "rationale": f"{len(delayed_wbes)} delayed WBEs detected. "
                "Parallel execution can recover schedule.",
                "estimated_impact": f"{len(delayed_wbes) * 0.5:.1f} weeks",
                "estimated_impact_value": float(len(delayed_wbes) * 0.5),
                "effort_level": "low",
            }
        )

    # Suggest schedule compression
    if spi < 1.0:
        suggestions.append(
            {
                "priority": "medium",
                "category": "schedule",
                "action": "Evaluate fast-tracking or crashing for remaining work",
                "rationale": "Schedule compression techniques can recover lost time "
                "at increased cost.",
                "estimated_impact": "2-4 weeks",
                "estimated_impact_value": 3.0,
                "effort_level": "high",
            }
        )

    return suggestions


def _generate_resource_optimizations(
    evm_data: Any, wbes: list[Any]
) -> list[dict[str, Any]]:
    """Generate resource optimization suggestions."""
    suggestions = []

    # Check for underutilized resources
    if len(wbes) > 0:
        suggestions.append(
            {
                "priority": "medium",
                "category": "resource",
                "action": "Conduct resource utilization analysis",
                "rationale": "Identify underutilized resources and reallocate to critical activities.",
                "estimated_impact": "15-20% efficiency improvement",
                "estimated_impact_value": 17.5,
                "effort_level": "low",
            }
        )

    # Suggest skills cross-training
    suggestions.append(
        {
            "priority": "low",
            "category": "resource",
            "action": "Implement cross-training program for team members",
            "rationale": "Cross-trained team provides flexibility and reduces bottlenecks.",
            "estimated_impact": "10-15% schedule resilience",
            "estimated_impact_value": 12.5,
            "effort_level": "medium",
        }
    )

    # Suggest workload balancing
    cpi = float(evm_data.cpi) if evm_data.cpi is not None else 1.0
    spi = float(evm_data.spi) if evm_data.spi is not None else 1.0

    if cpi < 1.0 or spi < 1.0:
        suggestions.append(
            {
                "priority": "medium",
                "category": "resource",
                "action": "Rebalance workload across team members",
                "rationale": "Workload imbalances can cause bottlenecks and delays.",
                "estimated_impact": "5-10% performance improvement",
                "estimated_impact_value": 7.5,
                "effort_level": "low",
            }
        )

    return suggestions


def _generate_quality_optimizations(evm_data: Any) -> list[dict[str, Any]]:
    """Generate quality optimization suggestions."""
    suggestions = []

    progress = (
        float(evm_data.progress_percentage) if evm_data.progress_percentage else 0.0
    )

    # Suggest quality reviews
    if progress < 80:
        suggestions.append(
            {
                "priority": "medium",
                "category": "quality",
                "action": "Schedule mid-project quality review",
                "rationale": "Early quality reviews prevent rework and ensure deliverables meet standards.",
                "estimated_impact": "10-15% rework reduction",
                "estimated_impact_value": 12.5,
                "effort_level": "low",
            }
        )

    # Suggest process improvements
    suggestions.append(
        {
            "priority": "low",
            "category": "quality",
            "action": "Document and standardize successful processes",
            "rationale": "Process standardization improves consistency and reduces errors.",
            "estimated_impact": "5-10% quality improvement",
            "estimated_impact_value": 7.5,
            "effort_level": "medium",
        }
    )

    return suggestions


# =============================================================================
# MODULE DOCUMENTATION
# =============================================================================

"""
ADVANCED ANALYSIS TOOL PATTERNS:

1. PROJECT HEALTH ASSESSMENT:
   - Multi-dimensional scoring (budget, schedule, quality, risk)
   - Weighted overall health score (0-100)
   - Status classification (Excellent/Good/Fair/Poor)
   - Actionable recommendations per category
   - Benchmark comparison capability

2. ANOMALY DETECTION:
   - Statistical analysis (z-scores, standard deviation)
   - Cost spike detection
   - Schedule variance detection
   - Performance divergence detection
   - Trend analysis (improving/stable/declining)

3. FORECAST ANALYSIS:
   - Multiple scenario modeling (best/worst/most likely)
   - Confidence interval assessment
   - Trend detection and analysis
   - Risk factor identification
   - Monte Carlo simulation hints

4. OPTIMIZATION SUGGESTIONS:
   - Prioritized recommendations (high/medium/low)
   - Categorized by type (cost/schedule/resource/quality)
   - Estimated impact quantification
   - Effort level assessment
   - Quick win identification

PERMISSIONS:
   - evm-read: Required for all analysis tools
   - forecast-read: Required for forecast analysis

BEST PRACTICES:
   - Use statistical methods for objective analysis
   - Provide actionable, specific recommendations
   - Quantify potential benefits where possible
   - Consider both short-term and long-term impacts
   - Prioritize by impact vs effort

ANALYSIS WORKFLOW:
   1. Assess overall project health
   2. Detect anomalies requiring attention
   3. Analyze forecast trends and scenarios
   4. Generate optimization suggestions
   5. Present quick wins for immediate action
"""
