# Plan: Conversation History Windowing

**Created:** 2026-04-03
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 -- DB-Level Windowing (SQL LIMIT)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 (DB-Level Windowing) from analysis
- **Architecture**: Add `max_context_turns` column to `AIAssistantConfig`. Modify `list_messages()` to accept a `limit` parameter with a subquery-based approach to fetch the N most recent messages (avoiding the wrong-message pitfall described in analysis Decision Question 3). Modify `_build_conversation_history()` to compute a message limit from the config, request windowed messages, and prepend a static truncation summary when older messages are omitted.
- **Key Decisions**:
  - Default window = 20 turns (40 messages) when `max_context_turns` is NULL
  - Use subquery pattern in `list_messages()` to get the N most recent messages ordered chronologically
  - Summary placeholder: simple count string, no LLM summarization
  - System prompt is NOT counted against the turn window
  - The current user message (the one that triggered the invocation) is always included

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: `_build_conversation_history()` returns only the most recent N turns when `max_context_turns` is set, where 1 turn = 1 user + 1 assistant message VERIFIED BY: unit test
- [ ] FC-2: When `max_context_turns` is NULL, the default of 20 turns (40 messages) is applied VERIFIED BY: unit test
- [ ] FC-3: When total messages are within the window limit, all messages are returned with no truncation summary VERIFIED BY: unit test
- [ ] FC-4: When messages are truncated, a `SystemMessage` prefix is prepended indicating the count of omitted messages VERIFIED BY: unit test
- [ ] FC-5: Tool messages are excluded from the windowed count and result (existing behavior preserved) VERIFIED BY: unit test
- [ ] FC-6: Both execution paths (`_chat_impl` at line 487 and `_run_agent_graph` at line 645) apply windowing identically VERIFIED BY: unit test + manual verification
- [ ] FC-7: `max_context_turns` is persisted via the standard assistant config CRUD API (create/update) VERIFIED BY: integration test
- [ ] FC-8: `list_messages()` with `limit=None` returns all messages (backward compatible) VERIFIED BY: existing tests pass unchanged

**Technical Criteria:**

- [ ] TC-1: Performance: DB-level LIMIT avoids loading unnecessary rows for long sessions VERIFIED BY: SQL query review (EXPLAIN plan)
- [ ] TC-2: Code Quality: MyPy strict + Ruff clean on all modified files VERIFIED BY: CI pipeline
- [ ] TC-3: Test coverage >= 80% on all new/modified code VERIFIED BY: pytest --cov

**TDD Criteria:**

- [ ] TDD-1: All test cases written before implementation code
- [ ] TDD-2: Each test failed first (documented in DO phase log)
- [ ] TDD-3: Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Add `max_context_turns` column to `AIAssistantConfig` model + Alembic migration
- Add `max_context_turns` to Pydantic schemas (Base, Create, Update, Public)
- Add `limit` parameter to `AIConfigService.list_messages()` with subquery pattern
- Modify `_build_conversation_history()` to accept `assistant_config`, compute limit, call windowed `list_messages()`, prepend truncation summary
- Update both call sites (`_chat_impl` line 487, `_run_agent_graph` line 645) to pass `assistant_config`
- Update existing tests to mock `config_service.list_messages` instead of non-existent `_get_session_messages`
- Add new unit tests for windowing behavior
- Pass `recursion_limit` and `max_context_turns` through in `create_assistant_config` service method (existing gap that must be fixed since we touch the same code)

**Out of Scope:**

