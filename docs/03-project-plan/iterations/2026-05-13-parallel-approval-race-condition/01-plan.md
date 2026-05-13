# Plan: Fix Parallel Approval Race Condition

**Created:** 2026-05-13
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 -- Auto-Approve Remaining Flag on InterruptNode

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 from analysis -- Add `auto_approve_remaining: bool` flag to `InterruptNode` that short-circuits the approval polling loop for all subsequent HIGH-risk tools in the same execution.
- **Architecture**: Single boolean attribute on the per-execution `InterruptNode`, shared across subagents via `get_request_interrupt_node()`. Guard clause in `BackcastSecurityMiddleware._check_risk_level_with_approval()` returns `(True, None)` when flag is set, skipping semaphore and polling entirely. The flag propagates through: ApprovalDialog checkbox -> ChatInterface handler -> useStreamingChat.sendApprovalResponse -> WS message -> ai_chat.py handlers -> AgentService -> InterruptNode.
- **Key Decisions**:
  1. Reject does NOT cancel auto-approve flag (per CHECK phase decision)
  2. Checkbox appears only for HIGH risk level in STANDARD mode
  3. Auto-approved tools log at INFO level (not WARNING)
  4. Flag resets naturally when InterruptNode is discarded at execution end

### Success Criteria

**Functional Criteria:**

- [ ] SC-1: When `auto_approve_remaining=True` is set on an InterruptNode, all subsequent HIGH-risk tools in STANDARD mode execute without approval dialogs, and the backend logs `AUTO_APPROVE: tool='...' auto-approved (auto_approve_remaining=True)` at INFO level. VERIFIED BY: unit test + manual verification
- [ ] SC-2: The `_consecutive_approval_timeouts` counter resets to 0 when a new InterruptNode is detected (new execution), even on a cached middleware instance. VERIFIED BY: unit test
- [ ] SC-3: All existing approval-related tests pass without modification to their assertions. VERIFIED BY: test suite
- [ ] SC-4: A new test confirms that after auto-approve is set, a subsequent tool call skips the semaphore and executes immediately. VERIFIED BY: unit test
- [ ] SC-5: Backward compatibility: a client that does not send `auto_approve_remaining` in the WS message produces identical behavior to the current system. VERIFIED BY: integration test + manual verification

**Technical Criteria:**

- [ ] Code Quality: MyPy strict mode zero errors, Ruff zero errors. VERIFIED BY: `uv run ruff check . && uv run mypy app/`
- [ ] Test coverage >= 80% on modified files. VERIFIED BY: `uv run pytest --cov=app/ai/tools/interrupt_node.py --cov=app/ai/middleware/backcast_security.py`

**Business Criteria:**

- [ ] A prompt triggering 15 HIGH-risk tool calls completes within normal execution time (no timeout cascade) when auto-approve is used. VERIFIED BY: manual verification

### Scope Boundaries

**In Scope:**

- Backend: `InterruptNode` attribute + `register_approval_response` enhancement
- Backend: `BackcastSecurityMiddleware` guard clause + timeout counter fix
- Backend: Pydantic schema additions (`ApprovalRequest`, `WSApprovalResponseMessage`)
- Backend: Route handler threading (WS + REST)
- Backend: `AgentService.register_approval_response` parameter plumbing
- Frontend: TypeScript type addition
- Frontend: `sendApprovalResponse` parameter threading
- Frontend: `ApprovalDialog` checkbox UI
- Frontend: `ChatInterface` handler wiring
- Tests: unit tests for new behavior

**Out of Scope:**

