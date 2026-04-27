"""Tests for AgentService._run_agent_graph event publishing."""

from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.ai.execution.agent_event_bus import AgentEventBus
from app.models.domain.ai import AIAssistantConfig, AIConversationSession
from app.models.schemas.ai import (
    AIModelCreate,
    AIProviderCreate,
)


async def _setup_assistant_config(
    db_session: AsyncSession,
) -> AIAssistantConfig:
    """Create provider, model, and assistant config in database."""
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
    )
    provider = await config_service.create_provider(provider_in)

    model_in = AIModelCreate(
        model_id="gpt-4",
        display_name="GPT-4",
        provider_id=provider.id,
    )
    model = await config_service.create_model(model_in)

    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=str(model.id),
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=1000,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()
    await db_session.refresh(assistant_config)

    return assistant_config


async def _create_session_with_user_message(
    db_session: AsyncSession,
    assistant_config: AIAssistantConfig,
    user_id: str,
) -> AIConversationSession:
    """Create a conversation session with a user message."""
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)
    session = await config_service.create_session(
        user_id=user_id,
        assistant_config_id=assistant_config.id,
    )
    await config_service.add_message(
        session_id=session.id,
        role="user",
        content="Hello",
    )
    return session


def _make_token_stream_events() -> list[dict]:
    """Create mock streaming events with two token chunks."""
    chunk1 = MagicMock()
    chunk1.text = "Hello"
    chunk1.content = "Hello"

    chunk2 = MagicMock()
    chunk2.text = " world"
    chunk2.content = " world"

    return [
        {"event": "on_chat_model_stream", "data": {"chunk": chunk1}},
        {"event": "on_chat_model_stream", "data": {"chunk": chunk2}},
        {"event": "on_end", "data": {"output": {"messages": []}}},
    ]


def _make_end_event() -> list[dict]:
    """Create a single on_end event for simple stream completion."""
    return [
        {"event": "on_end", "data": {"output": {"messages": []}}},
    ]


async def _run_with_mocks(
    service: AgentService,
    assistant_config: AIAssistantConfig,
    session_id: object,
    user_id: object,
    event_bus: AgentEventBus,
    events: list[dict],
) -> None:
    """Run _run_agent_graph with standard mocks and the given events."""
    mock_llm = MagicMock()
    mock_graph = MagicMock()

    async def mock_astream_events(
        *args: object, **kwargs: object
    ) -> AsyncIterator[dict]:
        for event in events:
            yield event

    mock_graph.astream_events = mock_astream_events
    mock_interrupt_node = None

    with (
        patch.object(
            service,
            "_get_llm_client_config",
            return_value=({"api_key": "test"}, "gpt-4", "openai"),
        ),
        patch.object(
            service,
            "_create_langchain_llm",
            return_value=mock_llm,
        ),
        patch(
            "app.ai.agent_service._get_user_role",
            return_value="guest",
        ),
        patch(
            "app.ai.agent_service.create_project_tools",
            return_value=[],
        ),
        patch.object(
            service,
            "_create_deep_agent_graph",
            return_value=(mock_graph, mock_interrupt_node),
        ),
        patch(
            "app.ai.agent_service.set_request_context",
        ),
        patch(
            "app.ai.agent_service.shared_checkpointer",
        ),
        patch(
            "app.ai.agent_service.clear_request_context",
        ),
    ):
        await service._run_agent_graph(
            message="Hello",
            assistant_config=assistant_config,
            session_id=session_id,
            user_id=user_id,
            event_bus=event_bus,
        )


@pytest.mark.asyncio
async def test_run_agent_graph_publishes_token_events(
    db_session: AsyncSession,
) -> None:
    """Test that _run_agent_graph publishes token_batch events to the bus."""
    service = AgentService(db_session)
    assistant_config = await _setup_assistant_config(db_session)

    user_id = uuid4()
    conversation_session = await _create_session_with_user_message(
        db_session,
        assistant_config,
        str(user_id),
    )

    event_bus = AgentEventBus(execution_id=str(uuid4()))
    events = _make_token_stream_events()

    await _run_with_mocks(
        service,
        assistant_config,
        conversation_session.id,
        user_id,
        event_bus,
        events,
    )

    token_events = [e for e in event_bus.replay() if e.event_type == "token_batch"]
    assert len(token_events) >= 1


