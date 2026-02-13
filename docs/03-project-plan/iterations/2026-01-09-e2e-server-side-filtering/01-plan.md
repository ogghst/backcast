# Plan: Update E2E Tests for Server-Side Filtering

## 1. Objective

Update the End-to-End (E2E) test suite to support the newly implemented server-side filtering and pagination in the backend APIs. ensure all tests pass with the new `PaginatedResponse` structure.

## 2. Context

In the previous iteration ("Frontend Table Harmonization - Phase 2"), the backend API endpoints for Projects, WBEs, and Cost Elements were updated to return a paginated response structure:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

Previously, these endpoints returned a simple list `[...]`. The frontend application code has been updated, but the E2E tests (Playwright) which often mock responses or inspect network traffic, have not been updated.

## 3. Analysis

### Impacted Areas

1.  **Network Interception/Mocking:** Any tests using `page.route()` to mock API responses for `/api/v1/projects`, `/api/v1/wbes`, or `/api/v1/cost-elements` need to be updated to return the paginated structure.
2.  **Response Verification:** Tests that inspect response bodies (e.g., `response.json()`) to assert on data (count, content) will fail because they expect an array but will receive a dict/object.
3.  **Pagination:** Navigation steps might be needed if tests rely on finding an item that is now on page 2 (though unlikely for test data sizes, beneficial to verify).

### Impacted Test Files

Based on recent runs and codebase knowledge:

- `tests/e2e/projects_crud.spec.ts`
- `tests/e2e/wbes_crud.spec.ts`
- `tests/e2e/cost_elements_crud.spec.ts`
- `tests/e2e/server_side_filtering.spec.ts` (if logic exists or needs creation)

## 4. Implementation Plan

1.  **Audit Failures:** Run the full E2E suite to capture the baseline of failures.
2.  **Update Mocks:** grep for `json: [` or usage of `route.fulfill` in `tests/e2e` and wrap array responses in `{ items: [...], total: ... }`.
3.  **Update Assertions:** Fix any code stripping `items` from the response or expecting `length` on the root object.
4.  **Verify:** Run the suite again to ensure green.

## 5. Success Criteria

- All E2E tests pass.
- No regression in test execution time.
