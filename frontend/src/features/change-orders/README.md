# Change Orders Feature

Comprehensive change order management with workflow, approval authority, and impact analysis.

## Overview

The Change Orders feature provides full lifecycle management for project change requests, including:

- Draft creation with automatic branch isolation
- Financial impact analysis
- Authority-based approval workflow
- Merge to main with conflict detection
- Complete audit trail

## Architecture

### Components

- **WorkflowActions**: Authority-aware action buttons for workflow transitions
- **WorkflowButtons**: Legacy component (being replaced by WorkflowActions)
- **ChangeOrderDetailsSection**: Display change order metadata
- **ApprovalInfo**: Display approval authority and SLA information
- **ImpactAnalysisDashboard**: Financial impact visualization

### Hooks

#### API Hooks

- **useChangeOrders**: Fetch change orders list with pagination
- **useChangeOrder**: Fetch single change order by ID
- **useCreateChangeOrder**: Create new change order with branch creation
- **useUpdateChangeOrder**: Update change order metadata
- **useDeleteChangeOrder**: Soft delete change order
- **useMergeChangeOrder**: Merge change order branch to main

#### Approval Hooks

- **useApprovalInfo**: Fetch approval information (impact level, assigned approver, user authority)
- **useSubmitForApproval**: Submit draft for approval (calculates impact, assigns approver, locks branch)
- **useApproveChangeOrder**: Approve a change order (validates authority, transitions to Approved)
- **useRejectChangeOrder**: Reject a change order (validates authority, unlocks branch)
- **useCanApprove**: Check if current user can approve a specific change order

#### Other Hooks

- **useWorkflowActions**: Legacy workflow transition actions
- **useImpactAnalysis**: Fetch financial impact analysis
- **useCheckMergeConflicts**: Check for merge conflicts before merging

## Approval Authority System

### Authority Levels

The system supports four authority levels (in order of increasing authority):

1. **LOW**: Can approve low-impact changes (< €10,000)
2. **MEDIUM**: Can approve medium-impact changes (< €50,000)
3. **HIGH**: Can approve high-impact changes (< €100,000)
4. **CRITICAL**: Can approve any change (≥ €100,000)

### Approval Flow

```
Draft → Submit for Approval → Submitted for Approval → Approve → Approved → Merge → Implemented
                                                      ↘ Reject → Rejected
```

### Authority Check Logic

The `useCanApprove` hook combines multiple checks:

1. **Permission check**: User must have `change-order-approve` permission
2. **Status check**: Change order must be in "Submitted for Approval" or "Under Review" status
3. **Backend validation**: Backend validates user authority against impact level
4. **Assigned approver check**: For some workflows, only the assigned approver can approve

Example:

```tsx
import { useCanApprove } from "@/features/change-orders/api/useCanApprove";

function MyComponent({ changeOrder }: { changeOrder: ChangeOrderPublic }) {
  const { canApprove, authorityLevel, isLoading, reason } = useCanApprove(changeOrder);

  if (isLoading) return <Spin />;

  if (!canApprove) {
    return (
      <Tooltip title={reason}>
        <Button disabled>Approve</Button>
      </Tooltip>
    );
  }

  return (
    <Button type="primary" onClick={handleApprove}>
      Approve (Level: {authorityLevel})
    </Button>
  );
}
```

## Usage Examples

### Creating a Change Order

```tsx
import { useCreateChangeOrder } from "@/features/change-orders/api/useChangeOrders";

function CreateChangeOrderForm() {
  const createMutation = useCreateChangeOrder();

  const handleSubmit = (data: ChangeOrderCreate) => {
    createMutation.mutate(data, {
      onSuccess: (co) => {
        console.log(`Created ${co.code} with branch ${co.branch}`);
      }
    });
  };

  return <ChangeOrderForm onSubmit={handleSubmit} />;
}
```

### Submitting for Approval

```tsx
import { useSubmitForApproval } from "@/features/change-orders/api/useApprovals";

function ChangeOrderActions({ changeOrder }: { changeOrder: ChangeOrderPublic }) {
  const submitMutation = useSubmitForApproval();

  const handleSubmit = () => {
    submitMutation.mutate({
      id: changeOrder.change_order_id,
      comment: "Ready for review",
    });
  };

  return (
    <Button
      type="primary"
      onClick={handleSubmit}
      loading={submitMutation.isPending}
      disabled={changeOrder.status !== "Draft"}
    >
      Submit for Approval
    </Button>
  );
}
```

### Approving a Change Order

```tsx
import { useApproveChangeOrder } from "@/features/change-orders/api/useApprovals";
import { useCanApprove } from "@/features/change-orders/api/useCanApprove";

function ApproveButton({ changeOrder }: { changeOrder: ChangeOrderPublic }) {
  const approveMutation = useApproveChangeOrder();
  const { canApprove, authorityLevel, reason } = useCanApprove(changeOrder);

  const handleApprove = () => {
    approveMutation.mutate({
      id: changeOrder.change_order_id,
      approval: { comments: "Approved within authority level" },
    });
  };

  if (!canApprove) {
    return <Button disabled>Approve</Button>;
  }

  return (
    <Button
      type="primary"
      onClick={handleApprove}
      loading={approveMutation.isPending}
    >
      Approve ({authorityLevel})
    </Button>
  );
}
```

### Using WorkflowActions Component

The `WorkflowActions` component provides a complete set of authority-aware buttons:

```tsx
import { WorkflowActions } from "@/features/change-orders/components";

function ChangeOrderDetail({ changeOrder }: { changeOrder: ChangeOrderPublic }) {
  return (
    <div>
      <ChangeOrderDetailsSection changeOrder={changeOrder} />
      <Divider />
      <WorkflowActions changeOrder={changeOrder} mode="all" />
    </div>
  );
}
```

The component automatically:

- Shows "Submit for Approval" only to the creator when status is Draft
- Shows "Approve"/"Reject" only to authorized users
- Displays authority level badges
- Disables buttons with tooltips explaining why
- Provides confirmation modals for all actions
- Collects optional comments for audit trail

## API Response Types

### ChangeOrderPublic

```typescript
type ChangeOrderPublic = {
  change_order_id: string;      // Root UUID
  id: string;                    // Version ID (primary key)
  code: string;                  // Business identifier (e.g., CO-2026-001)
  project_id: string;            // Project this change applies to
  title: string;                 // Brief title
  description?: string;          // Detailed description
  justification?: string;        // Business justification
  effective_date?: string;       // When change takes effect
  status?: string;               // Workflow state
  created_by: string;            // User who created this version
  created_at?: string;           // When this version was created
  updated_by?: string;           // User who last updated
  updated_at?: string;           // When last updated
  branch: string;                // Branch name (e.g., BR-CO-2026-001)
  parent_id?: string;            // Parent version ID
  deleted_at?: string;           // Soft delete timestamp
  available_transitions?: string[]; // Valid status transitions
  can_edit_status?: boolean;     // Whether status can be edited
  branch_locked?: boolean;       // Whether the branch is locked
};
```

### ApprovalInfoPublic

```typescript
type ApprovalInfoPublic = {
  impact_level?: string;                     // LOW/MEDIUM/HIGH/CRITICAL
  financial_impact?: {                       // Impact details
    budget_delta: number;
    revenue_delta: number;
  };
  assigned_approver?: {                      // Assigned approver details
    user_id: string;
    full_name: string;
    email: string;
    role: string;
  };
  sla_assigned_at?: string;                  // When SLA started
  sla_due_date?: string;                     // SLA deadline
  sla_status?: string;                       // pending/approaching/overdue
  sla_business_days_remaining?: number;      // Days until deadline
  user_authority_level?: string;             // Current user's level
  user_can_approve?: boolean;                // Whether user can approve
};
```

### ChangeOrderApproval

```typescript
type ChangeOrderApproval = {
  comments?: string;  // Optional comments for audit trail
};
```

## Query Keys

All change order queries use the `queryKeys.changeOrders` factory:

```typescript
import { queryKeys } from "@/api/queryKeys";

// List
queryKeys.changeOrders.list(projectId, params)

// Detail
queryKeys.changeOrders.detail(id, { asOf, approvalInfo })

// Impact
queryKeys.changeOrders.impact(id)

// Merge conflicts
queryKeys.changeOrders.mergeConflicts(id, sourceBranch, targetBranch)
```

## Testing

```tsx
import { render, screen } from "@testing-library/react";
import { QueryClientWrapper } from "@/test-utils";
import { WorkflowActions } from "./WorkflowActions";

describe("WorkflowActions", () => {
  it("shows submit button for draft change order creator", () => {
    const changeOrder = {
      ...mockChangeOrder,
      status: "Draft",
      created_by: "user-123",
    };

    render(
      <QueryClientWrapper>
        <WorkflowActions changeOrder={changeOrder} mode="all" />
      </QueryClientWrapper>
    );

    expect(screen.getByText("Submit for Approval")).toBeInTheDocument();
  });

  it("hides approve button for unauthorized users", () => {
    const changeOrder = {
      ...mockChangeOrder,
      status: "Submitted for Approval",
    };

    render(
      <QueryClientWrapper>
        <WorkflowActions changeOrder={changeOrder} mode="all" />
      </QueryClientWrapper>
    );

    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
  });
});
```

## Error Handling

All mutations include error handling with toast notifications:

```typescript
// Success
toast.success(`Change Order ${data.code} approved successfully`);

// Error
toast.error(`Error approving change order: ${error.message}`);
```

For custom error handling, use the `onError` callback:

```typescript
const approveMutation = useApproveChangeOrder({
  onError: (error) => {
    message.error(`Failed to approve: ${error.message}`);
    // Custom error handling logic
  }
});
```

## Best Practices

1. **Always use WorkflowActions component** instead of manual buttons for consistency
2. **Check authority before showing approve/reject buttons** using `useCanApprove`
3. **Invalidate queries** after mutations to keep UI in sync
4. **Provide comments** for approve/reject actions for audit trail
5. **Handle loading states** to prevent duplicate submissions
6. **Use confirmation modals** for destructive actions (reject, merge)

## Migration from Legacy Code

If you're using the old `WorkflowButtons` component:

```tsx
// Old
import { WorkflowButtons } from "@/features/change-orders/components";
<WorkflowButtons changeOrder={changeOrder} mode="all" />

// New
import { WorkflowActions } from "@/features/change-orders/components";
<WorkflowActions changeOrder={changeOrder} mode="all" />
```

The new `WorkflowActions` component includes:

- Authority-based visibility (only shows buttons user can use)
- Authority level badges on approve/reject buttons
- Disabled state with tooltips for unauthorized users
- Proper integration with backend approval API

## Future Enhancements

- Bulk approval for multiple change orders
- Delegation of approval authority
- Approval workflow customization per project
- Email notifications for approval requests
- Approval history trail with comments
