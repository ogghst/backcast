# Plan: Token Usage Monitoring

**Created:** 2026-04-03
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 -- Context Estimator Module + Actual Usage Capture

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 from analysis (Moderate -- dedicated module + actual API capture)
- **Architecture**: New `TokenEstimator` utility class in `backend/app/ai/token_estimator.py` providing pre-flight estimation (chars/4 heuristic) and post-flight actual usage capture from `on_chat_model_end` events. No new DB schema.
- **Key Decisions**:
  1. Use chars/4 heuristic for pre-flight input token estimation (no tiktoken dependency)
  2. Capture real API token counts from LangChain `on_chat_model_end` events via `usage_metadata`
  3. No new DB columns -- context window sizes stored as static mapping
  4. Fix the misleading `total_tokens` counter (currently counts characters) to store actual API-reported tokens
  5. Accumulate `prompt_tokens` and `completion_tokens` across all LLM calls in a single graph execution
  6. Two structured log markers: `[CONTEXT_USAGE_ESTIMATE]` (pre-flight) and `[CONTEXT_USAGE_ACTUAL]` (post-flight)

### Success Criteria

**Functional Criteria:**

- [ ] AC-1: Pre-flight estimation logged before graph invocation with estimated input tokens and context window percentage. VERIFIED BY: unit test on `TokenEstimator.log_context_usage_estimate` + log capture assertion
- [ ] AC-2: Actual token usage captured from every `on_chat_model_end` event, accumulating `prompt_tokens` and `completion_tokens` across all LLM calls in a single execution. VERIFIED BY: unit test simulating `on_chat_model_end` events with mock `usage_metadata`
- [ ] AC-3: The `total_tokens` field on `AIAgentExecution` stores actual API completion tokens (not character counts) when API data is available. VERIFIED BY: inspection of `_run_agent_graph` completion block where `execution.total_tokens` is set
- [ ] AC-4: Context window size lookup works for known models (gpt-4o, gpt-4o-mini) and returns `None` gracefully for unknown models. VERIFIED BY: unit test on `TokenEstimator.get_context_window_size`
- [ ] AC-5: Token estimation is accurate within +/- 20% of actual for messages over 100 characters. VERIFIED BY: unit test comparing estimate against known message sizes

**Technical Criteria:**

- [ ] AC-6: MyPy strict mode passes with zero errors on all new/modified files. VERIFIED BY: `cd backend && uv run mypy app/ai/token_estimator.py app/ai/agent_service.py`
- [ ] AC-7: Ruff passes with zero errors on all new/modified files. VERIFIED BY: `cd backend && uv run ruff check app/ai/token_estimator.py app/ai/agent_service.py`
- [ ] AC-8: Test coverage >= 80% on `token_estimator.py`. VERIFIED BY: `cd backend && uv run pytest --cov=app/ai/token_estimator tests/unit/ai/test_token_estimator.py`
- [ ] AC-9: Zero latency impact on graph invocation (estimation is synchronous arithmetic, not I/O). VERIFIED BY: estimation runs before `async for event in graph.astream_events(...)`, not in the streaming loop
- [ ] AC-10: Structured log format matches existing project conventions (f-string with pipe-separated key=value pairs). VERIFIED BY: log capture test

**Business Criteria:**

- [ ] AC-11: Operators can grep logs for `[CONTEXT_USAGE_ESTIMATE]` to see pre-flight context usage before each agent invocation. VERIFIED BY: manual verification or log capture test
- [ ] AC-12: Operators can grep logs for `[CONTEXT_USAGE_ACTUAL]` to see real API token usage after each agent invocation. VERIFIED BY: manual verification or log capture test

### Scope Boundaries

**In Scope:**

