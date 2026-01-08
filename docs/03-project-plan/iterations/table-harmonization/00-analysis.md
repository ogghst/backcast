# Request Analysis: Frontend Table Harmonization

**Analysis Date:** 2026-01-08  
**Requested By:** User  
**Analyzed By:** AI Assistant

## Clarified Requirements

The user requests that all tables in the frontend have **consistent column sorting, searching, and filtering features**. This means:

1. **Functional Requirements:**

   - All tables should support column sorting (client-side or server-side)
   - All tables should support searching/filtering on relevant columns
   - Implementation should be consistent across all list pages
   - Features should be discoverable and work intuitively

2. **Non-Functional Requirements:**

   - Maintainability: Single source of truth for table patterns
   - Type Safety: Maintain strict TypeScript typing
   - Performance: Client-side for small datasets, server-side for large ones
   - Accessibility: WCAG compliance via Ant Design

3. **Constraints:**
   - Must use existing Ant Design components
   - Must maintain current `StandardTable` + `useTableParams` pattern
   - Must not break existing E2E tests
   - Must align with EVCS architecture principles

## Context Discovery Findings

### Product Scope

**Relevant User Stories:**

- Users need to quickly find entities in large lists (Projects, WBEs, Cost Elements, Users, Departments)
- Users need to sort by different criteria (code, name, budget, date)
- Users need to filter by status, type, or other categorical attributes

**Domain Concepts:**

- All entity lists follow master-detail pattern
- Tables display: Users, Departments, Projects, WBEs, Cost Elements, Cost Element Types
- Most entities are versioned (bitemporal) and support branches

### Architecture Context

**Bounded Contexts Involved:**

- User Management (UserList)
- Department Management (DepartmentManagement)
- Project & WBE Management (ProjectList, WBEList, WBETable)
- Cost Element & Financial Tracking (CostElementManagement)

**Existing Patterns:**

- `StandardTable<T>` - Reusable table wrapper component
- `useTableParams<T>` - URL-synced pagination/sorting hook
- `useCrud` - Generic CRUD hooks with React Query

**Architectural Constraints:**

- ADR-004: Quality Standards (MyPy strict, type safety)
- ADR-005: Bitemporal versioning affects filtering requirements
- Pattern established: URL-based state for pagination/sorting

### Codebase Analysis

#### Current Table Implementations

| Component                 | Location                                       | Sorting   | Filtering  | Searching | Notes                                                        |
| ------------------------- | ---------------------------------------------- | --------- | ---------- | --------- | ------------------------------------------------------------ |
| **UserList**              | `pages/admin/UserList.tsx`                     | ✅ Client | ❌ None    | ❌ None   | Uses `sorter: true` on "Full Name"                           |
| **DepartmentManagement**  | `pages/admin/DepartmentManagement.tsx`         | ✅ Client | ❌ None    | ❌ None   | Uses `sorter: true` on "Name"                                |
| **ProjectList**           | `features/projects/components/ProjectList.tsx` | ❌ None   | ❌ None    | ❌ None   | No sorting or filtering                                      |
| **WBEList**               | `pages/wbes/WBEList.tsx`                       | ❌ None   | ❌ None    | ❌ None   | No sorting or filtering                                      |
| **WBETable**              | `components/hierarchy/WBETable.tsx`            | ✅ Client | ❌ None    | ❌ None   | Client-side sort on "Code" via `localeCompare`               |
| **CostElementManagement** | `pages/financials/CostElementManagement.tsx`   | ✅ Client | ✅ Filters | ❌ None   | Most advanced: supports Type & WBE filters + branch selector |

#### Implementation Details

**StandardTable Component:**

```typescript
// frontend/src/components/common/StandardTable.tsx
// - Wraps Ant Design Table
// - Accepts tableParams (pagination, sortField, sortOrder, filters)
// - Passes onChange handler for table events
// - Supports optional toolbar slot
```

**useTableParams Hook:**

```typescript
// frontend/src/hooks/useTableParams.ts
// - Syncs pagination and sorting to URL params (?page=1&per_page=10)
// - Handles single sorter (field + order)
// - Does NOT handle filters yet (commented as "MVP")
```

**Key Observations:**

1. **Inconsistency in Sorting:**

   - Some tables use `sorter: true` (server-side expectation)
   - WBETable uses `sorter: (a, b) => ...` (client-side)
   - Most tables have NO sorting at all

2. **Inconsistency in Filtering:**

   - Only CostElementManagement implements column filters
   - Uses Ant Design's `filters` prop on columns
   - Filters passed to backend via `tableParams`

3. **No Global Search:**

   - None of the tables have a search input
   - No full-text search across all columns

4. **URL State Management:**

   - `useTableParams` handles pagination + sorting
   - Filters are NOT synced to URL (partially implemented)

5. **Backend Support:**
   - Current backend services accept `skip`, `limit`
   - Cost Element service also accepts filter params (wbe_id, type_id)
   - Projects/WBEs services do NOT accept filters yet

