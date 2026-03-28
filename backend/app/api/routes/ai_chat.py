"""API routes for AI chat."""

import asyncio
import logging
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.ai.tools.types import ExecutionMode
from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.core.config import settings
from app.core.rbac import get_rbac_service
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.ai import (
    AIConversationMessagePublic,
    AIConversationSessionPublic,
    WSApprovalResponseMessage,
    WSChatRequest,
    WSErrorMessage,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


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
) -> list[AIConversationSessionPublic]:
    """List conversation sessions for the current user."""
    sessions = await config_service.list_sessions(current_user.user_id)
    return [AIConversationSessionPublic.model_validate(s) for s in sessions]


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
            logger.warning(f"WebSocket connection rejected: user not found for email {subject}")
            await websocket.close(code=1008, reason="User not found")
            return

        user_id = user.user_id

        # Step 2: Check RBAC permission
        rbac_service = get_rbac_service()
        if not rbac_service.has_permission(user.role, "ai-chat"):
            logger.warning(f"WebSocket connection rejected: user {user_id} lacks ai-chat permission")
            await websocket.close(code=1008, reason="Insufficient permissions: ai-chat required")
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
            chat_stream() as background tasks, while approval responses
            are handled immediately.
            """
            nonlocal current_chat_task, current_session_id

            while True:
                data = await websocket.receive_json()
                message_type = data.get("type", "chat")

                # Handle pong keepalive — client responding to our ping, no action needed
                if message_type == "pong":
                    continue

                # Handle approval response messages immediately (non-blocking)
                if message_type == "approval_response":
                    try:
                        approval_response = WSApprovalResponseMessage.model_validate(data)
                        # Use session_holder.value — updated by chat_stream() when session is created
                        # (not current_session_id which is only updated after chat_stream() completes)
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
                        # and execute the tool — no need to call resume_graph_after_approval
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
                        logger.error(f"Error handling approval response: {approval_err}", exc_info=True)
                        await websocket.send_json(
                            WSErrorMessage(
                                type="error",
                                message=f"Error processing approval: {str(approval_err)}",
                                code=500,
                            ).model_dump()
                        )
                    continue

                # Handle chat messages - launch as background task
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

                # Update current session ID for approval handling
                if request.session_id:
                    current_session_id = request.session_id
                    session_holder.value = request.session_id

                # Launch chat_stream as background task (non-blocking)
                # Use a closure factory to avoid late binding issues with loop variables
                def create_chat_stream_task(
                    msg: str,
                    asst_config: Any,
                    sess_id: UUID | None,
                    tit: str | None,
                    proj_id: UUID | None,
                    br_id: UUID | None,
                    as_of_dt: datetime | None,
                    br_name: str | None,
                    br_mode: Literal["merged", "isolated"] | None,
                    exec_mode: ExecutionMode,
                ) -> asyncio.Task[None]:
                    """Create a background task for chat_stream with captured values.

                    This factory function captures the current loop variables by value,
                    avoiding late binding issues where all tasks would share the final
                    loop iteration values.
                    """
                    async def run_chat_stream() -> None:
                        """Run chat_stream and update session_id when complete."""
                        nonlocal current_session_id
                        try:
                            await agent_service.chat_stream(
                                message=msg,
                                assistant_config=asst_config,
                                session_id=sess_id,
                                user_id=user_id,
                                websocket=websocket,
                                db=db,
                                title=tit,
                                project_id=proj_id,
                                branch_id=br_id,
                                as_of=as_of_dt,
                                branch_name=br_name,
                                branch_mode=br_mode,
                                execution_mode=exec_mode,
                                session_holder=session_holder,
                            )
                            # Update current_session_id from session_holder in case a new session was created
                            current_session_id = session_holder.value
                            logger.info(f"WebSocket chat stream completed successfully for user {user_id}")
                        except Exception as stream_err:
                            err_msg = str(stream_err)
                            logger.error(f"Error in chat_stream for user {user_id}: {err_msg}", exc_info=True)
                            # CRITICAL: Roll back the session to reset transaction state
                            # After a database error, the session enters a failed state and
                            # all subsequent operations will fail without a rollback
                            await db.rollback()
                            try:
                                await websocket.send_json(
                                    WSErrorMessage(
                                        type="error",
                                        message=err_msg,
                                        code=500,
                                    ).model_dump()
                                )
                            except Exception:
                                pass  # WebSocket may already be closing

                    return asyncio.create_task(run_chat_stream())

                # Create and track the background task with captured values
                chat_task = create_chat_stream_task(
                    msg=request.message,
                    asst_config=assistant_config,
                    sess_id=request.session_id,
                    tit=request.title,
                    proj_id=request.project_id,
                    br_id=request.branch_id,
                    as_of_dt=request.as_of,
                    br_name=request.branch_name,
                    br_mode=request.branch_mode,
                    exec_mode=ExecutionMode(request.execution_mode),
                )
                tasks.add(chat_task)
                current_chat_task = chat_task
                # Remove task from set when it completes
                chat_task.add_done_callback(tasks.discard)

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
            logger.info(f"WebSocket disconnected normally for user {user_id}: code={e.code}, reason={e.reason}")
        except RuntimeError as e:
            # Starlette raises RuntimeError when receive_json() is called on a closed WebSocket
            # This happens when the client disconnects during streaming and the loop continues
            if "not connected" in str(e).lower():
                logger.info(f"WebSocket disconnected (RuntimeError) for user {user_id}: {e}")
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

            # Cancel all background tasks on disconnect
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Wait for tasks to finish cancellation (with timeout)
            if tasks:
                await asyncio.wait(tasks, timeout=2.0, return_when=asyncio.ALL_COMPLETED)
            tasks.clear()
            # Clean up interrupt node for this session
            if current_session_id is not None:
                agent_service.unregister_interrupt_node(current_session_id)

        # Context manager automatically closes the db session
        logger.debug(f"WebSocket connection cleanup completed for user {user_id}")
