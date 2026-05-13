# Analysis: Fix Parallel Approval Race Condition

**Created:** 2026-05-13
**Request:** Fix two compounding bugs that make multi-tool AI executions unusable: (1) no bulk approval for parallel HIGH-risk tools, and (2) `_consecutive_approval_timeouts` never resets between executions, causing permanent tool blocking after 3 timeouts.

---

## Clarified Requirements

### Functional Requirements

- **FR-1**: When a user approves a HIGH-risk tool, they must be able to opt in to auto-approve all subsequent HIGH-risk tools within the same execution (same InterruptNode lifecycle).
- **FR-2**: The `_consecutive_approval_timeouts` counter on `BackcastSecurityMiddleware` must reset when a new execution starts (i.e., when the InterruptNode identity changes), preventing permanent blocking across executions.
- **FR-3**: The auto-approve flag must apply across all subagents sharing the same InterruptNode via `get_request_interrupt_node()`.
- **FR-4**: A user rejection must NOT cancel the auto-approve flag. Rejection is a one-time override for the specific tool; the flag persists for the remainder of the execution.
- **FR-5**: The approval dialog must display an "Auto-approve remaining tools" checkbox. When checked and the user clicks Approve, the backend sets the flag.
- **FR-6**: The flag must reset naturally when the InterruptNode is discarded at execution end. No manual cleanup required.

### Non-Functional Requirements

- **NFR-1**: Backward compatible. `auto_approve_remaining` defaults to `False` in all schemas (Pydantic and TypeScript). Old clients continue working identically.
- **NFR-2**: All existing approval-related tests must continue passing without modification to their assertions.
- **NFR-3**: Auto-approved tools must produce a distinct log line (`AUTO_APPROVE: ...`) for audit trail visibility.

### Constraints

- **C-1**: The `InterruptNode` is per-execution, shared across subagents via ContextVar (`get_request_interrupt_node()`). The flag must live on this shared instance.
- **C-2**: The `BackcastSecurityMiddleware` is per-subagent, created once and cached in compiled graphs. State that should be per-execution must not accumulate across executions on this instance.
- **C-3**: The `_approval_semaphore` serializes approval requests to one-at-a-time. Auto-approved tools must skip this semaphore entirely to avoid serialization overhead.
- **C-4**: The WS protocol is bidirectional JSON. The `auto_approve_remaining` field must be added to the existing `WSApprovalResponseMessage` (client->server) and optionally acknowledged server-side.

---

## Context Discovery

### Architecture Context

- **Bounded contexts involved**: AI Chat (agent execution, approval workflow)
- **Key shared infrastructure**: `InterruptNode` (per-execution, shared via ContextVar), `BackcastSecurityMiddleware` (per-subagent, cached in compiled graph), `AgentService._interrupt_nodes` dict (session_id -> InterruptNode)
- **WS protocol**: Server sends `WSApprovalRequestMessage`; client responds with `WSApprovalResponseMessage`; server polls via `_poll_for_approval()` with `_approval_semaphore` serialization

### Codebase Analysis

**Backend:**

| File | Role | Current State |
|------|------|---------------|
| `backend/app/ai/tools/interrupt_node.py` | Per-execution approval state | No `auto_approve_remaining` attribute. `register_approval_response()` only takes `approval_id` and `approved`. |
| `backend/app/ai/middleware/backcast_security.py` | Per-subagent risk/approval check | `_consecutive_approval_timeouts` is an instance attribute that never resets. No execution-boundary detection. |
| `backend/app/models/schemas/ai.py` | WS message schemas | `ApprovalRequest` (line 298) and `WSApprovalResponseMessage` (line 774) lack `auto_approve_remaining` field. |
| `backend/app/api/routes/ai_chat.py` | WS + REST handlers | WS handler (line 749) passes `approval_id` and `approved` to `agent_service.register_approval_response()`. REST handler (line 516) calls `interrupt_node.register_approval_response()` directly. Neither passes `auto_approve_remaining`. |
| `backend/app/ai/agent_service.py` | Agent orchestration | `register_approval_response()` (line 2409) takes `session_id`, `approval_id`, `approved`. No `auto_approve_remaining` parameter. |
| `backend/app/ai/graph_cache.py` | ContextVar helpers for per-request context | `get_request_interrupt_node()` returns the shared InterruptNode. Already supports the cross-subagent sharing pattern needed. |

**Frontend:**

