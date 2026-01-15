# Workflow UI Integration - PLAN (Strategic Analysis and Iteration Planning)

**Date Created:** 2026-01-13
**Epic:** E006 (Branching & Change Order Management)
**User Story:** E06-U06-UI (Workflow-Aware Status Management)
**Iteration:** Workflow UI - Frontend Workflow State Management
**Status:** Planning Phase
**Related Docs:**
- [00-analysis.md](./00-analysis.md) - Detailed problem analysis
- [Phase 2 Plan](../phase2/01-plan.md) - Backend implementation
- [Product Backlog](../../../product-backlog.md) - E06-U06-UI definition

---

## Phase 1: Context Analysis

### Documentation Review

**Functional Requirements Alignment:**

From [`functional-requirements.md`](../../01-product-scope/functional-requirements.md):

- **FR-8.3**: "The system shall track change order status through defined workflow states including draft, submitted for approval, under review, approved, rejected, and implemented."

**Gap Identified:**
- ✅ Backend: `ChangeOrderWorkflowService` implements complete state machine
- ❌ Frontend: `ChangeOrderModal` shows all 7 status options regardless of workflow state
- ❌ No enforcement of valid transitions in UI
- ❌ No visual feedback when branch is locked

**Architecture Constraints:**

From [`coding-standards.md`](../../02-architecture/coding-standards.md):

- **Source of Truth:** Backend Pydantic models are single source of truth
- **Strict Typing:** Zero tolerance for `Any` types (MyPy strict mode, TypeScript strict mode)
- **API-First:** Frontend must consume backend API, no duplicate business logic
- **Quality Gates:** 80%+ test coverage required, zero linting errors

**Dependencies Met:**

| Dependency | Status | Notes |
|------------|--------|-------|
| E06-U06 (Lock/Unlock Branches) | ✅ Complete | Backend workflow service implemented |
| ChangeOrderWorkflowService | ✅ Complete | All transition rules implemented |
| BranchService | ✅ Complete | Lock/unlock operations working |
| branches table | ✅ Complete | Migration applied |

### Codebase Analysis

**Current Frontend Implementation:**

File: [`frontend/src/features/change-orders/components/ChangeOrderModal.tsx`](../../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx)

```typescript
// Lines 21-29: Static status options (PROBLEM)
const CHANGE_ORDER_STATUS_OPTIONS = [
  { label: "Draft", value: "Draft" },
  { label: "Submitted", value: "Submitted" },
  { label: "Under Review", value: "Under Review" },
  { label: "Approved", value: "Approved" },
  { label: "Rejected", value: "Rejected" },
  { label: "Implemented", value: "Implemented" },
  { label: "Closed", value: "Closed" },
];

// Used in Form.Item (Line 175):
<Form.Item
  name="status"
  label="Status"
  initialValue="Draft"
  rules={[{ required: true }]}
>
  <Select options={CHANGE_ORDER_STATUS_OPTIONS} />
</Form.Item>
```

**Problems Identified:**

1. **Hardcoded Options:** All 7 statuses always shown
2. **No Workflow Awareness:** Create mode shows non-initial statuses
3. **No Lock Check:** Status field enabled even when branch locked
4. **No Transition Validation:** Users can select invalid states
5. **Backend Validates Too Late:** Error occurs after form submission

**Existing Backend Implementation:**

File: [`backend/app/services/change_order_workflow_service.py`](../../../../backend/app/services/change_order_workflow_service.py)

```python
# Already implemented methods:
async def get_available_transitions(self, current: str) -> List[str]:
    """Get all valid status transitions from the current state."""

async def can_edit_on_status(self, status: str) -> bool:
    """Determine if Change Order details can be edited in this status."""
```

**Integration Points:**

