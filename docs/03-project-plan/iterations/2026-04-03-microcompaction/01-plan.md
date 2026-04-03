# Plan: Microcompaction (DB Storage Optimization)

**Created:** 2026-04-03
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 -- Rule-Based Microcompaction

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 (Rule-Based DB-Level Microcompaction)
- **Architecture**: After each `_run_agent_graph()` completes and messages are persisted, spawn a background `asyncio.create_task()` that loads assistant messages older than N turns, truncates their `tool_results` payloads using rule-based extraction, and writes the compacted versions back to the database.
- **Key Decisions**:
  1. Rule-based compression only -- no LLM cost, deterministic output
  2. Retain JSON structure when compacting (each tool result entry keeps `{tool, success, result, error}` shape with truncated `result`)
  3. Track compaction state in `message_metadata` JSONB column (no schema migration)
  4. Background post-processing via `asyncio.create_task()` -- does not block the response
  5. New `update_message()` method on `AIConfigService` for in-place tool_results updates
  6. No frontend changes required

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: After graph execution, messages with `tool_results` older than N turns (default 2) are compacted in the database VERIFIED BY: integration test
- [ ] FC-2: Compacted tool results retain the JSON structure `{tool, success, result, error}` with truncated `result` field VERIFIED BY: unit test
- [ ] FC-3: Messages already compacted are skipped on subsequent passes VERIFIED BY: unit test checking `compacted: true` in metadata
- [ ] FC-4: The most recent N assistant messages (configurable, default 2) are never compacted VERIFIED BY: unit test with boundary conditions
- [ ] FC-5: Human messages (`role=user`) and AI content (`msg.content`) are never modified VERIFIED BY: integration test
- [ ] FC-6: Compaction runs as a non-blocking background task; graph execution returns immediately VERIFIED BY: integration test timing
- [ ] FC-7: Compaction failures are logged but do not affect the main execution flow VERIFIED BY: unit test with forced error

**Technical Criteria:**

- [ ] TC-1: MyPy strict mode passes with zero errors VERIFIED BY: `cd backend && uv run mypy app/`
- [ ] TC-2: Ruff linting passes with zero errors VERIFIED BY: `cd backend && uv run ruff check .`
- [ ] TC-3: Test coverage >= 80% on new code VERIFIED BY: `uv run pytest --cov=app.ai.context --cov=app.services.ai_config_service`
- [ ] TC-4: Compaction reduces tool_results payload size by >= 50% for payloads > 2KB VERIFIED BY: unit test measurement
- [ ] TC-5: Compaction completes in < 500ms for a session with 50 messages VERIFIED BY: integration test timing

**TDD Criteria:**

- [ ] All tests written before implementation code (RED-GREEN-REFACTOR)
- [ ] Each test fails first (documented in DO phase log)
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- `Microcompactor` class in `backend/app/ai/context/microcompactor.py` (new file)
- `update_message()` method on `AIConfigService` (new method, existing file)
- Integration point in `AgentService._run_agent_graph()` after message persistence (existing file, 1-2 lines added)
- Unit tests for `Microcompactor` compression logic
- Integration tests for end-to-end compaction flow
- Unit tests for `AIConfigService.update_message()`

**Out of Scope:**

- LLM-powered summarization (future iteration)
- Frontend changes (compacted tool results display fine in Activity Panel)
- `_build_conversation_history()` changes (separate future iteration for context windowing)
- Compression of `content` column on assistant messages
- Compression of `tool_calls` JSONB column
- Migration or re-compaction of existing historical data (can be a one-time script later)
- Pluggable strategy abstraction (YAGNI -- add when needed)

---

## Work Decomposition

### Task Breakdown

