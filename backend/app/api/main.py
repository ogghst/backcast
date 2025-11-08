from fastapi import APIRouter

from app.api.routes import (
    baseline_logs,
    budget_summary,
    budget_timeline,
    cost_categories,
    cost_element_schedules,
    cost_element_types,
    cost_elements,
    cost_registrations,
    cost_summary,
    cost_timeline,
    earned_value_entries,
    login,
    private,
    projects,
    users,
    utils,
    wbes,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
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
api_router.include_router(budget_summary.router)
api_router.include_router(budget_timeline.router)
api_router.include_router(baseline_logs.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