| Component | Current State | Target State |
|-----------|---------------|--------------|
| ChangeOrderPublic Schema | No workflow metadata | Add `available_transitions`, `can_edit_status`, `branch_locked` |
| ChangeOrderService._to_public() | Basic field mapping | Call workflow service for metadata |
| ChangeOrderModal | Static options | Dynamic options from API |
| Form Validation | Post-submit error | Pre-submit prevention |

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** The Change Order creation and edit forms display all 7 possible workflow states, allowing users to select invalid workflow transitions and attempt to modify locked branches.

**Why Now:**
- Phase 2 backend workflow service is complete and tested
- Users are starting to use Change Order creation form
- Confusing UI leading to failed form submissions
- Branch locking works but UI doesn't reflect it

**Impact If Not Addressed:**
- **User Experience:** Poor - confusing dropdown with invalid options
- **Data Integrity:** Medium risk - backend validates but errors occur late
- **Workflow Enforcement:** Frontend doesn't guide users through valid states
- **Branch Locking:** Users can waste time editing forms that will fail

**Business Value:**
- **HIGH:** Improves user experience and reduces form submission errors
- **HIGH:** Enforces workflow rules at UI level (defensive programming)
- **MEDIUM:** Prevents wasted time on invalid selections
- **MEDIUM:** Makes branch locking visible to users

### 2. Success Criteria (Measurable)

**Functional Criteria:**

| Criterion | Test Case | Expected Result |
|-----------|-----------|-----------------|
| **Create Mode - Draft Only** | `test_create_mode_shows_draft_only` | Status dropdown has 1 option (Draft) or is disabled |
| **Edit Mode - Valid Transitions** | `test_edit_mode_shows_valid_transitions` | Dropdown shows only `get_available_transitions()` results |
| **Locked Branch - Disabled** | `test_locked_branch_disables_status` | Status field disabled when `branch_locked == true` |
| **Cannot Edit Status** | `test_cannot_edit_status_disables_field` | Status field disabled when `can_edit_status == false` |
| **Visual Warning** | `test_locked_branch_shows_warning` | Alert banner shown when branch locked |
| **Backend Schema** | `test_change_order_public_has_workflow_metadata` | Response includes all 3 workflow fields |

**Technical Criteria:**

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Type Coverage | 100% | No `any` types, all interfaces defined |
| Test Coverage | > 80% | Backend unit + integration, frontend component tests |
| Linting | 0 errors | MyPy strict (backend), ESLint (frontend) |
| Performance | < 100ms | Additional workflow query overhead < 100ms |
| API Compatibility | Non-breaking | Optional fields with defaults |

**User Experience Criteria:**

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Error Prevention | 100% | No invalid status selections possible |
| Visual Feedback | Clear | Users understand why field is disabled |
| Form Submission | Success rate > 95% | No workflow-related submission errors |

### 3. Scope Definition

**In Scope:**

1. **Backend Changes:**
   - ✅ Add `available_transitions: List[str]` to `ChangeOrderPublic` schema
   - ✅ Add `can_edit_status: bool` to `ChangeOrderPublic` schema
   - ✅ Add `branch_locked: bool` to `ChangeOrderPublic` schema
   - ✅ Modify `ChangeOrderService._to_public()` to populate workflow metadata
   - ✅ Add unit tests for schema changes
   - ✅ Add integration tests for workflow metadata in API responses

2. **Frontend Changes:**
   - ✅ Create `useWorkflowInfo()` hook for dynamic status options
   - ✅ Modify `ChangeOrderModal` to use dynamic options
   - ✅ Add disabled state logic for locked branches
   - ✅ Add visual warning banner for locked branches
   - ✅ Regenerate TypeScript types from OpenAPI spec
   - ✅ Add component tests for modal behavior
   - ✅ Add manual E2E verification

3. **Documentation:**
   - ✅ Update CHANGELOG.md with workflow UI changes
   - ✅ Update 03-check.md with quality assessment

**Out of Scope:**