| #  | Task                                                                                          | Files                                                                                                           | Dependencies  | Success Criteria                          | Complexity |
| -- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------- | ----------------------------------------- | ---------- |
| 1  | Add `update_message()` to `AIConfigService` for in-place tool_results/metadata updates        | `backend/app/services/ai_config_service.py` (modify, line ~508)                                                 | None          | TC-1, TC-2; unit test passes              | Low        |
| 2  | Create `Microcompactor` class with rule-based `compact_tool_results()` method                 | `backend/app/ai/context/__init__.py` (new), `backend/app/ai/context/microcompactor.py` (new)                    | None          | FC-2, FC-4, TC-1, TC-2, TC-4             | Low        |
| 3  | Add `compact_session()` async method that orchestrates DB load + compact + update per session | `backend/app/ai/context/microcompactor.py` (modify)                                                             | Tasks 1, 2    | FC-1, FC-3, FC-5, FC-7, TC-1, TC-2       | Medium     |
| 4  | Integrate microcompaction call into `AgentService._run_agent_graph()` after message save      | `backend/app/ai/agent_service.py` (modify, after line ~1124)                                                    | Tasks 1, 3    | FC-6, FC-7; integration test passes       | Low        |
| 5  | Write unit tests for `Microcompactor.compact_tool_results()`                                  | `backend/tests/unit/ai/test_microcompactor.py` (new)                                                            | Task 2        | TC-3, FC-2, FC-4, TC-4                   | Low        |
| 6  | Write unit tests for `Microcompactor.compact_session()`                                       | `backend/tests/unit/ai/test_microcompactor.py` (modify)                                                         | Tasks 1, 3    | TC-3, FC-1, FC-3, FC-5, FC-7             | Medium     |
| 7  | Write unit tests for `AIConfigService.update_message()`                                       | `backend/tests/unit/services/test_ai_config_service.py` (modify)                                                | Task 1        | TC-3                                      | Low        |
| 8  | Run full quality checks (mypy, ruff, pytest) on modified files only                           | All modified files                                                                                              | Tasks 1-7     | TC-1, TC-2, TC-3                          | Low        |

### Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Add update_message() to AIConfigService"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Create Microcompactor with rule-based compact_tool_results()"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-003
    name: "Add compact_session() orchestration method to Microcompactor"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-004
    name: "Integrate microcompaction into AgentService._run_agent_graph()"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-003]

  - id: BE-005
    name: "Unit tests for compact_tool_results() compression logic"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]
    kind: test

  - id: BE-006
    name: "Unit tests for compact_session() orchestration"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-003]
    kind: test

  - id: BE-007
    name: "Unit tests for AIConfigService.update_message()"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: BE-008
    name: "Run quality checks (mypy, ruff, coverage) on modified scope"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005, BE-006, BE-007]
    kind: test
```

**Execution levels:**

- Level 0 (parallel): BE-001, BE-002
- Level 1 (depends on Level 0): BE-003 (depends on BE-001 + BE-002), BE-005 (depends on BE-002), BE-007 (depends on BE-001)
- Level 2 (depends on Level 1): BE-004, BE-006
- Level 3 (final gate): BE-008

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File                                       | Expected Behavior                                                        |
| -------------------- | ------- | ----------------------------------------------- | ------------------------------------------------------------------------ |
| FC-1                 | T-001   | tests/unit/ai/test_microcompactor.py            | `compact_session()` compacts messages older than N turns in DB           |
| FC-2                 | T-002   | tests/unit/ai/test_microcompactor.py            | `compact_tool_results()` returns list with same JSON structure keys      |
| FC-3                 | T-003   | tests/unit/ai/test_microcompactor.py            | Messages with `compacted: true` in metadata are skipped                  |
| FC-4                 | T-004   | tests/unit/ai/test_microcompactor.py            | Most recent N messages have `tool_results` unchanged                     |
| FC-5                 | T-005   | tests/unit/ai/test_microcompactor.py            | `role=user` messages are never touched; `content` never modified         |
| FC-6                 | T-006   | tests/unit/ai/test_microcompactor.py            | `compact_session()` is called via `asyncio.create_task()`                |
| FC-7                 | T-007   | tests/unit/ai/test_microcompactor.py            | Compaction error is caught, logged, and does not propagate               |
| TC-1                 | T-008   | CI pipeline                                     | `uv run mypy app/` zero errors                                           |
| TC-2                 | T-009   | CI pipeline                                     | `uv run ruff check .` zero errors                                        |
| TC-3                 | T-010   | CI pipeline                                     | Coverage >= 80% on new modules                                           |
| TC-4                 | T-011   | tests/unit/ai/test_microcompactor.py            | 5KB payload compacts to <= 2.5KB                                         |
| TC-5                 | T-012   | tests/unit/ai/test_microcompactor.py            | `compact_session()` with 50 messages completes in < 500ms                |
| TC-1/2 (service)     | T-013   | tests/unit/services/test_ai_config_service.py   | `update_message()` persists tool_results and metadata changes            |

---

## Detailed Task Specifications

### Task 1: Add `update_message()` to `AIConfigService`

**File:** `backend/app/services/ai_config_service.py`
**Location:** After the existing `add_message()` method (after line 507)

**What to add:**
A new async method `update_message(message_id: UUID, tool_results: list[dict[str, Any]] | None = None, message_metadata: dict[str, Any] | None = None) -> AIConversationMessage` that:

1. Loads the message by primary key (`session.get(AIConversationMessage, message_id)`)
2. If `tool_results` is provided, sets `msg.tool_results = tool_results`
3. If `message_metadata` is provided, merges it into the existing metadata (shallow merge: `{**existing_meta, **message_metadata}`)
4. Flushes and returns the updated message

**Why no Pydantic schema:** This is an internal operation not exposed via API. A simple method signature suffices per analysis decision question 4.

**Test specification (T-013):**
- Create a message via `add_message()`, then call `update_message()` with new `tool_results` and `message_metadata`
- Assert `tool_results` and `message_metadata` are persisted correctly
- Assert existing metadata keys are preserved when merging

### Task 2: Create `Microcompactor` class with `compact_tool_results()`

**File:** `backend/app/ai/context/__init__.py` (new, empty or minimal)
**File:** `backend/app/ai/context/microcompactor.py` (new)

**Class structure:**

```
class Microcompactor:
    def __init__(self, config_service: AIConfigService, keep_recent: int = 2, max_result_chars: int = 500)
    async def compact_session(self, session_id: UUID) -> None
    @staticmethod
    def compact_tool_results(tool_results: list[dict[str, Any]], max_result_chars: int = 500) -> list[dict[str, Any]]
