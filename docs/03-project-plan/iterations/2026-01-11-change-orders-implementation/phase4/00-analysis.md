# Phase 4: Change Order Approval & Merge - Analysis

**Date Created:** 2026-01-14
**Last Updated:** 2026-01-14
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 4 of 4 - Change Order Approval & Merge
**Status:** Analysis Phase - Approved Design
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
3. **Merge Operations:** Merging approved COs into target branch (main) with automatic status transition
4. **Rejection Handling:** Returning rejected COs to Draft for rework
5. **Frontend UI:** Unified Change Order Modal with workflow stepper, action buttons, and step details

**Key Assumptions:**
- Backend workflow service already implemented (`ChangeOrderWorkflowService`)
- Backend merge endpoint exists (`POST /change-orders/{id}/merge`)
- Phase 3 (Impact Analysis) is complete
- RBAC permissions are defined (`change-order-update` for merge)

### Decisions Made

| Question | Decision |
| :--- | :--- |
| **Transition Comments** | Optional comment field for all status transitions (Submit, Approve, Reject, Merge) - not mandatory but captured for audit trail |
| **Merge Conflicts** | Block merge and display conflicts to user - must be resolved before merge can proceed |
| **Approved → Implemented** | Automatic transition after successful merge (no manual status change required) |
| **Notifications** | Toast notifications sufficient (no WebSocket required) |
| **UI Pattern** | Unified Change Order Modal (not separate page) with workflow stepper + action buttons + step details |

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

### Option 1: Workflow Action Buttons with Confirmation Modals

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

### Option 3: Unified Change Order Modal with Workflow Stepper (CHOSEN)

**Architecture & Design:**
- Unified modal that opens when user clicks on a Change Order
- Contains three main sections:
  1. **Change Order Details**: Title, description, creator, timestamps, branch info
  2. **Workflow Indicator & Actions**: Visual stepper showing current status, action buttons for available transitions
  3. **Step Details**: Dynamic content based on current workflow step (impact analysis, affected entities, metrics)

**Component Structure:**

```typescript
features/change-orders/components/
├── ChangeOrderModal.tsx              // Main modal container with tabs/sections
├── WorkflowStepper.tsx               // Visual workflow progress indicator
├── WorkflowButtons.tsx               // Encapsulated action buttons component
├── WorkflowTransitionModal.tsx       // Comment input for status transitions
├── MergeConfirmationModal.tsx        // Merge confirmation with conflict display
├── ChangeOrderDetailsSection.tsx     // CO metadata display
├── StepDetailsSection.tsx            // Dynamic step content renderer
└── BranchLockIndicator.tsx           // Visual lock status indicator

// Modified components
├── ChangeOrderList.tsx               // Click opens modal instead of navigation
└── useWorkflowActions.ts             // Hook for workflow operations
```

**UX Flow:**
1. User clicks on a Change Order in the list
2. Modal opens with three sections:
   - **Header**: CO title + status badge + branch lock indicator
   - **Left Panel**: Workflow stepper + action buttons
   - **Right Panel/Content Area**: Tabbed content (Details / Impact / Entities / Audit Trail)
3. User can perform workflow actions directly in modal
4. Modal updates in real-time as actions complete

**Modal Content by Workflow Step:**

