# Analysis: Autocompaction with Error Recovery for Context Overflow

**Created:** 2026-04-03
**Request:** Detect context window overflow errors mid-conversation, summarize conversation history into compressed form, and retry the LLM call. Prevent opaque failures and conversation loss.

---

## Clarified Requirements

The user's request addresses a specific failure mode: when a long AI chat conversation accumulates enough history that the next LLM call exceeds the model's context window, the agent crashes with a generic error. Users see an opaque error message and lose their in-progress conversation.

### Functional Requirements

- Detect context overflow errors specifically (distinguish from other API errors)
- Preserve the system prompt and most recent N turns verbatim
- Summarize older conversation turns into a compressed summary
- Retry the LLM call with the compacted history (max 2 retries)
- Continue streaming tokens to the event bus normally after retry
- Update the execution status correctly through the retry lifecycle

### Non-Functional Requirements

- Must not break existing event bus publishing flow
- Must not add noticeable latency to non-overflow cases
- Compaction summary must preserve enough context for the LLM to continue coherently
- Retry must be transparent to the user (no manual intervention required)

### Constraints

- Single execution path: `_run_agent_graph()` in `agent_service.py` (line 607)
- Error handling at line 1064 catches all exceptions with `except Exception`
- History built at line 645 by `_build_conversation_history()`, returns `list[BaseMessage]`
- System prompt prepended at line 656 as first `SystemMessage`
- LLM is `ChatOpenAI` from `langchain_openai`; errors arrive as `openai.BadRequestError`
- The `shared_checkpointer` (`MemorySaver`) stores graph state -- retry needs a clean checkpoint
- The graph is invoked via `graph.astream_events()` -- a streaming iterator that cannot be restarted
- Two execution entry points: `start_execution()` (background, line 1169) and direct `chat()` (synchronous, line 464)

### Assumptions (to validate)

1. Context overflow manifests as `openai.BadRequestError` with status code 400 and error code `context_length_exceeded`
2. The compaction can use the same LLM model to generate summaries (self-summarization)
3. The system prompt does not change between retries (it is deterministic from config)
4. After compaction, the graph state/checkpointer should be reset to avoid stale state

---

## Context Discovery

### Product Scope

- AI Chat bounded context: conversation sessions with tool-calling agents
- No existing user story for context window management or autocompaction
- The AI chat system is designed for long-running conversations (EVM analysis, change orders) that naturally accumulate context

### Architecture Context

- **Bounded contexts involved:** AI Chat (single context)
- **Existing patterns to follow:**
  - Error handling uses event bus publishing: `_publish("error", {...})`
  - Execution status lifecycle: `pending -> running -> completed/error/awaiting_approval`
  - `start_execution()` wraps `_run_agent_graph()` in its own try/except for DB status updates
- **Architectural constraints:**
  - Single-server deployment, in-memory event bus, `MemorySaver` checkpointer
  - Graph is cached and reused (`CompiledGraphCache`), retry cannot modify the graph
  - Middleware reads context from `ContextVar` bridge, set before invocation

### Codebase Analysis

**Backend:**

- **Entry point:** `backend/app/ai/agent_service.py`
  - `_run_agent_graph()` (line 607): Main streaming execution, builds history, invokes graph, publishes events
  - `_build_conversation_history()` (line 1382): Loads all DB messages for session as `list[BaseMessage]`
  - `start_execution()` (line 1169): Wraps `_run_agent_graph()` in independent DB session + execution tracking
  - `chat()` (line 464): Non-streaming path, uses `graph.ainvoke()` (not streaming), also vulnerable to overflow
- **Error handling:** Line 1064 catches `Exception`, publishes error event, returns. Line 1282 in `start_execution()` catches errors from `_run_agent_graph()` and updates execution status to "error".
- **LLM client:** `ChatOpenAI` from `langchain_openai`. Error types from `openai` package: `BadRequestError` (status 400) for context overflow, inherits from `APIStatusError`.
- **State:** `AgentState` TypedDict with `messages`, `tool_call_count`, `max_tool_iterations`, `next`. Uses `operator.add` reducer for messages (append-only).
- **Checkpointer:** `MemorySaver` singleton in `graph_cache.py` -- in-memory, keyed by `thread_id` (session_id).

**No existing utilities for:**
- Token counting (`tiktoken` not installed, no `get_num_tokens` calls)
- Message trimming or summarization
- Conversation compaction
- Context window management

**Key insight:** The `_build_conversation_history()` method loads ALL messages from the session. There is no pagination or truncation. As conversations grow, every message is sent to the LLM on each turn. This is the root cause of the problem.

---

## Solution Options

### Option 1: Pre-emptive History Compaction (Pre-invoke Guard)

**Architecture & Design:**

Add a compaction step BEFORE the graph is invoked. After `_build_conversation_history()` returns, estimate token count and compact if it approaches the model's limit. This is a deterministic guard that prevents the error from ever reaching the LLM API.

