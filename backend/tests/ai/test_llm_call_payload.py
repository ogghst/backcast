"""Tests for the ``[LLM_CALL_PAYLOAD]`` request-size diagnostic.

Covers the helper pieces that compute the size of each LLM request's
message payload (driven by the glm-4.7 ~247k-prompt-token bloat incident):

1. ``_message_text`` -- renders a BaseMessage (incl. multimodal content
   blocks and AIMessage.tool_calls args) to a size-measurable string.
2. ``_extract_event_messages`` -- pulls the input messages out of an
   ``on_chat_model_start`` event across the v2, v1, and legacy ``prompts``
   shapes, and returns ``None`` for a payload-less event.
3. ``_log_llm_call_payload`` -- emits the ``[LLM_CALL_PAYLOAD]`` line with
   correct msg/char/byte/by_role values, includes the subagent attribution,
   and degrades to ``bytes=N/A`` without raising on malformed input.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def service() -> Any:
    """An AgentService instance with no real deps -- only helpers are used."""
    from app.ai.agent_service import AgentService

    svc = AgentService.__new__(AgentService)
    return svc


def _make_state(*, subagent: str | None = None) -> Any:
    """Build a minimal StreamState-like object for the diagnostic helpers."""
    from app.ai.graph_params import StreamState

    bus = MagicMock()
    bus.publish = MagicMock()
    # Bypass __post_init__ TokenUsageAccumulator import cost; not needed here.
    state = StreamState.__new__(StreamState)
    state.event_bus = bus
    state.session_id = MagicMock()
    state.llm_call_count = 5
    state.model_name = "glm-4.7"
    state.current_subagent_name = subagent
    return state


# ---------------------------------------------------------------------------
# _message_text
# ---------------------------------------------------------------------------


class TestMessageText:
    def test_plain_string_content(self) -> None:
        from app.ai.agent_service import _message_text

        assert _message_text(HumanMessage(content="hello")) == "hello"

    def test_multimodal_content_blocks(self) -> None:
        from app.ai.agent_service import _message_text

        msg = HumanMessage(
            content=[
                {"type": "text", "text": "describe "},
                {"type": "text", "text": "this image"},
                {"type": "image_url", "image_url": {"url": "http://x"}},
            ]
        )
        # Only the text blocks contribute; image block carries no "text".
        assert _message_text(msg) == "describe this image"

    def test_list_of_plain_strings(self) -> None:
        from app.ai.agent_service import _message_text

        msg = HumanMessage(content=["a", "b", "c"])
        assert _message_text(msg) == "abc"

    def test_ai_message_includes_tool_call_args(self) -> None:
        from app.ai.agent_service import _message_text

        msg = AIMessage(
            content="thinking",
            tool_calls=[{"name": "search", "args": {"q": "budget"}, "id": "1"}],
        )
        text = _message_text(msg)
        assert "thinking" in text
        # tool_call args text is appended and counts toward payload size.
        assert "budget" in text


# ---------------------------------------------------------------------------
# _extract_event_messages
# ---------------------------------------------------------------------------


class TestExtractEventMessages:
    def test_v2_nested_list_shape(self, service: Any) -> None:
        # astream_events v2: data["messages"] = [[SystemMessage, HumanMessage]]
        data = {
            "messages": [[SystemMessage(content="sys"), HumanMessage(content="hi")]]
        }
        msgs = service._extract_event_messages(data)
        assert msgs is not None
        assert len(msgs) == 2
        assert isinstance(msgs[0], SystemMessage)

    def test_flat_list_shape(self, service: Any) -> None:
        data = {"messages": [HumanMessage(content="hi"), AIMessage(content="hey")]}
        msgs = service._extract_event_messages(data)
        assert msgs is not None
        assert len(msgs) == 2

    def test_v1_nested_input_shape(self, service: Any) -> None:
        data = {"input": {"messages": [[HumanMessage(content="hi")]]}}
        msgs = service._extract_event_messages(data)
        assert msgs is not None
        assert len(msgs) == 1

    def test_legacy_prompts_shape(self, service: Any) -> None:
        data = {"prompts": ["hello world", "second"]}
        msgs = service._extract_event_messages(data)
        assert msgs is not None
        assert len(msgs) == 2

    def test_missing_payload_returns_none(self, service: Any) -> None:
        assert service._extract_event_messages({}) is None
        assert service._extract_event_messages({"data": {}}) is None


# ---------------------------------------------------------------------------
# _log_llm_call_payload (end-to-end line emission)
# ---------------------------------------------------------------------------


class TestLogLlmCallPayload:
    def test_emits_correct_counts_and_role_breakdown(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = _make_state()
        messages = [
            SystemMessage(content="S" * 100),
            HumanMessage(content="H" * 50),
            AIMessage(
                content="A" * 200,
                tool_calls=[{"name": "t", "args": {"x": "Y" * 10}, "id": "1"}],
            ),
            ToolMessage(content="T" * 500, tool_call_id="1"),
        ]
        data = {"messages": [messages]}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._log_llm_call_payload(state, data)

        payload_lines = [
            r.message for r in caplog.records if "LLM_CALL_PAYLOAD" in r.message
        ]
        assert len(payload_lines) == 1
        line = payload_lines[0]

        assert "#5" in line  # correlated to llm_call_count
        assert "msgs=4" in line
        # No subagent set -> no subagent attribution.
        assert "subagent=" not in line

        # All four roles present in the by_role breakdown.
        for role in ("system", "human", "ai", "tool"):
            assert f"{role}:" in line

        # bytes == total UTF-8 byte length (ASCII here, so chars == bytes for
        # the base content; tool_call args add extra). Just sanity-check it is
        # a positive integer and present.
        assert "bytes=" in line
        bytes_token = [p for p in line.split("|") if p.strip().startswith("bytes=")][0]
        bytes_val = int(bytes_token.strip().split("=")[1])
        assert bytes_val >= 100 + 50 + 200 + 500

    def test_includes_subagent_attribution(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = _make_state(subagent="project_manager")
        data = {"messages": [[HumanMessage(content="hi")]]}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._log_llm_call_payload(state, data)

        payload_lines = [
            r.message for r in caplog.records if "LLM_CALL_PAYLOAD" in r.message
        ]
        assert len(payload_lines) == 1
        assert "subagent=project_manager" in payload_lines[0]

    def test_non_ascii_counts_utf8_bytes(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = _make_state()
        # "é" is 2 bytes in UTF-8 but 1 char; "€" is 3 bytes / 1 char.
        data = {"messages": [[HumanMessage(content="é€")]]}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._log_llm_call_payload(state, data)

        payload_lines = [
            r.message for r in caplog.records if "LLM_CALL_PAYLOAD" in r.message
        ]
        line = payload_lines[0]
        assert "chars=2" in line
        assert "bytes=5" in line  # 2 + 3

    def test_missing_payload_degrades_to_na(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An event with no recognizable messages must NOT raise and must log bytes=N/A."""
        state = _make_state()

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            # Empty data dict -> no messages/prompts keys.
            service._log_llm_call_payload(state, {})

        payload_lines = [
            r.message for r in caplog.records if "LLM_CALL_PAYLOAD" in r.message
        ]
        assert len(payload_lines) == 1
        assert "bytes=N/A" in payload_lines[0]
        assert "msgs=0" in payload_lines[0]

    def test_malformed_event_does_not_raise(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A diagnostics log must never break a run -- wrap everything."""
        state = _make_state()
        # A messages list containing a non-BaseMessage junk object.
        data = {"messages": [["not a message"]]}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            # Should complete without raising.
            service._log_llm_call_payload(state, data)

        payload_lines = [
            r.message for r in caplog.records if "LLM_CALL_PAYLOAD" in r.message
        ]
        assert len(payload_lines) == 1
        # Junk object skipped -> zero messages, but still a valid line (no crash).
        assert "msgs=0" in payload_lines[0]
