# PLAN: Frontend Table Harmonization - Phase 2 (Server-Side)

**Iteration:** 2026-01-08-table-harmonization-phase2  
**Phase:** 1 of 3 (Planning)  
**Status:** 📋 Planning  
**Planned Start:** TBD  
**Estimated Duration:** 4-5 days

---

## Objectives

### Primary Goal

Migrate the **three-level filtering system** from client-side to server-side for Projects, WBEs, and Cost Elements to enable:

1. **Global search** across entire datasets (not just current page)
2. **Scalable filtering** for datasets > 1000 records
3. **Zero UX regression** - identical user experience as Phase 1

### Success Criteria

- ✅ Global search works across entire dataset (not per-page)
- ✅ Per-column text filters work server-side
- ✅ Categorical filters work server-side
- ✅ Sorting works server-side
- ✅ **Identical UX** to Phase 1 (users notice zero difference except performance)
- ✅ URL format unchanged (`?filters=column:value;column:value`)
- ✅ Zero TypeScript errors (strict mode)
- ✅ Zero E2E test failures
- ✅ Backend response time < 200ms (p95) with 10,000 records

### Out of Scope (Phase 3)

- ❌ Advanced query builder UI
- ❌ Saved filters/views
- ❌ Export filtered results
- ❌ Global search across all entities (cross-entity)

---

## Phase 2 Scope

### Entities to Migrate (3 total)

| #   | Entity        | Service              | Current State       | Target State   | Priority |
| --- | ------------- | -------------------- | ------------------- | -------------- | -------- |
| 1   | Projects      | `ProjectService`     | ✅ Client-side only | ✅ Server-side | High     |
| 2   | WBEs          | `WBEService`         | ✅ Client-side only | ✅ Server-side | High     |
| 3   | Cost Elements | `CostElementService` | ✅ Client-side only | ✅ Server-side | High     |

**Note:** Users and Departments will remain client-side (small datasets, optimal performance).

### Features to Implement

**1. Server-Side Search**

- Backend accepts `?search=` query param
- Searches across specified text fields using `ILIKE`
- Case-insensitive matching
- Returns total count for pagination

**2. Server-Side Filtering**

- Backend accepts `?filters=` query param (existing URL format)
- Parses format: `column:value;column:value;column:value1,value2`
- Converts to SQLAlchemy WHERE clauses
- Supports both text and categorical filters

**3. Server-Side Sorting**

- Backend accepts `?sort_field=` and `?sort_order=` query params (already exists)
- Applies ORDER BY dynamically
- Validates allowed fields

**4. Frontend Integration**

- Modify TanStack Query hooks to pass params to backend
- Remove client-side filtering logic (`useMemo`)
- Add loading states during server requests
- Maintain identical UX

---

## Technical Approach

### URL Format (Unchanged from Phase 1)

**User-Facing URL:**

```
/projects?page=1&per_page=20&search=alpha&filters=status:active;branch:main,dev&sort_field=name&sort_order=asc
```

**Backend Receives:**

- `page=1`
- `per_page=20`
- `search=alpha`
- `filters=status:active;branch:main,dev`
- `sort_field=name`
- `sort_order=asc`

### Filter Format Conversion

**Phase 1 (Client-Side):**

```typescript
// Frontend parses URL and filters in-memory
const filtered = data.filter(
  (item) => item.status === "active" && ["main", "dev"].includes(item.branch)
);
```

**Phase 2 (Server-Side):**

```python
# Backend parses filters and builds SQL
# Input: "status:active;branch:main,dev"
# Output: WHERE status = 'active' AND branch IN ('main', 'dev')
```

### Architecture Pattern

```
┌─────────────────────────────────────────────┐
│  Frontend (No UX Change)                    │
│  - User interacts with same UI              │
│  - URL format unchanged                     │
│  - StandardTable looks identical            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  useTableParams Hook                        │
│  - Reads URL params (same as Phase 1)       │
│  - NEW: Passes to TanStack Query            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  TanStack Query (e.g., useProjects)         │
│  - NEW: Sends params to backend             │
│  - Caches by query key                      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Backend API Endpoint                       │
│  - NEW: Accepts search, filters params      │
│  - Validates fields                         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Service Layer (ProjectService, etc.)       │
│  - NEW: Parses filter string                │
│  - NEW: Builds SQLAlchemy WHERE clauses     │
│  - NEW: Applies search (ILIKE)              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Database (PostgreSQL)                      │
│  - Executes optimized query                 │
│  - Returns paginated results + total        │
└─────────────────────────────────────────────┘
```

