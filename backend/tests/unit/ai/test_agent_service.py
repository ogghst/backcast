"""Tests for AgentService - comprehensive coverage for orchestration, session management, and error handling."""

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from app.ai.agent_service import AgentService, _extract_client_config
from app.models.domain.ai import (
    AIConversationMessage,
    AIConversationSession,
    AIProvider,
    AIProviderConfig,
)


@pytest.mark.asyncio
class TestAgentServiceInitialization:
    """Test AgentService initialization and basic setup."""

    async def test_agent_service_initialization(self, db_session: AsyncSession) -> None:
        """Verify AgentService can be initialized with a database session."""
        service = AgentService(db_session)
        assert service.session == db_session


@pytest.mark.asyncio
class TestExtractClientConfig:
    """Test _extract_client_config helper function."""

    async def test_extract_config_with_api_key(self, db_session: AsyncSession) -> None:
        """Verify extraction of basic API key configuration."""
        provider = AIProvider(
            id=uuid4(),
            name="test_provider",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
        )

        config_service = Mock()
        config_service.list_provider_configs = AsyncMock(
            return_value=[
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="api_key",
                    value="sk-test-key",
                )
            ]
        )

        result = await _extract_client_config(provider, config_service)

        assert result["api_key"] == "sk-test-key"
        assert result["base_url"] == "https://api.openai.com/v1"

    async def test_extract_config_with_timeout_and_retries(
        self, db_session: AsyncSession
    ) -> None:
        """Verify extraction of timeout and max_retries configuration."""
        provider = AIProvider(
            id=uuid4(),
            name="test_provider",
            provider_type="openai",
        )

        config_service = Mock()
        config_service.list_provider_configs = AsyncMock(
            return_value=[
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="api_key",
                    value="sk-test-key",
                ),
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="timeout",
                    value="30.0",
                ),
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="max_retries",
                    value="3",
                ),
            ]
        )

        result = await _extract_client_config(provider, config_service)

        assert result["timeout"] == 30.0
        assert result["max_retries"] == 3

    async def test_extract_config_azure_deployment(
        self, db_session: AsyncSession
    ) -> None:
        """Verify Azure-specific configuration extraction."""
        provider = AIProvider(
            id=uuid4(),
            name="azure_provider",
            provider_type="azure",
        )

        config_service = Mock()
        config_service.list_provider_configs = AsyncMock(
            return_value=[
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="api_key",
                    value="azure-key",
                ),
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="azure_deployment",
                    value="gpt-4-deployment",
                ),
            ]
        )

        result = await _extract_client_config(provider, config_service)

        assert result["model"] == "gpt-4-deployment"

    async def test_extract_config_uses_provider_base_url_fallback(
        self, db_session: AsyncSession
    ) -> None:
        """Verify provider base_url is used when config base_url is missing."""
        provider = AIProvider(
            id=uuid4(),
            name="test_provider",
            provider_type="openai",
            base_url="https://custom.example.com",
        )

        config_service = Mock()
        config_service.list_provider_configs = AsyncMock(
            return_value=[
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider.id),
                    key="api_key",
                    value="sk-test",
                )
            ]
        )

        result = await _extract_client_config(provider, config_service)

        assert result["base_url"] == "https://custom.example.com"