| Status | Stepper State | Action Buttons | Step Details Content |
| :--- | :--- | :--- | :--- |
| **Draft** | Step 1 active | `Submit for Approval` | - Change description<br>- Affected entities list<br>- Impact metrics preview |
| **Submitted for Approval** | Step 2 active | `Start Review` | - Submission details<br>- Pending reviewer assignment<br>- Read-only entity changes |
| **Under Review** | Step 3 active | `Approve`, `Reject` | - Full impact analysis<br>- Entity change summary<br>- Cost/benefit metrics<br>- Reviewer comments |
| **Approved** | Step 4 active | `Merge` (shows conflicts if any) | - Merge preview<br>- Conflict list (if any)<br>- Target branch comparison<br>- Final impact summary |
| **Rejected** | Step 3 error | `Reopen for Approval` | - Rejection reason<br>- Feedback comments<br>- Required fixes |
| **Implemented** | Step 5 complete | (No actions) | - Merge confirmation<br>- Final entity states<br>- Audit trail<br>- Links to affected entities |

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| **Pros** | - All workflow info in one place<br>- Clear visual progression<br>- No page navigation needed<br>- Context maintained throughout<br>- Easier to show conflicts/metrics |
| **Cons** | - Larger modal (may be overwhelming)<br>- Requires careful layout design<br>- More state management in modal |
| **Complexity** | Medium |
| **Maintainability** | High (encapsulated components) |
| **Performance** | Good (single modal, no navigation) |

---

## Comparison Summary

| Criteria | Option 1 (Action Buttons) | Option 2 (Inline Dropdown) | Option 3 (Unified Modal) ⭐ |
| :--- | :--- | :--- | :--- |
| **Development Effort** | Medium (2-3 days) | Low (1-2 days) | Medium (2-3 days) |
| **UX Clarity** | High (explicit actions) | Medium (implicit effects) | High (visual stepper + contextual) |
| **Discoverability** | High (buttons visible) | Low (hidden in dropdown) | High (workflow path shown) |
| **Flexibility** | High (easy to customize) | Low (tied to dropdown) | High (step-based content) |
| **Best For** | Production systems | Rapid prototypes | Production workflows |

---

## Recommendation

**Option 3 (Unified Change Order Modal) is chosen for implementation.**

**Justification:**

1. **Single Source of Truth:** All workflow information in one modal - no navigation needed
2. **Clear Visual Progression:** Stepper component shows exactly where the CO is in the workflow
3. **Context-Rich Actions:** Action buttons are displayed alongside relevant step details
4. **Efficient User Flow:** Click list item → modal opens → perform action → close (no page loads)
5. **Better Information Architecture:** Step-specific content (impact analysis, conflicts, metrics) shown contextually
6. **Encapsulated Components:** `WorkflowButtons` component can be reused elsewhere if needed
7. **Conflict Visibility:** Merge conflicts can be displayed prominently before user attempts merge

**Implementation Plan:**

1. **Backend** (mostly complete, may need additions):
   - ✅ `ChangeOrderWorkflowService` with state transitions
   - ✅ Branch locking on status change
   - ✅ Merge endpoint
   - ⚠️ Add merge conflict detection to `BranchableService.merge_branch()`
   - ⚠️ Add optional comment field to status transition endpoint
   - ⚠️ Return conflict details in merge response

2. **Frontend** (to implement):
   - `ChangeOrderModal` - Main modal with layout
   - `WorkflowStepper` - Visual progress indicator (5 steps)
   - `WorkflowButtons` - Encapsulated action buttons component
   - `WorkflowTransitionModal` - Comment input for transitions
   - `MergeConfirmationModal` - Shows conflicts, blocks merge if conflicts exist
   - `StepDetailsSection` - Dynamic content based on workflow step
   - Update `ChangeOrderList` to open modal on row click
   - `useWorkflowActions` hook for workflow operations
   - Toast notifications for feedback

---

## Detailed Design for Chosen Option

### User Experience Flow

```
1. User clicks on Change Order row in list
   └─> Opens ChangeOrderModal
       ├─> Header: Title, Status Badge, Branch Lock Indicator
       ├─> Left Panel: Workflow Stepper + WorkflowButtons
       └─> Right Panel: Tabbed content (Details / Impact / Entities / Audit)

2. User reviews workflow status in stepper
   └─> Current step highlighted
       └─> Previous steps: completed (green)
           └─> Future steps: disabled

3. User clicks action button (e.g., "Submit for Approval")
   └─> Opens WorkflowTransitionModal
       ├─> Shows transition being performed
       ├─> Optional comment input (TextArea)
       └─> Confirm/Cancel buttons

4. On confirm:
   └─> API call to update status
       ├─> Success: Toast notification, modal updates, stepper advances
       └─> Error: Toast notification with error message, modal stays open

5. For Merge (when Approved):
   └─> Opens MergeConfirmationModal
       ├─> Checks for conflicts first
       ├─> If conflicts: Shows conflict list, blocks merge
       └─> If no conflicts: Shows merge preview, allows confirm
           └─> On merge: Status auto-transitions to "Implemented"
```

