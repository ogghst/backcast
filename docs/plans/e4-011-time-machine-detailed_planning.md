# E4-011 Time Machine Detailed Plan

Numbered checklist for implementing the global “time machine” date selector with backend session persistence and data filtering.

---

## 1. Update Strategic Documents
- **Description:** Amend `docs/prd.md`, `docs/plan.md`, and `docs/project_status.md` with the time-machine requirement (UI location, default behavior, backend session storage, filtering rules).
- **Acceptance Criteria:**
  - PRD explicitly states the “time machine” control, default date = today, supports past/future.
  - Project plan and status sections reference the new feature (epic/task alignment, sprint impact).
- **Test-First Requirement:** Not applicable (documentation-only change).
- **Expected Files:** `docs/prd.md`, `docs/plan.md`, `docs/project_status.md`.
- **Dependencies:** None.

## 2. Persist Time Machine Date on User
- **Description:** Add nullable `time_machine_date` column to `User` model with migration, schemas, and default handling (null = today).
- **Acceptance Criteria:**
  - Database migration adds column with timezone-aware date (UTC).
  - Pydantic schemas (`UserPublic`, `UserUpdateMe`, etc.) expose the field.
  - Backend tests fail initially when looking for the field in `UserPublic`.
- **Test-First Requirement:** Add/modify backend test (e.g., in `backend/tests/api/routes/test_users.py`) expecting `time_machine_date` in response → RED.
- **Expected Files:** `backend/app/models/user.py`, new Alembic migration, affected schemas/tests.
- **Dependencies:** Step 1 complete.

## 3. Time Machine Session Dependency & API
- **Description:** Create FastAPI dependency to resolve current control date (user column or today) plus endpoints to read/update it (e.g., `/users/me/time-machine`).
- **Acceptance Criteria:**
  - Dependency returns `date` object, defaults to today when unset.
  - PATCH endpoint updates column, validates ISO date, persists.
  - Tests prove: (a) dependency returns stored date, (b) updating endpoint changes DB, (c) invalid date returns 422.
- **Test-First Requirement:** Add failing tests in `backend/tests/api/routes/test_users.py` (new suite for time-machine endpoints/dependency) prior to implementation.
- **Expected Files:** `backend/app/api/deps.py`, new route module or existing user routes, schemas.
- **Dependencies:** Step 2.

> ### Process Checkpoint #1 (after Step 3)
> - Should we continue with the plan as-is?
> - Have any assumptions (e.g., user column sufficiency) been invalidated?
> - Does the current state match expectations (docs updated, column + dependency ready)?

## 4. Global Backend Filtering
- **Description:** Introduce shared utilities (e.g., `apply_time_machine_filters(query, control_date)`) ensuring each read endpoint respects creation/registration/baseline timestamps ≤ control date.
- **Acceptance Criteria:**
  - Identify target models and primary date fields: `created_at`/`updated_at` for structural objects, `registration_date` for cost/earned value entries, `baseline_date` for baselines, etc.
  - For each service/query touched, tests confirm data newer than control date is excluded while older data still appears.
  - All existing tests updated to inject the dependency (mocking today) and new tests cover at least one entity per category.
- **Test-First Requirement:** For each domain (e.g., cost registrations, earned value, baselines), add failing tests in their respective service/api suites expecting filtered results.
- **Expected Files:** Multiple backend service and route modules (e.g., `app/services/cost_summary.py`, `app/api/routes/earned_value.py`, etc.), new helper module for filters.
- **Dependencies:** Step 3.

## 5. Frontend Time Machine Context & API Integration
- **Description:** Build a React context/provider storing the selected date, reading/writing via new backend endpoints, and exposing hooks for consumers.
- **Acceptance Criteria:**
  - Provider fetches initial date (default today) on layout load.
  - Hook `useTimeMachineDate()` returns date, setter triggers mutation + optimistic update.
  - Vitest/unit tests ensure provider defaults and updates correctly (failing test first).
