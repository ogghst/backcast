"""Analysis tool template for project EVM metrics and health assessment.

Provides a single comprehensive tool that combines EVM metrics, health scoring,
variance analysis, and KPIs into one call. Replaces the previous 8 granular tools
that all called the same EVMService.calculate_evm_metrics_batch method.

Usage:
    1. Import EVMService method via @ai_tool decorator
    2. Use ToolContext for dependency injection and temporal context
    3. Return results in AI-friendly format with temporal metadata
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.core.versioning.enums import BranchMode

logger = logging.getLogger(__name__)


@ai_tool(
    name="get_project_analysis",
    description="Get EVM metrics, health score, variance breakdown, and KPIs for a project. "
    "Returns comprehensive analysis including PV, EV, AC, CPI, SPI, forecast values, "
    "health assessment, cost/schedule status labels, and actionable recommendations. "
    "Set include_variance_breakdown=true to also get per-WBE variance data. "
    "Temporal context (branch, as_of date) is enforced by the system.",
    permissions=["evm-read"],
    category="analysis",
    risk_level=RiskLevel.LOW,
)
async def get_project_analysis(
    project_id: str,
    include_variance_breakdown: bool = False,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get comprehensive EVM analysis for a project.

    Context: Provides database session and EVM service for full project analysis.

    Args:
        project_id: UUID of the project to analyze
        include_variance_breakdown: If true, fetch per-WBE variance data
        context: Injected tool execution context

    Returns:
        Dictionary with comprehensive analysis:
        - evm: PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, BAC, progress, warning
        - health: score (0-100), status, category breakdown (budget, schedule, quality, risk)
        - variance: cost/schedule status labels and percentages
        - kpis: key metrics dict and recommendations list
        - wbe_breakdown: per-WBE variance data (only if include_variance_breakdown=true)

    Raises:
        ValueError: If project_id is invalid
    """
    log_temporal_context("get_project_analysis", context)

    try:
        from app.models.schemas.evm import EntityType
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

        cpi = float(evm_data.cpi) if evm_data.cpi is not None else 0.0
        spi = float(evm_data.spi) if evm_data.spi is not None else 0.0
        cv = float(evm_data.cv)
        sv = float(evm_data.sv)
        bac = float(evm_data.bac)
        pv = float(evm_data.pv)

        budget_score = _calculate_budget_score(cpi, cv, bac, evm_data)
        schedule_score = _calculate_schedule_score(spi, sv, pv)
        quality_score = _calculate_quality_score(evm_data)
        risk_score = _calculate_risk_score(cpi, spi, evm_data)

        weights = {"budget": 0.35, "schedule": 0.35, "quality": 0.15, "risk": 0.15}
        health_score = (
            budget_score * weights["budget"]
            + schedule_score * weights["schedule"]
            + quality_score * weights["quality"]
            + risk_score * weights["risk"]
        )

        if health_score >= 90:
            health_status = "Excellent"
        elif health_score >= 75:
            health_status = "Good"
        elif health_score >= 60:
            health_status = "Fair"
        else:
            health_status = "Poor"

        cv_pct = (cv / bac * 100) if bac > 0 else 0.0

        recommendations = [
            rec
            for rec in [
                "Monitor CPI closely" if cpi < 0.95 else None,
                "Monitor SPI closely" if spi < 0.95 else None,
                "Performance is excellent" if cpi >= 0.95 and spi >= 0.95 else None,
            ]
            if rec is not None
        ]

        result: dict[str, Any] = {
            "project_id": project_id,
            "as_of_date": as_of.isoformat(),
            "evm": {
                "planned_value": pv,
                "earned_value": float(evm_data.ev),
                "actual_cost": float(evm_data.ac),
                "cost_variance": cv,
                "schedule_variance": sv,
                "cost_performance_index": cpi,
                "schedule_performance_index": spi,
                "estimate_at_completion": float(evm_data.eac)
                if evm_data.eac is not None
                else 0.0,
                "estimate_to_complete": float(evm_data.etc)
                if evm_data.etc is not None
                else 0.0,
                "variance_at_completion": float(evm_data.vac)
                if evm_data.vac is not None
                else 0.0,
                "budget_at_completion": bac,
                "progress_percentage": float(evm_data.progress_percentage)
                if evm_data.progress_percentage is not None
                else 0.0,
                "warning": evm_data.warning,
            },
            "health": {
                "score": round(health_score, 1),
                "status": health_status,
                "categories": {
                    "budget": {"score": budget_score},
                    "schedule": {"score": schedule_score},
                    "quality": {"score": quality_score},
                    "risk": {"score": risk_score},
                },
            },
            "variance": {
                "cost_variance_percentage": round(cv_pct, 1),
                "cost_status": "Under Budget" if cv >= 0 else "Over Budget",
                "schedule_status": "Ahead of Schedule"
                if sv >= 0
                else "Behind Schedule",
                "performance_status": _get_performance_status(cpi, spi),
            },
            "kpis": {
                "cost_performance_index": round(cpi, 2),
                "schedule_performance_index": round(spi, 2),
                "cost_variance": round(cv, 2),
                "schedule_variance": round(sv, 2),
            },
            "recommendations": recommendations,
        }

        if include_variance_breakdown:
            result["wbe_breakdown"] = await _get_wbe_variance_breakdown(
                service, project_id, as_of, branch, branch_mode
            )

        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_project_analysis: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


