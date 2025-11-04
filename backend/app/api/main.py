from fastapi import APIRouter

from app.api.routes import (
    budget_summary,
    budget_timeline,
    cost_element_schedules,
    cost_element_types,
    cost_elements,
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
api_router.include_router(budget_summary.router)
api_router.include_router(budget_timeline.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
