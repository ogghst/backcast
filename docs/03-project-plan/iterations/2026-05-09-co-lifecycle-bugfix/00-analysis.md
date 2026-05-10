# Analysis: Change Order Lifecycle Bug Fixes

**Created:** 2026-05-09
**Request:** Fix 3 critical backend bugs and 10 UI issues discovered during end-to-end change order lifecycle testing. Backend bugs were temporarily patched to unblock testing; permanent fixes with test coverage are needed.

---

## Clarified Requirements

End-to-end testing of the full CO lifecycle (Draft -> Submitted -> Approved -> Implemented) on a real project (HOUSE-REN-2026) revealed three backend bugs that broke the merge flow, plus ten UI issues affecting the user experience. The temporary patches allow the workflow to complete but need proper engineering with regression tests.

### Functional Requirements

**Backend (3 bugs -- must fix):**

- **BUG-1**: `_detect_merge_conflicts()` must treat entities that exist only on the source branch as additions (no conflict), not as errors. The temporary `return []` is correct in behavior but needs an explicit test proving the case.
- **BUG-2**: `MergeBranchCommand.execute()` must support "create-on-merge": when the entity has no current version on the target branch, clone the source version onto the target branch. The temporary patch does this but the cloned entity's temporal ranges must be set correctly via raw SQL (which the patch does) and the path needs test coverage.
- **BUG-3**: `merge_change_order()` must not attempt to merge the CO entity itself from the isolation branch when the CO was never forked there. COs exist only on main; the isolation branch contains the project data (WBEs, CostElements). The temporary patch uses `BranchMode.STRICT` to correctly detect this, but the logic should be explicit about why COs are skipped.
- **SLA-1 (additional)**: `sla_due_date` may not be cleared on rejection. The architecture doc states rejection unlocks the branch and the implementation guide shows `sla_due_date: None (cleared)` as expected behavior. Needs verification.

**Frontend (10 UI issues -- priority split):**

- **UI-6** (MEDIUM): Edit button enabled on "Implemented" CO -- terminal state, violates state machine.
- **UI-7** (MEDIUM): Approval tab shows "Can Approve" for Implemented CO -- misleading, no actions available.
- **UI-8**: Approval tab shows "$0 delta" after merge -- should show original impact or be hidden.
- **UI-9**: SLA section shows "5 business days remaining" for completed CO.
- **UI-10** (data integrity): Delete action visible on Implemented CO.
- **UI-1**: Branch name note in CO create dialog doesn't update when code field changes.
- **UI-2**: Stale error messages not cleared when code field changes.
- **UI-3**: antd `useForm` not connected warning (antd v6 deprecation).
- **UI-4**: Edit dialog auto-opens after CO creation (unexpected UX).
- **UI-5**: `: :` text artifact visible before tabpanel content.

### Non-Functional Requirements

- All fixes must preserve bitemporal data integrity (valid_time, transaction_time ranges).
- Branch isolation semantics must remain correct: merge must not corrupt main-branch data.
- Test coverage for the three backend bugs must be at least 80% for the new code paths.
- Frontend fixes must not break existing change order creation, submission, or approval flows.

### Constraints

- The temporary patches are already on branch `agent-architecture` in the working tree (uncommitted). The proper fix should replace these patches, not layer on top.
- Existing tests in `test_merge_conflict_detection.py` and `test_merge_branch_command.py` must continue to pass.
- The change order workflow state machine (`_TRANSITIONS`, `_LOCK_TRANSITIONS`, `_UNLOCK_TRANSITIONS`) is not being changed -- only the merge execution logic.

---

## Context Discovery

### Product Scope

- Relevant user stories: [change-management-user-stories.md](../../../01-product-scope/change-management-user-stories.md)
  - Section 3.2 "Performing Work on a Change": create new WBEs/CostElements on the CO branch.
  - Section 3.6 "Accepting the Change (Merge)": conflict detection, "Change Wins" strategy, budget recalculation.
- Section 4 state machine table: "Implemented" is a terminal state with no allowed actions.
- Business rule: COs are created on main. The isolation branch (`BR-{code}`) holds the project data changes. The CO entity itself is not forked to the isolation branch.

### Architecture Context

- Bounded contexts involved:
  - **Change Order Workflow** (`docs/02-architecture/backend/contexts/change-order-workflow/`)
  - **EVCS Core / Branching** (`docs/02-architecture/backend/contexts/branching/` or `evcs-core/`)
- Key patterns:
  - `BranchableService._detect_merge_conflicts()` -- conflict detection via parent-chain divergence walking.
  - `MergeBranchCommand` -- command pattern for atomic merge operations with `control_date`.
  - `ChangeOrderService.merge_change_order()` -- orchestrator that merges WBEs, CostElements, recalculates budget, then optionally merges the CO entity.
