# Technical Debt Register

**Last Updated:** 2026-02-21
**Total Debt Items:** 24 (24 completed)
**Total Estimated Effort:** 109 hours
**Completed Effort:** 30.25 hours

---

## Debt Items

### High Severity

#### [TD-067] FK Constraint: Business Key vs Primary Key in Temporal Entities

- **Source:** Change Order Workflow Recovery (2026-02-06)
- **Description:** `ChangeOrder.assigned_approver_id` foreign key references `users(id)` (auto-generated primary key) instead of `users(user_id)` (business key). This causes issues in bitemporal queries because PK changes across versions while business key remains stable.
- **Impact:** Data integrity issues in bitemporal queries; using PK may return wrong or expired versions
- **Estimated Effort:** 2-3 days (16-24 hours)
- **Target Date:** 2026-02-15
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Priority:** High
- **Risk:** Data integrity issues in bitemporal queries
- **Solution Options:**
  1. **Option 1 (Preferred)**: Update FK to Reference Business Keys - Correct bitemporal semantics, stable references, aligns with ADR-005. Requires data migration (16-24 hours)
  2. **Option 2**: Add Generated Column with Business Key Reference - No data migration, backward compatible, but more complex query logic and doesn't fix root issue (8-16 hours)
  3. **Option 3 (Current)**: Application Layer Workaround - No database changes, but risk of inconsistent queries, not long-term solution (0 hours - already implemented)
- **Affected Entities:**
  1. **Change Orders** (`backend/app/models/domain/change_order.py:122`) - `assigned_approver_id` → should reference `users.user_id` (Status: ⚠️ Known issue)
  2. **Projects** (`backend/app/models/domain/project.py`) - May have FK references to users (Status: 🔍 Needs audit)
  3. **WBEs** (`backend/app/models/domain/wbe.py`) - `project_id` reference needs verification (Status: 🔍 Needs audit)
  4. **Cost Elements** (`backend/app/models/domain/cost_element.py`) - `wbe_id` reference needs verification (Status: 🔍 Needs audit)
  5. **All temporal entities** with FK references (Status: 🔍 Comprehensive audit needed)
- **Migration Plan (Option 1 - Preferred):**
  1. **Audit Phase** (1 day): Scan all temporal entities for FK references, document all PK vs business key mismatches, assess data impact
  2. **Design Phase** (0.5 days): Design migration strategy, plan for zero-downtime deployment, rollback procedures
  3. **Implementation Phase** (1-1.5 days): Create Alembic migration to update FK constraints, update model definitions to use business keys, update service layer, update tests
  4. **Testing Phase** (0.5 days): Unit tests for FK references, integration tests for bitemporal queries, performance tests
  5. **Documentation Phase** (0.5 days): Update coding standards, document FK reference pattern for temporal entities, add ADR supplement if needed
- **Action Items:**
  - [ ] Audit all FK references in temporal entities
  - [ ] Create migration plan for Option 1
  - [ ] Update coding standards to specify business key FKs for temporal entities
  - [ ] Add validation to prevent PK-based FKs in new temporal entities
  - [ ] Schedule implementation iteration
- **References:**
  - **Issue**: CO-2026-003 recovery
  - **ADR**: ADR-005 Bitemporal Versioning
  - **Files**: `backend/app/models/domain/change_order.py:122`, `backend/scripts/repair_change_order_co_2026_003.py`, `backend/app/services/change_order_service.py:recover_change_order()`
  - **Iteration**: 2026-02-06-change-order-workflow-recovery

#### [TD-069] Failing Time Machine Store Tests

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** 3 failing tests in `src/stores/useTimeMachineStore.test.ts` related to time machine state management. View mode not preserved when switching projects, and project settings not maintained correctly.
- **Impact:** Code quality regression risk; time machine functionality may not work correctly across project changes
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-02-28
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** High
- **Risk:** Broken time travel functionality, inconsistent user experience
- **Test File:** [frontend/src/stores/useTimeMachineStore.test.ts](../../frontend/src/stores/useTimeMachineStore.test.ts)
- **Failing Tests:**
  - View mode preservation across project changes
  - Project settings persistence
  - State synchronization between time machine and project contexts
