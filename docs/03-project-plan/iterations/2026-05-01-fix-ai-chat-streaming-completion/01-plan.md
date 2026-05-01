# Plan: Fix AI Chat Streaming Completion

**Created:** 2026-05-01
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 -- Fix backend event ordering + frontend `activeExecutionId` guard + stale-streaming timeout

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 from analysis
- **Architecture**: Three surgical changes across backend and frontend to fix the event ordering root cause and add two defensive guards
- **Key Decisions**:
  1. Swap `execution_status` to publish BEFORE `complete`/`error` in `agent_service.py` (both success and error paths)
  2. Add `recentlyCompletedRef` in `useStreamingChat.ts` to prevent the `activeExecutionId` effect from closing the WebSocket after a completion event
  3. Add a 15-second stale-streaming timeout in `ChatInterface.tsx` as a safety net for edge cases where events are lost

### Success Criteria

**Functional Criteria:**

- [ ] AC-1: After an AI response completes, `isStreaming` transitions to `false` within 2 seconds VERIFIED BY: manual E2E test + backend unit test
- [ ] AC-2: After completion, the stop button disappears and the textarea re-enables VERIFIED BY: manual E2E observation
- [ ] AC-3: Users can send follow-up messages without page refresh after a completion VERIFIED BY: manual E2E test (send message, wait for completion, send another message)
- [ ] AC-4: The `execution_status` event with `status: "completed"` is forwarded to the frontend BEFORE the `complete` event VERIFIED BY: backend unit test on event ordering
- [ ] AC-5: The `execution_status` event with `status: "error"` is forwarded to the frontend BEFORE the `error` event VERIFIED BY: backend unit test on error path ordering
- [ ] AC-6: If `isStreaming` stays `true` for 15 seconds with no activity, all streaming state is force-cleared VERIFIED BY: frontend unit test with fake timers

**Technical Criteria:**

- [ ] AC-7: Backend: MyPy strict mode passes on `agent_service.py` VERIFIED BY: `uv run mypy app/ai/agent_service.py`
- [ ] AC-8: Backend: Ruff passes on `agent_service.py` VERIFIED BY: `uv run ruff check app/ai/agent_service.py`
- [ ] AC-9: Frontend: TypeScript strict mode passes on modified files VERIFIED BY: `npm run typecheck`
- [ ] AC-10: Frontend: ESLint passes on modified files VERIFIED BY: `npm run lint`
- [ ] AC-11: The `activeExecutionId` effect does NOT close the WebSocket within 5 seconds of `onComplete` being called VERIFIED BY: frontend unit test

### Scope Boundaries

**In Scope:**

- Swap `_publish("execution_status")` before `_publish("complete")` in `agent_service.py` success path (lines ~1801-1810)
- Swap `event_bus.publish("execution_status")` before `event_bus.publish("error")` in `agent_service.py` error path (lines ~1970-1991)
- Add `recentlyCompletedRef` to `useStreamingChat.ts` and guard the `activeExecutionId` effect (lines ~1111-1122)
- Add stale-streaming timeout `useEffect` to `ChatInterface.tsx`

**Out of Scope:**

