# PLAN: Frontend Table Harmonization - Phase 1

**Iteration:** 2026-01-08-table-harmonization  
**Phase:** 1 of 3 (Client-Side Implementation)  
**Status:** 📋 Planning  
**Planned Start:** 2026-01-08  
**Estimated Duration:** 2-3 days

---

## Objectives

### Primary Goal

Implement **consistent sorting, filtering, and search** features across all 6 frontend table components using **client-side** logic.

### Success Criteria

- ✅ All tables have sortable columns (where appropriate)
- ✅ All tables have filterable columns (categorical data)
- ✅ All tables have search input (per-page, URL-synced)
- ✅ Zero TypeScript errors (strict mode)
- ✅ Zero E2E test failures
- ✅ Consistent UX across all tables

### Out of Scope (Phase 2)

- ❌ Server-side sorting/filtering/search
- ❌ Global search across all pages
- ❌ Backend API changes
- ❌ Pagination size changes

---

## Phase 1 Scope

### Tables to Update (6 total)

| #   | Component             | Location                                       | Current State      | Target State     |
| --- | --------------------- | ---------------------------------------------- | ------------------ | ---------------- |
| 1   | UserList              | `pages/admin/UserList.tsx`                     | 🟡 Partial sorting | ✅ Full features |
| 2   | DepartmentManagement  | `pages/admin/DepartmentManagement.tsx`         | 🟡 Partial sorting | ✅ Full features |
| 3   | ProjectList           | `features/projects/components/ProjectList.tsx` | ❌ No features     | ✅ Full features |
| 4   | WBEList               | `pages/wbes/WBEList.tsx`                       | ❌ No features     | ✅ Full features |
| 5   | WBETable              | `components/hierarchy/WBETable.tsx`            | 🟡 Partial sorting | ✅ Full features |
| 6   | CostElementManagement | `pages/financials/CostElementManagement.tsx`   | ✅ Most advanced   | ✅ Harmonized    |

### Features to Implement

**1. Column Sorting (Client-Side)**

- All sortable columns use custom comparator functions
- Sort state synced to URL (`?sort_field=name&sort_order=asc`)
- Three states: ascending, descending, none
- Visual indicator (arrow icons)

**2. Column Filtering (Client-Side)**

- Categorical columns (e.g., role, status, type) have filter dropdowns
- Multiple selections allowed per column
- Filter state synced to URL (`?filters=role:admin,user`)
- Clear filters option

**3. Search Input (Client-Side)**

- Single search input in toolbar
- Searches across all text columns
- Debounced (300ms) for performance
- Search state synced to URL (`?search=project`)
- Case-insensitive matching

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────┐
│  List Page Component (e.g., UserList)      │
│  - Uses useTableParams hook                 │
│  - Defines column configurations            │
│  - Client-side filtering logic              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  useTableParams Hook (Enhanced)             │
│  - Manages URL state (page, sort, filters)  │
│  - NEW: search parameter                    │
│  - NEW: filters serialization               │
│  - Returns: tableParams, handleTableChange  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  StandardTable Component (Enhanced)         │
│  - NEW: searchable prop                     │
│  - NEW: searchPlaceholder prop              │
│  - NEW: search input in toolbar             │
│  - Client-side filtering on dataSource      │
└─────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Client-Side Only (Phase 1)**

   - All data filtering happens in browser
   - Fast for datasets < 1000 rows
   - No backend changes required

2. **URL State Management**

   - All table state persists in URL
   - Enables sharing filtered views
   - Browser back/forward navigation works

3. **Reusable Components**

   - `StandardTable` handles common UI
   - `useTableParams` handles state logic
   - Tables only define column configs

4. **Type Safety**
   - Generic types: `StandardTable<T>`, `useTableParams<T>`
   - No `any` casting (per coding standards)
   - Full TypeScript strict mode

---

## Detailed Task Breakdown

### Task 1: Enhance `useTableParams` Hook ⏱️ 2 hours

**File:** `frontend/src/hooks/useTableParams.ts`

**Subtasks:**

- [ ] 1.1: Add `search` parameter to `TableParams` interface
- [ ] 1.2: Add `filters` serialization/deserialization to/from URL
- [ ] 1.3: Parse `?search=` from URL query params
- [ ] 1.4: Parse `?filters=` from URL (JSON serialized)
- [ ] 1.5: Update `handleTableChange` to sync filters to URL
- [ ] 1.6: Add JSDoc documentation
- [ ] 1.7: Update unit tests in `useTableParams.test.tsx`

**Acceptance Criteria:**

- ✅ Hook returns `search` in `tableParams`
- ✅ Hook returns `filters` in `tableParams`
- ✅ URL updates when search changes
- ✅ URL updates when filters change
- ✅ Browser back/forward works correctly
- ✅ All tests pass