- **Action Items:**
  - [ ] Investigate test failures and root cause
  - [ ] Fix state management logic in useTimeMachineStore
  - [ ] Ensure all tests pass
  - [ ] Add regression tests for time machine state transitions
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-070] Missing Query Key Factory Pattern

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Query keys defined inline throughout the codebase with inconsistent patterns. This makes cache management harder and can lead to key conflicts.
- **Impact:** Harder to maintain cache, potential cache key conflicts, type safety issues
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-03-15
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** High
- **Risk:** Cache inconsistencies, difficult debugging, maintenance burden
- **Solution:** Create centralized query key factory following TanStack Query best practices
- **Reference Solution Created:** `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts`
- **Affected Features:** All features using TanStack Query (projects, WBEs, change orders, forecasts, etc.)
- **Action Items:**
  - [ ] Review and finalize query key factory pattern
  - [ ] Migrate all query hooks to use centralized keys
  - [ ] Update query invalidation logic
  - [ ] Add TypeScript types for query keys
  - [ ] Document query key patterns
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md), [TanStack Query Best Practices](https://tanstack.com/query/latest/docs/react/guides/query-keys)

#### [TD-071] No Optimistic Updates

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Mutations wait for server response before updating UI, causing slower perceived performance. No optimistic update patterns implemented across the application.
- **Impact:** Slower perceived performance, poor user experience during mutations
- **Estimated Effort:** 6 hours
- **Target Date:** 2026-03-15
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** High
- **Risk:** Poor user experience, especially on slow connections
- **Solution:** Implement optimistic update patterns using TanStack Query's `optimisticUpdater` and `onMutate` callbacks
- **Reference Solution Created:** `/home/nicola/dev/backcast_evs/frontend/src/api/utils/optimisticUpdates.ts`
- **Affected Mutations:** All create/update/delete mutations (projects, WBEs, change orders, etc.)
- **Action Items:**
  - [ ] Create optimistic update utilities
  - [ ] Implement optimistic updates for high-impact mutations (create WBE, update project, etc.)
  - [ ] Add rollback logic for failed mutations
  - [ ] Test optimistic update behavior
  - [ ] Document patterns for future mutations
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-072] Column Definitions Recreated Every Render

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** 116 lines of column definitions in `ProjectList.tsx` (lines 143-258) recreated on every render, causing unnecessary computation.
- **Impact:** Performance degradation, especially with large datasets
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-03-01
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** High
- **Risk:** Poor performance with large project lists
- **Solution:** Extract column definitions to custom hook with `useMemo`
- **Affected Files:**
  - `frontend/src/features/projects/components/ProjectList.tsx:143-258`
  - `frontend/src/features/users/components/UserList.tsx`
  - `frontend/src/features/wbes/components/WBEList.tsx`
- **Reference Solution Created:** `/home/nicola/dev/backcast_evs/frontend/src/features/projects/components/ProjectList.columns.tsx`
- **Action Items:**
  - [ ] Extract column definitions to separate files
  - [ ] Wrap in custom hooks with useMemo
  - [ ] Apply pattern to UserList and WBEList
  - [ ] Test performance improvement
  - [ ] Document pattern for future table components
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-073] Inconsistent Error Handling

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Some components use try-catch, others rely on mutation error handling. No centralized error handling pattern across the application.
- **Impact:** Inconsistent user experience, difficult to maintain, potential for unhandled errors
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-03-08
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** High
- **Risk:** Poor user experience, inconsistent error messages, potential for unhandled errors
- **Solution:** Create centralized error handling utilities with consistent patterns
- **Reference Solution Created:** `/home/nicola/dev/backcast_evs/frontend/src/utils/errorHandling.ts`
- **Affected Components:** All form components, mutation handlers, and API calls
- **Action Items:**
  - [ ] Design error handling pattern (user notification, logging, retry logic)
  - [ ] Create centralized error handling utilities
  - [ ] Migrate components to use centralized handling
  - [ ] Add error boundary components
  - [ ] Document error handling patterns
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-074] Missing useCallback/useMemo

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Event handlers and computed values recreated on every render in multiple components. This causes unnecessary re-renders of child components.
- **Impact:** Performance degradation, unnecessary re-renders
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-03-01
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** High
- **Risk:** Poor performance, especially in components with complex state
- **Solution:** Add `useCallback` for event handlers and `useMemo` for computed values
- **Affected Files:**
  - `frontend/src/features/projects/components/ProjectList.tsx`
  - `frontend/src/features/users/components/UserList.tsx`
  - `frontend/src/features/wbes/components/WBEList.tsx`