- LLM-based conversation summarization (future concern)
- Frontend changes (the `max_context_turns` field is backend-only configuration)
- Token counting / estimation (turns-based window is sufficient)
- Caching of conversation history
- New module/directory for windowing logic (unnecessary per analysis recommendation)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 1 | Add `max_context_turns` column to `AIAssistantConfig` model | `backend/app/models/domain/ai.py` (line ~140) | None | Column defined as `Mapped[int \| None]`, nullable, no server default | Low |
| 2 | Create Alembic migration for new column | `backend/alembic/versions/` (new file) | Task 1 | Migration adds nullable INTEGER column `max_context_turns` to `ai_assistant_configs` | Low |
| 3 | Add `max_context_turns` to Pydantic schemas | `backend/app/models/schemas/ai.py` (lines 169-212) | None | Field present in Base, Create, Update, Public schemas with correct type and validation (ge=1, le=1000) | Low |
| 4 | Add `limit` parameter to `list_messages()` with subquery | `backend/app/services/ai_config_service.py` (lines 465-473) | None | When limit is set, returns only the N most recent messages in chronological order; when limit is None, returns all (backward compatible) | Medium |
| 5 | Modify `_build_conversation_history()` for windowing | `backend/app/ai/agent_service.py` (lines 1382-1407) | Tasks 1, 4 | Accepts `assistant_config`, computes message limit, calls windowed `list_messages()`, prepends summary | Medium |
| 6 | Update call sites to pass `assistant_config` | `backend/app/ai/agent_service.py` (lines 487, 645) | Task 5 | Both `_chat_impl` and `_run_agent_graph` pass `assistant_config` to `_build_conversation_history` | Low |
| 7 | Fix `create_assistant_config` to pass `recursion_limit` and `max_context_turns` | `backend/app/services/ai_config_service.py` (lines 308-317) | Task 1 | Constructor includes both fields | Low |
| 8 | Update existing tests + add new windowing tests | `backend/tests/unit/ai/test_agent_service.py` (lines 317-440) | Tasks 5, 6 | Existing tests fixed to mock correct method; new tests for FC-1 through FC-6 | Medium |
| 9 | Run quality checks | All modified files | Tasks 1-8 | MyPy strict zero errors, Ruff zero errors, all tests pass | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| FC-1 | T-001 | `tests/unit/ai/test_agent_service.py` | Windowed history returns only last N turns |
| FC-2 | T-002 | `tests/unit/ai/test_agent_service.py` | NULL max_context_turns uses default of 20 |
| FC-3 | T-003 | `tests/unit/ai/test_agent_service.py` | Messages within window returned in full, no summary |
| FC-4 | T-004 | `tests/unit/ai/test_agent_service.py` | Truncated history has SystemMessage summary prefix |
| FC-5 | T-005 | `tests/unit/ai/test_agent_service.py` | Tool messages excluded from count and result |
| FC-6 | T-006 | `tests/unit/ai/test_agent_service.py` | Both call sites verified via integration |
| FC-7 | T-007 | `tests/unit/ai/test_agent_service.py` or integration | Create/update assistant config persists max_context_turns |
| FC-8 | T-008 | `tests/unit/ai/test_agent_service.py` | list_messages(limit=None) returns all messages |

---

## Detailed Implementation Specification

### Task 1: Add `max_context_turns` to Domain Model

**File:** `backend/app/models/domain/ai.py`
**Location:** After `recursion_limit` field (line 140), before `allowed_tools`

**Change:** Add one new mapped column:

```python
# Maximum conversation turns to include in LLM context (1 turn = 1 user + 1 assistant message)
# NULL means use the application default (20 turns)
max_context_turns: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Import:** `Integer` is already imported on line 16.

### Task 2: Alembic Migration

**Command:** `cd backend && uv run alembic revision --autogenerate -m "add_max_context_turns_to_assistant_config"`

**Expected migration content:**
- `op.add_column('ai_assistant_configs', sa.Column('max_context_turns', sa.Integer(), nullable=True))`
- No server default (NULL = use application default of 20)
- Downgrade: `op.drop_column('ai_assistant_configs', 'max_context_turns')`

**Verification:** `uv run alembic upgrade head` succeeds, column exists in `ai_assistant_configs` table.

### Task 3: Pydantic Schemas

**File:** `backend/app/models/schemas/ai.py`

**3a. `AIAssistantConfigBase` (line 169):**
Add after `recursion_limit` field (line 178), before `allowed_tools`:

```python
max_context_turns: int | None = Field(
    None,
    ge=1,
    le=1000,
    description="Maximum conversation turns to include in LLM context (NULL = default 20)",
)
```

**3b. `AIAssistantConfigUpdate` (line 191):**
Add after `recursion_limit` field (line 199), before `allowed_tools`:

```python
max_context_turns: int | None = Field(
    None, ge=1, le=1000, description="Maximum conversation turns for LLM context"
)
```

**3c. No changes needed to `AIAssistantConfigCreate`** -- it inherits from `Base`, so it automatically gets the new field.

**3d. No changes needed to `AIAssistantConfigPublic`** -- it inherits from `Base`, so it automatically gets the new field.

### Task 4: Add `limit` Parameter to `list_messages()`

**File:** `backend/app/services/ai_config_service.py`
**Location:** Lines 465-473

**Current signature:**
```python
async def list_messages(self, session_id: UUID) -> list[AIConversationMessage]:
```

**New signature:**
```python
async def list_messages(
    self, session_id: UUID, limit: int | None = None
) -> list[AIConversationMessage]:
```

**Implementation approach -- subquery pattern:**

The current query does `ORDER BY created_at` which returns oldest-first. A naive `LIMIT` would return the oldest N messages, which is the opposite of what we need. The solution is a subquery that selects the N most recent message IDs, then the outer query fetches those messages in chronological order.

```python
async def list_messages(
    self, session_id: UUID, limit: int | None = None
) -> list[AIConversationMessage]:
    """List messages in a session.

    Args:
        session_id: Session to list messages for
        limit: Maximum number of messages to return (most recent).
               None = return all messages.

    Returns:
        Messages ordered chronologically (oldest first).
    """
    if limit is not None:
        # Subquery: get the IDs of the N most recent messages
        recent_ids = (
            select(AIConversationMessage.id)
            .where(AIConversationMessage.session_id == session_id)
            .order_by(AIConversationMessage.created_at.desc())
            .limit(limit)
            .correlate(AIConversationMessage)
            .subquery()
        )
        # Outer query: fetch those messages in chronological order
        stmt = (
            select(AIConversationMessage)
            .where(AIConversationMessage.id.in_(select(recent_ids.c.id)))
            .order_by(AIConversationMessage.created_at)
        )
    else:
        stmt = (
            select(AIConversationMessage)
            .where(AIConversationMessage.session_id == session_id)
            .order_by(AIConversationMessage.created_at)
        )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

