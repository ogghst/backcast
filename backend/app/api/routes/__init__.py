# API routes package initialization

# Import all route modules for easy access
from app.api.routes import (
    auth,
    change_orders,
    cost_element_types,
    cost_elements,
    cost_registrations,
    dashboard,
    departments,
    evm,
    forecasts,
    progress_entries,
    project_members,
    projects,
    schedule_baselines,
    users,
    wbes,
)

__all__ = [
    "auth",
    "change_orders",
    "cost_element_types",
    "cost_elements",
    "cost_registrations",
    "dashboard",
    "departments",
    "evm",
    "forecasts",
    "progress_entries",
    "project_members",
    "projects",
    "schedule_baselines",
    "users",
    "wbes",
]
