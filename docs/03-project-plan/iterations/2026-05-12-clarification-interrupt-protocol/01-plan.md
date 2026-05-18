# Plan: Clarification Interrupt Protocol (ask_user Tool)

**Created:** 2026-05-12
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 -- `ask_user` Supervisor Tool

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 from analysis -- `ask_user` tool for the supervisor orchestrator
- **Architecture**: A new `ask_user` tool that enables two clarification phases: (1) pre-delegation question from supervisor to user, (2) forwarding specialist `open_questions` to user. Uses the same polling pattern as the existing `InterruptNode` approval flow.
- **Key Decisions**:
  - Tool-level blocking (NOT graph-level interrupt/resume) -- follows proven pattern
  - `ask_user` is supervisor-only, NOT available to specialists
  - Polling via event bus + WebSocket, same as approval flow
  - `supervisor_iterations` does NOT increment during clarification
  - Same specialist cannot re-run after clarification (blocked by `completed_specialists` set union)
  - Maximum 4 clarifications per turn (configurable via `MAX_CLARIFICATIONS_PER_TURN`)
  - Clarification answers persisted as distinct chat messages

### Success Criteria

**Functional Criteria:**

- [ ] AC-1: Supervisor can call `ask_user(question, context)` before delegating to any specialist, and the user's answer returns as a tool result VERIFIED BY: unit test + integration test
- [ ] AC-2: After a specialist returns `open_questions` in its findings, the supervisor can forward those questions to the user via `ask_user`, and the answer returns as a tool result VERIFIED BY: integration test
- [ ] AC-3: Frontend renders `clarification_request` as an inline card with text input and submit button within the chat flow (not a modal) VERIFIED BY: component test + E2E test
- [ ] AC-4: User's answer is sent via WebSocket `clarification_response` message and delivered back to the waiting `ask_user` tool VERIFIED BY: unit test
- [ ] AC-5: Clarification count is enforced -- after `MAX_CLARIFICATIONS_PER_TURN` calls, the tool returns an error instead of asking VERIFIED BY: unit test
- [ ] AC-6: Clarification answers are persisted as distinct messages in the chat history (role="user", with clarification metadata) VERIFIED BY: integration test
- [ ] AC-7: Existing approval interrupt flow is not broken -- both approval and clarification can coexist in the same session VERIFIED BY: regression test
- [ ] AC-8: 5-minute timeout on clarification polling -- if no response, tool returns a timeout error VERIFIED BY: unit test

**Technical Criteria:**

- [ ] AC-9: MyPy strict mode passes with zero errors on all new code VERIFIED BY: `uv run mypy app/` on modified files
- [ ] AC-10: Ruff lint passes with zero errors on all new code VERIFIED BY: `uv run ruff check .` on modified files
- [ ] AC-11: New backend code achieves 80%+ test coverage VERIFIED BY: `uv run pytest --cov=app/ai/tools/clarification_tool.py --cov=app/ai/supervisor_orchestrator.py`
- [ ] AC-12: New frontend component achieves 80%+ test coverage VERIFIED BY: `npm run test:coverage`
- [ ] AC-13: `ask_user` tool works within LangGraph's `astream_events()` cycle -- `on_tool_start`/`on_tool_end` events fire correctly VERIFIED BY: integration test

**Business Criteria:**

- [ ] AC-14: Supervisor prompt updated to instruct: (a) check for ambiguity before delegating, (b) review `open_questions` in briefing after specialist completion and forward to user when unresolvable VERIFIED BY: code review

### Scope Boundaries

**In Scope:**

- Backend: `ask_user` tool creation, event bus integration, clarification response registration, supervisor prompt update, `MAX_CLARIFICATIONS_PER_TURN` config setting
- Backend: WS message schemas for `clarification_request` and `clarification_response`
- Backend: WS handler for `clarification_response` message type
- Backend: Clarification answer persistence as chat messages
- Frontend: `ClarificationCard` inline component with text input
- Frontend: `clarification_request`/`clarification_response` types and type guards
- Frontend: Integration into `ChatInterface` message handling
- Tests: Unit tests for `ask_user` tool, integration tests for full clarification flow, component tests for `ClarificationCard`

**Out of Scope:**