- **Action Items:**
  - [ ] Audit components for missing useCallback/useMemo
  - [ ] Add useCallback to event handlers
  - [ ] Add useMemo to computed values
  - [ ] Verify performance improvements
  - [ ] Add to code review checklist
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

---

### Medium Severity

#### [TD-016] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading for very large projects.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-02-01
- **Status:** 🔴 Open
- **Owner:** Full Stack Developer

#### [TD-057] MERGE Mode Branch Deletion Detection ✅

- **Source:** EVCS Documentation Compliance Analysis (2026-01-14)
- **Description:** `get_as_of()` with MERGE mode falls back to main branch even when entity is deleted on requested branch. The `_is_deleted_on_branch()` check may not properly detect deleted entities during fallback.
- **Impact:** Zombie check test `test_wbe_zombie_check_merge_mode_no_fallback` fails; deleted entities on branches incorrectly appear in MERGE mode queries
- **Estimated Effort:** 2 hours
- **Actual Effort:** 2 hours
- **Target Date:** 2026-01-20
- **Completed Date:** 2026-01-27
- **Status:** ✅ Completed
- **Owner:** Backend Developer
- **Resolution:** Fixed deletion detection in both `TemporalService._is_deleted_on_branch()` and `BranchableService.get_as_of()` to check temporal aspect (`deleted_at <= as_of`) instead of just checking if ANY deleted version exists. This ensures MERGE mode correctly handles:
  - Entities deleted BEFORE query time: No fallback to main (correct zombie behavior)
  - Entities deleted AFTER query time: Falls back to main (entity was still valid at query time)
- **Files Modified:**
  - `backend/app/core/versioning/service.py`: Added temporal check to `_is_deleted_on_branch()`
  - `backend/app/core/branching/service.py`: Added temporal check to MERGE mode deletion detection
- **Tests Added:**
  - `tests/unit/test_td57_deletion_detection.py`: Comprehensive temporal deletion tests
  - `tests/unit/test_td57_edge_case.py`: Edge case tests for temporal deletion
- **Documentation:** [EVCS Implementation Guide](../02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md), [Temporal Query Reference](../02-architecture/cross-cutting/temporal-query-reference.md)
- **Test File:** [tests/unit/test_zombie_checks.py](../../backend/tests/unit/test_zombie_checks.py)

#### [TD-062] Configure Pre-commit Hooks for Ruff Auto-fix

- **Source:** Code Quality Cleanup ACT phase (2026-01-19)
- **Description:** Ruff linting errors accumulated in codebase due to lack of automated checks before commits. Pre-commit hooks should automatically run `ruff check --fix` to catch and fix linting issues before they enter the codebase.
- **Impact:** Prevents linting errors from accumulating, reduces manual cleanup effort
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Tech Lead
- **Notes:** Should be configured to run on Python files only, with `--fix` option for auto-correctable issues

#### [TD-063] Add Zombie Check Tests for All Versioned Entities