- ❌ Workflow state machine changes (already complete in Phase 2)
- ❌ Branch lock enforcement in entity write operations (future: E06-U06 extension)
- ❌ API endpoint for `/available-transitions` (using existing GET /change-orders/{id})
- ❌ Advanced workflow features (parallel approvals, conditional transitions)
- ❌ Workflow designer UI (future: Camunda/Temporal integration)
- ❌ Branch selector lock icon (already done in Phase 2)
- ❌ Time Machine workflow state visualization (future iteration)

**Assumptions:**

1. Backend `ChangeOrderWorkflowService` is correct and tested
2. `branches` table migration has been applied
3. Frontend build environment can regenerate types successfully
4. No breaking changes to existing API consumers (new fields are optional)
5. Single developer iteration (no code conflicts expected)

---

## Phase 3: Implementation Options

| Aspect | Option A: API Extension | Option B: Quick Fix (Frontend Only) | Option C: New Endpoint |
|--------|------------------------|-----------------------------------|----------------------|
| **Approach Summary** | Add workflow metadata to existing ChangeOrderPublic schema | Hardcode "Draft only" in create mode, keep edit mode unchanged | Create new GET /change-orders/{id}/workflow endpoint |
| **Backend Changes** | Extend `_to_public()` method, add 3 optional schema fields | None | Create new endpoint with workflow service |
| **Frontend Changes** | Create `useWorkflowInfo()` hook, dynamic options, disabled logic | Disable status field on create only | Call new endpoint for workflow data |
| **Design Patterns** | Enrich existing API response, single source of truth | Frontend rule, bypasses backend | Separate workflow resource |
| **Pros** | • Single API call for all data<br>• Backend stays source of truth<br>• Future-proof for workflow changes<br>• Clean architecture | • Minimal code change<br>• Fast implementation<br>• No backend changes | • Clear separation of concerns<br>• Workflow data isolated |
| **Cons** | • Schema extension (breaking if not optional)<br>• Slightly larger response size | • Doesn't solve edit mode problem<br>• Duplicates workflow logic in frontend<br>• Incomplete solution | • Additional API call<br>• More complex frontend<br>• Endpoint proliferation |
| **Test Strategy Impact** | Unit tests for `_to_public()`, integration tests for API | Component tests only | Integration tests for new endpoint |
| **Risk Level** | Low (optional fields, backward compatible) | Medium (incomplete, partial solution) | Medium (more integration points) |
| **Estimated Complexity** | Simple (1-2 hours backend, 2-3 hours frontend) | Trivial (15 minutes) | Moderate (2-3 hours total) |
| **User Value** | HIGH (complete solution) | LOW (partial - create only) | HIGH (complete solution) |
| **Maintainability** | HIGH (single source of truth) | LOW (frontend-backend split) | MEDIUM (separate endpoint) |

### Recommendation: **Option A - API Extension**

**Justification:**

1. **Aligns with Architecture:** Backend remains single source of truth (per coding standards)
2. **Complete Solution:** Handles both create and edit modes properly
3. **Future-Proof:** Workflow changes automatically reflected in UI
4. **Single Source of Truth:** No duplicate workflow logic in frontend
5. **Backward Compatible:** Optional fields with defaults don't break existing consumers
6. **Efficient:** Single API call instead of multiple requests
7. **Low Risk:** Schema extension is additive, no breaking changes