- LangGraph native `interrupt()` / `interrupt_before` / `interrupt_after` (deferred -- analysis concluded this is higher risk)
- Mandatory pre-delegation review step (Option 3 from analysis -- over-engineered for simple requests)
- BriefingDocument schema changes (clarifications injected via existing `supervisor_analysis` field)
- Specialist-side changes (the `_SCOPE_BOUNDARY` prompt + `parse_structured_findings()` pipeline already exists)
- Re-running same specialist after clarification (blocked by `completed_specialists` set union -- by design)
- Multi-turn clarification conversations (one question -> one answer per call)
- Clarification in non-supervisor orchestrator modes (Deep Agent, direct tools)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|-----------------|------------|
| 1 | Add `MAX_CLARIFICATIONS_PER_TURN` config setting | `backend/app/core/config.py` | none | Setting exists with default=4, accessible via `settings.MAX_CLARIFICATIONS_PER_TURN` | Low |
| 2 | Add WS clarification message schemas | `backend/app/models/schemas/ai.py` | none | `WSClarificationRequestMessage` and `WSClarificationResponseMessage` are valid Pydantic models; they appear in the `WSMessage` union | Low |
| 3 | Create `ask_user` clarification tool | `backend/app/ai/tools/clarification_tool.py` (NEW) | Task 1, Task 2 | Tool publishes `clarification_request` event, polls for response with 5-min timeout, returns user answer as string; enforces max clarification count | High |
| 4 | Add `register_clarification_response()` to `AgentService` | `backend/app/ai/agent_service.py` | Task 3 | Method stores user's answer in `_pending_clarifications` dict; `ask_user` tool polling detects it | Medium |
| 5 | Handle `clarification_response` in WS handler | `backend/app/api/routes/ai_chat.py` | Task 2, Task 4 | `message_type == "clarification_response"` is handled; answer is forwarded to `AgentService.register_clarification_response()` | Medium |
| 6 | Add `ask_user` to supervisor tools and update prompt | `backend/app/ai/supervisor_orchestrator.py` | Task 3 | `ask_user` appears in `supervisor_tools` list; supervisor prompt includes clarification instructions | Medium |
| 7 | Add clarification event handling in `_run_agent_graph` | `backend/app/ai/agent_service.py` | Task 3 | `clarification_request` events from `ask_user` tool are forwarded to the event bus during streaming; clarification answer is persisted as a chat message | High |
| 8 | Add frontend clarification types and type guards | `frontend/src/features/ai/chat/types.ts` | none | `WSClarificationRequestMessage`, `WSClarificationResponseMessage`, `isClarificationRequestMessage()` type guard exist; `WSServerMessage` union is updated | Low |
| 9 | Create `ClarificationCard` inline component | `frontend/src/features/ai/chat/components/ClarificationCard.tsx` (NEW) | Task 8 | Component renders question text, context text, text input, submit button; sends `clarification_response` via WS callback; shows "waiting" state | Medium |
| 10 | Integrate clarification into `ChatInterface` | `frontend/src/features/ai/chat/components/ChatInterface.tsx` | Task 8, Task 9 | `clarification_request` messages render `ClarificationCard` inline in the chat flow; response is sent via WS | Medium |
| 11 | Backend unit tests | `backend/tests/unit/ai/test_clarification_tool.py` (NEW), `backend/tests/unit/ai/test_clarification_integration.py` (NEW) | Tasks 3-7 | All AC-1 through AC-8 test specifications pass | High |
| 12 | Frontend component tests | `frontend/src/features/ai/chat/components/__tests__/ClarificationCard.test.tsx` (NEW) | Tasks 9-10 | Component renders correctly; submit sends response; disabled state while waiting | Medium |
| 13 | Regression test -- approval flow still works | `backend/tests/unit/ai/test_approval_regression.py` (NEW) | Tasks 3-7 | Existing approval flow tests pass without modification; approval + clarification can coexist | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| AC-1: Pre-delegation clarification | T-001 | `tests/unit/ai/test_clarification_tool.py` | `ask_user` publishes `clarification_request` event; polling returns user answer as string |
| AC-2: Specialist -> human forwarding | T-002 | `tests/unit/ai/test_clarification_tool.py` | Supervisor reads `open_questions` from briefing, calls `ask_user`, answer returns |
| AC-3: Frontend inline card | T-003 | `components/__tests__/ClarificationCard.test.tsx` | Card renders question, context, input, button; submit fires callback |
| AC-4: WS round-trip | T-004 | `tests/unit/ai/test_clarification_integration.py` | WS `clarification_response` message triggers `register_clarification_response()`, polling detects it |
| AC-5: Max clarification count | T-005 | `tests/unit/ai/test_clarification_tool.py` | After 4 calls, 5th call returns error string instead of asking |
| AC-6: Answer persistence | T-006 | `tests/unit/ai/test_clarification_integration.py` | After clarification completes, answer appears as a message with role="user" and clarification metadata |
| AC-7: Approval coexistence | T-007 | `tests/unit/ai/test_approval_regression.py` | Approval flow tests pass unchanged; interrupt node unaffected |
| AC-8: Timeout | T-008 | `tests/unit/ai/test_clarification_tool.py` | After 5 minutes with no response, tool returns timeout error string |
| AC-9: MyPy strict | T-009 | CI pipeline | `uv run mypy app/ai/tools/clarification_tool.py` passes |
| AC-10: Ruff clean | T-010 | CI pipeline | `uv run ruff check app/ai/tools/clarification_tool.py` passes |
| AC-13: astream_events compat | T-011 | `tests/unit/ai/test_clarification_integration.py` | `on_tool_start` fires for `ask_user`; `on_tool_end` fires when answer returns |

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/ai/
│   ├── test_clarification_tool.py       # ask_user tool unit tests
│   ├── test_clarification_integration.py # AgentService + WS handler integration
│   └── test_approval_regression.py       # Approval flow not broken
├── frontend/
│   └── components/__tests__/
│       └── ClarificationCard.test.tsx    # Component rendering + interaction
└── (existing tests must continue to pass)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
|---|---|---|---|---|
| T-001 | `test_ask_user_publishes_clarification_request` | AC-1 | Unit | `ask_user("Which project?", "User asked about status")` publishes `AgentEvent(event_type="clarification_request")` with question and context in data |
| T-001b | `test_ask_user_returns_user_answer` | AC-1 | Unit | After answer is registered in `_pending_clarifications`, next poll iteration returns the answer string |
| T-002 | `test_ask_user_for_specialist_open_questions` | AC-2 | Unit | Supervisor reads briefing with `open_questions=["Which WBE?"], calls `ask_user`, answer returns |
| T-003 | `test_clarification_card_renders_question` | AC-3 | Component | `ClarificationCard` renders the question text, context text, a textarea, and a submit button |
| T-003b | `test_clarification_card_submit_sends_response` | AC-3 | Component | Clicking submit calls `onSubmit` callback with the entered answer text |
| T-003c | `test_clarification_card_disabled_while_waiting` | AC-3 | Component | After submit, textarea and button are disabled; "waiting" indicator shown |
| T-004 | `test_ws_clarification_response_round_trip` | AC-4 | Integration | WS handler receives `{"type": "clarification_response", ...}`, calls `register_clarification_response()`, tool polling returns answer |
| T-005 | `test_ask_user_enforces_max_count` | AC-5 | Unit | After `MAX_CLARIFICATIONS_PER_TURN` calls, next call returns `"Maximum clarification questions reached (4). Proceeding with available information."` |
| T-005b | `test_ask_user_count_resets_per_turn` | AC-5 | Unit | Count is per-execution (per `_run_agent_graph` call), not global |
| T-006 | `test_clarification_answer_persisted_as_message` | AC-6 | Integration | After clarification completes, `config_service.add_message()` was called with role="user" and metadata containing `{"clarification": true, "question": "...", "clarification_id": "..."}` |
| T-007 | `test_approval_flow_unchanged_with_clarification` | AC-7 | Regression | Existing approval test suite passes without any modifications |
| T-008 | `test_ask_user_timeout_returns_error` | AC-8 | Unit | When polling exceeds `AI_APPROVAL_TIMEOUT_SECONDS` with no response, tool returns `"Clarification timed out. Proceeding with available information."` |
| T-011 | `test_ask_user_produces_tool_events` | AC-13 | Integration | During `astream_events()`, `on_tool_start(name="ask_user")` and `on_tool_end` events fire correctly |

### Test Infrastructure Needs

- **Fixtures**: Mock `AgentEventBus` with controllable publish/subscribe; mock `_pending_clarifications` dict; mock WebSocket connection
- **Mocks**: `config_service.add_message()` for persistence verification; `AgentService.register_clarification_response()` for WS handler tests
- **Database state**: No special seed data needed -- clarification does not touch domain entities

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | `ask_user` tool blocks within `astream_events()` -- LangGraph may have a timeout for long-running tools | Low | High | The approval polling pattern already proves tool-level blocking works within `astream_events()`; the existing 5-minute timeout in `InterruptNode` is the same mechanism |
| Technical | Clarification and approval both use polling on the same event bus -- event type collision or handler confusion | Low | Medium | Event types are distinct strings (`clarification_request` vs `approval_request`); handler routing is by `message_type` field |
| Integration | WebSocket disconnect during clarification wait -- user closes browser tab | Medium | Low | Same as approval: 5-minute timeout returns error to supervisor, which synthesizes from available context; no state corruption risk |
| Integration | Supervisor calls `ask_user` but user never responds (ignores the card) | Medium | Low | 5-minute timeout returns error string; supervisor proceeds with available information and notes the ambiguity in its response |
| Frontend | Multiple clarification cards appear simultaneously if supervisor calls `ask_user` multiple times | Low | Medium | `MAX_CLARIFICATIONS_PER_TURN` limits to 4; each card has a unique `clarification_id`; frontend renders them sequentially |
| Regression | New `ask_user` tool appears in specialist tool lists by mistake | Low | High | `ask_user` is explicitly added to `supervisor_tools` only, never passed to specialist compilation; explicit test to verify specialists cannot call it |

---

## Prerequisites

### Technical

- [x] No database migrations needed (clarification state is in-memory, no new tables)
- [x] Dependencies installed (all existing; no new packages)
- [x] Environment configured (new `MAX_CLARIFICATIONS_PER_TURN` env var with default=4)

### Documentation

- [x] Analysis phase approved (Option 1)
- [x] Existing patterns reviewed: `InterruptNode`, `AgentEventBus`, `WSApprovalRequestMessage`
- [x] Supervisor orchestrator architecture understood

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  # === Level 0: Independent foundation tasks ===
  - id: BE-001
    name: "Add MAX_CLARIFICATIONS_PER_TURN config setting"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add WS clarification message schemas (WSClarificationRequestMessage, WSClarificationResponseMessage)"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: FE-001
    name: "Add frontend clarification types, type guards, and update WSServerMessage union"
    agent: pdca-frontend-do-executor
    dependencies: []

  # === Level 1: Core tool depends on config + schemas ===
  - id: BE-003
    name: "Create ask_user clarification tool (clarification_tool.py)"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  # === Level 2: Integration depends on tool ===
  - id: BE-004
    name: "Add register_clarification_response() to AgentService and wire into _run_agent_graph"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-005
    name: "Handle clarification_response in WebSocket handler (ai_chat.py)"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-004]

  - id: BE-006
    name: "Add ask_user to supervisor tools and update supervisor prompt"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  # === Level 3: Frontend UI depends on types ===
  - id: FE-002
    name: "Create ClarificationCard inline component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Integrate clarification into ChatInterface message handling"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  # === Level 4: Tests depend on all implementation ===
  - id: BE-007
    name: "Backend unit tests for ask_user tool (happy path, max count, timeout)"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004, BE-005, BE-006]
    kind: test

  - id: BE-008
    name: "Backend integration tests (WS round-trip, answer persistence, astream_events compat)"
    agent: pdca-backend-do-executor
    dependencies: [BE-007]
    kind: test

  - id: BE-009
    name: "Regression test -- approval flow still works with clarification present"
    agent: pdca-backend-do-executor
    dependencies: [BE-007]
    kind: test

  - id: FE-004
    name: "Frontend component tests for ClarificationCard"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]
    kind: test
```