- **Source:** Code Quality Cleanup ACT phase (2026-01-19)
- **Description:** Zombie check tests verify that soft-deleted entities correctly disappear from time-travel queries after their deletion timestamp, but remain visible for queries before deletion. Currently only implemented for forecasts.
- **Impact:** Ensures data integrity for time-travel queries across all versioned entities
- **Estimated Effort:** 1 day
- **Target Date:** 2026-01-22
- **Status:** 🔴 Open
- **Owner:** QA Engineer
- **Notes:** Should be added for Projects, WBEs, CostElements, ScheduleBaselines, and other versioned entities. Pattern documented in temporal-query-reference.md

#### [TD-064] Docker Compose for Local Development

- **Source:** Temporal Context Consistency ACT phase (2026-01-19)
- **Description:** OpenAPI client regeneration failed during frontend implementation due to backend server inaccessibility (port 8000 conflict or server configuration issue). A standardized Docker Compose setup would provide consistent local development environment with backend, frontend, and database services.
- **Impact:** Prevents development blockages, ensures backend dev server is always accessible for frontend work
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-01-22
- **Status:** 🔴 Open
- **Owner:** Tech Lead
- **Notes:** Should include backend (FastAPI), frontend (Vite dev server), and PostgreSQL services. Document standard startup sequence in developer onboarding guide.

#### [TD-065] Automate OpenAPI Client Generation in CI/CD

- **Source:** Temporal Context Consistency ACT phase (2026-01-19)
- **Description:** Manual type update was required when OpenAPI spec regeneration failed (backend server returned 404). An automated process to regenerate frontend types from backend OpenAPI spec would prevent contract misalignment.
- **Impact:** Ensures frontend-backend contract alignment, reduces manual work
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-23
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Notes:** Add npm script to regenerate types from running backend, integrate into CI pipeline to run on every backend commit. Fail build if contract changes detected.

#### [TD-066] Frontend ESLint Errors

- **Source:** EVM Analyzer Master-Detail UI ACT phase (2026-01-23)
- **Description:** 146 ESLint errors across multiple frontend files. None are in EVM feature code (`src/features/evm/`), which has 0 errors. All errors are in pre-existing legacy code.
- **Error Breakdown:**
  - `@typescript-eslint/no-explicit-any`: ~130 (Medium severity)
  - `@typescript-eslint/no-unused-vars`: ~10 (Low severity)
  - `react-refresh/only-export-components`: ~4 (Low severity)
  - `react-hooks/exhaustive-deps`: ~2 (Low severity)
- **Affected Files:** `src/api/client.ts`, `src/features/projects/`, `src/features/wbes/`, and various utility files
- **Impact:** `any` types reduce type safety; noisy error output makes it harder to spot new issues
- **Estimated Effort:** ~1 week
- **Target Date:** Post-E05-U04 iteration
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Resolution Strategy:** Incremental refactor - fix errors file-by-file during feature work, enforce zero new errors
- **Prevention:** Pre-commit hooks for ESLint, CI/CD gate for modified files, code review checklist item
- **Documentation:** [EVM Analyzer CHECK phase](./iterations/2026-01-22-evm-analyzer-master-detail-ui/03-check.md), [Frontend Coding Standards](../../02-architecture/frontend/coding-standards.md)

#### [TD-068] Impact Analysis Timeout Configuration ✅

- **Source:** Change Order Workflow Recovery (2026-02-06)
- **Description:** Impact analysis now has a 5-minute timeout, but this is hardcoded. Should be configurable via environment variables or settings.
- **Impact:** Low - unable to adjust timeout for different environments without code changes
- **Estimated Effort:** 1 hour
- **Actual Effort:** N/A
- **Target Date:** 2026-02-06
- **Completed Date:** 2026-02-06
- **Status:** ✅ Completed
- **Owner:** Backend Developer
- **Resolution:** Timeout configuration implemented in 2026-02-06-change-order-workflow-recovery iteration
- **Documentation:** [Change Order Workflow Recovery Iteration](./iterations/2026-02-06-change-order-workflow-recovery/)