---

## Current State Summary

### ✅ What Works Well

1. **Pagination:** Fully implemented in all tables via `StandardTable` + `useTableParams`
2. **Type Safety:** Generic types (`StandardTable<T>`, `useTableParams<T>`)
3. **Reusability:** Shared components reduce duplication
4. **URL State:** Pagination persists in URL

### ❌ Gaps and Inconsistencies

| Feature        | UserList   | DepartmentMgmt | ProjectList | WBEList | WBETable      | CostElementMgmt |
| -------------- | ---------- | -------------- | ----------- | ------- | ------------- | --------------- |
| Pagination     | ✅         | ✅             | ✅          | ✅      | ❌ (disabled) | ✅              |
| Column Sorting | 🟡 (1 col) | 🟡 (1 col)     | ❌          | ❌      | 🟡 (1 col)    | 🟡 (2 cols)     |
| Column Filters | ❌         | ❌             | ❌          | ❌      | ❌            | ✅ (2 filters)  |
| Global Search  | ❌         | ❌             | ❌          | ❌      | ❌            | ❌              |

### Technical Debt

- **TD-003:** Loose `as any` casting in table components (already identified)
- **TD-New:** `useTableParams` filter support is stubbed but not implemented
- **TD-New:** No consistent pattern for client vs server-side operations

---

## Solution Options

### Option 1: **Incremental Enhancement (Conservative)**

**Architecture & Design:**

- Enhance `useTableParams` to handle filters + global search
- Add UI components (Search input, filter dropdowns) to `StandardTable` toolbar
- Keep all sorting/filtering **client-side** for now
- Backend changes minimal (only for large datasets later)

**UX Design:**

- Add a search input in the toolbar (right side, before "Add" button)
- Column headers become sortable (click to toggle asc/desc/none)
- Filter icon appears on filterable columns (dropdown with checkboxes)
- All operations happen client-side (fast, no loading states)

**Implementation:**

1. Update `useTableParams`:
   - Add `search` parameter (synced to URL `?search=...`)
   - Add `filters` parameter (serialized to URL)
2. Update `StandardTable`:
   - Add optional `searchPlaceholder` prop
   - Render search input in toolbar if provided
   - Client-side filtering on `dataSource`
3. Update each list page:
   - Add `sorter: true` to all relevant columns
   - Add `filters` array to categorical columns
   - Implement client-side `onFilter` functions

**Trade-offs:**

| Aspect              | Assessment                                                                                                                       |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - Fast implementation (1-2 days)<br>- No backend changes needed<br>- Works immediately for current data sizes<br>- Low risk      |
| **Cons**            | - Won't scale beyond ~1000 rows<br>- Redundant logic if we need server-side later<br>- Search only on rendered page (not global) |
| **Complexity**      | Low                                                                                                                              |
| **Maintainability** | Good (centralized in StandardTable)                                                                                              |
| **Performance**     | Excellent for current scale, poor at >1000 rows                                                                                  |

---

### Option 2: **Server-Side Foundation (Future-Proof)**

**Architecture & Design:**

- Update backend services to accept `sort_by`, `sort_order`, `filters`, `search` params
- Update `useTableParams` to serialize all table state to URL and backend
- Implement server-side pagination, sorting, filtering, search
- Keep UI components same as Option 1

**UX Design:**

- Same as Option 1, but with loading indicators during operations
- Debounced search input (300ms) to reduce API calls
- Filter dropdowns load options from backend

**Implementation:**

1. **Backend (per entity):**
   - Update service methods: `get_users(skip, limit, sort_by, sort_order, search, **filters)`
   - Implement SQLAlchemy query building with dynamic filters
   - Add full-text search using PostgreSQL `to_tsvector`
2. **Frontend:**
   - Update `useTableParams` to serialize filters/search to URL
   - Update `useCrud.getUsers` to pass all params to backend
   - Update `StandardTable` to show loading states
3. **API Layer:**
   - Add query parameters to OpenAPI spec
   - Regenerate TypeScript clients

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                            |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - Scales to millions of rows<br>- Consistent with RESTful patterns<br>- Supports complex queries (date ranges, etc.)<br>- Database-optimized          |
| **Cons**            | - Longer implementation (3-5 days)<br>- Backend changes required for every entity<br>- Increased API calls (higher latency)<br>- More complex testing |
| **Complexity**      | Medium-High                                                                                                                                           |
| **Maintainability** | Excellent (standard REST pattern)                                                                                                                     |
| **Performance**     | Excellent at any scale                                                                                                                                |

---

### Option 3: **Hybrid Approach (Recommended)**

**Architecture & Design:**

- Client-side sorting, filtering, search for **small entities** (<500 rows expected)
  - Users, Departments, Cost Element Types
- Server-side for **large entities** (>500 rows expected)
  - Projects, WBEs, Cost Elements
