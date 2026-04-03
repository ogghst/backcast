# Analysis: Conversation History Windowing

**Created:** 2026-04-03
**Request:** Implement a sliding window on conversation history to prevent context window overflow in long AI chat sessions. Currently `_build_conversation_history()` loads every message with no truncation.

---

## Clarified Requirements

### Problem Statement

`_build_conversation_history()` in `agent_service.py:1382` calls `config_service.list_messages(session_id)` which performs an unbounded `SELECT ... ORDER BY created_at` with no limit. For sessions with 50+ turns, this can fill the LLM context window before any tool calls happen, causing token overflow errors or degraded response quality.

### Functional Requirements

- Load only the most recent N turns (user+assistant pairs) verbatim for LLM context
- N is configurable per assistant via a new `max_context_turns` field on `AIAssistantConfig`
- Older turns beyond the window should be represented by a summary/hint prefix (stub initially)
- Must apply identically in both execution paths: `_chat_impl()` (non-streaming, line 487) and `_run_agent_graph()` (streaming, line 645)
- Must support Alembic migration for the new schema column

### Non-Functional Requirements

- Zero performance regression for short sessions (under the window limit)
- Windowing logic must be unit-testable in isolation
- Must not break existing tests for `_build_conversation_history`

### Constraints

- AI entities use `SimpleEntityBase` (non-versioned, no EVCS) -- no bitemporal concerns
- Single-server deployment -- no distributed cache considerations
- The existing test suite mocks `_get_session_messages` (not the current production code path), so tests need alignment with the actual `config_service.list_messages()` call
- Summary generation is a future concern; initial implementation should use a static placeholder

### Assumptions

1. A "turn" is defined as a user message plus its corresponding assistant response (1 user + 1 assistant = 1 turn). Tool messages are already skipped in the current implementation.
2. The default window size should be reasonable for typical LLM context windows (e.g., 20 turns = ~40 messages).
3. The system prompt is NOT counted against the turn window -- it is always prepended separately.
4. The current user message (the one that triggered the invocation) is always included regardless of windowing.

---

## Context Discovery

### Product Scope

- The AI chat system is part of the E09 bounded context (AI Integration), documented in `docs/02-architecture/ai-chat-developer-guide.md`
- No specific user story addresses context window management -- this is a technical reliability enhancement
- The sprint backlog does not currently track this work item

### Architecture Context

- **Bounded context:** AI Integration (non-EVCS, `SimpleEntityBase` pattern)
- **Layered architecture:** The windowing logic belongs in the service/agent layer, not in the API or repository layer
- **Existing pattern to follow:** `AIConfigService.list_messages()` is the data access point; windowing should be applied after retrieval or via a new parameterized query
- **Graph caching:** The agent graph is cached and reused (`graph_cache.py`). Conversation history is NOT part of the cached graph -- it is rebuilt per request. Windowing changes will not affect caching.
- **Execution paths:** Both `chat()` (line 487) and `_run_agent_graph()` (line 645) call `_build_conversation_history()` identically

### Codebase Analysis

**Backend:**

- `backend/app/ai/agent_service.py:1382-1407` -- `_build_conversation_history()` loads ALL messages, converts to LangChain `HumanMessage`/`AIMessage`, skips "tool" role
- `backend/app/services/ai_config_service.py:465-473` -- `list_messages()` does unbounded `SELECT ... ORDER BY created_at`
- `backend/app/models/domain/ai.py:120-156` -- `AIAssistantConfig` has `model_id`, `temperature`, `max_tokens`, `system_prompt`, `allowed_tools`, `recursion_limit` but no context turn limit
- `backend/app/models/schemas/ai.py:169-212` -- Pydantic schemas for assistant config CRUD (Base, Create, Update, Public)
- `backend/tests/unit/ai/test_agent_service.py:317-370` -- Existing tests for `_build_conversation_history` (2 test cases: with messages, empty session)
- No existing `backend/app/ai/context/` directory -- this would be new

**Key observations:**