- Per-tool-name selective auto-approve (Option 2 from analysis)
- Batch approval UI (Option 3 from analysis)
- Migration or database schema changes
- Changes to CRITICAL risk level behavior (already blocked in STANDARD mode)
- Changes to LOW risk level behavior (already auto-approved)
- Subagent-specific auto-approve scoping

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 1 | Add `auto_approve_remaining` attribute to InterruptNode + update `register_approval_response` | `backend/app/ai/tools/interrupt_node.py` | none | SC-1: attribute exists, defaults to False, set to True when approved+auto_approve_remaining both True | Low |
| 2 | Add `auto_approve_remaining` field to Pydantic schemas | `backend/app/models/schemas/ai.py` | none | Field exists on both `ApprovalRequest` and `WSApprovalResponseMessage` with default `False` | Low |
| 3 | Add guard clause + timeout counter fix in BackcastSecurityMiddleware | `backend/app/ai/middleware/backcast_security.py` | task 1 | SC-1: auto-approve short-circuits; SC-2: counter resets on new InterruptNode; SC-4: skips semaphore | Medium |
| 4 | Thread `auto_approve_remaining` through AgentService | `backend/app/ai/agent_service.py` | task 1 | Parameter passed through to `interrupt_node.register_approval_response()` | Low |
| 5 | Thread `auto_approve_remaining` through route handlers (WS + REST) | `backend/app/api/routes/ai_chat.py` | tasks 2, 4 | Both handlers pass `auto_approve_remaining` to their respective downstream calls | Low |
| 6 | Add `auto_approve_remaining` to TypeScript types | `frontend/src/features/ai/chat/types.ts` | none | Field exists on `WSApprovalResponseMessage` as optional boolean | Low |
| 7 | Update `sendApprovalResponse` in useStreamingChat hook | `frontend/src/features/ai/chat/api/useStreamingChat.ts` | task 6 | Function accepts and sends `autoApproveRemaining` parameter | Low |
| 8 | Add "Auto-approve remaining" checkbox to ApprovalDialog | `frontend/src/features/ai/components/ApprovalDialog.tsx` | none | Checkbox renders for HIGH risk, `onApprove` signature changed to `(autoApproveRemaining: boolean) => void` | Medium |
| 9 | Wire ChatInterface handler to pass auto-approve state | `frontend/src/features/ai/chat/components/ChatInterface.tsx` | tasks 7, 8 | `handleApproval` and `handleApprove` thread `autoApproveRemaining` through | Low |

### Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Add auto_approve_remaining attribute to InterruptNode"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add auto_approve_remaining to Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-003
    name: "Add guard clause + timeout counter fix in BackcastSecurityMiddleware"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Thread auto_approve_remaining through AgentService"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-005
    name: "Thread auto_approve_remaining through route handlers (WS + REST)"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-004]

  - id: FE-001
    name: "Add auto_approve_remaining to TypeScript types"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Update sendApprovalResponse in useStreamingChat hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Add auto-approve checkbox to ApprovalDialog"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-004
    name: "Wire ChatInterface handler to pass auto-approve state"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002, FE-003]

  - id: TEST-001
    name: "Run backend approval tests (existing + new)"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]
    kind: test

  - id: TEST-002
    name: "Run frontend approval tests (existing + new)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004]
    kind: test
```

**Execution Levels:**

- **Level 0** (parallel): BE-001, BE-002, FE-001, FE-003
- **Level 1** (parallel): BE-003 (after BE-001), BE-004 (after BE-001), FE-002 (after FE-001)
- **Level 2** (parallel): BE-005 (after BE-002 + BE-004), FE-004 (after FE-002 + FE-003)
- **Level 3** (sequential): TEST-001 (after BE-005), TEST-002 (after FE-004)

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| SC-1: auto-approve skips subsequent approvals | T-001 | `backend/tests/ai/tools/test_interrupt_node_approval.py` | `register_approval_response(approved=True, auto_approve_remaining=True)` sets flag; next call to `_check_risk_level_with_approval` returns `(True, None)` without polling |
| SC-2: timeout counter resets on new InterruptNode | T-002 | `backend/tests/ai/middleware/test_backcast_security.py` (new or existing) | After simulating 3 timeouts on InterruptNode A, switching to InterruptNode B resets counter to 0 |
| SC-3: existing tests still pass | T-003 | `backend/tests/ai/tools/test_interrupt_node_approval.py`, `test_approval_workflow.py`, `test_agent_service_approval_integration.py` | All existing test assertions pass unchanged |
| SC-4: auto-approve skips semaphore | T-004 | `backend/tests/ai/middleware/test_backcast_security.py` (new or existing) | When `interrupt_node.auto_approve_remaining=True`, `_check_risk_level_with_approval` returns immediately without acquiring `_approval_semaphore` |
| SC-5: backward compatible | T-005 | `backend/tests/integration/ai/test_approval_workflow.py` | Client sends `WSApprovalResponseMessage` without `auto_approve_remaining` field; behavior identical to pre-change system |
| Checkbox UI for HIGH risk | T-006 | `frontend/src/features/ai/components/__tests__/ApprovalDialog.test.tsx` | Checkbox is visible when `risk_level="high"`, hidden when `risk_level="critical"`, `onApprove(true)` called when checkbox is checked |
| sendApprovalResponse threads param | T-007 | `frontend/src/features/ai/chat/api/__tests__/useStreamingChat.test.ts` (or manual) | WS message includes `auto_approve_remaining: true` when passed |

---

## Detailed Change Specifications

### BE-001: Add `auto_approve_remaining` attribute to InterruptNode

**File:** `backend/app/ai/tools/interrupt_node.py`

**Change 1 -- Add attribute to `__init__` (after line 116):**

```python
# CURRENT (line 116):
        self.interrupt_state: dict[str, dict[str, Any]] = {}

