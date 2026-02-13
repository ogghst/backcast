# ANALYSIS: Frontend Table Harmonization - Phase 2 (Server-Side)

**Iteration:** 2026-01-08-table-harmonization-phase2  
**Phase:** 0 of 3 (Analysis)  
**Status:** 📋 Planning  
**Date:** 2026-01-08

---

## 1. Context

### Phase 1 Achievements

Phase 1 successfully implemented **client-side** sorting, filtering, and search across all 6 frontend table components:

**Three-Level Filtering System:**

1. **Global Search** (Toolbar): Searches across ALL text columns, debounced (300ms), URL-synced
2. **Per-Column Filters** (Column Headers):
   - **Text columns**: Text input filter (e.g., Name, Email, Code)
   - **Categorical columns**: Checkbox dropdown filter (e.g., Role, Status, Branch)
3. **Column Sorting**: All columns sortable (asc/desc/none)

**Implementation Details:**

- ✅ `StandardTable` component enhanced with search input and toolbar
- ✅ `useTableParams` hook manages URL state
- ✅ **URL serialization format**: `?page=1&search=project&filters=role:admin,user;status:active`
  - Format: `filters=column:value;column:value;column:value1,value2`
- ✅ Consistent UX patterns across all 6 tables
- ✅ Type-safe implementation (no `any` casting)

**Tables Updated:**

- UserList, DepartmentManagement, ProjectList, WBEList, WBETable, CostElementManagement

### Phase 1 Limitations

**Performance Constraint:**

- Client-side filtering loads **all records** into memory
- Acceptable for datasets < 1000 records
- **Not scalable** for production datasets (Projects, WBEs, Cost Elements)
- Future entities (Cost Registrations) will exceed 1000 rows

**User Experience Gap:**

- Search is **per-page only** (not global across entire dataset)
- No ability to filter large datasets efficiently
- Backend already supports pagination but doesn't accept filter/search params

---

## 2. Problem Statement

### Current State

**Backend:**

- All list endpoints support pagination (`page`, `per_page`)
- No support for filtering by arbitrary fields
- No support for server-side search
- No support for server-side sorting

**Frontend:**

- Fetches all records (or first page only)
- Applies filtering/search/sort in browser using `useMemo`
- URL state already serializes filters (`filters=column:value;column:value`)
- **Ready for server-side**: Just need to pass URL params to API calls

### Target State

**Backend:**

- Endpoints accept filter parameters (e.g., `?status=active&role=admin`)
- Endpoints accept search parameters (e.g., `?search=project`)
- Endpoints accept sort parameters (e.g., `?sort_by=name&sort_order=asc`)
- Filtering is performed at the database level (efficient)

**Frontend:**

- Sends filter/search/sort params to backend (using existing URL format)
- Displays paginated results from server
- **Maintains identical UX** as Phase 1 (zero regression)
- **Three-level filtering system preserved**:
  - Global search → backend `?search=` param
  - Per-column text filters → backend `?filters=name:john` param
  - Categorical filters → backend `?filters=role:admin,user` param

---

## 3. Scope

### In Scope (Phase 2)

**Backend Changes:**

1. Add generic filtering support to `TemporalService` and `VersionedCommandABC`
2. Implement RSQL-style query parsing (e.g., `?filter=status==active;role==admin`)
3. Add search support (full-text or ILIKE across specified fields)
4. Add sort support (dynamic ORDER BY clauses)
5. Update OpenAPI schemas to document new query params

**Frontend Changes:**

1. Modify `useTableParams` to send params to backend (instead of local filtering)
2. Update TanStack Query hooks to pass filter/search/sort params
3. Ensure `StandardTable` continues to work seamlessly
4. Add loading states during server requests
5. Update E2E tests to verify server-side behavior

**Entities to Migrate:**

- Projects
- WBEs
- Cost Elements
- Users (optional, low priority)
- Departments (optional, low priority)

### Out of Scope

