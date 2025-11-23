from fastapi import APIRouter

from app.api.routes import (
    ai_chat,
    app_configuration,
    baseline_logs,
    budget_summary,
    budget_timeline,
    cost_categories,
    cost_element_schedules,
    cost_element_types,
    cost_elements,
    cost_performance_report,
    cost_registrations,
    cost_summary,
    cost_timeline,
    earned_value,
    earned_value_entries,
    evm_aggregation,
    evm_indices,
    forecasts,
    login,
    planned_value,
    private,
    projects,
    users,
    utils,
    variance_analysis_report,
    variance_threshold_config,
    wbes,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(ai_chat.router)
api_router.include_router(app_configuration.router)
api_router.include_router(utils.router)
api_router.include_router(projects.router)
api_router.include_router(wbes.router)
api_router.include_router(cost_elements.router)
api_router.include_router(cost_element_schedules.router)
api_router.include_router(cost_element_types.router)
api_router.include_router(cost_categories.router)
api_router.include_router(cost_registrations.router)
api_router.include_router(cost_summary.router)
api_router.include_router(cost_timeline.router)
api_router.include_router(earned_value_entries.router)
api_router.include_router(forecasts.router)
api_router.include_router(budget_summary.router)
api_router.include_router(budget_timeline.router)
api_router.include_router(planned_value.router)
api_router.include_router(earned_value.router)
api_router.include_router(evm_indices.router)
api_router.include_router(evm_aggregation.router)
api_router.include_router(baseline_logs.router)
api_router.include_router(cost_performance_report.router)
api_router.include_router(variance_analysis_report.router)
api_router.include_router(variance_threshold_config.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
