# PLAN: Pagination Metadata Refactor

**Iteration:** Pagination Metadata Refactor  
**Date:** 2026-01-09  
**Status:** 📋 **PLANNED** - Awaiting Implementation  
**Severity:** Critical - User-facing bug blocking multi-page data access

---

## Phase 1: Context Analysis

### Documentation Review

**Architecture Context:**

- **ADR-008:** Server-Side Filtering implemented 2026-01-08
- **API Response Patterns:** Defines `PaginatedResponse<T>` standard
- **UI Patterns:** Documents `StandardTable` and `useTableParams` usage
- **Coding Standards:** Emphasizes type safety, explicit typing, backend as source of truth

**Recent Work:**

- **2026-01-08:** Phase 2 - Server-side filtering completed
- **2026-01-09:** E2E Test stabilization completed
- Current iteration focused on technical debt paydown

### Codebase Analysis

**Affected Hook Files:**

1. `/frontend/src/features/projects/api/useProjects.ts` - ✅ Has paginated API
2. `/frontend/src/features/wbes/api/useWBEs.ts` - ✅ Has paginated API (hybrid)
3. Cost Elements - ⚠️ No dedicated hook file (uses inline queries)

**Affected Component Files:**

1. `/frontend/src/features/projects/components/ProjectList.tsx`
2. `/frontend/src/features/wbes/components/WBEList.tsx` (likely exists)
3. Cost Element components (need to identify)

**Shared Infrastructure:**

- `/frontend/src/hooks/useTableParams.ts` - ✅ Already supports pagination
- `/frontend/src/components/common/StandardTable.tsx` - ✅ Already accepts `pagination.total`
- `/frontend/src/hooks/useCrud.ts` - May need modification for generic pagination

---

## Phase 2: Problem Definition

### Problem Statement

**What:** Table components show only 1 page of results even when backend returns multiple pages of data.

**Why Important:** Users cannot access records beyond the first page (default 20 items), severely limiting the application's usability for projects with >20 entities.

**Business Impact:**

- **Severity:** Critical - Core functionality broken
- **User Impact:** Cannot view/manage most of their data
- **Scope:** Affects Projects, WBEs, and potentially Cost Elements
- **Root Cause:** Response unwrapping discards pagination metadata (`total`, `page`, `per_page`)

**What happens if not addressed:**

- Users cannot scale beyond MVP demo datasets
- Data appears "missing" causing support burden
- Workarounds (increasing page size) hit performance limits

**Business Value:**

- Unlocks application scalability
- Enables proper data management workflow
- Aligns frontend with backend pagination contract

### Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Pagination controls appear when `total > page_size`
- [ ] Clicking page numbers navigates correctly
- [ ] URL parameters sync with page navigation
- [ ] Total count displays accurately (e.g., "Showing 1-20 of 100")
- [ ] Sorting/filtering preserves pagination metadata
- [ ] Search resets to page 1

**Technical Criteria:**

- [ ] Type-safe `PaginatedResponse<T>` interface used consistently
- [ ] No duplicate API calls per page navigation
- [ ] Backend tests pass (153/153)
- [ ] Frontend type checking passes (strict mode)
- [ ] No console errors or warnings

**Test Coverage:**

- [ ] Unit tests for response unwrapping logic
- [ ] Integration tests for hook pagination behavior
- [ ] E2E tests verify pagination UI rendering
- [ ] E2E tests verify page navigation triggers API calls

**Edge Cases Handled:**

