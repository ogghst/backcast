# Analysis: Agentic Loop with Human-in-the-Loop for AI Chat

**Date:** 2026-03-20
**Status:** ANALYSIS COMPLETE - Awaiting User Feedback
**Iteration:** AI Agent Human-in-the-Loop Integration
**Points:** TBD

---

## 1. Requirements Summary

### User-Specified Scope

| Requirement | Description |
|-------------|-------------|
| **Agent Mode Toggle** | User can optionally enable "agent mode" for autonomous execution |
| **Autonomous Execution** | Agent performs work automatically using available tools |
| **Stop/Resume Control** | User can stop agent execution at any time and resume when desired |
| **Real-time Instructions** | User can send additional instructions even while agent is running |
| **Progress Notifications** | User receives notifications about agent progress and completion |
| **Human-in-the-Loop** | Agent can pause and request human approval/feedback before proceeding |

---

## 2. Current State Assessment

### 2.1 Existing Backend Infrastructure

**LangGraph Implementation:**
- File: `backend/app/ai/graph.py`
- StateGraph with agent node → tools node → agent loop
- Max 5 tool iterations before forced completion
- MemorySaver checkpointer for state persistence
- WebSocket streaming for real-time communication

**Current Message Flow:**
```
User Message → WebSocket
    ↓
AgentService.chat_stream()
    ↓
LangGraph StateGraph execution
    ↓
Events streamed via WebSocket:
  - token: Individual LLM tokens
  - tool_call: Tool invocation start
  - tool_result: Tool execution result
  - complete: Response finished
  - error: Error occurred
```

**Key Limitation:** Current system runs the agent loop to completion without human intervention points.

### 2.2 Existing Frontend Infrastructure

**Streaming Chat Hook:**
- File: `frontend/src/features/ai/chat/api/useStreamingChat.ts`
- WebSocket connection management with auto-reconnect
- Message type guards for protocol discrimination
- Callbacks: onToken, onToolCall, onToolResult, onComplete, onError

**Missing Features:**
- No agent mode toggle
- No stop/resume control during execution
- No way to send additional instructions during execution
- No interrupt/approval UI for human-in-the-loop

---

## 3. LangGraph Human-in-the-Loop Research

### 3.1 Interrupt Mechanism

LangGraph provides built-in support for pausing execution and requesting human input:

```python
from langgraph.types import interrupt

@tool
def some_action(param: str) -> str:
    # Pause execution and request human input
    response = interrupt({
        "action": "some_action",
        "param": param,
        "message": "Approve this action?"
    })

    if response.get("action") == "approve":
        return f"Executed: {response.get('param', param)}"

    return "Action cancelled by user"
```

### 3.2 Resume with Command

```python
from langgraph.types import Command

# Resume with approval
result = graph.invoke(
    Command(resume={"action": "approve", "param": "modified_value"}),
    config={"configurable": {"thread_id": session_id}}
)
```

### 3.3 Streaming Custom Events

```python
from langgraph.config import get_stream_writer

@tool
def long_running_task(query: str) -> str:
    writer = get_stream_writer()
    writer({"type": "progress", "data": "Starting task..."})

    # Do work
    writer({"type": "progress", "data": "50% complete"})

    return "Task complete"
```

---

## 4. Architecture Design

### 4.1 Backend Changes

**Enhanced Agent State:**
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    tool_call_count: int
    next: str
    # NEW: Agent execution control
    agent_mode: bool  # Whether agent mode is enabled
    human_approval_required: bool  # Whether to pause for approval
    interrupt_data: dict[str, Any] | None  # Pending interrupt data
```

**New Graph Nodes:**
- `human_input_node`: Pauses execution and waits for human feedback
- Conditional routing: Checks if human approval is needed

**New WebSocket Message Types:**

Client → Server:
```python
class WSAgentControlMessage:
    type: "agent_control"
    action: "start" | "stop" | "resume" | "send_instruction"
    data: dict[str, Any]
```

Server → Client:
```python
class WSInterruptMessage:
    type: "interrupt"
    interrupt_id: str
    data: dict[str, Any]
    message: str

class WSAgentStatusMessage:
    type: "agent_status"
    status: "thinking" | "awaiting_input" | "executing_tool" | "complete"
    progress: float  # 0.0 to 1.0
    current_step: str