- New `TokenEstimator` module in `backend/app/ai/token_estimator.py`
- Modification of `_run_agent_graph()` in `backend/app/ai/agent_service.py` to:
  - Call `TokenEstimator` for pre-flight estimation before `graph.astream_events()`
  - Handle `on_chat_model_end` events to accumulate actual token counts
  - Replace char-based `total_tokens` with actual API tokens
  - Add `[CONTEXT_USAGE_ACTUAL]` log in the summary block
- Unit tests for `TokenEstimator` in `backend/tests/unit/ai/test_token_estimator.py`

**Out of Scope:**

- No new DB schema changes (no migration)
- No frontend changes
- No new REST API endpoints for token history
- No per-subagent token breakdown (accumulates across all LLM calls)
- No context window size configuration via environment variables or admin UI
- No integration tests (unit tests provide sufficient coverage for this utility)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 1 | Create `TokenEstimator` module with estimation logic, context window lookup, and structured logging | `backend/app/ai/token_estimator.py` (new) | None | AC-1, AC-4, AC-5, AC-10 | Low |
| 2 | Write unit tests for `TokenEstimator` | `backend/tests/unit/ai/test_token_estimator.py` (new) | Task 1 | AC-1, AC-4, AC-5, AC-10 | Low |
| 3 | Modify `_run_agent_graph()` to integrate `TokenEstimator`: pre-flight estimate, `on_chat_model_end` handler, fix `total_tokens`, add actual usage log | `backend/app/ai/agent_service.py` (modify) | Task 1 | AC-2, AC-3, AC-11, AC-12 | Medium |
| 4 | Run quality gates (MyPy, Ruff, tests) and fix any issues | All modified files | Tasks 1-3 | AC-6, AC-7, AC-8 | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| AC-1 (pre-flight estimation logged) | T-001 | `tests/unit/ai/test_token_estimator.py` | `log_context_usage_estimate` produces log with `[CONTEXT_USAGE_ESTIMATE]` marker containing estimated_tokens and usage_percentage |
| AC-4 (context window lookup) | T-002 | `tests/unit/ai/test_token_estimator.py` | `get_context_window_size("gpt-4o")` returns 128000; `get_context_window_size("unknown-model")` returns None |
| AC-5 (estimation accuracy) | T-003 | `tests/unit/ai/test_token_estimator.py` | For a 400-char message, estimate returns 100 (+/- 20% bounds) |
| AC-10 (structured log format) | T-004 | `tests/unit/ai/test_token_estimator.py` | Log output contains pipe-separated key=value pairs matching `[KEY] key=value \| key=value` pattern |
| AC-2 (actual usage from on_chat_model_end) | T-005 | `tests/unit/ai/test_token_estimator.py` | `accumulate_usage_from_event` correctly extracts prompt_tokens and completion_tokens from mock event data |
| AC-3 (total_tokens uses API data) | T-006 | Verified by code inspection | In `_run_agent_graph`, the value stored in `execution.total_tokens` comes from accumulated `completion_tokens`, not `len(content)` |
| AC-12 (actual usage log) | T-007 | `tests/unit/ai/test_token_estimator.py` | `log_actual_usage` produces log with `[CONTEXT_USAGE_ACTUAL]` marker |

---

## Test Specification

### Test Hierarchy

```
tests/
  unit/
    ai/
      test_token_estimator.py    <-- New test file
        TestEstimateInputTokens
          test_estimate_basic_message
          test_estimate_empty_messages
          test_estimate_mixed_message_types
        TestGetContextWindowSize
          test_known_models_return_window_size
          test_unknown_model_returns_none
          test_case_insensitive_lookup
        TestLogContextUsageEstimate
          test_log_contains_required_fields
          test_log_format_matches_convention
        TestAccumulateUsageFromEvent
          test_accumulate_single_event
          test_accumulate_multiple_events
          test_accumulate_event_without_usage_metadata
        TestLogActualUsage
          test_log_contains_required_fields
          test_log_with_no_api_data
        TestTokenUsageAccumulator
          test_initial_state_is_zero
          test_to_dict_returns_correct_structure
```

### Test Cases (first 8)