**Technical Notes:**

```typescript
// URL format examples:
// ?page=1&per_page=10&search=project&sort_field=name&sort_order=asc
// ?filters=role:admin,user;status:active
```

---

### Task 2: Enhance `StandardTable` Component ⏱️ 3 hours

**File:** `frontend/src/components/common/StandardTable.tsx`

**Subtasks:**

- [ ] 2.1: Add `searchable?: boolean` prop
- [ ] 2.2: Add `searchPlaceholder?: string` prop
- [ ] 2.3: Add `onSearch?: (value: string) => void` prop
- [ ] 2.4: Render `Input.Search` in toolbar when `searchable=true`
- [ ] 2.5: Wire search input to call `onSearch` (debounced 300ms)
- [ ] 2.6: Add clear search button (X icon)
- [ ] 2.7: Update `StandardTable.test.tsx` with search tests
- [ ] 2.8: Add JSDoc documentation

**Acceptance Criteria:**

- ✅ Search input appears when `searchable={true}`
- ✅ Search input uses provided placeholder
- ✅ Search is debounced (300ms)
- ✅ Clear button resets search
- ✅ All tests pass
- ✅ Component is properly typed (no `any`)

**UI Design:**

```
┌─────────────────────────────────────────────┐
│ [Table Title]              🔍 [Search...] ⊕ │ ← Toolbar
└─────────────────────────────────────────────┘
│ Code ▲ │ Name ▼ │ Status 🔽 │ Actions │    ← Headers
├─────────┼─────────┼───────────┼─────────┤
│ ...     │ ...     │ ...       │ ...     │    ← Data
```

---

### Task 3: Update UserList Component ⏱️ 1.5 hours

**File:** `frontend/src/pages/admin/UserList.tsx`

**Subtasks:**

- [ ] 3.1: Add `searchable={true}` to `StandardTable`
- [ ] 3.2: Add `searchPlaceholder="Search users..."`
- [ ] 3.3: Implement client-side search logic (filter dataSource)
- [ ] 3.4: Add `sorter` comparator to all text columns
- [ ] 3.5: Add `filters` to `role` column (admin, user, viewer)
- [ ] 3.6: Add `filters` to `is_active` column (active, inactive)
- [ ] 3.7: Implement `onFilter` functions for each column
- [ ] 3.8: Test manually with various search/filter combinations

**Acceptance Criteria:**

- ✅ Search works across full_name, email, department
- ✅ All columns are sortable
- ✅ Role and Status are filterable
- ✅ URL state persists correctly
- ✅ No TypeScript errors

**Search Logic Example:**

```typescript
const filteredUsers = useMemo(() => {
  let result = users || [];

  // Apply search
  if (tableParams.search) {
    const search = tableParams.search.toLowerCase();
    result = result.filter(
      (u) =>
        u.full_name.toLowerCase().includes(search) ||
        u.email.toLowerCase().includes(search) ||
        u.department?.toLowerCase().includes(search)
    );
  }

  return result;
}, [users, tableParams.search]);
```

---

### Task 4: Update DepartmentManagement Component ⏱️ 1 hour

**File:** `frontend/src/pages/admin/DepartmentManagement.tsx`

**Subtasks:**

- [ ] 4.1: Add `searchable={true}` to `StandardTable`
- [ ] 4.2: Add `searchPlaceholder="Search departments..."`
- [ ] 4.3: Implement client-side search logic
- [ ] 4.4: Add `sorter` comparator to name, code columns
- [ ] 4.5: Test manually

**Acceptance Criteria:**

- ✅ Search works across name, code, description
- ✅ Name and Code columns are sortable
- ✅ No TypeScript errors

---

### Task 5: Update ProjectList Component ⏱️ 2 hours

**File:** `frontend/src/features/projects/components/ProjectList.tsx`

**Subtasks:**

- [ ] 5.1: Add `searchable={true}` to `StandardTable`
- [ ] 5.2: Add `searchPlaceholder="Search projects..."`
- [ ] 5.3: Implement client-side search logic
- [ ] 5.4: Add `sorter` comparator to code, name, budget, dates
- [ ] 5.5: Add `filters` to `branch` column (main, draft, dev)
- [ ] 5.6: Implement budget sorting (parse string to number)
- [ ] 5.7: Implement date sorting (parse string to Date)
- [ ] 5.8: Test manually

**Acceptance Criteria:**

- ✅ Search works across code, name
- ✅ All columns sortable (including budget, dates)
- ✅ Branch is filterable
- ✅ Currency values sort numerically
- ✅ Dates sort chronologically
- ✅ No TypeScript errors

**Numeric Sorting Example:**

```typescript
{
  title: "Budget",
  dataIndex: "budget",
  sorter: (a, b) => parseFloat(a.budget) - parseFloat(b.budget),
  render: (val) => formatCurrency(val),
}
```