**Key constraint:** The `limit` parameter counts ALL messages (user + assistant + tool). The caller is responsible for computing the appropriate limit based on turns. Tool messages are skipped downstream in `_build_conversation_history` as they are today.

### Task 5: Modify `_build_conversation_history()` for Windowing

**File:** `backend/app/ai/agent_service.py`
**Location:** Lines 1382-1407

**Current signature:**
```python
async def _build_conversation_history(self, session_id: UUID) -> list[BaseMessage]:
```

**New signature:**
```python
async def _build_conversation_history(
    self, session_id: UUID, assistant_config: AIAssistantConfig | None = None
) -> list[BaseMessage]:
```

The parameter is optional with default None to maintain backward compatibility during incremental migration. Both call sites will be updated immediately in Task 6.

**Implementation specification:**

1. Define a module-level constant: `DEFAULT_MAX_CONTEXT_TURNS = 20`

2. In the method body:
   a. Determine `max_turns` from `assistant_config.max_context_turns` if provided, else use `DEFAULT_MAX_CONTEXT_TURNS`
   b. Compute `message_limit = max_turns * 2` (each turn is user + assistant)
   c. Add a buffer multiplier (e.g., `message_limit * 2`) to account for tool messages that will be filtered out downstream. This ensures we fetch enough rows so that after filtering tools, we still have the desired number of turns.
   d. Call `self.config_service.list_messages(session_id, limit=message_limit_with_buffer)`
   e. Count total messages in the session via a new helper or by comparing with the fetched count. The simplest approach: call `list_messages(session_id, limit=None)` when we detect truncation (i.e., returned count == limit). But this causes a second query. The more efficient approach: fetch with limit; if the result length equals the limit (meaning there MIGHT be more), prepend the summary. This avoids a second query at the cost of an imprecise omitted count (we know "at least N messages were omitted" but not the exact total).
   f. **Decision**: Use the efficient approach. The summary will say `"[Earlier conversation history omitted. {total_fetched} most recent messages shown.]"` when truncation is detected. This avoids a COUNT(*) query and is sufficient for the MVP placeholder.

3. Truncation detection: If `limit` was applied and the returned message count equals `message_limit_with_buffer`, there MAY be older messages. Prepend the summary.

4. The conversion loop (user -> HumanMessage, assistant -> AIMessage, tool -> skip) remains unchanged.

**Revised method body specification:**

```python
# Module-level constant (near top of file or near the method)
DEFAULT_MAX_CONTEXT_TURNS = 20

async def _build_conversation_history(
    self, session_id: UUID, assistant_config: AIAssistantConfig | None = None
) -> list[BaseMessage]:
    """Build windowed conversation history from session messages.

    Args:
        session_id: The session ID corresponding to the current conversation
        assistant_config: Optional assistant config for window sizing.
            If None, no windowing is applied (backward compatible).

    Returns:
        List of LangChain BaseMessage instances. When windowing is active and
        older messages are truncated, a SystemMessage summary is prepended.
    """
    # Determine window size
    if assistant_config is not None:
        max_turns = assistant_config.max_context_turns or DEFAULT_MAX_CONTEXT_TURNS
        message_limit = max_turns * 2
        # 2x buffer: account for tool messages that will be filtered out
        db_limit = message_limit * 2
    else:
        max_turns = None
        db_limit = None

    messages: list[BaseMessage] = []
    db_messages = await self.config_service.list_messages(session_id, limit=db_limit)

    # Detect truncation: if we got exactly db_limit messages, older ones exist
    truncated = db_limit is not None and len(db_messages) >= db_limit

    # Convert to LangChain messages
    for msg in db_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
        elif msg.role == "tool":
            pass  # Skip tool messages in history - they're implicit

    # Truncate to exact turn window if needed (after filtering tools)
    if max_turns is not None and len(messages) > message_limit:
        messages = messages[-message_limit:]
        truncated = True

    # Prepend truncation summary
    if truncated:
        summary = SystemMessage(
            content="[Earlier conversation history omitted. "
                    f"{len(messages)} most recent messages shown.]"
        )
        messages.insert(0, summary)

    return messages
```