---

## Detailed Task Breakdown

### Task 1: Backend - Generic Filter Parser ⏱️ 4 hours

**File:** `backend/app/core/filtering.py` (create)

**Subtasks:**

- [ ] 1.1: Create `FilterParser` class
- [ ] 1.2: Implement `parse_filters(filter_string: str) -> Dict[str, List[str]]`
  - Input: `"status:active;branch:main,dev"`
  - Output: `{"status": ["active"], "branch": ["main", "dev"]}`
- [ ] 1.3: Implement `build_sqlalchemy_filters(model: Type, filters: Dict) -> List[BinaryExpression]`
  - Validates field names against model
  - Returns list of SQLAlchemy filter expressions
- [ ] 1.4: Add unit tests for parser
- [ ] 1.5: Add validation for SQL injection prevention

**Acceptance Criteria:**

- ✅ Parser handles all Phase 1 filter formats
- ✅ Invalid field names raise validation error
- ✅ SQL injection attempts are blocked
- ✅ All unit tests pass

**Example:**

```python
# backend/app/core/filtering.py
from typing import Dict, List, Type
from sqlalchemy import BinaryExpression
from sqlalchemy.orm import DeclarativeMeta

class FilterParser:
    @staticmethod
    def parse_filters(filter_string: str) -> Dict[str, List[str]]:
        """Parse filter string to dict.

        Args:
            filter_string: "column:value;column:value1,value2"

        Returns:
            {"column": ["value"], "column": ["value1", "value2"]}
        """
        if not filter_string:
            return {}

        filters = {}
        for filter_expr in filter_string.split(';'):
            if ':' not in filter_expr:
                continue
            column, values = filter_expr.split(':', 1)
            filters[column] = values.split(',')
        return filters

    @staticmethod
    def build_sqlalchemy_filters(
        model: Type[DeclarativeMeta],
        filters: Dict[str, List[str]]
    ) -> List[BinaryExpression]:
        """Build SQLAlchemy filter expressions.

        Args:
            model: SQLAlchemy model class
            filters: Parsed filters dict

        Returns:
            List of SQLAlchemy binary expressions

        Raises:
            ValueError: If field name is invalid
        """
        expressions = []
        for field, values in filters.items():
            # Validate field exists on model
            if not hasattr(model, field):
                raise ValueError(f"Invalid filter field: {field}")

            column = getattr(model, field)

            # Single value: equality
            if len(values) == 1:
                expressions.append(column == values[0])
            # Multiple values: IN clause
            else:
                expressions.append(column.in_(values))

        return expressions
```

---

### Task 2: Backend - Update ProjectService ⏱️ 3 hours

**File:** `backend/app/services/project.py`

**Subtasks:**

- [ ] 2.1: Add `search: Optional[str]` param to `get_projects()`
- [ ] 2.2: Add `filters: Optional[str]` param to `get_projects()`
- [ ] 2.3: Implement search logic (ILIKE on code, name)
- [ ] 2.4: Integrate `FilterParser` for filters
- [ ] 2.5: Update docstring and type hints
- [ ] 2.6: Add unit tests

**Acceptance Criteria:**

- ✅ Search works across code and name fields
- ✅ Filters work for status, branch, etc.
- ✅ Pagination still works correctly
- ✅ Total count reflects filtered results
- ✅ All unit tests pass

**Example:**

```python
# backend/app/services/project.py
from app.core.filtering import FilterParser

class ProjectService(TemporalService[Project, ProjectRead, ProjectCreate, ProjectUpdate]):
    async def get_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        filters: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_order: Optional[str] = "asc",
    ) -> Tuple[List[ProjectRead], int]:
        """Get paginated projects with search and filters.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            search: Search term (searches code, name)
            filters: Filter string (e.g., "status:active;branch:main")
            sort_field: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (projects, total_count)
        """
        stmt = select(Project)

        # Apply search
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Project.code.ilike(search_term),
                    Project.name.ilike(search_term),
                )
            )

        # Apply filters
        if filters:
            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                Project, parsed_filters
            )
            stmt = stmt.where(and_(*filter_expressions))

        # Apply sorting
        if sort_field:
            column = getattr(Project, sort_field)
            stmt = stmt.order_by(column.desc() if sort_order == "desc" else column.asc())

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute
        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        return [ProjectRead.model_validate(p) for p in projects], total
```

---

### Task 3: Backend - Update WBEService ⏱️ 3 hours

**File:** `backend/app/services/wbe.py`

**Subtasks:**

