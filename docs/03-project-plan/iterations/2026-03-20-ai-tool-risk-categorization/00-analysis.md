# Analysis: AI Tool Risk Categorization and Execution Modes

**Created:** 2026-03-20
**Request:** AI Tool Risk Categorization and Execution Modes
**Status:** ANALYSIS COMPLETE - Awaiting User Approval

---

## 1. Clarified Requirements

### 1.1 User Intent

The Backcast AI agent system currently implements Role-Based Access Control (RBAC) for tool permissions but lacks granular safety mechanisms for tool execution. Users want control over AI agent behavior based on risk tolerance, similar to systems like Claude Code and Cursor that provide "safe", "standard", and "expert" execution modes.

**Key Goals:**
1. Categorize tools by risk level (low/high/critical)
2. Allow users to select execution modes that control which tools can run
3. Implement explicit approval workflow for high-risk operations
4. Maintain security while providing flexibility for different user scenarios

### 1.2 Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| FR-1 | Tool Risk Categorization | All AI tools must be tagged with risk_level: low (read operations), high (create/update), critical (delete/security-sensitive) |
| FR-2 | Execution Mode Selection | Users can select execution mode: safe (low-risk only), standard (low+high with approval for critical), expert (all tools without approval) |
| FR-3 | Approval Workflow | Critical-risk tools require explicit user approval before execution in standard mode |
| FR-4 | Mode Persistence | User's selected execution mode persists across chat sessions |
| FR-5 | Visual Indicators | Frontend displays current execution mode and risk level of tools being invoked |
| FR-6 | RBAC Integration | Risk checks work in conjunction with existing RBAC system (both must pass) |
| FR-7 | WebSocket Protocol | New WebSocket message types for approval requests and responses |
| FR-8 | Audit Logging | All tool executions, approvals, and denials logged for security audit |

### 1.3 Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-1 | Performance | Risk checks must add < 10ms overhead to tool execution |
| NFR-2 | Type Safety | Full MyPy strict mode compliance for new code |
| NFR-3 | Test Coverage | 90%+ coverage for risk checking and approval logic |
| NFR-4 | Backward Compatibility | Existing tools without risk_level default to "high" (safe conservative default) |
| NFR-5 | Security | Approval tokens cryptographically signed, timeout after 5 minutes |
| NFR-6 | User Experience | Approval dialogs non-blocking for other chat sessions |

### 1.4 Constraints

| ID | Constraint | Description |
|----|------------|-------------|
| C-1 | Architecture | Must integrate with existing LangGraph StateGraph and RBACToolNode |
| C-2 | Database | No schema changes allowed in this iteration (use metadata annotations) |
| C-3 | Frontend | Use existing WebSocket infrastructure, add new message types |
| C-4 | Time | Implementation must be complete within current sprint (2 weeks) |
| C-5 | Testing | All existing tests must continue passing |

---

## 2. Context Discovery

### 2.1 Product Scope

**Relevant User Stories:**
- AI Chat Interface (US-AI-001): Natural language project queries
- AI Agent Tools (US-AI-002): Tool-based autonomous execution
- Change Order Management (US-CM-001): AI-assisted change order workflows

**Business Requirements:**
- Users need trust in AI agent behavior
- Different user roles have different risk tolerances
- Audit trail required for compliance
- System must prevent accidental data deletion

### 2.2 Architecture Context

**Bounded Contexts Involved:**
- AI Agent Bounded Context: LangGraph orchestration, tool execution
- Security Bounded Context: RBAC, permissions, authorization
- UI Bounded Context: Chat interface, mode selection, approval dialogs

**Existing Patterns to Follow:**
- RBAC Service Pattern (ADR-007): Service-based permission checking
- Tool Metadata Pattern: Tools annotated with metadata via decorator
- WebSocket Message Pattern: Type-safe schemas with discriminated unions
- LangGraph ToolNode Pattern: Custom wrapper for permission injection

**Architectural Constraints:**
- LangGraph StateGraph is the orchestration engine
- RBACToolNode wraps LangGraph's ToolNode for permission checks
- WebSocket is the primary communication protocol for AI chat
- No database migrations allowed (use code annotations)

