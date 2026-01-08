# Technical Debt: Update E2E Tests for Server-Side Filtering

**ID:** TD-003  
**Created:** 2026-01-08  
**Priority:** Medium  
**Estimated Effort:** 3-4 hours  
**Status:** Open

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

- ✅ Basic CRUD operations still work (create, read, update, delete)
- ❌ Not testing new search/filter/sort features
- ❌ May have assertions expecting array responses
- ❌ Not verifying pagination metadata

**Test Files Affected:**

- `frontend/e2e/projects_crud.spec.ts`
- `frontend/e2e/wbes_crud.spec.ts`
- `frontend/e2e/cost_elements_crud.spec.ts`

---

## Required Changes

### 1. Update API Response Assertions

**Before:**

```typescript
const response = await page.request.get("/api/v1/projects");
const projects = await response.json();
expect(Array.isArray(projects)).toBe(true);
```

**After:**

```typescript
const response = await page.request.get("/api/v1/projects?page=1&per_page=20");
const data = await response.json();
expect(data).toHaveProperty("items");
expect(data).toHaveProperty("total");
expect(data).toHaveProperty("page");
expect(data).toHaveProperty("per_page");
expect(Array.isArray(data.items)).toBe(true);
```

### 2. Add Search Tests

```typescript
test("should search projects by name", async ({ page }) => {
  // Navigate to projects page
  await page.goto("/projects");

  // Enter search term
  await page.fill('[placeholder="Search projects..."]', "Alpha");

  // Wait for results
  await page.waitForResponse(
    (resp) =>
      resp.url().includes("/api/v1/projects") &&
      resp.url().includes("search=Alpha")
  );

  // Verify filtered results
  const rows = page.locator("table tbody tr");
  await expect(rows).toHaveCount(greaterThan(0));

  // Verify all visible items contain search term
  const firstRow = rows.first();
  await expect(firstRow).toContainText("Alpha", { ignoreCase: true });
});
```

### 3. Add Filter Tests

```typescript
test("should filter projects by status", async ({ page }) => {
  await page.goto("/projects");

  // Open status filter dropdown
  await page.click('[data-testid="status-filter"]');

  // Select "Active" status
  await page.click("text=Active");

  // Wait for API call with filter
  await page.waitForResponse((resp) =>
    resp.url().includes("filters=status:Active")
  );

  // Verify all visible items have Active status
  const statusCells = page.locator('table tbody tr td:has-text("Active")');
  await expect(statusCells.first()).toBeVisible();
});
```

### 4. Add Sorting Tests

```typescript
test("should sort projects by name", async ({ page }) => {
  await page.goto("/projects");

  // Click name column header to sort
  await page.click('th:has-text("Name")');

  // Wait for API call with sort params
  await page.waitForResponse(
    (resp) =>
      resp.url().includes("sort_field=name") &&
      resp.url().includes("sort_order=asc")
  );

  // Verify sorting order
  const names = await page
    .locator("table tbody tr td:nth-child(2)")
    .allTextContents();
  const sortedNames = [...names].sort();
  expect(names).toEqual(sortedNames);

  // Click again for descending
  await page.click('th:has-text("Name")');
  await page.waitForResponse((resp) => resp.url().includes("sort_order=desc"));
});
```

### 5. Add Pagination Tests

```typescript
test("should paginate through results", async ({ page }) => {
  await page.goto("/projects");

  // Verify pagination controls visible
  await expect(page.locator(".ant-pagination")).toBeVisible();

  // Check total count displayed
  const totalText = await page
    .locator(".ant-pagination-total-text")
    .textContent();
  expect(totalText).toMatch(/Total \d+ items/);

  // Click next page
  await page.click(".ant-pagination-next");

  // Wait for page 2 API call
  await page.waitForResponse((resp) => resp.url().includes("page=2"));

  // Verify URL updated
  expect(page.url()).toContain("page=2");
});
```

### 6. Add Combined Operations Test

```typescript
test("should handle search + filter + sort + pagination", async ({ page }) => {
  await page.goto("/projects");

  // Apply search
  await page.fill('[placeholder="Search projects..."]', "Project");
  await page.waitForTimeout(500);

  // Apply filter
  await page.click('[data-testid="status-filter"]');
  await page.click("text=Active");
  await page.waitForTimeout(500);

  // Apply sort
  await page.click('th:has-text("Name")');
  await page.waitForTimeout(500);

  // Verify API call has all params
  const response = await page.waitForResponse(
    (resp) =>
      resp.url().includes("search=Project") &&
      resp.url().includes("filters=status:Active") &&
      resp.url().includes("sort_field=name")
  );

  expect(response.ok()).toBe(true);

  // Verify results displayed
  const rows = page.locator("table tbody tr");
  await expect(rows.first()).toBeVisible();
});
```

---

## Acceptance Criteria

- [ ] All existing CRUD tests still pass
- [ ] New search tests added for Projects, WBEs, Cost Elements
- [ ] New filter tests added for all entities
- [ ] New sorting tests added for all entities
- [ ] New pagination tests added for all entities
- [ ] Combined operations test (search + filter + sort)
- [ ] API response format assertions updated
- [ ] All tests pass consistently (no flakiness)
- [ ] Test execution time < 5 minutes

---

## Implementation Plan

1. **Phase 1: Update Existing Tests** (~1h)

   - Update API response assertions
   - Fix any broken tests
   - Ensure CRUD still works

2. **Phase 2: Add Search Tests** (~1h)

   - Projects search
   - WBEs search
   - Cost Elements search

3. **Phase 3: Add Filter/Sort Tests** (~1h)

   - Filter tests for each entity
   - Sort tests for each entity
   - Pagination tests

4. **Phase 4: Combined Operations** (~30min)

   - Test all features together
   - Verify URL state persistence

5. **Phase 5: Cleanup & Documentation** (~30min)
   - Remove test duplication
   - Add test documentation
   - Update README

---

## Dependencies

- Phase 2 implementation (✅ Complete)
- Backend running on port 8020
- Frontend running on port 5173
- Test database seeded with data

---

## Risks

- **Flakiness:** Search/filter tests may be timing-sensitive

  - **Mitigation:** Use proper `waitForResponse` instead of `waitForTimeout`

- **Test Data:** Tests depend on specific data existing

  - **Mitigation:** Use test fixtures or seed data in `beforeEach`

- **API Changes:** Future API changes may break tests
  - **Mitigation:** Use data-testid attributes, not brittle selectors

---

## Related Items

- Phase 2 Implementation: `docs/03-project-plan/iterations/2026-01-08-table-harmonization/phase2/`
- API Patterns: `docs/02-architecture/api-response-patterns.md`
- Existing E2E Tests: `frontend/e2e/`

---

## Notes

- Tests should be added incrementally, not all at once
- Focus on critical paths first (Projects CRUD + search)
- Can be done in a separate iteration
- Not blocking for Phase 2 deployment

---

**Assignee:** TBD  
**Target Completion:** Next iteration  
**Blocked By:** None  
**Blocks:** None
