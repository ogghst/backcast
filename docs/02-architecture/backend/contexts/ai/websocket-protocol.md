# WebSocket Protocol: Developer Guide

**Last Updated:** 2026-05-01
**Status:** Active
**Related:** [AI Context Overview](./README.md) | [Message Types Reference](./message-types.md)

## Overview

The AI chat uses a persistent WebSocket connection at `/api/v1/ai/chat/stream?token=<jwt>` for bidirectional streaming communication. This guide covers the connection lifecycle, reconnection strategy, and common development patterns.

## Connection Lifecycle

### 1. Connection Establishment

**Lazy Connection Pattern:**
The frontend does NOT connect on page load. Connection is deferred until:
- User sends a message (`sendMessage` triggers connection + pending message delivery)
- Component mounts with an active execution ID (resubscription to running execution)

**Authentication Flow:**
1. Client opens WebSocket with JWT token in query parameter
2. Server validates token BEFORE accepting connection
3. Server checks RBAC `ai-chat` permission
4. Server calls `websocket.accept()` only after both checks pass
5. If validation fails, server closes with specific codes:

| Close Code | Meaning | Client Action |
|-----------|---------|--------------|
| 1008 | Invalid token / no permission | Do NOT reconnect -- show login |
| 4008 | Token expired | Refresh token, then reconnect |
| 1000 | Normal closure | May reconnect with backoff |

**React Strict Mode Guard:**
In development, React Strict Mode mounts/unmounts/remounts components. The hook uses `isFirstMountRef` to prevent duplicate connections during this cycle.

### 2. Ping/Pong Keepalive

Server sends `ping` every 20 seconds during long agent execution. Client MUST respond with `pong`:
```json
// Server -> Client
{"type": "ping"}

// Client -> Server
{"type": "pong"}
```
Purpose: prevent reverse proxy (nginx 60s, cloud LBs 30-120s) from killing idle connections.

### 3. Reconnection Strategy

**Automatic reconnection with exponential backoff:**
- Max 5 attempts
- Base delay: 1000ms
- Delay formula: `1000 * 2^(attempt-1)` -> 1s, 2s, 4s, 8s, 16s
- Reconnect counter resets on successful open OR user-initiated message

**Page Visibility API:**
When browser tab becomes visible after being hidden:
1. Check if connection is dead (null or not OPEN)
2. Check if there's an active execution or pending message
3. If both: close stale connection, reset reconnect counter, reconnect immediately

**User-initiated reconnect:**
After max reconnect attempts, user can still send a message. This:
1. Resets `reconnectAttemptsRef` to 0
2. Triggers new connection
3. Delivers pending message on open

### 4. Event Replay and Resubscription

When reconnecting to an active execution:

```json
// Client -> Server (on reconnect)
{
  "type": "subscribe",
  "execution_id": "abc-123",
  "last_seen_sequence": 42
}
```

**Sequence tracking:**
- Every server event has a monotonically increasing `sequence` field
- Client tracks highest seen sequence in `lastSequenceRef`
- On reconnect, sends `last_seen_sequence` to skip already-seen events
- Backend calls `bus.replay(since_sequence=last_seen_sequence)` to replay only missed events

**sessionStorage persistence:**
- On component unmount, `lastSequenceRef` is saved to `sessionStorage` with key `ws-seq-{executionId}`
- On remount, restored from sessionStorage and cleaned up
- Prevents full replay when user navigates away and back

### 5. Connection Teardown

**Normal flow:**
- `complete` event -> connection stays OPEN for follow-up messages
- User navigates away -> cleanup effect closes WebSocket, persists sequence to sessionStorage
- Component unmount -> closes connection, clears all timeouts

**recentlyCompletedRef guard:**
After `complete` or `error`, a 5-second guard prevents the `activeExecutionId` effect from immediately closing the connection. This ensures follow-up messages can be sent on the same connection.

## Message Flow Examples

### New Chat Message

```
Client                                    Server
  |                                          |
  |--- chat {message, execution_mode} ------>|
  |                                          |-- validate & create session
  |<-- execution_started {execution_id} -----|
  |<-- thinking -----------------------------|
  |<-- token {content: "Hello"} -------------|
  |<-- token_batch {tokens: " world"} -------|
  |<-- tool_call {tool: "list_projects"} ----|
  |<-- tool_result {tool, result} ----------|
  |<-- token {content: "Found 3 projects"} --|
  |<-- complete {session_id, message_id} ----|
```

### Reconnection Mid-Execution

