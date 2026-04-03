# Analysis: Microcompaction (Selective Tool Result Compression)

**Created:** 2026-04-03
**Request:** After each graph execution, compress old tool results (older than N turns) while keeping recent ones intact. Store compressed versions in the database to reduce context window consumption on subsequent turns.

---

## Clarified Requirements

### Functional Requirements

- After each agent graph execution completes, identify tool result payloads that are older than N turns from the most recent message
- Compress old tool results to a condensed summary that retains key information (entity names, IDs, status, numeric values) while discarding verbose details
- Keep the most recent N tool result payloads intact (configurable, default 2)
- Preserve human messages and AI assistant messages verbatim (never compress `content` on user/assistant roles)
- Only compress the `tool_results` JSONB column content, not the `tool_calls` metadata
- Persist the compressed `tool_results` back to the database so subsequent `_build_conversation_history` calls benefit
- Track compaction state in `message_metadata` to avoid re-compacting already compacted messages
- Run as a background post-processing step, not blocking the response

### Non-Functional Requirements

- Must not corrupt conversation history or lose information critical to the LLM's ability to continue the conversation
- Compression should be deterministic and fast (no LLM calls for summarization at this stage)
- Must be safe against concurrent access (multiple executions on the same session)
- Must integrate cleanly with the existing `_build_conversation_history` flow

### Constraints

- AI chat entities use `SimpleEntityBase` (non-versioned, no EVCS)
- Single-server deployment, in-memory event bus
- `AIConfigService` has `add_message` but no `update_message` method currently
- `_build_conversation_history` currently reads only `content` and `role` from messages -- it does NOT load `tool_results` or `tool_calls` into LangChain message objects
- Tool results are stored as JSONB on the assistant message row (first segment gets all tool_calls and tool_results)
- Maximum observed tool_results payload: 111KB (111,427 bytes)

---

## Context Discovery

### Product Scope

- No specific user stories for context optimization -- this is an infrastructure improvement
- Related to AI Chat bounded context (`docs/02-architecture/ai-chat-developer-guide.md`)

### Architecture Context

- **Bounded context:** AI Chat (non-versioned entities)
- **Existing patterns:** Background tasks via `asyncio.create_task()`, event bus for decoupled execution
- **Architectural constraints:** Layered architecture (Service -> Repository), simple entity pattern

### Codebase Analysis

**Backend:**

Key files and their roles:

- `backend/app/ai/agent_service.py` -- `_run_agent_graph()` and `start_execution()` are the execution entry points. After execution completes and messages are persisted (lines 1081-1117), the method publishes completion events. This is the natural insertion point for a post-processing step.
- `backend/app/services/ai_config_service.py` -- `add_message()` persists messages with `tool_results` JSONB. Currently has NO `update_message()` method. One must be added.
- `backend/app/models/domain/ai.py` -- `AIConversationMessage` has columns: `role`, `content`, `tool_calls` (JSONB), `tool_results` (JSONB), `message_metadata` (JSONB, mapped from `metadata` column).
- `backend/app/ai/agent_service.py:_build_conversation_history()` (lines 1382-1407) -- Loads messages via `config_service.list_messages()`, builds `HumanMessage` and `AIMessage` objects from `content` only. Tool messages are explicitly skipped. **Critically: tool_results are NOT loaded into LangChain history at all.**

**Database evidence:**

From production queries:
- 481 assistant messages, average tool_results size: 3.6KB, maximum: 111KB
- Largest sessions accumulate 50-127KB of tool_results
- The `metadata` column currently tracks: `invocation_id`, `segment_index`, `total_segments`, `subagent_name`, `invocation_number`
- No existing compaction tracking in metadata

**Critical discovery: tool_results are NOT used in conversation history**

The `_build_conversation_history()` method converts DB messages to LangChain `HumanMessage` and `AIMessage` objects using only `msg.content`. The `tool_results` JSONB column is stored in the database but is **never loaded back into the conversation context window**. This means:

1. Tool results bloat the database but do not currently consume LLM context tokens
2. The `tool_results` data is available for the frontend Activity Panel display only
3. Microcompaction as described would reduce database storage, not LLM context window consumption

This changes the analysis significantly. See the "Architectural Alignment" section below.

---

## Architectural Alignment Assessment

**The proposed feature addresses database bloat, not context window bloat.**

The current `_build_conversation_history()` method loads messages and creates LangChain `HumanMessage`/`AIMessage` from the `content` column only. Tool results (`tool_results` JSONB) are stored in the database for:
1. Frontend Activity Panel rendering (showing what tools were called and their results)
2. Audit trail / debugging