Steps:
1. After building history (line 645), count tokens using `tiktoken` or LangChain's `get_num_tokens_from_messages()`
2. If token count exceeds a configurable threshold (e.g., 80% of model context window), run compaction
3. Compaction: summarize older messages into a `SystemMessage`, keep last N turns verbatim
4. Use the same LLM model to generate the summary (a separate `llm.invoke()` call, not streamed)
5. Pass compacted history to the graph as normal

**UX Design:**
- Transparent to the user
- Optional: publish an `info` event to the event bus so the frontend can show a brief "compressing conversation..." indicator
- No retry loop needed -- compaction happens once before invocation

**Implementation:**
- New module: `backend/app/ai/context/history_compactor.py` -- token counting, summarization logic
- Modify: `backend/app/ai/agent_service.py` -- call compactor after `_build_conversation_history()` in both `_run_agent_graph()` and `chat()`
- Modify: `backend/app/ai/state.py` -- no changes needed (state is not persisted between invocations)
- Config: Add `compaction_threshold_ratio` setting (default 0.8)
- Dependencies: Add `tiktoken` for accurate token counting

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Prevents error entirely (proactive, not reactive); simpler control flow; no retry loop; no checkpoint manipulation; works for both `chat()` and `_run_agent_graph()` paths |
| Cons            | Adds latency on every invocation for token counting (small, ~10ms); requires `tiktoken` dependency; compaction summary quality depends on the LLM's summarization ability; model context window sizes must be known/configured |
| Complexity      | Low-Med |
| Maintainability | Good -- isolated module, no changes to graph or event bus flow |
| Performance     | ~10ms overhead per invocation for token counting; ~2-5s one-time cost when compaction triggers |

---

### Option 2: Reactive Retry with Compaction (Post-error Recovery)

**Architecture & Design:**

Catch the specific context overflow error from the OpenAI API, compact the history, and retry the graph invocation. This is the approach described in the original request.

Steps:
1. Wrap the `graph.astream_events()` call in a retry loop (max 2 attempts)
2. On `openai.BadRequestError` with context overflow signature, catch it before the generic `except Exception`
3. Call compaction: summarize older messages, keep last N turns
4. Re-invoke the graph with compacted history
5. If compaction also fails, fall through to existing error handling

**UX Design:**
- Transparent to the user
- Publish a `compaction` event to event bus so frontend can optionally show "Recovering..."
- On first attempt tokens may already have been partially streamed -- the `astream_events` iterator may have yielded events before the error. Need to handle partial state.

**Implementation:**
- New module: `backend/app/ai/context/autocompactor.py` -- compaction logic
- Modify: `backend/app/ai/agent_service.py` -- wrap `astream_events` in retry loop, detect `BadRequestError`
- Modify: `backend/app/ai/state.py` -- add `compacted_summary: str | None` field (to track compaction state)
- Challenge: `astream_events()` is an async generator. The error may occur mid-stream after events have already been published. On retry, previously published events would be duplicated unless tracked.
- Challenge: The `MemorySaver` checkpointer may have partial state from the failed invocation. Need to clear or reset it.
- Challenge: Accumulated streaming state (`accumulated_content`, `main_agent_segments`, `_token_accumulator`) must be reset on retry.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Only activates when needed (zero overhead on normal calls); directly addresses the stated problem; provides a "safety net" approach |
| Cons            | Complex retry logic around async generator; partial event duplication risk; checkpointer state corruption risk; streaming state must be reset; only works for `_run_agent_graph()` path (not `chat()` which uses `ainvoke`); hard to test the mid-stream failure case |
| Complexity      | High |
| Maintainability | Fair -- retry logic interleaved with streaming state management is fragile |
| Performance     | Zero overhead on normal calls; ~2-5s recovery cost when triggered; potential event duplication |

---

### Option 3: Sliding Window History with Persistent Summary (Stateful Compaction)

**Architecture & Design:**

Maintain a persistent compacted summary in the database, updated incrementally after each conversation turn. Instead of compacting the entire history at once, append old messages to the summary as the conversation grows. The history sent to the LLM is always: `[SystemMessage(summary)] + [recent N turns]`.

Steps:
1. Add a `compacted_summary` column to `ai_conversation_sessions` table
2. After each successful turn, check if message count exceeds a threshold
3. If so, summarize the oldest message(s) into the persistent summary, delete or mark them
4. `_build_conversation_history()` reads: summary (as SystemMessage) + recent messages from DB
5. No retry needed -- the history always fits within the context window

**UX Design:**
- Completely transparent
- No latency spikes from compaction
- Gradual, incremental summarization preserves more context than one-shot compaction