# NEW (line 116):
        self.interrupt_state: dict[str, dict[str, Any]] = {}
        # Auto-approve flag: when True, subsequent HIGH-risk tools in this
        # execution skip approval polling. Set by user via "Auto-approve
        # remaining tools" checkbox. Resets naturally when InterruptNode is
        # discarded at execution end.
        self.auto_approve_remaining: bool = False
```

**Change 2 -- Update `register_approval_response` (lines 343-359):**

```python
# CURRENT:
    def register_approval_response(
        self,
        approval_id: str,
        approved: bool,
    ) -> None:
        """Register an approval response from the user.

        Args:
            approval_id: Approval ID being responded to
            approved: True if user approved, False if rejected

        Note:
            This method is called by AgentService when it receives
            a WSApprovalResponseMessage from the WebSocket.
        """
        if approval_id in self.pending_approvals:
            self.pending_approvals[approval_id]["approved"] = approved

# NEW:
    def register_approval_response(
        self,
        approval_id: str,
        approved: bool,
        auto_approve_remaining: bool = False,
    ) -> None:
        """Register an approval response from the user.

        Args:
            approval_id: Approval ID being responded to
            approved: True if user approved, False if rejected
            auto_approve_remaining: When True and approved is True, set the
                auto-approve flag so all subsequent HIGH-risk tools in this
                execution skip approval polling.

        Note:
            This method is called by AgentService when it receives
            a WSApprovalResponseMessage from the WebSocket.
            Rejection does NOT cancel the auto-approve flag -- reject is a
            one-time override for the specific tool.
        """
        if approval_id in self.pending_approvals:
            self.pending_approvals[approval_id]["approved"] = approved

        if approved and auto_approve_remaining:
            self.auto_approve_remaining = True
            logger.info(
                "AUTO_APPROVE_FLAG_SET: auto_approve_remaining=True "
                f"after approval_id={approval_id}"
            )
```

Note: This requires adding `from app.ai.agent_service import logger` at the top of the file (it is already imported lazily in `_send_approval_request` at line 184, but needs to be accessible at the module/class level or imported directly in the method). The simplest approach: use the same lazy import pattern inside the `if` block.

---

### BE-002: Add `auto_approve_remaining` to Pydantic schemas

**File:** `backend/app/models/schemas/ai.py`

**Change 1 -- `ApprovalRequest` schema (line 298):**

```python
# CURRENT:
class ApprovalRequest(BaseModel):
    """Request body for approving/rejecting a tool execution via REST."""

    approval_id: str = Field(..., description="UUID of the approval request")
    approved: bool = Field(..., description="True to approve, False to reject")

# NEW:
class ApprovalRequest(BaseModel):
    """Request body for approving/rejecting a tool execution via REST."""

    approval_id: str = Field(..., description="UUID of the approval request")
    approved: bool = Field(..., description="True to approve, False to reject")
    auto_approve_remaining: bool = Field(
        default=False,
        description="When True and approved, auto-approve all subsequent HIGH-risk tools in this execution",
    )