---

### Component: ChangeOrderModal

**Purpose:** Main modal container that orchestrates all CO information and workflow actions

**Props:**
```typescript
interface ChangeOrderModalProps {
  changeOrderId: string;
  open: boolean;
  onClose: () => void;
}

interface ChangeOrderPublic {
  change_order_id: string;
  project_id: string;
  title: string;
  description: string;
  status: ChangeOrderStatus;
  branch_name: string;
  branch_locked: boolean;
  available_transitions: string[];
  can_edit_status: boolean;
  created_at: string;
  created_by: UserPublic;
  updated_at: string;
  // Impact analysis data (populated from Phase 3)
  impact_summary?: ImpactSummary;
  affected_entities?: AffectedEntity[];
  merge_conflicts?: MergeConflict[];
}
```

**Layout Structure:**
```typescript
export const ChangeOrderModal: React.FC<ChangeOrderModalProps> = ({
  changeOrderId,
  open,
  onClose,
}) => {
  const { data: changeOrder, isLoading } = useChangeOrder(changeOrderId);
  const [activeTab, setActiveTab] = useState("details");

  if (isLoading) return <Modal open={open} footer={null}><Spin /></Modal>;

  return (
    <Modal
      title={
        <Space>
          <span>{changeOrder?.title}</span>
          <StatusBadge status={changeOrder?.status} />
          <BranchLockIndicator locked={changeOrder?.branch_locked} />
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={1000}
      footer={null}
    >
      <Row gutter={16}>
        {/* Left Panel: Workflow */}
        <Col span={8}>
          <Card title="Workflow">
            <WorkflowStepper status={changeOrder?.status} />
            <Divider />
            <WorkflowButtons
              changeOrder={changeOrder}
              onSuccess={() => {
                // Refetch CO data to update modal
                queryClient.invalidateQueries(["change-order", changeOrderId]);
              }}
            />
          </Card>
        </Col>

        {/* Right Panel: Details */}
        <Col span={16}>
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <Tabs.TabPane tab="Details" key="details">
              <ChangeOrderDetailsSection changeOrder={changeOrder} />
            </Tabs.TabPane>
            <Tabs.TabPane tab="Impact Analysis" key="impact">
              <StepDetailsSection
                status={changeOrder?.status}
                impactData={changeOrder?.impact_summary}
              />
            </Tabs.TabPane>
            <Tabs.TabPane tab="Affected Entities" key="entities">
              <AffectedEntitiesList entities={changeOrder?.affected_entities} />
            </Tabs.TabPane>
            <Tabs.TabPane tab="Audit Trail" key="audit">
              <AuditTrail changeOrderId={changeOrderId} />
            </Tabs.TabPane>
          </Tabs>
        </Col>
      </Row>
    </Modal>
  );
};
```

---

### Component: WorkflowStepper

**Purpose:** Visual progress indicator showing current workflow state

**Implementation:**
```typescript
interface WorkflowStepperProps {
  status: ChangeOrderStatus;
}

const WORKFLOW_STEPS = [
  { title: "Draft", status: "Draft" },
  { title: "Submitted", status: "Submitted for Approval" },
  { title: "Under Review", status: "Under Review" },
  { title: "Approved", status: "Approved" },
  { title: "Implemented", status: "Implemented" },
];

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({ status }) => {
  const getCurrentIndex = () => {
    return WORKFLOW_STEPS.findIndex((step) => step.status === status);
  };

  const currentIndex = getCurrentIndex();

  return (
    <Steps
      current={currentIndex}
      direction="vertical"
      size="small"
    >
      {WORKFLOW_STEPS.map((step, index) => (
        <Steps.Step
          key={step.status}
          title={step.title}
          status={
            index < currentIndex
              ? "finish"
              : index === currentIndex
              ? "process"
              : "wait"
          }
        />
      ))}
    </Steps>
  );
};
```

