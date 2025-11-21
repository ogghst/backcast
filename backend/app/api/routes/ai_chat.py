"""AI Chat WebSocket endpoint for real-time chat communication."""

import json
import uuid
from datetime import date
from typing import Literal

import jwt
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.api.deps import get_db
from app.core import security
from app.core.config import settings
from app.models import WBE, CostElement, Project, TokenPayload, User
from app.services.ai_chat import (
    ContextType,
    generate_initial_assessment,
    send_chat_message,
)

router = APIRouter(prefix="/ai-chat", tags=["ai-chat"])


async def get_current_user_from_websocket(
    websocket: WebSocket, session: Session, token: str | None
) -> User:
    """Authenticate user from WebSocket token."""
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise HTTPException(status_code=403, detail="Missing authentication token")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        await websocket.close(code=4002, reason="Invalid authentication token")
        raise HTTPException(status_code=403, detail="Could not validate credentials")

    user = session.get(User, token_data.sub)
    if not user:
        await websocket.close(code=4003, reason="User not found")
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        await websocket.close(code=4004, reason="Inactive user")
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def _ensure_project_exists(session: Session, project_id: uuid.UUID) -> Project:
    """Ensure project exists and return it."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_wbe_exists(session: Session, wbe_id: uuid.UUID) -> WBE:
    """Ensure WBE exists and return it."""
    wbe = session.get(WBE, wbe_id)
    if not wbe:
        raise HTTPException(status_code=404, detail="WBE not found")
    return wbe


def _ensure_cost_element_exists(
    session: Session, cost_element_id: uuid.UUID
) -> CostElement:
    """Ensure cost element exists and return it."""
    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")
    return cost_element


async def _validate_context_access(
    session: Session,
    context_type: ContextType,
    context_id: uuid.UUID,
    _user: User,  # Currently unused but may be needed for future access checks
) -> None:
    """Validate that user can access the context."""
    if context_type == "project":
        _ensure_project_exists(session, context_id)
        # Additional access checks can be added here if needed
    elif context_type == "wbe":
        wbe = _ensure_wbe_exists(session, context_id)
        # Ensure user can access the project that owns this WBE
        if wbe.project_id:
            _ensure_project_exists(session, wbe.project_id)
    elif context_type == "cost-element":
        cost_element = _ensure_cost_element_exists(session, context_id)
        # Ensure user can access the project via WBE
        if cost_element.wbe_id:
            wbe = _ensure_wbe_exists(session, cost_element.wbe_id)
            if wbe.project_id:
                _ensure_project_exists(session, wbe.project_id)
    elif context_type == "baseline":
        # Baseline validation will be added in a later step
        # For now, we'll validate access via the project
        pass
    else:
        raise HTTPException(
            status_code=400, detail=f"Invalid context type: {context_type}"
        )


@router.websocket("/{context_type}/{context_id}/ws")
async def ai_chat_websocket(
    websocket: WebSocket,
    context_type: Literal["project", "wbe", "cost-element", "baseline"],
    context_id: uuid.UUID,
    token: str | None = Query(default=None, description="JWT authentication token"),
    control_date: date | None = Query(
        default=None, description="Control date for time-machine filtering"
    ),
) -> None:
    """
    WebSocket endpoint for AI chat communication with streaming support.

    Message Protocol:
    - Client sends: {"type": "start_analysis" | "message", "content": string, "conversation_history": array}
    - Server sends: {"type": "assessment_chunk" | "response" | "error" | "status" | "assessment_complete", "content": string}

    Operations:
    - start_analysis: Generates initial assessment, streams chunks via WebSocket
    - message: Handles chat message, streams AI response chunks via WebSocket
    """
    # Accept WebSocket connection
    await websocket.accept()

    # Get database session
    session = next(get_db())
    user = None

    try:
        # Authenticate user
        user = await get_current_user_from_websocket(websocket, session, token)

        # Validate context access
        _validate_context_access(session, context_type, context_id, user)

        # Use control_date from query or user's time-machine date or today
        if control_date is None:
            control_date = user.time_machine_date or date.today()

        # Define async send_message function for streaming
        async def send_message(message: dict) -> None:
            """Send message via WebSocket."""
            await websocket.send_json(message)

        # Handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                message_type = data.get("type")
                content = data.get("content", "")
                conversation_history = data.get("conversation_history", [])

                if message_type == "start_analysis":
                    # Generate initial assessment
                    await generate_initial_assessment(
                        session=session,
                        user_id=user.id,
                        context_type=context_type,
                        context_id=context_id,
                        control_date=control_date,
                        send_message=send_message,
                    )

                elif message_type == "message":
                    # Handle chat message
                    await send_chat_message(
                        session=session,
                        user_id=user.id,
                        context_type=context_type,
                        context_id=context_id,
                        control_date=control_date,
                        message=content,
                        conversation_history=conversation_history,
                        send_message=send_message,
                    )

                else:
                    await send_message(
                        {
                            "type": "error",
                            "content": f"Unknown message type: {message_type}",
                        }
                    )

            except WebSocketDisconnect:
                # Client disconnected
                break

            except json.JSONDecodeError:
                await send_message(
                    {
                        "type": "error",
                        "content": "Invalid JSON message",
                    }
                )

            except Exception as e:
                await send_message(
                    {
                        "type": "error",
                        "content": f"Error processing message: {str(e)}",
                    }
                )

    except HTTPException:
        # HTTP exceptions are already handled with WebSocket close
        pass

    except Exception as e:
        # Send error and close connection
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "content": f"Connection error: {str(e)}",
                }
            )
        except Exception:
            pass
        await websocket.close(code=4000, reason="Internal server error")

    finally:
        # Clean up database session
        session.close()
