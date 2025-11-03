<!-- 892847a4-3dcd-4121-9a8c-d7a15c7fd2e3 5afc49e5-3df9-490c-a2f2-6e841fecfa71 -->
# Enhanced Table Features with TanStack Table

## ANALYSIS PHASE SUMMARY

### 1. CODEBASE PATTERN ANALYSIS

**Existing Table Patterns:**

**Current Implementation (Chakra UI Basic Tables):**

- `frontend/src/routes/_layout/projects.tsx` - ProjectsTable (5 columns)
- `frontend/src/routes/_layout/projects.$id.tsx` - WBEsTable (5 columns)
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` - CostElementsTable (5 columns)
- Pattern: Basic Chakra UI `Table.Root` with hardcoded columns
- Pagination: TanStack Router search params + custom PaginationRoot
- No filtering, no sorting, no column customization

**Reference Pattern - Admin Table:**

- `frontend/src/routes/_layout/admin.tsx` - UsersTable with Actions column
- Uses same Chakra UI basic table pattern
- Shows Actions column integration pattern

**State Management Patterns:**

- TanStack Query for data fetching (`useQuery` with `queryKey` arrays)
- TanStack Router for URL state (`validateSearch` with Zod schemas)
- localStorage for auth token (`frontend/src/hooks/useAuth.ts`)
- React state hooks for component-level state

### 2. INTEGRATION TOUCHPOINT MAPPING

**Files to Create:**

1. `frontend/src/hooks/useTablePreferences.ts` - Custom hook for localStorage persistence
2. `frontend/src/components/DataTable/DataTable.tsx` - Reusable TanStack Table component
3. `frontend/src/components/DataTable/ColumnVisibilityMenu.tsx` - Column toggle UI
4. `frontend/src/components/DataTable/ColumnResizer.tsx` - Resize handle component
5. `frontend/src/components/DataTable/TableFilters.tsx` - Advanced filter UI
6. `frontend/src/components/DataTable/types.ts` - Shared TypeScript types

**Files to Modify:**

1. `frontend/package.json` - Add TanStack Table v8 and react-dnd dependencies
2. `frontend/src/routes/_layout/projects.tsx` - Replace ProjectsTable with DataTable
3. `frontend/src/routes/_layout/projects.$id.tsx` - Replace WBEsTable with DataTable
4. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` - Replace CostElementsTable with DataTable
5. `frontend/tsconfig.json` - May need path aliases for @/components/DataTable

**Backend API (No Changes Required):**

- Current APIs support skip/limit pagination ✅
- Filtering/sorting will be client-side (adequate for current data volumes)

### 3. ABSTRACTION INVENTORY

**Reusable Components:**

- Chakra UI Table primitives: `Table.Root`, `Table.Header`, `Table.Row`, `Table.Cell`
- Menu components: `MenuRoot`, `MenuTrigger`, `MenuContent`, `MenuCheckboxItem`
- Checkbox: `@/components/ui/checkbox` with Chakra primitives
- Input: Chakra `Input` component for filters
- Icons: `react-icons` (FiChevronDown, FiChevronUp, FiSettings, etc.)
- Pagination: Custom `PaginationRoot` component (already integrated)

**Reusable Hooks:**

- `useQuery` from TanStack Query for data fetching
- `useNavigate` from TanStack Router for URL state
- Custom `useAuth` hook pattern (reference for new `useTablePreferences` hook)

**TypeScript Patterns:**

- Generic type parameters for reusable components
- Zod schemas for validation (can extend for filter state)
- API-generated types from OpenAPI (`types.gen.ts`)

**Data Available:**

Projects: 12 fields (project_name, customer_name, contract_value, project_code, pricelist_code, start_date, planned_completion_date, actual_completion_date, status, notes, project_id, project_manager_id)

WBEs: 8 fields (machine_type, serial_number, contracted_delivery_date, revenue_allocation, status, notes, wbe_id, project_id)

Cost Elements: 9 fields (department_code, department_name, budget_bac, revenue_plan, status, notes, cost_element_id, wbe_id, cost_element_type_id)

### 4. ALTERNATIVE APPROACHES

**Selected Approach: TanStack Table v8 with Client-Side Operations**

**Pros:**

- Industry standard for React data tables (100k+ weekly downloads)
- Headless UI pattern - works perfectly with Chakra UI
- Built-in column visibility, sorting, filtering, resizing
- Excellent TypeScript support with generic types
- No breaking changes to backend APIs
- Can upgrade to server-side operations later

**Cons:**

- New dependency (~50kb gzipped)
- Learning curve for team
- Client-side filtering may be slow for 1000+ rows (acceptable for MVP)

**Alignment:** Follows React best practices, composable architecture, maintains existing Chakra UI visual design

