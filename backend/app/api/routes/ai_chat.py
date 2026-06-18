"""API routes for AI chat."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agent_service import AgentService
from app.ai.briefing import BriefingDocument
from app.ai.event_types import AgentEventType, ExecutionStatus
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.lifecycle import execution_lifecycle
from app.ai.execution.runner_manager import runner_manager
from app.ai.tools.types import ExecutionMode
from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.api.errors import build_ws_error
from app.api.websocket_utils import is_websocket_connected
from app.core.jwt_utils import validate_jwt_token
from app.db.session import get_db
from app.models.domain.ai import (
    AIAgentExecution,
    AIAssistantConfig,
    AIConversationSession,
)
from app.models.domain.user import User
from app.models.schemas.ai import (
    AgentExecutionHistoryContext,
    AgentExecutionHistoryItem,
    AgentExecutionHistoryPaginated,
    AgentExecutionPublic,
    AgentExecutionRunningCount,
    AIConversationMessagePublic,
    AIConversationSessionPaginated,
    AIConversationSessionPublic,
    ApprovalRequest,
    InvokeAgentRequest,
    WSApprovalResponseMessage,
    WSAskUserResponse,
    WSChatRequest,
    WSSubscribeMessage,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


async def forward_bus_events(
    bus: AgentEventBus,
    websocket: WebSocket,
    user_id: UUID | None = None,
) -> None:
    """Forward events from an AgentEventBus to a WebSocket connection.

    Subscribes to the bus, loops with 1-second timeout to check disconnects,
    and forwards each event as JSON. Unsubscribes on exit.
    """
    queue = bus.subscribe()
    try:
        while not bus.is_completed:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except TimeoutError:
                if not is_websocket_connected(websocket):
                    break
                continue
            if not is_websocket_connected(websocket):
                break
            payload = {**event.data, "type": event.event_type}
            try:
                await websocket.send_json(payload)
            except Exception:
                if user_id:
                    logger.warning(
                        "Failed to forward event to WebSocket for user %s", user_id
                    )
                break
            if event.event_type in (AgentEventType.COMPLETE, AgentEventType.ERROR):
                break
        else:
            # Loop exited because bus.is_completed became True.
            # Drain any remaining events from the queue (especially the complete/error event).
            logger.debug(
                "forward_bus_events: bus completed, draining queue for bus %s",
                bus.execution_id,
            )
            while not queue.empty():
                try:
                    event = queue.get_nowait()
                    if not is_websocket_connected(websocket):
                        break
                    payload = {**event.data, "type": event.event_type}
                    await websocket.send_json(payload)
                    if event.event_type in (
                        AgentEventType.COMPLETE,
                        AgentEventType.ERROR,
                    ):
                        break
                except Exception:
                    break
    finally:
        bus.unsubscribe(queue)


def _enrich_session_briefing(
    session_public: AIConversationSessionPublic,
    session: AIConversationSession,
) -> None:
    """Compile briefing markdown and specialist names from stored briefing_data."""
    if not session.briefing_data:
        return
    doc = BriefingDocument.from_state(session.briefing_data)
    session_public.briefing_markdown = doc.to_markdown()
    session_public.briefing_specialists = [sec.specialist_name for sec in doc.sections]
    session_public.briefing_data = session.briefing_data


async def _enrich_session_resume_metadata(
    session_public: AIConversationSessionPublic,
    session: AIConversationSession,
    db: AsyncSession,
) -> None:
    """Set can_resume from latest execution and plan_data.

    A session is resumable when the latest execution is stopped and plan_data
    has at least one incomplete step. The backend detects resume mode
    automatically from session state -- no step index is sent to the client.
    """
    from app.ai.plan import PlanDocument

    # Find the latest execution for this session
    stmt = (
        select(AIAgentExecution)
        .where(AIAgentExecution.session_id == str(session.id))
        .order_by(AIAgentExecution.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    latest_exec = result.scalar_one_or_none()
    if latest_exec is None or latest_exec.status != ExecutionStatus.STOPPED:
        return

    # Check plan_data for incomplete steps
    plan_data = session.plan_data
    if not plan_data or not isinstance(plan_data, dict):
        return

    plan = PlanDocument.from_state(plan_data)
    if plan.get_first_incomplete_step_index() is not None:
        session_public.can_resume = True


async def _cleanup_stale_execution(db: AsyncSession, execution_id: str) -> bool:
    """Clean up an orphaned execution left behind by a server restart.

    When the in-memory event bus is lost (server restart/crash), execution
    rows can remain stuck at ``status='running'`` with no ``completed_at``.
    This helper marks such an execution as errored and clears the session's
    ``active_execution_id`` so the client can recover gracefully.

    Returns True if a stale execution was found and cleaned up.
    """
    result = await db.execute(
        select(AIAgentExecution).where(
            AIAgentExecution.id == execution_id,
            AIAgentExecution.status == ExecutionStatus.RUNNING,
        )
    )
    execution = result.scalar_one_or_none()
    if execution is None:
        return False

    now = datetime.now(UTC)
    execution.status = ExecutionStatus.ERROR
    execution.error_message = "Server restarted during execution"
    execution.completed_at = now  # type: ignore[assignment]

    await db.execute(
        update(AIConversationSession)
        .where(AIConversationSession.active_execution_id == execution_id)
        .values(active_execution_id=None)
    )
    await db.commit()
    return True


class SessionIdHolder:
    """Mutable container for session_id to pass by reference.

    Context: When creating a new session in chat_stream(), the session_id
    needs to be communicated back to the WebSocket endpoint for approval
    handling. Since Python passes arguments by assignment, we use this
    simple container to hold the session_id and update it by reference.
    """

    def __init__(self) -> None:
        """Initialize with None session_id."""
        self.value: UUID | None = None


def get_ai_config_service(session: AsyncSession = Depends(get_db)) -> AIConfigService:
    """Get AI configuration service."""
    return AIConfigService(session)


@router.get(
    "/sessions",
    response_model=list[AIConversationSessionPublic],
    operation_id="list_ai_sessions",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def list_sessions(
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
    context_type: str | None = Query(
        None, description="Filter by context type (general, project, wbe, cost_element)"
    ),
    context_id: str | None = Query(
        None, description="Filter by specific entity ID (e.g., project UUID, WBE ID)"
    ),
) -> list[AIConversationSessionPublic]:
    """List conversation sessions for the current user.

    Includes active agent execution status for each session, allowing
    the frontend to display running indicators in the session list.

    Args:
        context_type: Optional context type filter (general, project, wbe, cost_element)
        context_id: Optional entity ID filter for scoped context
    """
    sessions = await config_service.list_sessions(
        current_user.user_id, context_type=context_type, context_id=context_id
    )
    result: list[AIConversationSessionPublic] = []

    if not sessions:
        return result

    # Collect session IDs and find active executions in a single query
    session_ids = [s.id for s in sessions]
    active_statuses = [
        s.value
        for s in (
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.AWAITING_APPROVAL,
        )
    ]
    exec_stmt = select(AIAgentExecution).where(
        AIAgentExecution.session_id.in_(session_ids),
        AIAgentExecution.status.in_(active_statuses),
    )
    exec_result = await config_service.session.execute(exec_stmt)
    active_executions: dict[str, AIAgentExecution] = {
        str(e.session_id): e for e in exec_result.scalars().all()
    }

    for s in sessions:
        session_public = AIConversationSessionPublic.model_validate(s)
        execution = active_executions.get(str(s.id))
        if execution is not None:
            session_public.active_execution = AgentExecutionPublic.model_validate(
                execution
            )
        _enrich_session_briefing(session_public, s)
        await _enrich_session_resume_metadata(session_public, s, config_service.session)
        result.append(session_public)

    return result


@router.get(
    "/sessions/paginated",
    response_model=AIConversationSessionPaginated,
    operation_id="list_ai_sessions_paginated",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def list_sessions_paginated(
    skip: int = 0,
    limit: int = 10,
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
    context_type: str | None = Query(
        None, description="Filter by context type (general, project, wbe, cost_element)"
    ),
    context_id: str | None = Query(
        None, description="Filter by specific entity ID (e.g., project UUID, WBE ID)"
    ),
) -> AIConversationSessionPaginated:
    """List chat sessions with pagination.

    Args:
        skip: Number of sessions to skip (default: 0)
        limit: Sessions per page (default: 10, max: 50)
        context_type: Optional context type filter (general, project, wbe, cost_element)
        context_id: Optional entity ID filter for scoped context
        current_user: Authenticated user (injected)
        config_service: AI config service (injected)

    Returns:
        Paginated response with sessions, has_more flag, and total_count
    """
    limit = min(limit, 50)  # Cap at 50

    sessions, has_more = await config_service.list_sessions_paginated(
        user_id=current_user.user_id,
        skip=skip,
        limit=limit,
        context_type=context_type,
        context_id=context_id,
    )

    result: list[AIConversationSessionPublic] = []

    if not sessions:
        return AIConversationSessionPaginated(
            sessions=result,
            has_more=False,
            total_count=0,
        )

    # Collect session IDs and find active executions in a single query
    session_ids = [s.id for s in sessions]
    active_statuses = [
        s.value
        for s in (
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.AWAITING_APPROVAL,
        )
    ]
    exec_stmt = select(AIAgentExecution).where(
        AIAgentExecution.session_id.in_(session_ids),
        AIAgentExecution.status.in_(active_statuses),
    )
    exec_result = await config_service.session.execute(exec_stmt)
    active_executions: dict[str, AIAgentExecution] = {
        str(e.session_id): e for e in exec_result.scalars().all()
    }

    for s in sessions:
        session_public = AIConversationSessionPublic.model_validate(s)
        execution = active_executions.get(str(s.id))
        if execution is not None:
            session_public.active_execution = AgentExecutionPublic.model_validate(
                execution
            )
        _enrich_session_briefing(session_public, s)
        await _enrich_session_resume_metadata(session_public, s, config_service.session)
        result.append(session_public)

    # Get total count
    total_count = await config_service.count_sessions(current_user.user_id)

    return AIConversationSessionPaginated(
        sessions=result,
        has_more=has_more,
        total_count=total_count,
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[AIConversationMessagePublic],
    operation_id="list_ai_session_messages",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def get_session_messages(
    session_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
) -> list[AIConversationMessagePublic]:
    """Get messages for a conversation session."""
    # Verify session belongs to user
    session = await config_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    messages = await config_service.list_messages(session_id)
    return [AIConversationMessagePublic.model_validate(m) for m in messages]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_ai_session",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def delete_session(
    session_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
) -> None:
    """Delete a conversation session."""
    # Verify session belongs to user
    session = await config_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await config_service.delete_session(session_id)


@router.post(
    "/sessions/{session_id}/invoke",
    response_model=AgentExecutionPublic,
    operation_id="invoke_agent",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def invoke_agent(
    session_id: UUID,
    body: InvokeAgentRequest,
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
    db: AsyncSession = Depends(get_db),
) -> AgentExecutionPublic:
    """Invoke an agent execution for a conversation session.

    Derives the assistant_config_id from the session's relationship.
    Starts a background agent run that can be polled via the status endpoint.
    """
    # Verify session exists and belongs to user
    stmt = (
        select(AIConversationSession)
        .where(AIConversationSession.id == session_id)
        .options(selectinload(AIConversationSession.assistant_config))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    assistant_config = session.assistant_config
    if assistant_config is None:
        raise HTTPException(
            status_code=500, detail="Session has no associated assistant config"
        )
    if not assistant_config.is_active:
        raise HTTPException(status_code=400, detail="Assistant config is not active")

    agent_service = AgentService(db)
    # Session model stores UUIDs as str (PG_UUID mapping); cast for typed service layer
    project_uuid: UUID | None = UUID(session.project_id) if session.project_id else None
    branch_uuid: UUID | None = UUID(session.branch_id) if session.branch_id else None
    execution_id = await agent_service.start_execution(
        message=body.message,
        assistant_config=assistant_config,
        session_id=session_id,
        user_id=current_user.user_id,
        project_id=project_uuid,
        branch_id=branch_uuid,
        execution_mode=body.execution_mode,
    )

    # Fetch the created execution record
    exec_stmt = select(AIAgentExecution).where(AIAgentExecution.id == execution_id)
    exec_result = await db.execute(exec_stmt)
    execution = exec_result.scalar_one()
    return AgentExecutionPublic.model_validate(execution)


@router.get(
    "/sessions/{session_id}/executions",
    response_model=list[AgentExecutionPublic],
    operation_id="list_session_executions",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def list_session_executions(
    session_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
    db: AsyncSession = Depends(get_db),
) -> list[AgentExecutionPublic]:
    """List agent executions for a conversation session."""
    # Verify session exists and belongs to user
    session = await config_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = (
        select(AIAgentExecution)
        .where(AIAgentExecution.session_id == session_id)
        .order_by(AIAgentExecution.created_at.desc())
    )
    result = await db.execute(stmt)
    executions = result.scalars().all()
    return [AgentExecutionPublic.model_validate(e) for e in executions]


@router.get(
    "/executions/{execution_id}/status",
    response_model=AgentExecutionPublic,
    operation_id="get_execution_status",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def get_execution_status(
    execution_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentExecutionPublic:
    """Get the status of an agent execution.

    Verifies ownership by checking the execution's session belongs to
    the current user.
    """
    # Fetch execution with session for ownership check
    stmt = select(AIAgentExecution).where(AIAgentExecution.id == execution_id)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Verify ownership via session
    session_stmt = select(AIConversationSession).where(
        AIConversationSession.id == execution.session_id
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if session is None or session.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    return AgentExecutionPublic.model_validate(execution)


@router.get(
    "/executions",
    response_model=AgentExecutionHistoryPaginated,
    operation_id="list_agent_executions",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def list_agent_executions(
    status: str | None = Query(
        None, description="Filter by execution status (running, completed, ...)"
    ),
    limit: int = Query(20, ge=1, description="Page size (max 50)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
) -> AgentExecutionHistoryPaginated:
    """List the current user's agent executions for the Agents History page.

    Returns executions newest-first, optionally filtered by status, joined
    with the owning conversation session (for ownership + context) and the
    assistant config (for the display name).
    """
    limit = min(limit, 50)  # Cap at 50, mirroring sessions pagination.

    rows, total, has_more = await config_service.list_executions_paginated(
        user_id=current_user.user_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    items: list[AgentExecutionHistoryItem] = []
    for row in rows:
        execution = row[0]
        session_context = row[1] or {}
        context = AgentExecutionHistoryContext(
            type=session_context.get("type"),
            name=session_context.get("name"),
            project_id=str(row[2]) if row[2] is not None else None,
            branch_id=str(row[3]) if row[3] is not None else None,
        )
        items.append(
            AgentExecutionHistoryItem(
                id=execution.id,
                name=execution.name,
                status=execution.status,
                execution_mode=execution.execution_mode,
                run_in_background=execution.run_in_background,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                session_id=execution.session_id,
                context=context,
                assistant_name=row[4],
                total_tokens=execution.total_tokens,
                tool_calls_count=execution.tool_calls_count,
            )
        )

    return AgentExecutionHistoryPaginated(items=items, total=total, has_more=has_more)


@router.get(
    "/executions/running-count",
    response_model=AgentExecutionRunningCount,
    operation_id="count_running_agent_executions",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def count_running_agent_executions(
    current_user: UserIdentity = Depends(get_current_user),
    config_service: AIConfigService = Depends(get_ai_config_service),
) -> AgentExecutionRunningCount:
    """Count the user's currently-active executions (running or awaiting approval).

    Lightweight endpoint for the Agents History menu badge.
    """
    count = await config_service.count_running_executions(current_user.user_id)
    return AgentExecutionRunningCount(count=count)


@router.post(
    "/executions/{execution_id}/stop",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="stop_agent_execution",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def stop_agent_execution(
    execution_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Stop a running agent execution (the Agents History Stop button).

    Verifies ownership by checking the execution's session belongs to the
    current user.  Returns 404 (not 403) for unknown / other-user executions
    to avoid leaking existence, mirroring :func:`get_execution_status`.
    """
    # Fetch execution by id.
    stmt = select(AIAgentExecution).where(AIAgentExecution.id == execution_id)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Verify ownership via session.
    session_stmt = select(AIConversationSession).where(
        AIConversationSession.id == execution.session_id
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if session is None or session.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    ok = AgentService.request_stop(str(execution_id))
    if not ok:
        # Unknown to the lifecycle or already terminal.
        raise HTTPException(
            status_code=404, detail="Execution not found or already terminal"
        )
    # 204 No Content — nothing to return.
    return None


@router.post(
    "/executions/{execution_id}/approve",
    operation_id="approve_execution",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def approve_execution(
    execution_id: UUID,
    body: ApprovalRequest,
    current_user: UserIdentity = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approve or reject a tool execution via REST.

    Allows approving/rejecting a pending tool execution without an active
    WebSocket connection. Looks up the InterruptNode for the execution's
    session and registers the approval response.

    Args:
        execution_id: UUID of the execution to approve.
        body: ApprovalRequest with approval_id and approved flag.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        Dict with status and approved flag.

    Raises:
        HTTPException: 404 if execution not found, 400 if approval registration fails.
    """
    # Fetch execution with session for ownership check (same pattern as get_execution_status)
    exec_stmt = select(AIAgentExecution).where(AIAgentExecution.id == execution_id)
    exec_result = await db.execute(exec_stmt)
    execution = exec_result.scalar_one_or_none()

    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Verify ownership via session
    session_stmt = select(AIConversationSession).where(
        AIConversationSession.id == execution.session_id
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if session is None or session.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Look up InterruptNode for the session via AgentService class-level dict
    agent_service = AgentService(db)
    interrupt_node = agent_service.get_interrupt_node(UUID(str(execution.session_id)))

    if interrupt_node is None:
        raise HTTPException(
            status_code=400,
            detail="No pending approval found for this execution's session",
        )

    # Register the approval response
    interrupt_node.register_approval_response(body.approval_id, body.approved)

    logger.info(
        f"REST approval registered: execution_id={execution_id}, "
        f"approval_id={body.approval_id}, approved={body.approved}"
    )

    return {"status": "ok", "approved": body.approved}


@router.websocket("/stream")
async def chat_stream(
    websocket: WebSocket,
    token: Annotated[str, Query()],
) -> None:
    """WebSocket endpoint for streaming AI chat responses.

    Authentication:
        - JWT token must be provided via query parameter: ?token=<jwt_token>
        - Token is validated BEFORE connection is accepted
        - Expired tokens receive 4008 (custom auth expiration code)

    Authorization:
        - User must have 'ai-chat' permission
        - Connection is closed with 1008 (policy violation) if unauthorized

    Lifecycle:
        1. Validate JWT token from query parameter (before accepting connection)
        2. Check RBAC permission
        3. Accept WebSocket connection
        4. Receive WSChatRequest from client
        5. Stream response via AgentService.chat_stream()
        6. Handle disconnect and errors gracefully

    WebSocket Close Codes:
        - 4008: Authentication token expired (client should refresh and NOT reconnect)
        - 1008: Policy violation (invalid token, missing user, no permission)
        - 1000: Normal closure
    """
    from app.db.session import async_session_maker

    user_id: UUID | None = None
    user: User | None = None

    # Validate token BEFORE accepting the connection to prevent reconnection loops
    # This ensures the frontend can distinguish between auth failures and connection issues

    # Step 1: Validate JWT token using centralized utility
    jwt_result = validate_jwt_token(token)
    if not jwt_result.is_valid:
        logger.warning(f"WebSocket connection rejected: {jwt_result.error_detail}")
        close_code = jwt_result.close_code if jwt_result.close_code else 1008
        await websocket.close(
            code=close_code, reason=jwt_result.error_detail or "Authentication failed"
        )
        return

    if jwt_result.subject is None:
        logger.warning("WebSocket connection rejected: missing subject in token")
        await websocket.close(code=1008, reason="Invalid token: missing subject")
        return

    subject = jwt_result.subject

    # Create database session after token validation using context manager
    # This ensures proper cleanup even with early returns
    async with async_session_maker() as db:
        # JWT subject is the user_id (UUID string)
        try:
            user_id = UUID(subject)
        except ValueError:
            logger.warning(
                "WebSocket connection rejected: invalid user_id in token subject"
            )
            await websocket.close(code=1008, reason="Invalid token subject")
            return

        from app.services.user import UserService

        user_service = UserService(db)
        user = await user_service.get_user(user_id)
        if user is None:
            logger.warning(
                f"WebSocket connection rejected: user not found for id {user_id}"
            )
            await websocket.close(code=1008, reason="User not found")
            return

        if not user.is_active:
            logger.warning(
                f"WebSocket connection rejected: user {user_id} is deactivated"
            )
            await websocket.close(code=1008, reason="User account is deactivated")
            return

        user_id = user.user_id

        # Step 2: Check RBAC permission
        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )

        set_unified_rbac_session(db)
        unified_service = get_unified_rbac_service()
        has_chat_perm = await unified_service.has_permission(
            user_id=user.user_id,
            required_permission="ai-chat",
        )
        if not has_chat_perm:
            logger.warning(
                f"WebSocket connection rejected: user {user_id} lacks ai-chat permission"
            )
            await websocket.close(
                code=1008, reason="Insufficient permissions: ai-chat required"
            )
            return

        # Step 3: Now accept the connection since authentication and authorization passed
        await websocket.accept()
        logger.info(f"WebSocket chat connection established for user {user_id}")

        # Step 4: Keep the connection alive, processing messages in a loop.
        # The loop exits when the client disconnects (WebSocketDisconnect is raised).
        config_service = AIConfigService(db)
        agent_service = AgentService(db)

        # Track current session ID for approval handling
        # Use mutable container so chat_stream() can update it when creating new sessions
        session_holder = SessionIdHolder()
        current_session_id: UUID | None = None

        # Task tracking for concurrent message handling
        tasks: set[asyncio.Task[None]] = set()
        # Agent execution tasks are tracked separately -- they must NOT be
        # cancelled on WebSocket disconnect so the agent continues running
        # and the client can re-subscribe after reconnection.
        execution_tasks: set[asyncio.Task[None]] = set()
        current_chat_task: asyncio.Task[None] | None = None

        # Thin transport: this connection attaches a single opaque presence
        # token (reused across all executions on this socket) to the
        # transport-agnostic ExecutionLifecycle.  ``observed`` is the per-
        # connection set of execution_ids we attached so disconnect can detach
        # each.  The lifecycle (NOT this endpoint) owns grace-stop, stop
        # signalling, and terminal cleanup decisions.
        observer_token: object = object()
        observed: set[str] = set()

        # Flag to stop the ping loop when connection closes
        stop_ping = asyncio.Event()

        async def ping_loop() -> None:
            """Send ping keepalive every 20 seconds to prevent proxy timeouts.

            Reverse proxies (nginx: 60s default, cloud LBs: 30-120s) can close
            idle connections during long agent execution or approval polling.
            This keepalive ensures the connection stays active.
            """
            try:
                while not stop_ping.is_set():
                    await asyncio.sleep(20)
                    if not stop_ping.is_set():
                        await websocket.send_json({"type": "ping"})
            except asyncio.CancelledError:
                # Task was cancelled - normal cleanup
                pass
            except Exception as e:
                # WebSocket closed or error - stop pinging
                logger.debug(f"Ping loop error for user {user_id}: {e}")

        async def message_handler() -> None:
            """Handle incoming WebSocket messages concurrently.

            This function runs as a background task to process messages
            without blocking approval responses. Chat messages launch
            start_execution() as background tasks and forward events from
            the AgentEventBus to the WebSocket, while approval responses
            are handled immediately.

            Both the ``subscribe`` (reconnect) and ``chat`` handlers run
            their live event forwarding as a background task in ``tasks``
            (via :func:`create_event_forwarding_task`) rather than
            ``await``ing :func:`forward_bus_events` inline.  Awaiting
            inline blocks this message loop, which delays
            ``WebSocketDisconnect`` detection on the next
            ``receive_json``; for the reconnect path that meant the
            observer token stayed attached long after the socket was
            gone, firing the disconnect grace-stop ~minutes late.
            """
            nonlocal current_chat_task, current_session_id

            def create_event_forwarding_task(
                bus: AgentEventBus,
                ws: WebSocket,
                uid: UUID,
            ) -> asyncio.Task[None]:
                """Create a background task that forwards bus events to the WebSocket."""
                return asyncio.create_task(forward_bus_events(bus, ws, user_id=uid))

            while True:
                data = await websocket.receive_json()
                message_type = data.get("type", "chat")

                # Handle pong keepalive -- client responding to our ping, no action needed
                if message_type == "pong":
                    continue

                # Handle subscribe messages for reconnection to running executions
                if message_type == "subscribe":
                    try:
                        sub_msg = WSSubscribeMessage.model_validate(data)
                        bus = runner_manager.get_bus(str(sub_msg.execution_id))
                        if bus is None:
                            # Bus lost — likely a server restart. Clean up any
                            # orphaned execution row so the client can recover.
                            await _cleanup_stale_execution(
                                db, str(sub_msg.execution_id)
                            )
                            await websocket.send_json(
                                build_ws_error(
                                    f"Execution {sub_msg.execution_id} not found or already completed",
                                    code=404,
                                ).model_dump()
                            )
                            continue

                        # Replay missed events (only those after the client's last seen sequence)
                        events = bus.replay(since_sequence=sub_msg.last_seen_sequence)
                        if events:
                            await websocket.send_json(
                                {"type": "replay_start", "count": len(events)}
                            )
                            for event in events:
                                payload = {**event.data, "type": event.event_type}
                                try:
                                    await websocket.send_json(payload)
                                except Exception:
                                    break
                            await websocket.send_json({"type": "replay_end"})

                        # If execution is already done, no need to subscribe live
                        if bus.is_completed:
                            continue

                        # Re-attach the presence token to the execution.  This
                        # cancels any pending grace-stop from a PRIOR
                        # disconnect: a reconnect within the grace window
                        # keeps the run alive.  Lifecycle ownership stays in
                        # ExecutionLifecycle; the endpoint only tracks which
                        # executions to detach on disconnect.
                        execution_lifecycle.attach(
                            str(sub_msg.execution_id), observer_token
                        )
                        observed.add(str(sub_msg.execution_id))

                        # Forward live events as a transport-scoped background
                        # task (added to ``tasks`` so the disconnect
                        # ``finally`` cancels it).  Do NOT ``await`` it inline
                        # -- that would block this message loop and delay
                        # ``WebSocketDisconnect`` detection, leaving the
                        # observer token attached long after the socket died
                        # (the disconnect grace-stop fired ~minutes late).
                        forwarding_task = create_event_forwarding_task(
                            bus, websocket, user_id
                        )
                        tasks.add(forwarding_task)
                        forwarding_task.add_done_callback(tasks.discard)
                        continue
                    except Exception as sub_err:
                        logger.error(
                            f"Error in subscribe handler for user {user_id}: {sub_err}",
                            exc_info=True,
                        )
                        try:
                            await websocket.send_json(
                                build_ws_error(
                                    f"Error subscribing to execution: {str(sub_err)}",
                                    code=500,
                                ).model_dump()
                            )
                        except Exception:
                            pass
                    continue

                # Handle approval response messages immediately (non-blocking)
                if message_type == "approval_response":
                    try:
                        approval_response = WSApprovalResponseMessage.model_validate(
                            data
                        )
                        # Use session_holder.value -- updated when session is created
                        active_session_id = session_holder.value
                        if active_session_id is None:
                            await websocket.send_json(
                                build_ws_error(
                                    "No active chat session for approval",
                                    code=400,
                                ).model_dump()
                            )
                            continue

                        # Register the approval response with the AgentService
                        # The polling loop in BackcastSecurityMiddleware will detect this
                        # and execute the tool
                        success = agent_service.register_approval_response(
                            session_id=active_session_id,
                            approval_id=approval_response.approval_id,
                            approved=approval_response.approved,
                        )
                        if not success:
                            await websocket.send_json(
                                build_ws_error(
                                    f"Failed to register approval for session {active_session_id}",
                                    code=400,
                                ).model_dump()
                            )
                            continue

                        logger.info(
                            f"Registered approval response: approval_id={approval_response.approval_id}, "
                            f"approved={approval_response.approved}"
                        )
                    except Exception as approval_err:
                        logger.error(
                            f"Error handling approval response: {approval_err}",
                            exc_info=True,
                        )
                        await websocket.send_json(
                            build_ws_error(
                                f"Error processing approval: {str(approval_err)}",
                                code=500,
                            ).model_dump()
                        )
                    continue

                # Handle ask_user_response messages -- resolve the waiting Future
                if message_type == "ask_user_response":
                    try:
                        ask_response = WSAskUserResponse.model_validate(data)
                        from app.ai.tools.ask_user import resolve_ask_user_response

                        resolve_ask_user_response(
                            ask_response.ask_id, ask_response.answer
                        )
                        logger.info(
                            "Resolved ask_user response: ask_id=%s",
                            ask_response.ask_id,
                        )
                    except Exception as ask_err:
                        logger.error(
                            "Error handling ask_user_response: %s",
                            ask_err,
                            exc_info=True,
                        )
                        try:
                            await websocket.send_json(
                                build_ws_error(
                                    f"Error processing ask_user response: {str(ask_err)}",
                                    code=500,
                                ).model_dump()
                            )
                        except Exception:
                            pass
                    continue

                # Handle chat messages -- create session, start execution, forward events
                request = WSChatRequest.model_validate(data)

                # Validate assistant config per message
                if not request.assistant_config_id:
                    await websocket.send_json(
                        build_ws_error(
                            "Assistant config is required for new sessions",
                            code=400,
                        ).model_dump()
                    )
                    continue

                assistant_config = await config_service.get_assistant_config(
                    request.assistant_config_id
                )
                if not assistant_config:
                    await websocket.send_json(
                        build_ws_error(
                            "Assistant config not found",
                            code=404,
                        ).model_dump()
                    )
                    continue

                if not assistant_config.is_active:
                    await websocket.send_json(
                        build_ws_error(
                            "Assistant config is not active",
                            code=400,
                        ).model_dump()
                    )
                    continue

                # --- Session creation (duplicated from chat_stream) ---
                effective_session_id: UUID | None = request.session_id
                if effective_session_id:
                    # Verify existing session
                    existing_session = await config_service.get_session(
                        effective_session_id
                    )
                    if not existing_session:
                        await websocket.send_json(
                            build_ws_error(
                                f"Session {effective_session_id} not found",
                                code=404,
                            ).model_dump()
                        )
                        continue
                else:
                    # Create new session with context
                    new_session = await config_service.create_session(
                        user_id=user_id,
                        assistant_config_id=assistant_config.id,
                        title=request.title,
                        project_id=request.project_id,
                        branch_id=request.branch_id,
                        context=request.context,
                    )
                    effective_session_id = new_session.id
                    session_holder.value = effective_session_id
                    current_session_id = effective_session_id
                    await db.commit()

                # Update session holder for approval handling
                session_holder.value = effective_session_id
                current_session_id = effective_session_id

                # Convert FileAttachment objects to dicts for service layer
                attachment_dicts = None
                if request.attachments:
                    attachment_dicts = [
                        {
                            "file_id": a.file_id,
                            "filename": a.filename,
                            "content_type": a.file_type,  # file_type -> content_type
                            "file_size": a.file_size,
                            "content": a.content,
                        }
                        for a in request.attachments
                    ]

                # Save user message to session (with attachments if provided)
                await config_service.add_message(
                    session_id=effective_session_id,
                    role="user",
                    content=request.message,
                    attachments=attachment_dicts,
                )
                await db.commit()

                # --- Start execution as background task ---
                exec_id = str(uuid.uuid4())
                exec_bus = runner_manager.create_bus(exec_id)

                exec_mode = request.execution_mode
                run_bg = request.run_in_background

                # Use a factory to capture loop variables by value, avoiding
                # late-binding issues (B023) where the closure would reference
                # the final loop iteration values instead of the current ones.
                def create_execution_task(
                    msg: str,
                    asst_config: AIAssistantConfig,
                    sess_id: UUID,
                    proj_id: UUID | None,
                    br_id: UUID | None,
                    as_of_dt: datetime | None,
                    br_name: str | None,
                    br_mode: Literal["merged", "isolated"] | None,
                    e_mode: ExecutionMode,
                    e_id: str,
                    e_bus: AgentEventBus,
                    run_in_background: bool,
                ) -> asyncio.Task[None]:
                    """Create a background task for start_execution with captured values."""

                    async def run_execution() -> None:
                        """Run start_execution with captured values."""
                        try:
                            await agent_service.start_execution(
                                message=msg,
                                assistant_config=asst_config,
                                session_id=sess_id,
                                user_id=user_id,
                                project_id=proj_id,
                                branch_id=br_id,
                                as_of=as_of_dt,
                                branch_name=br_name,
                                branch_mode=br_mode,
                                execution_mode=e_mode,
                                execution_id=e_id,
                                event_bus=e_bus,
                                run_in_background=run_in_background,
                            )
                        except Exception as exec_err:
                            logger.error(
                                f"Error in start_execution {e_id}: {exec_err}",
                                exc_info=True,
                            )

                    return asyncio.create_task(run_execution())

                execution_task = create_execution_task(
                    msg=request.message,
                    asst_config=assistant_config,
                    sess_id=effective_session_id,
                    proj_id=request.project_id,
                    br_id=request.branch_id,
                    as_of_dt=request.as_of,
                    br_name=request.branch_name,
                    br_mode=request.branch_mode,
                    e_mode=exec_mode,
                    e_id=exec_id,
                    e_bus=exec_bus,
                    run_in_background=run_bg,
                )
                execution_tasks.add(execution_task)
                current_chat_task = execution_task
                execution_task.add_done_callback(execution_tasks.discard)

                # Attach the presence token to the execution so the lifecycle
                # knows a transport is observing it.  Safe to call even if
                # ``start_execution`` has not reached ``register`` yet: the
                # lifecycle holds the token in ``_pending`` until register
                # pulls it in (attach-before-register race).
                execution_lifecycle.attach(exec_id, observer_token)
                observed.add(exec_id)

                # --- Send execution_started immediately ---
                try:
                    await websocket.send_json(
                        {
                            "type": "execution_started",
                            "execution_id": exec_id,
                        }
                    )
                except Exception:
                    logger.warning(
                        f"Failed to send execution_started for user {user_id}"
                    )
                    # Continue anyway -- the execution is running

                # --- Forward events from bus to WebSocket (non-blocking) ---
                # The forwarding task is transport-scoped: it is cancelled on
                # disconnect (added to ``tasks``) because it is specific to
                # THIS socket.  The agent execution task stays in
                # ``execution_tasks`` and outlives the connection -- the
                # lifecycle's grace-stop / terminate tear it down when the run
                # ends or the grace window expires with no observer.
                forwarding_task = create_event_forwarding_task(
                    exec_bus,
                    websocket,
                    user_id,
                )
                tasks.add(forwarding_task)
                forwarding_task.add_done_callback(tasks.discard)

        try:
            # Start ping loop and message handler as background tasks
            ping_task = asyncio.create_task(ping_loop())
            tasks.add(ping_task)
            ping_task.add_done_callback(tasks.discard)

            message_task = asyncio.create_task(message_handler())
            tasks.add(message_task)
            message_task.add_done_callback(tasks.discard)

            # Wait for the message handler to complete (disconnect)
            await message_task

        except WebSocketDisconnect as e:
            logger.info(
                f"WebSocket disconnected normally for user {user_id}: code={e.code}, reason={e.reason}"
            )
        except RuntimeError as e:
            # Starlette raises RuntimeError when receive_json() is called on a closed WebSocket
            # This happens when the client disconnects during streaming and the loop continues
            if "not connected" in str(e).lower():
                logger.info(
                    f"WebSocket disconnected (RuntimeError) for user {user_id}: {e}"
                )
            else:
                # Re-raise unexpected RuntimeErrors
                await db.rollback()
                raise
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {str(e)}", exc_info=True)
            await db.rollback()
            try:
                await websocket.send_json(
                    build_ws_error(
                        f"Internal server error: {str(e)}",
                        code=500,
                    ).model_dump()
                )
            except Exception:
                # WebSocket may already be closed
                pass
        finally:
            # Clear RBAC session context before db session closes
            set_unified_rbac_session(None)

            # Signal ping loop to stop
            stop_ping.set()

            # Cancel infrastructure tasks (ping, message handler) but NOT agent
            # execution tasks -- those continue running in the background so the
            # client can re-subscribe after reconnection.
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Wait for infrastructure tasks to finish cancellation (with timeout)
            if tasks:
                await asyncio.wait(
                    tasks, timeout=2.0, return_when=asyncio.ALL_COMPLETED
                )
            tasks.clear()

            # Execution tasks are intentionally NOT cancelled here.
            # They outlive the connection: the transport-agnostic
            # ExecutionLifecycle owns grace-stop (after
            # ``settings.AI_DISCONNECT_GRACE_SECONDS`` with no observer) and
            # terminal ``terminate`` (run by ``start_execution``'s finally
            # block, which cancels asks + removes the bus).

            # Clean up interrupt node for this session
            if current_session_id is not None:
                agent_service.unregister_interrupt_node(current_session_id)

            # Thin transport: detach the presence token from every execution
            # this socket observed.  The lifecycle decides whether to
            # grace-stop (last observer gone) or keep running (another
            # observer still attached / a reconnect lands within grace).  The
            # endpoint no longer owns stop / ask-cancel / cleanup decisions.
            for eid in list(observed):
                execution_lifecycle.detach(eid, observer_token)
            observed.clear()

        # Context manager automatically closes the db session
        logger.debug(f"WebSocket connection cleanup completed for user {user_id}")