- **Test-First Requirement:** Add failing React unit test (e.g., `frontend/src/hooks/__tests__/useTimeMachineDate.test.tsx`) asserting provider supplies default value and update mutation.
- **Expected Files:** New context/hook files under `frontend/src/context` or `hooks`, updated React Query client definitions.
- **Dependencies:** Steps 2-4 (API + filtering ready).

## 6. Navbar Time Machine Component
- **Description:** Implement Chakra-based date picker (top-left, next to user button) that consumes the context.
- **Acceptance Criteria:**
  - UI renders on desktop navbar (per spec) with accessible label, supports past/future selection via calendar.
  - Changing date calls context setter, handles loading/error states.
  - Component snapshot/unit test or React Testing Library ensures renders + interactions.
- **Test-First Requirement:** Add failing component test verifying the picker appears and invokes update handler.
- **Expected Files:** `frontend/src/components/Common/Navbar.tsx`, new `TimeMachinePicker` component file, CSS/theme adjustments.
- **Dependencies:** Step 5.

> ### Process Checkpoint #2 (after Step 6)
> - Continue as planned?
> - Are backend/UX integrations functioning together?
> - Any unexpected regressions or scope issues?

## 7. Propagate Control Date Through Data Fetching
- **Description:** Update all React Query hooks/services to include the time-machine date in their query keys and request params/headers; ensure caches segregate by date.
- **Acceptance Criteria:**
  - Each API call uses the context date (e.g., adds `control_date` query param).
  - React Query keys include the date to prevent stale mixing.
  - Integration tests (Playwright or component-level) confirm switching dates refreshes data.
  - Add failing test(s) before updates (e.g., Playwright script expecting two different snapshots).
- **Test-First Requirement:** For a representative page (projects detail timeline), add a failing Playwright/Vitest integration test verifying datasets change when time-machine date changes.
- **Expected Files:** React query hooks, components like `BudgetTimeline`, `EarnedValueSummary`, plus client service wrappers.
- **Dependencies:** Steps 4-6.

## 8. Regression & Accessibility Testing
- **Description:** Run backend + frontend test suites, add targeted coverage for regression-prone flows (baseline viewing, cost registrations) and confirm date picker accessibility.
- **Acceptance Criteria:**
  - `pytest` + `npm test` + Playwright suites pass with new scenarios.
  - Accessibility checks (e.g., axe or Chakra’s recommended approach) validate control has label/help text.
  - Document manual QA steps/results.
- **Test-First Requirement:** Not applicable (execution of existing suites), but add failing accessibility test if coverage lacking.
- **Expected Files:** Test run artifacts, documentation (e.g., `docs/completions/pla_2_time-machine-testing.md`).
- **Dependencies:** Steps 1-7.

---

## TDD Discipline Rules
1. Every code step begins with a failing automated test covering the intended behavior (documentation steps excluded).
2. Follow strict red → green → refactor cycles; do not batch multiple production changes before seeing tests pass.
3. Limit to three implementation attempts per step; if still failing, stop and request guidance.
4. Tests must assert behavior/outputs (e.g., filtered records absent) rather than mere type-check or compilation signals.

## Process Checkpoints
- **Checkpoint #1:** After Step 3 (docs + user column + dependency/API). Ask required questions before moving on.
- **Checkpoint #2:** After Step 6 (frontend picker wired to API). Validate combined flow and assumptions.

## Scope Boundaries
- Focus exclusively on the time machine requirement: session persistence, backend filtering, navbar control, and data propagation.
- Any adjacent refactors (e.g., redesigning Navbar, altering unrelated APIs) require explicit user approval before proceeding.

## Rollback Strategy
- **Safe Rollback Point:** After Step 2 (schema/migration) and Step 3 (dependency) are merged independently, we can revert by dropping the column/migration and removing the dependency routes.
- **Alternative Approach if Abandoned:** Fall back to a hybrid `X-Time-Machine-Date` request header without persistent storage (Option C in PLA-1 analysis). This would require reworking backend filters to read headers but would avoid DB schema changes.

---

End of plan.