They are NOT loaded into the LLM context window. Therefore, "microcompaction" of tool_results does NOT reduce the LLM's context window consumption. It only reduces database storage.

**However**, if future context management features (like the separate "conversation history windowing" iteration) change `_build_conversation_history()` to include tool results in the context, then microcompaction becomes a prerequisite. Additionally, even without LLM context savings, reducing 111KB tool result blobs to summaries is valuable for:
- Database storage efficiency
- API response payload sizes when loading message history for the frontend
- Future-proofing for when tool results ARE included in context

**The proposed solution is architecturally sound but its value proposition needs adjustment.**

---

## Solution Options

### Option 1: DB-Level Microcompaction (Post-Execution Background Task)

**Architecture & Design:**

After each `_run_agent_graph()` completes and messages are persisted, spawn a background `asyncio.create_task()` that:

1. Loads all assistant messages for the session ordered by `created_at`
2. Identifies messages with `tool_results` that have not been compacted (no `compacted: true` in metadata)
3. Excludes the most recent N messages (configurable, default 2)
4. For each eligible message, compresses `tool_results` by extracting key fields (tool name, success/error status, entity IDs/names) and discarding verbose output
5. Updates the message row in-place: replaces `tool_results` with the compacted version, adds `compacted: true` to `message_metadata`

Compression strategy (rule-based, no LLM call):
- For each tool result object, keep: `tool`, `success`, `error`
- For `result` field, truncate to a max character limit (e.g., 500 chars) with a summary prefix
- Add `_compacted_from_size` to metadata for audit trail

**UX Design:**
- No user-visible changes in this phase
- Frontend Activity Panel would show compacted summaries for old turns (acceptable since old details are no longer actionable)
- Recent tool results remain fully visible

**Implementation:**

New files:
- `backend/app/ai/context/microcompactor.py` -- `Microcompactor` class with `compact_session(session_id, keep_recent=N)` method

Modified files:
- `backend/app/services/ai_config_service.py` -- Add `update_message(message_id, tool_results, metadata)` method
- `backend/app/ai/agent_service.py` -- Call microcompaction after message persistence in `_run_agent_graph()` (via `asyncio.create_task()`) and in `start_execution()` cleanup

**Trade-offs:**

| Aspect          | Assessment                                                 |
| --------------- | ---------------------------------------------------------- |
| Pros            | Clean separation of concerns; no LLM cost; deterministic; reduces DB storage; future-proofs for context inclusion |
| Cons            | Does NOT currently reduce LLM context window usage (since tool_results are not loaded into history); adds a background task that could fail silently |
| Complexity      | Low -- rule-based truncation, single background task       |
| Maintainability | Good -- single new module, minimal integration points      |
| Performance     | Negligible impact on user-facing latency (background task) |

---

### Option 2: LLM-Powered Summarization (Full Compaction Analog)

**Architecture & Design:**

After each graph execution, use the same LLM to generate a natural language summary of old tool results. Replace the verbose `tool_results` JSONB with a `{ "_summary": "...", "_original_size": N }` structure.

The LLM receives the tool result content and a prompt asking it to extract the key information the agent would need to continue the conversation coherently.

**UX Design:**
- Higher quality summaries than rule-based truncation
- Old tool results replaced with human-readable summaries in Activity Panel

**Implementation:**

Same files as Option 1, plus:
- `backend/app/ai/context/llm_summarizer.py` -- Uses the session's configured LLM to summarize tool results
- Requires additional LLM API calls (cost and latency implications)

**Trade-offs:**

| Aspect          | Assessment                                                 |
| --------------- | ---------------------------------------------------------- |
| Pros            | Higher quality summaries; preserves semantic meaning; closer to Claude Code's Stage 2 compaction |
| Cons            | Additional LLM API cost per compaction pass; increased latency; non-deterministic summaries; risk of LLM hallucination in summaries; more complex implementation |
| Complexity      | Medium -- LLM call management, prompt engineering, error handling |
| Maintainability | Fair -- LLM summarization prompts need tuning and maintenance |
| Performance     | Additional LLM calls add 1-3 seconds per compaction pass   |

---

### Option 3: Hybrid -- Rule-Based Now, LLM Later (Incremental Approach)

**Architecture & Design:**

Implement Option 1 (rule-based truncation) as the immediate solution, but design the `Microcompactor` interface to support pluggable compression strategies. Add a `CompressionStrategy` protocol:

