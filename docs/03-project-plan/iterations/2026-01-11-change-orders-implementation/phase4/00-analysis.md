# Phase 4: Change Order Approval & Merge - Analysis

**Date Created:** 2026-01-14
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 4 of 4 - Change Order Approval & Merge
**Status:** Analysis Phase
**Related Docs:**
- [Change Management User Stories](../../../01-product-scope/change-management-user-stories.md)
- [Product Backlog](../../product-backlog.md)
- [Phase 3 CHECK](../phase3/03-check.md)
- [Phase 3 ACT](../phase3/04-act.md)
- [Overall Analysis](../00-analysis.md)

---

## Request Analysis: Implement Change Order Approval & Merge Workflow

### Clarified Requirements

The user requests implementation of the **Approval and Merge** phase of the Change Management system. This phase enables:

1. **Workflow State Transitions:** Status changes (Draft → Submitted → Approved → Implemented)
2. **Branch Locking:** Automatic locking when CO is submitted for review
3. **Merge Operations:** Merging approved COs into target branch (main)
4. **Rejection Handling:** Returning rejected COs to Draft for rework
5. **Frontend UI:** Action buttons, confirmation modals, status indicators

**Key Assumptions:**
- Backend workflow service already implemented (`ChangeOrderWorkflowService`)
- Backend merge endpoint exists (`POST /change-orders/{id}/merge`)
- Phase 3 (Impact Analysis) is complete
- RBAC permissions are defined (`change-order-update` for merge)

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories from [change-management-user-stories.md](../../../01-product-scope/change-management-user-stories.md):**

| Story | Description | Priority | Status |
|-------|-------------|----------|--------|
| 3.5 | Submitting the Change (status transition, branch lock) | High | Backend ✅, Frontend ❌ |
| 3.6 | Accepting the Change (Merge workflow) | Critical | Backend ✅, Frontend ❌ |
| 3.7 | Rejecting or Deleting the Change | Critical | Backend ✅, Frontend ❌ |

**Workflow State Machine** (already defined in `ChangeOrderWorkflowService`):

```
Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented
         ↑                                    ↓
         └────────────────────────────────────┘
             (Rejected can return to Draft)
```

**Branch Locking Rules:**
- **Lock on:** Draft → Submitted for Approval
- **Unlock on:** Under Review → Rejected
- **Locked = Read-Only:** No entity modifications allowed in CO branch

### Architecture Context

**Bounded Contexts Involved:**
1. **E006 (Branching & Change Order Management)** - Primary context
2. **E003 (Entity Versioning System)** - Merge operations, branch management
3. **E004 (Project Structure Management)** - WBEs, Cost Elements affected by merge

**Existing Patterns:**
- **Workflow State Machine:** `ChangeOrderWorkflowService` with transitions and lock rules
- **Generic Services:** `BranchableService[T].merge_branch()` for merge operations
- **Command Pattern:** `MergeBranchCommand` for executing merges
- **RBAC Integration:** Permission checks on workflow endpoints

### Codebase Analysis

#### Backend

**Existing Implementation:**

| File | Description | Status |
|------|-------------|--------|
| `backend/app/services/change_order_service.py` | CO service with `merge_change_order()`, `update_change_order()` | ✅ Complete |
| `backend/app/services/change_order_workflow_service.py` | State machine with transitions, lock rules | ✅ Complete |
| `backend/app/api/routes/change_orders.py` | `/merge` endpoint, `/update` endpoint | ✅ Complete |
| `backend/app/core/branching/service.py` | `BranchableService.merge_branch()` | ✅ Complete |

**Workflow Service Features** (already implemented):

```python
class ChangeOrderWorkflowService:
    # Valid transitions
    _TRANSITIONS = {
        "Draft": ["Submitted for Approval"],
        "Submitted for Approval": ["Under Review"],
        "Under Review": ["Approved", "Rejected"],
        "Rejected": ["Submitted for Approval"],
        "Approved": ["Implemented"],
        "Implemented": [],  # Terminal
    }

    # Lock rules
    _LOCK_TRANSITIONS = {("Draft", "Submitted for Approval")}
    _UNLOCK_TRANSITIONS = {("Under Review", "Rejected")}
    _EDITABLE_STATUSES = {"Draft", "Rejected"}
```