---

### Task 6: Update WBEList Component ⏱️ 2 hours

**File:** `frontend/src/pages/wbes/WBEList.tsx`

**Subtasks:**

- [ ] 6.1: Add `searchable={true}` to `StandardTable`
- [ ] 6.2: Add `searchPlaceholder="Search WBEs..."`
- [ ] 6.3: Implement client-side search logic
- [ ] 6.4: Add `sorter` comparator to code, name, level, budget
- [ ] 6.5: Add `filters` to `level` column (L1, L2, L3, ...)
- [ ] 6.6: Add `filters` to `branch` column (main, draft, dev)
- [ ] 6.7: Test manually

**Acceptance Criteria:**

- ✅ Search works across code, name
- ✅ All columns sortable
- ✅ Level and Branch are filterable
- ✅ Budget sorts numerically
- ✅ No TypeScript errors

---

### Task 7: Update WBETable Component ⏱️ 1.5 hours

**File:** `frontend/src/components/hierarchy/WBETable.tsx`

**Subtasks:**

- [ ] 7.1: Add optional `searchable` prop
- [ ] 7.2: Add optional `onSearch` prop
- [ ] 7.3: Ensure existing `localeCompare` sorter is consistent
- [ ] 7.4: Add `filters` to `level` column (if applicable)
- [ ] 7.5: Test in drill-down context (ProjectDetailPage, WBEDetailPage)

**Acceptance Criteria:**

- ✅ Existing sorting works correctly
- ✅ Component accepts search props (optional)
- ✅ No regressions in drill-down pages
- ✅ No TypeScript errors

**Note:** WBETable is used in detail pages, not list pages. Search may not be needed here, but we ensure consistency.

---

### Task 8: Harmonize CostElementManagement Component ⏱️ 1.5 hours

**File:** `frontend/src/pages/financials/CostElementManagement.tsx`

**Subtasks:**

- [ ] 8.1: Add `searchable={true}` to `StandardTable`
- [ ] 8.2: Add `searchPlaceholder="Search cost elements..."`
- [ ] 8.3: Ensure existing filters (Type, WBE) work correctly
- [ ] 8.4: Standardize to match other tables' patterns
- [ ] 8.5: Remove any custom filter logic that's now redundant
- [ ] 8.6: Test manually with branch selector

**Acceptance Criteria:**

- ✅ Search works across code, name
- ✅ Existing Type and WBE filters still work
- ✅ Branch selector still works
- ✅ Consistent with other tables
- ✅ No TypeScript errors

**Note:** This table already has the most features. We're harmonizing, not rebuilding.

---

### Task 9: Update E2E Tests ⏱️ 3 hours

**Files:**

- `frontend/e2e/admin_login.spec.ts`
- `frontend/e2e/users_crud.spec.ts`
- `frontend/e2e/departments_crud.spec.ts`
- `frontend/e2e/projects_crud.spec.ts`
- `frontend/e2e/wbes_crud.spec.ts`
- `frontend/e2e/cost_elements_crud.spec.ts`

**Subtasks:**

- [ ] 9.1: Add test for search in UserList
- [ ] 9.2: Add test for sorting in ProjectList
- [ ] 9.3: Add test for filtering in WBEList
- [ ] 9.4: Verify no regressions in existing CRUD tests
- [ ] 9.5: Run full E2E suite locally
- [ ] 9.6: Fix any failing tests

**Acceptance Criteria:**

- ✅ All existing E2E tests pass
- ✅ New search/filter/sort tests pass
- ✅ No flaky tests

**Example Test:**

```typescript
test("should search users by name", async ({ page }) => {
  await page.goto("/admin/users");
  await expect(page.locator(".ant-table-wrapper")).toBeVisible();

  // Search
  await page.getByPlaceholder("Search users...").fill("admin");
  await expect(page.locator(".ant-table-row")).toHaveCount(1);

  // Clear search
  await page.getByPlaceholder("Search users...").clear();
  await expect(page.locator(".ant-table-row")).toHaveCount.greaterThan(1);
});
```

---

### Task 10: Documentation ⏱️ 2 hours

**Files to Create/Update:**

- `docs/02-architecture/frontend/ui-patterns.md` (create)
- `docs/02-architecture/frontend/developer-guide.md` (update or create)
- Component JSDoc (already done in tasks above)

**Subtasks:**

- [ ] 10.1: Create `ui-patterns.md` documenting StandardTable patterns
- [ ] 10.2: Document when to use client vs server mode (Phase 2)
- [ ] 10.3: Add examples of column configurations
- [ ] 10.4: Update developer guide with "How to create a list page"
- [ ] 10.5: Document search, filter, sort patterns

**Acceptance Criteria:**