```
Client                                    Server
  |                                          |
  |--- subscribe {execution_id, seq: 42} --->|
  |                                          |-- replay missed events
  |<-- [replayed events since seq 42] -------|
  |<-- [live events continue] ---------------|
```

### Approval Workflow

```
Client                                    Server
  |                                          |
  |<-- approval_request {tool, args} --------|
  |                                          |-- 30s countdown begins
  |<-- polling_heartbeat {remaining: 25} ----|
  |<-- polling_heartbeat {remaining: 20} ----|
  |--- approval_response {approved: true} -->|
  |                                          |-- tool executes
  |<-- tool_result --------------------------|
```

## Backend Architecture: AgentEventBus

The event bus decouples agent execution from WebSocket delivery:

```
AgentService.start_execution()
    |
    v
background task publishes events -> AgentEventBus
                                       |
                                       +-- subscriber queue 1 -> WebSocket handler
                                       |
                                       +-- bounded log (1000 events) -> replay for late subscribers
```

Key properties:
- **Bounded circular buffer**: `collections.deque(maxlen=1000)` -- prevents unbounded memory growth
- **Per-subscriber queues**: slow consumers don't block others
- **Sequence numbers**: monotonically increasing, assigned by bus on publish
- **Completion tracking**: `is_completed` flag set after `complete`/`error` events

Source: `backend/app/ai/execution/agent_event_bus.py`

## Development Patterns

### Adding a New Message Type

1. **Backend schema**: Add Pydantic model in `backend/app/models/schemas/ai.py`:
   ```python
   class WSMyNewMessage(BaseModel):
       type: Literal["my_new_type"] = "my_new_type"
       # fields...
   ```

2. **Frontend type**: Add interface in `frontend/src/features/ai/chat/types.ts`:
   ```typescript
   export interface WSMyNewMessage {
     type: "my_new_type";
     // fields...
   }
   ```

3. **Add to union type**: Add `WSMyNewMessage` to `WSServerMessage` union
4. **Add type guard**: Add `isMyNewMessage()` function
5. **Backend publish**: Call `bus.publish(AgentEvent(event_type="my_new_type", data=...))` in agent execution
6. **Frontend handler**: Add routing case in `handleMessage` callback in `useStreamingChat.ts`

### Testing WebSocket Features

**Backend unit tests**: `backend/tests/api/routes/ai_chat/test_websocket_integration.py`
- Mock WebSocket with `AsyncMock(spec=WebSocket)`
- Patch `app.db.session.async_session_maker` and `app.api.routes.ai_chat.get_rbac_service`
- Use `ChatStreamPatcher` context manager for consistent service mocking

**Frontend unit tests**: `frontend/src/features/ai/chat/api/__tests__/useStreamingChat.test.tsx`
- Mock `WebSocket` class, `useAuthStore`, `useTimeMachineStore`
- Use `connectViaSendMessage` helper for lazy connection pattern
- Mock `sessionStorage` for sequence persistence tests
- Use `vi.useFakeTimers()` for timeout-related tests

## Common Pitfalls

1. **Forgetting execution_mode**: `sendMessage` requires `executionMode` as 3rd arg. Without it, the hook errors immediately.

2. **React Strict Mode double-mount**: The hook guards against this with `isFirstMountRef`. When testing, account for the fact that the first mount is "consumed" -- a second render won't create a second connection.

3. **Sequence persistence across navigation**: Without sessionStorage persistence, remounting the chat component sends `last_seen_sequence=0`, causing full event replay and duplicate content.

4. **recentlyCompletedRef race**: After completion, the `activeExecutionId` effect might try to close the connection before follow-up messages can be sent. The 5-second guard prevents this.

5. **WebSocket close code 1008 vs 4008**: 1008 means permanent auth failure (don't reconnect). 4008 means token expired (refresh and reconnect). The frontend handles these differently.

## Source Files

| Component | Backend | Frontend |
|-----------|---------|----------|
| WS Endpoint | `app/api/routes/ai_chat.py` | -- |
| WS Hook | -- | `features/ai/chat/api/useStreamingChat.ts` |
| Message Types | `app/models/schemas/ai.py` | `features/ai/chat/types.ts` |
| Event Bus | `app/ai/execution/agent_event_bus.py` | -- |
| Agent Service | `app/ai/agent_service.py` | -- |
| Agent Config | `app/ai/config_service.py` | -- |
| Upload | `app/api/routes/ai_upload.py` | `features/ai/chat/api/attachmentUpload.ts` |
| Tests | `tests/api/routes/ai_chat/test_websocket_integration.py` | `features/ai/chat/api/__tests__/useStreamingChat.test.tsx` |