| Test ID | Test Name | Criterion | Type | Verification |
| --- | --- | --- | --- | --- |
| T-001 | `test_estimate_basic_message` | AC-5 | Unit | 400-char HumanMessage returns 100 tokens (chars/4) |
| T-002 | `test_estimate_mixed_message_types` | AC-5 | Unit | List of [SystemMessage, HumanMessage, AIMessage] sums all content lengths / 4 |
| T-003 | `test_known_models_return_window_size` | AC-4 | Unit | `get_context_window_size("gpt-4o")` returns 128000 |
| T-004 | `test_unknown_model_returns_none` | AC-4 | Unit | `get_context_window_size("claude-3")` returns None |
| T-005 | `test_log_contains_required_fields` | AC-1, AC-10 | Unit | Captured log contains `estimated_tokens`, `context_window_size`, `usage_percentage`, `model_name`, `session_id` |
| T-006 | `test_accumulate_single_event` | AC-2 | Unit | Single event with `usage_metadata={"input_tokens": 500, "output_tokens": 200}` updates accumulator to prompt=500, completion=200 |
| T-007 | `test_accumulate_event_without_usage_metadata` | AC-2 | Unit | Event with missing `usage_metadata` leaves accumulator unchanged (no crash) |
| T-008 | `test_to_dict_returns_correct_structure` | AC-3, AC-12 | Unit | `TokenUsageAccumulator.to_dict()` returns dict with `prompt_tokens`, `completion_tokens`, `total_tokens` keys |

### Test Infrastructure Needs

- **Fixtures needed**: None beyond standard pytest. `langchain_core.messages.SystemMessage`, `HumanMessage`, `AIMessage` will be imported directly.
- **Mocks/stubs**: `caplog` fixture for log capture assertions. Mock event dicts for `on_chat_model_end` simulation (plain dicts matching LangChain event structure, no need to mock actual LangChain objects).
- **Database state**: None required -- all tests are pure unit tests.

---

## Detailed Implementation Specification

### Task 1: Create `TokenEstimator` Module

**File:** `backend/app/ai/token_estimator.py` (NEW)

**Classes and functions to implement:**

1. **`CONTEXT_WINDOW_SIZES: dict[str, int]`** -- Module-level constant mapping model names to context window sizes in tokens:
   ```python
   CONTEXT_WINDOW_SIZES: dict[str, int] = {
       "gpt-4o": 128_000,
       "gpt-4o-mini": 128_000,
       "gpt-4.5-preview": 128_000,
       "gpt-4.1": 1_047_576,
       "gpt-4.1-mini": 1_047_576,
       "gpt-4.1-nano": 1_047_576,
       "o3": 200_000,
       "o4-mini": 200_000,
   }
   ```

2. **`estimate_input_tokens(messages: list[BaseMessage]) -> int`** -- Pure function. Sum `len(msg.content)` for all messages, divide by 4, return int. Handles both `str` and `list` content types (LangChain messages can have `content` as either). Returns 0 for empty list.

3. **`get_context_window_size(model_name: str) -> int | None`** -- Pure function. Looks up `model_name` in `CONTEXT_WINDOW_SIZES`. Returns `None` for unknown models.

4. **`log_context_usage_estimate(messages: list[BaseMessage], model_name: str, session_id: str, execution_id: str) -> int`** -- Logs a `[CONTEXT_USAGE_ESTIMATE]` structured log line and returns the estimated token count. Log format:
   ```
   [CONTEXT_USAGE_ESTIMATE] session_id={session_id} | execution_id={execution_id} | model={model_name} | estimated_input_tokens={tokens} | context_window_size={size} | usage_percentage={pct:.1f}%
   ```
   When model is unknown, logs `context_window_size=unknown` and `usage_percentage=N/A`.