```

**`compact_tool_results()` specification (pure function, static method):**

Input: A list of tool result dicts, each shaped as:
```json
{"tool": "list_projects", "success": true, "result": <any JSON>, "error": null}
```

Output: A new list of tool result dicts with the same structure, where:
- `tool`: kept verbatim
- `success`: kept verbatim
- `error`: kept verbatim (including `null`)
- `result`: If the serialized JSON of the `result` field exceeds `max_result_chars`, replace with a truncated version that is a dict `{"_truncated": true, "_original_size": N, "preview": "<first 200 chars of stringified result>"}`. If it fits within the limit, keep verbatim.

**Key design choices:**
- `result` truncation preserves JSON structure (returns a dict, not a raw string) so the frontend Activity Panel rendering does not break
- `_truncated` flag and `_original_size` provide audit trail
- `preview` captures the first 200 chars of the stringified result for quick scanning
- The `max_result_chars` default of 500 chars means most tool results under ~500 chars are left untouched

**Test specifications:**

- T-002: Pass a list of 3 tool results; verify output has same length and each entry has keys `{tool, success, result, error}`
- T-004: (tested indirectly via compact_session -- see Task 3)
- T-011: Pass a tool result with a 5KB `result` string; verify output `result` is a dict with `_truncated: true` and `preview` field of 200 chars, and total serialized size is <= 2.5KB

### Task 3: Add `compact_session()` orchestration method

**File:** `backend/app/ai/context/microcompactor.py` (modify)

**Method specification:**

`async def compact_session(self, session_id: UUID) -> None`

1. Call `config_service.list_messages(session_id)` to get all messages ordered by `created_at`
2. Filter to `role == "assistant"` messages that have non-null `tool_results`
3. Of those, filter out messages where `message_metadata.get("compacted") == True` (already compacted)
4. Of those, exclude the last `keep_recent` messages (most recent N stay intact)
5. For each remaining message:
   a. Call `compact_tool_results(msg.tool_results, self.max_result_chars)`
   b. Compute original size: `len(json.dumps(msg.tool_results))`
   c. Call `config_service.update_message(msg.id, tool_results=compacted, message_metadata={"compacted": True, "compacted_at": <ISO timestamp>, "compacted_original_size": original_size})`
6. Wrap the entire method in try/except; log errors with `logger.error` but do not re-raise

**Concurrency safety:** Since this runs as a background task after the main execution completes, and only modifies `tool_results` on messages from previous turns (not the current one), concurrent access risk is low. The `compacted: true` flag prevents double-processing.

**Test specifications:**

- T-001: Create 5 assistant messages with tool_results, call `compact_session()`, verify messages 0-2 (first 3, assuming keep_recent=2 means messages 3-4 are kept) are compacted and messages 3-4 are untouched
- T-003: Create messages where some already have `compacted: True` in metadata; verify only uncompacted ones are processed
- T-005: Include `role="user"` messages in the session; verify they are never touched (their `tool_results` is always null anyway)
- T-007: Mock `config_service.update_message()` to raise an exception; verify `compact_session()` catches it, logs, and continues processing other messages (or completes without re-raising)

### Task 4: Integrate microcompaction into `AgentService._run_agent_graph()`

**File:** `backend/app/ai/agent_service.py`
**Location:** After the message persistence block completes (after line ~1124, before the "Publish main agent completion" block at line 1126)

**What to add:**

A single block that spawns the background task:

```python
# Spawn background microcompaction
try:
    from app.ai.context.microcompactor import Microcompactor
    compactor = Microcompactor(self.config_service)
    asyncio.create_task(compactor.compact_session(session_id))