---

### Component: WorkflowButtons

**Purpose:** Encapsulated component for workflow action buttons with all transition logic

**Props:**
```typescript
interface WorkflowButtonsProps {
  changeOrder: ChangeOrderPublic;
  onSuccess?: () => void;
}
```

**Implementation:**
```typescript
export const WorkflowButtons: React.FC<WorkflowButtonsProps> = ({
  changeOrder,
  onSuccess,
}) => {
  const {
    transition,
    merge,
    isTransitioning,
    isMerging,
  } = useWorkflowActions(changeOrder.change_order_id);

  const { available_transitions, can_edit_status, branch_locked } = changeOrder;

  // Handle status transition with optional comment
  const handleTransition = async (newStatus: string) => {
    const modal = Modal.confirm({
      title: `Change status to "${newStatus}"?`,
      content: (
        <WorkflowTransitionContent
          targetStatus={newStatus}
          onCommentChange={(comment) => {
            // Store comment for submission
          }}
        />
      ),
      onOk: async () => {
        await transition({ status: newStatus, comment: comment });
        onSuccess?.();
      },
    });
  };

  // Handle merge with conflict check
  const handleMerge = async () => {
    // First check for conflicts
    const conflicts = await checkMergeConflicts(changeOrder.change_order_id);

    if (conflicts && conflicts.length > 0) {
      // Show conflicts, block merge
      Modal.error({
        title: "Merge Conflicts Detected",
        content: <MergeConflictsList conflicts={conflicts} />,
        width: 800,
      });
      return;
    }

    // No conflicts, show merge confirmation
    Modal.confirm({
      title: "Merge Change Order?",
      content: (
        <MergeConfirmationContent
          sourceBranch={changeOrder.branch_name}
          targetBranch="main"
          impactSummary={changeOrder.impact_summary}
        />
      ),
      onOk: async () => {
        await merge("main");
        onSuccess?.();
      },
      okText: "Merge",
      okButtonProps: { danger: true },
    });
  };

  // Show merge button if Approved
  if (changeOrder.status === "Approved") {
    return (
      <Button
        type="primary"
        onClick={handleMerge}
        loading={isMerging}
        disabled={!can_edit_status}
        block
      >
        Merge to Main
      </Button>
    );
  }

  // Show action buttons for available transitions
  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      {available_transitions.map((nextStatus) => (
        <Button
          key={nextStatus}
          type={getButtonType(nextStatus)}
          onClick={() => handleTransition(nextStatus)}
          disabled={!can_edit_status}
          loading={isTransitioning}
          block
        >
          {getButtonLabel(nextStatus)}
        </Button>
      ))}
    </Space>
  );
};

// Helper functions
const getButtonType = (status: string): "primary" | "default" | "dashed" => {
  if (status === "Approved") return "primary";
  if (status === "Rejected") return "default";
  return "default";
};

const getButtonLabel = (status: string): string => {
  const labels: Record<string, string> = {
    "Submitted for Approval": "Submit for Review",
    "Under Review": "Start Review",
    "Approved": "Approve",
    "Rejected": "Reject",
    "Implemented": "Merge",
  };
  return labels[status] || status;
};
```

---

### Component: WorkflowTransitionModal (inline content)

**Purpose:** Content for status transition modal with optional comment