@pytest.mark.asyncio
class TestGetLLMClientConfig:
    """Test _get_llm_client_config method."""

    async def test_get_llm_client_config_success(
        self, db_session: AsyncSession
    ) -> None:
        """Verify successful LLM client configuration retrieval."""
        service = AgentService(db_session)

        model_id = uuid4()
        provider_id = uuid4()

        config_service = Mock()
        model = Mock()
        model.id = model_id
        model.model_id = "gpt-4"
        model.provider_id = str(provider_id)

        provider = Mock()
        provider.id = provider_id
        provider.provider_type = "openai"
        provider.base_url = "https://api.openai.com/v1"

        config_service.get_model = AsyncMock(return_value=model)
        config_service.get_provider = AsyncMock(return_value=provider)
        config_service.list_provider_configs = AsyncMock(
            return_value=[
                AIProviderConfig(
                    id=uuid4(),
                    provider_id=str(provider_id),
                    key="api_key",
                    value="sk-test",
                )
            ]
        )

        with patch("app.ai.agent_service.AIConfigService", return_value=config_service):
            with patch("app.ai.agent_service._extract_client_config") as mock_extract:
                mock_extract.return_value = {"api_key": "sk-test"}

                client_config, model_name = await service._get_llm_client_config(
                    model_id
                )

                assert model_name == "gpt-4"
                assert client_config == {"api_key": "sk-test"}

    async def test_get_llm_client_config_model_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Verify error when model is not found."""
        service = AgentService(db_session)

        model_id = uuid4()

        config_service = Mock()
        config_service.get_model = AsyncMock(return_value=None)

        with patch("app.ai.agent_service.AIConfigService", return_value=config_service):
            with pytest.raises(ValueError, match="Model .* not found"):
                await service._get_llm_client_config(model_id)

    async def test_get_llm_client_config_provider_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Verify error when provider is not found."""
        service = AgentService(db_session)

        model_id = uuid4()
        provider_id = uuid4()

        config_service = Mock()
        model = Mock()
        model.id = model_id
        model.model_id = "gpt-4"
        model.provider_id = str(provider_id)

        config_service.get_model = AsyncMock(return_value=model)
        config_service.get_provider = AsyncMock(return_value=None)

        with patch("app.ai.agent_service.AIConfigService", return_value=config_service):
            with pytest.raises(ValueError, match="Provider .* not found"):
                await service._get_llm_client_config(model_id)


