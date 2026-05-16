"""Unit tests for token usage monitoring and estimation."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.ai.token_estimator import (
    TokenUsageAccumulator,
    estimate_input_tokens,
    get_context_window_size,
    log_actual_usage,
    log_context_usage_estimate,
)

_TARGET_LOGGER = "app.ai.token_estimator"

class _LogCapture:
    """Simple log capture that attaches directly to a named logger.

    Avoids pytest caplog interference from Alembic migration logging setup
    in session-scoped fixtures that may run before these tests.
    """

    def __init__(self, logger_name: str, level: int = logging.INFO) -> None:
        self._logger = logging.getLogger(logger_name)
        self._level = level
        self._handler: logging.Handler | None = None
        self.records: list[logging.LogRecord] = []
        self._original_level: int = logging.NOTSET
        self._original_propagate: bool = True
        self._original_disabled: bool = False

    def __enter__(self) -> "_LogCapture":
        self._handler = _RecordHandler(self.records)
        self._handler.setLevel(self._level)
        self._original_level = self._logger.level
        self._original_propagate = self._logger.propagate
        self._original_disabled = self._logger.disabled
        self._logger.addHandler(self._handler)
        # Re-enable logger in case Alembic's fileConfig disabled it
        self._logger.disabled = False
        self._logger.propagate = True
        # Ensure logger level allows the desired records through
        if self._original_level > self._level or self._original_level == logging.NOTSET:
            self._logger.setLevel(self._level)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._handler:
            self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._original_level)
        self._logger.propagate = self._original_propagate
        self._logger.disabled = self._original_disabled

    @property
    def text(self) -> str:
        return "\n".join(r.getMessage() for r in self.records)

class _RecordHandler(logging.Handler):
    """Handler that appends LogRecords to a list."""

    def __init__(self, records: list[logging.LogRecord]) -> None:
        super().__init__()
        self._records = records

    def emit(self, record: logging.LogRecord) -> None:
        self._records.append(record)

class TestEstimateInputTokens:
    """Test suite for estimate_input_tokens function."""

    def test_estimate_basic_message(self) -> None:
        """400-char HumanMessage returns 100 tokens (chars/4)."""
        msg = HumanMessage(content="a" * 400)
        result = estimate_input_tokens([msg])
        assert result == 100

    def test_estimate_empty_messages(self) -> None:
        """Empty message list returns 0."""
        result = estimate_input_tokens([])
        assert result == 0

    def test_estimate_mixed_message_types(self) -> None:
        """List of mixed message types sums all content lengths / 4."""
        messages: list[BaseMessage] = [
            SystemMessage(content="a" * 100),
            HumanMessage(content="b" * 200),
            AIMessage(content="c" * 300),
        ]
        result = estimate_input_tokens(messages)
        assert result == 150  # (100 + 200 + 300) / 4

    def test_estimate_list_content_type(self) -> None:
        """Messages with list content (multimodal) are handled."""
        msg = HumanMessage(
            content=[{"type": "text", "text": "hello world"}]  # type: ignore[arg-type]
        )
        result = estimate_input_tokens([msg])
        # list content -> len(str(...)) / 4
        assert result >= 0

    def test_estimate_single_char_message(self) -> None:
        """1-char message returns 0 (integer division)."""
        msg = HumanMessage(content="a")
        result = estimate_input_tokens([msg])
        assert result == 0

class TestGetContextWindowSize:
    """Test suite for get_context_window_size function."""

    def test_known_models_return_window_size(self) -> None:
        """Known models return their context window size."""
        assert get_context_window_size("gpt-4o") == 128_000
        assert get_context_window_size("gpt-4o-mini") == 128_000
        assert get_context_window_size("gpt-4.1") == 1_047_576
        assert get_context_window_size("gpt-4.1-mini") == 1_047_576
        assert get_context_window_size("gpt-4.1-nano") == 1_047_576
        assert get_context_window_size("o3") == 200_000
        assert get_context_window_size("o4-mini") == 200_000

    def test_unknown_model_returns_none(self) -> None:
        """Unknown models return None."""
        assert get_context_window_size("claude-3") is None
        assert get_context_window_size("nonexistent") is None

    def test_case_sensitive_lookup(self) -> None:
        """Lookup is case-sensitive."""
        assert get_context_window_size("GPT-4o") is None
        assert get_context_window_size("gpt-4O") is None

class TestLogContextUsageEstimate:
    """Test suite for log_context_usage_estimate function."""

    def test_log_contains_required_fields(self) -> None:
        """Log contains all required fields."""
        messages = [HumanMessage(content="a" * 400)]
        with _LogCapture(_TARGET_LOGGER) as capture:
            result = log_context_usage_estimate(
                messages=messages,
                model_name="gpt-4o",
                session_id="sess-123",
                execution_id="exec-456",
            )

        assert result == 100  # Returns estimated tokens
        assert "[CONTEXT_USAGE_ESTIMATE]" in capture.text
        assert "session_id=sess-123" in capture.text
        assert "execution_id=exec-456" in capture.text
        assert "model=gpt-4o" in capture.text
        assert "estimated_input_tokens=100" in capture.text
        assert "context_window_size=128000" in capture.text
        assert "usage_percentage=" in capture.text

    def test_log_format_matches_convention(self) -> None:
        """Log uses pipe-separated key=value format."""
        messages = [HumanMessage(content="test")]
        with _LogCapture(_TARGET_LOGGER) as capture:
            log_context_usage_estimate(
                messages=messages,
                model_name="gpt-4o",
                session_id="s1",
                execution_id="e1",
            )

        assert " | " in capture.text

    def test_log_unknown_model(self) -> None:
        """Unknown model logs context_window_size=unknown and usage_percentage=N/A."""
        messages = [HumanMessage(content="test")]
        with _LogCapture(_TARGET_LOGGER) as capture:
            log_context_usage_estimate(
                messages=messages,
                model_name="unknown-model",
                session_id="s1",
                execution_id="e1",
            )

        assert "context_window_size=unknown" in capture.text
        assert "usage_percentage=N/A" in capture.text

class TestAccumulateUsageFromEvent:
    """Test suite for TokenUsageAccumulator.accumulate_from_event."""

    def test_accumulate_single_event_langchain_format(self) -> None:
        """Single event with LangChain usage_metadata updates accumulator."""
        acc = TokenUsageAccumulator()
        event_data: dict[str, object] = {
            "output": AIMessage(
                content="test",
                usage_metadata={
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "total_tokens": 700,
                },
            ),
        }
        acc.accumulate_from_event(event_data)
        assert acc.prompt_tokens == 500
        assert acc.completion_tokens == 200

    def test_accumulate_multiple_events(self) -> None:
        """Multiple events accumulate correctly."""
        acc = TokenUsageAccumulator()
        for _ in range(3):
            event_data: dict[str, object] = {
                "output": AIMessage(
                    content="test",
                    usage_metadata={
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_tokens": 150,
                    },
                ),
            }
            acc.accumulate_from_event(event_data)

        assert acc.prompt_tokens == 300
        assert acc.completion_tokens == 150

    def test_accumulate_event_without_usage_metadata(self) -> None:
        """Event with missing usage_metadata leaves accumulator unchanged."""
        acc = TokenUsageAccumulator()
        event_data: dict[str, object] = {
            "output": AIMessage(content="test"),
        }
        acc.accumulate_from_event(event_data)
        assert acc.prompt_tokens == 0
        assert acc.completion_tokens == 0

    def test_accumulate_event_with_empty_output(self) -> None:
        """Event with no output field leaves accumulator unchanged."""
        acc = TokenUsageAccumulator()
        acc.accumulate_from_event({})
        assert acc.prompt_tokens == 0
        assert acc.completion_tokens == 0

    def test_accumulate_openai_format(self) -> None:
        """Event with OpenAI response_metadata format."""
        acc = TokenUsageAccumulator()
        event_data: dict[str, object] = {
            "output": AIMessage(
                content="test",
                response_metadata={
                    "token_usage": {
                        "prompt_tokens": 300,
                        "completion_tokens": 100,
                    },
                },
            ),
        }
        acc.accumulate_from_event(event_data)
        assert acc.prompt_tokens == 300
        assert acc.completion_tokens == 100

    def test_accumulate_langchain_preferred_over_openai(self) -> None:
        """LangChain usage_metadata takes priority over OpenAI response_metadata."""
        acc = TokenUsageAccumulator()
        event_data: dict[str, object] = {
            "output": AIMessage(
                content="test",
                usage_metadata={
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                },
                response_metadata={
                    "token_usage": {
                        "prompt_tokens": 999,
                        "completion_tokens": 888,
                    },
                },
            ),
        }
        acc.accumulate_from_event(event_data)
        assert acc.prompt_tokens == 10
        assert acc.completion_tokens == 5

class TestLogActualUsage:
    """Test suite for log_actual_usage function."""

    def test_log_contains_required_fields(self) -> None:
        """Log contains all required fields."""
        acc = TokenUsageAccumulator()
        event_data: dict[str, object] = {
            "output": AIMessage(
                content="test",
                usage_metadata={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                },
            ),
        }
        acc.accumulate_from_event(event_data)

        with _LogCapture(_TARGET_LOGGER) as capture:
            log_actual_usage(
                accumulator=acc,
                model_name="gpt-4o",
                session_id="sess-123",
                execution_id="exec-456",
            )

        assert "[CONTEXT_USAGE_ACTUAL]" in capture.text
        assert "session_id=sess-123" in capture.text
        assert "execution_id=exec-456" in capture.text
        assert "model=gpt-4o" in capture.text
        assert "prompt_tokens=100" in capture.text
        assert "completion_tokens=50" in capture.text
        assert "total_tokens=150" in capture.text

    def test_log_with_zero_usage(self) -> None:
        """Log works with zero usage (no API data captured)."""
        acc = TokenUsageAccumulator()
        with _LogCapture(_TARGET_LOGGER) as capture:
            log_actual_usage(
                accumulator=acc,
                model_name="gpt-4o",
                session_id="s1",
                execution_id="e1",
            )

        assert "[CONTEXT_USAGE_ACTUAL]" in capture.text
        assert "prompt_tokens=0" in capture.text
        assert "completion_tokens=0" in capture.text
        assert "total_tokens=0" in capture.text

class TestTokenUsageAccumulator:
    """Test suite for TokenUsageAccumulator dataclass."""

    def test_initial_state_is_zero(self) -> None:
        """Newly created accumulator has zero tokens."""
        acc = TokenUsageAccumulator()
        assert acc.prompt_tokens == 0
        assert acc.completion_tokens == 0

    def test_to_dict_returns_correct_structure(self) -> None:
        """to_dict returns expected keys and computed total."""
        acc = TokenUsageAccumulator()
        event_data: dict[str, object] = {
            "output": AIMessage(
                content="test",
                usage_metadata={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                },
            ),
        }
        acc.accumulate_from_event(event_data)
        result = acc.to_dict()

        assert result == {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

    def test_to_dict_empty_accumulator(self) -> None:
        """to_dict with no accumulated data returns all zeros."""
        acc = TokenUsageAccumulator()
        result = acc.to_dict()

        assert result == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
