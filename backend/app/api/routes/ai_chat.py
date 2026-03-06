"""API routes for AI chat.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIConversationMessagePublic,
    AIConversationSessionPublic,
)
from app.services.ai_config_service import AIConfigService

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


def get_ai_config_service(session: AsyncSession = Depends(get_db)) -> AIConfigService:
    """Get AI configuration service."""
    return AIConfigService(session)


def get_agent_service(session: AsyncSession = Depends(get_db)) -> AgentService:
    """Get agent service."""
    return AgentService(session)


@router.post(
    "/chat",
    response_model=AIChatResponse,
    operation_id="ai_chat",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def chat(
    request: AIChatRequest,
    current_user: User = Depends(get_current_active_user),
    agent_service: AgentService = Depends(get_agent_service),
    config_service: AIConfigService = Depends(get_ai_config_service),
) -> AIChatResponse:
    """Send a chat message using LangGraph agent."""
    # Get assistant config - must be provided for new sessions
    if not request.assistant_config_id:
        raise HTTPException(
            status_code=400, detail="Assistant config is required"
        )
    assistant_config = await config_service.get_assistant_config(
        request.assistant_config_id
    )
    if not assistant_config:
        raise HTTPException(
            status_code=400, detail="Assistant config is required"
        )
    if not assistant_config.is_active:
        raise HTTPException(
            status_code=400, detail="Assistant config is not active"
        )
    # Process chat using agent service
    response = await agent_service.chat(
        message=request.message,
        assistant_config=assistant_config,
        session_id=request.session_id,
        user_id=current_user.user_id,
    )
    return response


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
    return [
        AIConversationSessionPublic.model_validate(s) for s in sessions
    ]


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
    return [
        AIConversationMessagePublic.model_validate(m) for m in messages
    ]


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