**Complexity:** Medium-High (2-3 days implementation)

**Risk:** Low - well-tested library, no backend changes

---

**Alternative 1: Chakra UI Table + Manual State Management (NOT SELECTED)**

**Pros:** No new dependencies, incremental approach

**Cons:** Reinventing the wheel, more code to maintain, missing features (resize, reorder)

**Risk:** Medium - custom code bugs, feature gaps

---

**Alternative 2: AG-Grid or React-Table v7 (NOT SELECTED)**

**Pros:** Feature-rich, battle-tested

**Cons:** AG-Grid is paid for advanced features; React-Table v7 is deprecated

**Risk:** AG-Grid licensing, React-Table v7 migration path unclear

### 5. ARCHITECTURAL IMPACT ASSESSMENT

**Principles Followed:**

✅ **Separation of Concerns:** DataTable component is reusable across all tables

✅ **Progressive Enhancement:** Existing tables work, new features are additive

✅ **State Management:** URL state (sorting) + localStorage (preferences) + React state (UI)

✅ **Type Safety:** Full TypeScript support with generics

✅ **Accessibility:** TanStack Table has excellent a11y support

✅ **Performance:** Virtual scrolling available if needed (future)

**Maintenance Considerations:**

- DataTable component becomes core infrastructure (must be well-tested)
- Column definitions are declarative and easy to modify
- localStorage keys need versioning for future schema changes
- Each table has separate preferences (projects-table, wbes-table, cost-elements-table)

**Testing Challenges:**

- Backend tests unchanged (no API changes) ✅
- Frontend: Manual testing for column operations (Playwright tests future enhancement)
- localStorage mocking for unit tests
- Responsive design testing (mobile vs desktop)

**Future Extension Points:**

- Server-side filtering/sorting (add query params to backend APIs)
- CSV/Excel export functionality
- Bulk selection and operations
- Virtual scrolling for large datasets
- Saved filter presets

---

## IMPLEMENTATION PLAN

### Phase 1: Dependencies and Infrastructure (TDD - Setup)

**1.1 Install TanStack Table and supporting libraries**

```bash
cd frontend
npm install @tanstack/react-table@^8.20.5
npm install react-dnd react-dnd-html5-backend  # For column reordering
```

**1.2 Create useTablePreferences hook**

- Create `frontend/src/hooks/useTablePreferences.ts`
- Generic hook with TypeScript: `useTablePreferences<T>(tableId: string, defaultState: T)`
- Functions: `getPreferences()`, `setPreferences()`, `resetPreferences()`
- localStorage key pattern: `table-preferences-${tableId}`
- Handles JSON serialization/deserialization with error handling

**1.3 Create DataTable types**

- Create `frontend/src/components/DataTable/types.ts`
- Export interfaces: `ColumnDefExtended`, `TablePreferences`, `FilterConfig`
- Type definitions for filter types: text, select, date range

### Phase 2: Core DataTable Component (TDD - Build Reusable Component)

**2.1 Create base DataTable component**

- Create `frontend/src/components/DataTable/DataTable.tsx`
- Generic component: `DataTable<TData>()`
- Props: `data`, `columns`, `tableId`, `onRowClick?`, `isLoading`
- Integrate TanStack Table: `useReactTable` hook
- Render Chakra UI Table with TanStack Table state
- Support pagination (integrate existing PaginationRoot)

**2.2 Add column visibility controls**

- Create `frontend/src/components/DataTable/ColumnVisibilityMenu.tsx`
- Settings icon button triggers menu (FiSettings)
- MenuCheckboxItem for each column (show/hide toggles)
- Sync with TanStack Table `columnVisibility` state
- Save to localStorage via `useTablePreferences`

**2.3 Add column sorting**

- Modify DataTable to show sort indicators (FiChevronUp/FiChevronDown)
- Click column header to toggle sort direction
- TanStack Table `getSortedRowModel()` for client-side sorting
- Visual indicator in column header

**2.4 Add column resizing**

- Create `frontend/src/components/DataTable/ColumnResizer.tsx`
- Draggable resize handle at column border
- TanStack Table `getResizedColumnModel()`
- Save column widths to localStorage

### Phase 3: Advanced Filtering UI (TDD - Build Filter Components)

**3.1 Create TableFilters component**

- Create `frontend/src/components/DataTable/TableFilters.tsx`
- Filter bar above table with collapsible sections
- Per-column filter inputs based on column type
- Text filters: Chakra `Input` with debounce
- Select filters: Chakra `Select` for status columns
- Date range filters: Date inputs for date columns

**3.2 Implement filter logic**

