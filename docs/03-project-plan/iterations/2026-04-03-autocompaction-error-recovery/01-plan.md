# Plan: Pre-emptive History Compaction with Reactive Fallback

**Created:** 2026-04-03
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Option 1 (Pre-emptive History Compaction) + Option 2 element (reactive fallback)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 (Pre-emptive History Compaction) as the primary mechanism, with a targeted reactive fallback (Option 2 element) for estimation misses.
- **Architecture**: A new `HistoryCompactor` module in `backend/app/ai/context/` that estimates token count after `_build_conversation_history()` returns, compacts if approaching the model's context window limit, and also catches `BadRequestError` with `context_length_exceeded` during graph invocation to retry once with compaction.
- **Key Decisions**:
  1. Use the **same LLM model** as the session to generate summaries (per user decision).
  2. **Pre-emptive compaction** runs BEFORE graph invocation (primary mechanism).
  3. **Reactive fallback** catches `openai.BadRequestError` with `context_length_exceeded` and retries once (safety net for token estimation inaccuracies).
  4. Token counting via `tiktoken` (already installed in the virtual environment).
  5. Model context window sizes resolved from a static lookup table keyed by model name (no DB migration).
  6. Preserve last **6 turns** (3 user + 3 assistant) verbatim during compaction.
  7. No DB schema changes -- compaction is purely in-memory history manipulation.
  8. No frontend changes required.

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: When conversation history exceeds 80% of the model's context window, the compactor summarizes older messages into a `SystemMessage` and preserves the last 6 turns verbatim VERIFIED BY: unit test
- [ ] FC-2: When conversation history is below the threshold, the compactor returns the history unchanged with zero modifications VERIFIED BY: unit test
- [ ] FC-3: When the pre-emptive check misses and `openai.BadRequestError` with `context_length_exceeded` is raised, the reactive fallback catches it, compacts, and retries once VERIFIED BY: unit test
- [ ] FC-4: After compaction, the LLM continues the conversation coherently without losing awareness of earlier topics VERIFIED BY: integration test
- [ ] FC-5: Both `_run_agent_graph()` (streaming) and `chat()` (synchronous) execution paths are protected VERIFIED BY: code inspection + unit test
- [ ] FC-6: Compaction failures (LLM summarization error) are caught, logged, and fall through to existing error handling without crashing VERIFIED BY: unit test

**Technical Criteria:**

- [ ] TC-1: Performance: Token counting adds < 50ms to non-compaction invocations VERIFIED BY: timing assertion in unit test
- [ ] TC-2: Code Quality: mypy strict + ruff clean on all new/modified files VERIFIED BY: `uv run ruff check . && uv run mypy app/`
- [ ] TC-3: Test coverage >= 80% on new module `backend/app/ai/context/` VERIFIED BY: `uv run pytest --cov=app/ai/context`
- [ ] TC-4: No changes to `AgentState`, `graph.py`, event bus, or DB schema VERIFIED BY: diff review

**TDD Criteria:**

- [ ] All tests written **before** implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage >= 80% on the new module
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- New module: `backend/app/ai/context/history_compactor.py` -- token estimation, context window lookup, summarization logic
- New module: `backend/app/ai/context/__init__.py` -- package init
- Modify: `backend/app/ai/agent_service.py` -- integrate compactor into `_run_agent_graph()` and `_chat_impl()`
- New tests: `backend/tests/unit/ai/test_history_compactor.py`
- New tests: `backend/tests/unit/ai/test_agent_service_compaction.py`

**Out of Scope:**

