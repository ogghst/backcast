# AI Tools API Documentation

## Overview

The AI Tools API provides a comprehensive tool system for LangGraph agents with built-in risk categorization, execution modes, and approval workflows. This document describes the API contracts, WebSocket protocols, and execution modes.

**Version:** 1.0.0
**Last Updated:** 2026-03-22

---

## Table of Contents

1. [Execution Modes](#execution-modes)
2. [Risk Levels](#risk-levels)
3. [WebSocket Protocol](#websocket-protocol)
4. [API Schemas](#api-schemas)
5. [Tool Metadata](#tool-metadata)
6. [Approval Workflow](#approval-workflow)

---

## Execution Modes

The AI Tools API supports three execution modes that control which tools can be executed based on their risk levels:

| Mode | Description | Risk Levels Allowed | Approval Required |
|------|-------------|---------------------|-------------------|
| `safe` | Read-only operations | `low` only | No |
| `standard` | Normal operations (default) | `low`, `high` | Yes, for `high` (critical blocked) |
| `expert` | All operations | `low`, `high`, `critical` | No |

### Mode Selection

Execution mode is selected by the client via the `execution_mode` field in `WSChatRequest`:

```json
{
  "type": "chat",
  "message": "Create a new project",
  "execution_mode": "standard"
}
```

**Default:** `standard`

### Mode Persistence

The frontend stores the selected execution mode in `localStorage` under the key `ai_execution_mode`. The mode persists across browser sessions but resets to `standard` if not set.

---

## Risk Levels

Every AI tool is categorized with a risk level that determines which execution modes can use it:

| Risk Level | Description | Examples | Compatible Modes |
|------------|-------------|----------|------------------|
| `low` | Read-only operations, no side effects | - Query projects<br>- Get EVM metrics<br>- List change orders | `safe`, `standard`, `expert` |
| `high` | Data modification with validation | - Create project<br>- Update WBE<br>- Generate forecast | `standard`, `expert` |
| `critical` | Destructive operations, bulk changes | - Delete project<br>- Bulk update WBEs<br>- Approve change order | `expert` only (blocked in `standard` mode) |

### Default Risk Level

Tools without an explicit `risk_level` annotation default to `RiskLevel.HIGH` for backward compatibility and safety.

---

## WebSocket Protocol

### Message Flow

```
Client → Server: WSChatRequest
    ↓
Server processes with LangGraph agent
    ↓
Server → Client: Stream of messages (tokens, tool calls, etc.)
    ↓
If high-risk tool in standard mode:
    Server → Client: WSApprovalRequestMessage
    Client displays ApprovalDialog
    Client → Server: WSApprovalResponseMessage
    Server resumes execution
Note: Critical tools are blocked entirely in standard mode -- they never reach approval.
    ↓
Server → Client: WSCompleteMessage
```

### Message Types

#### Client → Server Messages

**WSChatRequest**
```json
{
  "type": "chat",
  "message": "Create a new project called Test Project",
  "session_id": "uuid-or-null",
  "assistant_config_id": "uuid",
  "title": "Optional session title",
  "project_id": "uuid-or-null",
  "branch_id": "uuid-or-null",
  "as_of": "datetime-or-null",
  "branch_name": "main",
  "branch_mode": "merged",
  "execution_mode": "standard",  // NEW: execution mode field
  "attachments": [],
  "images": []
}
```

**WSApprovalResponseMessage**
```json
{
  "type": "approval_response",
  "approval_id": "uuid",
  "approved": true,
  "user_id": "uuid",
  "timestamp": "2026-03-22T10:30:00Z"
}
```

#### Server → Client Messages

**WSTokenMessage**
```json
{
  "type": "token",
  "content": "partial",
  "session_id": "uuid"
}
```

**WSToolCallMessage**
```json
{
  "type": "tool_call",
  "tool": "create_project",
  "args": {"name": "Test Project"}
}
```

**WSToolResultMessage**
```json
{
  "type": "tool_result",
  "tool": "create_project",
  "result": {"status": "success", "project_id": "uuid"}
}
```

**WSApprovalRequestMessage** (NEW)
```json
{
  "type": "approval_request",
  "approval_id": "uuid",
  "session_id": "uuid",
  "tool_name": "delete_project",
  "tool_args": {"project_id": "uuid"},
  "risk_level": "high",
  "expires_at": "2026-03-22T10:35:00Z"  // 5 minutes from request
}
```

**WSCompleteMessage**
```json
{
  "type": "complete",
  "session_id": "uuid",
  "message_id": "uuid"
}
```

**WSErrorMessage**
```json
{
  "type": "error",
  "message": "Error description",
  "code": 400
}
```

---

## API Schemas

### Pydantic Schemas

Located in `backend/app/models/schemas/ai.py`:

```python
class WSChatRequest(BaseModel):
    """WebSocket chat message from client."""
    type: str = Field(default="chat")
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: UUID | None = None
    assistant_config_id: UUID | None = None
    title: str | None = Field(None, max_length=255)
    project_id: UUID | None = None
    branch_id: UUID | None = None
    as_of: datetime | None = None
    branch_name: str | None = Field("main")
    branch_mode: Literal["merged", "isolated"] | None = Field("merged")
    execution_mode: Literal["safe", "standard", "expert"] = Field("standard")  # NEW
    attachments: list[FileAttachment] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)

class WSApprovalRequestMessage(BaseModel):
    """Server -> Client: Request approval for critical tool execution."""
    type: Literal["approval_request"]
    approval_id: str
    session_id: UUID
    tool_name: str
    tool_args: dict[str, Any]
    risk_level: Literal["high"]
    expires_at: datetime

class WSApprovalResponseMessage(BaseModel):
    """Client -> Server: User decision on approval request."""
    type: Literal["approval_response"]
    approval_id: str
    approved: bool
    user_id: UUID
    timestamp: datetime
```

### TypeScript Types

Located in `frontend/src/features/ai/chat/types.ts`:

```typescript
export type ExecutionMode = 'safe' | 'standard' | 'expert';

export interface WSChatRequest {
  type: string;
  message: string;
  session_id?: string;
  assistant_config_id?: string;
  title?: string;
  project_id?: string;
  branch_id?: string;
  as_of?: string;
  branch_name?: string;
  branch_mode?: 'merged' | 'isolated';
  execution_mode: ExecutionMode;  // NEW
  attachments: FileAttachment[];
  images: string[];
}

export interface ApprovalRequestMessage {
  type: 'approval_request';
  approval_id: string;
  session_id: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  risk_level: 'critical';
  expires_at: string;
}

export interface ApprovalResponseMessage {
  type: 'approval_response';
  approval_id: string;
  approved: boolean;
  user_id: string;
  timestamp: string;
}
```

---

## Tool Metadata

Every AI tool is decorated with `@ai_tool` and includes metadata:

```python
@ai_tool(
    name="create_project",
    description="Create a new project",
    permissions=["project:create"],
    category="crud",
    risk_level=RiskLevel.HIGH,  # NEW: risk level
)
async def create_project(
    name: str,
    description: str | None = None,
    context: ToolContext,
) -> dict[str, Any]:
    """Create a new project."""
    # Implementation
    pass
```

### Tool Metadata Structure

```python
@dataclass
class ToolMetadata:
    """Metadata for AI tools."""
    name: str
    description: str
    permissions: list[str]
    category: str | None = None
    version: str = "1.0.0"
    risk_level: RiskLevel = RiskLevel.HIGH  # NEW field
```

### Tool Discovery

Tools are discoverable via the `/api/v1/ai/tools` endpoint:

```json
{
  "tools": [
    {
      "name": "create_project",
      "description": "Create a new project",
      "permissions": ["project:create"],
      "category": "crud",
      "version": "1.0.0",
      "risk_level": "high"
    },
    {
      "name": "delete_project",
      "description": "Delete a project and all its data",
      "permissions": ["project:delete"],
      "category": "crud",
      "version": "1.0.0",
      "risk_level": "critical"
    }
  ]
}
```

---

## Approval Workflow

### When Approval is Required

Approval is required when:
1. Execution mode is `standard`
2. Tool has `risk_level="high"`
3. User has the required permissions

Note: Critical tools are BLOCKED entirely in standard mode and never reach the approval flow.

### Approval Flow

```
1. User sends message with execution_mode="standard"
2. Agent selects critical tool
3. Server sends WSApprovalRequestMessage
4. Frontend displays ApprovalDialog (non-blocking)
5. User clicks "Approve" or "Reject"
6. Frontend sends WSApprovalResponseMessage
7. Server processes response:
   - If approved: Execute tool and return results
   - If rejected: Return error message
```

### Approval Timeout

Approval requests expire after 5 minutes. If the user doesn't respond within this time, the tool execution is cancelled with an error message.

### Audit Logging

All tool executions and approval decisions are logged to the audit log:

```python
# Audit entry for tool execution
{
  "timestamp": "2026-03-22T10:30:00Z",
  "user_id": "uuid",
  "tool_name": "delete_project",
  "tool_args": {"project_id": "uuid"},
  "execution_mode": "standard",
  "risk_level": "critical",
  "approved": true,
  "approval_id": "uuid"
}
```

---

## Error Handling

### Risk-Based Errors

```json
{
  "type": "error",
  "message": "Tool 'delete_project' has critical risk level. Standard mode blocks critical tools entirely. Switch to expert mode to use this tool.",
  "code": 403
}
```

```json
{
  "type": "error",
  "message": "Tool 'delete_project' requires critical risk level. Safe mode only allows low-risk tools.",
  "code": 403
}
```

### Approval Errors

```json
{
  "type": "error",
  "message": "Tool execution was rejected by user",
  "code": 403
}
```

```json
{
  "type": "error",
  "message": "Approval request has expired (5-minute timeout)",
  "code": 408
}
```

---

## Performance

### Risk Check Overhead

Risk checking adds minimal overhead to tool execution:
- **Median overhead:** < 10ms (measured via benchmark tests)
- **Implementation:** In-memory filtering, no database queries

### Benchmark Results

See `backend/tests/performance/test_risk_check_overhead.py` for detailed performance benchmarks.

---

## Security Considerations

1. **Permission checking** always runs before risk checking
2. **Approval tokens** are cryptographically signed UUIDs
3. **Approval timeout** prevents indefinite holds
4. **Audit logging** tracks all critical tool executions
5. **Default risk level** is `HIGH` for unannotated tools (safe default)

---

## Backward Compatibility

- Existing tools without `risk_level` default to `RiskLevel.HIGH`
- Clients not sending `execution_mode` default to `standard`
- WebSocket messages are additive (new message types don't break existing clients)

---

## Related Documentation

- [User Guide: AI Execution Modes](/docs/05-user-guide/ai-execution-modes.md)
- [Architecture Decision: RBAC Service](/docs/02-architecture/decisions/ADR-007-rbac-service.md)
- [Implementation Plan: AI Tool Risk Categorization](/docs/03-project-plan/iterations/2026-03-20-ai-tool-risk-categorization/01-plan.md)

---

## Changelog

### Version 1.0.0 (2026-03-22)

**Added:**
- Execution modes: `safe`, `standard`, `expert`
- Risk levels: `low`, `high`, `critical`
- Approval workflow for high-risk tools in standard mode; critical tools blocked
- WebSocket messages: `WSApprovalRequestMessage`, `WSApprovalResponseMessage`
- Tool metadata `risk_level` field
- Audit logging for tool executions and approvals

**Changed:**
- `WSChatRequest` now includes `execution_mode` field (default: `standard`)

**Deprecated:**
- None

**Removed:**
- None