1. The tests mock `_get_session_messages` which does not exist in production code -- production calls `self.config_service.list_messages(session_id)` directly
2. `list_messages()` currently has no `limit` parameter
3. The `AIAssistantConfig` model and its Pydantic schemas are the natural place for `max_context_turns`
4. There is no existing summarization infrastructure

---

## Solution Options

### Option 1: Database-Level Windowing (SQL LIMIT)

**Architecture & Design:**

Add a `max_context_turns` column to `AIAssistantConfig`. Modify `list_messages()` to accept an optional `limit` parameter. In `_build_conversation_history()`, pass the assistant config's limit to load only the N most recent messages. For messages beyond the window, prepend a static SystemMessage placeholder.

**Implementation:**

- Add `max_context_turns: Mapped[int | None]` to `AIAssistantConfig` model
- Add Alembic migration for the new column (nullable, default NULL = unlimited)
- Add `max_context_turns` to Pydantic schemas (Base, Create, Update, Public)
- Add `limit` parameter to `AIConfigService.list_messages()` using SQLAlchemy `.limit()`
- Modify `_build_conversation_history()` to accept `assistant_config`, compute limit from `max_context_turns * 2` (user+assistant per turn), and call `list_messages(session_id, limit=...)`
- When messages are truncated, prepend a static `SystemMessage` placeholder like `[Earlier conversation history omitted. {N} earlier messages were exchanged.]`
- Both call sites (line 487, line 645) already have `assistant_config` in scope, so passing it is straightforward

**Trade-offs:**

| Aspect          | Assessment                                                    |
| --------------- | ------------------------------------------------------------- |
| Pros            | Minimal code change; leverages PostgreSQL for efficiency; testable; clean separation |
| Cons            | Static placeholder is crude; no semantic compression of older context |
| Complexity      | Low                                                           |
| Maintainability | Good -- follows existing patterns, no new abstractions        |
| Performance     | Excellent -- DB-level LIMIT avoids loading unnecessary rows   |

---

### Option 2: Application-Level Windowing with Dedicated Module

**Architecture & Design:**

Create a new module `backend/app/ai/context/history_window.py` containing a `HistoryWindow` class that encapsulates all windowing logic. This class takes the full message list, the window size, and returns the windowed result with summary prefix. The `list_messages()` method remains unchanged (no limit). The windowing happens entirely in application code.

**Implementation:**

- Create `backend/app/ai/context/history_window.py` with `HistoryWindow` class
- `HistoryWindow.apply(messages: list[AIConversationMessage], max_turns: int) -> list[BaseMessage]`
- Add `max_context_turns` to model, schemas, migration (same as Option 1)
- `_build_conversation_history()` loads ALL messages, then delegates to `HistoryWindow.apply()`
- The class handles: turn counting, slicing, summary prefix generation, edge cases
- Easily testable in isolation without DB mocking

**Trade-offs:**

| Aspect          | Assessment                                                    |
| --------------- | ------------------------------------------------------------- |
| Pros            | Clean separation of concerns; highly testable; easy to extend with summarization later |
| Cons            | Still loads ALL messages from DB before discarding most of them; extra module to maintain |
| Complexity      | Low-Medium                                                    |
| Maintainability | Good -- but introduces a module for what is currently ~25 lines of logic |
| Performance     | Poor for long sessions -- loads 100+ rows to use 40           |

---

### Option 3: Hybrid -- DB-Level Truncation with Summary Extension Point

**Architecture & Design:**

Combine the efficiency of Option 1 (DB-level LIMIT) with the extensibility of Option 2 (dedicated module). Use SQL LIMIT to load only the window, but introduce a lightweight `build_summary_prefix(count: int) -> str` function (not a class) that can be replaced with LLM-based summarization later. No new module directory -- the function lives alongside the existing agent service code.

**Implementation:**