- ❌ Global search across all entities (future)
- ❌ Advanced query builder UI (future)
- ❌ Saved filters/views (future)
- ❌ Export filtered results (future)

---

## 4. Technical Approach

### Option A: RSQL (Recommended)

**RSQL (RESTful Service Query Language)** is a standard for expressing queries in URLs.

**Example:**

```
GET /api/v1/projects?filter=status==active;budget>100000&sort=name,asc&page=1&per_page=20
```

**Pros:**

- Industry standard (used by Spring Data REST, etc.)
- Expressive (supports `==`, `!=`, `>`, `<`, `=in=`, etc.)
- Single query param (`filter`) keeps URLs clean
- Easy to parse with libraries like `rsql-parser`

**Cons:**

- Requires backend parser implementation
- Slightly more complex than simple key-value params

**Implementation:**

- Use Python library: `rsql-parser` or custom parser
- Map RSQL to SQLAlchemy filters dynamically
- Validate allowed fields to prevent SQL injection

---

### Option B: Simple Key-Value Params

**Example:**

```
GET /api/v1/projects?status=active&budget_min=100000&sort_by=name&sort_order=asc
```

**Pros:**

- Simple to implement
- Easy to understand
- No parsing library needed

**Cons:**

- URL gets cluttered with many filters
- Hard to express complex queries (OR, IN, etc.)
- Not standardized

**Implementation:**

- Add query params to FastAPI endpoint signatures
- Map params to SQLAlchemy filters manually
- Requires separate param for each filterable field

---

### Option C: JSON in Query Param

**Example:**

```
GET /api/v1/projects?filters={"status":"active","budget":{"$gt":100000}}&sort={"name":"asc"}
```

**Pros:**

- Flexible (supports nested objects)
- Can express complex queries

**Cons:**

- URL encoding is ugly
- Not RESTful
- Hard to read/debug

---

### Recommendation: **Option A (RSQL)**

RSQL provides the best balance of expressiveness, standardization, and scalability. It's worth the upfront investment for long-term maintainability.

---

## 5. Architecture Design

### Backend Layer Changes

```
┌─────────────────────────────────────────────┐
│  FastAPI Endpoint (e.g., /api/v1/projects)  │
│  - Accepts: filter, search, sort params     │
│  - Validates: allowed fields, operators     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  ProjectService (or TemporalService)        │
│  - Parses RSQL filter string                │
│  - Builds SQLAlchemy WHERE clauses          │
│  - Applies search (ILIKE across fields)     │
│  - Applies sort (ORDER BY)                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  SQLAlchemy Query                           │
│  - Executes optimized SQL                   │
│  - Returns paginated results                │
└─────────────────────────────────────────────┘
```

### Frontend Layer Changes

```
┌─────────────────────────────────────────────┐
│  List Page Component (e.g., ProjectList)    │
│  - Uses useTableParams hook                 │
│  - Passes params to TanStack Query          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  useTableParams Hook (Enhanced)             │
│  - Serializes filters to RSQL format        │
│  - Returns: filter, search, sort strings    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  TanStack Query Hook (e.g., useProjects)    │
│  - Sends filter/search/sort to backend      │
│  - Caches results by query key              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Backend API                                │
│  - Returns paginated, filtered results      │
└─────────────────────────────────────────────┘
```

---

## 6. Data Flow Example

### User Action: Filter Projects by Status

**Step 1: User Interaction**

- User selects "Active" in Status filter dropdown

**Step 2: Frontend State Update**

- `useTableParams` updates URL: `?filters=status:active` (existing Phase 1 format)
- **NEW**: Convert to RSQL for backend: `status==active`
- URL format stays the same (user-facing), RSQL is internal

**Step 3: API Request**

- TanStack Query sends: `GET /api/v1/projects?filter=status==active&page=1&per_page=20`

**Step 4: Backend Processing**

- FastAPI endpoint receives `filter` param
- `ProjectService` parses RSQL: `status==active`
- Builds SQLAlchemy filter: `Project.status == "active"`
- Executes query with pagination