- TanStack Table `getFilteredRowModel()` for client-side filtering
- Custom filter functions for different data types
- Case-insensitive text search
- Multiple filters combine with AND logic
- Clear all filters button

### Phase 4: Column Reordering (TDD - Drag and Drop)

**4.1 Add drag-and-drop for columns**

- Integrate `react-dnd` for column reordering
- Drag handle in column headers
- Visual feedback during drag (ghost column)
- TanStack Table `columnOrder` state
- Save order to localStorage

### Phase 5: Table Migrations (TDD - Replace Existing Tables)

**5.1 Migrate ProjectsTable**

- Modify `frontend/src/routes/_layout/projects.tsx`
- Define column definitions for all 12 Project fields
- Default visible columns: project_name, customer_name, status, start_date, planned_completion_date
- Advanced filters: text search, status select, date ranges
- Maintain row click navigation to project detail
- tableId: "projects-table"

**5.2 Migrate WBEsTable**

- Modify `frontend/src/routes/_layout/projects.$id.tsx`
- Define column definitions for all 8 WBE fields
- Default visible columns: machine_type, status, serial_number, revenue_allocation, contracted_delivery_date
- Advanced filters: text search, status select
- Maintain row click navigation to WBE detail
- tableId: "wbes-table"

**5.3 Migrate CostElementsTable**

- Modify `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`
- Define column definitions for all 9 Cost Element fields
- Default visible columns: department_name, department_code, status, budget_bac, revenue_plan
- Advanced filters: text search, status select, budget range
- Remove row click (no detail page)
- tableId: "cost-elements-table"

### Phase 6: Polish and Testing

**6.1 Responsive design**

- Mobile: Stack filters vertically, reduce columns
- Desktop: Full feature set
- Chakra UI responsive props: `display={{ base: "none", md: "block" }}`

**6.2 Loading states**

- Skeleton loading for table rows
- Disable interactions during loading
- Reuse existing `PendingItems` pattern

**6.3 Empty states**

- Maintain existing empty state UI
- Show "No results" when filters return empty

**6.4 Manual testing checklist**

- [ ] Column visibility toggle works, persists to localStorage
- [ ] Column resize works, persists to localStorage
- [ ] Column reorder works, persists to localStorage
- [ ] Sorting works (ascending/descending/none)
- [ ] Text filters work (case-insensitive)
- [ ] Status filters work (select dropdown)
- [ ] Date filters work (range selection)
- [ ] Multiple filters combine correctly (AND logic)
- [ ] Clear filters button works
- [ ] Pagination works with filters
- [ ] Row click navigation works (Projects, WBEs)
- [ ] Preferences persist across page refresh
- [ ] Preferences are separate per table
- [ ] Reset to defaults button works
- [ ] Responsive design works on mobile

---

## TECHNICAL SPECIFICATIONS

### DataTable Component API

```typescript
interface DataTableProps<TData> {
  data: TData[]
  columns: ColumnDef<TData>[]
  tableId: string  // Unique ID for localStorage
  onRowClick?: (row: TData) => void
  isLoading?: boolean
  count: number  // Total count for pagination
  page: number
  onPageChange: (page: number) => void
  pageSize?: number
}

// Usage example:
<DataTable
  data={projects}
  columns={projectColumns}
  tableId="projects-table"
  onRowClick={(project) => navigate({ to: `/projects/${project.project_id}` })}
  isLoading={isLoading}
  count={count}
  page={page}
  onPageChange={setPage}
/>
```

### localStorage Structure

```typescript
interface TablePreferences {
  columnVisibility: Record<string, boolean>
  columnOrder: string[]
  columnWidths: Record<string, number>
  sorting: { id: string; desc: boolean }[]
  filters: Record<string, any>
}

// localStorage key: `table-preferences-${tableId}`
// Example: "table-preferences-projects-table"
```

### Column Definition Example (Projects)

```typescript
const projectColumns: ColumnDef<ProjectPublic>[] = [
  {
    accessorKey: 'project_name',
    header: 'Project Name',
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: 'text',
    size: 200,
  },
  {
    accessorKey: 'status',
    header: 'Status',
    enableSorting: true,
    enableColumnFilter: true,
    filterType: 'select',
    filterOptions: ['active', 'on-hold', 'completed', 'cancelled'],
    cell: ({ getValue }) => (
      <span style={{ textTransform: 'capitalize' }}>
        {getValue() || 'active'}
      </span>
    ),
  },
  {
    accessorKey: 'start_date',
    header: 'Start Date',
    enableSorting: true,
    enableColumnFilter: true,
    filterType: 'dateRange',
    cell: ({ getValue }) => new Date(getValue()).toLocaleDateString(),
  },
  // ... more columns
]
```

---

## SUCCESS CRITERIA

