# Current Iteration

**Iteration:** E2E Test Stabilization & Debt Paydown

**Start Date:** 2026-01-09
**End Date:** 2026-01-09
**Status:** ✅ **COMPLETE**

---

## Goal

Resolve E2E failures caused by API changes (Server-Side Filtering) and address technical debt to ensure a stable testing baseline.

**Key Focus Areas:**

1. **E2E Tests:** Update mocking and assertions for `PaginatedResponse`.
2. **Backend Filtering:** Fix type casting issues in `FilterParser`.
3. **Frontend Search:** Ensure search parameters are passed to API.

---

## Stories in Scope

| Story                     | Points | Priority | Status  | Actual Time | Dependencies |
| ------------------------- | ------ | -------- | ------- | ----------- | ------------ |
| [TD-003] Update E2E Tests | 3h     | High     | ✅ Done | 1.5h        | None         |

---

## Success Criteria

- [x] All E2E tests pass (`projects_crud`, `wbes_crud`, `cost_elements_crud`)
- [x] Backend tests pass (153/153)
- [x] Type casting works for integer/boolean filters
- [x] Search functionality works in Cost Elements table

---

## Iteration Records

- **PLAN:** [01-plan.md](iterations/2026-01-09-e2e-server-side-filtering/01-plan.md)
- **DO:** [02-do.md](iterations/2026-01-09-e2e-server-side-filtering/02-do.md)
- **CHECK:** [03-check.md](iterations/2026-01-09-e2e-server-side-filtering/03-check.md)
- **ACT:** [04-act.md](iterations/2026-01-09-e2e-server-side-filtering/04-act.md)

---

## Previous Iterations

- **[2026-01-08] Frontend Table Harmonization - Phase 2:** ✅ Complete (100%)

---

## Next Iteration Planning

**Proposed Focus Areas:**

### Option 1: Technical Debt Paydown (Recommended)

- **TD-012:** E2E Test Data Isolation (3h)
- **TD-013:** FilterParser Error Messages (2h)
- **TD-014:** Frontend Filter Type Safety (3h)
- **Estimated Effort:** 8 hours
- **Benefit:** Improved test reliability and type safety

### Option 2: Feature Development

- Advanced filtering UI (Filter Builder)
- Saved filter presets
- Export filtered results
- **Estimated Effort:** 8-12 hours
- **Benefit:** Enhanced user experience

### Option 3: Performance Optimization

- Database indexes for filtered columns
- Query result caching
- Performance profiling
- **Estimated Effort:** 6-8 hours
- **Benefit:** Faster query response times

**Recommendation:** Option 1 (Technical Debt) to maintain code quality and test reliability before adding new features.

---

## Backlog

### Technical Debt (See [Technical Debt Register](technical-debt-register.md))

- [TD-012] E2E Test Data Isolation (3h) - High Priority
- [TD-013] FilterParser Error Messages (2h)
- [TD-014] Frontend Filter Type Safety (3h)
- [TD-015] useTableParams Type Safety (2h)
- [TD-016] Performance Optimization - Large Projects (3h)
- [TD-017] Remaining Page-Level API Adapters (1h)

### Feature Enhancements

- Advanced filter UI with filter builder
- Saved filter presets per user
- Export functionality for filtered results
- Bulk operations on filtered items
- Filter history and recent filters

### Performance

- Add database indexes for commonly filtered columns
- Implement query result caching
- Profile and optimize slow queries
- Implement virtual scrolling for large tables

### Testing

- Add dedicated search functionality tests
- Add filter combination tests
- Add pagination edge case tests
- Implement visual regression testing
