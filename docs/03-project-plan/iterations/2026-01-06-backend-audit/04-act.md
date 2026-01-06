# ACT Phase: Standardization and Continuous Improvement

**Date:** 2026-01-06
**Iteration:** Backend Audit Gap Fix

## Purpose

Decide actions based on learnings, standardize successful patterns, and implement improvements.

---

## 1. Prioritized Improvement Implementation

Based on CHECK phase decisions, execute improvements:

### Critical Issues (Implement Immediately)

- None. Verification passed with no security or data integrity issues.

### High-Value Refactoring

- None required immediately.

### Technical Debt Items

- **TD-AUDIT-01**: Refactor `tests/unit/core/versioning/test_audit.py` to use a shared mock entity definition instead of defining `MockAuditEntity` in-line. This will be useful when testing other mixins (e.g., Branchable) that often copy-paste this mock.

---

## 2. Pattern Standardization

Identify patterns from this implementation that should be adopted codebase-wide:

| Pattern                       | Description                                                                                                    | Benefits                                                               | Risks                                                                | Standardize?       |
| :---------------------------- | :------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------- | :------------------------------------------------------------------- | :----------------- |
| **Command-Context Injection** | Passing `actor_id` (and potentially other context) via `UseCase/Service` to `Command` constructors explicitly. | Explicit audit trail, easier testing (no global context), type safety. | Requires wiring through multiple layers (API -> Service -> Command). | **Yes (Option A)** |
| **Mixin-Based Auditing**      | Using `VersionableMixin` to standardize audit columns (`created_by`, `deleted_by`) across all entities.        | DRY, consistency, automatic migration support.                         | Changes to mixin affect all tables (migrations can be heavy).        | **Yes (Option A)** |
| **Strict Async pytest**       | Using `@pytest_asyncio.fixture` always.                                                                        | Avoids future pytest depreciation warnings/errors.                     | None.                                                                | **Yes (Option A)** |

---

## 3. Documentation Updates Required

Track what documentation needs updating:

| Document                                                   | Update Needed                                                       | Priority | Assigned To | Completion Date |
| :--------------------------------------------------------- | :------------------------------------------------------------------ | :------- | :---------- | :-------------- |
| `docs/02-architecture/contexts/evcs-core/architecture.md`  | Update "Command Pattern" section to include `actor_id` requirement. | Medium   | AI          | 2026-01-06      |
| `docs/02-architecture/cross-cutting/security-practices.md` | Mention "Audit Logging" via `created_by`/`deleted_by`.              | Low      | AI          | 2026-01-06      |

**Specific Actions:**

- [x] Update `VersionableMixin` documentation (implicitly done via code)
- [ ] Update `evcs-core` documentation to reflect the new `actor_id` flow.

---

## 4. Technical Debt Ledger

### Debt Created This Iteration

| Item            | Description                        | Impact            | Estimated Effort to Fix | Target Date    |
| :-------------- | :--------------------------------- | :---------------- | :---------------------- | :------------- |
| **TD-AUDIT-01** | Inline `MockAuditEntity` in tests. | Low (duplication) | 0.5 days                | Next Iteration |

### Debt Resolved This Iteration

| Item                  | Resolution                              | Time Spent |
| :-------------------- | :-------------------------------------- | :--------- |
| **Backend Audit Gap** | Implemented `created_by` / `deleted_by` | 4 hours    |

**Net Debt Change:** +1 item (minor), -1 Critical Gap (Audit)

**Action:** Update `docs/02-architecture/02-technical-debt.md`

---

## 5. Process Improvements

### Process Retrospective

**What Worked Well:**

- **TDD for Schema Changes**: Writing the test expecting specific fields forced clarity on nullable vs non-nullable decisions before DB migration.
- **Incremental Migration**: Adding column -> backfill -> alter column worked perfectly to avoid "NOT NULL" errors on existing data.

**What Could Improve:**

- **Test Fixture Discovery**: Wasted time guessing fixture names (`backend_evs_test` vs `db_session`). Should verify `conftest.py` earlier.
- **Migration Idempotency**: `create_table` failed on retry. Always use defensive `IF NOT EXISTS` or clean-up steps in development migrations unless strictly production-bound.

**Prompt Engineering Refinements:**

- AI needs to establish _fixture availability_ before writing tests. (e.g., "Check `conftest.py` for fixtures").

### Proposed Process Changes

| Change                   | Rationale                  | Implementation                                    | Owner |
| :----------------------- | :------------------------- | :------------------------------------------------ | :---- |
| **Check Fixtures First** | Prevent test setup errors. | Add "Review `conftest.py`" step to "Plan" prompt. | AI    |

---

## 6. Knowledge Gaps Identified

### Team Learning Needs

- **SQLAlchemy AsyncIO State**: Attempting to access attributes on expired objects in sync context (`MissingGreenlet`).
- **Solution**: Explicitly capture data before `await update/delete` or use `await session.refresh()`.

---

## 7. Metrics for Next PDCA Cycle

| Metric                     | Baseline (Pre-Change) | Target               | Actual     | Measurement Method |
| :------------------------- | :-------------------- | :------------------- | :--------- | :----------------- |
| Audit Coverage             | 0%                    | 100% (Core Entities) | 100%       | Unit Tests         |
| Test Coverage (Versioning) | X%                    | >80%                 | >85% (Est) | Coverage Tool      |

---

## 8. Next Iteration Implications

**What This Iteration Unlocked:**

- **Full Traceability**: We can now implement "History View" with user names, "Blame" views, and compliance auditing.
- **Security Foundation**: Row-level security (RLS) policies could be built on top of `created_by` if needed.

**New Priorities Emerged:**

- **Frontend Integration**: Frontend project list/details needs to _show_ this Creator info. (Currently just backend storage).

---

## 9. Concrete Action Items

- [x] Merge PR / Apply Changes (Already applied to local).
- [ ] Update `02-technical-debt.md` with TD-AUDIT-01.
- [ ] Update Architecture documentation with Audit pattern.
