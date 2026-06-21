"""Main application entry point."""

import asyncio
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
    agent_schedules,
    ai_chat,
    ai_config,
    ai_upload,
    auth,
    change_order_config,
    change_orders,
    control_accounts,
    cost_element_types,
    cost_elements,
    cost_event_types,
    cost_events,
    cost_registration_attachments,
    cost_registrations,
    dashboard,
    dashboard_layouts,
    documents,
    evm,
    forecasts,
    gantt,
    mcp_servers,
    notifications,
    organizational_units,
    progress_entries,
    project_budget_settings,
    projects,
    rbac_admin,
    schedule_baselines,
    schedule_dependencies,
    search,
    system_admin,
    user_role_assignments,
    users,
    wbs_elements,
    work_packages,
)
from app.core.branching.exceptions import BranchLockedException
from app.core.config import settings
from app.core.exceptions.filtering import FilterError
from app.core.logging import setup_logging

# Suppress all PendingDeprecationWarnings from LangGraph (safe to ignore as they come from dependencies)

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

    # Seed users and RBAC FIRST (idempotent, safe on every startup).
    # Must run before the RBAC permissions cache refresh below so the cache
    # never snapshots a pre-seed role state (which would serve stale
    # permissions for up to the cache TTL).
    from app.db.session import async_session_maker

    try:
        _t0 = _time.time()
        from app.db.seed_users_rbac import seed_users_and_rbac

        async with async_session_maker() as session:
            await seed_users_and_rbac(session)
            await session.commit()
        logger.info("[STARTUP] users_rbac_seed OK %.0fms", (_time.time() - _t0) * 1000)
    except Exception:
        logger.warning("[STARTUP] users_rbac_seed FAILED", exc_info=True)

    # Initialize RBAC permissions cache (runs AFTER seeding so it reflects
    # the fully-seeded role/permission state).
    _t0 = _time.time()
    async with async_session_maker() as session:
        from app.core.config import settings as app_settings

        if app_settings.RBAC_PROVIDER == "database":
            from app.core.rbac_unified import (
                get_unified_rbac_service,
                rbac_session,
            )

            async with rbac_session(session):
                unified_svc = get_unified_rbac_service()
                await unified_svc.refresh_permissions_cache()

    logger.info("[STARTUP] rbac_init OK %.0fms", (_time.time() - _t0) * 1000)

    # Configure the unified notification dispatcher + channels.
    from app.core.notifications import (
        notification_dispatcher,
        system_emitter,
    )
    from app.core.notifications.channels.telegram import (
        TelegramChannel,
        TelegramUpdatePoller,
        parse_start_command,
    )
    from app.core.notifications.registry import ChannelKind

    _telegram_poller: TelegramUpdatePoller | None = None
    _scheduler_task: asyncio.Task[None] | None = None
    _scheduler_stop: asyncio.Event | None = None
    if settings.TELEGRAM_ENABLED and settings.TELEGRAM_BOT_TOKEN:
        notification_dispatcher.configure(
            {
                ChannelKind.TELEGRAM: TelegramChannel(
                    settings.TELEGRAM_BOT_TOKEN,
                    settings.TELEGRAM_CHAT_ID,
                    settings.TELEGRAM_BOT_USERNAME,
                )
            }
        )
        logger.info("[STARTUP] notifications_telegram_channel OK")

        # Dev fallback: long-poll getUpdates instead of the webhook.
        if settings.TELEGRAM_USE_POLLING:
            from typing import Any

            from app.services.telegram_link_service import TelegramLinkService

            async def _on_telegram_update(update: dict[str, Any]) -> None:
                parsed = parse_start_command(update)
                if parsed is None:
                    return
                token, chat_id, tg_user_id = parsed
                async with async_session_maker() as session:
                    await TelegramLinkService(session).verify_by_token(
                        token, chat_id, tg_user_id
                    )
                    await session.commit()

            _telegram_poller = TelegramUpdatePoller(
                settings.TELEGRAM_BOT_TOKEN, _on_telegram_update
            )
            await _telegram_poller.start()
            logger.info("[STARTUP] notifications_telegram_poller OK")

    # Notify admins of system startup via the unified emitter.
    await system_emitter.emit(
        "system.startup",
        title="Backcast started",
        message="Backcast server started successfully.",
    )

    # Initialize RustFS/S3 bucket (non-critical, graceful degradation)
    try:
        _t0 = _time.time()
        from app.services.storage_service import StorageService

        storage = StorageService()
        await storage.ensure_bucket_exists()
        logger.info("[STARTUP] storage_init OK %.0fms", (_time.time() - _t0) * 1000)
    except Exception:
        logger.warning("[STARTUP] storage_init FAILED", exc_info=True)

    # Initialize MCP client manager (non-critical, graceful degradation)
    try:
        _t0 = _time.time()
        from app.ai.mcp.client_manager import MCPClientManager

        async with async_session_maker() as session:
            mcp_mgr = MCPClientManager()
            await mcp_mgr.initialize(session)
        logger.info("[STARTUP] mcp_init OK %.0fms", (_time.time() - _t0) * 1000)
    except Exception:
        logger.warning("[STARTUP] mcp_init FAILED", exc_info=True)

    # Start the in-process agent scheduler (lifespan task). Same process as the
    # API, so scheduled runs launch where the in-memory ExecutionLifecycle /
    # event-bus live. Non-critical: a failure here never blocks startup.
    try:
        from app.scheduler.main import run_scheduler_loop

        _scheduler_stop = asyncio.Event()
        _scheduler_task = asyncio.create_task(
            run_scheduler_loop(_scheduler_stop),
            name="agent-scheduler",
        )
        logger.info("[STARTUP] agent_scheduler OK")
    except Exception:
        logger.warning("[STARTUP] agent_scheduler FAILED", exc_info=True)

    logger.info("[STARTUP] COMPLETE %.0fms", (_time.time() - _startup_start) * 1000)

    yield

    # Shutdown: clean up resources
    if _scheduler_task is not None and _scheduler_stop is not None:
        _scheduler_stop.set()
        try:
            await asyncio.wait_for(_scheduler_task, timeout=10)
        except (TimeoutError, asyncio.CancelledError):
            _scheduler_task.cancel()
        logger.info("[SHUTDOWN] agent_scheduler OK")

    if _telegram_poller is not None:
        try:
            await _telegram_poller.stop()
            logger.info("[SHUTDOWN] notifications_telegram_poller OK")
        except Exception:
            logger.warning(
                "[SHUTDOWN] notifications_telegram_poller FAILED", exc_info=True
            )

    try:
        await notification_dispatcher.shutdown()
    except Exception:
        logger.warning("[SHUTDOWN] notifications_dispatcher FAILED", exc_info=True)

    # Shutdown MCP client manager
    try:
        from app.ai.mcp.client_manager import MCPClientManager

        mcp_mgr = MCPClientManager()
        await mcp_mgr.shutdown()
    except Exception:
        logger.warning("[SHUTDOWN] mcp_shutdown FAILED", exc_info=True)