**Merge Endpoint** (already exists):

```python
@router.post("/{change_order_id}/merge")
async def merge_change_order(
    change_order_id: UUID,
    target_branch: str = Query("main"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrder:
    """Merge a Change Order's branch into the target branch."""
    return await service.merge_change_order(
        change_order_id=change_order_id,
        actor_id=current_user.user_id,
        target_branch=target_branch,
    )
```

**Status Update** (already exists):

```python
@router.put("/{change_order_id}")
async def update_change_order(
    change_order_id: UUID,
    change_order_in: ChangeOrderUpdate,  # Includes status field
    ...
) -> ChangeOrder:
    """Update a change order's metadata with workflow validation."""
    # Validates transitions via workflow service
    # Triggers branch lock/unlock based on status changes
```

#### Frontend

**Existing Components:**

| Component | File | Reusability |
|-----------|------|-------------|
| `ChangeOrderList` | `features/change-orders/components/ChangeOrderList.tsx` | High - extend with actions |
| `ChangeOrderForm` | `features/change-orders/components/ChangeOrderForm.tsx` | High - add workflow controls |
| `BranchSelector` | `components/time-machine/BranchSelector.tsx` | High - add lock indicators |

**Missing Components:**

- **Workflow Action Buttons**: Submit, Approve, Reject, Merge buttons in CO list/detail view
- **Confirmation Modals**: For merge, reject, delete actions
- **Status Transition Form**: For selecting next status with validation
- **Lock Indicator**: Visual cue when branch is locked
- **Merge Results Display**: Success/failure feedback after merge

**State Management:**

- **Server State**: TanStack Query for CO data (existing `useChangeOrders`)
- **Client State**: Need workflow state for action confirmations
- **Routing**: `/projects/:projectId/change-orders/:changeOrderId` (existing)

---

## Solution Options

### Option 1: Workflow Action Buttons with Confirmation Modals (Recommended)

**Architecture & Design:**
- Add action buttons to `ChangeOrderList` and `ChangeOrderDetail` views
- Each workflow action has dedicated button:
  - **Submit** (Draft → Submitted for Approval)
  - **Approve** (Under Review → Approved)
  - **Reject** (Under Review → Rejected)
  - **Merge** (Approved → Implemented)
  - **Reopen** (Rejected → Submitted for Approval)
- Confirmation modals for destructive actions (Merge, Reject, Delete)
- Status dropdown with filtered options based on `available_transitions`

**Component Structure:**

```typescript
// New components
features/change-orders/components/
├── WorkflowActionBar.tsx           // Action buttons row
├── StatusTransitionModal.tsx        // Status change confirmation
├── MergeConfirmationModal.tsx       // Merge confirmation
├── RejectReasonModal.tsx            // Reject with reason input
└── BranchLockIndicator.tsx          // Visual lock status

// Modified components
├── ChangeOrderList.tsx              // Add action column
└── ChangeOrderDetail.tsx            // Add workflow actions
```

**UX Design:**
- **Action Visibility**: Buttons shown/hidden based on `can_edit_status` and `available_transitions`
- **Confirmation Required**: Merge and Reject require explicit confirmation
- **Feedback**: Toast notifications on successful status change
- **Branch Lock**: Amber lock icon when `branch_locked = true`

**Implementation:**
- Extend `ChangeOrderPublic` schema with `available_transitions` (already exists!)
- Create `useWorkflowActions` hook for status transitions
- Use Ant Design `Modal.confirm()` for simple confirmations
- Custom modals for complex actions (merge, reject)

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| **Pros** | - Clear user intent<br>- Explicit confirmation prevents mistakes<br>- Workflow rules enforced by backend<br>- Buttons self-document available actions |
| **Cons** | - More UI components<br>- Requires careful permission handling |
| **Complexity** | Medium |
| **Maintainability** | High |
| **Performance** | Good (minimal API overhead) |

---

### Option 2: Inline Status Dropdown with Auto-Actions