except Exception:
    logger.debug("Microcompaction spawn failed", exc_info=True)
```

**Design choices:**
- Import is inline to avoid circular imports and to fail gracefully if the module is unavailable
- The `asyncio.create_task()` call is fire-and-forget; errors inside `compact_session()` are caught and logged internally
- The outer try/except ensures that even a failed import or instantiation does not affect the main flow
- Uses `self.config_service` which is already bound to the session; the background task will share the same DB session. This is acceptable because the session remains open during the request lifecycle. If this proves problematic, the DO phase can create a separate session via the session factory.

**Test specification:**

- T-006: Verify that after `_run_agent_graph()` completes, `asyncio.create_task` was called with `compact_session`. This can be verified by patching `asyncio.create_task` and asserting it was called, or by checking that after execution, old messages in the test session are compacted.

### Task 5-7: Tests (specified above in each task)

All test files follow existing project patterns:
- `backend/tests/unit/ai/test_microcompactor.py` -- new file, uses `@pytest.mark.asyncio` and `db_session` fixture
- `backend/tests/unit/services/test_ai_config_service.py` -- append new test class

### Task 8: Quality checks

Run on modified scope only:

```bash
cd backend
uv run mypy app/ai/context/microcompactor.py app/services/ai_config_service.py app/ai/agent_service.py
uv run ruff check app/ai/context/ app/services/ai_config_service.py app/ai/agent_service.py
uv run pytest tests/unit/ai/test_microcompactor.py tests/unit/services/test_ai_config_service.py -v --cov=app.ai.context --cov=app.services.ai_config_service --cov-report=term-missing
```

---

## Test Specification

### Test Hierarchy

```text
tests/
├── unit/
│   ├── ai/
│   │   └── test_microcompactor.py          (NEW -- 8-10 test cases)
│   └── services/
│       └── test_ai_config_service.py       (MODIFY -- add 2-3 test cases)
└── integration/
    └── (no new integration tests -- unit coverage sufficient)