### 2.3 Codebase Analysis

#### Backend

**Existing Related APIs:**

| File | Purpose | Relevance |
|------|---------|-----------|
| `backend/app/ai/agent_service.py` | LangGraph orchestration | Main entry point, needs execution mode handling |
| `backend/app/ai/graph.py` | StateGraph construction | Needs risk-aware routing |
| `backend/app/ai/tools/rbac_tool_node.py` | Permission checking | Extends for risk checking |
| `backend/app/ai/tools/types.py` | Tool metadata | ToolMetadata needs risk_level field |
| `backend/app/ai/tools/__init__.py` | Tool registry | Tool discovery and filtering |
| `backend/app/models/schemas/ai.py` | Pydantic schemas | WSChatRequest needs execution_mode field |
| `backend/app/core/rbac.py` | RBAC service | Reference pattern for risk service |

**Data Models:**

```python
# Current ToolMetadata (backend/app/ai/tools/types.py)
@dataclass
class ToolMetadata:
    name: str
    description: str
    permissions: list[str]
    category: str | None = None
    version: str = "1.0.0"
    # MISSING: risk_level field

# Current WSChatRequest (backend/app/models/schemas/ai.py)
class WSChatRequest(BaseModel):
    type: str = "chat"
    message: str
    session_id: UUID | None
    assistant_config_id: UUID | None
    title: str | None
    project_id: UUID | None
    branch_id: UUID | None
    # MISSING: execution_mode field
```

**Similar Patterns:**

1. **RBACToolNode Permission Check** (`rbac_tool_node.py:56-95`):
   - Reads tool metadata for permissions
   - Checks permissions via RBACService
   - Returns error message if denied
   - **Pattern to follow:** Add risk check alongside permission check

2. **Tool Decorator Pattern** (observed in tool templates):
   - Tools decorated with `@ai_tool`
   - Metadata attached to function
   - **Pattern to follow:** Add risk_level parameter to decorator

3. **WebSocket Message Flow** (`agent_service.py:460-585`):
   - Streams events via astream_events
   - Sends token, tool_call, tool_result, complete, error messages
   - **Pattern to follow:** Add approval_request, approval_response messages

**Technical Debt/Limitations:**
- No audit logging for tool executions
- Tool metadata not centralized (scattered across template files)
- No user preference storage for execution mode
- WebSocket protocol lacks approval flow

#### Frontend

**Comparable Components:**

| File | Purpose | Relevance |
|------|---------|-----------|
| `frontend/src/features/ai/components/AIAssistantModal.tsx` | Chat UI | Needs mode selector and approval dialog |
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` | WebSocket hook | Handle new approval message types |
| `frontend/src/pages/admin/AIAssistantManagement.tsx` | Admin UI | Reference for mode configuration UI |

**State Management:**
- React hooks (useState, useEffect) for component state
- TanStack Query for server state
- WebSocket hooks for real-time communication
- **Approach:** Add execution mode to user preferences (localStorage or backend)

**Routing Structure:**
- Single-page application with modal-based chat
- No routing changes required
- WebSocket connection managed in hook

**Similar UI Patterns:**
- AIAssistantModal has assistant config selector
- Can add execution mode selector alongside
- Approval dialog similar to existing confirmation dialogs

---

## 3. Solution Options

### Option 1: LangGraph Interrupt-Based Human-in-the-Loop

**Architecture & Design:**

Leverages LangGraph's built-in `interrupt()` mechanism for pausing execution and requesting human input. Risk checking happens at tool invocation, and critical tools pause execution for approval.

**Components:**
1. **ToolMetadata Extension**: Add `risk_level: Literal["low", "high", "critical"]` field
2. **LangGraph Interrupt Node**: New node that pauses graph before critical tools
3. **WebSocket Approval Protocol**: `approval_request` and `approval_response` messages
4. **Frontend Approval Dialog**: Modal for user to approve/reject critical operations
5. **Execution Mode State**: Managed in ToolContext, filtered tools based on mode

**Data Flow:**
```
User Message (with execution_mode)
    ↓