#### [TD-075] Missing React.memo Optimizations

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Multiple components re-render unnecessarily when parent updates. No `React.memo` wrappers applied to performance-critical components.
- **Impact:** Performance degradation in data-heavy components, unnecessary re-renders
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-03-15
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Medium
- **Risk:** Poor performance with large datasets
- **Solution:** Add `React.memo` to performance-critical components with proper prop comparison
- **Affected Components:** All list components, cards, and data display components
- **Example Component:** `frontend/src/features/change-orders/components/KPICards.tsx`
- **Action Items:**
  - [ ] Identify performance-critical components
  - [ ] Add React.memo wrappers with proper comparison functions
  - [ ] Verify performance improvements
  - [ ] Add to frontend coding standards
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-076] Large Component Files

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** `ProjectList.tsx` is 378 lines and doing too much (table, columns, modal, history drawer). Component violates single responsibility principle.
- **Impact:** Difficult to maintain, test, and understand; high cognitive load
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-03-08
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Medium
- **Risk:** Maintainability issues, difficult to onboard new developers
- **Solution:** Extract column definitions and sub-components into separate files
- **Affected Files:**
  - `frontend/src/features/projects/components/ProjectList.tsx` (378 lines)
  - Other large components (need audit)
- **Action Items:**
  - [ ] Audit all component files for size violations (>300 lines)
  - [ ] Extract column definitions to separate files (see TD-072)
  - [ ] Extract sub-components (modals, drawers, etc.)
  - [ ] Create reusable patterns for component organization
  - [ ] Update coding standards with max file size guidelines
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-077] Reusable Form Field Components

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Similar form fields repeated across components. No standardized form field components for common patterns (text inputs, selects, date pickers, etc.).
- **Impact:** Code duplication, inconsistency, higher maintenance burden
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-03-15
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Medium
- **Risk:** Inconsistent UX, code duplication, maintenance burden
- **Solution:** Create reusable form field components with consistent validation, styling, and error handling
- **Reference Solution Created:** `/home/nicola/dev/backcast_evs/frontend/src/components/forms/FormField.tsx`
- **Affected Components:** All form components across the application
- **Action Items:**
  - [ ] Design form field component API
  - [ ] Implement common form field types (text, select, date, number, etc.)
  - [ ] Add consistent validation patterns
  - [ ] Migrate existing forms to use new components
  - [ ] Document form field patterns
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-078] Missing Barrel Exports

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Some features lack proper `index.ts` barrel exports, causing long import paths and inconsistent imports across the codebase.
- **Impact:** Poor developer experience, inconsistent imports, refactoring difficulty
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-03-01
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Medium
- **Risk:** Developer friction, inconsistent code organization
- **Solution:** Create barrel exports for all features with consistent patterns
- **Affected Features:** Features lacking `index.ts` barrel exports (needs audit)
- **Action Items:**
  - [ ] Audit all features for missing barrel exports
  - [ ] Create index.ts files with consistent export patterns
  - [ ] Update imports to use barrel exports
  - [ ] Document barrel export patterns in coding standards
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

---

### Low Severity

#### [TD-059] WBE Hierarchical Filter API Response Format

- **Source:** Backend Test Suite Run (2026-01-14)
- **Description:** `test_get_wbes_param_filter` fails with `TypeError: string indices must be integers, not 'str'` when querying `/api/v1/wbes?parent_wbe_id=null`. The API response format doesn't match expected list of dictionaries structure.
- **Impact:** Hierarchical WBE filtering (parent_wbe_id parameter) returns incorrect response format; test blocked
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Notes:**
  - Test expects: List of WBE dictionaries with `code` field
  - Actual response: Unknown type (likely error dict or string)
  - May be related to parameter parsing for `parent_wbe_id=null` string value
  - Pre-existing issue, unrelated to temporal query changes