```

**Change 2 -- `WSApprovalResponseMessage` schema (line 774):**

```python
# CURRENT:
class WSApprovalResponseMessage(BaseModel):
    """WebSocket approval response message from client.

    Client -> Server message with user's decision on approval request.
    Sent when user clicks "Approve" or "Reject" in the approval dialog.
    """

    type: Literal["approval_response"] = Field(
        default="approval_response", description="Message type discriminator"
    )
    approval_id: str = Field(..., description="Approval ID being responded to")
    approved: bool = Field(..., description="True if user approved, False if rejected")
    user_id: UUID = Field(..., description="User ID making the decision")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of the decision"
    )

# NEW:
class WSApprovalResponseMessage(BaseModel):
    """WebSocket approval response message from client.

    Client -> Server message with user's decision on approval request.
    Sent when user clicks "Approve" or "Reject" in the approval dialog.
    """

    type: Literal["approval_response"] = Field(
        default="approval_response", description="Message type discriminator"
    )
    approval_id: str = Field(..., description="Approval ID being responded to")
    approved: bool = Field(..., description="True if user approved, False if rejected")
    auto_approve_remaining: bool = Field(
        default=False,
        description="When True and approved, auto-approve all subsequent HIGH-risk tools in this execution",
    )
    user_id: UUID = Field(..., description="User ID making the decision")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of the decision"
    )
```

---

### BE-003: Add guard clause + timeout counter fix in BackcastSecurityMiddleware

**File:** `backend/app/ai/middleware/backcast_security.py`

**Change 1 -- Add `_last_seen_interrupt_node` to `__init__` (after line 77):**

```python
# CURRENT (line 77):
        self._consecutive_approval_timeouts: int = 0

# NEW (line 77):
        self._consecutive_approval_timeouts: int = 0
        # Track last seen InterruptNode identity to detect execution boundaries.
        # The middleware is per-subagent and cached in compiled graphs, so it
        # persists across executions. We reset the timeout counter when the
        # InterruptNode reference changes (new execution).
        self._last_seen_interrupt_node: InterruptNode | None = None
```

**Change 2 -- Add early-return guard clause in `_check_risk_level_with_approval` (after line 597, before line 599):**

The guard clause must go after the `needs_approval` check (line 597) and before the existing `if not needs_approval: return True, None` (line 598-599). It should be inserted between the `needs_approval` computation and the `if not needs_approval` return.

```python
# CURRENT (lines 590-599):
        # Check if we need approval (HIGH in STANDARD mode)
        mode = ctx.execution_mode
        needs_approval = (
            risk_level >= RiskLevel.HIGH
            and mode == ExecutionMode.STANDARD
            and interrupt_node is not None
        )

        if not needs_approval:
            return True, None

# NEW (lines 590-615):
        # Check if we need approval (HIGH in STANDARD mode)
        mode = ctx.execution_mode
        needs_approval = (
            risk_level >= RiskLevel.HIGH
            and mode == ExecutionMode.STANDARD
            and interrupt_node is not None
        )

        if not needs_approval:
            return True, None

        # --- Execution boundary detection ---
        # Reset timeout counter when InterruptNode identity changes (new execution).
        # This prevents permanent tool blocking across executions on cached middleware.
        if interrupt_node is not self._last_seen_interrupt_node:
            self._consecutive_approval_timeouts = 0
            self._last_seen_interrupt_node = interrupt_node

        # --- Auto-approve guard clause ---
        # When the user has opted in to auto-approve remaining tools, skip the
        # semaphore acquisition and polling loop entirely. This is the core fix
        # for the parallel approval race condition.
        if interrupt_node.auto_approve_remaining:
            self._consecutive_approval_timeouts = 0
            logger.info(
                f"AUTO_APPROVE: tool='{tool_name}' auto-approved "
                f"(auto_approve_remaining=True)"
            )
            return True, None