**Implementation:**
```typescript
interface WorkflowTransitionContentProps {
  targetStatus: string;
  onCommentChange: (comment: string) => void;
}

export const WorkflowTransitionContent: React.FC<WorkflowTransitionContentProps> = ({
  targetStatus,
  onCommentChange,
}) => {
  const [comment, setComment] = useState("");

  useEffect(() => {
    onCommentChange(comment);
  }, [comment]);

  return (
    <div>
      <p>
        This will transition the Change Order to <strong>{targetStatus}</strong>.
      </p>
      <p style={{ marginTop: 16, marginBottom: 8 }}>
        Add a comment (optional):
      </p>
      <TextArea
        rows={3}
        placeholder="Explain your decision..."
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={500}
        showCount
      />
    </div>
  );
};
```

---

### Component: MergeConfirmationModal (inline content)

**Purpose:** Merge confirmation with conflict display

**Implementation:**
```typescript
interface MergeConfirmationContentProps {
  sourceBranch: string;
  targetBranch: string;
  impactSummary?: ImpactSummary;
}

export const MergeConfirmationContent: React.FC<MergeConfirmationContentProps> = ({
  sourceBranch,
  targetBranch,
  impactSummary,
}) => {
  return (
    <div>
      <Alert
        message="This operation cannot be undone"
        description="Merging will apply all changes to the main branch and automatically transition the status to Implemented."
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="Source Branch">
          <Tag>{sourceBranch}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Target Branch">
          <Tag color="green">{targetBranch}</Tag>
        </Descriptions.Item>
        {impactSummary && (
          <>
            <Descriptions.Item label="Entities Affected">
              {impactSummary.entity_count}
            </Descriptions.Item>
            <Descriptions.Item label="Cost Impact">
              {formatCurrency(impactSummary.cost_delta)}
            </Descriptions.Item>
          </>
        )}
      </Descriptions>

      <p style={{ marginTop: 16, fontSize: 12, color: "#666" }}>
        💡 Add a comment on the next screen to document this merge.
      </p>
    </div>
  );
};
```

---

### Component: MergeConflictsList

**Purpose:** Display merge conflicts in error modal

**Implementation:**
```typescript
interface MergeConflictsListProps {
  conflicts: MergeConflict[];
}

export const MergeConflictsList: React.FC<MergeConflictsListProps> = ({
  conflicts,
}) => {
  return (
    <div>
      <p>
        The following conflicts must be resolved before merging:
      </p>
      <List
        dataSource={conflicts}
        renderItem={(conflict) => (
          <List.Item>
            <List.Item.Meta
              title={
                <Space>
                  <Tag color="red">Conflict</Tag>
                  <span>{conflict.entity_type}: {conflict.entity_name}</span>
                </Space>
              }
              description={
                <span>
                  {conflict.conflict_type} - Version {conflict.branch_version} conflicts with version {conflict.main_version}
                </span>
              }
            />
          </List.Item>
        )}
      />
      <Alert
        message="Merge Blocked"
        description="Please resolve these conflicts by rebasing or updating the change order."
        type="error"
        showIcon
        style={{ marginTop: 16 }}
      />
    </div>
  );
};
```

---

### Component: StepDetailsSection

**Purpose:** Render step-specific content based on workflow status

**Implementation:**
```typescript
interface StepDetailsSectionProps {
  status: ChangeOrderStatus;
  impactData?: ImpactSummary;
}

export const StepDetailsSection: React.FC<StepDetailsSectionProps> = ({
  status,
  impactData,
}) => {
  switch (status) {
    case "Draft":
      return <DraftStepContent impactData={impactData} />;
    case "Submitted for Approval":
      return <SubmittedStepContent />;
    case "Under Review":
      return <UnderReviewStepContent impactData={impactData} />;
    case "Approved":
      return <ApprovedStepContent impactData={impactData} />;
    case "Rejected":
      return <RejectedStepContent />;
    case "Implemented":
      return <ImplementedStepContent />;
    default:
      return <Empty description="No details available" />;
  }
};

// Step content components
const DraftStepContent: React.FC<{ impactData?: ImpactSummary }> = ({ impactData }) => (
  <div>
    <h4>Change Summary</h4>
    <p>Review the following before submitting:</p>
    {impactData && <ImpactMetricsPreview data={impactData} />}
  </div>
);

const UnderReviewStepContent: React.FC<{ impactData?: ImpactSummary }> = ({ impactData }) => (
  <div>
    <h4>Impact Analysis</h4>
    {impactData ? <FullImpactReport data={impactData} /> : <Spin />}
  </div>
);

const ApprovedStepContent: React.FC<{ impactData?: ImpactSummary }> = ({ impactData }) => (
  <div>
    <h4>Ready to Merge</h4>
    <p>This change order has been approved and is ready to be merged.</p>
    {impactData && <FinalImpactSummary data={impactData} />}
  </div>
);
```