- Frontend changes (no "compressing..." indicator -- deferred to future iteration)
- DB migration for persistent summary (Option 3 -- future iteration)
- Per-model configurable threshold in `AIModel` table
- Subagent-level compaction (subagents have their own context management)
- Incremental / persistent summarization

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Create `context` package with `__init__.py` | `backend/app/ai/context/__init__.py` | none | Package imports cleanly | Low |
| 2 | Implement `get_model_context_window()` -- static lookup of model name to token limit | `backend/app/ai/context/history_compactor.py` | task 1 | Returns correct limits for known models; returns safe default (128000) for unknown | Low |
| 3 | Implement `count_message_tokens()` -- tiktoken-based token counting for a list of BaseMessage | `backend/app/ai/context/history_compactor.py` | task 1 | Token counts are within +/-5% of actual OpenAI tokenization for test messages | Low |
| 4 | Implement `compact_history()` -- summarize older messages, preserve last N turns | `backend/app/ai/context/history_compactor.py` | tasks 2, 3 | Output is `[SystemMessage(summary), ...last_N_messages]`; summary preserves key facts; total tokens < threshold | Med |
| 5 | Implement `HistoryCompactor.should_compact()` -- threshold check | `backend/app/ai/context/history_compactor.py` | tasks 2, 3 | Returns `True` when tokens > 80% of window; `False` otherwise | Low |
| 6 | Implement `HistoryCompactor.compact()` -- full orchestration (check + summarize) | `backend/app/ai/context/history_compactor.py` | tasks 4, 5 | Returns compacted history or original if under threshold | Med |
| 7 | Implement `is_context_overflow_error()` -- detect `BadRequestError` with `context_length_exceeded` | `backend/app/ai/context/history_compactor.py` | task 1 | Returns `True` for the specific error pattern; `False` for all other errors | Low |
| 8 | Integrate pre-emptive compaction into `_run_agent_graph()` after line 656 (after system prompt insertion) | `backend/app/ai/agent_service.py` | task 6 | History is compacted before graph invocation; graph receives compacted history | Med |
| 9 | Integrate pre-emptive compaction into `_chat_impl()` after line 491 (after system prompt insertion) | `backend/app/ai/agent_service.py` | task 6 | History is compacted before graph invocation; graph receives compacted history | Low |
| 10 | Integrate reactive fallback in `_run_agent_graph()` error handling around line 1064 | `backend/app/ai/agent_service.py` | tasks 7, 8 | On `context_length_exceeded` error, compacts and retries once; publishes recovery event to event bus | High |
| 11 | Write unit tests for `history_compactor.py` | `backend/tests/unit/ai/test_history_compactor.py` | task 6 | All FC-1 through FC-6 covered; >= 80% coverage | Med |
| 12 | Write integration tests for agent_service compaction integration | `backend/tests/unit/ai/test_agent_service_compaction.py` | tasks 8, 9, 10 | Integration between compactor and agent_service verified | Med |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FC-1: Compaction when over threshold | T-001 | `tests/unit/ai/test_history_compactor.py` | `compact()` returns `[SystemMessage(summary)] + last_6_messages`, total tokens < 80% threshold |
| FC-2: No-op when under threshold | T-002 | `tests/unit/ai/test_history_compactor.py` | `compact()` returns original list unchanged when tokens < threshold |
| FC-3: Reactive fallback catches overflow | T-003 | `tests/unit/ai/test_history_compactor.py` | `is_context_overflow_error()` returns `True` for BadRequestError with context_length_exceeded code |
| FC-4: Coherent continuation after compaction | T-004 | `tests/unit/ai/test_history_compactor.py` | Summary SystemMessage contains key facts from compacted messages |
| FC-5: Both execution paths protected | T-005 | `tests/unit/ai/test_agent_service_compaction.py` | Both `_run_agent_graph` and `_chat_impl` call compactor |
| FC-6: Compaction failure graceful | T-006 | `tests/unit/ai/test_history_compactor.py` | When LLM raises during summarization, original history returned, error logged |
| TC-1: Token counting performance | T-007 | `tests/unit/ai/test_history_compactor.py` | Token counting for 50 messages completes in < 50ms |

---

## Implementation Details

### File: `backend/app/ai/context/__init__.py`

Empty package init. Exports `HistoryCompactor` from `history_compactor` module.

### File: `backend/app/ai/context/history_compactor.py`

This is the core new module. It contains:

#### 1. `MODEL_CONTEXT_WINDOWS` -- Static Lookup Table

```python
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "o1": 200000,
    "o1-mini": 128000,
    "o3-mini": 200000,
    "gpt-3.5-turbo": 16385,
}
DEFAULT_CONTEXT_WINDOW = 128000
```

Function `get_model_context_window(model_name: str) -> int`:
- Normalize model name (lowercase, strip whitespace).
- Match against keys using prefix matching (e.g., "gpt-4o-2024-08-06" matches "gpt-4o").
- Return `DEFAULT_CONTEXT_WINDOW` for unknown models.

#### 2. `count_message_tokens(messages: list[BaseMessage], model: str) -> int`

- Use `tiktoken` with encoding `cl100k_base` (covers GPT-4 family).
- Count tokens for each message, accounting for the per-message overhead (approximately 4 tokens for role/formatting).
- Return total token count.

#### 3. `COMPACT_SYSTEM_PROMPT` -- Summarization Prompt Template