- Refactoring the WebSocket connection lifecycle
- Changing the `forward_bus_events` loop break logic
- Adding reconnection retry logic
- Handling the reconnection-to-completed-execution scenario (separate issue)
- Any changes to the event bus or runner manager

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                                         | Files                                                    | Dependencies  | Success Criteria                                             | Complexity |
| --- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------- | ------------------------------------------------------------ | ---------- |
| 1   | Swap `execution_status` publish order before `complete` and `error` in `agent_service.py`    | `backend/app/ai/agent_service.py`                        | none          | AC-4, AC-5: `execution_status` arrives before `complete`/`error` | Low        |
| 2   | Add `recentlyCompletedRef` guard to `activeExecutionId` effect in `useStreamingChat.ts`      | `frontend/src/features/ai/chat/api/useStreamingChat.ts`  | none          | AC-11: WebSocket not closed within 5s of completion          | Low        |
| 3   | Add stale-streaming timeout `useEffect` in `ChatInterface.tsx`                               | `frontend/src/features/ai/chat/components/ChatInterface.tsx` | none          | AC-6: Streaming force-cleared after 15s idle                | Low        |
| 4   | Backend tests for event ordering                                                             | `backend/tests/unit/ai/test_agent_service_events.py`     | Task 1        | AC-4, AC-5 verified by automated tests                      | Medium     |
| 5   | Frontend tests for `recentlyCompletedRef` guard and stale-streaming timeout                  | `frontend/src/features/ai/chat/` tests                   | Tasks 2, 3    | AC-11, AC-6 verified by automated tests                     | Medium     |
| 6   | Integration verification: full E2E chat flow                                                 | manual                                                   | Tasks 1-5     | AC-1, AC-2, AC-3                                            | Low        |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File / Location                                          | Expected Behavior                                                             |
| -------------------- | ------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| AC-4                 | T-001   | `backend/tests/unit/ai/test_agent_service_events.py`         | `_run_agent_graph` publishes `execution_status` before `complete`             |
| AC-5                 | T-002   | `backend/tests/unit/ai/test_agent_service_events.py`         | Error path publishes `execution_status` before `error`                        |
| AC-11                | T-003   | Frontend unit test (useStreamingChat)                         | `activeExecutionId` effect skips WebSocket close when `recentlyCompletedRef` is true |
| AC-6                 | T-004   | Frontend unit test (ChatInterface)                            | Stale-streaming timeout clears all streaming state after 15s                  |

---

## Test Specification

### Test Hierarchy

```text
├── Backend Unit Tests
│   ├── T-001: Event ordering in success path
│   └── T-002: Event ordering in error path
├── Frontend Unit Tests
│   ├── T-003: recentlyCompletedRef guard behavior
│   └── T-004: Stale-streaming timeout behavior
└── Manual E2E Verification
    └── Full chat flow (send, complete, follow-up)
```

### Test Cases

| Test ID | Test Name                                                       | Criterion | Type   | Verification                                                                                       |
| ------- | --------------------------------------------------------------- | --------- | ------ | -------------------------------------------------------------------------------------------------- |
| T-001   | `test_run_agent_graph_publishes_execution_status_before_complete` | AC-4      | Unit   | Mock the event bus publish calls; verify `execution_status` call index < `complete` call index     |
| T-002   | `test_run_agent_graph_error_path_publishes_execution_status_before_error` | AC-5      | Unit   | Mock event bus in error path; verify `execution_status` call index < `error` call index            |
| T-003   | `test_activeExecutionId_effect_does_not_close_ws_after_recent_completion` | AC-11     | Unit   | Set `recentlyCompletedRef.current = true`, trigger effect with `activeExecutionId = null`, verify `wsRef.current.close()` NOT called |
| T-004   | `test_stale_streaming_timeout_clears_state_after_15s`           | AC-6      | Unit   | Set `isStreaming = true`, advance Jest timers by 15s, verify all streaming state cleared           |

### Test Infrastructure Needs

- **Backend T-001/T-002**: Mock `_publish` function or `AgentEventBus.publish`; need a test fixture that captures publish call order. The existing `_publish` is a local function inside `_run_agent_graph`, so the test should either mock the event bus or use a spy on `AgentEventBus.publish`.
- **Frontend T-003**: Mock `WebSocket`, render `useStreamingChat` hook with `activeExecutionId` transitions. Use `@testing-library/react-hooks` or `renderHook`.
- **Frontend T-004**: Use `vi.useFakeTimers()` in Vitest to advance time. Render `ChatInterface` component or test the effect in isolation.

---

## Detailed Task Specifications

### Task 1: Swap `execution_status` publish order in `agent_service.py`

**File**: `backend/app/ai/agent_service.py`

**Success path (lines ~1789-1810)** -- current order:
1. `_publish("agent_complete", ...)` (line 1780)
2. `_publish("complete", WSCompleteMessage(...))` (line 1791)
3. `_publish("execution_status", ...)` (line 1802) -- NEVER FORWARDED because loop breaks on "complete"

**Required new order:**
1. `_publish("agent_complete", ...)` (unchanged)
2. `_publish("execution_status", ...)` -- MOVE HERE (before complete)
3. `_publish("complete", WSCompleteMessage(...))` -- MOVE HERE (after execution_status)

