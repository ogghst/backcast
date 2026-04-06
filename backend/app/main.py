"""Main application entry point."""

import logging
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
    project_members,
    projects,
    schedule_baselines,
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
    # Configure logging on startup
    setup_logging()

    # Clean up orphaned agent executions from previous server instance
    await _cleanup_orphaned_executions()

    # Seed dashboard template layouts (idempotent)
    from app.services.dashboard_layout_service import seed_dashboard_templates

    await seed_dashboard_templates()

    # Startup: could check db connection here
    yield
    # Shutdown: clean up resources


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
    logger.error(f"Validation error on {request.url}: {exc.errors()}")

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

# Add WebSocket route directly to app (bypasses router for better CORS handling)
# The WebSocket endpoint handles its own authentication via query parameter
# This is already registered via the router, so we don't need to add it again