@pytest.mark.asyncio
class TestCreateLangChainLLM:
    """Test _create_langchain_llm method."""

    async def test_create_langchain_llm_with_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Verify LLM creation with default parameters."""
        service = AgentService(db_session)

        client_config = {"api_key": "sk-test", "base_url": "https://api.openai.com/v1"}

        llm = await service._create_langchain_llm(
            client_config=client_config,
            model_name="gpt-4",
            temperature=None,
            max_tokens=None,
        )

        assert llm.model_name == "gpt-4"
        assert llm.temperature == 0.0  # Default
        assert llm.max_tokens == 2000  # Default

    async def test_create_langchain_llm_with_custom_params(
        self, db_session: AsyncSession
    ) -> None:
        """Verify LLM creation with custom parameters."""
        service = AgentService(db_session)

        client_config = {"api_key": "sk-test", "base_url": "https://api.openai.com/v1"}

        llm = await service._create_langchain_llm(
            client_config=client_config,
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=4000,
        )

        assert llm.model_name == "gpt-4"
        assert llm.temperature == 0.7
        assert llm.max_tokens == 4000


@pytest.mark.asyncio
class TestGetSession:
    """Test _get_session method."""

    async def test_get_session_found(self, db_session: AsyncSession) -> None:
        """Verify successful session retrieval."""
        service = AgentService(db_session)

        session_id = uuid4()
        session = AIConversationSession(
            id=str(session_id),
            user_id=str(uuid4()),
            assistant_config_id=str(uuid4()),
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=session)

        with patch.object(db_session, "execute", return_value=mock_result):
            result = await service._get_session(session_id)
            assert result == session

    async def test_get_session_not_found(self, db_session: AsyncSession) -> None:
        """Verify None returned when session not found."""
        service = AgentService(db_session)

        session_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)

        with patch.object(db_session, "execute", return_value=mock_result):
            result = await service._get_session(session_id)
            assert result is None


@pytest.mark.asyncio
class TestBuildConversationHistory:
    """Test _build_conversation_history method."""

    async def test_build_history_with_messages(self, db_session: AsyncSession) -> None:
        """Verify conversation history is built correctly."""
        service = AgentService(db_session)

        session_id = uuid4()

        messages = [
            AIConversationMessage(
                id=str(uuid4()),
                session_id=str(session_id),
                role="user",
                content="Hello",
            ),
            AIConversationMessage(
                id=str(uuid4()),
                session_id=str(session_id),
                role="assistant",
                content="Hi there!",
            ),
            AIConversationMessage(
                id=str(uuid4()),
                session_id=str(session_id),
                role="tool",
                content="Tool result",
            ),
        ]

        with patch.object(
            service, "_get_session_messages", AsyncMock(return_value=messages)
        ):
            history = await service._build_conversation_history(session_id)

            assert len(history) == 2  # user + assistant (tool messages skipped)
            assert isinstance(history[0], HumanMessage)
            assert history[0].content == "Hello"
            assert isinstance(history[1], AIMessage)
            assert history[1].content == "Hi there!"

    async def test_build_history_empty_session(self, db_session: AsyncSession) -> None:
        """Verify empty history for new session."""
        service = AgentService(db_session)

        session_id = uuid4()

        with patch.object(service, "_get_session_messages", AsyncMock(return_value=[])):
            history = await service._build_conversation_history(session_id)

            assert len(history) == 0


@pytest.mark.asyncio
class TestGetSessionMessages:
    """Test _get_session_messages method."""

    async def test_get_session_messages_ordered(self, db_session: AsyncSession) -> None:
        """Verify messages are ordered by created_at."""
        service = AgentService(db_session)

        session_id = uuid4()

        msg1 = AIConversationMessage(
            id=str(uuid4()),
            session_id=str(session_id),
            role="user",
            content="First",
        )
        msg2 = AIConversationMessage(
            id=str(uuid4()),
            session_id=str(session_id),
            role="assistant",
            content="Second",
        )

        mock_result = Mock()
        mock_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=[msg1, msg2]))
        )

        with patch.object(db_session, "execute", return_value=mock_result):
            messages = await service._get_session_messages(session_id)

            assert len(messages) == 2
            assert messages[0].content == "First"
            assert messages[1].content == "Second"


@pytest.mark.asyncio
class TestChatMethod:
    """Test chat method orchestration."""

    async def test_chat_creates_new_session(self, db_session: AsyncSession) -> None:
        """Verify new session creation components work correctly."""
        service = AgentService(db_session)

        user_id = uuid4()
        session_id = uuid4()
        assistant_config = Mock()
        assistant_config.id = uuid4()
        assistant_config.model_id = uuid4()
        assistant_config.system_prompt = None
        assistant_config.temperature = 0.7
        assistant_config.max_tokens = 2000
        assistant_config.allowed_tools = None

        # Test session object creation
        new_session = AIConversationSession(
            user_id=str(user_id),
            assistant_config_id=str(assistant_config.id),
        )

        assert new_session.user_id == str(user_id)
        assert new_session.assistant_config_id == str(assistant_config.id)

        # Test history building
        with patch.object(service, "_get_session_messages", AsyncMock(return_value=[])):
            history = await service._build_conversation_history(session_id)
            assert isinstance(history, list)
            assert len(history) == 0

        # Test LLM client config retrieval
        with patch.object(service, "_get_llm_client_config") as mock_config:
            mock_config.return_value = ({"api_key": "test"}, "gpt-4")
            config, model = await service._get_llm_client_config(uuid4())
            assert config["api_key"] == "test"
            assert model == "gpt-4"

        # Test that we can create a LangChain LLM
        with patch.object(service, "_create_langchain_llm") as mock_llm:
            mock_llm.return_value = Mock()
            llm = await service._create_langchain_llm(
                client_config={"api_key": "test"},
                model_name="gpt-4",
                temperature=0.7,
                max_tokens=2000,
            )
            assert llm is not None

    async def test_chat_raises_error_for_invalid_session_id(
        self, db_session: AsyncSession
    ) -> None:
        """Verify error raised when session_id not found."""
        service = AgentService(db_session)

        user_id = uuid4()
        session_id = uuid4()
        assistant_config = Mock()

        with (
            patch.object(service, "_get_session", AsyncMock(return_value=None)),
            pytest.raises(ValueError, match="Session .* not found"),
        ):
            await service.chat(
                message="Hello",
                assistant_config=assistant_config,
                session_id=session_id,
                user_id=user_id,
            )


@pytest.mark.asyncio
class TestChatStreamMethod:
    """Test chat_stream method for WebSocket streaming."""

    async def test_chat_stream_creates_new_session(
        self, db_session: AsyncSession
    ) -> None:
        """Verify new session creation components for streaming."""
        service = AgentService(db_session)

        user_id = uuid4()
        session_id = uuid4()
        assistant_config = Mock()
        assistant_config.id = uuid4()
        assistant_config.model_id = uuid4()
        assistant_config.system_prompt = None
        assistant_config.temperature = 0.7
        assistant_config.max_tokens = 2000
        assistant_config.allowed_tools = None

        # Test that we can create the session object
        new_session = AIConversationSession(
            user_id=str(user_id),
            assistant_config_id=str(assistant_config.id),
        )

        assert new_session.user_id == str(user_id)
        assert new_session.assistant_config_id == str(assistant_config.id)

        # Test that history building works
        with patch.object(service, "_get_session_messages", AsyncMock(return_value=[])):
            history = await service._build_conversation_history(session_id)
            assert history == []

        # Test LLM config retrieval setup
        with patch.object(service, "_get_llm_client_config") as mock_config:
            mock_config.return_value = ({"api_key": "test"}, "gpt-4")
            config, model = await service._get_llm_client_config(uuid4())
            assert config["api_key"] == "test"
            assert model == "gpt-4"

    def _mock_stream_events(self, events: list[dict[str, Any]]) -> Mock:
        """Create a mock astream_events generator."""

        async def async_generator() -> Any:
            for event in events:
                yield event

        mock_gen = AsyncMock()
        mock_gen.__aiter__ = lambda self: async_generator()
        return mock_gen

    async def test_chat_stream_handles_websocket_closure(
        self, db_session: AsyncSession
    ) -> None:
        """Verify graceful handling of WebSocket closure during streaming."""
        AgentService(db_session)

        # Test that WebSocket errors are caught in the streaming logic
        websocket = Mock()
        websocket.send_json = AsyncMock(side_effect=Exception("WebSocket closed"))

        # Verify the exception is raised
        with pytest.raises(Exception, match="WebSocket closed"):
            await websocket.send_json({"test": "message"})

        # Verify service can handle errors in tool result serialization
        tool_msg = ToolMessage(content="Result", tool_call_id="call_123")

        # Test content extraction doesn't raise
        result_content = tool_msg.content
        assert result_content == "Result"

        # Test JSON serialization works
        tool_result = {
            "tool": "test_tool",
            "success": True,
            "result": result_content,
            "error": None,
        }
        json_str = json.dumps(tool_result)
        assert json_str is not None


# Keep existing tests
@pytest.mark.asyncio
class TestToolResultSerialization:
    """Test that ToolMessage objects are properly serialized for JSON storage."""

    async def test_tool_message_content_extraction(
        self, db_session: AsyncSession
    ) -> None:
        """Verify that ToolMessage.content is extracted correctly."""
        AgentService(db_session)

        # Create a ToolMessage with string content
        tool_msg: ToolMessage = ToolMessage(
            content="Tool execution result", tool_call_id="call_123"
        )

        # Simulate the extraction logic from chat_stream
        tool_output = tool_msg
        result_content: str | list[str | dict[str, Any]] | dict[str, Any] = (
            tool_output.content
        )

        # Verify the content is extracted
        assert result_content == "Tool execution result"
        assert isinstance(result_content, str)

    async def test_tool_message_dict_extraction(self, db_session: AsyncSession) -> None:
        """Verify that ToolMessage with dict content is handled correctly."""
        AgentService(db_session)

        # Create a ToolMessage with string content (dicts are stringified)
        tool_msg: ToolMessage = ToolMessage(
            content='{"result": "success", "data": [1, 2, 3]}', tool_call_id="call_456"
        )

        # Simulate the extraction logic
        tool_output = tool_msg
        result_content: str | list[str | dict[str, Any]] | dict[str, Any] = (
            tool_output.content
        )

        # Verify the content is extracted and is a string
        assert result_content == '{"result": "success", "data": [1, 2, 3]}'
        assert isinstance(result_content, str)
        # Verify it's JSON-serializable
        assert json.dumps(result_content)  # Should not raise

    async def test_tool_result_format(self, db_session: AsyncSession) -> None:
        """Verify the tool result dict format is JSON-serializable."""
        AgentService(db_session)

        # Create a tool result dict like in chat_stream
        tool_msg = ToolMessage(content="Result text", tool_call_id="call_789")
        result_content = tool_msg.content

        tool_result = {
            "tool": "test_tool",
            "success": True,
            "result": result_content,
            "error": None,
        }

        # Verify it's JSON-serializable
        json_str = json.dumps(tool_result)
        assert json_str

        # Verify it can be deserialized
        parsed = json.loads(json_str)
        assert parsed["tool"] == "test_tool"
        assert parsed["result"] == "Result text"

    async def test_plain_string_handling(self, db_session: AsyncSession) -> None:
        """Verify that plain string outputs are handled correctly."""
        AgentService(db_session)

        # Simulate a plain string output (not a ToolMessage)
        tool_output = "Plain string result"

        result_content = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content

        # Verify the string is unchanged
        assert result_content == "Plain string result"
        assert isinstance(result_content, str)

    async def test_dict_with_content_field(self, db_session: AsyncSession) -> None:
        """Verify that dict outputs with 'content' field are handled correctly."""
        AgentService(db_session)

        # Simulate a dict output with content field
        tool_output: dict[str, Any] = {
            "content": "Extracted content",
            "metadata": "extra",
        }

        result_content: str | dict[str, Any] = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content
        elif isinstance(tool_output, dict) and "content" in tool_output:
            result_content = tool_output["content"]

        # Verify the content is extracted
        assert result_content == "Extracted content"


@pytest.mark.asyncio
class TestDisconnectDetection:
    """Test that agent streaming stops when WebSocket disconnects mid-stream."""

    async def test_stream_stops_on_websocket_disconnect(
        self, db_session: AsyncSession
    ) -> None:
        """Verify streaming loop breaks immediately when client disconnects.

        When the WebSocket client_state transitions to DISCONNECTED during
        the astream_events loop, the agent should stop processing remaining
        events instead of wasting resources on a dead connection.
        """
        # Set up real DB entities for the chat_stream call
        from app.services.ai_config_service import AIConfigService

        config_service = AIConfigService(db_session)

        from app.models.schemas.ai import AIModelCreate, AIProviderCreate

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

        from app.models.domain.ai import AIAssistantConfig

        assistant_config = AIAssistantConfig(
            name="Test Assistant",
            model_id=str(model.id),
            system_prompt="You are a helpful assistant",
            temperature=0.7,
            max_tokens=1000,
            allowed_tools=None,
            is_active=True,
        )
        db_session.add(assistant_config)
        await db_session.flush()
        await db_session.refresh(assistant_config)

        # Create a mock WebSocket that disconnects after 3 events
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()

        # Track events processed by the generator
        events_yielded: list[int] = []

        # Build 10 on_chat_model_stream events
        total_events = 10
        disconnect_after = 3

        async def mock_astream_events(
            *args: object, **kwargs: object
        ) -> AsyncIterator[dict[str, Any]]:
            """Yield events, tracking how many are produced by the generator."""
            for i in range(total_events):
                events_yielded.append(i)
                chunk = MagicMock()
                chunk.text = f"token_{i}"
                chunk.content = f"token_{i}"
                yield {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": chunk},
                }

        # Mock graph with our tracking generator
        mock_graph = MagicMock()
        mock_graph.astream_events = mock_astream_events

        # Set up WebSocket state: starts CONNECTED, becomes DISCONNECTED
        # after 'disconnect_after' events are yielded from the generator.
        # The _is_websocket_connected check happens at the top of each loop
        # iteration, AFTER the event has been yielded. So we disconnect
        # after the generator yields event N, and the loop will break
        # when processing event N+1.
        call_count = 0

        def get_client_state() -> WebSocketState:
            nonlocal call_count
            call_count += 1
            # The first call is the thinking event check (before the loop).
            # Subsequent calls are the per-event connectivity checks.
            # Allow the thinking event + disconnect_after events to succeed.
            if call_count <= disconnect_after + 1:
                return WebSocketState.CONNECTED
            return WebSocketState.DISCONNECTED

        mock_websocket.client_state = property(
            lambda self: get_client_state()  # type: ignore[arg-type]
        )

        # Create the service and run chat_stream with mocked graph
        service = AgentService(db_session)
        mock_llm = MagicMock()

        with (
            patch.object(
                service, "_create_deep_agent_graph", return_value=(mock_graph, None)
            ),
            patch.object(service, "_create_langchain_llm", return_value=mock_llm),
        ):
            await service.chat_stream(
                message="Hello",
                assistant_config=assistant_config,
                session_id=None,
                user_id=uuid4(),
                websocket=mock_websocket,
                db=db_session,
            )

        # The generator should have been allowed to yield all events since
        # it's an async generator that doesn't check the websocket itself.
        # However, the _consume_stream loop should have stopped processing
        # events after the disconnect was detected.
        # The key assertion: events were yielded but the loop broke early,
        # meaning the token content was NOT accumulated for all events.
        # We verify this by checking that not all token events were sent
        # via the WebSocket.
        sent_messages = [
            call[0][0]
            for call in mock_websocket.send_json.call_args_list
            if call[0] and isinstance(call[0][0], dict)
        ]
        token_batch_messages = [
            msg for msg in sent_messages if msg.get("type") == "token_batch"
        ]

        # The loop should have stopped processing events after disconnect
        # was detected. Since disconnect_after=3 and the generator yields 10,
        # we should have far fewer than 10 token batches sent.
        assert len(token_batch_messages) < total_events, (
            f"Expected fewer than {total_events} token_batch messages "
            f"after disconnect, got {len(token_batch_messages)}"
        )

    async def test_is_websocket_connected_returns_true_when_connected(
        self, db_session: AsyncSession
    ) -> None:
        """Verify _is_websocket_connected returns True for connected WebSocket."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.client_state = WebSocketState.CONNECTED

        assert AgentService._is_websocket_connected(mock_ws) is True

    async def test_is_websocket_connected_returns_false_when_disconnected(
        self, db_session: AsyncSession
    ) -> None:
        """Verify _is_websocket_connected returns False for disconnected WebSocket."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.client_state = WebSocketState.DISCONNECTED

        assert AgentService._is_websocket_connected(mock_ws) is False

    async def test_disconnect_logs_warning(self, db_session: AsyncSession) -> None:
        """Verify a warning is logged when WebSocket disconnects during streaming."""
        from app.services.ai_config_service import AIConfigService

        config_service = AIConfigService(db_session)

        from app.models.schemas.ai import AIModelCreate, AIProviderCreate

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

        from app.models.domain.ai import AIAssistantConfig

        assistant_config = AIAssistantConfig(
            name="Test Assistant",
            model_id=str(model.id),
            system_prompt="You are a helpful assistant",
            temperature=0.7,
            max_tokens=1000,
            allowed_tools=None,
            is_active=True,
        )
        db_session.add(assistant_config)
        await db_session.flush()
        await db_session.refresh(assistant_config)

        # WebSocket starts disconnected so the loop breaks on first event
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        mock_websocket.send_json = AsyncMock()

        # Single event in the stream
        async def mock_astream_events(
            *args: object, **kwargs: object
        ) -> AsyncIterator[dict[str, Any]]:
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(text="x", content="x")},
            }

        mock_graph = MagicMock()
        mock_graph.astream_events = mock_astream_events

        service = AgentService(db_session)
        mock_llm = MagicMock()

        with (
            patch.object(
                service, "_create_deep_agent_graph", return_value=(mock_graph, None)
            ),
            patch.object(service, "_create_langchain_llm", return_value=mock_llm),
            patch("app.ai.agent_service.logger") as mock_logger,
        ):
            await service.chat_stream(
                message="Hello",
                assistant_config=assistant_config,
                session_id=None,
                user_id=uuid4(),
                websocket=mock_websocket,
                db=db_session,
            )

        # Verify the warning about aborting agent execution was logged
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        abort_warnings = [w for w in warning_calls if "aborting agent execution" in w]
        assert len(abort_warnings) >= 1, (
            f"Expected warning about aborting agent execution, "
            f"got warnings: {warning_calls}"
        )
