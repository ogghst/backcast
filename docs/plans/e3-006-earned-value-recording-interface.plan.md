# E3-006 Earned Value Recording Interface Plan

## Overview
- **Approach:** Dedicated CRUD implementation mirroring cost registrations (Approach A)
- **Key Constraints:**
  - Earned value derived as `BAC × percent_complete ÷ 100`
  - Baseline association optional (no mandatory locking)
  - Percent complete and deliverable description required
  - Completion dates unique per cost element; no duplicate dates allowed
  - Schedule validation mirrors cost registrations (block before start, warn after end)
- **Standards:** TDD with failing tests first, ≤100 LOC / ≤5 files per commit target, reuse existing abstractions, no duplication

## 1. Implementation Steps

1. **Backend Test Harness & API Skeleton**
   - **Acceptance Criteria:**
     - New backend tests cover earned value entry CRUD scenarios (create success with derived value, validation failures, list/read/update/delete) and currently fail.
     - No production code changes yet.
   - **Test-First Requirement:** Execute `backend/tests/api/routes/test_earned_value_entries.py` (new) and observe failures.
   - **Expected Files:**
     - `backend/tests/api/routes/test_earned_value_entries.py`
     - `backend/tests/utils/earned_value_entry.py` (fixture helper if needed)
   - **Dependencies:** None.

2. **Backend Earned Value API Implementation**
   - **Acceptance Criteria:**
     - Step 1 tests pass green.
     - FastAPI router enforces percent range (0–100), completion-date uniqueness per cost element, optional baseline_id, schedule-aware validation (error before start, warning if after end), and derives `earned_value` from current cost element BAC.
     - Responses include warning payloads consistent with cost registration behavior.
   - **Test-First Requirement:** Previously failing tests from Step 1.
   - **Expected Files:**
     - `backend/app/api/routes/earned_value_entries.py`
     - `backend/app/api/main.py`
     - `backend/app/models/__init__.py`
     - `backend/app/core/seeds.py` (if seed cleanup required)
     - Supporting test utilities updated as needed.
   - **Dependencies:** Completion of Step 1.

3. **Frontend Client & Table Scaffolding**
   - **Acceptance Criteria:**
     - TypeScript/compile step fails because new components reference unimplemented services.
     - Earned value table and CRUD dialog skeletons exist with TODO placeholders (no live API calls yet).
   - **Test-First Requirement:** Add failing TypeScript assertion (e.g., import in route causing build failure) before wiring logic.
   - **Expected Files:**
     - Generated client artifacts (`frontend/src/client/*`).
     - `frontend/src/components/Projects/EarnedValueEntriesTable.tsx`.
     - `frontend/src/components/Projects/{Add,Edit,Delete}EarnedValueEntry.tsx`.
     - `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx` (new tab import).
   - **Dependencies:** Backend endpoints available (Step 2).

4. **Frontend Earned Value CRUD Wiring**
   - **Acceptance Criteria:**
     - Frontend tests or manual TypeScript checks pass.
     - Components fetch/mutate via generated client, surface schedule warnings, block duplicate dates and invalid percentages, and show earned value as read-only derived field.
     - Toasts and query invalidation replicate existing patterns.
   - **Test-First Requirement:** Resolve failing check introduced in Step 3.
   - **Expected Files:**
     - Updates to components from Step 3.
     - New hook(s) such as `frontend/src/hooks/useEarnedValueValidation.ts` if created.
     - Route/table integration updates.
   - **Dependencies:** Completion of Step 3.

5. **Documentation & Project Status Update**
   - **Acceptance Criteria:**
     - `docs/project_status.md` reflects E3-006 completion with summary notes.
     - Any related docs adjusted; all automated tests green.
   - **Test-First Requirement:** Introduce temporary failing expectation (e.g., TODO check in test or lint) before editing docs, then remove once documentation updated.
   - **Expected Files:**
     - `docs/project_status.md`
     - Optional additional docs.
   - **Dependencies:** Steps 1–4 complete.

## 2. TDD Discipline Rules
- Introduce failing tests (or TypeScript checks) before production code changes for every step.
- Follow red → green → refactor cycle; refactor only when tests pass.
- Limit to three attempts per step; escalate if still failing.
- Tests must assert behavior (responses, UI rendering, validation), not just compile state.

## 3. Process Checkpoints
- **After Step 2:** Pause to confirm the backend matches expectations, assumptions remain valid, and decide whether to proceed.
- **After Step 4:** Pause to review UI behavior, verify assumptions, and confirm readiness for documentation updates.

During checkpoints ask:
1. Should we continue with the plan as-is?
2. Have any assumptions been invalidated?
3. Does the current state match our expectations?

## 4. Scope Boundaries
- Work strictly covers E3-006 earned value recording interface and associated documentation updates.
- Any additional enhancements or refactors require explicit user approval before proceeding.

## 5. Rollback Strategy
- **Safe rollback point:** Commit after Step 1 (tests only) preserves baseline state if backend implementation proves problematic.
- **Alternative approach:** If Approach A fails, consult user to pivot to merging within existing cost registration module or delivering backend API-only variant while postponing UI.
