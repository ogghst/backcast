# Workflow UI Integration - ANALYSIS

**Date Created:** 2026-01-13
**Epic:** E006 (Branching & Change Order Management)
**Iteration:** Workflow UI - Frontend Workflow State Management
**Status:** Analysis Phase
**Related Docs:**
- [Frontend Integration Plan](../frontend-integration/01-plan.md)
- [Phase 2 Backend Implementation](../phase2/01-plan.md)
- [Product Backlog](../../../product-backlog.md)

---

## 1. Problem Identification

### Issue Summary

**User Observation:** The Change Order creation form shows all 7 possible workflow states instead of only the initial state ("Draft"). The workflow state management is implemented in the backend (`ChangeOrderWorkflowService`) but not enforced in the frontend UI.

**Current Behavior:**
- [`ChangeOrderModal.tsx`](../../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx#L21-L29) shows all status options: Draft, Submitted, Under Review, Approved, Rejected, Implemented, Closed
- Users can select any status regardless of whether it's a valid transition
- Backend rejects invalid transitions with error, but UI allows the selection
- Status field is not disabled when `can_edit_on_status()` returns false

**Expected Behavior:**
- On **create**: Only "Draft" should be available (or field disabled)
- On **edit**: Only show valid transitions from current status via `get_available_transitions()`
- Disable status field when workflow state doesn't allow editing

### Root Cause

1. **Frontend-Backend Disconnect:** Frontend has hardcoded status options independent of backend workflow rules
2. **No API Integration:** Frontend doesn't call backend workflow service for available transitions
3. **Missing Validation:** No client-side enforcement of workflow rules before form submission

### Impact

| Impact Area | Severity | Description |
|------------|----------|-------------|
| **User Experience** | High | Confusing UI with invalid options, errors after submission |
| **Data Integrity** | Medium | Backend validates, but users can waste time on invalid selections |
| **Workflow Enforcement** | Medium | Branch locking happens but UI doesn't guide users through valid states |

---

## 2. Documentation Review

### E06-U06 Current Scope (from Phase 2 Plan)

From [`../phase2/01-plan.md`](../phase2/01-plan.md#L230-L239):

**E06-U06: Lock/Unlock Branches**
- ✅ `branches` table with composite PK (name, project_id) and `locked` boolean
- ✅ `change_orders` table - add `branch_name` column
- ✅ `Branch` domain model and `BranchService` (lock/unlock operations)
- ✅ Branch API routes (`/api/v1/branches/`)
- ✅ CRITICAL FIX: `ChangeOrderService.create_change_order()` - create branch in SAME transaction
- ✅ MODIFY: `ChangeOrderService.update_change_order()` - trigger branch lock/unlock on status change
- ✅ MODIFY: `BranchSelector` - add lock icon indicators
- ⚠️ **MISSING:** Frontend workflow-aware status dropdown (this gap)

### Backend Workflow Service (Already Implemented)

From [`../phase2/01-plan.md`](../phase2/01-plan.md#L812-L1103):

**`ChangeOrderWorkflowService` Interface:**
```python
async def get_available_transitions(self, current: str) -> List[str]:
    """Get all valid status transitions from the current state."""

async def can_edit_on_status(self, status: str) -> bool:
    """Determine if Change Order details can be edited in this status."""

async def is_valid_transition(self, from_status: str, to_status: str) -> bool:
    """Validate if a status transition is allowed."""
```

**Workflow States:**
```
Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented
```

**Transition Rules:**
- `Draft` → `Submitted for Approval`: **LOCKS** branch
- `Under Review` → `Approved`: Branch remains **LOCKED**
- `Under Review` → `Rejected`: **UNLOCKS** branch
- `Rejected` → `Submitted for Approval`: **LOCKS** branch again

### Functional Requirements Alignment

**FR-8.3 (Change Order Approval Workflow):**
> "The system shall track change order status through defined workflow states including draft, submitted for approval, under review, approved, rejected, and implemented."

**Gap:** UI doesn't enforce or guide users through these states.

---

## 3. Gap Analysis

### Current Implementation vs. Requirements

| Requirement | Backend | Frontend | Gap |
|------------|---------|----------|-----|
| **Workflow state machine** | ✅ `ChangeOrderWorkflowService` | ❌ No equivalent | Frontend needs workflow awareness |
| **Valid transitions** | ✅ `get_available_transitions()` | ❌ Hardcoded list | Need API call or sync |
| **Edit permissions** | ✅ `can_edit_on_status()` | ❌ Always enabled | Need conditional disabling |
| **Status on create** | ✅ Defaults to "Draft" | ⚠️ Shows all options | Should be "Draft" only or disabled |
| **Status on edit** | ✅ Validates transitions | ❌ Shows all options | Should filter by current status |
| **Branch lock indicators** | ✅ `branches.locked` field | ⚠️ In BranchSelector | Need in ChangeOrderModal |

### API Requirements

**New Endpoint Needed:**
```http
GET /api/v1/change-orders/{id}/workflow/available-transitions
```

**Response:**
```json
{
  "current_status": "Draft",
  "available_transitions": ["Submitted for Approval"],
  "can_edit": true,
  "is_locked": false
}
```

**Alternative:** Use existing `GET /api/v1/change-orders/{id}` and add workflow info to response (preferred - no new endpoint)

---

## 4. Solution Options

### Option A: Quick Fix (Create Only)

**Approach:** Disable status field on create, show only "Draft"

**Pros:**
- Minimal code change (1 line)
- Fixes the immediate confusion
- No backend changes needed

**Cons:**
- Doesn't solve edit workflow
- No guidance on valid transitions
- Field appears disabled without explanation

**Effort:** 15 minutes

---

### Option B: API Integration (Full Workflow)

**Approach:**
1. Add `available_transitions` field to ChangeOrder schema response
2. Create `useWorkflowTransitions()` hook
3. Update `ChangeOrderModal` to use dynamic options
4. Disable status field when `can_edit` is false
5. Add visual indicators for locked branches

**Pros:**
- Complete workflow enforcement in UI
- Guides users through valid states
- Prevents invalid selections before submission
- Aligns with backend implementation

**Cons:**
- Requires backend schema update
- More complex implementation
- Additional testing needed

**Effort:** 3-4 hours

---

### Option C: Hybrid (Frontend State Machine)

**Approach:** Duplicate workflow rules in TypeScript

**Pros:**
- No backend changes needed
- Fast implementation
- Full UI control

**Cons:**
- **DANGER:** Frontend and backend can diverge
- Double maintenance burden
- Violates DRY principle

**Effort:** 2-3 hours

**Recommendation:** ❌ **DO NOT USE** - High maintenance risk

---

### Recommended Approach: **Option B - API Integration**

**Justification:**
1. **Single Source of Truth:** Backend `ChangeOrderWorkflowService` remains authoritative
2. **Future-Proof:** Workflow changes automatically reflected in UI
3. **Complete Solution:** Handles create, edit, and lock states
4. **Aligns with Architecture:** Frontend displays what backend allows
5. **Scalable:** Easy to extend with additional workflow rules

---

## 5. Technical Design

### Backend Changes

**1. Update ChangeOrder Schema**

File: [`backend/app/models/schemas/change_order.py`](../../../../backend/app/models/schemas/change_order.py)

```python
@dataclass
class ChangeOrderPublic:
    # ... existing fields ...
    available_transitions: List[str] | None = None  # NEW
    can_edit_status: bool = True  # NEW
    branch_locked: bool = False  # NEW
```

**2. Update ChangeOrderService**

File: [`backend/app/services/change_order_service.py`](../../../../backend/app/services/change_order_service.py)

```python
def _to_public(self, co: ChangeOrder) -> ChangeOrderPublic:
    """Convert to public schema with workflow information."""
    # Get available transitions
    transitions = await self.workflow.get_available_transitions(co.status)
    can_edit = await self.workflow.can_edit_on_status(co.status)

    # Check if branch is locked
    branch_locked = False
    if co.branch_name:
        try:
            branch = await self.branch_service.get_by_name_and_project(
                co.branch_name, co.project_id
            )
            branch_locked = branch.locked
        except NoResultFound:
            pass

    return ChangeOrderPublic(
        # ... existing fields ...
        available_transitions=transitions,
        can_edit_status=can_edit,
        branch_locked=branch_locked,
    )
```

### Frontend Changes

**1. Update Generated Types**

```bash
cd frontend && npm run generate-client
```

**2. Create Workflow Hook**

File: `frontend/src/features/change-orders/hooks/useWorkflowInfo.ts`

```typescript
import { computed } from "react";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

export function useWorkflowInfo(
  currentStatus?: string,
  availableTransitions?: string[],
  canEdit?: boolean,
  isLocked?: boolean
) {
  const { selectedBranch } = useTimeMachineStore();

  const statusOptions = computed(() => {
    if (!currentStatus) {
      // Create mode: only Draft
      return [{ label: "Draft", value: "Draft" }];
    }

    // Edit mode: filter by available transitions
    return (availableTransitions || []).map((status) => ({
      label: status,
      value: status,
    }));
  });

  const isStatusDisabled = computed(() => {
    // Disabled if cannot edit OR branch is locked
    return !canEdit || isLocked;
  });

  const isLocked = computed(() => {
    return isLocked && selectedBranch !== "main";
  });

  return {
    statusOptions,
    isStatusDisabled,
    isLocked,
  };
}
```

**3. Update ChangeOrderModal**

File: [`frontend/src/features/change-orders/components/ChangeOrderModal.tsx`](../../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx)

```typescript
// Replace static CHANGE_ORDER_STATUS_OPTIONS with:
const { statusOptions, isStatusDisabled, isLocked } = useWorkflowInfo(
  isEdit ? initialValues?.status : undefined,
  initialValues?.available_transitions,
  initialValues?.can_edit_status,
  initialValues?.branch_locked
);

// In Form.Item:
<Form.Item
  name="status"
  label="Status"
  tooltip={isLocked ? "Branch is locked - status cannot be changed" : undefined}
>
  <Select
    options={statusOptions}
    disabled={isStatusDisabled}
  />
</Form.Item>

// Add locked branch warning:
{isLocked && (
  <Alert
    type="warning"
    message="Branch Locked"
    description="This change order is under review. No modifications are allowed."
  />
)}
```

---

## 6. Success Criteria

### Functional Requirements

- [ ] **Create Mode:** Status dropdown shows only "Draft" (or is disabled)
- [ ] **Edit Mode:** Status dropdown shows only valid transitions from current state
- [ ] **Locked Branch:** Status field disabled when branch is locked
- [ ] **Visual Feedback:** Warning message when working on locked branch
- [ ] **Error Prevention:** Users cannot select invalid workflow states

### Technical Requirements

- [ ] Backend ChangeOrder schema includes workflow metadata
- [ ] Frontend uses `useWorkflowInfo` hook for status options
- [ ] No hardcoded status values in frontend
- [ ] TypeScript strict mode (zero errors)
- [ ] ESLint clean (zero warnings)

### User Experience

- [ ] Clear indication of why status field is disabled
- [ ] Workflow states match backend rules exactly
- [ ] No confusing invalid options
- [ ] Smooth transition between states

---

## 7. Implementation Plan

### Phase 1: Backend (1 hour)

1. **Update ChangeOrderPublic Schema**
   - Add `available_transitions: List[str]`
   - Add `can_edit_status: bool`
   - Add `branch_locked: bool`

2. **Update ChangeOrderService**
   - Add `_to_public()` method with workflow info
   - Call `get_available_transitions()`
   - Call `can_edit_on_status()`
   - Check branch lock status

3. **Test Backend**
   - Unit test for `_to_public()` with each status
   - Verify transitions are correct
   - Verify lock status is accurate

### Phase 2: Frontend (2 hours)

1. **Regenerate Types**
   - Run `npm run generate-client`
   - Verify new fields in ChangeOrderPublic

2. **Create useWorkflowInfo Hook**
   - Implement status options computation
   - Implement disabled state logic
   - Add TypeScript types

3. **Update ChangeOrderModal**
   - Replace static options with dynamic
   - Add disabled state
   - Add locked branch warning
   - Update form validation

4. **Test Frontend**
   - Manual testing of create flow
   - Manual testing of edit flow
   - Verify status options update correctly

### Phase 3: Integration (30 minutes)

1. **End-to-End Testing**
   - Create CO → verify status is Draft
   - Edit CO → verify only valid transitions shown
   - Submit for approval → verify branch locks
   - Try editing locked CO → verify disabled

2. **Documentation**
   - Update CHANGELOG.md
   - Update user guide (if needed)

---

## 8. Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| **Breaking Change** | Schema update affects existing API consumers | Low | Medium | Make fields optional with defaults |
| **Performance** | Additional workflow queries slow down API | Low | Low | Workflow is in-memory, fast |
| **Frontend Sync** | Generated types don't update correctly | Medium | Medium | Manual verification step |
| **Edge Cases** | Unhandled workflow states | Low | Low | Comprehensive testing |

---

## 9. Effort Estimation

### Time Breakdown

| Task | Hours |
|------|-------|
| **Backend Development** | 1.0 |
| - Schema update | 0.3 |
| - Service integration | 0.5 |
| - Testing | 0.2 |
| **Frontend Development** | 2.0 |
| - Type generation | 0.2 |
| - Hook creation | 0.5 |
| - Modal updates | 0.8 |
| - Testing | 0.5 |
| **Integration Testing** | 0.5 |
| **Documentation** | 0.5 |
| **Total** | **4.0 hours** |

### Dependencies

- ✅ Phase 2 backend complete
- ✅ `ChangeOrderWorkflowService` implemented and tested
- ✅ Frontend build environment working

### Prerequisites

1. Backend running locally
2. Database migrated with branches table
3. Test Change Order exists for edit flow testing

---

## 10. Recommendation

**Go/No-Go Decision:** ✅ **GO**

**Justification:**
- **Low Risk:** Simple schema extension, no breaking changes
- **High Value:** Fixes user confusion, enforces workflow in UI
- **Fast Implementation:** ~4 hours total
- **Aligns with Architecture:** Frontend reflects backend rules
- **Completes E06-U06:** Fills the identified gap

**Next Steps:**
1. Create detailed `01-plan.md` for this sub-iteration
2. Implement backend changes (Phase 1)
3. Implement frontend changes (Phase 2)
4. Create `03-check.md` with quality assessment

---

## Output Files

**Created:**
- `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/workflow-ui/00-analysis.md` (this file)

**To Be Created:**
- `workflow-ui/01-plan.md` - Detailed implementation plan
- `workflow-ui/02-do.md` - DO phase documentation
- `workflow-ui/03-check.md` - CHECK phase quality assessment

---

## References

- [Phase 2 Plan - ChangeOrderWorkflowService Design](../phase2/01-plan.md#L812-L1103)
- [ChangeOrderModal Current Implementation](../../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx)
- [ChangeOrderService Backend](../../../../backend/app/services/change_order_service.py)
- [Product Backlog - E06-U06](../../../product-backlog.md)
