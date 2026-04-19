"""API routes for AI chat."""

import asyncio
import logging
import uuid
from datetime import datetime
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
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.websockets import WebSocketState

from app.ai.agent_service import AgentService
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.runner_manager import runner_manager
from app.ai.tools.types import ExecutionMode
from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.core.config import settings
from app.core.rbac import get_rbac_service
from app.db.session import get_db
from app.models.domain.ai import (
    AIAgentExecution,
    AIAssistantConfig,
    AIConversationSession,
)
from app.models.domain.user import User
from app.models.schemas.ai import (
    AgentExecutionPublic,
    AIConversationMessagePublic,
    AIConversationSessionPaginated,
    AIConversationSessionPublic,
    ApprovalRequest,
    InvokeAgentRequest,
    WSApprovalResponseMessage,
    WSChatRequest,
    WSErrorMessage,
    WSSubscribeMessage,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


def _is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if the WebSocket is still connected.

    Args:
        websocket: WebSocket connection to check.

    Returns:
        True if the client state is not DISCONNECTED.
    """
    return websocket.client_state != WebSocketState.DISCONNECTED


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
    current_user: User = Depends(get_current_active_user),
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
    active_statuses = ("pending", "running", "awaiting_approval")
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
    current_user: User = Depends(get_current_active_user),
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
    active_statuses = ("pending", "running", "awaiting_approval")
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
        execution_mode=ExecutionMode(body.execution_mode),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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


@router.post(
    "/executions/{execution_id}/approve",
    operation_id="approve_execution",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def approve_execution(
    execution_id: UUID,
    body: ApprovalRequest,
    current_user: User = Depends(get_current_active_user),
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
        - 1008: Policy violation (invalid token, insufficient permissions)
        - 1000: Normal closure
    """
    from app.db.session import async_session_maker

    user_id: UUID | None = None
    user: User | None = None

    # Validate token BEFORE accepting the connection to prevent reconnection loops
    # This ensures the frontend can distinguish between auth failures and connection issues

    # Step 1: Validate JWT token
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject = payload.get("sub")
        if subject is None:
            logger.warning("WebSocket connection rejected: missing subject in token")
            # Close with policy violation without accepting - client will see error in onerror
            await websocket.close(code=1008, reason="Invalid token: missing subject")
            return

    except ExpiredSignatureError:
        logger.warning("WebSocket connection rejected: token signature has expired")
        # Use custom close code 4008 to signal token expiration (4000-4999 range for app-specific codes)
        # Frontend should detect this and NOT attempt reconnection, instead trigger re-authentication
        await websocket.close(code=4008, reason="Token expired")
        return

    except (JWTError, ValidationError) as e:
        logger.warning(f"WebSocket connection rejected: invalid token - {str(e)}")
        await websocket.close(code=1008, reason=f"Invalid token: {str(e)}")
        return

    # Create database session after token validation using context manager
    # This ensures proper cleanup even with early returns
    async with async_session_maker() as db:
        # Extract user_id from email subject (assuming sub is email)
        from app.services.user import UserService

        user_service = UserService(db)
        user = await user_service.get_by_email(subject)
        if user is None:
            logger.warning(
                f"WebSocket connection rejected: user not found for email {subject}"
            )
            await websocket.close(code=1008, reason="User not found")
            return

        user_id = user.user_id

        # Step 2: Check RBAC permission
        rbac_service = get_rbac_service()
        if not rbac_service.has_permission(user.role, "ai-chat"):
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
            """
            nonlocal current_chat_task, current_session_id

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
                            await websocket.send_json(
                                WSErrorMessage(
                                    type="error",
                                    message=f"Execution {sub_msg.execution_id} not found or already completed",
                                    code=404,
                                ).model_dump()
                            )
                            continue

                        # Replay missed events first
                        for event in bus.replay():
                            payload = {**event.data, "type": event.event_type}
                            try:
                                await websocket.send_json(payload)
                            except Exception:
                                break

                        # If execution is already done, no need to subscribe live
                        if bus.is_completed:
                            continue

                        # Subscribe to live events
                        sub_queue = bus.subscribe()
                        try:
                            while not bus.is_completed:
                                try:
                                    event = await asyncio.wait_for(
                                        sub_queue.get(),
                                        timeout=1.0,
                                    )
                                    if not _is_websocket_connected(websocket):
                                        break
                                    payload = {**event.data, "type": event.event_type}
                                    await websocket.send_json(payload)
                                    if event.event_type in ("complete", "error"):
                                        break
                                except TimeoutError:
                                    if not _is_websocket_connected(websocket):
                                        break
                                    continue
                        finally:
                            bus.unsubscribe(sub_queue)
                    except Exception as sub_err:
                        logger.error(
                            f"Error in subscribe handler for user {user_id}: {sub_err}",
                            exc_info=True,
                        )
                        try:
                            await websocket.send_json(
                                WSErrorMessage(
                                    type="error",
                                    message=f"Error subscribing to execution: {str(sub_err)}",
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
                                WSErrorMessage(
                                    type="error",
                                    message="No active chat session for approval",
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
                                WSErrorMessage(
                                    type="error",
                                    message=f"Failed to register approval for session {active_session_id}",
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
                            WSErrorMessage(
                                type="error",
                                message=f"Error processing approval: {str(approval_err)}",
                                code=500,
                            ).model_dump()
                        )
                    continue

                # Handle chat messages -- create session, start execution, forward events
                request = WSChatRequest.model_validate(data)

                # Validate assistant config per message
                if not request.assistant_config_id:
                    await websocket.send_json(
                        WSErrorMessage(
                            type="error",
                            message="Assistant config is required for new sessions",
                            code=400,
                        ).model_dump()
                    )
                    continue

                assistant_config = await config_service.get_assistant_config(
                    request.assistant_config_id
                )
                if not assistant_config:
                    await websocket.send_json(
                        WSErrorMessage(
                            type="error",
                            message="Assistant config not found",
                            code=404,
                        ).model_dump()
                    )
                    continue

                if not assistant_config.is_active:
                    await websocket.send_json(
                        WSErrorMessage(
                            type="error",
                            message="Assistant config is not active",
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
                            WSErrorMessage(
                                type="error",
                                message=f"Session {effective_session_id} not found",
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

                exec_mode = ExecutionMode(request.execution_mode)

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
                            )
                        except Exception as exec_err:
                            logger.error(
                                f"Error in start_execution {e_id}: {exec_err}",
                                exc_info=True,
                            )

                    return asyncio.create_task(run_execution())

                def create_event_forwarding_task(
                    bus: AgentEventBus,
                    ws: WebSocket,
                    uid: UUID,
                ) -> asyncio.Task[None]:
                    """Create a background task that forwards bus events to the WebSocket."""

                    async def _forward() -> None:
                        queue = bus.subscribe()
                        try:
                            while True:
                                try:
                                    event = await asyncio.wait_for(
                                        queue.get(),
                                        timeout=1.0,
                                    )
                                except TimeoutError:
                                    if not _is_websocket_connected(ws):
                                        break
                                    continue
                                if not _is_websocket_connected(ws):
                                    break
                                payload = {**event.data, "type": event.event_type}
                                try:
                                    await ws.send_json(payload)
                                except Exception:
                                    logger.warning(
                                        f"Failed to forward event to WebSocket for user {uid}"
                                    )
                                    break
                                if event.event_type in ("complete", "error"):
                                    break
                        finally:
                            bus.unsubscribe(queue)

                    return asyncio.create_task(_forward())

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
                )
                execution_tasks.add(execution_task)
                current_chat_task = execution_task
                execution_task.add_done_callback(execution_tasks.discard)

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
                forwarding_task = create_event_forwarding_task(
                    exec_bus,
                    websocket,
                    user_id,
                )
                execution_tasks.add(forwarding_task)
                forwarding_task.add_done_callback(execution_tasks.discard)

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
                    WSErrorMessage(
                        type="error",
                        message=f"Internal server error: {str(e)}",
                        code=500,
                    ).model_dump()
                )
            except Exception:
                # WebSocket may already be closed
                pass
        finally:
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
            # They clean up via add_done_callback(execution_tasks.discard).
            # The start_execution() finally block handles bus cleanup.

            # Clean up interrupt node for this session
            if current_session_id is not None:
                agent_service.unregister_interrupt_node(current_session_id)

        # Context manager automatically closes the db session
        logger.debug(f"WebSocket connection cleanup completed for user {user_id}")
