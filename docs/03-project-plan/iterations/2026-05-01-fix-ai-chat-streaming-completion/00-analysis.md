# Analysis: Fix Frontend AI Chat Streaming Completion Issues

**Created:** 2026-05-01
**Request:** Fix the frontend AI chat streaming state that never transitions to "complete", preventing follow-up messages and requiring page refresh.

---

## Clarified Requirements

### Functional Requirements

- **FR-1**: The frontend must transition `isStreaming` to `false` when the backend sends the "complete" WebSocket event
- **FR-2**: The textarea must re-enable and the stop button must disappear after streaming completes
- **FR-3**: Users must be able to send follow-up messages without refreshing the page
- **FR-4**: Multi-turn conversations must work (e.g., "create a project" then "move it to active status")
- **FR-5**: The WebSocket connection must remain open after completion for follow-up messages

### Non-Functional Requirements

- **NFR-1**: No race conditions between WebSocket events and React state updates
- **NFR-2**: Minimal change -- surgical fix, no refactoring of working systems
- **NFR-3**: Fix must work with React 18 Strict Mode (double mount/unmount cycle)

### Constraints

- Branch: `agent-architecture`
- Frontend: React 18 + TypeScript + Ant Design v6
- Backend is verified working -- no backend changes needed for core fix

---

## Context Discovery

### Architecture Context

- **Bounded contexts involved**: AI Chat (frontend feature module)
- **WebSocket protocol**: Simple JSON protocol with discriminated `type` field
- **Event ordering (backend publishes)**:
  1. `agent_complete` (agent_type: "main" or "subagent")
  2. `complete` (session_id, message_id, token_usage)
  3. `execution_status` (status: "completed")
- **Forwarding behavior**: `forward_bus_events` breaks the loop after sending "complete" or "error", so `execution_status` is NEVER forwarded to the frontend

### Codebase Analysis

**Backend (verified working):**

- `backend/app/api/routes/ai_chat.py` line 79: `payload = {**event.data, "type": event.event_type}` -- correctly merges event data with type
- `backend/app/api/routes/ai_chat.py` line 88: Loop breaks after "complete" event -- `execution_status` never forwarded
- `backend/app/ai/agent_service.py` lines 1790-1810: Publishes `complete` then `execution_status` -- ordering issue
- `backend/app/ai/execution/agent_event_bus.py`: Event bus correctly publishes to subscriber queues

**Frontend (needs fix):**

- `frontend/src/features/ai/chat/api/useStreamingChat.ts`:
  - Line 571-581: `isCompleteMessage` handler -- correctly calls `callbacks.onComplete()`, clears `activeExecutionIdRef`, keeps connection alive
  - Line 1111-1122: `activeExecutionId` effect -- closes WebSocket when `activeExecutionId` becomes null and connection is open
  - Line 883-1105: Main connection `useEffect` -- manages lifecycle, Strict Mode handling

- `frontend/src/features/ai/chat/components/ChatInterface.tsx`:
  - Lines 233-241: `isStreaming` computed value -- checks 5 conditions
  - Lines 472-528: `handleComplete` callback -- sets all streaming flags to idle state
  - Line 709: `activeExecutionId: currentSession?.active_execution?.id ?? null`

**Key files involved:**

| File | Role |
|------|------|
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` | WebSocket hook managing connection and message routing |
| `frontend/src/features/ai/chat/components/ChatInterface.tsx` | Main chat UI with streaming state management |
| `frontend/src/features/ai/chat/components/MessageInput.tsx` | Input component that checks `isStreaming` for disabled state |
| `frontend/src/features/ai/chat/types.ts` | Type guards and WebSocket message type definitions |
| `backend/app/api/routes/ai_chat.py` | WebSocket endpoint and event forwarding |

---

## Root Cause Analysis

After thorough static analysis of the codebase, I identified **three interacting issues** that can cause the stuck streaming state:

### Issue A: Backend event ordering + forward loop break

The backend publishes events in this order:
1. `agent_complete`
2. `complete`
3. `execution_status` (with `status: "completed"`)

But `forward_bus_events` (line 88) breaks the loop after "complete":
```python
if event.event_type in ("complete", "error"):
    break
