# Technical Debt: Update E2E Tests for Server-Side Filtering

**ID:** TD-003  
**Created:** 2026-01-08  
**Priority:** Medium  
**Estimated Effort:** 1 hour  
**Status:** Closed

---

## Context

Phase 2 implementation added server-side filtering, search, and sorting for Projects, WBEs, and Cost Elements. The API now returns paginated responses with `{items, total, page, per_page}` format instead of plain arrays.

The E2E test suite needs to be updated to:

1. Handle new API response format
2. Test search functionality
3. Test filter interactions
4. Test sorting behavior
5. Verify pagination UI

---

## Current State

**E2E Tests Status:**

- ✅ **Projects:** `projects_crud.spec.ts` is fully updated with search, filter, sort, pagination, and API format checks.
- ✅ **WBEs:** `wbe_crud.spec.ts` is fully updated with search, filter, sort, pagination, and API format checks.
- ✅ **Cost Elements:** `cost_elements_crud.spec.ts` is fully updated.

**Test Files Affected:**

- `frontend/tests/e2e/cost_elements_crud.spec.ts`

---

## Required Changes (Cost Elements Only)

### 1. Verification of API Response Format

```typescript
test("should verify cost elements api response format", async ({ page }) => {
  // ...
  expect(data).toHaveProperty("items");
  expect(data).toHaveProperty("total");
  // ...
});
```

### 2. Filter, Sort, and Pagination Tests

Need to add specific tests for:

- Filtering by Cost Element Type
- Sorting by Code/Name
- Pagination controls
- Combined operations

---

## Acceptance Criteria

- [x] Projects tests updated (Done)
- [x] WBEs tests updated (Done)
- [x] Cost Elements API response format assertions updated
- [x] Cost Elements Filter tests added
- [x] Cost Elements Sorting tests added
- [x] Cost Elements Pagination tests added
- [x] Cost Elements Combined operations test
- [x] All tests pass consistently

---

## Implementation Plan

1. **Update `cost_elements_crud.spec.ts`** (~1h)
   - Add API helpers for efficient data setup (Dept, Type, Project, WBE)
   - Implement new test cases
   - Ensure existing CRUD test remains valid

---

## Dependencies

- Phase 2 implementation (✅ Complete)
- Backend running on port 8020
- Frontend running on port 5173

---

## Notes

- `projects_crud.spec.ts` and `wbe_crud.spec.ts` serve as the reference implementation.
- Use `page.request` for setup to avoid slow UI interactions in the new tests.

---

**Assignee:** TBD  
**Target Completion:** This iteration  
**Blocked By:** None  
**Blocks:** None
