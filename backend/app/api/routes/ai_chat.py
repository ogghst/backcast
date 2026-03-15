"""API routes for AI chat."""

import logging
from typing import Annotated
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
from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.core.config import settings
from app.core.rbac import get_rbac_service
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.ai import (
    AIConversationMessagePublic,
    AIConversationSessionPublic,
    WSChatRequest,
    WSErrorMessage,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


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
    db: AsyncSession | None = None

    try:
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

        # Create database session after token validation
        db = async_session_maker()

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

        while True:
            data = await websocket.receive_json()
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

            # Process the message and stream the response
            try:
                await agent_service.chat_stream(
                    message=request.message,
                    assistant_config=assistant_config,
                    session_id=request.session_id,
                    user_id=user_id,
                    websocket=websocket,
                    db=db,
                    title=request.title,
                )
                logger.info(f"WebSocket chat stream completed successfully for user {user_id}")
            except Exception as stream_err:
                err_msg = str(stream_err)
                logger.error(f"Error in chat_stream for user {user_id}: {err_msg}", exc_info=True)
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

    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected normally for user {user_id}: code={e.code}, reason={e.reason}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}", exc_info=True)
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
        # Ensure database session is closed
        if db is not None:
            await db.close()
        logger.debug(f"WebSocket connection cleanup completed for user {user_id}")