1. ✅ TanStack Table v8 installed and integrated
2. ✅ All 3 tables (Projects, WBEs, Cost Elements) migrated to DataTable
3. ✅ Column visibility toggle working (show/hide any column)
4. ✅ Column reordering working (drag and drop)
5. ✅ Column resizing working (drag column borders)
6. ✅ Single-column sorting working (click headers)
7. ✅ Advanced filters working (text, select, date range)
8. ✅ Multiple filters combine with AND logic
9. ✅ All preferences persist to localStorage
10. ✅ Preferences are separate per table (3 independent configs)
11. ✅ Reset to defaults button working
12. ✅ Responsive design works on mobile
13. ✅ Row click navigation still works (Projects, WBEs)
14. ✅ Pagination still works with filters
15. ✅ Loading and empty states preserved
16. ✅ No linter errors or TypeScript errors
17. ✅ No backend API changes required

---

## RISKS AND MITIGATIONS

| Risk | Impact | Mitigation |

|------|--------|------------|

| TanStack Table learning curve | MEDIUM | Use official docs, follow examples, start simple |

| Client-side filtering slow (1000+ rows) | LOW | Acceptable for MVP, can add server-side later |

| localStorage quota exceeded | LOW | Keep preferences minimal, add quota handling |

| Column reorder complexity | MEDIUM | Use react-dnd library (tested solution) |

| Breaking existing tables | HIGH | ✅ Migrate one table at a time, test thoroughly |

| Mobile UX degradation | MEDIUM | Progressive enhancement, hide advanced features on small screens |

| TypeScript generic complexity | MEDIUM | Use TanStack Table examples, strong typing from start |

---

## DEPENDENCIES

- ✅ Existing Chakra UI components (Table, Menu, Input, etc.)
- ✅ TanStack Query for data fetching (already integrated)
- ✅ TanStack Router for URL state (already integrated)
- ✅ localStorage API (browser standard)
- ⏳ NEW: @tanstack/react-table v8 (to be installed)
- ⏳ NEW: react-dnd + react-dnd-html5-backend (to be installed)

---

## ESTIMATED EFFORT

- Phase 1: Dependencies and Infrastructure - 2 hours
- Phase 2: Core DataTable Component - 6 hours
- Phase 3: Advanced Filtering UI - 4 hours
- Phase 4: Column Reordering - 3 hours
- Phase 5: Table Migrations (3 tables) - 6 hours
- Phase 6: Polish and Testing - 3 hours
- **Total: ~24 hours (3 days of focused development)**

---

## INCREMENTAL DELIVERY STRATEGY

To maintain TDD discipline and small commits:

1. **Commit 1:** Install dependencies, create useTablePreferences hook (RED → GREEN)
2. **Commit 2:** Create base DataTable with basic rendering (RED → GREEN)
3. **Commit 3:** Add column visibility toggle (RED → GREEN)
4. **Commit 4:** Add sorting functionality (RED → GREEN)
5. **Commit 5:** Add column resizing (RED → GREEN)
6. **Commit 6:** Add text filters (RED → GREEN)
7. **Commit 7:** Add select and date filters (RED → GREEN)
8. **Commit 8:** Add column reordering (RED → GREEN)
9. **Commit 9:** Migrate ProjectsTable (RED → GREEN)
10. **Commit 10:** Migrate WBEsTable (RED → GREEN)
11. **Commit 11:** Migrate CostElementsTable (RED → GREEN)
12. **Commit 12:** Polish, responsive design, final testing (RED → GREEN)

### To-dos

- [ ] Install TanStack Table v8, react-dnd, and react-dnd-html5-backend dependencies
- [ ] Create useTablePreferences custom hook for localStorage persistence with generic types
- [ ] Create DataTable/types.ts with TypeScript interfaces for column definitions and preferences
- [ ] Create base DataTable component with TanStack Table integration and Chakra UI rendering
- [ ] Implement column visibility toggle with ColumnVisibilityMenu component
- [ ] Add single-column sorting with visual indicators in column headers
- [ ] Implement column resizing with draggable handles using ColumnResizer component
- [ ] Create TableFilters component with text, select, and date range filter inputs
- [ ] Implement client-side filtering logic with TanStack Table filtered row model
- [ ] Add column reordering with react-dnd drag-and-drop functionality
- [ ] Migrate ProjectsTable to use DataTable with all 12 fields and column definitions
- [ ] Migrate WBEsTable to use DataTable with all 8 fields and column definitions
- [ ] Migrate CostElementsTable to use DataTable with all 9 fields and column definitions
- [ ] Implement responsive design for mobile and tablet screens
- [ ] Add loading states, empty states, and error handling
- [ ] Complete manual testing checklist for all features across all 3 tables