```

**Modified AgentService Methods:**
- `chat_stream_with_agent_mode()`: New method supporting agent mode
- `handle_interrupt()`: Process interrupt and pause execution
- `resume_from_interrupt()`: Continue with user feedback
- `send_intermediate_instruction()`: Inject new message during execution

**Checkpointer Enhancement:**
- Switch from MemorySaver to PostgreSQL checkpointer
- Enables persistent interrupt state across server restarts
- Supports long-running agent workflows

### 4.2 Frontend Changes

**New UI Components:**
- `AgentModeToggle`: Switch between chat and agent modes
- `AgentControlPanel`: Stop, resume, send instruction buttons
- `InterruptApprovalModal`: Display interrupt and collect user response
- `AgentStatusIndicator`: Show current agent status and progress

**Enhanced useStreamingChat Hook:**
```typescript
interface UseStreamingChatConfig {
  agentMode?: boolean;
  onInterrupt?: (interrupt: WSInterruptMessage) => void;
  onAgentStatus?: (status: WSAgentStatusMessage) => void;
}

interface UseStreamingChatReturn {
  stopAgent: () => void;
  resumeAgent: (response?: Record<string, unknown>) => void;
  sendInstruction: (instruction: string) => void;
}
```

**New Agent State Management:**
```typescript
interface AgentExecutionState {
  mode: 'chat' | 'agent';
  status: 'idle' | 'thinking' | 'awaiting_input' | 'executing' | 'paused' | 'complete' | 'error';
  progress: number;
  currentStep: string;
  pendingInterrupt: InterruptData | null;
  canStop: boolean;
  canResume: boolean;
  canSendInstruction: boolean;
}
```

### 4.3 Database Schema Changes

**New table: `ai_agent_executions`**
```sql
CREATE TABLE ai_agent_executions (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES ai_conversation_sessions(id),
    thread_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL, -- 'running', 'paused', 'completed', 'failed'
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    tool_calls_count INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    interrupt_data JSONB,
    metadata JSONB
);
```

---

## 5. User Experience Flow

### Agent Mode Workflow

1. **User enables agent mode** via toggle switch
2. **User sends initial request**: "Create a project for automation system X"
3. **Agent begins execution**:
   - Status indicator shows "thinking"
   - Progress bar updates
4. **Agent calls tool**: Status changes to "executing_tool: create_project"
5. **Agent encounters decision point**:
   - Tool triggers interrupt
   - Frontend shows approval modal
   - Status: "awaiting_input"
6. **User reviews and approves** (or modifies parameters):
   - Clicks "Approve" or "Cancel"
   - Can edit parameters before approval
7. **Agent resumes** with user feedback
8. **User sends additional instruction**: "Also add a WBE for station 5"
   - Agent pauses current work
   - Processes new instruction
   - Resumes original task
9. **User stops agent**: Clicks stop button
   - Agent gracefully stops after current tool completes
   - State saved for potential resume
10. **Agent completes**: Final summary displayed
    - Browser notification sent
    - Full execution log available

---

## 6. Implementation Breakdown

### Phase 1: Backend Foundation (Backend - 5 points)

| Task | Description |
|------|-------------|
| Enhanced Agent State | Add agent_mode, human_approval_required, interrupt_data fields |
| Human Input Node | Create node that pauses for human feedback |
| Conditional Routing | Add routing logic for interrupt handling |
| PostgreSQL Checkpointer | Replace MemorySaver with persistent checkpointer |
| Database Migration | Create ai_agent_executions table |

### Phase 2: WebSocket Protocol (Backend - 3 points)

| Task | Description |
|------|-------------|
| Agent Control Message | Handle start/stop/resume/send_instruction actions |
| Interrupt Message | Send interrupt data to frontend |
| Agent Status Message | Stream status updates and progress |
| Resume Handler | Implement Command(resume=...) handling |
| Instruction Injection | Support mid-execution message injection |

### Phase 3: Agent Mode Logic (Backend - 4 points)

| Task | Description |
|------|-------------|
| chat_stream_with_agent_mode() | New method with agent mode support |
| Interrupt Handling | Process interrupts and save state |
| Resume from Interrupt | Continue execution with user feedback |
| Progress Events | Emit custom progress events via get_stream_writer() |
| Stop/Resume Logic | Graceful stop with state persistence |

### Phase 4: Frontend UI (Frontend - 4 points)

| Task | Description |
|------|-------------|
| Agent Mode Toggle | Toggle switch component |
| Agent Control Panel | Stop/resume/send instruction buttons |
| Agent Status Indicator | Status display with progress bar |
| Enhanced useStreamingChat | Add agent control methods |
| Agent State Management | Zustand store for agent execution state |

### Phase 5: Interrupt Handling (Frontend - 3 points)

| Task | Description |
|------|-------------|
| Interrupt Approval Modal | Display interrupt and collect response |
| WebSocket Message Handling | Handle new message types |
| Parameter Editing UI | Allow modification of parameters before approval |
| Notification System | Browser notifications for completion |

### Phase 6: Testing & Documentation (3 points)

| Task | Description |
|------|-------------|
| Unit Tests | Test graph nodes, interrupt handling, state management |
| Integration Tests | End-to-end agent mode workflows |
| Documentation | User guide, API documentation |

---

## 7. Security & RBAC Considerations

1. **Permission Checks**: Agent mode requires specific permission
2. **Tool Validation**: All tool calls still go through RBAC
3. **Audit Trail**: All agent actions logged with user context
4. **Cost Controls**: Max iterations, token limits, timeout
5. **Interrupt Security**: Validate interrupt responses before resuming

---

## 8. Performance Considerations

1. **Checkpointer**: PostgreSQL for production (MemorySaver for dev)
2. **State Size**: Limit message history to prevent bloat
3. **Concurrent Agents**: Thread isolation per user/session
4. **Cleanup**: Automatic state cleanup after completion
5. **WebSocket Reconnect**: Reconnect with existing thread_id

---

## 9. Edge Cases & Mitigations

| Edge Case | Mitigation |
|-----------|------------|
| WebSocket Disconnect | Reconnect with existing thread_id |
| Server Restart | State persisted in PostgreSQL checkpointer |
| Tool Failure | Agent recovers or requests human help |
| Max Iterations | Graceful completion with status |
| User Never Approves | Timeout and graceful shutdown |

---

## 10. Success Criteria

### Must Have (MVP)
- [ ] User can toggle agent mode on/off
- [ ] Agent autonomously executes tool calls
- [ ] User can stop agent execution at any time
- [ ] User can resume paused agent execution
- [ ] User can send instructions during execution
- [ ] User receives notifications on completion
- [ ] Agent pauses for human approval when needed
- [ ] Progress updates displayed in real-time
- [ ] Full execution log available for review
- [ ] RBAC enforced throughout
- [ ] All unit tests pass
- [ ] MyPy and Ruff checks pass

### Quality Gates
- 80%+ test coverage for new code
- Zero MyPy errors
- Zero Ruff errors
- All integration tests passing

---

## 11. Technical Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex state management | High | Use LangGraph's built-in checkpointing |
| WebSocket reliability | High | Reconnection logic with thread_id |
| Long-running operations | Medium | Timeouts, max iterations, graceful degradation |
| UI complexity | Medium | Progressive disclosure, clear status indicators |
| Testing difficulty | Medium | Unit tests for graph, integration tests for flow |
| PostgreSQL checkpointer complexity | Low | Follow LangGraph documentation patterns |

---

## 12. Questions for User Feedback

### Pending Decisions

1. **Default Agent Mode**: Should agent mode be opt-in or opt-out?
   - Recommendation: Opt-in (toggle off by default)

2. **Approval Triggers**: Which actions should require human approval?
   - All write operations (create, update, delete)
   - Only high-impact operations (delete, large changes)
   - User-configurable per assistant

3. **Notification Method**: How should completion notifications work?
   - Browser notifications (requires permission)
   - In-app toast notifications
   - Both

4. **State Retention**: How long should agent execution state be retained?
   - 24 hours
   - 7 days
   - Until explicitly cleared

5. **Concurrent Agents**: Should users be able to run multiple agents simultaneously?
   - One per session
   - Multiple with isolation
   - User-configurable limit

---

## 13. References

**Architecture Documentation:**
- [AI/ML Integration Context](../../02-architecture/01-bounded-contexts.md#10-aiml-integration)
- [Functional Requirements: AI Integration](../../01-product-scope/functional-requirements.md#126-ai-integration)

**External References:**
- [LangGraph Documentation - Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Documentation - Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)
- [LangGraph Documentation - Use Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)

**Related Iterations:**
- [2026-03-09-langgraph-agent-enhancement](../2026-03-09-langgraph-agent-enhancement/)
- [2026-03-08-ai-chat-interface](../2026-03-08-ai-chat-interface/)
- [2026-03-08-websocket-streaming](../2026-03-08-websocket-streaming/)

---

## 14. Next Steps

1. **User Approval**: Review this analysis and provide feedback on pending decisions
2. **PLAN Phase**: Create detailed implementation plan with task breakdown
3. **DO Phase**: Implement following TDD methodology
4. **CHECK Phase**: Verify all tests pass, run quality checks
5. **ACT Phase**: Update documentation, create sprint in project plan

---

**Analysis Complete** ✓