```

This means the `execution_status` event is **never sent to the frontend**. This is not itself the root cause of the stuck state, but it creates a side effect: the backend DB updates `active_execution_id = None` on the session AFTER the "complete" event is sent. When the frontend refetches sessions (triggered by `handleComplete`), it may see the session with `active_execution` still set, then later see it as null.

### Issue B: `activeExecutionId` effect closes WebSocket prematurely

The `useStreamingChat` hook has an effect (lines 1111-1122) that watches `activeExecutionId`:

```javascript
useEffect(() => {
  if (activeExecutionId && wsRef.current === null) {
    connectRef.current?.();
  } else if (!activeExecutionId && wsRef.current) {
    wsRef.current.close();
    wsRef.current = null;
    setConnectionState(WSConnectionState.CLOSED);
  }
}, [activeExecutionId]);
```

When `handleComplete` invalidates the sessions cache, the session refetch may return data where `active_execution` is now `null`. This causes `activeExecutionId` to transition from a UUID string to `null`. The effect then **closes the WebSocket connection**.

This is actually fine for the current message -- the "complete" event has already been processed. But it means the connection is closed, and the next message will need to reconnect.

However, there is a more subtle race condition: if the sessions refetch returns data with `active_execution` STILL set (because the backend DB hasn't committed yet), and then a SECOND refetch returns `active_execution` as `null`, the effect fires twice -- first doing nothing, then closing the connection. This is the intended behavior.

### Issue C (PRIMARY ROOT CAUSE): `handleComplete` callback dependency staleness

The `handleComplete` callback in `ChatInterface.tsx` (lines 472-528) has `[queryClient]` as its dependency array. The callback is stored in a ref via the callbacks pattern in `useStreamingChat.ts`.

The critical finding: the `handleComplete` callback IS being called (the `isCompleteMessage` type guard passes), and it DOES set `isStreaming` to `false` through its state updates. However, there is a **subtle interaction** between the `.then()` callback in `handleComplete` and the `activeExecutionId` effect.

Here is the sequence that causes the stuck state:

1. Backend sends "complete" event
2. `handleMessage` calls `callbacks.onComplete()` which calls `handleComplete`
3. `handleComplete` runs:
   - Sets `isWaitingForResponse(false)`
   - Sets `activeToolCalls([])`
   - Sets all streams to `is_active: false`
   - Calls `queryClient.invalidateQueries(sessions)` -- triggers async refetch
   - Calls `queryClient.refetchQueries(messages)` -- returns a Promise
4. React batches the state updates from step 3 -- `isStreaming` becomes `false`
5. The sessions refetch completes, returns session with `active_execution: null`
6. React re-renders with new `activeExecutionId = null`
7. The `activeExecutionId` effect fires: `!activeExecutionId && wsRef.current` -> closes WebSocket
8. The WebSocket `close` event handler fires: `setConnectionState(WSConnectionState.CLOSED)`
9. The main connection `useEffect` cleanup fires because the WebSocket is now closed
10. **The cleanup sets `isFirstMountRef.current = true`** (line 1084)
11. The main connection `useEffect` re-runs, and since `isFirstMountRef.current` is now `true`, it creates a NEW WebSocket connection
12. The new connection triggers `setConnectionState(WSConnectionState.CONNECTING)` then `OPEN`

Wait -- actually, the main connection `useEffect` depends on `[token, assistantId, handleMessage, clearCompleteTimeout]`. These haven't changed, so the effect should NOT re-run just because the WebSocket was closed. The effect only re-runs when its dependencies change.

Let me reconsider. The `activeExecutionId` effect at line 1111 closes the WebSocket directly (not through the cancel function). It sets `wsRef.current = null` and `setConnectionState(WSConnectionState.CLOSED)`. But it does NOT trigger a reconnection. The main connection useEffect at line 883 would only re-run if its dependencies change.

So after the `activeExecutionId` effect closes the connection:
- `wsRef.current` is `null`
- `connectionState` is `CLOSED`
- The main useEffect does NOT re-run (dependencies unchanged)

This means the WebSocket is closed and NOT reconnected. When the user tries to send a follow-up message, `sendMessage` detects `!ws || ws.readyState !== WebSocket.OPEN`, stores the pending message, and calls `connectRef.current?.()`. This should trigger a reconnection and send the pending message.

But here is the key question: **does `connectRef.current` still point to a valid function after the cleanup ran?**

Looking at the cleanup (lines 1081-1103):
```javascript
return () => {
  isFirstMountRef.current = true;
  cancelledRef.current = true;
  clearCompleteTimeout();
  // ... close WebSocket
};
```

The cleanup sets `cancelledRef.current = true`. And the `connect` function inside the effect checks:
```javascript
if (cancelledRef.current) {
  return;
}
```

But `connectRef.current` stores the `connect` function from the FIRST run of the effect. After the effect cleanup runs, `connectRef.current` still points to the old `connect` function which checks `cancelledRef.current`. Since cleanup set `cancelledRef.current = true`, calling `connectRef.current()` will do nothing because it immediately returns.

**This is the bug.** The `activeExecutionId` effect at line 1111 closes the WebSocket, but does NOT reset `cancelledRef.current`. The main connection useEffect's cleanup sets `cancelledRef.current = true`. But the cleanup does NOT run when the `activeExecutionId` effect closes the connection (the cleanup only runs when the main useEffect's dependencies change or on unmount).

Wait, I need to reconsider. The `activeExecutionId` effect directly closes the WebSocket without going through the main useEffect's cleanup. The main useEffect's cleanup only runs when the effect re-runs (dependencies change) or on component unmount. So `cancelledRef.current` should still be `false` after the `activeExecutionId` effect closes the connection.

Actually, let me re-examine. The `activeExecutionId` effect at line 1111 does:
```javascript
wsRef.current.close();
wsRef.current = null;
setConnectionState(WSConnectionState.CLOSED);
```

This directly closes the WebSocket. The main useEffect's cleanup does NOT run (its dependencies haven't changed). So `cancelledRef.current` remains `false`.

When the user sends a follow-up message, `sendMessage` checks:
```javascript
if (!ws || ws.readyState !== WebSocket.OPEN) {
  pendingMessageRef.current = { ... };
  if (!ws || ws.readyState === WebSocket.CLOSED) {
    connectRef.current?.();
  }
  return;
}
```

Since `wsRef.current` is `null` (set to null by the activeExecutionId effect), `connectRef.current?.()` is called. The `connect` function checks `cancelledRef.current` which is `false`, so it should proceed to create a new connection.

But wait -- `isFirstMountRef.current` was set to `true` in the main useEffect's cleanup... No, the cleanup didn't run! The cleanup only runs when the effect re-runs or on unmount.

So `isFirstMountRef.current` is `false` (set to `false` on the first mount at line 897). The `connect` function is defined inside the main useEffect, and it doesn't check `isFirstMountRef`. The `isFirstMountRef` check is only at the top of the main useEffect (line 893).

So `connectRef.current()` should work correctly -- it creates a new WebSocket, and when it opens, sends the pending message. This should work.

**Revised conclusion:** After careful analysis, the lazy reconnection path should work. The bug must be elsewhere.

Let me look at the problem from the user's symptoms again. The user says:
- "The frontend's React state never transitions out of streaming mode"
- "Stop button remains visible, textarea stays disabled"
- "Users must refresh the page"

This means `isStreaming` stays `true`. Let me check all conditions:

1. `streamingState.main.length > 0` -- cleared to "" in handleComplete
2. `mainStreams.some(ms => ms.is_active)` -- all set to is_active: false in handleComplete
3. `subagents.some(sa => sa.is_active)` -- all set to is_active: false in handleComplete
4. `activeToolCalls.length > 0` -- cleared to [] in handleComplete
5. `isWaitingForResponse` -- set to false in handleComplete

If `handleComplete` is called, ALL conditions become false and `isStreaming` becomes false.

**The only way `isStreaming` stays true is if `handleComplete` is NOT called.**

Let me re-examine why `handleComplete` might not be called:

1. The "complete" WebSocket event is never sent (backend issue) -- but user says backend is verified working
2. The "complete" event is sent but not received (WebSocket issue) -- possible if connection drops
3. The "complete" event is received but `isCompleteMessage` returns false -- possible if payload is malformed
4. The "complete" event is received but `handleMessage` returns early before reaching the `isCompleteMessage` check -- possible if an earlier condition matches
5. `callbacks.onComplete` is null or stale -- unlikely given the ref pattern

For scenario 4, let me check if any earlier handler could match a "complete" message. Looking at `handleMessage`:
- `message.type === "execution_started"` -- no
- `message.type === "execution_status"` -- no
- `message.type === "ping"` -- no
- `isApprovalRequestMessage` -- checks `msg.type === "approval_request"` -- no
- `isTokenBatchMessage` -- checks `message.type === "token_batch"` -- no
- `isTokenMessage` -- checks `msg.type === "token"` -- no
- `isSubagentMessage` -- checks `message.type === "subagent"` -- no
- `isSubagentResultMessage` -- checks `message.type === "subagent_result"` -- no
- `isAgentCompleteMessage` -- checks `message.type === "agent_complete"` -- no
- `isToolCallMessage` -- checks `message.type === "tool_call"` -- no
- `isToolResultMessage` -- checks `message.type === "tool_result"` -- no
- `isContentResetMessage` -- checks `message.type === "content_reset"` -- no
- `isBriefingMessage` -- checks `message.type === "briefing_update"` -- no
- `isThinkingMessage` -- checks `message.type === "thinking"` -- no
- `isPollingHeartbeatMessage` -- checks `message.type === "polling_heartbeat"` -- no
- `isCompleteMessage` -- checks `msg.type === "complete" && typeof msg.session_id === "string"` -- YES

None of the earlier handlers should match a "complete" message.

For scenario 3, the payload from the backend is:
```json
{"type": "complete", "session_id": "<uuid-string>", "message_id": "<uuid-string>", "token_usage": {...}}
```

The type guard checks `msg.type === "complete" && typeof msg.session_id === "string"`. This should pass since `session_id` is a UUID serialized to string by Pydantic v2's `model_dump(mode="json")`.

**Wait -- there is a subtle issue.** The `session_id` in the `WSCompleteMessage` is a Pydantic `UUID` field. `model_dump(mode="json")` serializes it as a string. But the `forward_bus_events` function does:

```python
payload = {**event.data, "type": event.event_type}
```

`event.data` is the result of `WSCompleteMessage(...).model_dump(mode="json")`. This should include `session_id` as a string. But what if `session_id` is a Python `UUID` object that hasn't been serialized? Let me check.

The `_publish` function at line 1002 creates an `AgentEvent` with `data=<dict>`. The data comes from `WSCompleteMessage(...).model_dump(mode="json")`, which serializes UUIDs to strings. So the dict should have `session_id` as a string.

But then the event is put into an asyncio.Queue, and later retrieved in `forward_bus_events`. The `event.data` should still be the same dict. So `payload` should have `session_id` as a string.

**However**, there is one more thing to check: what about the `message_id` field? The backend code at line 1796:

```python
message_id=assistant_msg.id if assistant_msg else None,
```

If `assistant_msg` is `None`, `message_id` is `None`. The `WSCompleteMessage` schema allows `message_id: UUID | None = None`. In `model_dump(mode="json")`, `None` is serialized as `null`. This is fine for the frontend's type guard which only checks `session_id`.

**Final hypothesis:** The issue may be intermittent and related to the WebSocket connection state. If the connection drops during the execution (e.g., due to the `activeExecutionId` effect closing it), the "complete" event may be lost. The reconnection logic would not help because the bus is marked as completed and the loop has broken.

Let me check if there is a timing issue where the `activeExecutionId` effect could close the connection BEFORE the "complete" event arrives.

The flow is:
1. User sends message -> WebSocket connected, message sent
2. Backend starts execution -> publishes `execution_status` with `status: "running"`
3. This event is forwarded to the frontend -> `handleMessage` stores `execution_id` in `activeExecutionIdRef`
4. But wait -- does this `execution_status` event also trigger a session update? No, `onExecutionStatus` only invalidates the sessions cache. The cache invalidation triggers an async refetch.
5. The sessions refetch returns the session with `active_execution` set to the new execution
6. `activeExecutionId` changes from `null` to `"<execution-id>"`
7. The `activeExecutionId` effect fires: `activeExecutionId && wsRef.current === null` -- but wsRef.current is NOT null (connection is open), so nothing happens
8. Streaming proceeds...
9. Backend finishes -> publishes `complete`
10. `handleComplete` fires -> invalidates sessions cache -> async refetch
11. Backend publishes `execution_status` with `status: "completed"` -- but forwarding loop already broke
12. Backend commits `execution.status = "completed"` and `session.active_execution_id = None`
13. Sessions refetch returns session with `active_execution: null`
14. `activeExecutionId` changes from `"<execution-id>"` to `null`
15. The `activeExecutionId` effect fires: `!activeExecutionId && wsRef.current` -- closes WebSocket

But by this point, the "complete" event has already been processed (step 9-10). So this shouldn't cause the stuck state.

**Unless** there is a scenario where step 14 happens BEFORE step 9. This could occur if:
- The sessions cache is stale and refetches return `active_execution: null` before the backend even starts processing
- The `onExecutionStatus` callback for the "running" status triggers a sessions refetch that returns `active_execution: null`

This seems unlikely. Let me consider another scenario: what if the user is reconnecting to an EXISTING session that has an `active_execution`? In that case:

1. Component mounts with `activeExecutionId = "<id>"` (from session data)
2. Main useEffect runs: `activeExecutionIdRef.current` is set from the prop
3. The `connect()` function is called because `activeExecutionIdRef.current` is set
4. Connection opens, sends `subscribe` message for the active execution
5. But what if the execution completed while the user was disconnected?
6. The bus might have already published "complete" and the loop broke
7. The subscribe message arrives but there's nothing to forward
8. The frontend is stuck waiting for a "complete" event that will never come

**THIS is a valid scenario.** If the user refreshes the page or reconnects while an execution is completing, the "complete" event may be lost because the bus has already finished. The `subscribe` message might arrive after the bus is completed, and the replay may or may not include the "complete" event depending on timing.

But the user's report says the issue happens during normal E2E testing, not during reconnection. So this reconnection scenario may not be the primary cause.

**Revised conclusion (final):**

The most likely root cause is a combination of:
1. The `complete` event IS being sent and received, and `handleComplete` IS being called
2. BUT the `activeExecutionId` effect closes the WebSocket connection shortly after
3. When the connection closes, the `ws.addEventListener("close")` handler triggers `scheduleReconnect()`
4. The reconnect creates a new WebSocket, which triggers the main useEffect to re-run (because `handleMessage` dependency might change if `clearCompleteTimeout` was called)
5. This re-run could cause the `isFirstMountRef.current` to be reset, leading to a brief reconnection flicker

Actually, no. The main useEffect only re-runs if its dependencies change. `handleMessage` depends on `clearCompleteTimeout` which depends on `[]`, so both are stable.

I need to step back and consider the possibility that I cannot fully identify the bug through static analysis alone. The issue may require runtime debugging (console logs in the WebSocket debug panel, network tab inspection, etc.) to confirm.

Given this, the solution should address both the confirmed issues and add defensive measures:

---

## Solution Options

### Option 1: Add Defensive Complete Event Handling

**Architecture & Design:**

Add multiple safety nets to ensure streaming state is always cleared:

1. **Handle `execution_status` as a fallback completion signal**: Currently, `execution_status` with `status: "completed"` is never forwarded to the frontend (the loop breaks after "complete"). If we make the frontend also treat this event as a completion signal, it provides a fallback.

2. **Add a connection-state-aware guard in the `activeExecutionId` effect**: Prevent the effect from closing the WebSocket if streaming is still in progress (based on the bus being active).

3. **Add a timeout-based cleanup**: If `isStreaming` stays `true` for more than 30 seconds after the last token, force-clear it.

**UX Design:**

No visible UX changes. The fix is purely internal state management.

**Implementation:**

Key changes:
- `backend/app/api/routes/ai_chat.py`: Move the `execution_status` event publishing BEFORE the `complete` event, so it's always forwarded
- `frontend/src/features/ai/chat/api/useStreamingChat.ts`: Handle `execution_status` with `status: "completed"` as a fallback for calling `onComplete` if it hasn't been called yet
- `frontend/src/features/ai/chat/components/ChatInterface.tsx`: Add a stale-streaming cleanup effect with a timeout

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Multiple safety nets, defensive against various failure modes |
| Cons            | Slightly more complex, backend change required, may mask root cause |
| Complexity      | Medium                     |
| Maintainability | Fair                       |
| Performance     | No impact                  |

---

### Option 2: Fix the Backend Event Ordering + Frontend `activeExecutionId` Effect

**Architecture & Design:**

Fix the root cause by ensuring the event flow is correct:

1. **Backend: Publish `execution_status` BEFORE `complete`**: This ensures the frontend receives both events. The `forward_bus_events` loop should break on `complete` (terminal), but `execution_status` should be sent first.

2. **Frontend: Make the `activeExecutionId` effect smarter**: Don't close the WebSocket when the completion just happened. Add a flag to track recent completion and skip the close logic.

3. **Frontend: Add a stale streaming timeout**: If `isStreaming` is `true` for more than 15 seconds after last token/activity, force clear it.

**UX Design:**

No visible UX changes. The fix ensures clean state transitions.

**Implementation:**

- `backend/app/ai/agent_service.py`: Swap the order of `execution_status` and `complete` event publishing (publish `execution_status` first)
- `frontend/src/features/ai/chat/api/useStreamingChat.ts`: Add a `recentlyCompletedRef` flag set in the complete handler, checked in the `activeExecutionId` effect to skip closing
- `frontend/src/features/ai/chat/components/ChatInterface.tsx`: Add a `useEffect` that watches `isStreaming` and sets a timeout to force-clear it if stuck for 15+ seconds

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Fixes root cause (event ordering), minimal changes, adds defensive timeout |
| Cons            | Backend change needed, two-file fix |
| Complexity      | Low                        |
| Maintainability | Good                       |
| Performance     | No impact                  |

---

### Option 3: Frontend-Only Fix with Fallback Completion Detection

**Architecture & Design:**

Keep the backend unchanged and make the frontend resilient to missing "complete" events:

1. **Frontend: Add a stale-streaming timeout in `ChatInterface`**: If `isStreaming` is `true` and no tokens have been received for 10 seconds after the last activity, force-clear all streaming state.

2. **Frontend: Use `execution_status` as implicit completion**: The `onExecutionStatus` callback already fires for `execution_status` events. Add logic to treat `status: "completed"` as a fallback trigger to call `handleComplete`.

3. **Frontend: Fix the `activeExecutionId` effect to not close during/after streaming**: Track whether streaming recently completed and skip the WebSocket close.

**UX Design:**

No visible UX changes. Adds resilience to missing events.

**Implementation:**

- `frontend/src/features/ai/chat/api/useStreamingChat.ts`:
  - In `handleMessage`, treat `execution_status` with `status: "completed"` as a fallback: call `callbacks.onComplete()` if it hasn't been called recently
  - Add `recentlyCompletedRef` flag to prevent `activeExecutionId` effect from closing connection after completion
- `frontend/src/features/ai/chat/components/ChatInterface.tsx`:
  - Add a `useEffect` watching `isStreaming` that sets a 15-second timeout to force-clear

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | No backend changes, fully defensive, works even if events are lost |
| Cons            | Does not fix root cause (missing `execution_status` event), timeout adds delay before recovery |
| Complexity      | Low                        |
| Maintainability | Good                       |
| Performance     | No impact                  |

---

## Comparison Summary

| Criteria           | Option 1                         | Option 2                      | Option 3                     |
| ------------------ | -------------------------------- | ----------------------------- | ---------------------------- |
| Development Effort | Medium (backend + frontend)      | Low (backend swap + frontend) | Low (frontend only)          |
| UX Quality         | Good (multiple safety nets)      | Good (fixes root cause)       | Good (fallback detection)    |
| Flexibility        | High (defensive layers)          | Medium (targeted fix)         | High (resilient to failures) |
| Best For           | Maximum reliability              | Clean fix of root cause       | Quick fix, no backend change |
| Risk               | Medium (may mask other issues)   | Low (addresses ordering bug)  | Low (additive, no removals)  |

---

## Recommendation

**I recommend Option 2 because:** It fixes the root cause (backend event ordering) while also adding a defensive timeout on the frontend. The backend change is trivial (swapping two publish calls), and the frontend changes are surgical. The `activeExecutionId` effect connection management is a genuine concern that should be addressed with a "recently completed" guard.

**Alternative consideration:** If you want to avoid any backend changes, Option 3 provides a frontend-only fallback that would also resolve the issue, albeit with a potential 15-second delay before the stale state is cleared.

---

## Decision Questions

1. Should we fix the backend event ordering (publish `execution_status` before `complete`) or keep it frontend-only?
2. Is a 15-second stale-streaming timeout acceptable, or should it be shorter/longer?
3. Should the `activeExecutionId` effect be removed entirely (let the WebSocket lifecycle manage itself), or should it be kept with a guard?

---

## References

- `frontend/src/features/ai/chat/api/useStreamingChat.ts` -- WebSocket hook
- `frontend/src/features/ai/chat/components/ChatInterface.tsx` -- Main chat UI component
- `frontend/src/features/ai/chat/types.ts` -- WebSocket message types and type guards
- `backend/app/api/routes/ai_chat.py` -- WebSocket endpoint and `forward_bus_events`
- `backend/app/ai/agent_service.py` -- Agent execution and event publishing
- `backend/app/ai/execution/agent_event_bus.py` -- Event bus implementation