async def _cleanup_orphaned_executions() -> None:
    """Mark running/pending executions as errored after a server restart.

    When the server restarts, in-memory event buses are destroyed but the
    database may still contain executions with active statuses.  Sessions
    referencing these via ``active_execution_id`` will fail on reconnect.
    This handler reconciles that state on every startup.
    """
    from sqlalchemy import select, update

    from app.ai.event_types import ExecutionStatus
    from app.db.session import async_session_maker
    from app.models.domain.ai import AIAgentExecution, AIConversationSession

    orphaned_statuses = [
        s.value
        for s in (
            ExecutionStatus.RUNNING,
            ExecutionStatus.PENDING,
            ExecutionStatus.AWAITING_APPROVAL,
        )
    ]

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
                status=ExecutionStatus.ERROR,
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
# Note: When allow_credentials=True, origins cannot be wildcard ("*")
# Specific origins must be listed in BACKEND_CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,  # Required for cookie-based authentication
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

    # Check for transaction errors specifically
    from sqlalchemy.exc import SQLAlchemyError

    from app.core.db_utils import is_transaction_aborted

    if isinstance(exc, SQLAlchemyError) and is_transaction_aborted(exc):
        logger.error(
            "Transaction error detected on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "A database transaction error occurred. Please try again.",
                "error_type": "transaction_error",
            },
        )

    from app.core.notifications import system_emitter

    system_emitter.emit_fire_and_forget(
        "system.unhandled_exception",
        title="Unhandled exception",
        message=f"Unhandled {type(exc).__name__}: {str(exc)[:200]}",
        payload={
            "path": str(request.url.path),
            "method": request.method,
        },
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
    organizational_units.router,
    prefix=f"{settings.API_V1_STR}/organizational-units",
    tags=["Organizational Units"],
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
    project_budget_settings.router,
    prefix=f"{settings.API_V1_STR}/projects",
    tags=["Project Budget Settings"],
)
app.include_router(
    wbs_elements.router,
    prefix=f"{settings.API_V1_STR}/wbs-elements",
    tags=["WBS Elements"],
)
app.include_router(
    control_accounts.router,
    prefix=f"{settings.API_V1_STR}/control-accounts",
    tags=["Control Accounts"],
)
app.include_router(
    cost_element_types.router,
    prefix=f"{settings.API_V1_STR}/cost-element-types",
    tags=["Cost Element Types"],
)
app.include_router(
    cost_event_types.router,
    prefix=f"{settings.API_V1_STR}/cost-event-types",
    tags=["Cost Event Types"],
)
app.include_router(
    cost_elements.router,
    prefix=f"{settings.API_V1_STR}/cost-elements",
    tags=["Cost Elements"],
)
app.include_router(
    cost_events.router,
    prefix=f"{settings.API_V1_STR}/cost-events",
    tags=["Cost Events"],
)
app.include_router(
    cost_registrations.router,
    prefix=f"{settings.API_V1_STR}/cost-registrations",
    tags=["Cost Registrations"],
)
app.include_router(
    cost_registration_attachments.router,
    prefix=f"{settings.API_V1_STR}/cost-registrations",
    tags=["Cost Registration Attachments"],
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
    schedule_dependencies.router,
    prefix=f"{settings.API_V1_STR}/schedule-dependencies",
    tags=["Schedule Dependencies"],
)
app.include_router(
    progress_entries.router,
    prefix=f"{settings.API_V1_STR}/progress-entries",
    tags=["Progress Entries"],
)
app.include_router(
    work_packages.router,
    prefix=f"{settings.API_V1_STR}/work-packages",
    tags=["Work Packages (PMI)"],
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
    agent_schedules.router,
    prefix=settings.API_V1_STR,
    tags=["Agent Schedules"],
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
app.include_router(
    mcp_servers.router,
    prefix=settings.API_V1_STR,
    tags=["MCP Servers"],
)
app.include_router(
    change_order_config.router,
    prefix=f"{settings.API_V1_STR}/change-order-config",
    tags=["Change Order Config"],
)
app.include_router(
    documents.router,
    prefix=settings.API_V1_STR,
    tags=["Documents"],
)
app.include_router(
    notifications.router,
    prefix=f"{settings.API_V1_STR}/notifications",
    tags=["Notifications"],
)
app.include_router(
    user_role_assignments.router,
    prefix=f"{settings.API_V1_STR}/role-assignments",
    tags=["Role Assignments"],
)
app.include_router(
    system_admin.router,
    prefix=f"{settings.API_V1_STR}/admin/system",
    tags=["System Admin"],
)

# Add WebSocket route directly to app (bypasses router for better CORS handling)
# The WebSocket endpoint handles its own authentication via query parameter
# This is already registered via the router, so we don't need to add it again