- Add `max_context_turns` to model, schemas, migration (same as Options 1 and 2)
- Add `limit` parameter to `list_messages()` (same as Option 1)
- Add a private method `_build_truncation_summary(omitted_count: int) -> str` to `AgentService`
- Modify `_build_conversation_history()` to:
  1. First query total message count (lightweight `COUNT(*)`)
  2. If count exceeds window, load only the windowed messages via `list_messages(session_id, limit=...)`
  3. Prepend summary if truncation occurred
- The count query avoids loading rows just to count them

**Trade-offs:**

| Aspect          | Assessment                                                    |
| --------------- | ------------------------------------------------------------- |
| Pros            | DB-efficient; provides extension point for future summarization; no new module overhead |
| Cons            | Two DB queries (count + windowed fetch) instead of one; slightly more complex than Option 1 |
| Complexity      | Medium                                                        |
| Maintainability | Good -- count+limit pattern is well understood                |
| Performance     | Good -- two lightweight queries vs. loading all rows          |

---

## Comparison Summary

| Criteria           | Option 1: DB-LIMIT Only   | Option 2: App-Level Module | Option 3: Hybrid (DB+Summary) |
| ------------------ | ------------------------- | -------------------------- | ----------------------------- |
| Development Effort | ~3 hours                  | ~4 hours                   | ~4.5 hours                    |
| Performance        | Excellent (1 query)       | Poor (full load)           | Good (2 lightweight queries)  |
| Extensibility      | Low (hardcoded prefix)    | High (dedicated module)    | Medium (extension function)   |
| Complexity         | Low                       | Low-Medium                 | Medium                        |
| Best For           | Immediate fix, MVP        | Future-rich summarization  | Balanced fix + extensibility  |

---

## Recommendation

**I recommend Option 1 (DB-Level Windowing) because:**

1. The problem is clear and urgent -- unbounded history loading is a production reliability risk. Option 1 solves it with the smallest blast radius.
2. It follows the project's "Simplicity First" principle -- minimum code that solves the problem, nothing speculative.
3. The static summary placeholder is sufficient for now. LLM-based summarization can be added later without architectural changes -- just replace the prefix string with a summary call.
4. The DB-level LIMIT is the most performant approach, which matters for sessions with 50+ turns.
5. No new module or class hierarchy is needed. The change touches exactly 4 files: model, schema, service, agent_service.

**Alternative consideration:** If you anticipate implementing LLM-based conversation summarization within the next sprint, Option 3 is the better foundation because the count query enables "summarize the older part" flows. But per the project guidelines, we should not build abstractions for single-use code or features that were not requested.

**Regarding the new file `backend/app/ai/context/history_window.py` proposed in the original request:** This is unnecessary overhead for the current scope. The windowing logic is approximately 15 lines (compute limit, call list_messages with limit, prepend summary). A dedicated module adds directory structure, imports, and indirection for no current benefit. If summarization becomes a complex feature later, the module can be introduced then.

---

## Decision Questions

1. What should the default `max_context_turns` value be when NULL (unlimited)? Should we use a hardcoded default (e.g., 20) in `_build_conversation_history()`, or should the migration set a server default on the column?

2. Should the truncation summary include any metadata about the omitted messages (e.g., "5 questions about project X were asked"), or is a simple count placeholder sufficient for now?

3. Should `list_messages()` always return messages in chronological order (oldest first) even with a LIMIT, or should it reverse-order to get the N most recent? The current implementation returns oldest-first, which means LIMIT would return the oldest N messages -- the opposite of what we want. This requires either: (a) reverse-ordering the query and re-reversing the result, or (b) a subquery approach.

---

## References

- [AI Chat Developer Guide](../../02-architecture/ai-chat-developer-guide.md)
- [Backend Coding Standards](../../02-architecture/backend/coding-standards.md)
- [AI Domain Models](../../../backend/app/models/domain/ai.py)
- [AI Config Service](../../../backend/app/services/ai_config_service.py)
- [Agent Service](../../../backend/app/ai/agent_service.py)
- [Agent Service Tests](../../../backend/tests/unit/ai/test_agent_service.py)
- [AI Pydantic Schemas](../../../backend/app/models/schemas/ai.py)
