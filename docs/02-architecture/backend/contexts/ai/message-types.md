# WebSocket Message Types Reference

**Last Updated:** 2026-05-01
**Status:** Active

Complete reference for the AI chat WebSocket protocol. All types are defined in:

- Frontend: [frontend/src/features/ai/chat/types.ts](../../../../../frontend/src/features/ai/chat/types.ts)
- Backend: [backend/app/models/schemas/ai.py](../../../../../backend/app/models/schemas/ai.py) (lines 507-936)

The protocol uses simple JSON messages with a `type` discriminator field.

---

## Client to Server Messages

### `chat` -- Send a message to the AI

Initiates a new conversation or continues an existing one. The server creates an `AIAgentExecution` and streams events back.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | Yes | User message content (1-10000 chars) |
| `session_id` | `UUID \| null` | No | Existing session ID, or null for new session |
| `assistant_config_id` | `UUID \| null` | No | Assistant config to use (required for new sessions) |
| `title` | `string` | No | Optional session title for new sessions |
| `execution_mode` | `"safe" \| "standard" \| "expert"` | No | Tool risk mode (default: `"standard"`) |
| `as_of` | `ISO datetime \| null` | No | Historical date for temporal queries |
| `branch_name` | `string` | No | Branch name (default: `"main"`) |
| `branch_mode` | `"merged" \| "isolated"` | No | Branch view mode (default: `"merged"`) |
| `project_id` | `UUID` | No | Project scope for project-specific chat |
| `branch_id` | `UUID` | No | Branch context UUID |
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

### `approval_response` -- Approve or reject a critical tool

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
  "timestamp": "2026-05-01T14:30:00Z"
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
  "completed_at": "2026-05-01T14:32:15.123Z"
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

### `briefing_update` -- Specialist briefing update

Sent when a specialist agent updates the compiled briefing document. The frontend uses this to render a live briefing panel.

| Field | Type | Description |
|-------|------|-------------|
| `briefing` | `string` | Compiled briefing markdown |
| `specialist_name` | `string` | Name of the specialist that updated |
| `completed_specialists` | `string[]` | List of completed specialist names |

```json
{
  "type": "briefing_update",
  "briefing": "# Project Briefing\n\n## EVM Analysis\nCPI: 0.95, SPI: 1.02...\n\n## Risk Assessment\n...",
  "specialist_name": "evm_analyst",
  "completed_specialists": ["evm_analyst"]
}
```

### `agent_transition` -- Agent enter/exit

Sent when control transfers between agents in the supervisor graph. Used for visual transitions in the UI.

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

---

## Server to Client Messages -- Approval Workflow

### `approval_request` -- Critical tool needs approval

Sent when a high-risk tool requires user approval in standard mode. The client displays an approval dialog with a countdown timer.

| Field | Type | Description |
|-------|------|-------------|
| `approval_id` | `string` | UUID for this approval request |
| `session_id` | `UUID` | Chat session ID |
| `tool_name` | `string` | Name of the tool requiring approval |
| `tool_args` | `object` | Arguments that will be passed to the tool |
| `risk_level` | `"low" \| "high" \| "critical"` | Risk level of the tool |
| `expires_at` | `ISO datetime` | Expiration time (5 minutes from request) |

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
  "expires_at": "2026-05-01T14:35:00Z"
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
  "remaining_seconds": 20.0
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

## Type Summary

### Server Message Union

The frontend defines a discriminated union `WSServerMessage` covering all server-to-client types:

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
  | WSExecutionStartedMessage
  | WSExecutionStatusMessage
  | WSBriefingMessage
```

### Message Flow Sequence

```
Client                          Server
  |                               |
  |-------- chat --------------->|  create execution, send execution_started
  |<------- thinking ------------|
  |                               |
  |<------- planning ------------|  (optional, if agent creates a plan)
  |                               |
  |<------- tool_call -----------|  agent invokes a tool
  |<------- tool_result ---------|  tool completes
  |                               |
  |<------- subagent ------------|  (optional, delegate to specialist)
  |<------- token_batch ---------|  specialist streams response
  |<------- subagent_result -----|  specialist completes
  |<------- content_reset -------|
  |                               |
  |<------- token_batch ---------|  main agent synthesis
  |<------- briefing_update -----|  (optional, if specialists updated briefing)
  |                               |
  |<------- agent_complete ------|  main agent done
  |<------- execution_status ----|  status = "completed"
  |<------- complete ------------|  terminal event with token_usage
  |                               |
  |<------- ping ----------------|  (periodic, every 20s during execution)
  |-------- pong --------------->|
```

### Reconnection Flow

```
Client                          Server
  |                               |
  |--- WebSocket disconnected ---|
  |                               |  execution continues in background
  |                               |  events buffered in AgentEventBus
  |                               |
  |--- WebSocket reconnected --->|
  |                               |
  |-------- subscribe ---------->|  execution_id + last_seen_sequence
  |<------- replay events -------|  all events since last_seen_sequence
  |<------- live events ---------|  resume real-time forwarding
```
