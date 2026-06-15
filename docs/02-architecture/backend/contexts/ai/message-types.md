# WebSocket Protocol & Messages

> **Canonical source.** This is the single reference for both the AI chat **WebSocket protocol / connection lifecycle** and the full **message catalog**. It consolidates the former `websocket-protocol.md` and `api/ai-tools.md` (both deleted).

**Last Updated:** 2026-06-14
**Status:** Active

The AI chat uses a persistent WebSocket connection at `/api/v1/ai/chat/stream?token=<jwt>` for bidirectional streaming. This document covers connection lifecycle, reconnection strategy, execution-mode × risk-level gating, and the complete message catalog.

All types are defined in:

- Frontend: [frontend/src/features/ai/chat/types.ts](../../../../../frontend/src/features/ai/chat/types.ts)
- Backend WS schemas: [backend/app/models/schemas/ai.py](../../../../../backend/app/models/schemas/ai.py) (lines 626-1087)

The protocol uses simple JSON messages with a `type` discriminator field.

---

## Table of Contents

1. [Connection Lifecycle](#connection-lifecycle)
2. [Execution Modes & Risk Gating](#execution-modes--risk-gating)
3. [Client to Server Messages](#client-to-server-messages)
4. [Server to Client Messages -- Streaming](#server-to-client-messages----streaming)
5. [Server to Client Messages -- Tool Execution](#server-to-client-messages----tool-execution)
6. [Server to Client Messages -- Agent Orchestration](#server-to-client-messages----agent-orchestration)
7. [Server to Client Messages -- Approval & Ask-User Workflows](#server-to-client-messages----approval--ask-user-workflows)
8. [Server to Client Messages -- Lifecycle](#server-to-client-messages----lifecycle)
9. [Message Unions](#message-unions)
10. [Message Flow Diagrams](#message-flow-diagrams)
11. [Development Patterns](#development-patterns)
12. [Common Pitfalls](#common-pitfalls)
13. [Source Files](#source-files)

---

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

**Automatic reconnection with exponential backoff** (`useStreamingChat.ts` ~142-147, 1122-1131):

- `MAX_RECONNECT_ATTEMPTS = 5`
- `BASE_RECONNECT_DELAY = 1000` ms
- Delay formula: `BASE_RECONNECT_DELAY * Math.pow(2, attempt - 1)` → 1s, 2s, 4s, 8s, 16s

The reconnect counter resets on three triggers:

1. **On open** — when the WebSocket successfully opens (~1180)
2. **On user message** — a user-initiated send resets the counter (~935)
3. **On accept** — after the subscribe/handshake is accepted (~924)

**Page Visibility API:**
When the browser tab becomes visible after being hidden, the `visibilitychange` handler (~1337) decides whether to reconnect:

1. Check if connection is dead (null or not `OPEN`)
2. Check if there's an active execution or pending message
3. If both: close stale connection, reset reconnect counter, reconnect immediately

**User-initiated reconnect:**
After max reconnect attempts, the user can still send a message. This:

1. Resets `reconnectAttemptsRef` to 0
2. Triggers a new connection
3. Delivers the pending message on open

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
- Client tracks the highest seen sequence in `lastSequenceRef`
- On reconnect, sends `last_seen_sequence` to skip already-seen events
- Backend replays only events with `sequence > last_seen_sequence`

**sessionStorage persistence** (~268, 280-285, 481-490):

- The last sequence is persisted to `sessionStorage` under key `ws-seq-{executionId}`
- Persistence is **throttled** (≥2s between writes, ~481-490) to avoid write churn
- On a tab-hidden flush / unmount, the current sequence is written so a remount resumes from the right point (~1314, 1351)
- On remount, the stored sequence is restored and the key cleaned up (~280-285)
- Prevents full replay when the user navigates away and back

### 5. Connection Teardown

**Normal flow:**

- `complete` event → connection stays OPEN for follow-up messages
- User navigates away → cleanup effect closes the WebSocket, persists the sequence to sessionStorage
- Component unmount → closes the connection, clears all timeouts

**`recentlyCompletedRef` race-condition guard** (~311, 722-729):

After `complete` or `error`, a 5-second guard (`recentlyCompletedRef = true`, cleared after 5000 ms) prevents the `activeExecutionId` effect (~1389) from immediately closing the connection. This ensures follow-up messages can be sent on the same connection before the effect tears it down.

---

## Execution Modes & Risk Gating

The AI tools system gates tool execution by risk level. `RiskLevel` has exactly three members — **`LOW`, `HIGH`, `CRITICAL`** (there is NO `MEDIUM`; `backend/app/ai/tools/types.py:79-95`). The ordering supports comparison (`LOW < HIGH < CRITICAL`).

### Execution Mode × Risk Level Matrix

| Mode | `LOW` | `HIGH` | `CRITICAL` | Source |
|------|-------|--------|------------|--------|
| `safe` | Allowed | Filtered out | Filtered out | `tools/__init__.py` ~60-66 |
| `standard` (default) | Allowed | **Allowed with approval** | Filtered out (blocked) | `tools/__init__.py` ~67-73; `middleware/backcast_security.py:593` |
| `expert` | Allowed | Allowed | Allowed | `tools/__init__.py` ~74-76 |

**Two-layer gating:**

1. **Tool-set filtering** (`filter_tools_by_execution_mode`, `tools/__init__.py:30-81`) removes disallowed tools BEFORE the LLM ever sees them. In `standard` mode, `CRITICAL` tools never reach the model.
2. **Runtime guard** (`BackcastSecurityMiddleware._check_risk_level_with_approval`, `middleware/backcast_security.py:536-595`) re-checks at call time and triggers the **approval flow** for `risk_level >= HIGH` in `STANDARD` mode.

**Default risk level:** tools without an explicit `risk_level` annotation default to `RiskLevel.HIGH` for safety (`tools/types.py:346`, `tools/__init__.py:54-55`, `middleware/backcast_security.py:361,586`).

### Mode Selection

Execution mode is selected by the client via the `execution_mode` field in the `chat` message. Default: `standard`. The frontend persists the selection in `localStorage` under `ai_execution_mode`.

### Tool Discovery

Tools are discoverable via **`GET /api/v1/ai/config/tools`** (router prefix `/ai/config` + `/tools`; `api/routes/ai_config.py:32,375-381`). Each tool's metadata includes its `risk_level`.

---

## Client to Server Messages

### `chat` -- Send a message to the AI

Initiates a new conversation or continues an existing one. The server creates an `AIAgentExecution` and streams events back.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | Yes | User message content (1-10000 chars) |
| `session_id` | `UUID \| null` | No | Existing session ID, or null for new session |
| `assistant_config_id` | `UUID` | Yes | Assistant config to use |
| `title` | `string` | No | Optional session title for new sessions |
| `execution_mode` | `"safe" \| "standard" \| "expert"` | Yes | Tool risk mode (default: `"standard"`) |
| `as_of` | `ISO datetime \| null` | No | Historical date for temporal queries |
| `branch_name` | `string` | No | Branch name (default: `"main"`) |
| `branch_mode` | `"merged" \| "isolated"` | No | Branch view mode (default: `"merged"`) |
| `project_id` | `UUID` | No | Project scope for project-specific chat |
| `context` | `SessionContext` | No | Session context (type, id, project_id, name) |
| `attachments` | `FileAttachment[]` | No | Document/file attachments |
| `images` | `string[]` | No | Image URLs |

```json
{
  "type": "chat",
  "message": "What is the current EVM status of the electrical installation WBE?",
  "session_id": null,
  "assistant_config_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "execution_mode": "standard",
  "project_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "context": {
    "type": "wbe",
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "project_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Electrical Installation"
  },
  "attachments": [],
  "images": []
}
```

### `subscribe` -- Resubscribe to active execution

Sent on WebSocket reconnection to resume receiving events for an execution already in progress.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `execution_id` | `UUID` | Yes | ID of the execution to subscribe to |
| `last_seen_sequence` | `int` | No | Last sequence number processed (default: 0) |

```json
{
  "type": "subscribe",
  "execution_id": "987e6543-e21b-45d3-b789-123456789abc",
  "last_seen_sequence": 42
}
```

### `approval_response` -- Approve or reject a tool

User's decision on a pending `approval_request`. The `approval_id` must match an active request.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approval_id` | `string` | Yes | UUID matching the approval request |
| `approved` | `boolean` | Yes | True to approve, False to reject |
| `user_id` | `UUID` | Yes | ID of the user making the decision |
| `timestamp` | `ISO datetime` | No | Time of decision (server defaults to now) |

```json
{
  "type": "approval_response",
  "approval_id": "abc12345-6789-def0-1234-567890abcdef",
  "approved": true,
  "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "timestamp": "2026-06-14T14:30:00Z"
}
```

### `ask_user_response` -- Answer to an ask_user prompt

The user's answer to an `ask_user` question (`schemas/ai.py:1024-1036`).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ask_id` | `string` | Yes | ID matching the `ask_user` prompt |
| `answer` | `string` | Yes | The user's response text |

```json
{
  "type": "ask_user_response",
  "ask_id": "q1w2e3r4-t5y6-7890-abcd-ef1234567890",
  "answer": "Yes, use the standard cost overrun threshold of 5%."
}
```

### `pong` -- Keepalive response

Sent by the client in response to a server `ping`. No fields required.

```json
{
  "type": "pong"
}
```

---

## Server to Client Messages -- Streaming

### `execution_started` -- Execution created

Sent immediately after an agent execution is created, before streaming begins.

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | `string` | ID of the new execution |

```json
{
  "type": "execution_started",
  "execution_id": "987e6543-e21b-45d3-b789-123456789abc"
}
```

### `execution_status` -- Execution status changed

Sent when an execution transitions between statuses (`running`, `completed`, `error`, `awaiting_approval`).

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | `UUID` | ID of the execution |
| `status` | `string` | Current status |
| `error_message` | `string \| null` | Error details if status is `"error"` |

```json
{
  "type": "execution_status",
  "execution_id": "987e6543-e21b-45d3-b789-123456789abc",
  "status": "completed",
  "error_message": null
}
```

### `thinking` -- Agent processing

Sent when the agent begins processing, before any tokens or tool calls. Useful for showing a loading indicator.

No additional fields beyond `type`.

```json
{
  "type": "thinking"
}
```

### `token` -- Single streaming token

Individual LLM token as it is generated. In practice, tokens are usually batched via `token_batch` for performance.

| Field | Type | Description |
|-------|------|-------------|
| `content` | `string` | Partial text token |
| `session_id` | `UUID` | Session identifier |
| `source` | `"main" \| "subagent"` | Token source (default: `"main"`) |
| `subagent_name` | `string \| null` | Subagent name when `source` is `"subagent"` |
| `invocation_id` | `string \| null` | Unique invocation ID for the agent segment |

```json
{
  "type": "token",
  "content": "The CPI",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "source": "main",
  "subagent_name": null,
  "invocation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### `token_batch` -- Batched tokens

Multiple tokens concatenated into a single message. Reduces WebSocket overhead while maintaining streaming UX. Tokens are flushed periodically (configurable via `AI_TOKEN_BUFFER_INTERVAL_MS`) and at key transition points (tool calls, subagent boundaries).

| Field | Type | Description |
|-------|------|-------------|
| `tokens` | `string` | Concatenated token string |
| `session_id` | `UUID` | Session identifier |
| `source` | `"main" \| "subagent"` | Token source |
| `subagent_name` | `string \| null` | Subagent name when `source` is `"subagent"` |
| `invocation_id` | `string \| null` | Unique invocation ID for the agent segment |

```json
{
  "type": "token_batch",
  "tokens": "The CPI for this WBE is 0.95, indicating a slight cost overrun.",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "source": "main",
  "subagent_name": null,
  "invocation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### `content_reset` -- Clear content buffer

Sent when the frontend should reset its streaming content buffer, typically after a subagent completes and the main agent begins its synthesis phase.

| Field | Type | Description |
|-------|------|-------------|
| `reason` | `string` | Why the reset occurred (default: `"subagent_completed"`) |

```json
{
  "type": "content_reset",
  "reason": "subagent_completed"
}
```

---

## Server to Client Messages -- Tool Execution

### `tool_call` -- Tool invoked

Sent when the AI agent calls a tool. Provides the tool name and arguments for display in the message flow.

| Field | Type | Description |
|-------|------|-------------|
| `tool` | `string` | Tool function name |
| `args` | `object` | Tool arguments as key-value pairs |
| `step_number` | `int \| null` | Current step (1-indexed) |
| `total_steps` | `int \| null` | Estimated total steps |
| `invocation_id` | `string \| null` | Invocation ID for this tool call |

```json
{
  "type": "tool_call",
  "tool": "get_wbe_details",
  "args": {
    "wbe_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "step_number": 1,
  "total_steps": 3,
  "invocation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### `tool_result` -- Tool completed

Sent after a tool finishes execution with its result data.

| Field | Type | Description |
|-------|------|-------------|
| `tool` | `string` | Tool function name |
| `result` | `object` | Result data containing `tool`, `success`, `result`, `error` |
| `invocation_id` | `string \| null` | Invocation ID for this tool result |

```json
{
  "type": "tool_result",
  "tool": "get_wbe_details",
  "result": {
    "tool": "get_wbe_details",
    "success": true,
    "result": {
      "name": "Electrical Installation",
      "wbe_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "in_progress"
    },
    "error": null
  },
  "invocation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## Server to Client Messages -- Agent Orchestration

### `subagent` -- Delegated to subagent

Sent when the agent delegates work to a specialist subagent (e.g., EVM Analyst, Project Admin).

| Field | Type | Description |
|-------|------|-------------|
| `subagent` | `string` | Subagent name (e.g., `"evm_analyst"`) |
| `message` | `string \| null` | Description of what the subagent is doing |
| `invocation_id` | `string` | Unique ID for this subagent instance |
| `step_number` | `int \| null` | Current step |
| `total_steps` | `int \| null` | Estimated total steps |

```json
{
  "type": "subagent",
  "subagent": "evm_analyst",
  "message": "Calculating EVM metrics for the electrical installation WBE",
  "invocation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "step_number": 2,
  "total_steps": 3
}
```

### `subagent_result` -- Subagent completed

Sent when a subagent finishes with its final response text. The content is also persisted as an assistant message in the session.

| Field | Type | Description |
|-------|------|-------------|
| `subagent_name` | `string` | Name of the completed subagent |
| `content` | `string` | Subagent's final response text |
| `invocation_id` | `string` | Unique ID matching the `subagent` event |

```json
{
  "type": "subagent_result",
  "subagent_name": "evm_analyst",
  "content": "The EVM analysis shows CPI=0.95 and SPI=1.02. The cost variance is -$15,000...",
  "invocation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

### `agent_complete` -- Agent stream ended

Sent when an agent (main or subagent) finishes streaming. Used by the frontend to render completion indicators.

| Field | Type | Description |
|-------|------|-------------|
| `agent_type` | `"main" \| "subagent"` | Which agent completed |
| `invocation_id` | `string` | Unique ID for this agent stream |
| `agent_name` | `string \| null` | Display name (e.g., `"EVM Analyst"`, `"Assistant"`) |
| `completed_at` | `ISO datetime` | Completion timestamp |

```json
{
  "type": "agent_complete",
  "agent_type": "subagent",
  "invocation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "agent_name": "EVM Analyst",
  "completed_at": "2026-06-14T14:32:15.123Z"
}
```

### `planning` -- Agent planning step

Sent when the agent creates an execution plan using the `write_todos` tool.

| Field | Type | Description |
|-------|------|-------------|
| `plan` | `string \| null` | Plan description |
| `steps` | `PlanningStep[] \| null` | Steps with `text` and `done` fields |
| `step_number` | `int \| null` | Current step |
| `total_steps` | `int \| null` | Total steps in plan |
| `invocation_id` | `string \| null` | Invocation ID |

```json
{
  "type": "planning",
  "plan": "Analyze the electrical installation WBE",
  "steps": [
    { "text": "Fetch WBE details", "done": false },
    { "text": "Calculate EVM metrics", "done": false },
    { "text": "Summarize findings", "done": false }
  ],
  "step_number": 1,
  "total_steps": 3,
  "invocation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### `plan_update` -- Execution plan created or step status changed

Emitted by the **planner** (supervisor orchestrator) when an execution plan is created or when a step transitions status. This is an **event-bus payload** (`AgentEventType.PLAN_UPDATE`, `event_types.py:25`), not a backend Pydantic WS message class — the WS forwarder adapts it into a frontend-shaped message by stamping `type: "plan_update"` onto the event data (`api/routes/ai_chat.py:80`).

| Field | Type | Description |
|-------|------|-------------|
| `plan.original_request` | `string` | Original user request |
| `plan.steps` | `PlanStep[]` | Steps with `step_index`, `specialist`, `task_description`, `dependencies`, `expected_output`, `status` |
| `plan.estimated_complexity` | `"simple" \| "moderate" \| "complex"` | Planner complexity estimate |
| `plan.requires_planning` | `boolean` | Whether planning was required |
| `plan_markdown` | `string` | Pre-rendered markdown of the plan |
| `completed_steps` | `int` | Number of completed steps |
| `total_steps` | `int` | Total steps in plan |

```json
{
  "type": "plan_update",
  "plan": {
    "original_request": "Analyze the electrical installation WBE for cost overruns",
    "steps": [
      {
        "step_index": 0,
        "specialist": "evm_analyst",
        "task_description": "Compute CPI/SPI for the WBE",
        "dependencies": [],
        "expected_output": "EVM metrics with variance",
        "status": "in_progress"
      }
    ],
    "estimated_complexity": "moderate",
    "requires_planning": true
  },
  "plan_markdown": "## Plan\n1. Compute CPI/SPI for the WBE ...",
  "completed_steps": 0,
  "total_steps": 1
}
```

### `briefing_update` -- Specialist briefing update

Sent when a specialist agent updates the compiled briefing document. The frontend uses this to render a live briefing panel. `briefing` is a **structured document**, not a flat markdown string (`schemas/ai.py:747-780`).

| Field | Type | Description |
|-------|------|-------------|
| `briefing` | `BriefingDocumentPublic` | Structured briefing document (see below) |
| `specialist_name` | `string` | Name of the specialist that updated |
| `completed_specialists` | `string[]` | List of completed specialist names |

`BriefingDocumentPublic` / `BriefingDocumentData` (`schemas/ai.py:747-758`; frontend `types.ts:334-340`):

| Field | Type | Description |
|-------|------|-------------|
| `original_request` | `string` | Original user request |
| `follow_up_requests` | `string[]` | Follow-up requests |
| `sections` | `BriefingSectionPublic[]` | One section per specialist |
| `supervisor_analysis` | `string \| null` | Supervisor synthesis |
| `markdown` | `string` | Pre-rendered markdown fallback |

Each `BriefingSectionPublic` has `specialist_name`, `summary`, `key_findings[]`, `open_questions[]`, `delegation_notes`, and optional `task_description` / `step_index`.

```json
{
  "type": "briefing_update",
  "briefing": {
    "original_request": "Analyze the electrical installation WBE for cost overruns",
    "follow_up_requests": [],
    "sections": [
      {
        "specialist_name": "evm_analyst",
        "summary": "CPI of 0.95 indicates a slight cost overrun...",
        "key_findings": ["Cost variance: -$15,000", "SPI: 1.02 (on schedule)"],
        "open_questions": ["Is the overrun due to material or labor?"],
        "delegation_notes": "",
        "task_description": "Compute EVM metrics",
        "step_index": 0
      }
    ],
    "supervisor_analysis": null,
    "markdown": "# Briefing\n\n## EVM Analyst\nCPI: 0.95..."
  },
  "specialist_name": "evm_analyst",
  "completed_specialists": ["evm_analyst"]
}
```

### `agent_transition` -- Agent enter/exit

Sent when control transfers between agents in the supervisor graph. Used for visual transitions in the UI. This is a backend Pydantic WS schema (`WSAgentTransitionMessage`, `schemas/ai.py:706-724`).

| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | `string` | Name of the agent being entered or exited |
| `direction` | `"enter" \| "exit"` | Whether entering or exiting |
| `invocation_id` | `string \| null` | Unique ID for this agent activation |

```json
{
  "type": "agent_transition",
  "agent_name": "evm_analyst",
  "direction": "enter",
  "invocation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

### `temporal_context_change` -- Temporal view context changed

Emitted by the `set_temporal_context` tool (`tools/temporal_tools.py:178`, `event_type="temporal_context_change"`) when the assistant changes the temporal viewing context. Like `plan_update`, this is an **event-bus payload** adapted by the WS forwarder — not a backend Pydantic WS message class.

| Field | Type | Description |
|-------|------|-------------|
| `as_of` | `string \| null` | New "as of" timestamp (ISO datetime), or null for "now" |
| `branch_name` | `string` | New branch name |
| `branch_mode` | `"merged" \| "isolated"` | New branch view mode |

```json
{
  "type": "temporal_context_change",
  "as_of": "2026-03-01T00:00:00Z",
  "branch_name": "BR-001",
  "branch_mode": "isolated"
}
```

---

## Server to Client Messages -- Approval & Ask-User Workflows

### `approval_request` -- Tool needs approval

Sent when a tool with `risk_level >= HIGH` requires user approval in `standard` mode (`BackcastSecurityMiddleware._check_risk_level_with_approval`, `middleware/backcast_security.py:590-595`). The client displays an approval dialog with a countdown timer.

| Field | Type | Description |
|-------|------|-------------|
| `approval_id` | `string` | UUID for this approval request |
| `session_id` | `UUID` | Chat session ID |
| `tool_name` | `string` | Name of the tool requiring approval |
| `tool_args` | `object` | Arguments that will be passed to the tool |
| `risk_level` | `"low" \| "high" \| "critical"` | Risk level of the tool (`Literal[RISK_LEVEL_LOW, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL]`, `schemas/ai.py:870-873`) |
| `expires_at` | `ISO datetime` | Client-facing expiration (5 minutes from request, set by `InterruptNode`, `tools/interrupt_node.py:187`) |

> **Approval timeout (two layers).** The client-facing `expires_at` is 5 minutes (`InterruptNode`). The actual server-side cancellation timeout is **`settings.AI_APPROVAL_TIMEOUT_SECONDS = 60` seconds** (`config.py:48`); the middleware `_poll_for_approval` gives up at 60s (`middleware/backcast_security.py:423`). Treat the 60s middleware timeout as authoritative for "how long the tool actually blocks."

```json
{
  "type": "approval_request",
  "approval_id": "abc12345-6789-def0-1234-567890abcdef",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "tool_name": "update_cost_element",
  "tool_args": {
    "cost_element_id": "987e6543-e21b-45d3-b789-123456789abc",
    "actual_cost": 150000
  },
  "risk_level": "high",
  "expires_at": "2026-06-14T14:35:00Z"
}
```

### `polling_heartbeat` -- Approval countdown

Sent every 5 seconds during the approval waiting period to keep the WebSocket connection alive and provide countdown state.

| Field | Type | Description |
|-------|------|-------------|
| `approval_id` | `string` | Approval ID being polled |
| `elapsed_seconds` | `float` | Time elapsed since approval request |
| `remaining_seconds` | `float` | Time remaining until timeout |

```json
{
  "type": "polling_heartbeat",
  "approval_id": "abc12345-6789-def0-1234-567890abcdef",
  "elapsed_seconds": 10.0,
  "remaining_seconds": 50.0
}
```

### `ask_user` -- Agent needs user input

Sent when the agent needs user input via the `ask_user` tool (`WSAskUserMessage`, `schemas/ai.py:1038-1066`). The client renders a prompt and the user either answers (→ `ask_user_response`) or lets `expires_at` pass.

| Field | Type | Description |
|-------|------|-------------|
| `question` | `string` | The question to present to the user |
| `ask_id` | `string` | Unique identifier for this ask request |
| `context` | `string \| null` | Optional one-line explanation of why the question is asked |
| `options` | `string[] \| null` | Optional suggested answers for one-click selection |
| `expires_at` | `ISO datetime` | UTC timestamp at which the wait times out |
| `timeout_seconds` | `int` | Total seconds the tool will wait for a response |

```json
{
  "type": "ask_user",
  "question": "Which cost overrun threshold should I use for flagging WBEs?",
  "ask_id": "q1w2e3r4-t5y6-7890-abcd-ef1234567890",
  "context": "I need this to filter the EVM analysis.",
  "options": ["5% (standard)", "10% (lenient)"],
  "expires_at": "2026-06-14T14:31:00Z",
  "timeout_seconds": 120
}
```

---

## Server to Client Messages -- Lifecycle

### `complete` -- Response finished

Terminal event. Sent when the entire response is complete, including all tool calls and agent segments.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `UUID` | Session identifier |
| `message_id` | `UUID \| null` | Final message identifier (null if execution errored) |
| `token_usage` | `object \| null` | Token metrics: `prompt_tokens`, `completion_tokens`, `total_tokens` |

```json
{
  "type": "complete",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "message_id": "def45678-9abc-0123-def-456789abcdef",
  "token_usage": {
    "prompt_tokens": 2450,
    "completion_tokens": 820,
    "total_tokens": 3270
  }
}
```

### `error` -- Error occurred

Sent when an error occurs during processing. Also used for permission denied (code 403).

| Field | Type | Description |
|-------|------|-------------|
| `message` | `string` | Error details |
| `code` | `int \| null` | Optional error code (e.g., 403 for permission denied) |

```json
{
  "type": "error",
  "message": "Failed to connect to LLM provider",
  "code": 500
}
```

Permission denied variant (code 403):

```json
{
  "type": "error",
  "message": "You do not have permission to modify cost elements in this project",
  "code": 403,
  "detail": "permission_denied",
  "project_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "required_permission": "cost_element-update"
}
```

### `ping` -- Keepalive check

Sent every 20 seconds during long agent executions to prevent proxy timeouts. The client should respond with a `pong` message.

No additional fields beyond `type`.

```json
{
  "type": "ping"
}
```

---

## Message Unions

The two sides maintain **separate** discriminated unions. The backend union is a closed set of Pydantic WS message classes; the frontend union additionally includes the event-bus-payload-shaped messages that the WS forwarder adapts (`api/routes/ai_chat.py:80`) but that have no backend Pydantic WS class.

### Backend Union (`WSMessage`, `schemas/ai.py:1069-1087`)

```
WSMessage =
    WSTokenMessage
  | WSTokenBatchMessage
  | WSToolCallMessage
  | WSToolResultMessage
  | WSCompleteMessage
  | WSErrorMessage
  | WSApprovalRequestMessage
  | WSPollingHeartbeatMessage
  | WSThinkingMessage
  | WSPlanningMessage
  | WSSubagentMessage
  | WSSubagentResultMessage
  | WSAgentCompleteMessage
  | WSContentResetMessage
  | WSExecutionStatusMessage
  | WSAskUserMessage
```

> Note: `WSAgentTransitionMessage` and `WSAskUserMessage` are defined as Pydantic models in `schemas/ai.py` (706-724 and 1038-1066). `WSAgentTransitionMessage` is currently emitted via the event bus and forwarded generically rather than via the closed union, but the class exists. `plan_update` and `temporal_context_change` are **not** backend Pydantic WS classes — they are `AgentEvent` payloads adapted by the forwarder.

### Frontend Union (`WSServerMessage`, `types.ts:461-482`)

```
WSServerMessage =
  | WSTokenMessage
  | WSTokenBatchMessage
  | WSToolCallMessage
  | WSToolResultMessage
  | WSCompleteMessage
  | WSErrorMessage
  | WSPlanningMessage
  | WSSubagentMessage
  | WSSubagentResultMessage
  | WSThinkingMessage
  | WSContentResetMessage
  | WSPollingHeartbeatMessage
  | WSPingMessage
  | WSAgentCompleteMessage
  | WSAgentTransitionMessage
  | WSExecutionStartedMessage
  | WSExecutionStatusMessage
  | WSBriefingMessage
  | WSPlanUpdateMessage
  | WSTemporalContextChangeMessage
  | WSAskUserMessage
```

The frontend union is the authoritative consumer-facing list and includes `WSPlanUpdateMessage`, `WSTemporalContextChangeMessage`, `WSAgentTransitionMessage`, and `WSAskUserMessage` as first-class members.

---

## Message Flow Diagrams

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
  |                                          |-- 60s middleware poll begins
  |<-- polling_heartbeat {remaining} --------|
  |<-- polling_heartbeat {remaining} --------|
  |--- approval_response {approved: true} -->|
  |                                          |-- tool executes
  |<-- tool_result --------------------------|
```

---

## Development Patterns

### Adding a New Message Type

1. **Backend schema**: Add a Pydantic model in `backend/app/models/schemas/ai.py` and add it to the `WSMessage` union (for closed-set messages), OR publish it as an `AgentEvent` payload (for event-bus-only messages adapted by the forwarder).
2. **Frontend type**: Add an interface in `frontend/src/features/ai/chat/types.ts` and add it to the `WSServerMessage` union.
3. **Type guard**: Add an `is*Message()` function.
4. **Backend publish**: Call `bus.publish(AgentEvent(event_type="...", data=...))` in agent execution.
5. **Frontend handler**: Add a routing case in `handleMessage` in `useStreamingChat.ts`.

### Testing WebSocket Features

**Frontend unit tests**: `frontend/src/features/ai/chat/api/__tests__/useStreamingChat.test.tsx`

- Mock `WebSocket` class, `useAuthStore`, `useTimeMachineStore`
- Use `connectViaSendMessage` helper for the lazy connection pattern
- Mock `sessionStorage` for sequence persistence tests
- Use `vi.useFakeTimers()` for timeout-related tests

---

## Common Pitfalls

1. **Forgetting `execution_mode`**: `sendMessage` requires `executionMode` as an argument. Without it, the hook errors immediately.

2. **React Strict Mode double-mount**: The hook guards against this with `isFirstMountRef`. When testing, account for the fact that the first mount is "consumed" — a second render won't create a second connection.

3. **Sequence persistence across navigation**: Without sessionStorage persistence, remounting the chat component sends `last_seen_sequence=0`, causing full event replay and duplicate content.

4. **`recentlyCompletedRef` race**: After completion, the `activeExecutionId` effect might try to close the connection before follow-up messages can be sent. The 5-second guard prevents this.

5. **WebSocket close code 1008 vs 4008**: 1008 means permanent auth failure (don't reconnect). 4008 means token expired (refresh and reconnect). The frontend handles these differently.

6. **Two approval timeouts**: `InterruptNode.expires_at` (5 min, client-facing) and `settings.AI_APPROVAL_TIMEOUT_SECONDS` (60s, middleware poll). The 60s value governs actual cancellation.

---

## Source Files

| Component | Backend | Frontend |
|-----------|---------|----------|
| WS Endpoint | `app/api/routes/ai_chat.py` | -- |
| WS Hook | -- | `features/ai/chat/api/useStreamingChat.ts` |
| Message Types | `app/models/schemas/ai.py` (626-1087) | `features/ai/chat/types.ts` |
| Event Bus | `app/ai/execution/agent_event_bus.py` | -- |
| Agent Service | `app/ai/agent_service.py` | -- |
| Agent Config | `app/services/ai_config_service.py` (`AIConfigService`) | -- |
| Risk Gating | `app/ai/middleware/backcast_security.py`, `app/ai/tools/__init__.py` | -- |
| Approval / Interrupt | `app/ai/tools/interrupt_node.py` | -- |
| Upload | `app/api/routes/ai_upload.py` | `features/ai/chat/api/attachmentUpload.ts` |
| Frontend Tests | -- | `features/ai/chat/api/__tests__/useStreamingChat.test.tsx` |
