# Analysis: Token Usage Monitoring

**Created:** 2026-04-03
**Request:** Add token counting and logging to track context window usage percentage before each graph invocation, enabling visibility into how much of the context window is being consumed by the AI agent system.

---

## Clarified Requirements

### Functional Requirements

- **FR-1:** Log estimated context window usage (input tokens) before each graph invocation in `_run_agent_graph()`
- **FR-2:** Log actual token usage after each graph invocation completes, using real API response data when available
- **FR-3:** Replace the misleading `total_tokens` counter (line 734/823 in `agent_service.py`) which currently counts streaming output characters, not tokens
- **FR-4:** Store context window size information per model to enable percentage calculations
- **FR-5:** Persist token usage data in the existing `AIAgentExecution` record for post-execution querying

### Non-Functional Requirements

- **NFR-1:** Zero latency impact on the critical path -- estimation is a simple arithmetic operation before graph invocation
- **NFR-2:** No new runtime dependencies (no tiktoken or similar tokenization libraries)
- **NFR-3:** Structured log format consistent with existing markers (e.g., `[CONTEXT_USAGE_ESTIMATE]`)
- **NFR-4:** Follow existing coding standards (MyPy strict, docstrings with Context section, structured logging)

### Constraints

- Context window sizes vary by model (gpt-4o: 128K, gpt-4o-mini: 128K, gpt-4.5-preview: varies) -- must be configurable or derived from model metadata
- The `astream_events` API used in `_run_agent_graph()` does not currently capture `on_chat_model_end` events (only `on_chat_model_stream` is handled), so actual usage data requires capturing a different event type
- AI domain entities use `SimpleEntityBase` (non-versioned) -- no EVCS concerns

---

## Context Discovery

### Product Scope

- No specific user story covers token monitoring. This is a developer/operational observability feature.
- Relevant to the AI chat bounded context for system health and cost management.

### Architecture Context

- **Bounded contexts involved:** AI Chat context only (no cross-context impact)
- **Existing patterns to follow:**
  - Structured log markers: `[RUN_AGENT_GRAPH_COMPLETE]`, `[GRAPH_CACHE_HIT]`, etc.
  - `monitoring.py` provides `MonitoringContext` and `ToolExecutionMetrics` for tool-level metrics
  - `telemetry.py` provides OpenTelemetry integration (already instruments `OpenAIInstrumentor` for token tracking, but only when OTEL is enabled)
  - `AIAgentExecution.total_tokens` field exists in the domain model but is populated with character counts, not tokens
- **Architectural constraints:** Service-layer pattern (no direct DB access from utilities), non-versioned entities

### Codebase Analysis

**Backend:**

- **`agent_service.py` line 734:** `total_tokens = 0` initialized as a character counter
- **`agent_service.py` line 823:** `total_tokens += len(content)` counts streaming output characters
- **`agent_service.py` line 1165:** Logs `total_tokens` in `[RUN_AGENT_GRAPH_COMPLETE]` summary
- **`agent_service.py` line 645:** `history = await self._build_conversation_history(session_id)` -- this is the point where input context size can be estimated
- **`agent_service.py` line 656:** `history.insert(0, SystemMessage(content=system_prompt))` -- system prompt is added to history before invocation
- **`ai.py` (domain):** `AIModel` has `model_id` (string, e.g., "gpt-4o"), `display_name`, no `context_window_size`
- **`ai.py` (domain):** `AIAgentExecution` has `total_tokens: int` field (currently misused as character count)
- **`ai.py` (schema):** `AgentExecutionPublic` exposes `total_tokens` to API consumers
- **`monitoring.py`:** Existing `ToolExecutionMetrics` and `MonitoringContext` patterns
- **`telemetry.py`:** `OpenAIInstrumentor` already tracks token usage via OpenTelemetry when enabled, but this data goes to Jaeger, not application logs or DB

**Critical discovery:** LangChain `AIMessage` objects carry `usage_metadata` and `response_metadata` fields that contain actual token counts from the OpenAI API. These are available in `on_chat_model_end` events from `astream_events()`, but the current code only handles `on_chat_model_stream` events.

**No existing `backend/app/ai/context/` directory exists.**

---

## Solution Options

### Option 1: Minimal -- Structured Logging Only (No New Module)

**Architecture & Design:**

