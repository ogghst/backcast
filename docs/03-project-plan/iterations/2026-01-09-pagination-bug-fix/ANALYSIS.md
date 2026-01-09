# Request Analysis: Pagination Display Bug in ProjectList

**Date:** 2026-01-09  
**Status:** Analysis Complete  
**Severity:** Critical - User-facing pagination issue

---

## Clarified Requirements

The `ProjectList` component (and likely similar table components) shows only 1 page even when the backend returns more rows. This is a critical UX bug where users cannot navigate through multiple pages of data, despite server-side pagination being fully implemented.

**Expected Behavior:**

- Table should show pagination controls when `total > per_page`
- Users should be able to navigate between pages
- Page navigation should trigger new API requests with updated `page` parameter

**Current Behavior:**

- Table shows only the first page of results
- No pagination controls appear (or they don't function correctly)
- `total` count from backend is not being passed to the Ant Design Table component

---

## Context Discovery Findings

### Product Scope

- **Relevant User Stories:** Server-side filtering implementation (Phase 2, completed 2026-01-08)
- **Business Impact:** Users cannot view or manage entities beyond the first page (20 items), severely limiting application usability

### Architecture Context

**Bounded Contexts Involved:**

- Frontend UI Layer (StandardTable, useTableParams)
- Frontend Data Layer (TanStack Query hooks)
- Backend API Layer (Paginated responses)

**Existing Patterns:**

- Server-side pagination implemented via `PaginatedResponse<T>` schema
- Frontend uses `useTableParams` hook for URL state management
- `StandardTable` component wraps Ant Design Table
- Response unwrapping pattern: `unwrapResponse()` extracts items from `{items, total}` response

**Architectural Constraints:**

- Must maintain URL-synchronized pagination state
- Must preserve backward compatibility with existing table components
- Must follow established patterns from ADR-008 (Server-Side Filtering)

### Codebase Analysis

**Frontend:**

**Critical Files:**

1. `/frontend/src/features/projects/components/ProjectList.tsx` (Lines 36, 259)
2. `/frontend/src/features/projects/api/useProjects.ts` (Lines 109-112)
3. `/frontend/src/hooks/useTableParams.ts` (Lines 38-47)
4. `/frontend/src/components/common/StandardTable.tsx` (Lines 90-94)

**Root Cause Identified:**

🔴 **PRIMARY BUG:** Response unwrapping discards pagination metadata

```typescript
// useProjects.ts (Lines 109-112)
list: async (params) => {
  const serverParams = getPaginationParams(params);
  const res = await getProjectsPaginated(serverParams);
  return unwrapResponse(res); // ❌ DISCARDS total, page, per_page!
},
```

The `unwrapResponse()` helper extracts only the `items` array and **throws away** the `total`, `page`, and `per_page` metadata needed for pagination.

**Effect Chain:**

1. Backend returns: `{items: [...], total: 42, page: 1, per_page: 20}`
2. `unwrapResponse()` extracts: `[...]` (items only)
3. TanStack Query receives: `ProjectRead[]` (no metadata)
4. `ProjectList` component receives: `ProjectRead[]` (no total count)
5. `StandardTable` receives: `tableParams.pagination = {current: 1, pageSize: 10}` (no `total`)
6. Ant Design Table renders: **No pagination controls** (missing `total`)

---

## Root Cause Analysis

### Technical Cause

The issue stems from a **mismatch between API response format and frontend data handling**:

1. **Backend** correctly returns paginated response:

   ```json
   {
     "items": [...],
     "total": 42,
     "page": 1,
     "per_page": 20
   }
   ```

2. **Frontend data layer** (`useProjects` hook) **discards pagination metadata**:

   ```typescript
   return unwrapResponse(res); // Returns only items[]
   ```

3. **Frontend UI layer** (`StandardTable`) expects `total` in `tableParams.pagination`:

   ```typescript
   pagination={tableParams.pagination} // {current, pageSize} ❌ Missing total!
   ```

4. **Ant Design Table** requires `pagination.total` to render pagination controls:
   ```typescript
   // Ant Design internally checks:
   if (total > pageSize) {
     // Show pagination controls
   }
   ```

### Why This Wasn't Caught Earlier

- Server-side filtering (Phase 2) was implemented 2026-01-08
- Focus was on query parameters and filtering logic
- The `unwrapResponse()` pattern was designed for backward compatibility with array responses
- No integration tests verified pagination UI rendering
- Manual testing likely didn't exceed 20 items per entity

---

## Solution Options

### Option 1: Return Full Paginated Response from Hook (Recommended)

**Architecture & Design:**

- Modify `useProjects` hook to return full `PaginatedResponse<T>` instead of `T[]`
- Update all TanStack Query hooks (`useProjects`, `useWBEs`, `useCostElements`) to return metadata
- Create a new hook interface: `UsePaginatedListResult<T>`
- Update components to destructure `{items, total}` from hook response

**Implementation:**

```typescript
// useProjects.ts
interface UsePaginatedListResult<T> {
  items: T[];
  total: number;
  isLoading: boolean;
  // ... other TanStack Query properties
}

list: async (params) => {
  const serverParams = getPaginationParams(params);
  const res = await getProjectsPaginated(serverParams);
  // ✅ Return full response with metadata
  return res;
},

// ProjectList.tsx
const { data, isLoading } = useProjects(tableParams);
// ✅ Destructure items and total
const projects = data?.items || [];
const total = data?.total || 0;

// StandardTable
<StandardTable
  dataSource={projects}
  tableParams={{
    ...tableParams,
    pagination: {
      ...tableParams.pagination,
      total, // ✅ Pass total to Ant Design
    }
  }}
/>
```

**UX Design:**

- No UX change - fixes existing broken pagination
- Pagination controls appear when `total > pageSize`
- Page numbers accurately reflect data volume

**Trade-offs:**

| Aspect              | Assessment                                                                                                                             |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - Clean separation of concerns<br>- Type-safe<br>- Matches backend contract<br>- Enables future features (e.g., "Showing 1-20 of 100") |
| **Cons**            | - Requires updating multiple files<br>- Breaking change for components using these hooks                                               |
| **Complexity**      | **Medium** - Systematic refactor across all entity hooks                                                                               |
| **Maintainability** | **Excellent** - Explicit typing prevents future bugs                                                                                   |
| **Performance**     | No impact - same data transferred                                                                                                      |

---

### Option 2: Separate Metadata Query

**Architecture & Design:**

- Keep `useProjects()` returning `T[]`
- Create separate `useProjectsMetadata()` hook for pagination info
- Components call both hooks in parallel

**Implementation:**

```typescript
// useProjects.ts
export const useProjectsMetadata = (params) =>
  useQuery({
    queryKey: ["projects", "metadata", params],
    queryFn: async () => {
      const res = await getProjectsPaginated(params);
      return { total: res.total, page: res.page, per_page: res.per_page };
    },
  });

// ProjectList.tsx
const { data: projects } = useProjects(tableParams);
const { data: metadata } = useProjectsMetadata(tableParams);

<StandardTable
  dataSource={projects}
  tableParams={{
    ...tableParams,
    pagination: {
      ...tableParams.pagination,
      total: metadata?.total,
    },
  }}
/>;
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - Minimal changes to existing hook interface<br>- Backward compatible                                         |
| **Cons**            | - Two separate API calls (inefficient)<br>- Risk of inconsistent cache state<br>- Duplicates network requests |
| **Complexity**      | **Low** - Quick fix                                                                                           |
| **Maintainability** | **Poor** - Introduces anti-pattern                                                                            |
| **Performance**     | **Negative** - Double API calls                                                                               |

---

### Option 3: Extract Total in Component Layer

**Architecture & Design:**

- `useProjects` hook stores full response in TanStack Query cache
- Return both `items` and `total` from hook
- Component-level unwrapping

**Implementation:**

```typescript
// useProjects.ts
list: async (params) => {
  const serverParams = getPaginationParams(params);
  const res = await getProjectsPaginated(serverParams);
  return res; // ✅ Return full response
},

// Modify createResourceHooks to return metadata
export const useProjects = (params) => {
  const query = useList(params);
  return {
    ...query,
    data: query.data?.items, // Auto-unwrap items
    total: query.data?.total, // Expose total
  };
};

// ProjectList.tsx
const { data: projects, total } = useProjects(tableParams);
```

**Trade-offs:**

| Aspect              | Assessment                                                                      |
| ------------------- | ------------------------------------------------------------------------------- |
| **Pros**            | - Backward compatible (if default export unwraps)<br>- Explicit metadata access |
| **Cons**            | - Magic auto-unwrapping can be confusing<br>- Still requires component changes  |
| **Complexity**      | **Medium**                                                                      |
| **Maintainability** | **Fair** - Implicit unwrapping hides data structure                             |
| **Performance**     | No impact                                                                       |

---

## Comparison Summary

| Criteria               | Option 1 (Full Response)  | Option 2 (Separate Metadata) | Option 3 (Component Unwrap) |
| ---------------------- | ------------------------- | ---------------------------- | --------------------------- |
| **Development Effort** | Medium (3-4 files/entity) | Low (2 files/entity)         | Medium (3 files/entity)     |
| **API Efficiency**     | ✅ Single request         | ❌ Double requests           | ✅ Single request           |
| **Type Safety**        | ✅ Excellent              | ⚠️ Fair                      | ⚠️ Fair (implicit unwrap)   |
| **Maintainability**    | ✅ Excellent              | ❌ Poor                      | ⚠️ Fair                     |
| **Backward Compat**    | ❌ Breaking               | ✅ Compatible                | ⚠️ Partial                  |
| **Best For**           | Long-term solution        | Quick hotfix                 | Hybrid approach             |

---

## Recommendation

**I recommend Option 1 (Return Full Paginated Response) because:**

1. **Architectural Alignment:** Matches the backend contract established in ADR-008
2. **Type Safety:** Explicit `PaginatedResponse<T>` prevents similar bugs
3. **Future-Proof:** Enables features like "Showing X-Y of Z results"
4. **Performance:** No duplicate API calls
5. **Consistency:** All entity hooks follow same pattern

**Implementation Priority:**

- **Phase 1 (Immediate):** Fix `ProjectList` + `useProjects`
- **Phase 2 (Follow-up):** Migrate `WBEList` + `useWBEs`
- **Phase 3 (Cleanup):** Migrate `CostElementList` + `useCostElements`

**Alternative Consideration:**
If immediate deployment is critical and there's risk aversion to breaking changes, implement **Option 2** as a temporary hotfix, then refactor to **Option 1** in next sprint.

---

## Implementation Plan (Option 1)

### Files to Modify

**Per Entity (Projects example):**

1. **`useProjects.ts`** (or equivalent hook file):

   - Remove `unwrapResponse()` call in `list` function
   - Return full `PaginatedResponse<T>` from hook

2. **`ProjectList.tsx`** (or equivalent component):

   - Destructure `{items, total}` from hook response
   - Pass `total` to `tableParams.pagination`

3. **`StandardTable.tsx`** (shared component):

   - ✅ No changes needed - already accepts `pagination.total`

4. **`useTableParams.ts`** (shared hook):
   - ✅ No changes needed - already manages pagination state

### Testing Checklist

- [ ] Backend returns `{items, total, page, per_page}`
- [ ] Hook preserves all metadata fields
- [ ] Component displays correct total count
- [ ] Pagination controls render when `total > pageSize`
- [ ] Page navigation triggers correct API requests
- [ ] URL params sync with pagination state
- [ ] Sorting/filtering preserves pagination
- [ ] Edge cases: 0 results, exactly 1 page, 1000+ pages

### Rollout Strategy

1. Create feature branch: `fix/pagination-metadata`
2. Implement fix for Projects entity (highest priority)
3. Browser test with `>20` projects
4. Commit and verify in staging
5. Repeat for WBEs and Cost Elements
6. Update documentation (API Response Patterns)
7. Merge to main

---

## Questions for Decision

1. **Timeline:** Is this blocking production usage? (Determines hotfix vs. proper refactor)
2. **Scope:** Should we fix all entities (Projects, WBEs, Cost Elements) in one PR or incrementally?
3. **Testing:** Do we need E2E tests for pagination beyond existing browser tests?
4. **Documentation:** Should we add a "Pagination" section to the UI Patterns doc?

---

## References

- **ADR-008:** [Server-Side Filtering](file:///home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-008-server-side-filtering.md)
- **API Response Patterns:** [Cross-Cutting Docs](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/api-response-patterns.md)
- **UI Patterns:** [Frontend Docs](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/ui-patterns.md)
- **Coding Standards:** [Core Principles](file:///home/nicola/dev/backcast_evs/docs/02-architecture/coding-standards.md)

---

**Next Step:** Await user decision on recommended option and proceed to PLAN phase (create implementation ticket).