- Entity tier: ChangeOrder is **Branchable** (EntityBase + VersionableMixin + BranchableMixin).
- CO isolation branch is named `BR-{change_order_code}` (e.g., `BR-CO-2026-010`).

### Codebase Analysis

**Backend:**

- `app/core/branching/service.py:716-720` -- BUG-1 location. The patched code returns `[]` for missing target, which is correct. The original raised `ValueError`. No test exists for the "entity only on source" case.
- `app/core/branching/commands.py:374-405` -- BUG-2 location. The patched code adds a create-on-merge path that clones the source entity to the target branch with `parent_id=None` and sets temporal ranges via raw SQL. No test exists for this path.
- `app/services/change_order_service.py:913-929` -- BUG-3 location. The patched code uses `BranchMode.STRICT` to check if the CO exists on the isolation branch before attempting merge. The comment explains COs may or may not be forked. No test verifies this conditional merge.
- `app/services/change_order_workflow_service.py` -- SLA clearing on rejection should be verified here.
- Existing tests: `tests/unit/core/test_merge_conflict_detection.py` (4 tests, all for existing entities), `tests/unit/core/test_merge_branch_command.py` (4 tests, all for existing target), `tests/integration/test_change_order_full_merge.py` (integration test).

**Frontend:**

- CO components at `frontend/src/features/change-orders/components/`.
- Key files for UI bugs:
  - `ChangeOrderModal.test.tsx` / `ChangeOrderModal` -- create/edit dialog (UI-1, UI-2, UI-3, UI-4).
  - `StepDetailsSection.tsx` / `WorkflowStepper.tsx` -- status-dependent UI (UI-5, UI-6, UI-7, UI-9, UI-10).
  - Approval tab rendering -- (UI-7, UI-8).
- The state machine (Section 4 of user stories) defines "Implemented" as terminal. Frontend must disable all actions for this state.

---

## Solution Options

### Option 1: Surgical Backend Fixes + Targeted Frontend Polish

**Architecture & Design:**

Fix each bug at its exact location with minimal code changes. For the backend, validate the temporary patches as correct and add regression tests. For the frontend, add status guards to each affected component.

**Backend Implementation:**

- BUG-1: The `return []` patch is correct. Add one test case to `test_merge_conflict_detection.py`: entity created on source branch only, verify `_detect_merge_conflicts()` returns `[]`.
- BUG-2: The create-on-merge path in `MergeBranchCommand` is correct. Add one test case to `test_merge_branch_command.py`: create entity on source branch only, merge to target, verify entity exists on target with correct temporal ranges.
- BUG-3: The `BranchMode.STRICT` check is correct. Add one integration-level test to `test_change_order_merge_orchestration.py`: create CO on main, merge, verify no attempt to merge CO from isolation branch.
- SLA-1: Add assertion to existing rejection test that `sla_due_date` is `None` after rejection.
- Clean up comments in the patched code to document the design rationale.

**Frontend Implementation:**

- UI-6, UI-10: Add `status === "Implemented"` guard to disable edit/delete buttons.
- UI-7, UI-8, UI-9: Add `status === "Implemented"` guard to hide approval tab, SLA section, and delta display.
- UI-1, UI-2: Add `useEffect` to clear errors and update branch name preview when code field changes.
- UI-3: Address `useForm` deprecation warning (antd v6 migration note).
- UI-4: Remove auto-open of edit dialog after CO creation.
- UI-5: Fix the `: :` text artifact in tabpanel rendering.

**Trade-offs:**

| Aspect          | Assessment                                                                  |
| --------------- | --------------------------------------------------------------------------- |
| Pros            | Minimal risk, each fix is isolated and testable, fast to implement          |
| Cons            | Does not address root cause of why the code paths were missing              |
| Complexity      | Low                                                                         |
| Maintainability | Good -- fixes are self-documenting with dedicated tests                     |
| Performance     | No impact                                                                   |

---

### Option 2: Backend Merge Path Refactoring + Comprehensive Frontend Fix

**Architecture & Design:**

Refactor the merge execution path into a `MergeStrategy` abstraction that explicitly handles three cases: (a) update existing target, (b) create new on target, (c) skip (entity not on source). Refactor the frontend to use a centralized `useTerminalState` hook.

**Backend Implementation:**