def _calculate_budget_score(cpi: float, cv: float, bac: float, evm_data: Any) -> float:
    score = min(cpi * 100, 100)
    if cv < 0:
        variance_pct = abs(cv) / bac * 100 if bac > 0 else 0
        score -= variance_pct * 0.5
    vac = float(evm_data.vac) if evm_data.vac is not None else 0.0
    if vac < 0:
        vac_pct = abs(vac) / bac * 100 if bac > 0 else 0
        if vac_pct > 10:
            score -= vac_pct * 0.3
    return max(0, min(100, round(score, 1)))


def _calculate_schedule_score(spi: float, sv: float, pv: float) -> float:
    score = min(spi * 100, 100)
    if sv < 0:
        variance_pct = abs(sv) / pv * 100 if pv > 0 else 0
        score -= variance_pct * 0.5
    return max(0, min(100, round(score, 1)))


def _calculate_quality_score(evm_data: Any) -> float:
    progress = (
        float(evm_data.progress_percentage)
        if evm_data.progress_percentage is not None
        else 0.0
    )
    score = 85.0
    if 40 <= progress <= 80:
        score += 10
    elif progress > 80:
        score += 5
    elif progress < 0 or progress > 100:
        score -= 20
    return max(0, min(100, round(score, 1)))


def _calculate_risk_score(cpi: float, spi: float, evm_data: Any) -> float:
    score = 80.0
    if evm_data.warning:
        score -= 10
    divergence = abs(cpi - spi)
    if divergence > 0.2:
        score -= 15
    return max(0, min(100, round(score, 1)))


def _get_performance_status(cpi: float, spi: float) -> str:
    if cpi >= 0.95 and spi >= 0.95:
        return "On Track"
    elif cpi >= 0.85 and spi >= 0.85:
        return "At Risk"
    return "Off Track"


async def _get_wbe_variance_breakdown(
    service: Any,
    project_id: str,
    as_of: datetime,
    branch: str,
    branch_mode: BranchMode,
) -> list[dict[str, Any]]:
    from app.models.schemas.evm import EntityType
    from app.services.wbs_element_service import WBSElementService

    wbe_service = WBSElementService(service.db)
    try:
        wbes = await wbe_service.get_by_project(UUID(project_id), branch=branch)
    except Exception:
        return []

    if not wbes:
        return []

    wbe_ids = [wbe.wbs_element_id for wbe in wbes]
    wbe_map = {wbe.wbs_element_id: wbe for wbe in wbes}

    breakdown: list[dict[str, Any]] = []
    for wbe_id in wbe_ids:
        try:
            wbe_evm = await service.calculate_evm_metrics_batch(
                entity_type=EntityType.WBS_ELEMENT,
                entity_ids=[wbe_id],
                control_date=as_of,
                branch=branch,
                branch_mode=branch_mode,
            )
            wbe = wbe_map[wbe_id]
            breakdown.append(
                {
                    "wbs_element_id": str(wbe_id),
                    "wbs_element_name": wbe.name,
                    "cost_variance": float(wbe_evm.cv),
                    "schedule_variance": float(wbe_evm.sv),
                    "cpi": float(wbe_evm.cpi) if wbe_evm.cpi is not None else None,
                    "spi": float(wbe_evm.spi) if wbe_evm.spi is not None else None,
                }
            )
        except Exception:
            continue

    return breakdown
