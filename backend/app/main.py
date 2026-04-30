"""Main application entry point."""

import logging
import time as _time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Include routers
from app.api.routes import (
    ai_chat,
    ai_config,
    ai_upload,
    auth,
    change_orders,
    cost_element_types,
    cost_elements,
    cost_registrations,
    dashboard,
    dashboard_layouts,
    departments,
    evm,
    forecasts,
    gantt,
    progress_entries,
    project_budget_settings,
    project_members,
    projects,
    quality_events,
    rbac_admin,
    schedule_baselines,
    search,
    users,
    wbes,
)
from app.core.branching.exceptions import BranchLockedException
from app.core.config import settings
from app.core.exceptions.filtering import FilterError
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

# Import models to ensure they are registered with SQLAlchemy
# (user_preference removed - now embedded in user table as JSON)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _startup_start = _time.time()
    logger.info("[STARTUP] BEGIN")

    # Configure logging on startup
    setup_logging()

    # Clean up orphaned agent executions (non-critical)
    try:
        _t0 = _time.time()
        await _cleanup_orphaned_executions()
        logger.info("[STARTUP] orphan_cleanup OK %.0fms", (_time.time() - _t0) * 1000)
    except Exception:
        logger.warning("[STARTUP] orphan_cleanup FAILED", exc_info=True)

    # Seed dashboard template layouts (non-critical, idempotent)
    try:
        _t0 = _time.time()
        from app.services.dashboard_layout_service import seed_dashboard_templates

        await seed_dashboard_templates()
        logger.info(
            "[STARTUP] dashboard_templates OK %.0fms", (_time.time() - _t0) * 1000
        )
    except Exception:
        logger.warning("[STARTUP] dashboard_templates FAILED", exc_info=True)

    # Initialize RBAC (critical)
    _t0 = _time.time()
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        from app.core.config import settings as app_settings

        if app_settings.RBAC_PROVIDER == "database":
            from app.db.seeder import DataSeeder

            seeder = DataSeeder()
            await seeder.seed_rbac_roles(session)
            await session.commit()

            from app.core.rbac import get_rbac_service, set_rbac_session
            from app.core.rbac_database import DatabaseRBACService

            set_rbac_session(session)
            rbac_svc = get_rbac_service()
            if isinstance(rbac_svc, DatabaseRBACService):
                await rbac_svc.refresh_cache()
            set_rbac_session(None)

    logger.info("[STARTUP] rbac_init OK %.0fms", (_time.time() - _t0) * 1000)

    # Notify admins of system startup
    from app.core.notifications import notifier
    from app.core.notifications._types import NotificationEvent, NotificationPayload

    await notifier.send(
        NotificationPayload(
            event=NotificationEvent.SYSTEM_STARTUP,
            message="Backcast server started successfully.",
        )
    )

    logger.info("[STARTUP] COMPLETE %.0fms", (_time.time() - _startup_start) * 1000)

    yield

    # Shutdown: clean up resources
    await notifier.shutdown()


async def _cleanup_orphaned_executions() -> None:
    """Mark running/pending executions as errored after a server restart.

    When the server restarts, in-memory event buses are destroyed but the
    database may still contain executions with active statuses.  Sessions
    referencing these via ``active_execution_id`` will fail on reconnect.
    This handler reconciles that state on every startup.
    """
    from sqlalchemy import select, update

    from app.db.session import async_session_maker
    from app.models.domain.ai import AIAgentExecution, AIConversationSession

    orphaned_statuses = ("running", "pending", "awaiting_approval")

    async with async_session_maker() as db:
        # Find orphaned execution ids
        result = await db.execute(
            select(AIAgentExecution.id).where(
                AIAgentExecution.status.in_(orphaned_statuses)
            )
        )
        orphaned_ids = [row[0] for row in result.all()]

        if not orphaned_ids:
            return

        now = datetime.now(UTC)

        # Mark orphaned executions as errored
        await db.execute(
            update(AIAgentExecution)
            .where(AIAgentExecution.id.in_(orphaned_ids))
            .values(
                status="error",
                error_message="Server restarted during execution",
                completed_at=now,
            )
        )

        # Clear active_execution_id on sessions referencing these executions
        await db.execute(
            update(AIConversationSession)
            .where(AIConversationSession.active_execution_id.in_(orphaned_ids))
            .values(active_execution_id=None)
        )

        await db.commit()
        logger.info(
            "Cleaned up %d orphaned agent execution(s) on startup",
            len(orphaned_ids),
        )


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.BACKEND_CORS_METHODS,
    allow_headers=settings.BACKEND_CORS_HEADERS,
    expose_headers=["*"],
)


