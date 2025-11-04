# Code quality

## Retrospectives and Lessons Learned

This section captures key learnings from development sessions to prevent repeating mistakes and improve our workflow.

### Session 1: E1-004 Project Creation Interface (2025-11-02)

**Process Improvements That Worked:**

- High-level analysis before implementation (PLA_1 pattern)
- Reusing existing components as reference (AddUser.tsx pattern)
- TypeScript strict checking caught issues early
- Working agreements (TDD mindset) kept focus on quality

**Key Patterns to Remember:**

1. Modal forms: DialogRoot → DialogTrigger (Button) → DialogContent → Form
2. useQuery needs arrow function: `queryFn: () => Service.method()`
3. useMutation: mutationFn → onSuccess (toast, reset, close) → onSettled (invalidate)
4. React Hook Form Controller: `value={field.value || ""}` for nullable selects
5. React Hook Form: mode="onBlur" for optimal UX, criteriaMode="all" for validation

**Docker Build Checklist:**

```bash
After Docker build:
1. docker compose up -d --force-recreate <service>
2. docker compose exec <service> ls <expected-files>
3. docker compose logs <service> --tail=20
4. Hard refresh browser (Ctrl+F5)
5. Screenshot to verify UI changes
```

### Session 2: E1-004 Permission Bug Fix (2025-11-02)

**Critical Learning:** Always check logs FIRST before theorizing root causes.

**Process Improvements That Worked:**

- Direct database access via Docker exec for quick operations
- Python one-liner for database queries: `python -c "..."`
- Verification step after fixes

**Debugging Workflow Checklist:**

```bash
When debugging unexpected behavior:
1. Check backend logs: docker compose logs backend --tail=100
2. Check frontend browser console for errors
3. Check network tab for failed requests (status codes)
4. Identify failing endpoint and check its permissions
5. THEN review code and form hypotheses
6. Verify with additional logging/testing
```

**Key Technical Patterns:**

1. Debugging order: Logs → Network → Code (NOT Code → Theory → Logs)
2. Permission dependencies: Check `dependencies=[Depends(...)]` in route decorators
3. 403 vs 401: 403 = authenticated but insufficient privileges, 401 = not authenticated
4. Role-based access: Understand permission model before implementing features
5. JWT tokens contain user role - changes require logout/login to update

**Architectural Concern:**

Current design requires admin access to see project manager dropdown. Consider alternatives:

- Public endpoint `/api/v1/users/list-for-selection` (dropdown-only data)
- UI-level filtering by role
- Separate permission like "can_view_users"

### Session 3: Docker Compose Migration Error (2025-11-02)

**Critical Learning:** When Alembic can't find a migration revision, rebuild the Docker image to ensure latest migration files are included.

**Issue:** `docker compose up -d backend` failed with error: `Can't locate revision identified by '2bf8174fc249'`

**Root Cause:** The Docker image was built before the migration file existed or wasn't rebuilt after adding new migrations. When the `prestart` service tried to run `alembic upgrade head`, it couldn't find the migration file in the container.

**Solution:**
```bash
# Rebuild the backend image to include latest migration files
docker compose build backend

# Then start the service
docker compose up -d backend
```

**Migration File Consistency Check:**
- Migration docstring comment ("Revises: ...") should match the `down_revision` code
- Fixed: `2bf8174fc249` had comment saying "Revises: 2d34baa292d4" but code had `down_revision = '0883e2b56827'`

**Prevention Checklist:**
```bash
After adding new Alembic migrations:
1. docker compose build backend (ensures migration files are in image)
2. docker compose up -d backend (applies migrations via prestart)
3. docker compose logs prestart --tail=30 (verify migration succeeded)
4. docker compose ps backend (verify backend is running)
```

### Session 4: E1-005 WBE Creation Interface + Navigation Fix (2025-11-02)

**Process Improvements That Worked:**

- High-level analysis (PLA_1) before implementation identified correct pattern
- Following established pattern (AddProject.tsx) enabled smooth implementation
- Incremental step-by-step implementation (13 steps) kept progress clear
- Debugging with console logs and router devtools identified root cause quickly