- [ ] Zero results (no pagination controls)
- [ ] Exactly 1 page of results (no controls)
- [ ] 1000+ pages (pagination control doesn't break)
- [ ] Page parameter exceeds max pages (backend handles gracefully)

### Scope Definition

**In Scope:**

1. **Hook Layer Updates:**

   - Modify `useProjects` to return `PaginatedResponse<ProjectRead>`
   - Modify `useWBEs` to return `PaginatedResponse<WBERead>` (general listing mode)
   - Create or update Cost Element hooks for consistency

2. **Component Layer Updates:**

   - Update `ProjectList` to destructure `{items, total}` from hook
   - Update `WBEList` to destructure `{items, total}` from hook
   - Update Cost Element list components (if applicable)
   - Pass `total` to `StandardTable` pagination prop
   - **Enable Custom Page Size Selector:** Configure `StandardTable` to show size changer with options `['10', '20', '50', '100']`

3. **Type Definitions:**

   - Create shared `PaginatedResponse<T>` interface in types file
   - Update hook return types
   - Update component prop types

4. **Testing:**

   - Add unit tests for pagination metadata preservation
   - Update E2E tests to verify pagination controls render
   - Test page navigation triggers correct API requests
   - **Test Page Size Change:** Verify changing page size triggers new API call with correct `per_page`

5. **Documentation:**
   - Update API Response Patterns doc with frontend examples
   - Document pagination best practices in UI Patterns
   - Add troubleshooting section for common pagination bugs

**Out of Scope:**

- Backend API changes (already correct)
- `useTableParams` modifications (already supports pagination)
- `StandardTable` modifications (already supports `pagination.total`)
- WBE hierarchical mode (returns array, no pagination - by design)
- Cost Element hierarchical queries (if they exist)
- Advanced pagination features (jump to page input)
- Server-side page size validation beyond existing limits

**Deferred to Future:**

- "Showing X-Y of Z" display component (custom render)
- Infinite scroll as alternative to pagination
- Performance optimization for 10,000+ record tables

**Assumptions:**

- Backend APIs correctly return `PaginatedResponse` format
- Ant Design Table pagination prop accepts `total` field
- TanStack Query caching handles pagination cache keys correctly

---

## Phase 3: Implementation Options

### Option A: Full Paginated Response (Recommended)

**Approach Summary:**
Modify all entity hooks to return complete `PaginatedResponse<T>` object. Components destructure `{items, total}` and pass `total` to table. Additionally, enable Ant Design's `showSizeChanger` in `StandardTable`.

**Design Patterns:**

- **Data Transfer Object (DTO):** `PaginatedResponse<T>` as typed DTO
- **Adapter Pattern:** Hook layer adapts API response to component needs
- **Single Source of Truth:** Backend pagination metadata is authoritative

**Pros:**

- ✅ Type-safe and explicit
- ✅ Matches backend contract (ADR-008)
- ✅ Enables future features (e.g., "Showing X of Y" banner)
- ✅ No performance overhead
- ✅ Consistent pattern across all entities
- ✅ **Enhanced UX:** Users control data density

**Cons:**

- ⚠️ Breaking change for components using hooks
- ⚠️ Requires updating 6-9 files per entity
- ⚠️ Need to carefully handle hybrid responses (WBEs)

**Test Strategy Impact:**

- Add unit tests: Hook returns correct shape
- Update E2E tests: Assert pagination controls visible
- Integration tests: Verify `total` passed through layers

**Risk Level:** **Low**

- Well-defined change scope
- Type system catches breaking changes at compile time
- Backend already supports this pattern

**Estimated Complexity:** **Moderate**

- Systematic refactor, not exploratory work
- Clear implementation pattern to replicate
- 3 entities × 3 files each = ~9 file changes + tests

---

### Option B: Metadata Sidecar Hook

**Approach Summary:**
Keep `useProjects()` returning `T[]`, create parallel `useProjectsMetadata()` hook returning pagination data.

**Design Patterns:**

- **Composition:** Separate data and metadata concerns
- **Multiple Queries:** Two TanStack Query calls per table

**Pros:**

- ✅ Minimal changes to existing component code
- ✅ Backward compatible with non-paginated use cases

**Cons:**

- ❌ Two API calls per page load (inefficient)
- ❌ Cache consistency issues (data and metadata can diverge)
- ❌ Anti-pattern: duplicates network requests
- ❌ Confusing API for developers

**Test Strategy Impact:**

- Must test cache synchronization
- Must verify both hooks called with same params
- Edge cases: One hook succeeds, other fails

**Risk Level:** **Medium-High**

- Cache consistency bugs
- Performance regression
- Confusing for future developers

**Estimated Complexity:** **Simple** (but poor design)

---

### Option C: Hybrid - Metadata in Query Meta

**Approach Summary:**
Use TanStack Query's `meta` field to store pagination metadata alongside query data.

**Design Patterns:**

- **Metadata Tagging:** Attach auxiliary data to query result
- **Framework Feature:** Leverage TanStack Query built-in capabilities

**Pros:**

- ✅ Single API call
- ✅ Leverages TanStack Query features

**Cons:**

- ⚠️ Less explicit - metadata "hidden" in query meta
- ⚠️ Non-standard pattern for this codebase
- ⚠️ Harder to type-check metadata access

**Test Strategy Impact:**

- Test metadata correctly stored in query meta
- Verify components access meta correctly

**Risk Level:** **Medium**

- Less discoverable for other developers
- Debugging cache meta is harder

**Estimated Complexity:** **Moderate**

---

## Comparison Matrix

| Criteria               | Option A (Full Response) | Option B (Sidecar) | Option C (Meta)   |
| ---------------------- | ------------------------ | ------------------ | ----------------- |
| **Type Safety**        | ✅ Excellent             | ⚠️ Fair            | ⚠️ Fair           |
| **Performance**        | ✅ Optimal               | ❌ Poor (2× calls) | ✅ Optimal        |
| **Maintainability**    | ✅ Excellent             | ❌ Poor            | ⚠️ Fair           |
| **ADR-008 Alignment**  | ✅ Perfect               | ❌ Diverges        | ⚠️ Partial        |
| **Development Effort** | Moderate (2-3 days)      | Low (1 day)        | Moderate (2 days) |
| **Risk**               | Low                      | Medium-High        | Medium            |

### Recommendation

**Selected Option: A - Full Paginated Response**

**Justification:**

1. **Architecture Alignment:** Directly implements the pattern documented in ADR-008 and API Response Patterns
2. **Type Safety:** Full compile-time validation prevents similar bugs
3. **Future-Proof:** Lays foundation for "Showing X of Y" UI components
4. **Performance:** Single API call per page load
5. **Maintainability:** Explicit, self-documenting code

**Decision Rationale:**
While Option A requires more upfront work, it's the only option that properly addresses the architectural debt and prevents regression. Options B and C are technical workarounds that would create new problems.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
Pagination Metadata Tests
├── Unit Tests - Hook Layer
│   ├── useProjects returns PaginatedResponse shape
│   ├── useWBEs (general mode) returns PaginatedResponse shape
│   ├── useWBEs (hierarchical mode) returns array (unchanged)
│   ├── Hook preserves total, page, per_page from API
│   └── Edge case: Zero results returns {items: [], total: 0}
│
├── Integration Tests - Component Layer
│   ├── ProjectList receives pagination metadata
│   ├── WBEList receives pagination metadata
│   ├── Total is passed to StandardTable pagination prop
│   ├── Pagination controls render when total > pageSize
│   └── Pagination controls hidden when total <= pageSize
│
└── E2E Tests - Full Flow
    ├── Navigating to page 2 changes URL and fetches new data
    ├── Pagination shows correct total count
    ├── Sorting preserves current page
    ├── Filtering resets to page 1
    └── Search resets to page 1
```

**First 5 Test Cases (ordered by complexity):**

1. **Unit - Happy Path:**

   ```typescript
   test("useProjects returns paginated response shape", async () => {
     const { result } = renderHook(() => useProjects(defaultParams));
     await waitFor(() => expect(result.current.isSuccess).toBe(true));
     expect(result.current.data).toHaveProperty("items");
     expect(result.current.data).toHaveProperty("total");
   });
   ```

2. **Unit - Zero Results:**

   ```typescript
   test("useProjects handles zero results", async () => {
     mockApi.projects.getList.mockResolvedValue({
       items: [],
       total: 0,
       page: 1,
       per_page: 20,
     });
     const { result } = renderHook(() => useProjects(defaultParams));
     await waitFor(() => expect(result.current.data?.total).toBe(0));
   });
   ```

3. **Integration - Component Receives Metadata:**

   ```typescript
   test('ProjectList receives total from hook', () => {
     const mockData = {items: [...], total: 42, page: 1, per_page: 20};
     jest.spyOn(useProjects, 'default').mockReturnValue({data: mockData, ...});
     render(<ProjectList />);
     expect(screen.getByText(/42/)).toBeInTheDocument(); // Pagination shows total
   });
   ```

4. **E2E - Pagination Controls Render:**

   ```typescript
   test("pagination controls appear for multi-page results", async () => {
     await createProjects(25); // > 20 default page size
     await page.goto("/projects");
     const pagination = page.locator(".ant-pagination");
     await expect(pagination).toBeVisible();
     await expect(page.locator(".ant-pagination-item-2")).toBeVisible();
   });
   ```

5. **E2E - Page Navigation:**
   ```typescript
   test("clicking page 2 navigates and fetches new data", async () => {
     await createProjects(25);
     await page.goto("/projects");
     await page.click(".ant-pagination-item-2");
     await expect(page).toHaveURL(/page=2/);
     // Verify API called with page=2 param
   });
   ```

### Implementation Strategy

#### High-Level Approach

**Phase 1: Foundation (Type Definitions & Shared UI)**

- Create shared `PaginatedResponse<T>` type in `@/types/api.ts`
- Define hook result interface: `UsePaginatedListResult<T>`
- **Update `StandardTable.tsx`** to enable `showSizeChanger` by default

**Phase 2: Hook Layer (Data Layer)**

- Refactor `useProjects` to return full response
- Refactor `useWBEs` (general listing mode only)
- Add unit tests for each hook

**Phase 3: Component Layer (UI Layer)**

- Update `ProjectList` to destructure `{items, total}`
- Update `WBEList` to destructure `{items, total}`
- Pass `total` to `StandardTable`
- Add integration tests

**Phase 4: E2E Validation**

- Update E2E tests to verify pagination UI
- Test page navigation workflow
- Test interaction with filtering/sorting

**Phase 5: Documentation**

- Update API Response Patterns with frontend integration examples
- Add pagination section to UI Patterns
- Document troubleshooting common issues

#### Key Technologies/Patterns

- **TanStack Query:** Data fetching and caching
- **TypeScript Generics:** `PaginatedResponse<T>` for type safety
- **Destructuring:** `const {items, total} = data || {items: [], total: 0}`
- **TDD:** Write tests before implementation
- **Incremental Migration:** One entity at a time (Projects → WBEs → Cost Elements)

#### Component Breakdown

**Per Entity (Projects example):**

1. **Type Definition (`@/types/api.ts` or inline):**

   ```typescript
   export interface PaginatedResponse<T> {
     items: T[];
     total: number;
     page: number;
     per_page: number;
   }
   ```

2. **Hook Update (`useProjects.ts`):**

   ```typescript
   // BEFORE
   list: async (params) => {
     const res = await getProjectsPaginated(params);
     return unwrapResponse(res); // ❌
   };

   // AFTER
   list: async (params) => {
     const res = await getProjectsPaginated(params);
     return res; // ✅ Keep metadata
   };
   ```

3. **Component Update (`ProjectList.tsx`):**

   ```typescript
   // BEFORE
   const { data: projects, isLoading } = useProjects(tableParams);
   <StandardTable dataSource={projects || []} />;

   // AFTER
   const { data, isLoading } = useProjects(tableParams);
   const projects = data?.items || [];
   const total = data?.total || 0;
   <StandardTable
     dataSource={projects}
     tableParams={{
       ...tableParams,
       pagination: {
         ...tableParams.pagination,
         total, // ✅ Pass total
       },
     }}
   />;
   ```

**Shared Component Update (`StandardTable.tsx`):**

```typescript
// Update default pagination config
<Table
  pagination={{
    ...tableParams.pagination,
    showSizeChanger: true,
    pageSizeOptions: ["10", "20", "50", "100"],
  }}
/>
```

#### Integration Points

- **Backend API:** Already returns correct format (no changes)
- **`useTableParams` hook:** Already manages pagination state (no changes)
- **`StandardTable` component:** Already accepts `pagination.total` (no changes)
- **TanStack Query cache:** Cache keys remain unchanged
- **URL routing:** Pagination params already synced to URL (no changes)

**Special Case - WBEs Hybrid Response:**

WBEs endpoint uses hybrid logic:

- **Hierarchical queries** (projectId/parentWbeId): Returns `Array` (no pagination)
- **General listing**: Returns `PaginatedResponse`

**Solution:**

```typescript
// useWBEs.ts
list: async (params) => {
  const response = await WbEsService.getWbes(...);

  // Hierarchical mode: Return array wrapped in metadata
  if (params?.projectId || params?.parentWbeId) {
    return {
      items: Array.isArray(response) ? response : response.items,
      total: Array.isArray(response) ? response.length : response.total,
      page: 1,
      per_page: 1000, // Hierarchical queries return all
    };
  }

  // General listing mode: Return paginated response
  return response as PaginatedResponse<WBERead>;
}
```

---

## Phase 5: Risk Assessment

### Risks and Mitigations

| Risk Type       | Description                              | Probability | Impact | Mitigation Strategy                                                                                                                          |
| --------------- | ---------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Technical**   | Breaking existing components using hooks | Medium      | High   | 1. Use TypeScript strict mode to catch at compile time<br>2. Run all E2E tests before merge<br>3. Incremental rollout (one entity at a time) |
| **Technical**   | WBE hybrid response handling breaks      | Medium      | Medium | 1. Add explicit type guards<br>2. Unit tests for both modes<br>3. Backend team confirms contract                                             |
| **Technical**   | Cache key invalidation issues            | Low         | Medium | 1. Verify cache keys unchanged<br>2. Test refetch behavior<br>3. Clear cache on page navigation                                              |
| **Integration** | Ant Design Table doesn't accept total    | Low         | High   | 1. Verify in Ant Design docs<br>2. Browser test immediately<br>3. Have fallback plan (custom pagination)                                     |
| **Schedule**    | E2E tests fail after migration           | Medium      | Medium | 1. Update test data (create >20 items)<br>2. Update assertions (pagination visible)<br>3. Budget extra time for test fixes                   |
| **UX**          | Pagination controls don't render         | Low         | High   | 1. Browser test immediately after change<br>2. Verify `total` prop passed<br>3. Check Ant Design CSS loaded                                  |

### Critical Integration Points

**Risk: TanStack Query Cache Consistency**

- **Issue:** Query cache keys must remain consistent
- **Mitigation:** Use same query key structure, just change return type
- **Validation:** Unit test that cache keys unchanged

**Risk: E2E Test Failures**

- **Issue:** Tests may expect `data` to be array, not object
- **Mitigation:** Search codebase for direct `data.map()` usage
- **Validation:** Run E2E suite before and after each entity migration

---

## Phase 6: Effort Estimation

### Time Breakdown

**Per Entity (Projects, WBEs, Cost Elements):**

- **Development:**

  - Type definitions & Shared UI: 1 hour (shared)
  - Hook refactor: 1 hour
  - Component update: 1 hour
  - **Subtotal:** ~3 hours per entity cycle

- **Testing:**

  - Unit tests (hooks): 1 hour per entity
  - Integration tests (components): 1 hour per entity
  - E2E test updates: 0.5 hour per entity
  - **Subtotal:** 2.5 hours per entity × 3 = **7.5 hours**

- **Documentation:**

  - Update API Response Patterns: 1 hour
  - Update UI Patterns: 1 hour
  - Add troubleshooting guide: 0.5 hour
  - **Subtotal:** **2.5 hours**

- **Review & Deployment:**
  - Code review iterations: 2 hours
  - Browser smoke testing: 1 hour
  - Deploy to staging + validation: 1 hour
  - **Subtotal:** **4 hours**

**Total Estimated Effort:** **22.5 hours** (~3 days)

### Effort by Phase

| Phase                   | Hours    | Description                             |
| ----------------------- | -------- | --------------------------------------- |
| Foundation (Types + UI) | 1        | Shared types, StandardTable updates     |
| Projects Entity         | 5        | Hook + Component + Tests                |
| WBEs Entity             | 6        | Hook (hybrid logic) + Component + Tests |
| Cost Elements Entity    | 4        | Hook + Component + Tests (if needed)    |
| Documentation           | 2.5      | Docs updates                            |
| Testing & QA            | 2        | E2E suite validation                    |
| Review & Deploy         | 2        | Code review, staging deploy             |
| **Total**               | **22.5** | **~3 working days**                     |

### Prerequisites

**Before Starting:**

- [ ] Confirm backend APIs return `PaginatedResponse` format (already done)
- [ ] Verify Ant Design Table accepts `pagination.total` prop (check docs)
- [ ] Create feature branch: `fix/pagination-metadata`
- [ ] Ensure all existing tests pass (baseline)

**During Development:**

- [ ] Update sprint backlog with task breakdown
- [ ] Create this PLAN document
- [ ] Set up test data with >20 items per entity

**Infrastructure Needed:**

- [ ] Test database with sufficient seed data (>20 projects, >20 WBEs)
- [ ] Local development environment running
- [ ] Browser for manual testing
- [ ] E2E test environment configured

---

## Implementation Task Breakdown

### Phase 1: Foundation (1 hour)

- [ ] Create `@/types/api.ts` with `PaginatedResponse<T>` interface
- [ ] Update `.d.ts` files if needed
- [ ] Create feature branch `fix/pagination-metadata`
- [ ] **Update `StandardTable.tsx` to include `showSizeChanger` and `pageSizeOptions` defaults**

### Phase 2: Projects Entity (5 hours)

**Hook Layer (2 hours):**

- [ ] Update `useProjects.ts` - remove `unwrapResponse()` call
- [ ] Update return type to `PaginatedResponse<ProjectRead>`
- [ ] Write unit test: Hook returns correct shape
- [ ] Write unit test: Hook preserves pagination metadata
- [ ] Write unit test: Zero results edge case

**Component Layer (2 hours):**

- [ ] Update `ProjectList.tsx` - destructure `{items, total}`
- [ ] Pass `total` to `StandardTable` pagination prop
- [ ] Write integration test: Component receives metadata
- [ ] Write integration test: Pagination controls render

**E2E Tests (1 hour):**

- [ ] Update `projects_crud.spec.ts` - assert pagination visible
- [ ] Test page navigation workflow
- [ ] Run full E2E suite - verify pass

### Phase 3: WBEs Entity (6 hours)

**Hook Layer (3 hours):**

- [ ] Update `useWBEs.ts` - handle hybrid response
- [ ] Implement type guard for array vs object response
- [ ] Write unit test: General listing mode returns paginated
- [ ] Write unit test: Hierarchical mode returns wrapped array
- [ ] Write unit test: Type guard logic

**Component Layer (2 hours):**

- [ ] Update `WBEList.tsx` - destructure `{items, total}`
- [ ] Pass `total` to `StandardTable` pagination prop
- [ ] Write integration test: Component receives metadata
- [ ] Write integration test: Hierarchical mode still works

**E2E Tests (1 hour):**

- [ ] Update `wbes_crud.spec.ts` - assert pagination visible
- [ ] Test page navigation workflow
- [ ] Verify hierarchical queries unchanged
- [ ] Run full E2E suite - verify pass

### Phase 4: Cost Elements (4 hours)

**Analysis (0.5 hours):**

- [ ] Identify if Cost Elements use dedicated hooks or inline queries
- [ ] Determine if pagination is needed or hierarchical only

**Implementation (2.5 hours):**

- [ ] Create `useCostElements.ts` hook (if doesn't exist)
- [ ] OR update inline queries to handle pagination
- [ ] Update component to use pagination metadata
- [ ] Write unit and integration tests

**E2E Tests (1 hour):**

- [ ] Update `cost_elements_crud.spec.ts` if applicable
- [ ] Run full E2E suite - verify pass

### Phase 5: Documentation (2.5 hours)

- [ ] Update `api-response-patterns.md` - add frontend examples
- [ ] Update `ui-patterns.md` - add pagination section
- [ ] Create troubleshooting guide for pagination issues
- [ ] Update this PLAN doc status to "Complete"
- [ ] Create DO document with implementation log

### Phase 6: Testing & Deployment (3.5 hours)

**Browser Testing (1 hour):**

- [ ] Manual test Projects pagination (>20 items)
- [ ] Manual test WBEs pagination (>20 items)
- [ ] Manual test sorting + pagination interaction
- [ ] Manual test filtering + pagination interaction
- [ ] Manual test search + pagination interaction

**E2E Validation (1 hour):**

- [ ] Run full E2E suite: `npm run test:e2e`
- [ ] Verify all CRUD tests pass
- [ ] Verify pagination tests pass

**Code Review (1 hour):**

- [ ] Self-review all changes
- [ ] Check TypeScript strict mode passes
- [ ] Check no console errors
- [ ] Verify test coverage

**Deployment (0.5 hours):**

- [ ] Merge to main branch
- [ ] Deploy to staging
- [ ] Smoke test in staging
- [ ] Monitor for errors

---

## Approval

**Status:** 📋 **AWAITING IMPLEMENTATION**

**Approved By:** Nicola (User)  
**Approval Date:** 2026-01-09  
**Implementation Start:** 2026-01-09

---

## Related Documentation

- **Analysis:** [ANALYSIS.md](./ANALYSIS.md)
- **ADR-008:** [Server-Side Filtering](../../02-architecture/decisions/ADR-008-server-side-filtering.md)
- **API Response Patterns:** [Cross-Cutting Docs](../../02-architecture/cross-cutting/api-response-patterns.md)
- **UI Patterns:** [Frontend Docs](../../02-architecture/frontend/ui-patterns.md)
- **Coding Standards:** [Core Principles](../../02-architecture/coding-standards.md)

---

**Next Phase:** DO - Implementation with TDD approach