```

The insertion point is line 599, after `if not needs_approval: return True, None` and before the `if interrupt_node is None:` check on line 601.

---

### BE-004: Thread `auto_approve_remaining` through AgentService

**File:** `backend/app/ai/agent_service.py`

**Change -- Update `register_approval_response` (lines 2409-2431):**

```python
# CURRENT:
    def register_approval_response(
        self, session_id: UUID, approval_id: str, approved: bool
    ) -> bool:
        """Register an approval response from the user.

        Args:
            session_id: The session ID
            approval_id: The approval ID being responded to
            approved: True if user approved, False if rejected

        Returns:
            True if the approval was registered successfully, False otherwise
        """
        interrupt_node = self.get_interrupt_node(session_id)
        if interrupt_node is None:
            logger.warning(f"No InterruptNode found for session {session_id}")
            return False

        interrupt_node.register_approval_response(approval_id, approved)
        logger.info(
            f"Registered approval response for session {session_id}, approval_id={approval_id}, approved={approved}"
        )
        return True

# NEW:
    def register_approval_response(
        self,
        session_id: UUID,
        approval_id: str,
        approved: bool,
        auto_approve_remaining: bool = False,
    ) -> bool:
        """Register an approval response from the user.

        Args:
            session_id: The session ID
            approval_id: The approval ID being responded to
            approved: True if user approved, False if rejected
            auto_approve_remaining: When True and approved, set the auto-approve
                flag for subsequent HIGH-risk tools in this execution

        Returns:
            True if the approval was registered successfully, False otherwise
        """
        interrupt_node = self.get_interrupt_node(session_id)
        if interrupt_node is None:
            logger.warning(f"No InterruptNode found for session {session_id}")
            return False

        interrupt_node.register_approval_response(
            approval_id, approved, auto_approve_remaining=auto_approve_remaining
        )
        logger.info(
            f"Registered approval response for session {session_id}, "
            f"approval_id={approval_id}, approved={approved}, "
            f"auto_approve_remaining={auto_approve_remaining}"
        )
        return True
```

---

### BE-005: Thread `auto_approve_remaining` through route handlers

**File:** `backend/app/api/routes/ai_chat.py`

**Change 1 -- WS handler: approval_response section (lines 749-753):**

```python
# CURRENT (lines 749-753):
                        success = agent_service.register_approval_response(
                            session_id=active_session_id,
                            approval_id=approval_response.approval_id,
                            approved=approval_response.approved,
                        )

# NEW (lines 749-754):
                        success = agent_service.register_approval_response(
                            session_id=active_session_id,
                            approval_id=approval_response.approval_id,
                            approved=approval_response.approved,
                            auto_approve_remaining=approval_response.auto_approve_remaining,
                        )
```

**Change 2 -- REST handler (line 516):**

```python
# CURRENT (line 516):
    interrupt_node.register_approval_response(body.approval_id, body.approved)

# NEW (line 516):
    interrupt_node.register_approval_response(
        body.approval_id,
        body.approved,
        auto_approve_remaining=body.auto_approve_remaining,
    )
```

---

### FE-001: Add `auto_approve_remaining` to TypeScript types

**File:** `frontend/src/features/ai/chat/types.ts`

**Change -- `WSApprovalResponseMessage` interface (lines 503-509):**

```typescript
// CURRENT:
export interface WSApprovalResponseMessage {
  type: "approval_response";
  approval_id: string; // UUID matching the approval request
  approved: boolean; // User's decision (true = approve, false = reject)
  user_id: string; // ID of the user making the decision
  timestamp: string; // ISO datetime of the decision
}

// NEW:
export interface WSApprovalResponseMessage {
  type: "approval_response";
  approval_id: string; // UUID matching the approval request
  approved: boolean; // User's decision (true = approve, false = reject)
  auto_approve_remaining?: boolean; // When true+approved, auto-approve subsequent HIGH-risk tools
  user_id: string; // ID of the user making the decision
  timestamp: string; // ISO datetime of the decision
}
```

---

### FE-002: Update `sendApprovalResponse` in useStreamingChat hook

**File:** `frontend/src/features/ai/chat/api/useStreamingChat.ts`

**Change 1 -- `UseStreamingChatReturn` interface (line 107):**

```typescript
// CURRENT:
  sendApprovalResponse: (approvalId: string, approved: boolean) => void;

