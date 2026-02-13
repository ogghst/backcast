# Technical Debt Register

**Last Updated:** 2026-02-07
**Total Debt Items:** 10 (24 completed)
**Total Estimated Effort:** 55 hours
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
