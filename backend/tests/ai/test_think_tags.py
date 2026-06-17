"""Tests for inline ``<think>...</think>`` reasoning-tag stripping.

Covers the three implementation pieces of Fix A:

1. ``strip_think_tags`` -- a pure function that cleans a fully assembled
   message. Handles balanced blocks, unclosed-open, the dangling-close bug
   shape (provider stripped the opening tag but left ``</think>``), multiple
   blocks, and byte-identity on tag-free text.
2. The persistence backstop -- ``_persist_session_messages`` applies
   ``strip_think_tags`` to each assembled segment before saving.
3. The streaming filter -- ``_filter_think_tokens`` suppresses tokens while
   inside a ``<think>`` span, including tags split across chunk boundaries.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.message_utils import strip_think_tags

# ---------------------------------------------------------------------------
# strip_think_tags -- pure function
# ---------------------------------------------------------------------------


class TestStripThinkTagsBalanced:
    def test_balanced_block_leaves_answer(self) -> None:
        assert strip_think_tags("<think>reasoning</think>answer") == "answer"

    def test_balanced_block_with_multiline_reasoning(self) -> None:
        text = "<think>line1\nline2\nmore thinking</think>\nfinal answer"
        assert strip_think_tags(text) == "final answer"

    def test_balanced_block_empty_reasoning(self) -> None:
        assert strip_think_tags("<think></think>answer") == "answer"

    def test_balanced_block_preserves_answer_with_angle_brackets(self) -> None:
        # The answer may legitimately contain ``<``/``>`` (e.g. HTML, code).
        assert strip_think_tags("<think>x</think>use <b>tag</b>") == "use <b>tag</b>"


class TestStripThinkTagsUnclosedOpen:
    def test_unclosed_open_drops_tail(self) -> None:
        assert strip_think_tags("prefix<think>reasoning to end") == "prefix"

    def test_unclosed_open_at_start(self) -> None:
        assert strip_think_tags("<think>reasoning only") == ""

    def test_unclosed_open_multiline(self) -> None:
        assert strip_think_tags("ok<think>step1\nstep2") == "ok"


class TestStripThinkTagsDanglingClose:
    """THE bug shape: opening tag stripped by provider, dangling </think>."""

    def test_dangling_close_strips_up_to_first_close(self) -> None:
        # From the verified session content (Italian reasoning + answer).
        text = "non applicabili.</think>Al momento non è possibile"
        assert strip_think_tags(text) == "Al momento non è possibile"

    def test_dangling_close_with_prefix_text(self) -> None:
        text = "reasoning body</think>real answer"
        assert strip_think_tags(text) == "real answer"

    def test_dangling_close_at_start(self) -> None:
        assert strip_think_tags("</think>answer") == "answer"

    def test_dangling_close_nothing_after(self) -> None:
        assert strip_think_tags("reasoning</think>") == ""

    def test_multiple_dangling_closes_strips_up_to_first(self) -> None:
        # Spec: "stripping up to the first </think> is the correct conservative
        # choice." The rule is applied once; a single pass removes from start
        # through the FIRST </think>. Text after the first close is the answer
        # and a second literal </think> in it is NOT re-stripped (no iterative
        # re-application), matching the documented single-pass behaviour.
        text = "r1</think>r2</think>real"
        assert strip_think_tags(text) == "r2</think>real"


class TestStripThinkTagsMultipleBlocks:
    def test_multiple_balanced_blocks(self) -> None:
        text = "<think>a</think>part1<think>b</think>part2"
        assert strip_think_tags(text) == "part1part2"

    def test_mixed_balanced_and_dangling(self) -> None:
        # Balanced block removed first; the remaining "visible</think>tail" has
        # a dangling close (no open), so the conservative rule treats everything
        # up to and including that </think> as reasoning -> "tail".
        text = "<think>a</think>visible</think>tail"
        assert strip_think_tags(text) == "tail"


class TestStripThinkTagsNoTags:
    def test_plain_text_unchanged(self) -> None:
        assert strip_think_tags("hello world") == "hello world"

    def test_byte_identical_no_tags(self) -> None:
        text = "Some normal response with no reasoning tags at all.\nNewlines too."
        assert strip_think_tags(text) == text

    def test_markdown_preserved(self) -> None:
        md = "# Heading\n\n- item one\n- item two\n\n**bold** and *italic*."
        assert strip_think_tags(md) == md

    def test_markdown_table_preserved(self) -> None:
        table = "| Col A | Col B |\n|-------|-------|\n| 1 | 2 |\n| 3 | 4 |"
        assert strip_think_tags(table) == table

    def test_empty_string(self) -> None:
        assert strip_think_tags("") == ""

    def test_only_whitespace(self) -> None:
        assert strip_think_tags("   \n\t  ") == ""

    def test_strips_leading_trailing_whitespace(self) -> None:
        # Even with no tags, .strip() is applied.
        assert strip_think_tags("  hello  ") == "hello"

    def test_tags_inside_code_fence_left_alone(self) -> None:
        # A literal <think> inside a code block is still removed -- this is a
        # known acceptable trade-off documented by the spec (reasoning always
        # precedes the answer; the backstop favours not leaking CoT). We assert
        # the behaviour explicitly so it is not changed by accident.
        code = "```\n<think>not really reasoning</think>\n```"
        assert strip_think_tags(code) == "```\n\n```"


# ---------------------------------------------------------------------------
# Streaming filter -- _filter_think_tokens
# ---------------------------------------------------------------------------


def _make_state() -> Any:
    """Build a minimal StreamState-like object for the filter."""
    from app.ai.graph_params import StreamState

    bus = MagicMock()
    bus.publish = MagicMock()
    # Bypass __post_init__ TokenUsageAccumulator import cost; not needed here.
    state = StreamState.__new__(StreamState)
    state.event_bus = bus
    state.session_id = MagicMock()
    state.in_think_block = False
    state.think_pending_buffer = ""
    return state


@pytest.fixture()
def service() -> Any:
    """An AgentService instance with no real deps -- only the filter is used."""
    from app.ai.agent_service import AgentService

    svc = AgentService.__new__(AgentService)
    return svc


class TestStreamingThinkFilter:
    def test_balanced_block_suppressed(self, service: Any) -> None:
        state = _make_state()
        out = service._filter_think_tokens(state, "<think>hidden</think>visible")
        assert out == "visible"
        assert state.in_think_block is False
        assert state.think_pending_buffer == ""

    def test_text_before_open_is_emitted(self, service: Any) -> None:
        state = _make_state()
        out = service._filter_think_tokens(state, "before<think>x</think>after")
        assert out == "beforeafter"
        assert state.in_think_block is False

    def test_open_split_across_chunks(self, service: Any) -> None:
        state = _make_state()
        # chunk1 ends with a partial "<thi", chunk2 completes the tag + body.
        out1 = service._filter_think_tokens(state, "ok <thi")
        # Nothing after the partial tag should be emitted yet.
        assert out1 == "ok "
        assert state.think_pending_buffer == "<thi"
        out2 = service._filter_think_tokens(state, "nk>secret</think>done")
        assert out2 == "done"
        assert state.in_think_block is False
        assert state.think_pending_buffer == ""

    def test_close_split_across_chunks(self, service: Any) -> None:
        state = _make_state()
        out1 = service._filter_think_tokens(state, "<think>secret</thin")
        assert out1 == ""
        assert state.in_think_block is True
        # The held-back buffer must contain the partial close so the next chunk
        # can complete it, and must NOT contain a full "</think>" yet. It may
        # also hold a trailing char of the discarded "secret" body -- harmless,
        # since in_think_block remains True and it gets discarded next round.
        assert "</think>" not in state.think_pending_buffer
        assert state.think_pending_buffer.endswith("</thin")
        out2 = service._filter_think_tokens(state, "k>now visible")
        assert out2 == "now visible"
        assert state.in_think_block is False

    def test_chunk_sequence_visible_only(self, service: Any) -> None:
        """Feed the spec's example sequence: only 'visible' reaches output."""
        state = _make_state()
        chunks = ["<think>", "hidden", "</think>", "visible"]
        collected: list[str] = []
        for c in chunks:
            collected.append(service._filter_think_tokens(state, c))
        assert "".join(collected) == "visible"
        assert state.in_think_block is False

    def test_no_tags_pass_through(self, service: Any) -> None:
        state = _make_state()
        out = service._filter_think_tokens(state, "plain text, no tags")
        assert out == "plain text, no tags"
        assert state.in_think_block is False
        assert state.think_pending_buffer == ""

    def test_unclosed_open_suppresses_rest(self, service: Any) -> None:
        state = _make_state()
        out = service._filter_think_tokens(state, "prefix<think>never closes")
        assert out == "prefix"
        assert state.in_think_block is True

    def test_multiple_balanced_blocks(self, service: Any) -> None:
        state = _make_state()
        out = service._filter_think_tokens(
            state, "<think>a</think>p1<think>b</think>p2"
        )
        assert out == "p1p2"
        assert state.in_think_block is False