@pytest.mark.asyncio
async def test_run_agent_graph_publishes_complete_event(
    db_session: AsyncSession,
) -> None:
    """Test that _run_agent_graph publishes a complete event at the end."""
    service = AgentService(db_session)
    assistant_config = await _setup_assistant_config(db_session)

    user_id = uuid4()
    conversation_session = await _create_session_with_user_message(
        db_session,
        assistant_config,
        str(user_id),
    )

    event_bus = AgentEventBus(execution_id=str(uuid4()))
    events = _make_end_event()

    await _run_with_mocks(
        service,
        assistant_config,
        conversation_session.id,
        user_id,
        event_bus,
        events,
    )

    complete_events = [e for e in event_bus.replay() if e.event_type == "complete"]
    assert len(complete_events) == 1
    assert "session_id" in complete_events[0].data


@pytest.mark.asyncio
async def test_run_agent_graph_publishes_error_on_exception(
    db_session: AsyncSession,
) -> None:
    """Test that _run_agent_graph publishes error event when graph raises."""
    service = AgentService(db_session)
    assistant_config = await _setup_assistant_config(db_session)

    user_id = uuid4()
    conversation_session = await _create_session_with_user_message(
        db_session,
        assistant_config,
        str(user_id),
    )

    event_bus = AgentEventBus(execution_id=str(uuid4()))
    mock_llm = MagicMock()
    mock_graph = MagicMock()

    async def mock_astream_events_error(
        *args: object, **kwargs: object
    ) -> AsyncIterator[dict]:
        raise RuntimeError("Streaming failed")
        yield  # Never reached

    mock_graph.astream_events = mock_astream_events_error
    mock_interrupt_node = None

    with (
        patch.object(
            service,
            "_get_llm_client_config",
            return_value=({"api_key": "test"}, "gpt-4", "openai"),
        ),
        patch.object(
            service,
            "_create_langchain_llm",
            return_value=mock_llm,
        ),
        patch(
            "app.ai.agent_service._get_user_role",
            return_value="guest",
        ),
        patch(
            "app.ai.agent_service.create_project_tools",
            return_value=[],
        ),
        patch.object(
            service,
            "_create_deep_agent_graph",
            return_value=(mock_graph, mock_interrupt_node),
        ),
        patch(
            "app.ai.agent_service.set_request_context",
        ),
        patch(
            "app.ai.agent_service.shared_checkpointer",
        ),
        patch(
            "app.ai.agent_service.clear_request_context",
        ),
    ):
        await service._run_agent_graph(
            message="Hello",
            assistant_config=assistant_config,
            session_id=conversation_session.id,
            user_id=user_id,
            event_bus=event_bus,
        )

    error_events = [e for e in event_bus.replay() if e.event_type == "error"]
    assert len(error_events) >= 1


@pytest.mark.asyncio
async def test_run_agent_graph_uses_existing_session(
    db_session: AsyncSession,
) -> None:
    """Test that _run_agent_graph uses the provided session_id."""
    service = AgentService(db_session)
    assistant_config = await _setup_assistant_config(db_session)

    user_id = uuid4()

    # Create existing session with messages
    conversation_session = await _create_session_with_user_message(
        db_session,
        assistant_config,
        str(user_id),
    )
    original_session_id = conversation_session.id

    event_bus = AgentEventBus(execution_id=str(uuid4()))
    events = _make_end_event()

    await _run_with_mocks(
        service,
        assistant_config,
        original_session_id,
        user_id,
        event_bus,
        events,
    )

    complete_events = [e for e in event_bus.replay() if e.event_type == "complete"]
    assert len(complete_events) == 1
    assert str(complete_events[0].data.get("session_id")) == str(original_session_id)


@pytest.mark.asyncio
async def test_run_agent_graph_publishes_thinking_event(
    db_session: AsyncSession,
) -> None:
    """Test that _run_agent_graph publishes a thinking event at start."""
    service = AgentService(db_session)
    assistant_config = await _setup_assistant_config(db_session)

    user_id = uuid4()
    conversation_session = await _create_session_with_user_message(
        db_session,
        assistant_config,
        str(user_id),
    )

    event_bus = AgentEventBus(execution_id=str(uuid4()))
    events = _make_end_event()

    await _run_with_mocks(
        service,
        assistant_config,
        conversation_session.id,
        user_id,
        event_bus,
        events,
    )

    thinking_events = [e for e in event_bus.replay() if e.event_type == "thinking"]
    assert len(thinking_events) >= 1