- Extract merge strategy resolution into a `_resolve_merge_action()` method on `BranchableService`.
- BUG-1 and BUG-2 become explicit strategy branches rather than ad-hoc conditionals.
- BUG-3: The `merge_change_order()` method gets a clear separation between "merge project data" and "merge CO metadata" steps with explicit skip logic.
- SLA-1: Add a `_clear_sla_fields()` helper on the workflow service.

**Frontend Implementation:**

- Create `useTerminalState` hook that computes available actions from the state machine.
- Replace all scattered `status === "Implemented"` checks with the hook.
- Fix all 10 UI issues with the centralized state as the source of truth.

**Trade-offs:**

| Aspect          | Assessment                                                                  |
| --------------- | --------------------------------------------------------------------------- |
| Pros            | More robust long-term, prevents similar bugs, cleaner architecture          |
| Cons            | Larger scope, higher risk of regressions, longer implementation time        |
| Complexity      | Medium-High                                                                 |
| Maintainability | Good -- but introduces new abstraction that must be understood by the team   |
| Performance     | No impact                                                                   |

---

### Option 3: Backend-Only Focus (Defer Frontend)

**Architecture & Design:**

Focus exclusively on the 3 backend bugs + SLA verification. Defer all 10 UI issues to a separate iteration.

**Trade-offs:**

| Aspect          | Assessment                                                                  |
| --------------- | --------------------------------------------------------------------------- |
| Pros            | Fastest path to stable backend, smallest scope                              |
| Cons            | UI issues remain visible to users, data integrity risk (UI-10 delete on Implemented CO) |
| Complexity      | Low                                                                         |
| Maintainability | Good for backend, but deferred UI issues may compound                       |
| Performance     | No impact                                                                   |

---

## Comparison Summary

| Criteria           | Option 1: Surgical          | Option 2: Refactoring       | Option 3: Backend Only    |
| ------------------ | --------------------------- | --------------------------- | ------------------------- |
| Development Effort | 2-3 days                    | 5-7 days                    | 1-2 days                  |
| UX Quality         | All 10 UI issues fixed      | All 10 UI issues fixed      | No UI improvement         |
| Flexibility        | Each fix is independent     | Centralized pattern         | Backend only              |
| Best For           | Shipping fixes quickly      | Long-term architectural health | Unblocking merge flow only |
| Risk               | Low                         | Medium (refactoring scope)  | Low (but incomplete)      |

---

## Recommendation

**I recommend Option 1: Surgical Backend Fixes + Targeted Frontend Polish** because:

1. The temporary patches are already correct in behavior. The work is to validate them with tests and clean up the comments, not to redesign the merge path.
2. Option 2's `MergeStrategy` abstraction is speculative given that the current merge logic has exactly two paths (update vs. create) and the conditional is clear. A strategy pattern adds complexity without proportional benefit at this stage.
3. Option 3 leaves the data integrity risk of UI-10 (delete action on Implemented CO) unaddressed. This is unacceptable for a terminal-state entity.
4. The UI issues are mostly simple status guards. Centralizing them (Option 2) is premature; the current component structure handles status checks inline, which is the established pattern in this codebase.

**Alternative consideration:** If a fourth or fifth merge path were anticipated (e.g., three-way merge, cherry-pick), Option 2 would be justified. Currently, the merge has exactly two cases, making the surgical approach proportional.

---

## Decision Questions

1. Should UI-3 (antd v6 `useForm` deprecation warning) be addressed now, or tracked as a separate tech-debt item? Fixing it may touch many components beyond CO.
2. Is the SLA clearing on rejection (SLA-1) confirmed as a real bug, or was the observed behavior due to the test environment? This determines whether it gets a bugfix commit or just a verification test.
3. Should the create-on-merge path (BUG-2 fix) also handle the case where the entity was soft-deleted on the source branch? The current patch only handles active entities.

---

## References

- [Change Management User Stories](../../../01-product-scope/change-management-user-stories.md)
- [Change Order Workflow Architecture](../../../02-architecture/backend/contexts/change-order-workflow/architecture.md)
- [Change Order Workflow Implementation Guide](../../../02-architecture/backend/contexts/change-order-workflow/implementation-guide.md)
- [EVCS Entity Classification](../../../02-architecture/backend/contexts/evcs-core/entity-classification.md)
- Backend source: `app/core/branching/service.py` (BUG-1)
- Backend source: `app/core/branching/commands.py` (BUG-2)
- Backend source: `app/services/change_order_service.py` (BUG-3)
- Backend source: `app/services/change_order_workflow_service.py` (SLA-1)
- Existing tests: `tests/unit/core/test_merge_conflict_detection.py`
- Existing tests: `tests/unit/core/test_merge_branch_command.py`
- Existing tests: `tests/unit/services/test_change_order_merge_orchestration.py`