# Exception Handlers


@app.exception_handler(FilterError)
async def filter_exception_handler(request: Request, exc: FilterError) -> JSONResponse:
    """Handle filter parsing errors by returning 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(BranchLockedException)
async def branch_locked_exception_handler(
    request: Request, exc: BranchLockedException
) -> JSONResponse:
    """Handle branch locked exceptions by returning 403 Forbidden."""
    return JSONResponse(
        status_code=403,
        content={
            "detail": str(exc),
            "branch": exc.branch,
            "entity_type": exc.entity_type,
            "entity_id": exc.entity_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed information."""
    logger.error("Validation error on %s: %s", request.url, exc.errors())

    errors = exc.errors()
    formatted_errors = []
    for error in errors:
        formatted_errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": formatted_errors,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)

    from app.core.notifications import notifier
    from app.core.notifications._types import NotificationEvent, NotificationPayload

    notifier.send_fire_and_forget(
        NotificationPayload(
            event=NotificationEvent.UNHANDLED_EXCEPTION,
            message=f"Unhandled {type(exc).__name__}: {str(exc)[:200]}",
            details={
                "path": str(request.url.path),
                "method": request.method,
            },
        )
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Backcast API"}


app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(
    departments.router,
    prefix=f"{settings.API_V1_STR}/departments",
    tags=["Departments"],
)
app.include_router(
    projects.router,
    prefix=f"{settings.API_V1_STR}/projects",
    tags=["Projects"],
)
app.include_router(
    gantt.router,
    prefix=f"{settings.API_V1_STR}/projects",
    tags=["Gantt"],
)
app.include_router(
    project_members.router,
    prefix=settings.API_V1_STR,
    tags=["Project Members"],
)
app.include_router(
    project_budget_settings.router,
    prefix=f"{settings.API_V1_STR}/projects",
    tags=["Project Budget Settings"],
)
app.include_router(
    wbes.router,
    prefix=f"{settings.API_V1_STR}/wbes",
    tags=["WBEs"],
)
app.include_router(
    cost_element_types.router,
    prefix=f"{settings.API_V1_STR}/cost-element-types",
    tags=["Cost Element Types"],
)
app.include_router(
    cost_elements.router,
    prefix=f"{settings.API_V1_STR}/cost-elements",
    tags=["Cost Elements"],
)
app.include_router(
    cost_registrations.router,
    prefix=f"{settings.API_V1_STR}/cost-registrations",
    tags=["Cost Registrations"],
)
app.include_router(
    change_orders.router,
    prefix=f"{settings.API_V1_STR}/change-orders",
    tags=["Change Orders"],
)
app.include_router(
    forecasts.router,
    prefix=f"{settings.API_V1_STR}/forecasts",
    tags=["Forecasts"],
)
app.include_router(
    schedule_baselines.router,
    prefix=f"{settings.API_V1_STR}/schedule-baselines",
    tags=["Schedule Baselines"],
)
app.include_router(
    progress_entries.router,
    prefix=f"{settings.API_V1_STR}/progress-entries",
    tags=["Progress Entries"],
)
app.include_router(
    quality_events.router,
    prefix=f"{settings.API_V1_STR}/quality-events",
    tags=["Quality Events"],
)
app.include_router(
    evm.router,
    prefix=f"{settings.API_V1_STR}/evm",
    tags=["EVM"],
)
app.include_router(
    ai_config.router,
    prefix=settings.API_V1_STR,
    tags=["AI Configuration"],
)
app.include_router(
    ai_chat.router,
    prefix=settings.API_V1_STR,
    tags=["AI Chat"],
)
app.include_router(
    ai_upload.router,
    prefix=settings.API_V1_STR,
    tags=["AI Upload"],
)
app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_STR}/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    dashboard_layouts.router,
    prefix=f"{settings.API_V1_STR}/dashboard-layouts",
    tags=["Dashboard Layouts"],
)
app.include_router(
    rbac_admin.router,
    prefix=f"{settings.API_V1_STR}/admin/rbac",
    tags=["Admin RBAC"],
)
app.include_router(
    search.router,
    prefix=f"{settings.API_V1_STR}/search",
    tags=["Search"],
)

# Add WebSocket route directly to app (bypasses router for better CORS handling)
# The WebSocket endpoint handles its own authentication via query parameter
# This is already registered via the router, so we don't need to add it again