**Error path (lines ~1970-1991)** -- current order:
1. `event_bus.publish(AgentEvent(event_type="error", ...))` (line 1971)
2. `event_bus.publish(AgentEvent(event_type="execution_status", ...))` (line 1980) -- NEVER FORWARDED because loop breaks on "error"

**Required new order:**
1. `event_bus.publish(AgentEvent(event_type="execution_status", ...))` -- MOVE HERE (before error)
2. `event_bus.publish(AgentEvent(event_type="error", ...))` -- MOVE HERE (after execution_status)

**Success Criteria**: AC-4, AC-5

---

### Task 2: Add `recentlyCompletedRef` guard to `activeExecutionId` effect

**File**: `frontend/src/features/ai/chat/api/useStreamingChat.ts`

**Changes**:

A. Add a new ref near the existing refs (around line ~50-80):
   ```typescript
   const recentlyCompletedRef = useRef(false);
   ```

B. In the `isCompleteMessage` handler (around line 571-581), after `callbacks.onComplete(...)`, set the ref:
   ```typescript
   recentlyCompletedRef.current = true;
   setTimeout(() => { recentlyCompletedRef.current = false; }, 5000);
   ```
   This gives the `activeExecutionId` effect a 5-second window to skip closing.

C. In the `isErrorMessage` handler (around line 584-589), after the error handling, also set:
   ```typescript
   recentlyCompletedRef.current = true;
   setTimeout(() => { recentlyCompletedRef.current = false; }, 5000);
   ```

D. In the `activeExecutionId` effect (lines 1111-1122), add a guard:
   ```typescript
   } else if (!activeExecutionId && wsRef.current) {
     // Don't close if we just completed streaming -- the connection
     // should stay alive for follow-up messages
     if (recentlyCompletedRef.current) {
       return;
     }
     wsRef.current.close();
     wsRef.current = null;
     setConnectionState(WSConnectionState.CLOSED);
   }
   ```

**Success Criteria**: AC-11 -- WebSocket stays open for 5 seconds after completion

---

### Task 3: Add stale-streaming timeout in `ChatInterface.tsx`

**File**: `frontend/src/features/ai/chat/components/ChatInterface.tsx`

**Changes**:

Add a new `useEffect` after the `isStreaming` computation (around line 242) that watches `isStreaming` and force-clears all streaming state if it stays `true` for more than 15 seconds:

```typescript
// Safety net: force-clear streaming state if stuck for 15+ seconds
useEffect(() => {
  if (!isStreaming) return;

  const timeoutId = setTimeout(() => {
    // Force-clear all streaming state
    setIsWaitingForResponse(false);
    setActiveToolCalls([]);
    setStreamingState({
      main: "",
      mainStreams: new Map<string, MainAgentStream>(),
      subagents: new Map<string, SubagentStream>(),
    });
  }, 15_000);

  return () => clearTimeout(timeoutId);
}, [isStreaming]);
```

Note: The effect re-runs when `isStreaming` changes. If it transitions to `false` before 15s, the cleanup clears the timeout. If it stays `true`, the timeout fires and resets everything.

**Success Criteria**: AC-6 -- Streaming state force-cleared after 15s idle

---

### Task 4: Backend tests for event ordering

**File**: `backend/tests/unit/ai/test_agent_service_events.py` (new file)

**T-001**: Verify that in the success path, `execution_status` event is published before `complete` event.
- Approach: Mock the `_publish` function or spy on `event_bus.publish` to record call order
- Assert: The `execution_status` call appears before the `complete` call in the recorded sequence

**T-002**: Verify that in the error path, `execution_status` event is published before `error` event.
- Approach: Same mocking strategy, trigger error condition
- Assert: The `execution_status` call appears before the `error` call

**Success Criteria**: AC-4, AC-5

---

### Task 5: Frontend tests

**T-003**: Test `recentlyCompletedRef` guard behavior.
- Render `useStreamingChat` with mock WebSocket
- Simulate `onComplete` callback invocation
- Transition `activeExecutionId` from a value to `null`
- Assert: `wsRef.current.close()` is NOT called within 5 seconds
- After 5 seconds, transition `activeExecutionId` to `null` again
- Assert: Close IS called (guard expired)