Inline estimation directly in `_run_agent_graph()` using a small helper function. No new module or model changes. Estimate input tokens from message history using chars/4 heuristic. Add a `CONTEXT_WINDOW_SIZES` constant dict mapping model names to window sizes. Log structured context usage before graph invocation.

**UX Design:**

No frontend changes. Benefits developers and operators via structured log output. The existing `total_tokens` field on `AIAgentExecution` continues to store the char-based counter (rename in documentation only).

**Implementation:**

- Add `_estimate_context_tokens(messages: list[BaseMessage]) -> int` private method to `AgentService`
- Add `_CONTEXT_WINDOW_SIZES: dict[str, int]` class constant
- Add logging before `graph.astream_events()` call at ~line 783
- Fix the `total_tokens` label in the summary log to say `total_chars` or add both metrics
- Files modified: `agent_service.py` only

**Trade-offs:**

| Aspect          | Assessment                                             |
| --------------- | ------------------------------------------------------ |
| Pros            | Zero new files, minimal change surface, immediate value |
| Cons            | Estimation-only, no actual API token counts, no DB persistence of input tokens, char-based `total_tokens` counter still misleading |
| Complexity      | Low                                                    |
| Maintainability | Fair (logic embedded in agent_service)                 |
| Performance     | Negligible (one pass over message strings)              |

---

### Option 2: Moderate -- Context Estimator Module + Actual Usage Capture

**Architecture & Design:**

Create a lightweight `TokenEstimator` utility class in a new `backend/app/ai/token_estimator.py` file. This module provides:
1. Pre-invocation estimation of input tokens using chars/4 heuristic
2. Context window size lookup from a static mapping (no DB schema change)
3. Post-invocation actual token capture from `on_chat_model_end` events (which carry `usage_metadata`)
4. Structured logging of both estimated input and actual API-reported usage

Additionally, modify `_run_agent_graph()` to also handle `on_chat_model_end` events, accumulating real `prompt_tokens` and `completion_tokens` from the API response metadata.

**UX Design:**

No frontend changes. Developers get two log markers:
- `[CONTEXT_USAGE_ESTIMATE]` before invocation (estimated input tokens + percentage)
- `[CONTEXT_USAGE_ACTUAL]` after invocation (actual prompt/completion tokens from API)

The `total_tokens` field on `AIAgentExecution` is updated to store actual output tokens (from `usage_metadata.completion_tokens`) rather than character counts.

**Implementation:**

- New file: `backend/app/ai/token_estimator.py` -- `TokenEstimator` class with:
  - `CONTEXT_WINDOW_SIZES` dict (model_name -> max_tokens)
  - `estimate_input_tokens(messages: list[BaseMessage]) -> int`
  - `get_context_window_size(model_name: str) -> int | None`
  - `log_context_usage(messages, model_name, session_id, execution_id)` structured logging method
- Modify `agent_service.py`:
  - Import and use `TokenEstimator` before `graph.astream_events()` call
  - Add `on_chat_model_end` event handler in the streaming loop to capture `usage_metadata`
  - Fix `total_tokens` to store actual completion tokens
  - Add `[CONTEXT_USAGE_ESTIMATE]` log before invocation
  - Add `[CONTEXT_USAGE_ACTUAL]` log after completion
- No model/schema changes (`context_window_size` stays as static mapping)
- Files: 1 new, 1 modified

**Trade-offs:**

| Aspect          | Assessment                                                      |
| --------------- | --------------------------------------------------------------- |
| Pros            | Actual API token counts, proper separation of concerns, structured log markers, fixes the misleading `total_tokens` counter |
| Cons            | New file, `on_chat_model_end` event handling adds complexity to the already-large streaming loop |
| Complexity      | Medium                                                          |
| Maintainability | Good (estimation logic isolated in its own module)              |
| Performance     | Negligible (estimation is O(n) over message chars, actual usage is free from API) |

---

### Option 3: Full -- DB-Stored Context Window + Estimator Module + API Exposure

**Architecture & Design:**

Same as Option 2 plus:
1. Add `context_window_size` column to `ai_models` table (optional, nullable integer)
2. Expose context usage in `AgentExecutionPublic` schema (add `input_tokens`, `output_tokens`, `context_window_size` fields)
3. Store actual token counts per execution in DB for historical analysis
4. Provide REST API endpoint for token usage history

**UX Design:**

Frontend can display token usage per execution in the session history. The execution status polling response includes token breakdown.