**Why Not Option B:**
- Incomplete solution (doesn't fix edit mode)
- Violates "backend is source of truth" principle
- Creates technical debt (frontend workflow rules)

**Why Not Option C:**
- Unnecessary complexity (new endpoint)
- Additional network call
- Endpoint proliferation anti-pattern

> [!IMPORTANT] > **Human Decision Point**: I recommend **Option A (API Extension)** as it provides a complete, maintainable solution that aligns with our architecture principles. It requires ~4 hours total effort and solves both the create and edit mode problems while keeping the backend as the single source of truth.
>
> **Do you approve Option A, or would you prefer to discuss the other options?**

---

## Phase 4: Technical Design

### TDD Test Blueprint

**Backend Tests (pytest):**

```
tests/unit/test_change_order_service_workflow_metadata.py
├── test_to_public_includes_available_transitions()
├── test_to_public_includes_can_edit_status()
├── test_to_public_includes_branch_locked()
├── test_to_public_draft_status_allows_all_transitions()
├── test_to_public_submitted_status_allows_review_only()
├── test_to_public_approved_status_allows_implemented_only()
├── test_to_public_rejected_status_allows_resubmission()
├── test_to_public_branch_locked_true_when_branch_locked()
└── test_to_public_branch_locked_false_when_branch_unlocked()

tests/integration/test_change_order_workflow_api_integration.py
├── test_get_change_order_includes_workflow_metadata()
├── test_list_change_orders_includes_workflow_metadata()
├── test_create_change_order_returns_workflow_metadata()
├── test_workflow_metadata_updates_on_status_change()
└── test_workflow_metadata_reflects_branch_lock_state()
```

**Frontend Tests (Vitest):**

```
frontend/src/features/change-orders/hooks/useWorkflowInfo.test.ts
├── test_create_mode_returns_draft_only()
├── test_edit_mode_returns_available_transitions()
├── test_locked_branch_disables_status()
├── test_cannot_edit_status_disables_field()
└── test_unlocked_branch_allows_edit()

frontend/src/features/change-orders/components/ChangeOrderModal.test.tsx
├── test_create_mode_status_field_shows_draft_only()
├── test_edit_mode_status_field_filters_by_transitions()
├── test_locked_branch_disables_status_field()
├── test_locked_branch_shows_warning_banner()
├── test_submit_with_valid_transition_succeeds()
└── test_submit_with_locked_branch_fails_validation()
```

### First 5 Test Cases (Ordered Simple to Complex)

#### Test 1: `test_to_public_includes_available_transitions()`

**Purpose:** Verify that `ChangeOrderService._to_public()` adds the `available_transitions` field.

**Arrange:**
```python
# Given
co = ChangeOrder(
    id=uuid4(),
    code="CO-001",
    status="Draft",
    # ... other fields
)
service = ChangeOrderService(db_session, branch_service, workflow_service)
workflow_service.get_available_transitions.return_value = ["Submitted for Approval"]
```

**Act:**
```python
# When
result = service._to_public(co)
```

**Assert:**
```python
# Then
assert result.available_transitions == ["Submitted for Approval"]
workflow_service.get_available_transitions.assert_called_once_with("Draft")
```

#### Test 2: `test_to_public_includes_can_edit_status()`

**Purpose:** Verify that `can_edit_status` field is populated correctly.

**Arrange:**
```python
co = ChangeOrder(status="Under Review")
workflow_service.can_edit_on_status.return_value = False
```

**Act:**
```python
result = service._to_public(co)
```

**Assert:**
```python
assert result.can_edit_status is False
workflow_service.can_edit_on_status.assert_called_once_with("Under Review")
```

#### Test 3: `test_to_public_includes_branch_locked()`

**Purpose:** Verify that `branch_locked` field reflects actual branch state.

**Arrange:**
```python
co = ChangeOrder(branch_name="co-CO-001", project_id=project_id)
branch = Branch(name="co-CO-001", project_id=project_id, locked=True)
branch_service.get_by_name_and_project.return_value = branch
```

**Act:**
```python
result = service._to_public(co)
```

**Assert:**
```python
assert result.branch_locked is True
branch_service.get_by_name_and_project.assert_called_once()
```

#### Test 4: `test_create_mode_status_field_shows_draft_only()`

**Purpose:** Verify frontend create mode shows only Draft option.

**Arrange:**
```typescript
// No current status (create mode)
const { statusOptions } = useWorkflowInfo(
  undefined, // currentStatus
  undefined, // availableTransitions
  true,      // canEdit
  false      // isLocked
);
```

**Act:**
```typescript
const options = statusOptions.value;
```

**Assert:**
```typescript
expect(options).toEqual([{ label: "Draft", value: "Draft" }]);
expect(options.length).toBe(1);
```

#### Test 5: `test_edit_mode_status_field_filters_by_transitions()`

**Purpose:** Verify frontend edit mode shows only available transitions.

**Arrange:**
```typescript
// Current status: "Submitted for Approval"
// Available transitions: ["Under Review"]
const { statusOptions } = useWorkflowInfo(
  "Submitted for Approval",
  ["Under Review"],
  true,
  false
);
```

**Act:**
```typescript
const options = statusOptions.value;
```

**Assert:**
```typescript
expect(options).toEqual([{ label: "Under Review", value: "Under Review" }]);
expect(options).not.toContainEqual({ label: "Draft", value: "Draft" });
```

### Implementation Strategy

**High-Level Approach:**

1. **Backend-First:** Extend schema and service, test thoroughly
2. **Type Generation:** Regenerate frontend types from OpenAPI spec
3. **Frontend Hook:** Create reusable `useWorkflowInfo()` hook
4. **Component Integration:** Update `ChangeOrderModal` to use hook
5. **E2E Verification:** Manual testing of complete flows

**Key Technologies:**

- **Backend:** Python 3.12+, FastAPI, Pydantic, pytest-asyncio
- **Frontend:** TypeScript 5+, React 18, Vitest, Ant Design
- **Testing:** pytest (backend), Vitest (frontend), Playwright (E2E - optional)

**Integration Points:**

| Component | Integration Type | Notes |
|-----------|------------------|-------|
| ChangeOrderWorkflowService | Service composition | Called by `ChangeOrderService._to_public()` |
| BranchService | Service composition | Called for `branch_locked` check |
| ChangeOrderPublic Schema | Schema extension | Add 3 optional fields with defaults |
| useWorkflowInfo Hook | New hook | Encapsulates workflow logic for reuse |
| ChangeOrderModal | Component update | Replace static options with hook |
| API Client | Type regeneration | `npm run generate-client` after schema change |

**Component Breakdown:**

**Backend:**
```
backend/app/
├── models/
│   └── schemas/
│       └── change_order.py          # Add workflow fields to ChangeOrderPublic
├── services/
│   └── change_order_service.py      # Add _to_public() method
└── api/
    └── routes/
        └── change_orders.py         # No changes (uses _to_public automatically)

tests/
├── unit/
│   └── test_change_order_service_workflow_metadata.py
└── integration/
    └── test_change_order_workflow_api_integration.py
```

**Frontend:**
```
frontend/src/
├── features/
│   └── change-orders/
│       ├── hooks/
│       │   ├── useWorkflowInfo.ts           # NEW
│       │   └── useWorkflowInfo.test.ts      # NEW
│       └── components/
│           ├── ChangeOrderModal.tsx         # MODIFY
│           └── ChangeOrderModal.test.tsx    # MODIFY
├── api/
│   └── client.ts                            # No changes (types regenerated)
└── types/                                    # Auto-generated from OpenAPI
```

---

## Phase 5: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|-------------------|
| **Breaking Change** | Existing API consumers break when schema changes | Low | Medium | Make all new fields optional with default values (`None`, `True`, `False`) |
| **Type Generation Failure** | OpenAPI spec doesn't update correctly, TypeScript types don't match | Medium | Medium | Manually verify generated types, add manual verification step to plan |
| **Performance Regression** | Additional workflow queries slow down API response | Low | Low | Workflow service is in-memory (no DB), expected overhead < 50ms |
| **Frontend-Backend Sync** | Frontend expects fields that backend doesn't provide | Low | Medium | Integration test verifies API response structure before frontend implementation |
| **Edge Case Handling** | Null branch_name, missing workflow states, race conditions | Medium | Low | Comprehensive unit tests for all workflow states, add null checks |
| **Test Coverage Gap** | Missing test cases for workflow transitions | Low | Low | Test blueprint defined, TDD approach ensures coverage |
| **User Confusion** | Disabled status field without clear explanation | Medium | Medium | Add tooltip and warning banner with clear messaging |

**Overall Risk Level:** **LOW**

**Reasoning:**
- Backend workflow service is already tested and working
- Schema extension is additive (non-breaking)
- Clear test strategy with TDD approach
- Simple integration points (no complex state management)

---

## Phase 6: Effort Estimation

### Time Breakdown

| Phase | Task | Hours |
|-------|------|-------|
| **Backend Development** | | **1.5** |
| | Extend ChangeOrderPublic schema (3 fields) | 0.3 |
| | Implement `_to_public()` method | 0.5 |
| | Backend unit tests (8 tests) | 0.4 |
| | Backend integration tests (5 tests) | 0.3 |
| **Frontend Development** | | **2.5** |
| | Regenerate TypeScript types | 0.2 |
| | Create `useWorkflowInfo()` hook | 0.5 |
| | Update `ChangeOrderModal` component | 0.8 |
| | Frontend component tests (6 tests) | 0.6 |
| | Visual polish (warnings, tooltips) | 0.4 |
| **Integration & QA** | | **0.5** |
| | Manual E2E testing (create, edit, lock scenarios) | 0.3 |
| | Performance verification (API response times) | 0.2 |
| **Documentation** | | **0.5** |
| | Update CHANGELOG.md | 0.2 |
| | Create 03-check.md quality assessment | 0.3 |
| **Total Estimated Effort** | | **5.0 hours** |

### Prerequisites

**Must Complete First:**

1. ✅ Phase 2 backend implementation (complete - `ChangeOrderWorkflowService` working)
2. ✅ `branches` table migration applied (complete)
3. ⏳ Backend dev server running on port 8000
4. ⏳ Frontend dev server running on port 5173

**Documentation Updates:**

- [`CHANGELOG.md`](../../../../CHANGELOG.md) - Add workflow UI entry
- [`03-check.md`](./03-check.md) - Create quality assessment document

**Infrastructure Needed:**

- None (uses existing dev environment)

### Sequence of Work

1. **Backend Schema Extension** (0.3h)
2. **Backend Service Implementation** (0.5h)
3. **Backend Testing** (0.7h)
4. **Type Generation** (0.2h)
5. **Frontend Hook Creation** (0.5h)
6. **Frontend Component Updates** (1.2h)
7. **Frontend Testing** (0.6h)
8. **Integration Testing** (0.5h)
9. **Documentation** (0.5h)

**Critical Path:** Backend must be complete before type generation, which must be complete before frontend implementation.

---

## Output Format

**File Created:** `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/workflow-ui/01-plan.md`

**Related Documentation:**

- [Architecture - Coding Standards](../../02-architecture/coding-standards.md)
- [Product Scope - Functional Requirements](../../01-product-scope/functional-requirements.md)
- [Product Backlog - E06-U06-UI](../../product-backlog.md)
- [Phase 2 Plan - Backend Implementation](../phase2/01-plan.md)
- [00-analysis.md - Problem Analysis](./00-analysis.md)

---

## Next Steps

**Awaiting Approval:**

✅ **Option A (API Extension)** recommended

**After Approval:**

1. Begin **DO phase** ([02-do.md](./02-do.md))
2. Implement backend schema extension (TDD approach)
3. Implement frontend hook and component updates
4. Run complete test suite (backend + frontend)
5. Create **CHECK phase** document ([03-check.md](./03-check.md))
6. Create **ACT phase** improvements ([04-act.md](./04-act.md))

**Ready to proceed with DO phase upon approval.**

---

**Document Status:** ✅ Complete - Awaiting human approval to proceed to DO phase