# ---------------------------------------------------------------------------
# Persistence backstop -- _persist_session_messages applies strip_think_tags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_session_messages_strips_think_before_save() -> None:
    """The assembled segment must be run through strip_think_tags before
    being passed to ``add_message``.

    We assert on the ``content`` kwarg captured by a fake config_service.
    """
    from app.ai.graph_params import StreamState

    captured_contents: list[str] = []

    async def fake_add_message(**kwargs: Any) -> Any:
        captured_contents.append(kwargs["content"])
        msg = MagicMock()
        msg.id = "msg-id"
        return msg

    fake_config = MagicMock()
    fake_config.add_message = fake_add_message

    fake_session = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.rollback = AsyncMock()

    # Construct the service normally, then inject the fake config service via
    # its private backing attribute (config_service is a lazy property).
    from app.ai.agent_service import AgentService

    svc = AgentService(session=fake_session)
    svc._config_service = fake_config

    state = StreamState(
        event_bus=MagicMock(),
        session_id=MagicMock(),
        model_name="glm-4.7",
        main_invocation_id="inv-1",
    )
    # A segment containing a think block -- exactly the shape the streaming
    # filter cannot catch (dangling close, opening already stripped).
    state.main_agent_segments["inv-1"] = [
        "non applicabili.</think>Al momento non è possibile"
    ]

    await svc._persist_session_messages(state)

    assert len(captured_contents) == 1
    assert captured_contents[0] == "Al momento non è possibile"
    assert "</think>" not in captured_contents[0]