```
You are a conversation summarizer. Your task is to create a concise but comprehensive summary of the conversation history below.

Requirements:
- Preserve all key facts, decisions, and numerical data mentioned.
- Preserve the user's intent and any specific requests.
- Preserve any project IDs, WBE codes, cost element codes, or other domain identifiers.
- Preserve tool call results that contain important data.
- Be concise but do not lose critical context.
- Write in plain text, not markdown.
- Keep the summary under 1000 tokens.

Conversation to summarize:
---
{conversation_text}
---

Provide a concise summary that captures all essential context for continuing this conversation.
```

#### 4. `HistoryCompactor` Class

```python
class HistoryCompactor:
    def __init__(
        self,
        llm: ChatOpenAI,
        model_name: str,
        threshold_ratio: float = 0.8,
        recent_turns_to_keep: int = 6,
    ): ...

    def should_compact(self, messages: list[BaseMessage]) -> bool: ...

    async def compact(self, messages: list[BaseMessage]) -> list[BaseMessage]: ...

    async def _summarize_messages(self, messages: list[BaseMessage]) -> str: ...
```

**`should_compact(messages)`**:
- Count tokens in `messages`.
- Compare against `threshold_ratio * get_model_context_window(model_name)`.
- Return `True` if over threshold.

**`compact(messages)`**:
- If `should_compact()` returns `False`, return `messages` unchanged.
- Split messages: `messages_to_compact = messages[:-recent_turns_to_keep]`, `recent_messages = messages[-recent_turns_to_keep:]`.
- If `messages_to_compact` is empty (too few messages), return `messages` unchanged.
- Call `_summarize_messages(messages_to_compact)`.
- Build result: `[SystemMessage(content=f"[Conversation Summary]\n{summary}")] + recent_messages`.
- Log compaction event: original token count, new token count, messages compacted.

**`_summarize_messages(messages)`**:
- Format messages into a readable conversation string.
- Create summarization prompt from `COMPACT_SYSTEM_PROMPT` template.
- Call `await self.llm.ainvoke([SystemMessage(content=prompt)])` (synchronous LLM call, not streamed).
- Extract text content from the response.
- On error, log warning and return a fallback summary: "Previous conversation had {N} messages covering various topics."
- Wrap in try/except to never crash.

#### 5. `is_context_overflow_error(error: Exception) -> bool`

- Check if `error` is an instance of `openai.BadRequestError`.
- Check if `error.status_code == 400`.
- Check if error body contains `context_length_exceeded` in the error code.
- Return `True` only if all conditions match.

### File: `backend/app/ai/agent_service.py` -- Modifications

#### Modification 1: Pre-emptive compaction in `_run_agent_graph()` (after line 656)

After `history.insert(0, SystemMessage(content=system_prompt))` at line 656, insert:

```python
# Pre-emptive history compaction
from app.ai.context import HistoryCompactor

compactor = HistoryCompactor(
    llm=llm,
    model_name=model_name,
)
if compactor.should_compact(history):
    logger.info(
        f"[PRE_EMPTIVE_COMPACTION] Compacting history for session {session_id} | "
        f"model={model_name}"
    )
    history = await compactor.compact(history)
```

This runs after the LLM client is created (line 664-669) but before graph invocation (line 783).

#### Modification 2: Pre-emptive compaction in `_chat_impl()` (after line 491)

After `history.insert(0, SystemMessage(content=system_prompt))` at line 491, insert:

```python
# Pre-emptive history compaction
from app.ai.context import HistoryCompactor

compactor = HistoryCompactor(
    llm=llm,
    model_name=model_name,
)
if compactor.should_compact(history):
    logger.info(
        f"[PRE_EMPTIVE_COMPACTION] Compacting history for session {session_id} | "
        f"model={model_name}"
    )
    history = await compactor.compact(history)
```

#### Modification 3: Reactive fallback in `_run_agent_graph()` error handling (line 1064)

Replace the current bare `except Exception as e:` block at line 1064 with:

```python
except Exception as e:
    # Check for context overflow -- reactive fallback
    if is_context_overflow_error(e):
        logger.warning(
            f"[REACTIVE_COMPACTION] Context overflow detected for session {session_id} | "
            f"Retrying with compacted history"
        )
        try:
            # Compact with a more aggressive threshold
            compactor = HistoryCompactor(
                llm=llm,
                model_name=model_name,
                threshold_ratio=0.5,  # More aggressive for retry
                recent_turns_to_keep=4,  # Fewer turns kept
            )
            history = await compactor.compact(history)

            # Publish recovery event
            _publish(
                "info",
                {"message": "Recovering from context overflow...", "type": "compaction"},
            )

            # Retry the graph invocation with compacted history
            async for event in graph.astream_events(
                {
                    "messages": history,
                    "tool_call_count": 0,
                    "max_tool_iterations": recursion_limit,
                    "next": "agent",
                },
                config={
                    "recursion_limit": recursion_limit,
                    "configurable": {"thread_id": str(session_id)},
                },
                version="v1",
                context=BackcastRuntimeContext(
                    user_id=str(user_id),
                    user_role=user_role,
                    project_id=str(project_id) if project_id else None,
                    branch_id=str(branch_id) if branch_id else None,
                    execution_mode=execution_mode.value,
                ),
            ):
                # ... (same event handling logic as the original try block,
                #      extracted into a helper to avoid duplication)
                pass
        except Exception as retry_error:
            logger.error(
                f"[REACTIVE_COMPACTION_FAILED] Retry also failed: {retry_error}",
                exc_info=True,
            )
            event_bus.publish(
                AgentEvent(
                    event_type="error",
                    data={"message": str(retry_error), "code": 500},
                    timestamp=datetime.now(),
                )
            )
    else:
        logger.error(f"Error in _run_agent_graph: {e}", exc_info=True)
        event_bus.publish(
            AgentEvent(
                event_type="error",
                data={"message": str(e), "code": 500},
                timestamp=datetime.now(),
            )
        )
```

**Important design note on the reactive fallback**: The streaming event handling logic (lines 803-1058) is large. To avoid duplication, this plan specifies that the DO phase should extract the event handling into a private helper method `_process_stream_events()` that takes the async generator and processes all events. Both the original try block and the retry block call this same helper. This is a refactoring step that simplifies the reactive fallback without changing any event handling behavior.

### File: `backend/tests/unit/ai/test_history_compactor.py`

New test file for the compactor module.

### File: `backend/tests/unit/ai/test_agent_service_compaction.py`

New test file verifying the integration between agent_service and the compactor.

---

## Compaction Prompt Template

The summarization prompt is defined in section 4.3 above as `COMPACT_SYSTEM_PROMPT`. Key design choices:

1. **Explicit instruction to preserve domain identifiers**: Project IDs, WBE codes, cost element codes -- these are critical for tool calls to work correctly after compaction.
2. **Token budget constraint**: "Keep the summary under 1000 tokens" -- this ensures the summary itself does not contribute significantly to context overflow.
3. **Plain text output**: Avoids markdown formatting tokens that waste the budget.
4. **Fallback summary**: If summarization fails, a minimal fallback is generated from message metadata only.

---

## Test Specification

### Test Hierarchy

```
tests/
  unit/
    ai/
      test_history_compactor.py        # Core compactor unit tests
        -- token counting
        -- threshold detection
        -- compaction logic
        -- summarization
        -- error handling
        -- reactive error detection
      test_agent_service_compaction.py  # Integration with agent_service
        -- pre-emptive path (_run_agent_graph)
        -- pre-emptive path (_chat_impl)
        -- reactive fallback path
        -- no-op path (under threshold)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_compact_returns_summary_and_recent_turns` | FC-1 | Unit | Output starts with SystemMessage containing summary, followed by exactly 6 recent messages |