- **Test File:** [tests/api/test_wbes.py](../../backend/tests/api/test_wbes.py#L548)
- **Error:** `TypeError: string indices must be integers, not 'str'` at `assert any(w["code"] == "TF-1" for w in data_null)`

#### [TD-050] Change Order API Error Path Coverage

- **Source:** Phase 1 Change Orders CHECK phase (2026-01-12)
- **Description:** Change Order API routes have 56.63% coverage. Error paths not fully tested (40+ uncovered lines).
- **Impact:** Reduced confidence in error handling
- **Estimated Effort:** 4 hours
- **Target Date:** Phase 2 (2026-01-19)
- **Status:** 🔴 Open
- **Owner:** QA Engineer
- **Notes:** Critical paths covered, error paths can be addressed in Phase 2
- **Documentation:** [Phase 1 CHECK](./iterations/2026-01-11-change-orders-implementation/phase1/03-check.md)

#### [TD-052] Test Execution Location Documentation

- **Source:** Phase 1 Change Orders ACT phase (2026-01-12)
- **Description:** Tests must be run from `backend/` directory, not project root. Alembic config path issue causes confusion.
- **Impact:** Developers may run tests incorrectly, get confusing errors
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-01-15
- **Status:** 🔴 Open
- **Owner:** Tech Lead
- **Solution:** Add note to project README about test execution location
- **Documentation:** [Phase 1 ACT](./iterations/2026-01-11-change-orders-implementation/phase1/04-act.md)

#### [TD-053] Domain Model Test Coverage

- **Source:** Branch Mode Support ACT phase (2026-01-13)
- **Description:** Backend coverage 56.81% (below 80% target). Domain models (mostly data classes) lack tests. Service layer well covered.
- **Impact:** Reduced overall coverage metric
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-30
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Notes:** Data classes provide minimal value to test. Acceptable baseline for this iteration.
- **Documentation:** [Branch Mode CHECK](./iterations/2026-01-12-merge-isolation-strategies/03-check.md)

#### [TD-079] Inline Styles Instead of Styled Components

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Inline styles used throughout the codebase instead of styled components or CSS modules. Makes maintenance harder and reduces consistency.
- **Impact:** Harder to maintain styles, inconsistent styling approach, difficult to theme
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-03-31
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Low
- **Risk:** Maintainability issues, styling inconsistencies
- **Solution:** Extract inline styles to styled components or CSS modules
- **Example:** `frontend/src/features/change-orders/components/KPICards.tsx` - `style={{ marginBottom: 8, color: "#8c8c8c" }}`
- **Affected Files:** Throughout the codebase (needs audit)
- **Action Items:**
  - [ ] Audit codebase for inline style usage
  - [ ] Create styled component patterns for common styles
  - [ ] Migrate inline styles to styled components incrementally
  - [ ] Document styling patterns in coding standards
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

#### [TD-080] Unused ESLint Disable Directives

- **Source:** React Best Practices Review (2026-02-21)
- **Description:** Unused `/* eslint-disable */` directives in multiple auto-generated files. Clutters code and may hide real issues.
- **Impact:** Code cleanliness, potential for hiding real linting issues
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-03-01
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Low
- **Risk:** Minor - code cleanliness
- **Solution:** Remove unused directives or add files to `.eslintignore`
- **Affected Files:** Auto-generated files with unused ESLint disable directives
- **Action Items:**
  - [ ] Scan for unused ESLint disable directives
  - [ ] Remove unused directives
  - [ ] Add auto-generated files to `.eslintignore` if appropriate
  - [ ] Update code generation scripts to avoid adding directives
- **Documentation:** [REACT_BEST_PRACTICES_REVIEW.md](../../frontend/REACT_BEST_PRACTICES_REVIEW.md)

---

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
- Track trends and prevent accumulation

---

## Technical Debt Policy

### Adding New Items

When adding new technical debt items:

1. Document the problem clearly
2. Assess priority (High/Medium/Low)
3. Identify affected components
4. Propose solution options
5. Estimate effort
6. Create action items

### Resolving Items

When resolving technical debt:

1. Reference the debt item in commit messages
2. Update the Status field
3. Document the solution
4. Close related issues/tickets

### Review Cadence

- Review high-priority items monthly
- Review medium/low-priority items quarterly
- Update estimates as needed
- Archive resolved items annually