LangGraph Agent Node
    ↓
RBACToolNode (checks permissions)
    ↓
Risk Check (before critical tools)
    ↓
IF safe/standard mode AND critical tool:
    interrupt() → Send approval_request via WebSocket
    ↓
User approves via frontend
    ↓
graph.invoke(resume_command)
    ↓
Tool executes
```

**UX Design:**

- **Mode Selector**: Dropdown in AIAssistantModal header (Safe/Standard/Expert)
- **Visual Indicators**: Badge showing current mode, color-coded (green/orange/red)
- **Tool Execution Notification**: Toast showing tool name and risk level
- **Approval Dialog**: Non-blocking modal with:
  - Tool name and description
  - Risk level badge
  - Arguments preview
  - Approve/Reject buttons
  - "Don't ask again for this session" checkbox

**Implementation:**

**Backend Changes:**

| File | Changes | Lines |
|------|---------|-------|
| `backend/app/ai/tools/types.py` | Add risk_level to ToolMetadata, RiskLevel enum | +20 |
| `backend/app/ai/tools/rbac_tool_node.py` | Add risk checking, interrupt for critical tools | +80 |
| `backend/app/ai/graph.py` | Add interrupt handler node, conditional edge | +60 |
| `backend/app/ai/agent_service.py` | Handle approval in chat_stream, pass execution_mode | +100 |
| `backend/app/models/schemas/ai.py` | Add execution_mode to WSChatRequest, new WS message types | +50 |
| `backend/app/api/routes/ai_chat.py` | Pass execution_mode from request to service | +20 |
| `backend/app/ai/tools/templates/*.py` | Add risk_level to all tool decorators | +100 (distributed) |

**Frontend Changes:**

| File | Changes | Lines |
|------|---------|-------|
| `frontend/src/features/ai/components/AIAssistantModal.tsx` | Add mode selector, approval dialog, visual indicators | +200 |
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` | Handle approval message types, approval callbacks | +80 |
| `frontend/src/features/ai/chat/types.ts` | Add approval message schemas | +40 |

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | - Native LangGraph pattern<br>- Clean separation of concerns<br>- Leverages existing interrupt mechanism<br>- Non-blocking (other chats continue)<br>- Strong type safety |
| **Cons** | - More complex implementation<br>- Requires LangGraph state management<br>- Approval dialog non-blocking may confuse users<br>- More WebSocket message types |
| **Complexity** | High (interrupt handling, state resume) |
| **Maintainability** | Good (follows LangGraph patterns) |
| **Performance** | Excellent (< 5ms overhead for risk check) |
| **User Experience** | Good (explicit approvals, visual feedback) |

---

### Option 2: Pre-Execution Tool Filtering + Simple Approval

**Architecture & Design:**

Filters tools before binding to LLM based on execution mode. Critical tools removed from tool list in safe mode, included but marked for approval in standard mode. Approval handled via simple WebSocket request/response before tool execution.

**Components:**
1. **ToolMetadata Extension**: Add `risk_level` field
2. **Tool Filtering Service**: Filters tools based on mode before LLM binding
3. **Simple Approval Check**: Synchronous check in RBACToolNode before execution
4. **WebSocket Protocol**: Single `approval_required` message with wait for response
5. **Frontend Mode Selector**: Simple dropdown in chat interface

**Data Flow:**
```
User Message (with execution_mode)
    ↓
AgentService.chat_stream()
    ↓
Filter tools based on execution_mode
    ↓
Bind filtered tools to LLM
    ↓
LangGraph Agent Node
    ↓
RBACToolNode (permissions + risk check)
    ↓
IF critical tool in standard mode:
    Send approval_required via WebSocket
    WAIT for user response (blocking)
    ↓
IF approved: Execute tool
ELSE: Skip tool, return error
```

**UX Design:**

- **Mode Selector**: Simple dropdown in AIAssistantModal
- **Visual Indicators**: Mode badge, tool risk indicators in message history
- **Approval Dialog**: Blocking modal (user must respond to continue)
- **Mode Explanations**: Tooltip showing which tools allowed in each mode

**Implementation:**

**Backend Changes:**

| File | Changes | Lines |
|------|---------|-------|
| `backend/app/ai/tools/types.py` | Add risk_level, ExecutionMode enum | +25 |
| `backend/app/ai/tools/__init__.py` | Add filter_tools_by_mode() function | +40 |
| `backend/app/ai/tools/rbac_tool_node.py` | Add risk check, approval wait logic | +60 |
| `backend/app/ai/agent_service.py` | Filter tools, handle approval responses | +80 |
| `backend/app/models/schemas/ai.py` | Add execution_mode, approval messages | +45 |
| `backend/app/api/routes/ai_chat.py` | Pass execution_mode | +15 |
| `backend/app/ai/tools/templates/*.py` | Add risk_level to all tools | +100 |

**Frontend Changes:**

| File | Changes | Lines |
|------|---------|-------|
| `frontend/src/features/ai/components/AIAssistantModal.tsx` | Mode selector, blocking approval dialog | +150 |
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` | Handle approval messages, wait for response | +60 |
| `frontend/src/features/ai/chat/types.ts` | Approval schemas | +30 |

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | - Simpler implementation (no interrupts)<br>- Easier to understand and debug<br>- Fewer WebSocket message types<br>- Faster to implement |
| **Cons** | - Blocking approval (user must respond)<br>- Can't filter tools dynamically per request<br>- LLM can't see critical tools in safe mode<br>- Less flexible for future enhancements |
| **Complexity** | Medium (filtering + blocking approval) |
| **Maintainability** | Good (simpler code) |
| **Performance** | Good (< 10ms overhead, but blocks on approval) |
| **User Experience** | Fair (blocking approval may frustrate users) |

---

### Option 3: Hybrid Approach with Tool-Level Execution Modes

**Architecture & Design:**

Combines pre-execution filtering with a new "ToolExecutor" layer that wraps tool execution with risk-aware logic. Each tool invocation checks execution mode and risk level, with critical tools requiring approval in standard mode. Uses a callback-based approval system that integrates with existing WebSocket flow.

**Components:**
1. **ToolMetadata Extension**: Add `risk_level` and `execution_modes` (which modes allow this tool)
2. **ToolExecutor Class**: Wraps tool execution with risk checks and approval workflow
3. **Approval Service**: Manages pending approvals, timeouts, audit logging
4. **Enhanced RBACToolNode**: Uses ToolExecutor for all tool calls
5. **Frontend Approval Manager**: Manages approval UI state across multiple chats

**Data Flow:**
```
User Message (with execution_mode)
    ↓
AgentService.chat_stream()
    ↓
Create ToolExecutor with execution_mode
    ↓
Bind tools to LLM (all tools visible)
    ↓
LangGraph Agent Node
    ↓
RBACToolNode → ToolExecutor
    ↓
Check: tool.execution_modes.contains(current_mode)
    ↓
IF not allowed: Skip tool, return error
IF requires approval:
    Register approval in ApprovalService
    Send approval_request via WebSocket (non-blocking)
    ↓
Continue graph execution (tool pending)
    ↓
On approval response: Execute tool
On timeout/reject: Return error
```

**UX Design:**

- **Mode Selector**: Enhanced dropdown with descriptions
- **Visual Indicators**: Mode badge, tool risk icons, pending approval counter
- **Approval Dialog**: Non-blocking toast notification with approve/reject
- **Approval Manager**: Sidebar showing pending approvals across all sessions
- **Mode Configuration**: User can customize which tools require approval per mode

**Implementation:**

**Backend Changes:**

| File | Changes | Lines |
|------|---------|-------|
| `backend/app/ai/tools/types.py` | Add risk_level, execution_modes to ToolMetadata | +30 |
| `backend/app/ai/tools/tool_executor.py` | New ToolExecutor class with approval workflow | +150 |
| `backend/app/ai/tools/approval_service.py` | New ApprovalService for managing pending approvals | +120 |
| `backend/app/ai/tools/rbac_tool_node.py` | Integrate ToolExecutor | +40 |
| `backend/app/ai/agent_service.py` | Pass execution_mode, handle approval callbacks | +90 |
| `backend/app/models/schemas/ai.py` | Add approval messages, execution_mode | +55 |
| `backend/app/api/routes/ai_chat.py` | Approval response endpoint | +30 |
| `backend/app/ai/tools/templates/*.py` | Add risk_level, execution_modes | +120 |

**Frontend Changes:**

| File | Changes | Lines |
|------|---------|-------|
| `frontend/src/features/ai/components/AIAssistantModal.tsx` | Mode selector, approval toasts, pending approvals sidebar | +250 |
| `frontend/src/features/ai/components/ApprovalManager.tsx` | New component for managing approvals | +150 |
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` | Handle approval messages, callbacks | +90 |
| `frontend/src/features/ai/chat/types.ts` | Approval schemas, approval state | +50 |

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | - Most flexible and powerful<br>- Non-blocking approvals<br>- Centralized approval management<br>- Audit logging built-in<br>- Future-proof (extensible to group approvals) |
| **Cons** | - Highest complexity (3 new classes)<br>- More code to maintain<br>- Longer implementation time<br>- Over-engineering for current needs |
| **Complexity** | High (new service, executor, manager) |
| **Maintainability** | Fair (more moving parts) |
| **Performance** | Good (non-blocking, < 8ms overhead) |
| **User Experience** | Excellent (rich approval management) |

---

## 4. Comparison Summary

| Criteria | Option 1: LangGraph Interrupts | Option 2: Filtering + Blocking | Option 3: Hybrid + ToolExecutor |
|----------|-------------------------------|-------------------------------|--------------------------------|
| **Development Effort** | 530 lines backend, 320 lines frontend | 360 lines backend, 240 lines frontend | 635 lines backend, 540 lines frontend |
| **Implementation Time** | 5-7 days | 3-4 days | 7-10 days |
| **UX Quality** | Good (explicit approvals) | Fair (blocking) | Excellent (rich management) |
| **Flexibility** | High (native LangGraph) | Low (pre-filtered) | Very High (customizable) |
| **Complexity** | High (interrupt handling) | Medium (filtering) | High (new architecture) |
| **Maintainability** | Good (follows patterns) | Good (simple) | Fair (more parts) |
| **Performance** | Excellent (< 5ms) | Good (< 10ms, blocking) | Good (< 8ms) |
| **Best For** | Production-grade, scalable | Quick win, MVP | Enterprise, multi-user |

---

## 5. Recommendation

### I Recommend Option 1: LangGraph Interrupt-Based Human-in-the-Loop

**Rationale:**

1. **Aligns with LangGraph Best Practices**: Uses native `interrupt()` mechanism designed for human-in-the-loop workflows, ensuring compatibility with future LangGraph updates.

2. **Non-Blocking UX**: Approval requests don't block other chat sessions, allowing users to continue working while reviewing critical actions.

3. **Clean Architecture**: Separates concerns clearly - RBACToolNode handles permissions, RiskCheckNode handles risk, InterruptNode handles approvals. Each component has a single responsibility.

4. **Scalable**: Can easily extend to group approvals, timeout handling, and audit logging without major refactoring.

5. **Type Safety**: Leverages LangGraph's typed state and Command objects, maintaining strict type safety throughout.

6. **Future-Proof**: Sets foundation for advanced features like:
   - Conditional approval chains (approve all related changes)
   - Approval delegation (ask another user)
   - Approval policies (auto-approve based on risk score)

### Alternative Consideration:

**Choose Option 2 if:**
- Time constraints are critical (need quick win in 3-4 days)
- Team is less familiar with LangGraph internals
- Simpler blocking approval is acceptable for current use cases
- Don't need multi-user concurrent chat support

**Choose Option 3 if:**
- Building enterprise-grade multi-user system
- Need complex approval workflows (group approvals, delegation)
- Have 7-10 days for implementation
- Want centralized approval management across all AI features

---

## 6. Decision Questions

1. **Time Constraints**: Do you need this implemented quickly (3-4 days) or can we allocate 5-7 days for a more robust solution?

2. **Blocking vs Non-Blocking**: Is it acceptable for approval requests to block the current chat until user responds, or should other chats continue working?

3. **Future Enhancements**: Do you plan to add features like group approvals, approval delegation, or approval policies in the next 6 months?

4. **Team Familiarity**: How comfortable is the team with LangGraph internals (interrupts, state management, Command objects)?

5. **Multi-User Support**: Do multiple users need to chat simultaneously with their own approval workflows?

---

## 7. Implementation Preview (Option 1)

### Phase 1: Backend Foundation (Days 1-2)

1. Extend ToolMetadata with risk_level
2. Add ExecutionMode enum and validation
3. Update @ai_tool decorator with risk_level parameter
4. Annotate all existing tools with appropriate risk levels
5. Add unit tests for risk categorization

### Phase 2: Risk Checking (Days 2-3)

1. Create RiskCheckNode for LangGraph
2. Integrate risk check into RBACToolNode
3. Add execution_mode to ToolContext
4. Filter tools based on mode in safe/standard
5. Add integration tests

### Phase 3: Approval Workflow (Days 3-4)

1. Create InterruptNode with LangGraph interrupts
2. Add WebSocket approval message types
3. Implement approval handling in AgentService
4. Add approval timeout and audit logging
5. Add end-to-end tests

### Phase 4: Frontend Implementation (Days 4-5)

1. Add execution mode selector to AIAssistantModal
2. Create approval dialog component
3. Handle approval WebSocket messages
4. Add visual indicators for mode and tool risk
5. Add E2E tests with Playwright

### Phase 5: Documentation & Polish (Days 6-7)

1. Update API documentation
2. Add user guide for execution modes
3. Performance testing and optimization
4. Code review and refinement
5. Deploy to staging for QA

---

## 8. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **LangGraph interrupt complexity** | High | Prototype interrupt flow first, validate with simple test case |
| **WebSocket approval race conditions** | Medium | Use unique approval IDs, timeout handling, idempotent responses |
| **Tool annotation errors** | Medium | Automated linting rule to check risk_level on all @ai_tool decorators |
| **User confusion about modes** | Low | Clear tooltips, mode descriptions, and onboarding flow |
| **Performance degradation** | Low | Benchmark risk check overhead, optimize if > 10ms |
| **Breaking existing chats** | Medium | Backward compatible: tools without risk_level default to "high" |

---

## 9. References

### Architecture Documentation
- [ADR-007: RBAC Service Design](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-007-rbac-service.md)
- [AI Agent Architecture](/home/nicola/dev/backcast/docs/02-architecture/01-bounded-contexts.md)
- [Backend Coding Standards](/home/nicola/dev/backcast/docs/02-architecture/backend/coding-standards.md)

### Code References
- [RBACToolNode Implementation](/home/nicola/dev/backcast/backend/app/ai/tools/rbac_tool_node.py)
- [AgentService Chat Flow](/home/nicola/dev/backcast/backend/app/ai/agent_service.py)
- [LangGraph StateGraph Construction](/home/nicola/dev/backcast/backend/app/ai/graph.py)
- [Tool Metadata Types](/home/nicola/dev/backcast/backend/app/ai/tools/types.py)
- [WebSocket Schemas](/home/nicola/dev/backcast/backend/app/models/schemas/ai.py)

### External Resources
- [LangGraph Human-in-the-Loop Documentation](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [LangGraph Interrupt Reference](https://langchain-ai.github.io/langgraph/reference/#langgraph.types.interrupt)
- [Claude Code Safety Patterns](https://code.anthropic.com/docs/safety)

---

## 10. Next Steps

Upon user approval of Option 1:

1. Create detailed PLAN document (`01-plan.md`) with:
   - Detailed technical design
   - Database schema changes (if any)
   - API contract specifications
   - Test strategy
   - Deployment plan

2. Begin implementation following PDCA cycle:
   - DO: Implement according to plan
   - CHECK: Verify against requirements
   - ACT: Refine based on feedback

3. Daily standups to track progress and blockages

---

**Awaiting User Decision**: Please review the three options and decision questions, then indicate which approach you'd like to proceed with.