- `RuleBasedStrategy` -- immediate implementation (character limit truncation with key field extraction)
- `LLMSummaryStrategy` -- placeholder for future implementation

The `message_metadata` tracks which strategy was used (`compaction_strategy: "rule_based"`), enabling future re-compaction with the LLM strategy without data loss (the original `tool_results` could be retained in a `_original_tool_results` field during a transition period).

**UX Design:**
- Same as Option 1 for now
- Clear upgrade path to Option 2 without migration

**Implementation:**

Same as Option 1, plus:
- Strategy protocol pattern in `microcompactor.py`
- Metadata conventions for tracking compaction strategy

**Trade-offs:**

| Aspect          | Assessment                                                 |
| --------------- | ---------------------------------------------------------- |
| Pros            | Best of both worlds -- immediate value with upgrade path; clean abstraction; no premature LLM cost; metadata enables future migration |
| Cons            | Slightly more design complexity than Option 1; abstracting for future needs may be premature |
| Complexity      | Low-Medium -- strategy pattern adds minimal overhead       |
| Maintainability | Good -- extensible without modifying existing code         |
| Performance     | Same as Option 1 (rule-based strategy has no LLM overhead) |

---

## Comparison Summary

| Criteria           | Option 1: Rule-Based       | Option 2: LLM Summarization | Option 3: Hybrid           |
| ------------------ | -------------------------- | ---------------------------- | -------------------------- |
| Development Effort | 2-3 days                   | 4-5 days                     | 3 days                     |
| UX Quality         | Acceptable (truncated)     | High (semantic summaries)    | Acceptable now, high later |
| Flexibility        | Low                        | Low (hardcoded LLM approach) | High (pluggable strategies)|
| Best For           | Immediate DB bloat fix     | Quality-first approach       | Incremental delivery       |
| LLM Cost           | None                       | Additional per-turn cost     | None now, opt-in later     |
| Risk               | Low                        | Medium (hallucination risk)  | Low                        |

---

## Recommendation

**I recommend Option 1 (Rule-Based Microcompaction) because:**

1. **The value proposition is primarily database storage efficiency**, not LLM context window reduction (since `_build_conversation_history` does not currently load `tool_results` into the context). The simpler approach matches the actual benefit.

2. **No additional LLM API cost** -- rule-based truncation is deterministic and free.

3. **Low complexity, fast delivery** -- a single new module with one integration point.

4. **The metadata tracking** (`compacted: true`, `compaction_strategy`, `_original_size`) provides a clear upgrade path to Option 2 or Option 3 later if needed.

5. **No premature abstraction** -- following the project's simplicity-first principle (CLAUDE.md section 2). If LLM summarization becomes necessary, it can be added later without redesigning the interface.

**Alternative consideration:** Choose Option 3 (Hybrid) if you expect to need LLM summarization within the next sprint and want the strategy abstraction in place from day one. The extra day of design work pays off if the upgrade happens soon.

**Critical prerequisite note:** Before this feature provides LLM context window savings, `_build_conversation_history()` must be modified to include tool results in the LangChain message history. That is a separate concern (part of the conversation history windowing iteration). Microcompaction of the database payloads is a necessary prerequisite for that future change.

---

## Decision Questions

1. Should the compacted tool results retain the full `result` object structure (just truncated), or is a flat summary string acceptable? This affects whether the frontend Activity Panel needs changes.

2. What should the retention window be? The request says "most recent N tool results (default 2)" -- should this be per-session or per-execution? In sessions with 10+ turns, N=2 may be too aggressive for the frontend display.

3. Should we also compact the `content` column of assistant messages (which averages 1.2KB and peaks at 14KB), or is the focus strictly on `tool_results`?

4. Is it acceptable for the `update_message()` addition to `AIConfigService` to be a simple `session.execute(update(...))` without a formal Pydantic schema, given that this is an internal operation not exposed via API?

---

## References

- `backend/app/ai/agent_service.py` -- `_run_agent_graph()`, `_build_conversation_history()`, `start_execution()`
- `backend/app/services/ai_config_service.py` -- `add_message()`, `list_messages()`
- `backend/app/models/domain/ai.py` -- `AIConversationMessage` model
- `docs/02-architecture/ai-chat-developer-guide.md` -- Full architecture reference
- `docs/03-project-plan/iterations/2026-04-02-claude-code-like-context-management/` -- Deep research on Claude Code context management techniques
- `docs/04-pdca-prompts/analysis-prompt.md` -- Analysis phase workflow