---

## Documentation References

### Required Reading

- Supervisor Orchestrator: `docs/02-architecture/ai/supervisor-orchestrator.md`
- Agent Common Concepts: `docs/02-architecture/ai/agent-common-concepts.md`
- Coding Standards: `docs/02-architecture/coding-standards.md`

### Code References

- Approval polling pattern: `backend/app/ai/tools/interrupt_node.py` (lines 162-245 for `_send_approval_request`, `_check_approval`, `register_approval_response`)
- Event bus: `backend/app/ai/execution/agent_event_bus.py`
- Agent event: `backend/app/ai/execution/agent_event.py`
- WS message schemas: `backend/app/models/schemas/ai.py` (lines 746-876 for approval schemas)
- WS handler: `backend/app/api/routes/ai_chat.py` (lines 729-778 for approval response handling)
- Supervisor graph construction: `backend/app/ai/supervisor_orchestrator.py` (lines 251-264 for supervisor tools list)
- Handoff tool pattern: `backend/app/ai/handoff_tools.py` (for how supervisor-only tools are structured)
- Frontend types: `frontend/src/features/ai/chat/types.ts` (for WS type patterns)
- Frontend approval dialog: `frontend/src/features/ai/components/ApprovalDialog.tsx` (for approval UI pattern reference, but clarification card is inline, not modal)
- Backend config: `backend/app/core/config.py` (for settings pattern)