- [ ] 3.1: Add `search`, `filters` params to `get_wbes()`
- [ ] 3.2: Implement search logic (ILIKE on code, name)
- [ ] 3.3: Integrate `FilterParser`
- [ ] 3.4: Handle parent_wbe_name filter (requires join)
- [ ] 3.5: Add unit tests

**Acceptance Criteria:**

- ✅ Search works across code and name
- ✅ Filters work for level, branch, parent
- ✅ All unit tests pass

---

### Task 4: Backend - Update CostElementService ⏱️ 3 hours

**File:** `backend/app/services/cost_element.py`

**Subtasks:**

- [ ] 4.1: Add `search`, `filters` params to `get_cost_elements()`
- [ ] 4.2: Implement search logic (ILIKE on code, name)
- [ ] 4.3: Integrate `FilterParser`
- [ ] 4.4: Handle wbe_name and type_name filters (requires joins)
- [ ] 4.5: Add unit tests

**Acceptance Criteria:**

- ✅ Search works across code and name
- ✅ Filters work for type, WBE, branch
- ✅ All unit tests pass

---

### Task 5: Backend - Update API Endpoints ⏱️ 2 hours

**Files:**

- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/wbes.py`
- `backend/app/api/routes/cost_elements.py`

**Subtasks:**

- [ ] 5.1: Add `search: Optional[str] = Query(None)` to endpoints
- [ ] 5.2: Add `filters: Optional[str] = Query(None)` to endpoints
- [ ] 5.3: Pass params to service methods
- [ ] 5.4: Update OpenAPI documentation
- [ ] 5.5: Add API-level validation

**Acceptance Criteria:**

- ✅ Endpoints accept new query params
- ✅ OpenAPI docs show examples
- ✅ Invalid params return 400 errors

**Example:**

```python
# backend/app/api/routes/projects.py
@router.get("/", response_model=PaginatedResponse[ProjectRead])
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1),
    search: Optional[str] = Query(None, description="Search term (code, name)"),
    filters: Optional[str] = Query(
        None,
        description="Filters (e.g., 'status:active;branch:main,dev')",
    ),
    sort_field: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    service: ProjectService = Depends(get_project_service),
) -> PaginatedResponse[ProjectRead]:
    """List projects with search, filters, and sorting."""
    skip = (page - 1) * per_page
    projects, total = await service.get_projects(
        skip=skip,
        limit=per_page,
        search=search,
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    return PaginatedResponse(
        items=projects,
        total=total,
        page=page,
        per_page=per_page,
    )
```

---

### Task 6: Frontend - Update TanStack Query Hooks ⏱️ 2 hours

**Files:**

- `frontend/src/features/projects/api/projectsApi.ts`
- `frontend/src/features/wbes/api/wbesApi.ts`
- `frontend/src/features/cost-elements/api/costElementsApi.ts`

**Subtasks:**

- [ ] 6.1: Add `search`, `filters` params to API functions
- [ ] 6.2: Update query keys to include new params
- [ ] 6.3: Ensure proper cache invalidation

**Acceptance Criteria:**

- ✅ API functions pass params to backend
- ✅ Query keys include all params (for caching)
- ✅ TypeScript types are correct

**Example:**

```typescript
// frontend/src/features/projects/api/projectsApi.ts
export const useProjects = (params: {
  page: number;
  per_page: number;
  search?: string;
  filters?: string;
  sort_field?: string;
  sort_order?: "asc" | "desc";
}) => {
  return useQuery({
    queryKey: ["projects", params],
    queryFn: async () => {
      const response = await api.get("/api/v1/projects", { params });
      return response.data;
    },
  });
};
```

---

### Task 7: Frontend - Remove Client-Side Filtering ⏱️ 2 hours

**Files:**

- `frontend/src/features/projects/components/ProjectList.tsx`
- `frontend/src/pages/wbes/WBEList.tsx`
- `frontend/src/pages/financials/CostElementManagement.tsx`

**Subtasks:**

- [ ] 7.1: Remove `useMemo` filtering logic
- [ ] 7.2: Pass `tableParams` directly to API hooks
- [ ] 7.3: Add loading states (already handled by TanStack Query)
- [ ] 7.4: Verify UX is identical

**Acceptance Criteria:**

- ✅ No client-side filtering code remains
- ✅ Tables display server-filtered data
- ✅ UX is identical to Phase 1
- ✅ No TypeScript errors

**Example:**

```typescript
// frontend/src/features/projects/components/ProjectList.tsx
export const ProjectList: React.FC = () => {
  const { tableParams, handleTableChange } = useTableParams<ProjectRead>();

  // BEFORE (Phase 1 - Client-Side):
  // const filteredData = useMemo(() => {
  //   let result = data || [];
  //   if (tableParams.search) {
  //     result = result.filter(p => p.name.includes(tableParams.search));
  //   }
  //   return result;
  // }, [data, tableParams.search]);

  // AFTER (Phase 2 - Server-Side):
  const { data, isLoading } = useProjects({
    page: tableParams.page,
    per_page: tableParams.per_page,
    search: tableParams.search,
    filters: tableParams.filters,
    sort_field: tableParams.sortField,
    sort_order: tableParams.sortOrder,
  });

  return (
    <StandardTable
      dataSource={data?.items}
      loading={isLoading}
      // ... rest unchanged
    />
  );
};
```

---

### Task 8: Backend - Add Database Indexes ⏱️ 1 hour

**Files:**

- `backend/alembic/versions/XXXX_add_filter_indexes.py` (create)

**Subtasks:**

- [ ] 8.1: Create migration for indexes
- [ ] 8.2: Add index on `projects.status`
- [ ] 8.3: Add index on `projects.branch`
- [ ] 8.4: Add index on `wbes.level`
- [ ] 8.5: Add index on `wbes.branch`
- [ ] 8.6: Add index on `cost_elements.branch`
- [ ] 8.7: Run migration

**Acceptance Criteria:**

- ✅ Indexes created successfully
- ✅ Query performance improves (verify with EXPLAIN)

---

### Task 9: Update E2E Tests ⏱️ 3 hours

**Files:**

- `frontend/e2e/projects_crud.spec.ts`
- `frontend/e2e/wbe_crud.spec.ts`
- `frontend/e2e/cost_elements_crud.spec.ts`

**Subtasks:**

- [ ] 9.1: Verify search tests still pass
- [ ] 9.2: Verify filter tests still pass
- [ ] 9.3: Verify sort tests still pass
- [ ] 9.4: Add test for global search (create 30+ items, search across pages)
- [ ] 9.5: Add test for pagination with filters
- [ ] 9.6: Fix any failing tests

**Acceptance Criteria:**

- ✅ All existing E2E tests pass
- ✅ New global search test passes
- ✅ No flaky tests

**Example Test:**

```typescript
// frontend/e2e/projects_crud.spec.ts
test("should search globally across all pages", async ({ page }) => {
  // Create 30 projects (3 pages at 10 per page)
  for (let i = 1; i <= 30; i++) {
    await createProject(page, { code: `PROJ${i}`, name: `Project ${i}` });
  }

  await page.goto("/projects?per_page=10");

  // Search for project on page 3
  await page.getByPlaceholder("Search projects...").fill("Project 25");

  // Should find it even though it's not on current page
  await expect(page.getByText("PROJ25")).toBeVisible();
  await expect(page.getByText("1-1 of 1")).toBeVisible(); // Only 1 result
});
```

---

### Task 10: Backend - Add Unit Tests ⏱️ 3 hours

**Files:**

- `backend/tests/unit/core/test_filtering.py` (create)
- `backend/tests/unit/services/test_project_service.py` (update)
- `backend/tests/unit/services/test_wbe_service.py` (update)
- `backend/tests/unit/services/test_cost_element_service.py` (update)

**Subtasks:**

- [ ] 10.1: Test `FilterParser.parse_filters()`
- [ ] 10.2: Test `FilterParser.build_sqlalchemy_filters()`
- [ ] 10.3: Test service search functionality
- [ ] 10.4: Test service filter functionality
- [ ] 10.5: Test SQL injection prevention
- [ ] 10.6: Test invalid field names

**Acceptance Criteria:**

- ✅ All unit tests pass
- ✅ Code coverage > 90% for new code

---

### Task 11: Documentation ⏱️ 2 hours

**Files to Create/Update:**

- `docs/02-architecture/backend/filtering-and-search.md` (create)
- `docs/02-architecture/frontend/ui-patterns.md` (update)
- Component JSDoc (already done in tasks above)

**Subtasks:**

- [ ] 11.1: Document filter format specification
- [ ] 11.2: Document search implementation
- [ ] 11.3: Document when to use client vs server mode
- [ ] 11.4: Add examples for future developers
- [ ] 11.5: Update ADR if needed

**Acceptance Criteria:**

- ✅ Clear documentation for filter format
- ✅ Examples for common scenarios
- ✅ Consistent with coding standards

---

## Testing Strategy

### Unit Tests (Backend)

**Coverage:**

- ✅ Filter parsing (all formats)
- ✅ SQLAlchemy filter building
- ✅ Search logic (ILIKE)
- ✅ SQL injection prevention
- ✅ Invalid field validation

### Integration Tests (E2E)

**Coverage:**

- ✅ Global search across pages
- ✅ Per-column text filters
- ✅ Categorical filters
- ✅ Combined filters (search + filter + sort)
- ✅ Pagination with filters
- ✅ URL state persistence

### Performance Tests

**Coverage:**

- ✅ Query performance with 10,000 records
- ✅ Index effectiveness (EXPLAIN ANALYZE)
- ✅ Response time < 200ms (p95)

### Manual Testing Checklist

For each of the 3 migrated tables, verify:

- [ ] Global search finds items across all pages
- [ ] Per-column text filters work
- [ ] Categorical filters work
- [ ] Sorting works
- [ ] Pagination shows correct totals
- [ ] URL state persists
- [ ] Browser back/forward works
- [ ] UX is identical to Phase 1
- [ ] No console errors
- [ ] No TypeScript errors

---

## Risk Assessment

| Risk                                 | Impact | Probability | Mitigation                                       |
| ------------------------------------ | ------ | ----------- | ------------------------------------------------ |
| **Breaking existing E2E tests**      | High   | Medium      | Run tests frequently; feature flag for rollback  |
| **Performance regression**           | High   | Low         | Add indexes; profile queries; load test          |
| **SQL injection**                    | High   | Low         | Whitelist fields; validate operators; unit tests |
| **Frontend/backend schema mismatch** | Medium | Medium      | Generate types from OpenAPI; integration tests   |
| **UX regression**                    | High   | Low         | Extensive manual testing; E2E tests              |
| **Filter parsing bugs**              | Medium | Medium      | Comprehensive unit tests; edge case coverage     |

---

## Definition of Done

### Code Quality

- [ ] All TypeScript errors resolved (`tsc --noEmit`)
- [ ] All Python type errors resolved (`mypy`)
- [ ] All linting errors resolved (frontend + backend)
- [ ] No `any` casting (strict mode compliance)
- [ ] JSDoc/docstrings added to all public APIs

### Functionality

- [ ] Global search works across entire dataset
- [ ] All Phase 1 filters work server-side
- [ ] Pagination shows correct totals
- [ ] UX is identical to Phase 1

### Testing

- [ ] All backend unit tests pass
- [ ] All E2E tests pass
- [ ] Performance tests pass (< 200ms p95)
- [ ] Manual testing checklist completed
- [ ] No regressions identified

### Documentation

- [ ] `filtering-and-search.md` created
- [ ] `ui-patterns.md` updated
- [ ] Component JSDoc complete
- [ ] Code examples provided

### Review

- [ ] Code reviewed (self-review minimum)
- [ ] No known bugs or issues
- [ ] Ready for CHECK phase

---

## Timeline

**Total Estimated Time:** 28 hours ≈ **4-5 days**

| Day       | Tasks                          | Hours   |
| --------- | ------------------------------ | ------- |
| **Day 1** | Tasks 1-2 (Backend Foundation) | 7 hours |
| **Day 2** | Tasks 3-5 (Backend Services)   | 8 hours |
| **Day 3** | Tasks 6-7 (Frontend Migration) | 4 hours |
| **Day 4** | Tasks 8-10 (Testing)           | 7 hours |
| **Day 5** | Task 11 (Documentation)        | 2 hours |

**Buffer:** 0.5 days for unexpected issues

---

## Dependencies

**Upstream:**

- ✅ Phase 1 complete and deployed
- ✅ All tables use `StandardTable` and `useTableParams`
- ✅ URL format established

**Downstream:**

- Phase 3 (Advanced Features) depends on Phase 2 completion

**External:**

- None (all dependencies already in project)

---

## Next Steps

1. ✅ Approve this plan
2. ⏭️ Begin implementation (Task 1: Filter Parser)
3. ⏭️ Daily check-ins on progress
4. ⏭️ Create DO phase artifact when implementation begins
5. ⏭️ Move to CHECK phase when Definition of Done is met

---

## Notes

- **Zero UX Regression:** Users should not notice any difference except improved performance
- **URL Format Unchanged:** Existing URLs continue to work
- **Gradual Migration:** Only Projects, WBEs, Cost Elements migrate; Users/Departments stay client-side
- **Performance:** Database indexes are critical for query performance

---

**Plan Status:** 📋 Ready for Approval  
**Last Updated:** 2026-01-08