// NEW:
  sendApprovalResponse: (approvalId: string, approved: boolean, autoApproveRemaining?: boolean) => void;
```

**Change 2 -- `sendApprovalResponse` function (lines 875-916):**

```typescript
// CURRENT:
  const sendApprovalResponse = useCallback(
    (approvalId: string, approved: boolean) => {

// NEW:
  const sendApprovalResponse = useCallback(
    (approvalId: string, approved: boolean, autoApproveRemaining: boolean = false) => {
```

**Change 3 -- Include in response message (lines 896-902):**

```typescript
// CURRENT:
      const response: WSApprovalResponseMessage = {
        type: "approval_response",
        approval_id: approvalId,
        approved,
        user_id: userId,
        timestamp: new Date().toISOString(),
      };

// NEW:
      const response: WSApprovalResponseMessage = {
        type: "approval_response",
        approval_id: approvalId,
        approved,
        auto_approve_remaining: autoApproveRemaining,
        user_id: userId,
        timestamp: new Date().toISOString(),
      };
```

---

### FE-003: Add "Auto-approve remaining" checkbox to ApprovalDialog

**File:** `frontend/src/features/ai/components/ApprovalDialog.tsx`

**Change 1 -- Add `Checkbox` import and `useState` (lines 15-16):**

```typescript
// CURRENT:
import { useMemo } from "react";
import { Modal, Alert, Typography, Tag, Space, Descriptions, Button, theme } from "antd";

// NEW:
import { useState, useMemo } from "react";
import { Modal, Alert, Typography, Tag, Space, Descriptions, Button, Checkbox, theme } from "antd";
```

**Change 2 -- Update `ApprovalDialogProps` interface (lines 22-30):**

```typescript
// CURRENT:
interface ApprovalDialogProps {
  open: boolean;
  approvalRequest: WSApprovalRequestMessage | null;
  remainingSeconds?: number | null;
  onApprove: () => void;
  onReject: () => void;
  onCancel?: () => void;
}

// NEW:
interface ApprovalDialogProps {
  open: boolean;
  approvalRequest: WSApprovalRequestMessage | null;
  remainingSeconds?: number | null;
  onApprove: (autoApproveRemaining: boolean) => void;
  onReject: () => void;
  onCancel?: () => void;
}
```

**Change 3 -- Add checkbox state in component body (after line 76, inside the component function, before `isExpired`):**

```typescript
  // Checkbox state for auto-approve, reset on each open
  const [autoApproveRemaining, setAutoApproveRemaining] = useState(false);
```

Note: Because `destroyOnHidden` is set on the Modal (line 167), the component is destroyed and re-created each time it opens. This means the `useState(false)` will naturally reset each time the dialog opens. No additional reset logic is needed.

**Change 4 -- Update `handleApprove` internal function (lines 113-115):**

```typescript
// CURRENT:
  const handleApprove = () => {
    onApprove();
  };

// NEW:
  const handleApprove = () => {
    onApprove(autoApproveRemaining);
  };
```

**Change 5 -- Add checkbox between tool details and bottom info Alert (after the `</Descriptions>` closing tag on line 249, before the bottom `<Alert>` on line 251):**

```tsx
        </Descriptions>

        {/* Auto-approve checkbox: only shown for HIGH risk level */}
        {approvalRequest.risk_level === "high" && (
          <div style={{ marginTop: token.marginMD }}>
            <Checkbox
              checked={autoApproveRemaining}
              onChange={(e) => setAutoApproveRemaining(e.target.checked)}
            >
              Auto-approve remaining tools in this execution
            </Checkbox>
          </div>
        )}

        <Alert
```

---

### FE-004: Wire ChatInterface handler to pass auto-approve state

**File:** `frontend/src/features/ai/chat/components/ChatInterface.tsx`

**Change 1 -- Update `handleApproval` callback (lines 929-941):**

```typescript
// CURRENT:
  const handleApproval = useCallback((approved: boolean) => {
    if (!approvalRequest) {
      return;
    }

    // Send approval response
    streamingChat.sendApprovalResponse(approvalRequest.approval_id, approved);

    // Close dialog and clear state
    setShowApprovalDialog(false);
    setApprovalRequest(null);
    setApprovalRemaining(null);
  }, [approvalRequest, streamingChat]);

// NEW:
  const handleApproval = useCallback((approved: boolean, autoApproveRemaining: boolean = false) => {
    if (!approvalRequest) {
      return;
    }

    // Send approval response
    streamingChat.sendApprovalResponse(approvalRequest.approval_id, approved, autoApproveRemaining);

    // Close dialog and clear state
    setShowApprovalDialog(false);
    setApprovalRequest(null);
    setApprovalRemaining(null);
  }, [approvalRequest, streamingChat]);
```

**Change 2 -- Update `handleApprove` callback (lines 943-945):**

```typescript
// CURRENT:
  const handleApprove = useCallback(() => {
    handleApproval(true);
  }, [handleApproval]);

// NEW:
  const handleApprove = useCallback((autoApproveRemaining: boolean = false) => {
    handleApproval(true, autoApproveRemaining);
  }, [handleApproval]);
```

**Change 3 -- Find where `handleApprove` is passed to `ApprovalDialog` and ensure the signature matches.** The ApprovalDialog now calls `onApprove(autoApproveRemaining)` which flows through `handleApprove(autoApproveRemaining)` to `handleApproval(true, autoApproveRemaining)`. The `handleReject` remains unchanged (calls `handleApproval(false)` with no auto-approve).

---

## Test Specification

### Test Hierarchy

```text
tests/
  backend/
    ai/
      tools/
        test_interrupt_node_approval.py          (existing -- must still pass)
      middleware/
        test_backcast_security.py                (existing -- must still pass + new tests)
    integration/
      ai/
        test_approval_workflow.py                (existing -- must still pass)
        test_agent_service_approval_integration.py (existing -- must still pass)
  frontend/
    features/
      ai/
        components/
          __tests__/ApprovalDialog.test.tsx       (existing -- must update + new tests)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | `test_register_approval_response_sets_auto_approve_flag` | SC-1 | Unit | `register_approval_response(approved=True, auto_approve_remaining=True)` sets `interrupt_node.auto_approve_remaining = True` |
| T-002 | `test_auto_approve_flag_not_set_on_rejection` | SC-1 | Unit | `register_approval_response(approved=False, auto_approve_remaining=True)` does NOT set the flag |
| T-003 | `test_auto_approve_flag_not_set_when_param_false` | SC-1 | Unit | `register_approval_response(approved=True, auto_approve_remaining=False)` does NOT set the flag |
| T-004 | `test_timeout_counter_resets_on_new_interrupt_node` | SC-2 | Unit | After simulating 3 timeouts, switching to a new InterruptNode resets `_consecutive_approval_timeouts` to 0 |
| T-005 | `test_auto_approve_skips_semaphore_and_polling` | SC-4 | Unit | When `interrupt_node.auto_approve_remaining = True`, `_check_risk_level_with_approval` returns `(True, None)` without blocking |
| T-006 | `test_auto_approve_logs_info_message` | NFR-3 | Unit | Auto-approve triggers `logger.info` with `AUTO_APPROVE: tool='...'` message |
| T-007 | `test_backward_compatible_no_auto_approve_field` | SC-5 | Integration | Client sends WS message without `auto_approve_remaining`; system behaves identically to pre-change |
| T-008 | `test_existing_approval_tests_still_pass` | SC-3 | Regression | All existing tests in `test_interrupt_node_approval.py`, `test_approval_workflow.py`, `test_agent_service_approval_integration.py` pass |
| T-009 | `test_checkbox_visible_for_high_risk` | FR-5 | Unit (frontend) | Checkbox renders when `risk_level="high"` |
| T-010 | `test_checkbox_hidden_for_critical_risk` | FR-5 | Unit (frontend) | Checkbox not rendered when `risk_level="critical"` |
| T-011 | `test_on_approve_receives_checkbox_state` | FR-5 | Unit (frontend) | `onApprove(true)` called when checkbox checked + Approve clicked; `onApprove(false)` when unchecked |
| T-012 | `test_checkbox_resets_on_dialog_reopen` | FR-5 | Unit (frontend) | After closing and reopening dialog, checkbox is unchecked |

### Test Infrastructure Needs

- **Fixtures needed**: Existing `InterruptNode` fixtures from `test_interrupt_node_approval.py`; existing `BackcastSecurityMiddleware` fixtures from middleware tests
- **Mocks/stubs**: `asyncio.Semaphore` may need observation to verify skip behavior; `logger` may need capture for log assertion
- **Database state**: No database changes required (in-memory state only)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Guard clause in wrong position causes auto-approve to fire for LOW/CRITICAL risk tools | Low | High | Guard clause is AFTER `needs_approval` check which already gates on `risk_level >= HIGH AND mode == STANDARD AND interrupt_node is not None` |
| Technical | `_last_seen_interrupt_node` identity check fails due to InterruptNode reuse | Low | Medium | InterruptNode is created per-execution and stored in `_interrupt_nodes` dict by session_id. New execution creates a new instance. Identity check (`is`) is correct. |
| Integration | Frontend sends `auto_approve_remaining` but backend schema does not parse it | Low | Low | Field has `default=False` so missing field = no auto-approve. Extra field in strict-mode Pydantic would raise validation error -- but Pydantic v2 by default ignores extra fields unless `model_config = ConfigDict(extra='forbid')`. Verify `WSApprovalResponseMessage` does not forbid extras. |
| UX | User checks auto-approve but then wants to reject a specific tool | Medium | Low | By design: reject is a one-time override. The flag persists. This is the agreed behavior from CHECK phase decisions. |
| Regression | Existing approval tests break due to signature changes | Low | High | All new parameters have defaults (`auto_approve_remaining=False`). Existing call sites continue working. Run existing test suite as regression check. |

---

## Prerequisites

### Technical

- [x] No database migrations needed
- [x] Dependencies installed (no new packages required)
- [x] Ant Design `Checkbox` already available in frontend dependencies

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed (InterruptNode, BackcastSecurityMiddleware, graph_cache ContextVar patterns)

---

## Manual Verification Plan

1. Start backend (`cd backend && source .venv/bin/activate && uv run uvicorn app.main:app --reload --port 8020`) and frontend (`cd frontend && npm run dev`)
2. Open AI Chat, select Senior Project Manager, STANDARD mode
3. Send a prompt requiring multiple HIGH-risk tool calls (e.g., "Create a project with 5 WBEs")
4. Verify: first approval dialog shows "Auto-approve remaining tools in this execution" checkbox (visible for HIGH risk)
5. Check the checkbox, click Approve
6. Verify: subsequent tools execute without approval dialogs
7. Verify: backend logs show `AUTO_APPROVE: tool='...' auto-approved (auto_approve_remaining=True)` at INFO level
8. Start new chat, repeat WITHOUT checking the checkbox -- verify individual approvals still work normally
9. Verify: after checking auto-approve, clicking Reject on a subsequent tool rejects that one tool but auto-approve persists for the next one
10. Run backend tests: `cd backend && uv run pytest tests/ai/tools/test_interrupt_node_approval.py tests/integration/ai/test_approval_workflow.py tests/integration/ai/test_agent_service_approval_integration.py -x`
11. Run frontend tests: `cd frontend && npm test -- --grep "approval"`

---

## Documentation References

### Required Reading

- InterruptNode: `backend/app/ai/tools/interrupt_node.py`
- BackcastSecurityMiddleware: `backend/app/ai/middleware/backcast_security.py`
- Graph cache ContextVars: `backend/app/ai/graph_cache.py`
- WS protocol schemas: `backend/app/models/schemas/ai.py`

### Code References

- Existing approval test pattern: `backend/tests/ai/tools/test_interrupt_node_approval.py`
- Existing middleware test pattern: `backend/tests/ai/middleware/test_backcast_security.py`
- Existing integration test pattern: `backend/tests/integration/ai/test_approval_workflow.py`
- Frontend dialog test pattern: `frontend/src/features/ai/components/__tests__/ApprovalDialog.test.tsx`