5. **`TokenUsageAccumulator`** -- Simple dataclass with `prompt_tokens: int = 0` and `completion_tokens: int = 0`:
   - `accumulate_from_event(event_data: dict[str, Any]) -> None` -- Extracts `usage_metadata` from an `on_chat_model_end` event's `output` field. Handles both `usage_metadata.input_tokens/output_tokens` (LangChain standard) and `response_metadata.token_usage.prompt_tokens/completion_tokens` (OpenAI format via LangChain). Increments accumulators. Does nothing if metadata is missing.
   - `to_dict() -> dict[str, int]` -- Returns `{"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens, "total_tokens": self.prompt_tokens + self.completion_tokens}`

6. **`log_actual_usage(accumulator: TokenUsageAccumulator, model_name: str, session_id: str, execution_id: str) -> None`** -- Logs a `[CONTEXT_USAGE_ACTUAL]` structured log line:
   ```
   [CONTEXT_USAGE_ACTUAL] session_id={session_id} | execution_id={execution_id} | model={model_name} | prompt_tokens={prompt} | completion_tokens={completion} | total_tokens={total}
   ```

**Imports required:**
- `logging` (for module logger)
- `from langchain_core.messages import BaseMessage`
- `from dataclasses import dataclass`
- `from typing import Any`

---

### Task 3: Modify `_run_agent_graph()` in `agent_service.py`

**File:** `backend/app/ai/agent_service.py` (MODIFY)

**Change 1: Add import (near line 48, after existing ai imports)**

Add:
```python
from app.ai.token_estimator import (
    TokenUsageAccumulator,
    estimate_input_tokens,
    get_context_window_size,
    log_actual_usage,
    log_context_usage_estimate,
)
```

**Change 2: Add pre-flight estimation (after line 715, before `async for event in graph.astream_events(...)`)**

After `set_request_context(tool_context, interrupt_node)` and after the `if interrupt_node is not None:` block, insert a call to estimate context usage:
```python
# Estimate context window usage before graph invocation
estimated_tokens = log_context_usage_estimate(
    messages=history,
    model_name=model_name,
    session_id=str(session_id),
    execution_id=event_bus.execution_id,
)
```
This goes between line ~719 (end of interrupt_node registration) and line ~721 (start of recursion_limit extraction).

**Change 3: Replace `total_tokens = 0` with `TokenUsageAccumulator` (line 734)**

Replace:
```python
total_tokens = 0
```
With:
```python
total_output_chars = 0  # Track chars for streaming accumulation (kept for backward compat)
token_accumulator = TokenUsageAccumulator()
```

**Change 4: Update char counter in streaming handler (line 823)**

Replace:
```python
total_tokens += len(content)
```
With:
```python
total_output_chars += len(content)
```

**Change 5: Add `on_chat_model_end` event handler (between `on_chat_model_stream` handler and `on_tool_start` handler, around line 831)**

Insert a new `elif` block after the `on_chat_model_stream` handler (ending at line 830) and before `on_tool_start` (line 833):
```python
# Handle chat model end -- capture actual token usage
elif event_type == "on_chat_model_end":
    output = data.get("output")
    if output:
        token_accumulator.accumulate_from_event(data)
```

**Change 6: Update summary log (line 1159-1167)**

Replace:
```python
logger.info(
    f"[RUN_AGENT_GRAPH_COMPLETE] _run_agent_graph | "
    f"duration_ms={stream_duration_ms:.2f} | "
    f"execution_id={event_bus.execution_id} | "
    f"session_id={session_id} | "
    f"total_tokens={total_tokens} | "
    f"tool_calls_count={tool_calls_count}"
)
```
With:
```python
usage_dict = token_accumulator.to_dict()
logger.info(
    f"[RUN_AGENT_GRAPH_COMPLETE] _run_agent_graph | "
    f"duration_ms={stream_duration_ms:.2f} | "
    f"execution_id={event_bus.execution_id} | "
    f"session_id={session_id} | "
    f"total_output_chars={total_output_chars} | "
    f"prompt_tokens={usage_dict['prompt_tokens']} | "
    f"completion_tokens={usage_dict['completion_tokens']} | "
    f"total_tokens={usage_dict['total_tokens']} | "
    f"tool_calls_count={tool_calls_count}"
)

# Log actual token usage from API
log_actual_usage(
    accumulator=token_accumulator,
    model_name=model_name,
    session_id=str(session_id),
    execution_id=event_bus.execution_id,
)
```