- ✅ Clear documentation for future developers
- ✅ Code examples for common scenarios
- ✅ Consistent with coding standards

---

## Testing Strategy

### Unit Tests (Vitest + React Testing Library)

**Files:**

- `frontend/src/hooks/useTableParams.test.tsx` (update)
- `frontend/src/components/common/StandardTable.test.tsx` (update)

**Coverage:**

- ✅ URL state serialization/deserialization
- ✅ Debounced search behavior
- ✅ Filter state management
- ✅ Sort state management

### Integration Tests (E2E with Playwright)

**Coverage:**

- ✅ User can search across all tables
- ✅ User can sort columns
- ✅ User can filter by categorical values
- ✅ URL state persists and can be shared
- ✅ Browser back/forward navigation works

### Manual Testing Checklist

For each of the 6 tables, verify:

- [ ] Search input appears and is functional
- [ ] Search is case-insensitive
- [ ] Search is debounced (no performance issues)
- [ ] All relevant columns are sortable
- [ ] Column sort icons display correctly (asc/desc/none)
- [ ] **Text columns** have text input filter dropdowns
- [ ] **Categorical columns** have checkbox filter dropdowns
- [ ] Multiple filter selections work (can combine filters)
- [ ] Clear filters works (per column)
- [ ] URL updates correctly for all state changes (search + filters + sort)
- [ ] URL can be shared (paste in new tab, state restored)
- [ ] Browser back/forward works
- [ ] No console errors
- [ ] No TypeScript errors (`npm run type-check`)
- [ ] No linting errors (`npm run lint`)

---

## Risk Assessment

| Risk                                            | Impact | Probability | Mitigation                                       |
| ----------------------------------------------- | ------ | ----------- | ------------------------------------------------ |
| **Breaking existing E2E tests**                 | High   | Medium      | Run tests frequently during development          |
| **Performance degradation with large datasets** | Medium | Low         | Use `useMemo` for filtering, limit to <1000 rows |
| **TypeScript type errors**                      | Medium | Low         | Use strict mode, avoid `any` casting             |
| **URL serialization conflicts**                 | Low    | Low         | Use clear delimiter (`:`, `;`)                   |
| **Filter state complexity**                     | Medium | Medium      | Keep filter logic simple, test edge cases        |

---

## Definition of Done

### Code Quality

- [ ] All TypeScript errors resolved (`tsc --noEmit`)
- [ ] All linting errors resolved (`npm run lint`)
- [ ] No `any` casting (strict mode compliance)
- [ ] All functions have type annotations
- [ ] JSDoc added to all public APIs

### Functionality

- [ ] All 6 tables have search, sort, filter features
- [ ] URL state syncs correctly for all features
- [ ] Client-side filtering works for datasets <1000 rows
- [ ] Debouncing prevents performance issues

### Testing

- [ ] All unit tests pass (`npm test`)
- [ ] All E2E tests pass (`npm run test:e2e`)
- [ ] Manual testing checklist completed
- [ ] No regressions identified

### Documentation

- [ ] `ui-patterns.md` created
- [ ] Developer guide updated
- [ ] Component JSDoc complete
- [ ] Code examples provided

### Review

- [ ] Code reviewed (self-review minimum)
- [ ] No known bugs or issues
- [ ] Ready for CHECK phase

---

## Timeline

**Total Estimated Time:** 22.5 hours ≈ **2.5-3 days**

**Note:** Added 3 hours for per-column text filter implementation across all tables

| Day       | Tasks                       | Hours      |
| --------- | --------------------------- | ---------- |
| **Day 1** | Tasks 1-2 (Foundation)      | 5 hours    |
| **Day 2** | Tasks 3-8 (Tables)          | 10.5 hours |
| **Day 3** | Tasks 9-10 (Testing & Docs) | 4 hours    |

**Buffer:** 0.5 days for unexpected issues

---

## Dependencies

**Upstream:**

- ✅ Analysis complete and approved

**Downstream:**

- Phase 2 (server-side) depends on Phase 1 completion
- Documentation patterns will be reused in Phase 2

**External:**

- None

---

## Next Steps

1. ✅ Approve this plan
2. ⏭️ Begin implementation (Task 1)
3. ⏭️ Check in daily on progress
4. ⏭️ Create DO phase artifact when implementation begins
5. ⏭️ Move to CHECK phase when Definition of Done is met

---

## Notes

- **Phase 1 Limitation:** Search is per-page only (not global). This will be addressed in Phase 2.
- **Performance:** Client-side filtering is fast for current datasets but won't scale beyond ~1000 rows.
- **Future Work:** Phase 2 will add server-side capabilities for projects, WBEs, and cost elements.

---

**Plan Status:** 📋 Ready for Approval  
**Last Updated:** 2026-01-08
