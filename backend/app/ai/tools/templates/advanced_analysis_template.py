"""Advanced analysis tool template for project forecasting and anomaly detection.

Provides a single comprehensive tool that combines forecasting with scenario modeling,
anomaly detection, and optimization suggestions. Replaces the previous 4 granular tools
that all called the same EVMService methods and just reformatted output differently.

Usage:
    1. Import EVMService method via @ai_tool decorator
    2. Use ToolContext for dependency injection and temporal context
    3. Return results in AI-friendly format
"""

import logging
from datetime import UTC, datetime
from statistics import mean, stdev
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.core.versioning.enums import BranchMode

logger = logging.getLogger(__name__)


@ai_tool(
    name="get_project_forecast",
    description="Get forecast with scenarios, anomalies, and optimization suggestions. "
    "Returns EAC/ETC/VAC forecast with optimistic/likely/pessimistic scenarios, "
    "anomaly detection for unusual CPI/SPI patterns, and actionable suggestions. "
    "Set include_suggestions=false to skip optimization suggestions. "
    "Temporal context (branch, as_of date) is enforced by the system.",
    permissions=["forecast-read"],
    category="analysis",
    risk_level=RiskLevel.LOW,
)
async def get_project_forecast(
    project_id: str,
    include_suggestions: bool = True,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get comprehensive forecast analysis with scenarios, anomalies, and suggestions.

    Context: Provides database session and EVM service for forecast analysis.

    Args:
        project_id: UUID of the project to forecast
        include_suggestions: If true (default), include optimization suggestions
        context: Injected tool execution context

    Returns:
        Dictionary with forecast data:
        - forecast: EAC, ETC, VAC, BAC, AC, trend direction, confidence level
        - scenarios: optimistic, likely, pessimistic EAC estimates
        - anomalies: detected unusual CPI/SPI patterns
        - suggestions: actionable optimization suggestions (if include_suggestions=true)

    Raises:
        ValueError: If project_id is invalid
    """
    try:
        from app.models.schemas.evm import EntityType, EVMTimeSeriesGranularity
        from app.services.evm_service import EVMService

        service = EVMService(context.session)
        as_of = context.as_of or datetime.now(UTC)
        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGED
            if (context.branch_mode or "merged") == "merged"
            else BranchMode.ISOLATED
        )

        evm_data = await service.calculate_evm_metrics_batch(
            entity_type=EntityType.PROJECT,
            entity_ids=[UUID(project_id)],
            control_date=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        cpi = float(evm_data.cpi) if evm_data.cpi is not None else 1.0
        spi = float(evm_data.spi) if evm_data.spi is not None else 1.0
        bac = float(evm_data.bac)
        ac = float(evm_data.ac)
        ev = float(evm_data.ev)
        eac = float(evm_data.eac) if evm_data.eac is not None else 0.0
        etc = float(evm_data.etc) if evm_data.etc is not None else 0.0
        vac = float(evm_data.vac) if evm_data.vac is not None else 0.0

        timeseries = await service.get_evm_timeseries(
            entity_type=EntityType.PROJECT,
            entity_id=UUID(project_id),
            granularity=EVMTimeSeriesGranularity.WEEK,
            control_date=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        cpis = [float(p.cpi) for p in timeseries.points if p.cpi] if timeseries.points else []
        cpi_volatility = stdev(cpis) if len(cpis) > 1 else 0.1

        if cpis and cpis[-1] > cpi:
            trend_direction = "improving"
        elif cpis and cpis[-1] < cpi:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        confidence_score = 100 - (cpi_volatility * 100)
        if cpi < 0.8 or cpi > 1.2:
            confidence_score -= 20
        if spi < 0.8 or spi > 1.2:
            confidence_score -= 20
        confidence_score = max(0, min(100, confidence_score))

        if confidence_score >= 80:
            confidence_level = "High"
        elif confidence_score >= 60:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

        optimistic_cpi = cpi + cpi_volatility
        optimistic_eac = ac + (bac - ev) / optimistic_cpi if optimistic_cpi > 0 else bac * 1.5
        pessimistic_cpi = max(cpi - cpi_volatility, 0.7)
        pessimistic_eac = ac + (bac - ev) / pessimistic_cpi if pessimistic_cpi > 0 else bac * 2.0

        anomalies = _detect_anomalies(timeseries.points)

        result: dict[str, Any] = {
            "project_id": project_id,
            "forecast": {
                "estimate_at_completion": round(eac, 2),
                "estimate_to_complete": round(etc, 2),
                "variance_at_completion": round(vac, 2),
                "budget_at_completion": round(bac, 2),
                "actual_cost_to_date": round(ac, 2),
                "trend_direction": trend_direction,
                "confidence_level": confidence_level,
                "confidence_score": round(confidence_score, 1),
            },
            "scenarios": [
                {
                    "name": "Optimistic",
                    "estimate_at_completion": round(optimistic_eac, 2),
                    "variance_at_completion": round(bac - optimistic_eac, 2),
                    "assumption": f"CPI improves to {optimistic_cpi:.2f}",
                },
                {
                    "name": "Likely",
                    "estimate_at_completion": round(eac, 2),
                    "variance_at_completion": round(vac, 2),
                    "assumption": f"Current CPI of {cpi:.2f} continues",
                },
                {
                    "name": "Pessimistic",
                    "estimate_at_completion": round(pessimistic_eac, 2),
                    "variance_at_completion": round(bac - pessimistic_eac, 2),
                    "assumption": f"CPI degrades to {pessimistic_cpi:.2f}",
                },
            ],
            "anomalies": anomalies,
        }

        if include_suggestions:
            result["suggestions"] = _generate_suggestions(cpi, spi, vac, bac, eac, anomalies)

        if timeseries.points:
            result["analysis_period"] = {
                "start_date": timeseries.start_date.isoformat(),
                "end_date": timeseries.end_date.isoformat(),
                "weeks_analyzed": len(timeseries.points),
            }

        return result
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in get_project_forecast: {e}")
        return {"error": str(e)}


def _detect_anomalies(points: list[Any]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []

    if not points or len(points) < 3:
        return anomalies

    for i, point in enumerate(points):
        cpi_val = float(point.cpi) if point.cpi else None
        spi_val = float(point.spi) if point.spi else None

        if cpi_val is not None and (cpi_val < 0.8 or cpi_val > 1.2):
            anomalies.append(
                {
                    "type": "cpi_outlier",
                    "severity": "high" if cpi_val < 0.7 or cpi_val > 1.3 else "medium",
                    "description": f"CPI of {cpi_val:.2f} outside normal range (0.8-1.2)",
                    "period": f"Week {i + 1}",
                }
            )

        if spi_val is not None and (spi_val < 0.8 or spi_val > 1.2):
            anomalies.append(
                {
                    "type": "spi_outlier",
                    "severity": "high" if spi_val < 0.7 or spi_val > 1.3 else "medium",
                    "description": f"SPI of {spi_val:.2f} outside normal range (0.8-1.2)",
                    "period": f"Week {i + 1}",
                }
            )

        if cpi_val and spi_val:
            divergence = abs(cpi_val - spi_val)
            if divergence > 0.3:
                anomalies.append(
                    {
                        "type": "performance_divergence",
                        "severity": "high" if divergence > 0.5 else "medium",
                        "description": f"CPI ({cpi_val:.2f}) and SPI ({spi_val:.2f}) diverged by {divergence:.2f}",
                        "period": f"Week {i + 1}",
                    }
                )

    costs = [float(p.ac) for p in points]
    cost_changes = [costs[i] - costs[i - 1] for i in range(1, len(costs))]
    if cost_changes:
        mean_change = mean(cost_changes)
        try:
            std_change = stdev(cost_changes)
        except ValueError:
            std_change = 0
        if std_change > 0:
            for i, change in enumerate(cost_changes):
                z_score = abs((change - mean_change) / std_change)
                if z_score > 2.0:
                    anomalies.append(
                        {
                            "type": "cost_spike",
                            "severity": "high" if z_score > 3.0 else "medium",
                            "description": f"Cost {'increased' if change > 0 else 'decreased'} by {abs(change):.2f} (z-score: {z_score:.2f})",
                            "period": f"Week {i + 2}",
                        }
                    )

    return anomalies


def _generate_suggestions(
    cpi: float,
    spi: float,
    vac: float,
    bac: float,
    eac: float,
    anomalies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []

    if cpi < 0.9:
        suggestions.append(
            {
                "priority": "high",
                "category": "cost",
                "action": "Review cost overruns and renegotiate supplier contracts",
                "rationale": f"CPI of {cpi:.2f} indicates significant cost inefficiency",
            }
        )
    elif cpi < 0.95:
        suggestions.append(
            {
                "priority": "medium",
                "category": "cost",
                "action": "Monitor cost performance closely and identify overrun sources",
                "rationale": f"CPI of {cpi:.2f} shows early signs of cost pressure",
            }
        )
    elif cpi > 1.1:
        suggestions.append(
            {
                "priority": "low",
                "category": "cost",
                "action": "Consider accelerating work or expanding scope while under budget",
                "rationale": f"CPI of {cpi:.2f} indicates strong cost efficiency",
            }
        )

    if spi < 0.9:
        suggestions.append(
            {
                "priority": "high",
                "category": "schedule",
                "action": "Reallocate resources to critical path activities",
                "rationale": f"SPI of {spi:.2f} indicates significant schedule delays",
            }
        )
    elif spi < 0.95:
        suggestions.append(
            {
                "priority": "medium",
                "category": "schedule",
                "action": "Monitor schedule performance and consider fast-tracking",
                "rationale": f"SPI of {spi:.2f} shows early signs of schedule pressure",
            }
        )
    elif spi > 1.1:
        suggestions.append(
            {
                "priority": "low",
                "category": "schedule",
                "action": "Ahead of schedule: consider accelerating remaining work",
                "rationale": f"SPI of {spi:.2f} indicates strong schedule performance",
            }
        )

    if vac < 0:
        overrun_pct = abs(vac) / bac * 100 if bac > 0 else 0
        if overrun_pct > 20:
            suggestions.append(
                {
                    "priority": "high",
                    "category": "forecast",
                    "action": f"Projected {overrun_pct:.1f}% budget overrun: conduct scope audit",
                    "rationale": f"EAC of {eac:.2f} vs BAC of {bac:.2f}",
                }
            )
        elif overrun_pct > 10:
            suggestions.append(
                {
                    "priority": "medium",
                    "category": "forecast",
                    "action": f"Projected {overrun_pct:.1f}% budget overrun: implement mitigation",
                    "rationale": f"EAC of {eac:.2f} vs BAC of {bac:.2f}",
                }
            )

    high_anomalies = [a for a in anomalies if a["severity"] == "high"]
    if high_anomalies:
        suggestions.append(
            {
                "priority": "high",
                "category": "risk",
                "action": f"Investigate {len(high_anomalies)} high-severity anomalies detected in EVM trends",
                "rationale": "Anomalous patterns may indicate data quality issues or real project risks",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "priority": "low",
                "category": "general",
                "action": "Project performing within normal parameters. Continue current approach.",
                "rationale": f"CPI {cpi:.2f} and SPI {spi:.2f} within acceptable ranges",
            }
        )

    return suggestions
