# ACT Phase: Standardization of Time Travel Lists

## Purpose

Standardize use of `_apply_bitemporal_filter` and document "Valid Time" semantics.

---

## 1. Prioritized Improvement Implementation

### Critical Issues

- None identified. Validation successful.

### High-Value Refactoring

- **Completed:** `TemporalService._apply_bitemporal_filter` is now the single source of truth for list filtering.

---

## 2. Pattern Standardization

| Pattern               | Description                                                                      | Standardize? |
| :-------------------- | :------------------------------------------------------------------------------- | :----------- |
| **Valid Time Filter** | Use `_apply_bitemporal_filter` for all list/search endpoints supporting `as_of`. | **YES**      |
| **Zombie Check TDD**  | Use the "Create -> Delete -> Query Past" test pattern to verify history.         | **YES**      |

### Actions

- [x] Implemented `_apply_bitemporal_filter` in `TemporalService`.
- [ ] Create `docs/02-architecture/cross-cutting/temporal-query-reference.md` to document the pattern.
- [ ] Update `docs/03-project-plan/sprint-backlog.md` to mark iteration complete.

---

## 3. Documentation Updates Required

| Document                                            | Update Needed                                                                     | Priority |
| :-------------------------------------------------- | :-------------------------------------------------------------------------------- | :------- |
| `docs/02-architecture/cross-cutting/temporal-query-reference.md` | **Create New**. Explain Valid vs System time, and how to use the standard filter. | High     |
| `docs/03-project-plan/sprint-backlog.md`            | Mark items as Done.                                                               | High     |

---

## 4. Technical Debt Ledger

**Debt Resolved:**

- **Standardization:** Removed ad-hoc `as_of` logic in `ProjectService` and `CostElementService`.

**Net Debt Change:** Reduced complexity, increased consistency.

---

## 5. Process Improvements

**What Worked Well:**

- **TDD for Mechanics:** Writing the "Zombie" test first clarified the exact requirements for the SQL filter.
- **Service Layering:** Pushing logic up to `TemporalService` was the right move.

**Refinements:**

- Explicitly check "deleted" status during TDD (I initially missed checking `deleted_at` behavior in the base query refactor).

---

## 8. Next Iteration Implications

- **Users & Departments:** Can now easily add `as_of` support to `Users` and `Departments` using the same pattern.
- **Frontend History:** The frontend components for History are reliable; we can trust the API response.

---

## 10. Concrete Action Items

- [ ] Create `docs/02-architecture/cross-cutting/temporal-query-reference.md`.
- [ ] Update Sprint Backlog.

**Date Completed:** 2026-01-11