**Architecture & Design:**
- Single status dropdown in CO form/list
- Status change triggers automatic actions:
  - Selecting "Submitted for Approval" → Locks branch
  - Selecting "Approved" → Shows merge confirmation → Merges
  - Selecting "Rejected" → Shows reason modal → Unlocks branch

**Component Structure:**

```typescript
// Single component
features/change-orders/components/
└── StatusDropdown.tsx                // Handles all transitions with side effects
```

**UX Design:**
- Simpler UI with single control point
- Status change triggers all side effects automatically
- Progress stepper showing workflow progress

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| **Pros** | - Simpler UI<br>- Fewer components<br>- Less code |
| **Cons** | - Less discoverability (what will happen?)<br>- Harder to add custom actions<br>- Users may not understand side effects |
| **Complexity** | Low (code) / High (UX clarity) |
| **Maintainability** | Medium |
| **Performance** | Good |

---

### Option 3: Dedicated Workflow Page

**Architecture & Design:**
- Separate page for CO workflow management
- `/projects/:projectId/change-orders/:id/workflow`
- Stepper UI showing workflow stages
- Action buttons at each stage

**Component Structure:**

```typescript
features/change-orders/components/
├── WorkflowStepper.tsx              // Visual workflow progress
├── WorkflowStage.tsx                 // Individual stage with actions
└── WorkflowPage.tsx                  // Full workflow management page
```

**UX Design:**
- Visual representation of workflow (stepper)
- Clear current stage highlighting
- Action buttons context-aware per stage

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| **Pros** | - Clear workflow visualization<br>- Good for complex workflows<br>- Separates concerns |
| **Cons** | - Additional page/route<br>- More navigation<br>- Overkill for linear workflow |
| **Complexity** | Medium |
| **Maintainability** | Good |
| **Performance** | Good (additional page load) |

---

## Comparison Summary

| Criteria | Option 1 (Action Buttons) | Option 2 (Inline Dropdown) | Option 3 (Workflow Page) |
|----------|--------------------------|---------------------------|-------------------------|
| **Development Effort** | Medium (2-3 days) | Low (1-2 days) | Medium-High (3-4 days) |
| **UX Clarity** | High (explicit actions) | Medium (implicit effects) | High (visual stepper) |
| **Discoverability** | High (buttons visible) | Low (hidden in dropdown) | High (workflow path shown) |
| **Flexibility** | High (easy to customize) | Low (tied to dropdown) | Medium (stage-based) |
| **Best For** | Production systems | Rapid prototypes | Complex workflows |

---

## Recommendation

**I recommend Option 1: Workflow Action Buttons with Confirmation Modals**

**Justification:**

1. **Workflow Clarity:** Buttons make available actions explicit and discoverable
2. **Safety:** Confirmation modals prevent accidental destructive actions
3. **Backend Integration:** Leverages existing `available_transitions` field
4. **Scalability:** Easy to add custom actions (e.g., "Request Info")
5. **User Control:** Users understand exactly what will happen before clicking
6. **Pattern Consistency:** Follows existing Ant Design patterns (confirm dialogs)

**Implementation Plan:**

1. **Backend** (mostly complete):
   - ✅ `ChangeOrderWorkflowService` with state transitions
   - ✅ Branch locking on status change
   - ✅ Merge endpoint
   - ⚠️ May need merge conflict detection

2. **Frontend** (to implement):
   - Action buttons component with permission-based visibility
   - Confirmation modals for merge/reject
   - Status transition hook using `update_change_order`
   - Branch lock indicator in header
   - Toast notifications for feedback

---

## Detailed Design for Recommended Option

### Component: WorkflowActionBar

**Purpose:** Display available workflow actions based on CO status and permissions

**Props:**
```typescript
interface WorkflowActionBarProps {
  changeOrder: ChangeOrderPublic;
  onActionSuccess?: () => void;  // Callback to refresh data
}
```