**Implementation:**

- All of Option 2 plus:
- Alembic migration: add `context_window_size` to `ai_models`, add `input_tokens` and `output_tokens` to `ai_agent_executions`
- Update `AIModel` and `AIAgentExecution` domain models
- Update `AgentExecutionPublic` schema
- Populate `context_window_size` during model seeding or via admin UI
- Files: 1 new + 1 migration + 3-4 modified

**Trade-offs:**

| Aspect          | Assessment                                                               |
| --------------- | ------------------------------------------------------------------------ |
| Pros            | Full historical visibility, frontend-displayable, queryable for trends   |
| Cons            | DB schema changes, migration needed, more files touched, larger scope    |
| Complexity      | High                                                                     |
| Maintainability | Good (well-structured) but more surface area                             |
| Performance     | Negligible runtime impact, slight DB storage overhead                    |

---

## Comparison Summary

| Criteria           | Option 1 (Minimal) | Option 2 (Moderate)  | Option 3 (Full)      |
| ------------------ | ------------------ | -------------------- | -------------------- |
| Development Effort | ~1 hour            | ~2-3 hours           | ~4-6 hours           |
| Observability Gain | Logs only (estimated) | Logs + actual API data | Logs + DB + API + Frontend |
| Accuracy           | chars/4 estimate only | chars/4 + real API tokens | chars/4 + real API tokens |
| Files Changed      | 1                  | 2 (1 new + 1 mod)    | 5-6 (1 new + migration + mods) |
| Risk               | Very low           | Low                  | Medium (migration)   |
| Best For           | Quick debugging win | Production observability | Full audit trail     |

---

## Recommendation

**I recommend Option 2 because:**

1. **It fixes the core problem correctly.** The current `total_tokens` counter is misleading (counts characters, not tokens). Option 2 captures actual token usage from the API via `usage_metadata` on `on_chat_model_end` events -- this is the right data source, not a heavier tokenization library.

2. **It provides both pre-flight and post-flight visibility.** The pre-invocation estimate (chars/4) answers "will this overflow?" and the post-invocation actual data answers "what did it actually cost?" Both are valuable for different debugging scenarios.

3. **It avoids premature schema changes.** Adding DB columns (Option 3) is a reasonable future extension, but the immediate need is operational visibility via logs. Once the monitoring proves useful, the data can be persisted later.

4. **The `TokenEstimator` module is small and well-scoped.** A single file with ~60-80 lines of code, no external dependencies, easy to test. It follows the same pattern as `monitoring.py` (standalone utility module in the `ai/` package).

5. **`on_chat_model_end` event capture is a natural extension of the existing streaming loop.** The code already handles `on_chat_model_stream`, `on_tool_start`, `on_tool_end`, and `on_tool_error`. Adding `on_chat_model_end` is a small, surgical change that yields high-value data.

**Alternative consideration:** Choose Option 1 if you want the absolute minimum change and are comfortable with estimation-only data. Choose Option 3 if you need historical token usage reporting across sessions for cost allocation or trend analysis.

---

## Decision Questions

1. **Should the existing `total_tokens` field on `AIAgentExecution` be repurposed to store actual output tokens?** This would fix the current misuse but could break any downstream consumers expecting character counts. The `AgentExecutionPublic` schema already exposes this field to the API.

2. **Should context window sizes be configurable via environment variables or a static mapping?** Static mapping is simpler but needs code changes for new models. Environment variables allow runtime override but add configuration complexity.

3. **Is capturing `on_chat_model_end` for actual token usage acceptable, or do you need per-invocation (subagent-level) token breakdowns?** Each LLM call in the agent loop (main agent, subagents) produces its own `on_chat_model_end` event. Accumulating all of them gives total usage, but subagent-level granularity would require more complex tracking.

---

## References

- `backend/app/ai/agent_service.py` -- `_run_agent_graph()` at line 607, `total_tokens` at line 734, summary log at line 1159
- `backend/app/models/domain/ai.py` -- `AIModel`, `AIAgentExecution`
- `backend/app/models/schemas/ai.py` -- `AgentExecutionPublic`
- `backend/app/ai/monitoring.py` -- Existing `MonitoringContext` pattern
- `backend/app/ai/telemetry.py` -- `OpenAIInstrumentor` for OTEL-based token tracking
- `docs/02-architecture/ai-chat-developer-guide.md` -- Full architecture reference