### Task 6: Update Call Sites

**File:** `backend/app/ai/agent_service.py`

**6a. `_chat_impl` call site (line 487):**

Current:
```python
history = await self._build_conversation_history(session_id)
```

New:
```python
history = await self._build_conversation_history(session_id, assistant_config)
```

`assistant_config` is available as a parameter of `_chat_impl` (line 448).

**6b. `_run_agent_graph` call site (line 645):**

Current:
```python
history = await self._build_conversation_history(session_id)
```

New:
```python
history = await self._build_conversation_history(session_id, assistant_config)
```

`assistant_config` is available as a parameter of `_run_agent_graph` (line 610).

### Task 7: Fix `create_assistant_config` Service Method

**File:** `backend/app/services/ai_config_service.py`
**Location:** Lines 308-317

The current constructor does not pass `recursion_limit`. Since we are touching this method to add `max_context_turns`, we should also pass `recursion_limit` through.

**Current:**
```python
config = AIAssistantConfig(
    name=config_in.name,
    description=config_in.description,
    model_id=config_in.model_id,
    system_prompt=config_in.system_prompt,
    temperature=config_in.temperature,
    max_tokens=config_in.max_tokens,
    allowed_tools=config_in.allowed_tools,
    is_active=config_in.is_active,
)
```

**New:**
```python
config = AIAssistantConfig(
    name=config_in.name,
    description=config_in.description,
    model_id=config_in.model_id,
    system_prompt=config_in.system_prompt,
    temperature=config_in.temperature,
    max_tokens=config_in.max_tokens,
    recursion_limit=config_in.recursion_limit,
    max_context_turns=config_in.max_context_turns,
    allowed_tools=config_in.allowed_tools,
    is_active=config_in.is_active,
)
```

### Task 8: Test Plan

**File:** `backend/tests/unit/ai/test_agent_service.py`

**8a. Fix existing tests (lines 317-440):**

The existing tests mock `_get_session_messages` which does not exist in production. They need to be updated to mock `config_service.list_messages` instead. Specifically:

- `TestBuildConversationHistory` (line 318): Replace `patch.object(service, "_get_session_messages", ...)` with `patch.object(service.config_service, "list_messages", ...)`.
- `TestGetSessionMessages` (line 374): This class tests a method that does not exist. It should be removed or rewritten to test `config_service.list_messages` instead.
- All other tests that mock `_get_session_messages` (lines 435, 510): Same fix.

**8b. New test cases:**

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | `test_build_history_windowed_returns_last_n_turns` | FC-1 | Unit | Given 50 messages (25 turns) and max_context_turns=10, returns 20 messages (10 turns) |
| T-002 | `test_build_history_null_config_uses_default_20_turns` | FC-2 | Unit | Given max_context_turns=None, applies default of 20 turns (40 message limit) |
| T-003 | `test_build_history_within_window_returns_all` | FC-3 | Unit | Given 10 messages and max_context_turns=20, returns all 10 with no summary |
| T-004 | `test_build_history_truncated_prepends_summary` | FC-4 | Unit | Given 50 messages and max_context_turns=10, first element is SystemMessage with truncation text |
| T-005 | `test_build_history_excludes_tool_messages_from_count` | FC-5 | Unit | Given messages including tool roles, tool messages are not in output |
| T-006 | `test_build_history_no_config_no_windowing` | FC-8 | Unit | Given assistant_config=None, returns all messages (backward compat) |
| T-007 | `test_list_messages_with_limit_returns_recent` | FC-1 | Unit | `list_messages(session_id, limit=4)` returns the 4 most recent messages in chronological order |
| T-008 | `test_list_messages_without_limit_returns_all` | FC-8 | Unit | `list_messages(session_id)` returns all messages (existing behavior) |

**8c. Test fixture needs:**

- A helper to create a list of `AIConversationMessage` objects with specified roles and a mock `AIAssistantConfig` with configurable `max_context_turns`.
- Mock `self.config_service.list_messages` to return controlled message lists.
- No database fixtures needed for unit tests -- all mocking.