| File | Role | Current State |
|------|------|---------------|
| `frontend/src/features/ai/chat/types.ts` (line 503) | TS interface for WS messages | `WSApprovalResponseMessage` lacks `auto_approve_remaining` field. |
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` (line 875) | WS send function | `sendApprovalResponse(approvalId, approved)` takes 2 params. No `autoApproveRemaining` param. |
| `frontend/src/features/ai/components/ApprovalDialog.tsx` | Approval modal | `onApprove: () => void` takes no args. No checkbox UI. |
| `frontend/src/features/ai/chat/components/ChatInterface.tsx` (line 929) | Approval handler | `handleApproval(approved: boolean)` calls `sendApprovalResponse(approval_id, approved)`. No auto-approve param threading. |

**Existing tests that must remain passing:**

- `backend/tests/ai/tools/test_interrupt_node_approval.py` -- LOW/HIGH/CRITICAL risk approval behavior
- `backend/tests/integration/ai/test_approval_workflow.py` -- T-007 through T-009, T-015/T-016
- `backend/tests/integration/ai/test_agent_service_approval_integration.py` -- AgentService approval registration
- `frontend/src/features/ai/components/__tests__/ApprovalDialog.test.tsx` -- Dialog rendering and button behavior

---

## Solution Options

### Option 1: Auto-Approve Remaining Flag on InterruptNode (Approved Plan)

**Architecture & Design:**

Add `auto_approve_remaining: bool` to `InterruptNode`. When set, the `BackcastSecurityMiddleware._check_risk_level_with_approval()` short-circuits: skips `_approval_semaphore`, skips `_poll_for_approval()`, resets timeout counter, returns `(True, None)` immediately.

Separately, fix the timeout counter by detecting InterruptNode identity changes at the top of `_check_risk_level_with_approval()`: store `_last_seen_interrupt_node` and reset `_consecutive_approval_timeouts = 0` when the reference changes.

The flag propagates through the full stack: ApprovalDialog checkbox -> ChatInterface handler -> useStreamingChat.sendApprovalResponse -> WS message -> ai_chat.py WS handler -> AgentService.register_approval_response -> InterruptNode.register_approval_response.

**UX Design:**

The approval dialog gains a Checkbox component (from antd) labeled "Auto-approve remaining tools in this execution". It appears between the tool details (Descriptions) and the bottom info Alert. The checkbox state is internal to the dialog, reset on each open. When the user clicks Approve, the checkbox value is forwarded.

**Implementation:**

9 files to modify as specified in the plan. The changes are additive: new attributes, new parameters with defaults, early-return guard clause, one new UI element.

**Trade-offs:**

| Aspect          | Assessment                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------- |
| Pros            | Minimal surface area -- flag is a single boolean on the per-execution object. Naturally scoped. Backward compatible via defaults. Cross-subagent by design (shared InterruptNode). |
| Cons            | The "reject does not cancel auto-approve" behavior may surprise some users, though the rationale (avoid repeated checkbox-clicking) is sound. |
| Complexity      | Low. The core logic is an early-return guard clause in `_check_risk_level_with_approval()`. The rest is plumbing through schemas and handlers. |
| Maintainability | Good. The flag lives on InterruptNode which is already the approval authority. No new infrastructure needed. |
| Performance     | Significant improvement for batched operations. Auto-approved tools skip semaphore acquisition and polling, going directly to execution under `_global_tool_semaphore`. |

---

### Option 2: Bulk-Approve by Tool Name Pattern

**Architecture & Design:**

Instead of a blanket auto-approve flag, allow the user to approve all tools matching the same tool name (e.g., "approve all `create_wbe` calls"). Store a `Set[str]` of auto-approved tool names on the InterruptNode.

**UX Design:**

The approval dialog shows "Approve all remaining `create_wbe` calls" checkbox instead of a blanket "Auto-approve remaining tools". This gives finer control.

**Implementation:**

Similar plumbing to Option 1, but the InterruptNode stores `auto_approved_tool_names: set[str]` instead of a single boolean. The middleware checks `tool_name in interrupt_node.auto_approved_tool_names`. Additional set-management logic needed.

**Trade-offs:**

| Aspect          | Assessment                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------- |
| Pros            | Finer granularity. User can auto-approve `create_wbe` while still manually approving `create_cost_element`. |
| Cons            | More complex state management (set of strings vs single boolean). More complex UI (per-tool-name checkbox). Marginal benefit -- in practice, users who auto-approve want ALL remaining tools approved to avoid the timeout cascade. |
| Complexity      | Medium. Set management, per-tool-name UI state, more complex guard clause. |
| Maintainability | Fair. Additional data structure to reason about. |
| Performance     | Same improvement as Option 1 for the auto-approved tools. |

---

### Option 3: Server-Side Batch Approval with Execution Plan

**Architecture & Design:**

When the agent plans multiple tool calls, pre-register all approval requests. Present a single "batch approval" dialog to the user showing all pending tools, with approve-all/reject-all. The backend processes the batch in one shot.

**UX Design:**

A table-based dialog showing all queued tool calls. User can check/uncheck individual ones, then approve the batch.

**Implementation:**

This requires significant changes to the agent execution model: tools must be "planned" before execution, approval requests must be batch-sent, and the polling loop must handle multiple approvals simultaneously. This conflicts with the current one-at-a-time semaphore model.

**Trade-offs:**

| Aspect          | Assessment                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------- |
| Pros            | Maximum user control. Can review all operations upfront. Most transparent approach. |
| Cons            | Requires restructuring the agent execution pipeline (currently tools execute one at a time, interleaved with LLM reasoning). High implementation cost. Breaks the current streaming UX where tools are discovered incrementally. |
| Complexity      | High. Fundamental changes to execution model, approval pipeline, and UI paradigm. |
| Maintainability | Poor. Adds significant new abstractions that must coexist with existing single-approval flow. |
| Performance     | Potentially slower (must collect all tool calls before showing dialog) unless the agent can predict its full plan. |

---

## Comparison Summary

| Criteria           | Option 1 (Flag)       | Option 2 (Tool Pattern) | Option 3 (Batch Plan)  |
| ------------------ | --------------------- | ----------------------- | ---------------------- |
| Development Effort | Low (2-3 hours)       | Medium (4-5 hours)      | High (2-3 days)        |
| UX Quality         | Good                  | Good                    | Best (theoretically)   |
| Flexibility        | Good                  | Better                  | Best                   |
| Risk               | Minimal               | Low                     | High                   |
| Best For           | Quick fix, immediate relief | Selective auto-approval | Full redesign of approval UX |

---

## Recommendation

**I recommend Option 1 because:** It is the minimal fix that addresses both root causes with the smallest blast radius. The `auto_approve_remaining` boolean on `InterruptNode` is a single-attribute addition to an already-per-execution object, which means natural lifecycle management and cross-subagent sharing come for free. The timeout counter fix (detecting InterruptNode identity changes) is a clean, deterministic approach that does not require new infrastructure. The 9-file modification list is well-scoped and every change traces directly to a requirement.

The design is also opinionated in the right direction: in the real E2E scenario that triggered this bug, the user was executing 15 `create_wbe` calls and needed ALL of them approved. Option 2's per-tool-name granularity adds complexity for a use case that, in practice, requires blanket approval. Option 3 is a complete redesign that is out of scope for a bug fix.

**Alternative consideration:** If future user feedback reveals that finer-grained control is needed (e.g., auto-approve read-only tools but not mutating ones), Option 2's tool-name pattern set can be introduced as a backward-compatible evolution of Option 1. The `auto_approve_remaining` boolean can coexist with a future `auto_approved_tool_names` set.

---

## Decision Questions

1. Do you agree that "reject does not cancel auto-approve" is the correct behavior? The alternative is to reset the flag on any rejection, which forces the user to re-check the checkbox for subsequent approvals.
2. Should the "Auto-approve remaining tools" checkbox appear for ALL risk levels, or only for HIGH risk? CRITICAL tools are blocked entirely in STANDARD mode, so the checkbox would be irrelevant for them. LOW tools do not require approval at all.
3. Should the backend log auto-approved tools at `WARNING` level (audit emphasis) or `INFO` level (same as normal approvals)?

---

## Success Criteria

1. **SC-1**: When `auto_approve_remaining=True` is set on an InterruptNode, all subsequent HIGH-risk tools in STANDARD mode execute without approval dialogs, and the backend logs `AUTO_APPROVE: tool='...'` for each.
2. **SC-2**: The `_consecutive_approval_timeouts` counter resets to 0 when a new InterruptNode is detected (new execution), even on a cached middleware instance.
3. **SC-3**: All existing approval-related tests pass without modification: `test_interrupt_node_approval.py`, `test_approval_workflow.py`, `test_agent_service_approval_integration.py`, `ApprovalDialog.test.tsx`.
4. **SC-4**: A new test confirms that after auto-approve is set, a subsequent tool call skips the semaphore and executes immediately.
5. **SC-5**: Backward compatibility: a client that does not send `auto_approve_remaining` in the WS message produces identical behavior to the current system.

---

## References

- Plan file: `/home/nicola/.claude/plans/eventual-beaming-teapot.md`
- `backend/app/ai/tools/interrupt_node.py` -- InterruptNode with approval state
- `backend/app/ai/middleware/backcast_security.py` -- BackcastSecurityMiddleware with timeout counter
- `backend/app/ai/graph_cache.py` -- ContextVar helpers for per-request InterruptNode
- `backend/app/models/schemas/ai.py` -- WS message schemas
- `backend/app/api/routes/ai_chat.py` -- WS and REST approval handlers
- `backend/app/ai/agent_service.py` -- AgentService.register_approval_response()
- `frontend/src/features/ai/components/ApprovalDialog.tsx` -- Approval dialog
- `frontend/src/features/ai/chat/api/useStreamingChat.ts` -- WS send function
- `frontend/src/features/ai/chat/components/ChatInterface.tsx` -- Approval handler
- `frontend/src/features/ai/chat/types.ts` -- TypeScript WS message types