**T-004**: Test stale-streaming timeout.
- Render `ChatInterface` component (or test the effect in isolation)
- Set `isStreaming` to `true` by simulating streaming start
- Advance fake timers by 14 seconds
- Assert: Streaming state NOT cleared
- Advance fake timers by 2 more seconds (total 16s)
- Assert: All streaming state cleared (`isStreaming === false`)

**Success Criteria**: AC-6, AC-11

---

## Risk Assessment

| Risk Type   | Description                                                                                          | Probability | Impact | Mitigation                                                                                     |
| ----------- | ---------------------------------------------------------------------------------------------------- | ----------- | ------ | ---------------------------------------------------------------------------------------------- |
| Technical   | 15s timeout may be too short for very long agent responses with legitimate pauses (tool calls)       | Low         | Low    | Tool calls reset `isStreaming` via `handleToolCall`; the timeout only fires if NO state changes for 15s |
| Technical   | `recentlyCompletedRef` 5s window may not be enough if session refetch is slow                        | Low         | Medium | 5s is generous for a DB query; if needed, increase to 8s. The stale timeout at 15s is the ultimate fallback |
| Integration | Backend `execution_status` before `complete` may confuse existing frontend handlers                  | Low         | Low    | `isCompleteMessage` is the ONLY handler that checks `msg.type === "complete"`. `execution_status` is handled by a separate `isExecutionStatusMessage` guard earlier in the handler chain |
| Regression  | Moving `execution_status` before `complete` changes the bus event sequence                           | Low         | Low    | `execution_status` is NOT a terminal event (the loop does not break on it); it's already handled by the frontend |

---

## Documentation References

### Required Reading

- Analysis: `docs/03-project-plan/iterations/2026-05-01-fix-ai-chat-streaming-completion/00-analysis.md`
- WebSocket protocol: `backend/app/api/routes/ai_chat.py` lines 60-91 (forward_bus_events)
- Event publishing: `backend/app/ai/agent_service.py` lines 1779-1810 (success), 1970-1991 (error)

### Code References

- Backend event bus: `backend/app/ai/execution/agent_event_bus.py`
- Frontend WebSocket hook: `frontend/src/features/ai/chat/api/useStreamingChat.ts`
- Frontend streaming state: `frontend/src/features/ai/chat/components/ChatInterface.tsx`
- Frontend type guards: `frontend/src/features/ai/chat/types.ts`

---

## Prerequisites

### Technical

- [x] Backend dev server can start (`uv run uvicorn app.main:app --reload --port 8020`)
- [x] Frontend dev server can start (`npm run dev`)
- [x] PostgreSQL running (`docker-compose up -d postgres`)
- [x] No pending migrations required for this change

### Documentation

- [x] Analysis phase approved (Option 2)
- [x] Source files reviewed and line numbers confirmed

---

# Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Swap execution_status publish order before complete/error in agent_service.py"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: FE-001
    name: "Add recentlyCompletedRef guard to activeExecutionId effect in useStreamingChat.ts"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Add stale-streaming timeout useEffect in ChatInterface.tsx"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: BE-TEST-001
    name: "Backend unit tests for event ordering (success and error paths)"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: FE-TEST-001
    name: "Frontend unit tests for recentlyCompletedRef guard and stale-streaming timeout"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]
    kind: test

  - id: VERIFY-001
    name: "Integration verification: full E2E chat flow (send, complete, follow-up)"
    agent: pdca-backend-do-executor
    dependencies: [BE-TEST-001, FE-TEST-001]
```

### Execution Levels

- **Level 0 (parallel)**: BE-001, FE-001, FE-002 -- all three implementation tasks can run simultaneously
- **Level 1**: BE-TEST-001 (after BE-001), FE-TEST-001 (after FE-001 + FE-002)
- **Level 2**: VERIFY-001 (after all tests pass)

### Notes

- BE-001 and FE-001/FE-002 are independent and can be delegated to separate agents in parallel
- BE-TEST-001 and FE-TEST-001 should NOT run in parallel with each other (both are test suites, and the backend test may involve database operations)
- VERIFY-001 is a manual verification step that confirms the full flow works end-to-end