---

## Test Specification

### Test Hierarchy

```
tests/unit/ai/
  test_agent_service.py
  ├── TestBuildConversationHistory (existing -- update mocks)
  │   ├── test_build_history_with_messages (existing -- fix mock target)
  │   ├── test_build_history_empty_session (existing -- fix mock target)
  │   ├── test_build_history_windowed_returns_last_n_turns (NEW T-001)
  │   ├── test_build_history_null_config_uses_default_20_turns (NEW T-002)
  │   ├── test_build_history_within_window_returns_all (NEW T-003)
  │   ├── test_build_history_truncated_prepends_summary (NEW T-004)
  │   ├── test_build_history_excludes_tool_messages_from_count (NEW T-005)
  │   └── test_build_history_no_config_no_windowing (NEW T-006)
  └── TestListMessagesWindowing (NEW)
      ├── test_list_messages_with_limit_returns_recent (NEW T-007)
      └── test_list_messages_without_limit_returns_all (NEW T-008)
```

### Test Infrastructure Needs

- **Fixtures**: `mock_assistant_config` fixture with configurable `max_context_turns` attribute
- **Mocks**: `service.config_service.list_messages` for agent service tests; `session.execute` for config service tests
- **Database state**: No seed data required for unit tests; migration verified via Alembic upgrade head

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Subquery in `list_messages()` may perform poorly on very large message tables | Low | Low | The subquery targets a single session (filtered by `session_id`), so the result set is bounded. Add a composite index on `(session_id, created_at DESC)` if needed. |
| Technical | 2x buffer in `_build_conversation_history` may not account for extreme tool-message ratios | Low | Low | Post-filter truncation (`messages = messages[-message_limit:]`) is a safety net that handles this case. |
| Integration | Existing tests mock `_get_session_messages` which does not exist in production -- tests must be realigned | High | Medium | Task 8a explicitly addresses this. All existing tests will be fixed as part of this plan. |
| Regression | Adding `assistant_config` parameter to `_build_conversation_history` may break callers that don't pass it | Low | Low | Parameter is optional with default None; backward compatible. Both call sites are updated in Task 6. |
| Migration | Alembic autogenerate may detect other schema drift | Medium | Low | Review generated migration before applying; only commit the `max_context_turns` column addition. |

---

## Prerequisites

### Technical

- [ ] PostgreSQL running (`docker-compose up -d postgres`)
- [ ] Backend dependencies installed (`uv sync`)
- [ ] Current Alembic head applied (`uv run alembic upgrade head`)

### Documentation

- [x] Analysis phase approved (Option 1 selected)
- [x] Decision questions answered by user (default=20, subquery approach, simple count placeholder)
- [x] Architecture docs reviewed (AI bounded context, SimpleEntityBase pattern)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
# Conversation History Windowing -- Backend-only change, no frontend tasks
tasks:
  - id: BE-001
    name: "Add max_context_turns to domain model + Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Create Alembic migration for max_context_turns column"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Add limit parameter to list_messages() with subquery pattern"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-004
    name: "Modify _build_conversation_history() for windowing + update call sites"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-003]

  - id: BE-005
    name: "Fix create_assistant_config to pass recursion_limit and max_context_turns"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-006
    name: "Update existing tests + add new windowing tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004]

  - id: BE-007
    name: "Run quality checks (MyPy, Ruff, pytest) on modified scope"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-005, BE-006]
    kind: test
```

**Execution notes for orchestrator:**

- BE-001 and BE-003 have no dependencies and can run in parallel.
- BE-002 (migration) depends only on BE-001 (model change) and is needed before integration testing but not before unit test writing (tests mock the DB layer).
- BE-006 (tests) depends on BE-003 and BE-004 because tests verify the new signatures.
- BE-007 (quality checks) is the final gate and depends on all implementation tasks.

---

## Documentation References

### Required Reading

- AI Chat Developer Guide: `docs/02-architecture/ai-chat-developer-guide.md`
- Backend Coding Standards: `docs/02-architecture/backend/coding-standards.md`

### Code References

- Domain model pattern: `backend/app/models/domain/ai.py` (AIAssistantConfig class, line 120)
- Pydantic schema pattern: `backend/app/models/schemas/ai.py` (recursion_limit field as model for new field)
- Service method pattern: `backend/app/services/ai_config_service.py` (list_messages, line 465)
- Agent service: `backend/app/ai/agent_service.py` (_build_conversation_history, line 1382)
- Existing tests: `backend/tests/unit/ai/test_agent_service.py` (TestBuildConversationHistory, line 317)
