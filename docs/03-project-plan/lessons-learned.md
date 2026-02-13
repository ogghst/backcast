# Lessons Learned

**Last Updated:** 2026-01-09

This document captures key learnings from project iterations to improve future development practices.

---

## Table of Contents

- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Testing](#testing)
- [Architecture & Design](#architecture--design)
- [Process & Workflow](#process--workflow)

---

## Backend Development

### Type Casting in Generic Filters

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** PostgreSQL strictly enforces type matching. Comparing `integer = varchar` causes SQL errors.

**Learning:** When building generic filtering systems, always validate and cast filter values against the database schema types.

**Solution:**

```python
# Inspect SQLAlchemy column metadata
col_type = column.type.python_type

# Cast values appropriately
if col_type is int:
    casted_values = [int(v) for v in values]
elif col_type is bool:
    casted_values = [parse_bool(v) for v in values]
```

**Best Practice:** Use SQLAlchemy's type system to automatically handle type conversions in generic code.

---

### API Response Consistency

**Iteration:** Server-Side Filtering (2026-01-08)

**Problem:** Some endpoints returned arrays, others returned `PaginatedResponse`, causing frontend confusion.

**Learning:** Consistent API response structures are critical for maintainability.

**Solution:** Standardize all list endpoints to return `PaginatedResponse`:

```python
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

**Best Practice:** Document response formats in OpenAPI schema and enforce consistency through code generation.

---

## Frontend Development

### Search Parameter Integration

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** Search UI existed but search term wasn't being passed to API calls.

**Learning:** When adding server-side features, verify the entire data flow from UI → Hook → API → Backend.

**Solution:** Ensure all query parameters from `useTableParams` are included in API calls:

```typescript
const queryParams = {
  pagination: tableParams.pagination,
  sortField: tableParams.sortField,
  sortOrder: tableParams.sortOrder,
  filters: tableParams.filters,
  search: tableParams.search, // Don't forget this!
  branch: currentBranch,
};
```

**Best Practice:** Create integration tests that verify UI actions trigger correct API calls.

---

### Type Safety in Generic Hooks

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** `useTableParams` and filter types use `Record<string, any>`, losing type safety.

**Learning:** Generic hooks should accept type parameters to maintain compile-time safety.

**Recommendation:** Refactor to:

```typescript
export const useTableParams<T extends object>() => {
  // Type-safe filters based on T
}
```

**Best Practice:** Use TypeScript generics extensively in reusable hooks and utilities.

---

## Testing

### E2E Test Pagination Awareness

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** Tests assumed newly created items would appear on page 1, but pagination pushed them to later pages.

**Learning:** E2E tests must be resilient to data pollution from concurrent/previous test runs.

**Solution:** Use search to isolate test data before asserting visibility:

```typescript
// Instead of assuming item is on page 1
await expect(page.locator(`text=${itemName}`)).toBeVisible();

// Use search to find it
await searchInput.fill(itemName);
await waitForSearchResponse();
await expect(page.locator(`text=${itemName}`)).toBeVisible();
```

**Best Practice:** Design tests to be independent of database state and pagination.

---

### Dropdown Stability in E2E Tests

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** Clicking dropdown items immediately after opening caused "element detached" errors.

**Learning:** Ant Design dropdowns need time to render and attach to DOM.

**Solution:**

```typescript
await page.click("#dropdown-trigger");
await page.waitForSelector(".ant-select-dropdown", { state: "visible" });
await page.waitForTimeout(300); // Small delay for stability
await page.click(".ant-select-item");
```

**Best Practice:** Always wait for dropdowns/modals to be fully rendered before interacting.

---

### Test Data Isolation

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** E2E tests share database state, causing occasional flakiness.

**Learning:** Shared state between tests is a major source of flakiness.

**Recommendation:** Implement one of:

1. Database transactions with rollback after each test
2. Test data cleanup hooks
3. Separate test databases per worker

**Best Practice:** Design tests to be fully isolated and order-independent.

---

## Architecture & Design

### Generic vs. Specific Implementations

**Iteration:** Multiple iterations

**Learning:** Generic implementations (like `FilterParser`) need robust error handling and type safety.

**Best Practice:**

- Provide clear error messages for edge cases
- Use type introspection when possible
- Fallback gracefully when types can't be determined
- Document supported types and limitations

---

### Server-Side vs. Client-Side Processing

**Iteration:** Server-Side Filtering (2026-01-08)

**Learning:** Moving filtering/sorting/pagination to server improves performance but requires careful coordination.

**Checklist for Server-Side Features:**

- [ ] Backend implements feature correctly
- [ ] Frontend passes parameters correctly
- [ ] API response format is documented
- [ ] Frontend handles response correctly
- [ ] Tests verify end-to-end flow
- [ ] Error handling is robust

**Best Practice:** Implement server-side features incrementally, testing each layer.

---

## Process & Workflow

### PDCA Documentation

**Iteration:** All iterations

**Learning:** Structured PDCA documentation prevents context loss and improves iteration quality.

**Best Practice:**

- **PLAN:** Analyze problem, define approach
- **DO:** Document implementation details
- **CHECK:** Verify results, capture learnings
- **ACT:** Update debt register, plan next steps

**Benefit:** Future developers can understand decisions and avoid repeating mistakes.

---

### Test-Driven Debugging

**Iteration:** E2E Test Stabilization (2026-01-09)

**Learning:** Running tests after each change provides immediate feedback and prevents regressions.

**Best Practice:**

1. Reproduce issue with failing test
2. Make minimal fix
3. Run tests to verify
4. Refactor if needed
5. Run tests again

**Benefit:** Confidence in changes, faster debugging cycles.

---

### Legacy Code Cleanup

**Iteration:** E2E Test Stabilization (2026-01-09)

**Learning:** Removing duplicate/outdated tests improves maintainability.

**Best Practice:**

- Regularly review test suite for duplication
- Remove tests that no longer add value
- Consolidate similar tests
- Keep test count manageable

**Benefit:** Faster test runs, easier maintenance.

---

## Summary Statistics

| Category              | Lessons | Iterations |
| --------------------- | ------- | ---------- |
| Backend Development   | 2       | 2          |
| Frontend Development  | 2       | 2          |
| Testing               | 4       | 2          |
| Architecture & Design | 2       | 3          |
| Process & Workflow    | 3       | 4          |

**Total Lessons Captured:** 13
**Most Common Category:** Testing (31%)

---

## Next Review

**Date:** 2026-01-16
**Focus:** Review new lessons from upcoming iterations