**Step 5: Response**

- Backend returns: `{ items: [...], total: 42, page: 1, per_page: 20 }`

**Step 6: Frontend Rendering**

- TanStack Query caches result
- `StandardTable` displays filtered data
- Pagination shows "1-20 of 42"

---

## 7. Risk Assessment

| Risk                                     | Impact | Probability | Mitigation                                         |
| ---------------------------------------- | ------ | ----------- | -------------------------------------------------- |
| **RSQL parsing complexity**              | High   | Medium      | Use proven library; add comprehensive unit tests   |
| **SQL injection via malicious filters**  | High   | Low         | Whitelist allowed fields; validate operators       |
| **Breaking existing frontend behavior**  | High   | Medium      | Feature flag; gradual rollout; extensive E2E tests |
| **Performance regression on backend**    | Medium | Low         | Add database indexes; profile queries              |
| **URL length limits (too many filters)** | Low    | Low         | RSQL is compact; warn if URL > 2000 chars          |
| **Frontend/backend schema mismatch**     | Medium | Medium      | Generate TypeScript types from OpenAPI; add tests  |

---

## 8. Success Metrics

### Performance

- ✅ List endpoints respond in < 200ms (p95) with 10,000 records
- ✅ Database query execution < 50ms (p95)
- ✅ No N+1 queries introduced

### Functionality

- ✅ All Phase 1 features work identically (no UX regression)
- ✅ Filtering works correctly for all data types (string, number, date, boolean)
- ✅ Search works across specified fields
- ✅ Sorting works for all columns
- ✅ Pagination shows correct totals

### Quality

- ✅ 100% of E2E tests pass
- ✅ 100% of unit tests pass
- ✅ Zero TypeScript errors
- ✅ Zero security vulnerabilities (SQL injection, etc.)

---

## 9. Dependencies

### Upstream

- ✅ Phase 1 complete and deployed
- ✅ Backend uses SQLAlchemy (supports dynamic queries)
- ✅ Frontend uses TanStack Query (supports query params)

### Downstream

- Phase 3 (Advanced Features) depends on Phase 2 completion
- Future: Saved filters, export, global search

### External

- Python RSQL parser library (or custom implementation)
- Database indexes on frequently filtered columns

---

## 10. Open Questions

1. **RSQL Library:** Should we use an existing Python RSQL parser or build our own?

   - **Recommendation:** Start with custom parser for common operators (`==`, `!=`, `>`, `<`, `=in=`); extend as needed.

2. **Search Strategy:** Full-text search (PostgreSQL `tsvector`) or simple `ILIKE`?

   - **Recommendation:** Start with `ILIKE` for simplicity; migrate to full-text if performance issues arise.

3. **Filter Validation:** Should we validate filters at the endpoint level or service level?

   - **Recommendation:** Endpoint level (FastAPI dependency) for early rejection; service level for business logic.

4. **Backward Compatibility:** Should we support both client-side and server-side modes?

   - **Recommendation:** Yes, via `mode` prop on `StandardTable` (Phase 3 concept from original analysis).
   - Phase 2: Migrate Projects, WBEs, Cost Elements to server-side.
   - Keep Users, Departments client-side (small datasets, optimal performance).

5. **Feature Flag:** Should we use a feature flag to toggle server-side filtering?
   - **Recommendation:** Yes, for gradual rollout and easy rollback.

---

## 11. Next Steps

1. ✅ Review and approve this analysis
2. ⏭️ Create detailed PLAN document (Phase 2)
3. ⏭️ Spike: Implement RSQL parser prototype
4. ⏭️ Spike: Update one endpoint (Projects) as proof-of-concept
5. ⏭️ Validate performance with realistic dataset
6. ⏭️ Proceed to full implementation if spike is successful

---

**Analysis Status:** 📋 Ready for Review  
**Last Updated:** 2026-01-08