- Use feature flags in `StandardTable` to choose mode: `mode: "client" | "server"`

**UX Design:**

- Identical UX regardless of mode
- Smart debouncing only for server-side mode
- Loading indicators only for server-side

**Implementation:**

1. **Phase 1 (Client-side):** Implement Option 1 for all tables
2. **Phase 2 (Server-side):** Implement Option 2 for Projects, WBEs, Cost Elements
3. **Phase 3 (Refactor):** Abstract mode selection into `StandardTable` prop

**Component API:**

```typescript
<StandardTable<T>
  mode="client" // or "server"
  dataSource={data}
  columns={columns}
  searchable={true}
  searchPlaceholder="Search projects..."
  // ... rest unchanged
/>
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Pros**            | - Best of both worlds<br>- Optimal performance per use case<br>- Incremental migration path<br>- Flexibility for future growth |
| **Cons**            | - Two codepaths to maintain<br>- Decision complexity (when to use which?)<br>- More comprehensive testing needed               |
| **Complexity**      | Medium                                                                                                                         |
| **Maintainability** | Good (if well-abstracted)                                                                                                      |
| **Performance**     | Optimal for each use case                                                                                                      |

---

## Comparison Summary

| Criteria               | Option 1: Client-Side | Option 2: Server-Side   | Option 3: Hybrid         |
| ---------------------- | --------------------- | ----------------------- | ------------------------ |
| **Development Effort** | 1-2 days              | 3-5 days                | 2-3 days (phased)        |
| **UX Quality**         | ⭐⭐⭐⭐ (fast)       | ⭐⭐⭐ (loading states) | ⭐⭐⭐⭐ (context-aware) |
| **Scalability**        | ⚠️ <1000 rows         | ✅ Unlimited            | ✅ Adaptive              |
| **Backend Changes**    | None                  | High                    | Medium                   |
| **Flexibility**        | Low                   | Medium                  | High                     |
| **Best For**           | Small datasets only   | Large datasets only     | Mixed dataset sizes      |

---

## Recommendation

**I recommend Option 3: Hybrid Approach** because:

1. **Pragmatic:** Solves immediate problem (consistency) without over-engineering
2. **Scalable:** Provides migration path when data grows
3. **Aligned with PDCA:** Incremental improvement, measurable impact
4. **Low Risk:** Phase 1 delivers value quickly; Phase 2/3 are optional

**Implementation Sequence:**

1. **Sprint 1 (Immediate):** Phase 1 - Client-side for all tables
   - Achieves consistency goal
   - No backend changes
   - Quick win for UX
2. **Sprint 2-3 (As needed):** Phase 2 - Server-side for large entities
   - Only when performance degrades
   - Iterative per entity
3. **Future:** Phase 3 - Abstraction and refinement

**Alternative consideration:** If data sizes are guaranteed to stay small (<500 rows for ALL entities), choose **Option 1** for simplicity.

---

## Questions for Decision

1. **Data Growth:** Do we expect any entity to exceed 1,000 rows in the next 6 months?

   - If **No** → Option 1
   - If **Yes** → Option 3

2. **Backend Investment:** Are we willing to update backend services now or defer?

   - If **Now** → Option 2 or 3
   - If **Later** → Option 1 or 3

3. **Priority:** Is consistency more important than scalability right now?

   - If **Yes** → Option 1 (fast) or Option 3 Phase 1
   - If **No** → Option 2

4. **Search Scope:** Should search be global (across all pages) or per-page only?
   - **Per-page** → Option 1 viable
   - **Global** → Option 2 or 3 required

---

## Proposed Documentation Updates

Once a solution is chosen, update:

1. **Architecture:**

   - `docs/02-architecture/frontend/contexts/ui-patterns.md` (create if missing)
   - Document StandardTable patterns and when to use client vs server mode

2. **Component Documentation:**

   - Add JSDoc to `StandardTable` component
   - Add usage examples to Storybook (if available)

3. **Developer Guide:**

   - `docs/02-architecture/frontend/developer-guide.md`
   - "How to create a new list page" section
   - Include sorting, filtering, and search patterns

4. **ADR (if choosing Option 3):**
   - `docs/02-architecture/decisions/ADR-008-table-data-modes.md`
   - Document decision to support both client and server-side modes

---

## Next Steps

**If proceeding with recommended Option 3:**

1. ✅ User approves this analysis
2. ⏭️ Create PLAN artifact (`01-plan.md`) following PDCA workflow
3. ⏭️ Implement Phase 1 (client-side enhancements)
4. ⏭️ Verify with E2E tests
5. ⏭️ CHECK phase and documentation updates
6. ⏭️ Schedule Phase 2 when needed

**Estimated Timeline:**

- Analysis: ✅ Complete
- Planning: 30 minutes
- Implementation Phase 1: 1-2 days
- Testing: 0.5 days
- Documentation: 0.5 days
- **Total: 2-3 days**
