"""Tests for Phase-0 per-LLM-call usage instrumentation.

Covers:

1. ``estimate_tools_token_cost`` -- the tool-definition token heuristic in
   ``app.ai.message_utils`` (empty -> 0; fake tools -> sensible positive int;
   a tool that fails conversion is skipped, never raises).
2. ``_handle_chat_model_end`` -- emits exactly one ``[LLM_CALL_USAGE]`` line
   with the right prompt/completion tokens when ``usage`` is present, and
   degrades to ``N/A`` (still emitting one line, never raising) when
   ``usage`` is absent.
3. ``_extract_call_usage`` -- per-call extraction mirrors the accumulator and
   returns ``(None, None)`` for a payload-less event.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def service() -> Any:
    """An AgentService instance with no real deps -- only helpers are used."""
    from app.ai.agent_service import AgentService

    svc = AgentService.__new__(AgentService)
    return svc


def _make_state(
    *,
    subagent: str | None = None,
    llm_call_count: int = 7,
    planner_active: bool = False,
) -> Any:
    """Build a minimal StreamState-like object for the diagnostic helpers."""
    from app.ai.graph_params import StreamState

    bus = MagicMock()
    bus.publish = MagicMock()
    # Bypass __post_init__ TokenUsageAccumulator import cost; not needed here.
    state = StreamState.__new__(StreamState)
    state.event_bus = bus
    state.session_id = MagicMock()
    state.llm_call_count = llm_call_count
    state.model_name = "glm-4.7"
    state.current_subagent_name = subagent
    state.planner_active = planner_active
    state.all_tool_calls = []
    state.all_tool_results = []
    state.tool_calls_count = 0
    state.llm_call_start = None
    # accumulate_from_event is called inside _handle_chat_model_end; stub it so
    # we don't need a real TokenUsageAccumulator.
    state.token_accumulator = MagicMock()
    return state


def _fake_tool(name: str) -> Any:
    """Build a minimal StructuredTool with a real pydantic schema."""

    class _Args(BaseModel):
        query: str = Field(description="The search query")

    async def _run(query: str) -> str:  # pragma: no cover -- never invoked
        return f"result for {query}"

    return StructuredTool.from_function(
        coroutine=_run,
        name=name,
        description=f"Search the index for {name}.",
        args_schema=_Args,
    )


# ---------------------------------------------------------------------------
# estimate_tools_token_cost
# ---------------------------------------------------------------------------


class TestEstimateToolsTokenCost:
    def test_empty_list_is_zero(self) -> None:
        from app.ai.message_utils import estimate_tools_token_cost

        assert estimate_tools_token_cost([]) == 0

    def test_fake_tools_yield_positive_int(self) -> None:
        from app.ai.message_utils import estimate_tools_token_cost

        tools = [_fake_tool("search_docs"), _fake_tool("get_project")]
        cost = estimate_tools_token_cost(tools)
        # Each tool's OpenAI schema (name, description, args with a field) is
        # comfortably > a few hundred chars -> at least a few dozen tokens.
        assert isinstance(cost, int)
        assert cost > 0

    def test_more_tools_cost_more(self) -> None:
        """Token cost is monotonic in the number of bound tools."""
        from app.ai.message_utils import estimate_tools_token_cost

        one = estimate_tools_token_cost([_fake_tool("a")])
        three = estimate_tools_token_cost(
            [_fake_tool("a"), _fake_tool("b"), _fake_tool("c")]
        )
        assert three > one

    def test_bad_tool_does_not_raise(self) -> None:
        """A tool that fails conversion is skipped; the helper never raises."""
        from app.ai.message_utils import estimate_tools_token_cost

        class _Broken:
            pass

        # The broken object should be skipped; the valid tool still counts.
        cost = estimate_tools_token_cost([_Broken(), _fake_tool("ok")])  # type: ignore[list-item]
        assert cost > 0


# ---------------------------------------------------------------------------
# _extract_call_usage
# ---------------------------------------------------------------------------


class TestExtractCallUsage:
    def test_usage_metadata_on_aimessage(self, service: Any) -> None:
        msg = AIMessage(
            content="hi",
            usage_metadata={
                "input_tokens": 123,
                "output_tokens": 45,
                "total_tokens": (123) + (45),
            },
        )
        prompt, completion = service._extract_call_usage({"output": msg})
        assert prompt == 123
        assert completion == 45

    def test_response_metadata_token_usage(self, service: Any) -> None:
        msg = AIMessage(
            content="hi",
            response_metadata={
                "token_usage": {"prompt_tokens": 200, "completion_tokens": 30}
            },
        )
        prompt, completion = service._extract_call_usage({"output": msg})
        assert prompt == 200
        assert completion == 30

    def test_v1_generations_shape(self, service: Any) -> None:
        msg = AIMessage(
            content="hi",
            usage_metadata={
                "input_tokens": 9,
                "output_tokens": 1,
                "total_tokens": (9) + (1),
            },
        )
        data = {"output": {"generations": [[{"message": msg}]]}}
        prompt, completion = service._extract_call_usage(data)
        assert prompt == 9
        assert completion == 1

    def test_missing_output_returns_none_pair(self, service: Any) -> None:
        prompt, completion = service._extract_call_usage({})
        assert prompt is None
        assert completion is None

    def test_no_usage_returns_none_pair(self, service: Any) -> None:
        msg = AIMessage(content="hi")  # no usage_metadata / response_metadata
        prompt, completion = service._extract_call_usage({"output": msg})
        assert prompt is None
        assert completion is None


# ---------------------------------------------------------------------------
# _handle_chat_model_end -> [LLM_CALL_USAGE]
# ---------------------------------------------------------------------------


class TestHandleChatModelEndUsageLine:
    def test_emits_usage_line_with_tokens(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = _make_state()
        msg = AIMessage(
            content="hi",
            usage_metadata={
                "input_tokens": 4815,
                "output_tokens": 162,
                "total_tokens": (4815) + (162),
            },
        )
        event = {"data": {"output": msg}}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._handle_chat_model_end(state, event)

        usage_lines = [
            r.message for r in caplog.records if "LLM_CALL_USAGE" in r.message
        ]
        assert len(usage_lines) == 1
        line = usage_lines[0]
        assert "#7" in line  # llm_call_count
        assert "agent=supervisor" in line
        assert "prompt_tokens=4815" in line
        assert "completion_tokens=162" in line

    def test_specialist_label(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = _make_state(subagent="project_manager")
        msg = AIMessage(
            content="hi",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 2,
                "total_tokens": (10) + (2),
            },
        )
        event = {"data": {"output": msg}}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._handle_chat_model_end(state, event)

        usage_lines = [
            r.message for r in caplog.records if "LLM_CALL_USAGE" in r.message
        ]
        assert len(usage_lines) == 1
        assert "agent=specialist:project_manager" in usage_lines[0]

    def test_no_usage_emits_line_with_na(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing usage must NOT raise and must log prompt_tokens=N/A."""
        state = _make_state()
        msg = AIMessage(content="hi")  # no usage
        event = {"data": {"output": msg}}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            # Must not raise.
            service._handle_chat_model_end(state, event)

        usage_lines = [
            r.message for r in caplog.records if "LLM_CALL_USAGE" in r.message
        ]
        assert len(usage_lines) == 1
        assert "prompt_tokens=N/A" in usage_lines[0]
        assert "completion_tokens=N/A" in usage_lines[0]

    def test_missing_output_does_not_raise(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = _make_state()
        event = {"data": {}}  # no output key at all

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._handle_chat_model_end(state, event)

        usage_lines = [
            r.message for r in caplog.records if "LLM_CALL_USAGE" in r.message
        ]
        assert len(usage_lines) == 1
        assert "prompt_tokens=N/A" in usage_lines[0]

    def test_accumulated_tool_msgs_counted(
        self, service: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Supervisor-stream tool results are counted in the usage line."""
        state = _make_state()
        state.all_tool_results = [
            {"tool": "get_project", "result": "x" * 400},
            {"tool": "global_search", "result": "y" * 80},
        ]
        msg = AIMessage(
            content="hi",
            usage_metadata={
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": (1) + (1),
            },
        )
        event = {"data": {"output": msg}}

        with caplog.at_level(logging.INFO, logger="app.ai.agent_service"):
            service._handle_chat_model_end(state, event)

        line = [r.message for r in caplog.records if "LLM_CALL_USAGE" in r.message][0]
        assert "accumulated_tool_msgs=2" in line
        # 480 chars -> 120 estimated tokens.
        assert "chars=480" in line
        assert "est_tokens=120" in line