---

### Hook: useWorkflowActions

**Purpose:** Encapsulate workflow action logic with comment support

**Implementation:**
```typescript
interface TransitionParams {
  status: string;
  comment?: string;
}

export const useWorkflowActions = (changeOrderId: string) => {
  const queryClient = useQueryClient();

  const transitionMutation = useMutation({
    mutationFn: async (params: TransitionParams) => {
      return updateChangeOrder(changeOrderId, {
        status: params.status,
        comment: params.comment,  // Optional comment for audit trail
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      queryClient.invalidateQueries({ queryKey: ["change-order", changeOrderId] });
      message.success("Status updated successfully");
    },
    onError: (error) => {
      message.error(`Failed to update status: ${error.message}`);
    },
  });

  const mergeMutation = useMutation({
    mutationFn: async (params: { targetBranch: string; comment?: string }) => {
      return mergeChangeOrder(changeOrderId, params.targetBranch, params.comment);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      queryClient.invalidateQueries({ queryKey: ["change-order", changeOrderId] });
      message.success("Change Order merged successfully");
    },
    onError: (error) => {
      message.error(`Failed to merge: ${error.message}`);
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

---

### Component: BranchLockIndicator

**Purpose:** Visual cue when CO branch is locked

**Implementation:**
```typescript
export const BranchLockIndicator: React.FC<{ locked: boolean }> = ({ locked }) => {
  if (!locked) return null;

  return (
    <Tooltip title="Branch is locked - no modifications allowed while in review">
      <LockFilled style={{ color: "#faad14", marginLeft: 8 }} />
    </Tooltip>
  );
};
```

---

## Integration with Existing Components

### ChangeOrderList Modifications

**Make Row Clickable:**

```typescript
const columns: ColumnsType<ChangeOrderPublic> = [
  // ... existing columns
  {
    title: "Title",
    dataIndex: "title",
    key: "title",
    render: (text, record) => (
      <a
        onClick={(e) => {
          e.stopPropagation();
          openChangeOrderModal(record.change_order_id);
        }}
      >
        {text}
      </a>
    ),
  },
  // ... other columns
];

// Add onRow handler to entire table
<Table
  columns={columns}
  dataSource={changeOrders}
  onRow={(record) => ({
    onClick: () => openChangeOrderModal(record.change_order_id),
    style: { cursor: "pointer" },
  })}