| T-002 | `test_compact_noop_when_under_threshold` | FC-2 | Unit | When tokens < 80% threshold, returns original list by identity (same object) |
| T-003 | `test_compact_noop_when_few_messages` | FC-2 | Unit | When message count <= recent_turns_to_keep, returns original list |
| T-004 | `test_is_context_overflow_error_true_for_bad_request` | FC-3 | Unit | Returns True for BadRequestError with status 400 and context_length_exceeded code |
| T-005 | `test_is_context_overflow_error_false_for_other_errors` | FC-3 | Unit | Returns False for generic Exception, RateLimitError, APIConnectionError |
| T-006 | `test_compact_summary_preserves_domain_data` | FC-4 | Unit | Mock LLM returns summary; verify summary prompt includes domain data instructions |
| T-007 | `test_compact_failure_returns_original_history` | FC-6 | Unit | When mock LLM raises during summarization, original history returned |
| T-008 | `test_count_message_tokens_returns_positive_int` | TC-1 | Unit | Token count is > 0 for non-empty message list |
| T-009 | `test_count_message_tokens_performance` | TC-1 | Unit | 50 messages counted in < 50ms |
| T-010 | `test_get_model_context_window_known_models` | FC-1 | Unit | Known models return expected values; unknown returns 128000 |
| T-011 | `test_get_model_context_window_dated_variants` | FC-1 | Unit | "gpt-4o-2024-08-06" matches "gpt-4o" and returns 128000 |
| T-012 | `test_run_agent_graph_calls_compactor_when_over_threshold` | FC-5 | Unit | Mock compactor.should_compact returns True; verify compact() is called |
| T-013 | `test_run_agent_graph_skips_compactor_when_under_threshold` | FC-5 | Unit | Mock compactor.should_compact returns False; verify compact() is NOT called |
| T-014 | `test_chat_impl_calls_compactor_when_over_threshold` | FC-5 | Unit | Same as T-012 but for `_chat_impl` path |
| T-015 | `test_reactive_fallback_retries_on_overflow_error` | FC-3 | Unit | Mock graph raises context overflow; verify retry with compacted history |
| T-016 | `test_reactive_fallback_does_not_retry_other_errors` | FC-3 | Unit | Mock graph raises generic error; verify no retry, error propagated |

### Test Infrastructure Needs

- **Fixtures needed**: Mock `ChatOpenAI` that returns predetermined summaries; mock `AgentEventBus`; mock graph that raises specific errors.
- **Mocks/stubs**: `tiktoken` encoding (use real tiktoken, it is deterministic); `openai.BadRequestError` instances with specific error bodies.
- **Database state**: No database needed for compactor unit tests. Agent service integration tests may need `db_session` fixture for session creation.

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Token counting via tiktoken may not exactly match OpenAI's server-side counting, causing false negatives (overflow not caught) | Medium | High | Reactive fallback catches misses; use 80% threshold (conservative margin) |
| Technical | Summarization quality degrades for very long conversations (50+ turns), losing critical context | Low | Medium | Prompt explicitly instructs preservation of domain identifiers; fallback summary provides minimal context |
| Technical | Compaction adds latency (~2-5s) when triggered, which may cause WebSocket timeout | Low | Medium | Publish "info" event before compaction; timeout is typically 60s |
| Integration | Reactive fallback duplicates large event-handling block, risking divergence | Medium | Medium | Extract event handling into a shared helper method `_process_stream_events()` |
| Technical | Model name in DB may not match `MODEL_CONTEXT_WINDOWS` keys (e.g., custom model names, Ollama models) | Medium | Low | Prefix matching handles dated variants; unknown models fall back to 128000 (safe for most modern models) |
| Integration | Pre-emptive compaction modifies the `history` list in-place, which could affect logging or debugging | Low | Low | Compactor returns a new list (does not mutate input) |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Create context package and implement HistoryCompactor module"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Integrate pre-emptive compaction into _run_agent_graph() and _chat_impl()"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Implement reactive fallback in _run_agent_graph() error handling"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Write unit tests for HistoryCompactor"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: BE-005
    name: "Write integration tests for agent_service compaction"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-003]
    kind: test

  - id: BE-006
    name: "Run quality checks (mypy, ruff) and verify coverage"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]
    kind: test
```

---

## Documentation References

### Required Reading

- AI Chat Developer Guide: `docs/02-architecture/ai-chat-developer-guide.md`
- Architecture README: `docs/02-architecture/README.md`
- Coding Standards: `docs/02-architecture/coding-standards.md`

### Code References

- Token counting pattern: `tiktoken` library with `cl100k_base` encoding (standard for GPT-4 family)
- Error handling pattern: `backend/app/ai/agent_service.py` lines 1064-1078 (existing `except Exception` block)
- Event bus publishing: `backend/app/ai/agent_service.py` line 745-752 (`_publish` helper)
- LLM instantiation: `backend/app/ai/agent_service.py` lines 224-262 (`_create_langchain_llm`)
- Test patterns: `backend/tests/unit/services/test_ai_config_service.py`
- Test fixtures: `backend/tests/conftest.py` (AI provider/model/assistant fixtures at lines 1026-1171)

---

## Prerequisites

### Technical

- [x] `tiktoken` installed (verified in virtual environment)
- [x] `openai.BadRequestError` importable (verified)
- [ ] No new dependencies required

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed
- [x] User decisions captured (same model for summaries, pre-emptive + reactive fallback, 6 recent turns)
