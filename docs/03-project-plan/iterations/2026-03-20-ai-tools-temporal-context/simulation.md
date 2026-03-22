# AI Chat Temporal Context Simulation

## Scenario Setup

**User Configuration via Time Machine Component:**
- **Date:** January 15, 2025 at 10:30 AM (historical view)
- **Branch:** "BR-001" (Change Order for "Conveyor Upgrade")
- **Mode:** "isolated" (see only this branch's data, not main)

**Project:** "Automation Line B" (started December 2024)

---

## WebSocket Message Flow

### 1. Client → Server: User Message

```json
{
  "type": "chat",
  "message": "Show me all work breakdown elements for this project",
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "project_id": "proj-123",
  "branch_id": null,
  "assistant_config_id": "config-abc",

  // TEMPORAL CONTEXT FROM TIME MACHINE (NEW)
  "as_of": "2025-01-15T10:30:00Z",
  "branch_name": "BR-001",
  "branch_mode": "isolated"
}
```

### 2. Server: ToolContext Construction

```python
# In AgentService.chat_stream()
tool_context = ToolContext(
    session=db,
    user_id="user-123",
    user_role="project_manager",
    project_id="proj-123",
    branch_id=None,  # No change order session context

    # NEW TEMPORAL FIELDS
    as_of=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
    branch_name="BR-001",
    branch_mode="isolated"
)
```

### 3. Server: System Prompt with Temporal Context

```python
# System prompt generated BEFORE AI response
base_prompt = "You are a project management assistant for Backcast EVS..."

# Temporal context detected (non-default values)
temporal_note = """
[TEMPORAL CONTEXT]
You are viewing data as of January 15, 2025 in branch 'BR-001' (isolated mode).
- Only show entities that existed on this date
- Only show data from branch 'BR-001', NOT from main branch
- Mention this temporal context when it materially affects your answer
"""

system_prompt = base_prompt + temporal_note
```

---

## Tool Execution with Temporal Parameters

### 4. AI Tool Call: list_wbes

**BEFORE (Current Implementation - ignores temporal context):**
```python
# Tool receives context but IGNORES it
def list_wbes(
    context: Annotated[ToolContext, InjectedToolArg()],
    project_id: str,
    skip: int = 0,
    limit: int = 100
) -> str:
    # ❌ HARDCODED - ignores context.branch_name and context.as_of
    wbes, total = context.wbe_service.get_wbes(
        project_id=project_id,
        skip=skip,
        limit=limit,
        branch="main",  # ALWAYS main!
        as_of=None      # ALWAYS now!
    )
    return json.dumps({"wbes": wbes, "total": total})
```

**AFTER (New Implementation - respects temporal context):**
```python
# Tool receives context and USES it
def list_wbes(
    context: Annotated[ToolContext, InjectedToolArg()],
    project_id: str,
    skip: int = 0,
    limit: int = 100
) -> str:
    # ✅ Uses temporal parameters from context
    wbes, total = context.wbe_service.get_wbes(
        project_id=project_id,
        skip=skip,
        limit=limit,
        # Use context values with defaults
        branch=context.branch_name or "main",
        branch_mode=context.branch_mode or "merged",
        as_of=context.as_of
    )
    return json.dumps({"wbes": wbes, "total": total})
```

---

## Service Layer: Temporal Query Execution

### 5. Database Query with Temporal Filtering

```python
# In WBEService.get_wbes()
# PostgreSQL query with temporal filters

SELECT DISTINCT ON (wbe.id) wbe.*
FROM work_breakdown_elements wbe
WHERE wbe.project_id = 'proj-123'
  -- VALID TIME: Entity must exist as of Jan 15, 2025
  AND wbe.valid_time @> '2025-01-15T10:30:00Z'::timestamptz
  -- BRANCH FILTER: Only in BR-001 (isolated mode)
  AND wbe.branch_name = 'BR-001'
  -- ZOMBIE CHECK: Not soft-deleted as of this date
  AND (wbe.deleted_at IS NULL OR wbe.deleted_at > '2025-01-15T10:30:00Z'::timestamptz)
ORDER BY wbe.id, wbe.transaction_time DESC
LIMIT 100;
```

**Result:** Returns only WBEs that:
1. Existed on January 15, 2025 (time-travel)
2. Belong to branch "BR-001" (branch isolation)
3. Were not deleted as of that date (zombie protection)

---

## AI Response with Temporal Awareness

### 6. Server → Client: Streaming Response

```json
{
  "type": "token",
  "token": "Here"
}
{
  "type": "token",
  "token": " are"
}
{
  "type": "token",
  "token": " the"
}
...
{
  "type": "token",
  "token": " work"
}
{
  "type": "token",
  "token": " breakdown"
}
...
{
  "type": "complete",
  "message_id": "msg-456"
}
```

### 7. Final AI Response (What User Sees)

> "Here are the 3 work breakdown elements for Automation Line B:
>
> **Note:** This reflects the state as of **January 15, 2025** in change order branch **'BR-001'** (Conveyor Upgrade). You're viewing isolated branch data, so WBEs from the main branch are not shown.
>
> 1. **WBE-001: Conveyor Structure** - $45,000 budget
> 2. **WBE-002: Motor Installation** - $12,500 budget
> 3. **WBE-003: Control System** - $28,000 budget
>
> Total: 3 WBEs | $85,500 budgeted"

---

## Comparison: What If User Changed Temporal Context?

### Scenario A: Same Query, Different Date

**Time Machine:** Set to **February 20, 2025** (after more work was done)

> AI Response:
> "Here are the **5** work breakdown elements for Automation Line B:
>
> **Note:** This reflects the state as of **February 20, 2025** in change order branch **'BR-001'**.
>
> 1. **WBE-001: Conveyor Structure** - $45,000 budget (Completed)
> 2. **WBE-002: Motor Installation** - $12,500 budget (Completed)
> 3. **WBE-003: Control System** - $28,000 budget (In Progress)
> 4. **WBE-004: Safety Sensors** - $8,000 budget (Planned) ← *NEW*
> 5. **WBE-005: Testing** - $5,000 budget (Planned) ← *NEW*
>
> Total: 5 WBEs | $98,500 budgeted"

### Scenario B: Same Query, Main Branch (Merged Mode)

**Time Machine:** Set to **branch: "main"**, **mode: "merged"**

> AI Response:
> "Here are the **8** work breakdown elements for Automation Line B:
>
> **Note:** This reflects the state as of **now** in the **main branch** (merged mode shows all approved changes).
>
> [Shows all WBEs from main branch including approved change orders]"

---

## Key Behavioral Changes

### BEFORE Implementation ❌

```
User: "Show me projects"
Time Machine: Set to Jan 15, 2025, branch BR-001
AI: Shows 10 projects (current state, main branch) ← WRONG!
```

### AFTER Implementation ✅

```
User: "Show me projects"
Time Machine: Set to Jan 15, 2025, branch BR-001
AI: Shows 7 projects as of Jan 15, 2025 in BR-001 (isolated) ← CORRECT!
AI: "Note: Viewing data as of January 15, 2025 in branch 'BR-001'..."
```

---

## Technical Trace: Full Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│ USER ACTION                                                          │
│ Sets Time Machine: date=Jan 15, 2025, branch=BR-001, mode=isolated  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND: useTimeMachineStore                                       │
│ selectedTime: "2025-01-15T10:30:00Z"                                │
│ selectedBranch: "BR-001"                                            │
│ viewMode: "isolated"                                                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ WEBSOCKET MESSAGE (Client → Server)                                 │
│ {                                                                   │
│   "message": "Show me WBEs",                                        │
│   "as_of": "2025-01-15T10:30:00Z",  ← NEW                           │
│   "branch_name": "BR-001",             ← NEW                           │
│   "branch_mode": "isolated"            ← NEW                           │
│ }                                                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND: AgentService.chat_stream()                                │
│ Extract temporal params → Create ToolContext                        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SYSTEM PROMPT ENHANCEMENT                                           │
│ "You are viewing data as of Jan 15, 2025 in branch BR-001..."      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AI TOOL: list_wbes(context, project_id)                            │
│ Uses context.as_of, context.branch_name, context.branch_mode       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SERVICE LAYER: WBEService.get_wbes(                                │
│   as_of=datetime(2025,1,15),                                       │
│   branch="BR-001",                                                  │
│   branch_mode=BranchMode.STRICT                                    │
│ )                                                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DATABASE: PostgreSQL TSTZRANGE Query                               │
│ WHERE valid_time @> '2025-01-15T10:30:00Z'                          │
│   AND branch_name = 'BR-001'                                       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RESPONSE: "Here are 3 WBEs as of Jan 15, 2025 in BR-001..."        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Edge Cases Handled

### Case 1: Future Date Query
```
User Time Machine: as_of = "2026-12-31" (future)
Service Layer: Returns empty results (no entities yet)
AI Response: "There are no WBEs projected for this future date."
```

### Case 2: Invalid Branch
```
User Time Machine: branch = "non-existent"
Service Layer: Returns empty (branch doesn't exist)
AI Response: "This branch doesn't exist yet or has no data."
```

### Case 3: Mid-Conversation Time Machine Change
```
User (Time Machine at Jan 15): "Show me projects"
AI: Shows 7 projects as of Jan 15...

User changes Time Machine to Feb 20...

User: "And how many WBEs?"
AI: Shows WBEs as of Feb 20 (newest context applied immediately)
```