/>
```

**State Management for Modal:**

```typescript
export const ChangeOrderList: React.FC = () => {
  const [selectedCoId, setSelectedCoId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const openChangeOrderModal = (id: string) => {
    setSelectedCoId(id);
    setIsModalOpen(true);
  };

  return (
    <>
      <Table
        // ... table config
        onRow={(record) => ({
          onClick: () => openChangeOrderModal(record.change_order_id),
        })}
      />

      <ChangeOrderModal
        changeOrderId={selectedCoId}
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
};
```

### Optional: WorkflowButtons in List View

For quick actions without opening modal, add action column:

```typescript
{
  title: "Actions",
  key: "quick-actions",
  width: 120,
  render: (_, record) => (
    <WorkflowButtons
      changeOrder={record}
      onSuccess={() => refetch()}
      compact  // Use compact variant for list view
    />
  ),
}
```

---

## Backend Considerations

### Merge Conflict Detection

**Current Status:** Needs implementation

**Required Changes:**

1. **Add Conflict Detection to `BranchableService.merge_branch()`:**

```python
async def merge_branch(
    self,
    entity_id: UUID,
    source_branch: str,
    target_branch: str,
    actor_id: UUID,
) -> Tuple[T, List[MergeConflict]]:
    """Merge branch and return (merged_entity, conflicts)."""
    # Check for conflicts by comparing versions
    conflicts = await self._detect_merge_conflicts(
        entity_id, source_branch, target_branch
    )

    if conflicts:
        # Return conflicts without merging
        raise MergeConflictError(conflicts=conflicts)

    # No conflicts, proceed with merge
    merged = await self._execute_merge(
        entity_id, source_branch, target_branch, actor_id
    )
    return merged, []
```

2. **Add Conflict Response to Merge Endpoint:**

```python
@router.post("/{change_order_id}/merge")
async def merge_change_order(
    change_order_id: UUID,
    merge_request: MergeRequest,  # Includes optional comment
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderResponse:
    """
    Merge a Change Order's branch into target branch.
    Returns conflict details if merge is blocked.
    """
    try:
        result = await service.merge_change_order(
            change_order_id=change_order_id,
            actor_id=current_user.user_id,
            target_branch=merge_request.target_branch,
            comment=merge_request.comment,  # Optional audit comment
        )
        return result
    except MergeConflictError as e:
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": "merge_conflicts",
                "conflicts": [c.dict() for c in e.conflicts],
            },
        )
```

3. **Add Conflict Check Endpoint:**

```python
@router.get("/{change_order_id}/merge-conflicts")
async def check_merge_conflicts(
    change_order_id: UUID,
    target_branch: str = Query("main"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> List[MergeConflict]:
    """Check for merge conflicts without executing merge."""
    return await service.check_merge_conflicts(
        change_order_id=change_order_id,
        target_branch=target_branch,
    )
```

### Optional Comment for Transitions

**Current Status:** Needs implementation

**Required Changes:**

1. **Add `comment` Field to `ChangeOrderUpdate` Schema:**

```python
class ChangeOrderUpdate(BaseModel):
    status: Optional[ChangeOrderStatus] = None
    comment: Optional[str] = None  # Optional audit comment
```

2. **Store Comments in Audit Trail:**

```python
# Create audit log entry for status changes
audit_entry = ChangeOrderAuditLog(
    change_order_id=change_order_id,
    old_status=old_status,
    new_status=new_status,
    comment=comment,  # Store optional comment
    actor_id=actor_id,
    timestamp=datetime.utcnow(),
)
```

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

## Decisions Summary

All design questions have been resolved. See [Decisions Made](#decisions-made) section above for details.

Key decisions:
- Optional comment field for all status transitions (Submit, Approve, Reject, Merge)
- Merge conflicts block merge and display conflicts to user
- Approved → Implemented transition is automatic after successful merge
- Toast notifications are sufficient (no WebSocket required)
- Unified Change Order Modal (not separate page) with workflow stepper

---

## Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Users can click Change Order in list to open modal
- [ ] Modal displays CO details, workflow stepper, and action buttons
- [ ] Users can submit CO for review (Draft → Submitted) with optional comment
- [ ] Branch locks automatically on submit
- [ ] Users can approve/reject submitted COs with optional comment
- [ ] Users can merge approved COs to main
- [ ] Merge checks for conflicts first and blocks if conflicts exist
- [ ] Merge shows confirmation with impact summary
- [ ] Successful merge auto-transitions status to "Implemented"
- [ ] Rejecting CO returns to Draft with unlock
- [ ] Lock indicator visible when branch is locked
- [ ] Action buttons respect RBAC permissions

**Technical Criteria:**

- [ ] All status transitions validated by backend workflow service
- [ ] Frontend type safety (TypeScript strict mode)
- [ ] Zero ESLint errors
- [ ] TanStack Query cache invalidated on status change
- [ ] Error handling for failed transitions
- [ ] Loading states during async operations
- [ ] Optional comment stored in audit trail for all transitions

**Business Criteria:**

- [ ] Full audit trail (who changed status, when, optional comment)
- [ ] Irreversible operations require confirmation
- [ ] Workflow rules enforced server-side
- [ ] Branch isolation maintained during merge
- [ ] Merge conflicts prevent merge until resolved

---

## Definition of Done

**Phase 4 is complete when:**

- [ ] All acceptance criteria in Success Criteria are met
- [ ] Backend: Merge conflict detection implemented
- [ ] Backend: Optional comment field added to status transition endpoint
- [ ] Backend: Conflict check endpoint added
- [ ] Frontend: ChangeOrderModal implemented with all sections
- [ ] Frontend: WorkflowStepper component implemented
- [ ] Frontend: WorkflowButtons component implemented with all logic
- [ ] Frontend: WorkflowTransitionModal for status transitions with optional comment
- [ ] Frontend: MergeConfirmationModal with conflict display
- [ ] Frontend: StepDetailsSection with dynamic content per workflow step
- [ ] Frontend: ChangeOrderList updated to open modal on row click
- [ ] Frontend: TypeScript strict mode passes, ESLint passes
- [ ] Unit Tests: All components and hooks tested
- [ ] E2E Tests: Full workflow (Draft → Submit → Approve → Merge)
- [ ] E2E Tests: Merge conflict blocking
- [ ] Code reviewed and merged
- [ ] Documentation updated (ADR if needed)
- [ ] Demo: Complete workflow from Draft to Implemented

---

## User Experience Walkthrough

### Complete Workflow Example

**Scenario:** Project Manager wants to submit a Change Order for approval and get it merged.

**Step 1: Draft → Submit for Approval**

1. User clicks on Change Order "CO-001: Update WBE 3.2 Budget" in list
2. ChangeOrderModal opens showing:
   - Header: "CO-001: Update WBE 3.2 Budget" | Status: "Draft" (blue badge)
   - Left Panel: Workflow Stepper (Draft highlighted) + "Submit for Review" button
   - Right Panel: Change details
3. User reviews change in right panel
4. User clicks "Submit for Review"
5. Modal appears: "Change status to 'Submitted for Approval'?" with optional comment field
6. User enters: "Ready for review - cost increase approved by finance"
7. User clicks Confirm
8. Toast: "Status updated successfully"
9. Modal refreshes: Stepper advances to "Submitted", "Start Review" button appears

**Step 2: Under Review → Approve**

10. Reviewer opens modal, sees status "Under Review"
11. Right panel shows full impact analysis
12. Reviewer clicks "Approve"
13. Confirmation modal with optional comment
14. Reviewer enters: "Approved - impact within acceptable range"
15. Reviewer clicks Confirm
16. Modal refreshes: Stepper shows "Approved" with "Merge to Main" button

**Step 3: Approved → Merge → Implemented**

17. User clicks "Merge to Main"
18. System checks for conflicts (no conflicts found)
19. Confirmation modal shows source/target branches and impact summary
20. User clicks "Merge"
21. Merge executes, status auto-transitions to "Implemented"
22. Toast: "Change Order merged successfully"
23. Modal refreshes: Stepper shows all steps complete

**Step 4: Alternative - Merge Blocked by Conflicts**

17. User clicks "Merge to Main"
18. System checks for conflicts → CONFLICTS FOUND
19. Error modal displays conflict list and blocks merge
20. User must resolve conflicts (rebase/update CO) before retrying merge

---

## Next Steps

**Immediate Actions:**

1. Design approved - proceed to PLAN document
2. Create Phase 4 PLAN document with detailed tasks
3. Begin implementation with TDD approach

**Implementation Order:**

1. Backend changes (conflict detection, comment field)
2. Frontend components (ChangeOrderModal, WorkflowButtons)
3. Integration with ChangeOrderList
4. E2E tests

---

**Document Status:** Ready for Implementation
**Next Document:** [01-plan.md](./01-plan.md)
**Design Approved By:** Product Owner