```

### Test Cases

| Test ID | Test Name                                                       | Criterion | Type   | Expected Result                                                                                    |
| ------- | --------------------------------------------------------------- | --------- | ------ | -------------------------------------------------------------------------------------------------- |
| T-001   | `test_compact_session_compacts_old_messages`                    | FC-1      | Unit   | Messages older than keep_recent have tool_results truncated                                        |
| T-002   | `test_compact_tool_results_preserves_structure`                 | FC-2      | Unit   | Output list has same length; each entry has keys {tool, success, result, error}                    |
| T-003   | `test_compact_session_skips_already_compacted`                  | FC-3      | Unit   | Messages with compacted:true in metadata are not processed                                         |
| T-004   | `test_compact_session_preserves_recent_messages`                | FC-4      | Unit   | Last N assistant messages have tool_results unchanged                                              |
| T-005   | `test_compact_session_does_not_touch_user_messages`             | FC-5      | Unit   | User messages remain identical after compaction                                                    |
| T-006   | `test_compaction_runs_as_background_task`                       | FC-6      | Unit   | asyncio.create_task is called; _run_agent_graph returns before compaction completes                |
| T-007   | `test_compact_session_handles_errors_gracefully`                | FC-7      | Unit   | Exception in update_message is caught and logged; other messages still processed                   |
| T-011   | `test_compact_tool_results_reduces_large_payloads`              | TC-4      | Unit   | 5KB payload compacts to <= 2.5KB; result has _truncated:true                                      |
| T-012   | `test_compact_session_performance_50_messages`                  | TC-5      | Unit   | compact_session with 50 messages completes in < 500ms                                              |
| T-013   | `test_update_message_persists_tool_results_and_metadata`        | TC-1/2    | Unit   | update_message() persists changes; metadata merges correctly                                       |
| T-014   | `test_compact_tool_results_small_payload_unchanged`             | FC-2      | Unit   | Tool results under max_result_chars are returned verbatim (no truncation)                          |
| T-015   | `test_compact_session_empty_tool_results`                       | FC-1      | Unit   | Messages with tool_results=null or empty list are skipped without error                            |

### Test Infrastructure Needs

- **Fixtures needed:** Reuse existing `db_session`, `test_ai_provider`, `test_ai_model`, `test_ai_assistant` from `conftest.py`
- **New fixture:** `test_ai_session_with_messages` -- creates an AIConversationSession with N assistant messages containing tool_results of varying sizes. This should be a helper function, not a global fixture, since different tests need different message counts.
- **Database state:** No new tables or migrations required. Uses existing `ai_conversation_messages` table.
- **Mocks/stubs:** `config_service.update_message()` mock for error scenario tests (T-007). Time-dependent assertions for T-012 should use a threshold, not exact values.

---

## Risk Assessment

| Risk Type   | Description                                                          | Probability | Impact | Mitigation                                                                                      |
| ----------- | -------------------------------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------------------------------- |
| Technical   | Background task shares DB session with main request; session may close before compaction finishes | Low         | Medium | Monitor in testing; if it fails, switch to creating a separate AsyncSession in the background task |
| Technical   | Compaction corrupts data needed for frontend Activity Panel          | Low         | Medium | Compact preserves JSON structure; `_truncated` flag makes it clear; recent N messages untouched  |
| Technical   | Race condition: two executions on same session compact simultaneously | Low         | Low    | `compacted: true` flag makes compaction idempotent; same message compacted twice produces same result |
| Integration | Import failure in inline import prevents compaction                  | Low         | Low    | Outer try/except catches and logs; main flow unaffected                                         |
| Technical   | Large number of messages makes list_messages() slow                  | Low         | Low    | Sessions rarely exceed 100 messages; compaction runs after response so latency does not affect UX |

---

## Documentation References

### Required Reading

- AI Chat Developer Guide: `docs/02-architecture/ai-chat-developer-guide.md`
- Coding Standards: `docs/02-architecture/coding-standards.md`
- Analysis: `docs/03-project-plan/iterations/2026-04-03-microcompaction/00-analysis.md`

### Code References

- Existing message persistence pattern: `backend/app/ai/agent_service.py` lines 1080-1124
- Existing service CRUD pattern: `backend/app/services/ai_config_service.py` (e.g., `set_provider_config()` for merge pattern)
- AI entity model: `backend/app/models/domain/ai.py` `AIConversationMessage` class (lines 216-242)
- Test patterns: `backend/tests/unit/ai/test_agent_service.py` and `backend/tests/unit/services/test_ai_config_service.py`
- DB session fixture: `backend/tests/conftest.py` `db_session` fixture (lines 196-269)

---

## Prerequisites

### Technical

- [x] No database migrations required (all changes use existing JSONB columns)
- [x] No new Python dependencies required
- [x] Existing test infrastructure supports the test plan (db_session fixture, AI entity fixtures)

### Documentation

- [x] Analysis phase approved (00-analysis.md)
- [x] Option 1 selected by user
- [x] User confirmed: rule-based compression, no LLM cost, retain JSON structure

---

## File Change Summary

### New Files

| File                                                  | Purpose                              |
| ----------------------------------------------------- | ------------------------------------ |
| `backend/app/ai/context/__init__.py`                  | Package init (can be empty)          |
| `backend/app/ai/context/microcompactor.py`            | Microcompactor class                 |
| `backend/tests/unit/ai/test_microcompactor.py`        | Unit tests for microcompactor        |

### Modified Files

| File                                                | Change                                                | Lines Affected  |
| --------------------------------------------------- | ----------------------------------------------------- | --------------- |
| `backend/app/services/ai_config_service.py`         | Add `update_message()` method                         | ~15 new lines after line 507 |
| `backend/app/ai/agent_service.py`                   | Add microcompaction spawn after message persistence   | ~8 new lines after line 1124 |
| `backend/tests/unit/services/test_ai_config_service.py` | Add tests for `update_message()`                  | ~30-40 new lines appended    |