**Critical Learning:** TanStack Router nested routes require parent route components to render `<Outlet />` for child routes to render, even when route matching succeeds.

**Issue:** Projects table navigation changed URL correctly but page didn't render. Router devtools showed route matched (`/projects/$id` active, status 200), but `ProjectDetail` component never rendered.

**Root Cause:** The `Projects` component (parent route at `/projects`) didn't render an `<Outlet />`, so child route component (`ProjectDetail` at `/projects/$id`) couldn't render even though route matching worked.

**Solution:**
```tsx
// In projects.tsx (parent route)
function Projects() {
  const location = useRouterState({ select: (state) => state.location.pathname })
  const isExactProjectsRoute = location === '/projects'

  return (
    <>
      {isExactProjectsRoute && (
        <Container>...projects list...</Container>
      )}
      <Outlet /> {/* REQUIRED for child routes to render */}
    </>
  )
}
```

**Key Technical Patterns:**

1. **TanStack Router Nested Routes:** Parent routes MUST render `<Outlet />` for child routes to render
2. **Typed Route Navigation:** Use `to: "/projects/$id"` with `params: { id }` instead of string templates for type safety
3. **Router State Access:** Use `useRouterState({ select })` for efficient router state access
4. **Route Matching vs Rendering:** Route can match successfully but component won't render without Outlet
5. **Debugging Navigation:** Router devtools show route matching status; console logs show component rendering

**TanStack Router Nested Routes Checklist:**

```bash
When implementing nested routes:
1. Verify route files follow naming: parent.tsx and parent.$param.tsx
2. Parent route component MUST render <Outlet /> for child routes
3. Use typed route navigation: to="/route/$param" with params={{ param }}
4. Check router devtools to verify route matching
5. Add console logs in child components to verify rendering
6. If route matches but doesn't render, check for missing <Outlet />
```

**Navigation Pattern:**
- Typed route: `navigate({ to: "/projects/$id", params: { id }, search: { page: 1 } })`
- String template (works but less type-safe): `navigate({ to: \`/projects/\${id}\` })`

**Architectural Insight:**
- TanStack Router's file-based routing automatically creates nested route structure
- Parent routes are responsible for rendering their child routes via Outlet
- Route matching and component rendering are separate concerns in nested route architecture

### Session 5: Enhanced Table Features with TanStack Table (2025-11-02)

**Objective:** Enhance all table layouts with column customization, filtering, sorting, and pagination using TanStack Table v8.

**What We Accomplished:**
- Integrated TanStack Table v8 with Chakra UI rendering
- Migrated 3 tables (Projects, WBEs, Cost Elements) to unified DataTable component
- Implemented column visibility, sorting, resizing, and filtering features
- Created reusable infrastructure: DataTable, ColumnVisibilityMenu, ColumnResizer, TableFilters, types.ts
- Added useTablePreferences hook for future localStorage integration
- Reduced code by ~210 lines while adding powerful features
- Zero TypeScript errors, zero linter warnings

**Critical Learning:** TanStack Table manages state internally. localStorage integration requires manual wiring via onStateChange handlers, but wasn't implemented.

**Critical Moment 1: Type Extension Challenge**

**What Happened:** Initial attempt to extend `ColumnDef` via `interface ColumnDefExtended extends ColumnDef` failed with TypeScript error: "An interface can only extend an object type or intersection of object types with statically known members."

**Why Significant:** TanStack Table's `ColumnDef` is a union type, making traditional interface extension impossible. This blocked custom column properties.

**What We Learned:** Union types can't be extended with interfaces. Use intersection types instead: `type ColumnDefExtended = ColumnDef & ColumnDefExtensions`.

**Technical Pattern:**
```typescript
// ❌ Doesn't work (union type extension)
interface ColumnDefExtended extends ColumnDef<TData> { ... }

// ✅ Works (intersection type)
type ColumnDefExtended<TData> = ColumnDef<TData> & ColumnDefExtensions
```

**Critical Moment 2: TDD Without Frontend Testing Framework**

**What Happened:** Project only had Playwright E2E tests, no unit test framework. Modified TDD approach using temporary compile-check files.