**Change 7: Update `execution.total_tokens` persistence**

Find where `execution.total_tokens` is set (in the completion block where `AIAgentExecution` is updated). Replace the char-based assignment with actual API tokens:
```python
execution.total_tokens = token_accumulator.completion_tokens
```
If there is no existing assignment of `execution.total_tokens`, add it in the block where execution status is set to "completed".

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | `on_chat_model_end` event structure varies across LangChain versions or does not carry `usage_metadata` for some model providers | Medium | Low | `accumulate_from_event` uses defensive `.get()` calls and graceful no-op when metadata is missing. The char counter is preserved as `total_output_chars` as fallback in the summary log. |
| Technical | `usage_metadata` field name differs between LangChain versions (e.g., `input_tokens` vs `prompt_tokens`) | Medium | Low | `accumulate_from_event` checks both `usage_metadata.input_tokens/output_tokens` (LangChain standard) and `response_metadata.token_usage.prompt_tokens/completion_tokens` (OpenAI format). |
| Integration | The `total_tokens` field on `AIAgentExecution` previously stored char counts; downstream consumers (e.g., `AgentExecutionPublic` schema) now receive actual tokens, which are smaller numbers | Low | Low | No known frontend consumers of this field. The value change is in the correct direction (was misleadingly large, now accurate). If consumers exist, they will see lower numbers which are correct. |
| Performance | Token estimation adds a pass over all message content strings | Low | Low | Estimation is O(n) over message chars, runs synchronously before graph invocation (not in streaming loop). For typical conversations (< 100K chars) this takes < 1ms. |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Create TokenEstimator module (token_estimator.py)"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Write unit tests for TokenEstimator"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: BE-003
    name: "Modify agent_service.py to integrate TokenEstimator (pre-flight, on_chat_model_end, fix total_tokens)"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Run quality gates (MyPy, Ruff, tests) on modified files"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-003]
    kind: test
```

---

## Documentation References

### Required Reading

- Analysis: `docs/03-project-plan/iterations/2026-04-03-token-usage-monitoring/00-analysis.md`
- Coding Standards: `docs/02-architecture/coding-standards.md`
- Existing monitoring pattern: `backend/app/ai/monitoring.py` (same module structure to follow)
- Existing monitoring tests: `backend/tests/unit/ai/test_monitoring.py` (same test structure to follow)

### Code References

- Backend pattern: `backend/app/ai/monitoring.py` -- `ToolExecutionMetrics` dataclass + `MonitoringContext` + structured logging
- Test pattern: `backend/tests/unit/ai/test_monitoring.py` -- Arrange-Act-Assert with `caplog` for log capture
- Streaming event loop: `backend/app/ai/agent_service.py` lines 783-1058 -- existing `on_chat_model_stream` / `on_tool_start` / `on_tool_end` / `on_tool_error` handlers
- Domain model: `backend/app/models/domain/ai.py` line 274 -- `AIAgentExecution.total_tokens` field
- Schema: `backend/app/models/schemas/ai.py` line 252 -- `AgentExecutionPublic` schema

---

## Prerequisites

### Technical

- [x] No database migrations required
- [x] No new dependencies required (uses existing `langchain_core.messages.BaseMessage`)
- [x] LangChain `astream_events` already supports `on_chat_model_end` events (confirmed in LangChain docs)

### Documentation

- [x] Analysis phase approved (Option 2)
- [x] Architecture context reviewed (streaming event loop, monitoring patterns)
- [x] Key implementation files read and understood