**Implementation:**
```typescript
export const WorkflowActionBar: React.FC<WorkflowActionBarProps> = ({
  changeOrder,
  onActionSuccess,
}) => {
  const { available_transitions, can_edit_status, branch_locked } = changeOrder;
  const transitionMutation = useTransition();

  const handleTransition = async (newStatus: string) => {
    await Modal.confirm({
      title: `Change status to "${newStatus}"?`,
      content: getStatusConfirmationContent(newStatus),
      onOk: async () => {
        await transitionMutation.mutateAsync({
          changeOrderId: changeOrder.change_order_id,
          status: newStatus,
        });
        onActionSuccess?.();
      },
    });
  };

  // Show merge button if Approved
  if (changeOrder.status === "Approved") {
    return <MergeButton changeOrder={changeOrder} onSuccess={onActionSuccess} />;
  }

  // Show action buttons for available transitions
  return (
    <Space>
      {available_transitions.map((nextStatus) => (
        <Button
          key={nextStatus}
          type={getButtonType(nextStatus)}
          disabled={!can_edit_status || branch_locked}
          onClick={() => handleTransition(nextStatus)}
        >
          {getButtonLabel(nextStatus)}
        </Button>
      ))}
    </Space>
  );
};
```

### Component: MergeConfirmationModal

**Purpose:** Confirm merge operation with impact summary

**Features:**
- Shows source branch and target branch
- Warning about irreversible operation
- Option to require comment/reason
- Links to impact analysis

**Implementation:**
```typescript
interface MergeConfirmationProps {
  changeOrder: ChangeOrderPublic;
  onConfirm: () => Promise<void>;
}

export const MergeConfirmationModal: React.FC<MergeConfirmationProps> = ({
  changeOrder,
  onConfirm,
}) => {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  return (
    <Modal
      title="Merge Change Order"
      open={open}
      onOk={async () => {
        await onConfirm();
        setOpen(false);
      }}
      onCancel={() => setOpen(false)}
      okText="Merge"
      okButtonProps={{ danger: true }}
    >
      <Alert
        message="Warning"
        description="This operation will merge the change order branch into main. This action cannot be undone."
        type="warning"
        showIcon
      />
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="Source Branch">{changeOrder.branch_name}</Descriptions.Item>
        <Descriptions.Item label="Target Branch">main</Descriptions.Item>
        <Descriptions.Item label="Impact Analysis">
          <Link to={`/projects/${changeOrder.project_id}/change-orders/${changeOrder.change_order_id}/impact`}>
            View Impact Analysis
          </Link>
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  );
};
```

### Hook: useWorkflowActions

**Purpose:** Encapsulate workflow action logic

**Implementation:**
```typescript
export const useWorkflowActions = (changeOrderId: string) => {
  const queryClient = useQueryClient();

  const transitionMutation = useMutation({
    mutationFn: async (data: { status: string; reason?: string }) => {
      return updateChangeOrder(changeOrderId, {
        status: data.status,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      queryClient.invalidateQueries({ queryKey: ["change-order", changeOrderId] });
      message.success("Status updated successfully");
    },
  });

  const mergeMutation = useMutation({
    mutationFn: async (targetBranch: string = "main") => {
      return mergeChangeOrder(changeOrderId, targetBranch);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      queryClient.invalidateQueries({ queryKey: ["change-order", changeOrderId] });
      message.success("Change Order merged successfully");
    },
  });

  return {
    transition: transitionMutation.mutateAsync,
    merge: mergeMutation.mutateAsync,
    isTransitioning: transitionMutation.isPending,
    isMerging: mergeMutation.isPending,
  };
};
```

### Branch Lock Indicator

**Purpose:** Visual cue when CO branch is locked

**Location:** Time Machine header or CO detail header

**Implementation:**
```typescript
export const BranchLockIndicator: React.FC<{ locked: boolean }> = ({ locked }) => {
  if (!locked) return null;

  return (
    <Tooltip title="Branch is locked - no modifications allowed">
      <LockFilled style={{ color: "#faad14", marginLeft: 8 }} />
    </Tooltip>
  );
};
```

---

## Integration with Existing Components

### ChangeOrderList Modifications

**Add Actions Column:**

```typescript
const columns: ColumnsType<ChangeOrderPublic> = [
  // ... existing columns
  {
    title: "Actions",
    key: "actions",
    width: 200,
    render: (_, record) => (
      <Space size="small">
        <Link to={`../change-orders/${record.change_order_id}/impact`}>
          <Button icon={<FundOutlined />} size="small" />
        </Link>
        <WorkflowActionBar
          changeOrder={record}
          onActionSuccess={() => refetch()}
        />
      </Space>
    ),
  },
];
```