**Implementation:**
- Migration: Add `compacted_summary TEXT` column to `ai_conversation_sessions`
- New module: `backend/app/ai/context/incremental_compactor.py` -- incremental summarization
- Modify: `backend/app/ai/agent_service.py` -- call compactor after message save
- Modify: `_build_conversation_history()` -- prepend summary as SystemMessage
- Modify: `backend/app/services/ai_config_service.py` -- persist summary updates
- Modify: `backend/app/models/domain/ai.py` -- add column to `AIConversationSession`
- Modify: `backend/app/models/schemas/ai.py` -- add field to session schemas

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Zero runtime latency impact (compaction happens post-turn, not pre-turn); history always fits; smooth incremental summarization; most robust long-term solution |
| Cons            | Requires DB migration; changes to session model/schema/service; summarization quality degrades over many turns (summary-of-summary); complexity spread across multiple layers; modifies the persistence model |
| Complexity      | Med-High |
| Maintainability | Fair -- compaction quality degrades over time; more touch points across the stack |
| Performance     | Best runtime performance (no pre-invoke overhead); post-turn compaction is async |

---

## Comparison Summary

| Criteria           | Option 1: Pre-emptive Guard | Option 2: Reactive Retry | Option 3: Sliding Window |
| ------------------ | --------------------------- | ------------------------ | ------------------------ |
| Development Effort | Low (2-3 days)              | High (4-5 days)          | Med-High (4-5 days)      |
| UX Quality         | Good (transparent)          | Fair (potential pauses)  | Best (invisible)         |
| Flexibility        | Good                        | Low (streaming-only)     | Best                     |
| Best For           | Quick fix, minimal risk     | Exact original request   | Long-term architecture   |
| Risk Level         | Low                         | High                     | Medium                   |
| Test Coverage      | Easy to unit test           | Hard to test mid-stream  | Moderate                 |

---

## Recommendation

**I recommend Option 1 (Pre-emptive History Compaction) because:**

1. **Lowest risk.** It prevents the error before it occurs, avoiding all the complexity of retrying a mid-stream async generator, managing partial checkpoint state, and deduplicating events.

2. **Covers both execution paths.** The compaction runs after `_build_conversation_history()` and before graph invocation, so it works for both `_run_agent_graph()` (streaming) and `chat()` (synchronous). Option 2 only addresses the streaming path.

3. **Simplest implementation.** A new isolated module with token counting and summarization, called in one place. No changes to `AgentState`, no DB migrations, no checkpoint manipulation.

4. **Easiest to test.** Token counting and summarization are pure functions. No need to simulate mid-stream failures or async generator state.

5. **Incremental path to Option 3.** If long-term usage shows that pre-emptive compaction latency is unacceptable, the compactor module can be evolved into the incremental approach (Option 3) without changing the integration point.

**Alternative consideration:** Choose Option 3 if you anticipate very long conversations (50+ turns) where even the pre-emptive compaction latency becomes noticeable, or if you want the compaction to be completely invisible to the user. However, Option 3 requires a DB migration and touches more files, which increases the risk of regressions.

**I recommend against Option 2** because retrying an `astream_events()` async generator after a partial failure is architecturally fragile. The error can occur at any point during streaming (not just at the start), meaning events may have already been published to the bus, tokens flushed to the frontend, and checkpoints written. Cleaning all this state up reliably is significantly more complex than preventing the problem in the first place.

---

## Decision Questions

1. **Which LLM model should generate the compaction summary?** The same model as the conversation (simplest), or a faster/cheaper model (e.g., gpt-4o-mini)? Using the same model ensures quality but costs more; using a cheaper model reduces cost but may produce lower-quality summaries.

2. **How many recent turns should be preserved verbatim?** The request suggests 4 turns. Is this sufficient for the typical conversation patterns in this system? EVM analysis conversations may reference tool results from 5-6 turns back.

3. **Should the compaction threshold be configurable per assistant config, or global?** Different models have different context windows (gpt-4o: 128K, gpt-4o-mini: 128K, ollama models: varies). A global setting is simpler but may be too conservative for large-context models.

4. **Should the user be notified when compaction occurs?** An optional `info` event on the event bus would let the frontend show a brief "Compressing conversation..." indicator. This adds transparency but requires frontend changes.

---

## References

- [AI Chat Developer Guide](../../02-architecture/ai-chat-developer-guide.md) -- Full architecture reference
- [Architecture README](../../02-architecture/README.md) -- System overview
- Key files analyzed:
  - `backend/app/ai/agent_service.py` -- Main orchestration, `_run_agent_graph()`, `_build_conversation_history()`, `start_execution()`
  - `backend/app/ai/state.py` -- `AgentState` TypedDict
  - `backend/app/ai/graph_cache.py` -- `MemorySaver` checkpointer, `LLMClientCache`, ContextVar helpers
  - `backend/app/ai/llm_client.py` -- LLM client factory, imports `openai.BadRequestError` available
  - `backend/app/models/domain/ai.py` -- `AIConversationSession`, `AIAgentExecution` models
  - `backend/app/services/ai_config_service.py` -- Session/message persistence
