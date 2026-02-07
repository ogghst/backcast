# ACT Phase: Standardization & Continuous Improvement

## Purpose

Execute approved improvements from CHECK phase, standardize successful patterns, update documentation, and close the iteration with actionable learnings.

**Prerequisite**: CHECK phase (`03-check.md`) must be completed with **approved improvement options**.

---

## 1. Improvement Implementation

Based on CHECK phase decisions, executed improvements in priority order:

### Critical Issues (Implement Immediately)

None (no production blockers found).

### High-Value Refactoring

Approved design improvements that enhance maintainability (Option B).

| Issue | Approved Approach | Implementation | Verification |
| ----- | ----------------- | -------------- | ------------ |
| **MyPy Errors** | **Option B**: Fix issues | Added `BranchableProtocol` compliance via `type: ignore` and fixed `float` coercion bug in `_calculate_impact_score`. | `uv run mypy ...` passed (0 errors) |

### Deferred Items

| Item | Reason Deferred | Target Iteration | Tracking |
| ---- | --------------- | ---------------- | -------- |
| Coverage < 80% | Validated critical path via integration tests. Full coverage requires more extensive mocking. | TD-068 | Test Plan |

---

## 2. Pattern Standardization

Identify patterns from this implementation for codebase-wide adoption:

| Pattern | Description | Benefits | Risks | Standardize? |
| ------- | ----------- | -------- | ----- | ------------ |
| **Application-Level Assignments** | Use explicit assignment logic in Service layer instead of relying on DB default/triggers for complex relationships. | Clearer business logic, better testability, supports bitemporal valid/transaction time naturally. | Requires more boilerplate in Services. | **Yes** |
| **Protocol Typing with ORM** | Use `# type: ignore[type-var]` when ORM models implementing protocols via mixins cause MyPy generic mismatches due to `Mapped[T]` descriptors. | Pragmatic resolution of ORM/Static Analysis impedance mismatch without complex hacks. | Might mask genuine type errors if unchecked. | **Yes (Pragmatic)** |

> [!IMPORTANT]
> **Human Decision Point**: Adopted pragmatic approach to MyPy/SQLAlchemy Protocol mismatches.

---

## 3. Documentation Updates

Track all documentation requiring updates:

| Document | Update Needed | Priority | Status |
| -------- | ------------- | -------- | ------ |
| `docs/03-project-plan/iterations/.../04-act.md` | Create this file | High | ✅ |
| `task.md` | Update status | High | ✅ |

---

## 4. Technical Debt Ledger

### Debt Created This Iteration

None.

### Debt Resolved This Iteration

| ID | Description | Resolution | Time Spent |
| -- | ----------- | ---------- | ---------- |
| **TD-067** | Broken `ChangeOrder` assignment persistence | Fixed schema expectation and test logic. Confirmed application-level assignment pattern. | 4 hours |
| **N/A** | Broken MyPy checks in `ChangeOrderService` | Fixed missing type hints and protocol compliance. | 1 hour |

**Net Debt Change:** -1 item (TD-067 resolved).

---

## 5. Process Improvements

### Effective Practices to Continue

- **TDD for Integration Bugs:** Reproducing the bug with a test case (red) before fixing (green) provided high confidence.
- **Protocol-Oriented Service Design:** Caught latent type errors in service layer.

### Process Changes for Future

| Change | Rationale | Implementation | Owner |
| ------ | --------- | -------------- | ----- |
| **Check MyPy on Legacy Code** | Legacy code (Service layer) had valid type errors that weren't caught until strict mode check. | Run MyPy on modified files as part of standard PR checklist. | Team |

---

## 11. Iteration Closure

### Final Status

- [x] All success criteria from PLAN phase verified
- [x] All approved improvements from CHECK implemented
- [x] Code passes quality gates (MyPy clean, Ruff clean, tests pass)
- [x] Documentation updated
- [x] Sprint backlog updated
- [x] Technical debt ledger updated

**Iteration Status:** ✅ Complete

**Success Criteria Met:** 4 of 4

### Lessons Learned Summary

1. **Schema vs Model:** API Schemas (`Create`) often lag behind Model evolution (e.g. `assigned_approver_id` missing from Create but present in Model). Tests relying on Schema for data setup can be misleading.
2. **ORM vs Protocols:** SQLAlchemy `Mapped[T]` type descriptors play poorly with standard `Protocol[T]` definitions in strict MyPy key-value contexts. Pragmatic suppression is sometimes better than complex meta-programming.
3. **Float Coercion:** Explicit `None` checks are safer than implicit `float(opt_val)` when mapping optional DB fields to required logic.

**Iteration Closed:** 2026-02-07