**Why Significant:** Invented custom RED-GREEN workflow using TypeScript compilation errors as "test failures."

**What We Learned:** TDD discipline is adaptable - compile-time verification works when unit test frameworks aren't available. Process: Create temporary import files → Get compile errors (RED) → Implement → Verify compilation (GREEN) → Delete temp files.

**Process Pattern:**
1. Create `_test-hook-compile.ts` importing non-existent hook
2. Run `tsc --noEmit` → Compile errors (RED phase)
3. Implement hook with JSDoc
4. Verify compilation succeeds (GREEN phase)
5. Delete temp file

**Critical Moment 3: localStorage Integration Deferred**

**What Happened:** Created `useTablePreferences` hook but didn't wire into DataTable due to TanStack Table's internal state management complexity.

**Why Significant:** Uncovered mismatch between TanStack Table's built-in state management and custom persistence needs.

**What We Learned:** TanStack Table expects controlled state via `state` and `onStateChange` props. Integration requires: extracting state from table, mapping to localStorage structure, handling state merges, and providing reset functionality.

**What Didn't Work:**
- Assuming simple localStorage integration
- Trying to persist state without controlling table state
- Deferring integration made feature incomplete

**Process Improvements That Worked:**

1. **Compile-First TDD:** TypeScript as test framework when no unit tests available
2. **Incremental Migration:** One table at a time reduced risk of breaking everything
3. **Pattern Reuse:** Following existing AddProject/AddUser patterns accelerated development
4. **Interface Documentation:** JSDoc on public APIs improved understanding
5. **Temporary Verification Files:** Created/destroyed temp files for compile verification

**Wasted Effort:**

1. **Column Reordering:** Implemented drag-and-drop infrastructure (react-dnd installed) but cancelled due to TanStack Table complexity. Could have skipped from start.
2. **Date Range Filters:** Added types but didn't implement UI. Partial work left in codebase.
3. **localStorage Hook Creation:** Built hook without integration plan, now unused.
4. **Reset Button:** Never implemented despite being in success criteria.

**What We Should Have Done Differently:**

1. **Research Before Building:** Should have investigated TanStack Table state management before creating localStorage hook
2. **Scope Earlier:** Column reordering should have been evaluated for necessity before installing react-dnd
3. **Integration First:** Should have wired localStorage alongside feature development, not after
4. **Success Criteria Review:** Should have reviewed all 17 criteria before starting to catch unrealistic assumptions

**Technical Insights:**

1. **TanStack Table State:** Uses internal state with optional controlled mode. `useReactTable` returns table instance with all state getters.
2. **Column Extension Pattern:** Intersection types work for union-based types, interfaces don't.
3. **Chakra UI Integration:** TanStack Table headless design makes Chakra UI integration straightforward via `flexRender`.
4. **Responsive Design:** Filters hidden on mobile (`display={{ base: 'none', md: 'flex' }}`) maintains clean UI.
5. **Code Reduction:** Moving from 3 manual tables to 1 reusable component reduced total LOC despite added features.

**Single Most Valuable Change:**

**Implementation:** Create pre-implementation research checklist that includes:
1. Does library have built-in state management?
2. What's the integration pattern with our UI framework?
3. Are there existing examples in codebase?
4. What's the complexity of each feature?
5. Can features be added incrementally?

**Why:** Would have caught localStorage integration needs, column reorder complexity, and state management patterns BEFORE starting implementation. Estimated savings: 2-3 hours of rework and deferred features.

**Patterns to Remember:**

1. **TDD Without Unit Tests:** Use TypeScript compilation as verification
2. **Union Type Extension:** Use intersection types, not interfaces
3. **TanStack Table State:** Built-in state management requires onStateChange for persistence
4. **Incremental Migration:** One component at a time reduces risk
5. **Chakra UI Integration:** flexRender bridges headless libraries to Chakra

**Migration Checklist:**

```bash
When migrating existing UI to new library:
1. Research library's state management approach
2. Find integration examples with your UI framework
3. Verify extension points (types, state, render)
4. Plan controlled vs uncontrolled components
5. Test state persistence patterns early
6. Migrate one instance at a time
7. Keep old implementation until new one verified
```