### ChangeOrderDetail Modifications

**Add Workflow Section:**

```typescript
export const ChangeOrderDetail: React.FC = () => {
  const { changeOrderId } = useParams();
  const { data: changeOrder } = useChangeOrder(changeOrderId);

  return (
    <PageHeader
      title={changeOrder?.title}
      extra={<WorkflowActionBar changeOrder={changeOrder} />}
    >
      {/* ... existing detail content ... */}

      {/* Workflow Status Section */}
      <Card title="Workflow Status">
        <StatusStepper changeOrder={changeOrder} />
      </Card>
    </PageHeader>
  );
};
```

---

## Backend Considerations

### Merge Conflict Detection

**Current Status:** Backend `merge_branch()` exists but may not have conflict detection

**May Need:**
- Detect if main branch has changed since CO creation
- Warn user if conflicts detected
- Provide conflict resolution UI (or just warning)

**Analysis Required:**
- Check `BranchableService.merge_branch()` implementation
- Determine if conflict detection exists
- If not, add simple version conflict check

### Status Transition Validation

**Current Status:** ✅ Complete

`ChangeOrderWorkflowService.is_valid_transition()` validates:
- Transition is allowed per state machine
- Editing is allowed in current status
- Branch lock/unlock triggered appropriately

### Branch Locking

**Current Status:** ✅ Complete

`ChangeOrderService.update_change_order()` triggers:
- Lock on: Draft → Submitted for Approval
- Unlock on: Under Review → Rejected

---

## Questions for Decision

1. **Merge Confirmation:** Should we require a comment/reason for merge? (Could be audit trail)

2. **Conflict Handling:** If merge conflicts are detected, should we:
   - Block merge and show conflicts?
   - Warn but allow "force merge"?
   - Automatically resolve with "change wins" (current behavior)?

3. **Rejection Reason:** Should we require a reason when rejecting a CO? (Audit trail)

4. **Workflow Automation:** Should "Approved" → "Implemented" be automatic, or require explicit "Merge" action?

5. **Notification Scope:** Should we implement real-time notifications (WebSocket) or is toast sufficient?

---

## Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Users can submit CO for review (Draft → Submitted)
- [ ] Branch locks automatically on submit
- [ ] Users can approve/reject submitted COs
- [ ] Users can merge approved COs to main
- [ ] Merge shows confirmation with impact analysis link
- [ ] Rejecting CO returns to Draft with unlock
- [ ] Status dropdown only shows valid transitions
- [ ] Lock indicator visible when branch is locked
- [ ] Action buttons respect RBAC permissions

**Technical Criteria:**

- [ ] All status transitions validated by backend workflow service
- [ ] Frontend type safety (TypeScript strict mode)
- [ ] Zero ESLint errors
- [ ] TanStack Query cache invalidated on status change
- [ ] Error handling for failed transitions
- [ ] Loading states during async operations

**Business Criteria:**

- [ ] Full audit trail (who changed status, when)
- [ ] Irreversible operations require confirmation
- [ ] Workflow rules enforced server-side
- [ ] Branch isolation maintained during merge

---

## Definition of Done

**Phase 4 is complete when:**

- [ ] All acceptance criteria met
- [ ] Backend: Any missing validation implemented (if needed)
- [ ] Frontend: TypeScript strict mode passes, ESLint passes
- [ ] E2E Tests: Submit → Approve → Merge flow
- [ ] Code reviewed and merged
- [ ] Documentation updated (ADR if needed)
- [ ] Demo: Complete workflow from Draft to Implemented

---

## Next Steps

**Immediate Actions:**

1. Confirm Option 1 (Action Buttons) is acceptable
2. Answer decision questions above
3. Create Phase 4 PLAN document with detailed tasks
4. Begin implementation with TDD approach

---

**Document Status:** Ready for Review
**Next Document:** `01-plan.md` (after approval)
**Approval Required From:** Product Owner, Tech Lead
