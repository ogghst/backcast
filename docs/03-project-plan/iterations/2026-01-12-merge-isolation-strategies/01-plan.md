# PLAN Phase: Branch Mode Support for List Operations

**Date Created:** 2026-01-12
**Status:** Draft
**Related:** [Analysis](00-analysis.md) | [Time Travel & Branching Architecture](../../02-architecture/cross-cutting/temporal-query-reference.md)

---

## Phase 1: Context Analysis

### Documentation Review

**Product Scope & User Stories:**

- **Vision:** Git-style versioning with branch isolation for change orders
- **Branching Requirements:**
  - Merge Strategy: "Overwrites (source replaces target)"
  - Change Management User Story 3.8: "Toggling View Modes (Isolated vs. Merged)"
    - **Merged View (Default):** Composite state (Source + Change Branch)
    - **Isolated View:** ONLY entities modified/created in the branch
- **ADR-005:** Bitemporal versioning with `BranchMode` enum (STRICT/MERGE)

**Architecture Context:**

- **EVCS Core:** Single-table bitemporal pattern with `TSTZRANGE`
- **Service Layer:**
  - `TemporalService[T]` - Base service for versioned entities
  - `BranchableService[T]` - Extends TemporalService for branchable entities
  - `WBEService`, `ProjectService`, etc. - Entity-specific services
- **Current Implementation:**
  - `BranchableService.get_as_of()` supports MERGE mode (lines 226-289)
  - `WBEService.get_wbes()` only supports STRICT mode (line 199: `WHERE branch = :branch`)

**Coding Standards:**

- Strict typing (100% type annotation coverage)
- MyPy strict mode compliance
- Pydantic V2 with `strict=True` for schemas
- Service layer pattern: Services orchestrate, Commands execute
- 80%+ test coverage requirement

### Codebase Analysis

**Backend Existing Patterns:**

1. **MERGE Mode for Single Entities** (`BranchableService.get_as_of()`):

   ```python
   # Uses CASE to prioritize requested branch over main
   .order_by(
       case((entity.branch == branch, 0), else_=1),
       entity.valid_time.desc(),
   )
   ```

2. **STRICT Mode for Lists** (`WBEService.get_wbes()`):

   ```python
   stmt = self._get_base_stmt(as_of=as_of).where(WBE.branch == branch)
   ```

3. **Bitemporal Filtering** (`_apply_bitemporal_filter()`):
   - Standardized filter for `valid_time`, `transaction_time`, `deleted_at`
   - Used for time-travel queries with `as_of` parameter

**Frontend Existing Patterns:**

1. **Time Machine Store** (`useTimeMachineStore.ts`):
   - Zustand store with immer middleware
   - Persists `selectedTime` and `selectedBranch` per project
   - Provides `useTimeMachineParams()` hook for API integration

2. **Branch Selector Component** (`ProjectBranchSelector.tsx`):
   - Ant Design Select dropdown
   - Shows status badges for change order branches
   - Compact mode for header display

**Dependencies & Integration Points:**

**Backend:**

- `app/core/versioning/enums.py` - `BranchMode` enum (STRICT, MERGE)
- `app/core/branching/service.py` - `BranchableService` base class
- `app/services/project.py` - `ProjectService`
- `app/services/wbe.py` - `WBEService`
- `app/api/routes/projects.py` - Projects API endpoints
- `app/api/routes/wbes.py` - WBEs API endpoints

**Frontend:**

- `frontend/src/stores/useTimeMachineStore.ts` - Time machine state
- `frontend/src/components/time-machine/ProjectBranchSelector.tsx` - Branch selector
- `frontend/src/contexts/TimeMachineContext.tsx` - Time machine context
- `frontend/src/features/projects/api/useProjects.ts` - Projects API hooks
- `frontend/src/features/wbes/api/useWbes.ts` - WBEs API hooks

---

## Phase 2: Problem Definition

### 1. Problem Statement

The system currently supports MERGE mode for single-entity queries (`get_as_of()`), but list operations (`get_projects()`, `get_wbes()`) only implement STRICT isolation. This creates:

- **Inconsistent UX:** Individual entity lookups show merged state, but lists show isolated changes only
- **Incomplete Feature:** User Story 3.8 requires "Merged View (Default)" for lists
- **Poor Change Order Workflow:** Users cannot see the composite project state when working in a branch

**Impact:** Users working in change order branches cannot properly visualize the "Future State" of their project without manually merging data client-side, defeating the purpose of branch isolation for impact analysis.

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- All list endpoints support `mode` query parameter (`merged` | `isolated`)
- Default behavior is `merged` (as specified in user stories)
- DISTINCT ON query correctly prioritizes branch over main for each `root_id`
- Pagination works correctly (count and limit/offset applied to merged result)
- All existing filters (search, project_id, parent_wbe_id) continue to work

**Technical Criteria:**

- Query performance <200ms for typical datasets (<10K rows)
- No N+1 query problems
- MyPy strict mode: zero errors
- Ruff linting: zero errors
- Test coverage: 80%+ for new code

**Business Criteria:**

- Users can toggle between Isolated and Merged views
- Change order impact analysis shows composite state
- API backward compatibility (default to merged as per user stories)

### 3. Scope Definition

**In Scope:**

**Backend:**

- Implement `_apply_branch_mode_filter()` method in `BranchableService`
- Update list methods in `WBEService`, `ProjectService`, `CostElementService`
- Add `mode` query parameter to list API routes
- Write unit tests for branch mode filtering
- Write integration tests for API endpoints
- Update temporal-query-reference.md documentation

**Frontend:**

- Extend `useTimeMachineStore` with `viewMode` state
- Create `ViewModeSelector` component (button group toggle)
- Update `ProjectBranchSelector` to include view mode selector
- Update `TimeMachineContext` to inject `mode` parameter
- Update API hooks (`useProjects`, `useWbes`) to pass `mode` parameter

**Out of Scope:**

- Change Order entity operations (already exist)
- Single-entity `get_as_of()` methods (already support MERGE)
- Performance optimization beyond DISTINCT ON approach
- Complex merge conflicts (assumes branch isolation)
- E2E tests for view mode toggle (deferred)

**Assumptions:**

- PostgreSQL DISTINCT ON performance is acceptable for dataset sizes
- Default `mode=merged` is acceptable (no backward compatibility concerns in development)
- Branch precedence: Current branch > Main branch
- Deleted entities in branch should NOT fall back to main
- View mode selector only visible when branch != "main"

---

## Phase 3: Implementation Options

| Aspect | Option A (Recommended) | Option B | Option C |
|--------|------------------------|----------|----------|
| **Approach Summary** | Database-level DISTINCT ON with branch precedence | Application-level merge (two-step fetch) | Fallback-only (no list merging) |
| **Design Patterns** | Single query with DISTINCT ON (root_id), ORDER BY branch precedence | Fetch branch + main, merge in Python | No merge for lists |
| **Pros** | Single query, proper pagination, database optimization | Simpler initial SQL | Minimal backend changes |
| **Cons** | Slightly complex DISTINCT ON syntax | Breaks pagination, poor scalability | UX inconsistency, bad client performance |
| **Test Strategy Impact** | Test branch precedence, edge cases (deleted entities) | Test merge logic, pagination breaks | Minimal testing |
| **Risk Level** | Low | High | High |
| **Estimated Complexity** | Moderate | Simple (code) / Complex (fixing pagination) | Low |

### Recommendation

**Option A (Database-Level Composition with DISTINCT ON)**

**Justification:**

1. **Aligns with ADR-005:** Leverages PostgreSQL native capabilities
2. **Scalability:** Single query with proper database-side pagination
3. **Architecture:** Centralizes logic in `BranchableService`, consistent with existing patterns
4. **Performance:** Delegates heavy lifting to database engine
5. **User Story Compliance:** Directly satisfies "Merged View (Default)" requirement

> [!IMPORTANT] > **Human Decision Point**: Option A (Database-level DISTINCT ON) has been approved. Proceeding with implementation.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests (backend/tests/unit/services/)
│   ├── test_branchable_service_branch_mode.py
│   │   ├── test_distinct_on_prioritizes_branch_over_main
│   │   ├── test_isolated_mode_returns_only_branch_entities
│   │   ├── test_merged_mode_includes_unmodified_main_entities
│   │   └── test_deleted_entities_not_merged_from_main
│   └── test_wbe_service_branch_mode.py
│       ├── test_get_wbes_with_mode_parameter
│       └── test_filters_work_with_branch_mode
├── Integration Tests (backend/tests/api/)
│   ├── test_projects_api_branch_mode.py
│   └── test_wbes_api_branch_mode.py
└── End-to-End Tests (deferred to frontend iteration)
```

**First 3 Test Cases (Ordered Simplest → Most Complex):**

1. **test_isolated_mode_returns_only_branch_entities:**
   - Create 5 WBEs on main
   - Create 2 WBEs on BR-123 branch
   - Query with `branch="BR-123", mode="isolated"`
   - Assert: 2 results, all from BR-123

2. **test_distinct_on_prioritizes_branch_over_main:**
   - Create WBE with code="W001" on main
   - Create WBE with same code="W001" (same root_id) on BR-123 branch
   - Query with `branch="BR-123", mode="merged"`
   - Assert: 1 result, branch="BR-123"

3. **test_merged_mode_includes_unmodified_main_entities:**
   - Create 5 WBEs on main
   - Create 2 WBEs on BR-123 (different root_ids)
   - Query with `branch="BR-123", mode="merged"`
   - Assert: 5 results (2 from BR-123 + 3 from main)

### Implementation Strategy

**High-Level Approach:**

1. Add `_apply_branch_mode_filter()` method to `BranchableService`
2. Update list methods to accept `branch_mode` parameter
3. Add `mode` query parameter to API routes
4. Extend frontend store and components for view mode selection
5. Write tests following TDD pattern

**Component Breakdown:**

| Component | Changes |
|-----------|---------|
| **Backend:** | |
| `BranchableService` | Add `_apply_branch_mode_filter(stmt, branch, mode, as_of)` |
| `WBEService.get_wbes()` | Add `branch_mode` parameter, pass to filter method |
| `ProjectService.get_projects()` | Add `branch_mode` parameter, pass to filter method |
| `CostElementService.get_cost_elements()` | Add `branch_mode` parameter, pass to filter method |
| API Routes (`wbes.py`, `projects.py`) | Add `mode` query parameter, map to `BranchMode` enum |
| **Frontend:** | |
| `useTimeMachineStore.ts` | Add `viewMode` to `ProjectTimeMachineSettings`, add `selectViewMode()` action |
| `ViewModeSelector.tsx` | NEW: Button group toggle (Merged/Isolated) |
| `ProjectBranchSelector.tsx` | Add ViewModeSelector alongside BranchSelector |
| `TimeMachineContext.tsx` | Add `mode` to `useTimeMachineParams()` return value |
| `useProjects.ts`, `useWbes.ts` | Add `mode` to query params and query keys |

**SQL Pattern for DISTINCT ON:**

```sql
SELECT DISTINCT ON (wbe_id) *
FROM wbe
WHERE branch IN ('BR-123', 'main')
  -- bitemporal filters
ORDER BY wbe_id, (branch = 'BR-123') DESC, valid_time DESC
```

**Frontend Component Hierarchy:**

```text
ProjectBranchSelector
├── BranchSelector (existing)
│   └── Select dropdown with branch options
└── ViewModeSelector (NEW)
    └── Radio.Group (Merged | Isolated)
        ├── Only shown when branch !== "main"
        └── Default: "merged"
```

**Key Implementation Details:**

1. **Branch Precedence:** Use `CASE (branch = :current_branch) DESC` to prioritize
2. **Isolated Mode:** Use `WHERE branch = :branch` (current behavior)
3. **Deleted Entities:** Check `deleted_at` before falling back to main
4. **Time Travel:** Apply bitemporal filters before DISTINCT ON
5. **Frontend Persistence:** `viewMode` stored in localStorage per project
6. **Conditional Visibility:** View mode selector hidden on `main` branch

---

## Phase 5: Risk Assessment

### Risks and Mitigations

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Technical** | DISTINCT ON performance with large datasets | Medium | Medium | Use proper indexes on (root_id, branch); add EXPLAIN ANALYZE to tests |
| **Technical** | Complex interaction with bitemporal filters | Low | High | Apply bitemporal filters in subquery, DISTINCT ON in outer query |
| **Integration** | Breaking existing API consumers | Low | Medium | Development environment only; document breaking change |
| **Testing** | Edge cases with deleted entities | Medium | Medium | Explicit test for deleted entity merge behavior |
| **Testing** | Pagination edge cases (filter after DISTINCT) | Low | Medium | Write pagination-specific tests with small page sizes |

---

## Phase 6: Effort Estimation

### Time Breakdown

**Backend:**

| Task | Time |
|------|------|
| `BranchableService._apply_branch_mode_filter()` | 30 min |
| Update service list methods | 30 min |
| Update API routes | 30 min |
| Unit tests | 45 min |
| Integration tests | 45 min |
| **Backend Subtotal** | **~3 hours** |

**Frontend:**

| Task | Time |
|------|------|
| Extend `useTimeMachineStore` with `viewMode` | 15 min |
| Create `ViewModeSelector` component | 30 min |
| Update `ProjectBranchSelector` | 15 min |
| Update `TimeMachineContext` | 15 min |
| Update API hooks (`useProjects`, `useWbes`) | 15 min |
| Component testing (Vitest) | 30 min |
| **Frontend Subtotal** | **~2 hours** |

**Documentation:**

| Task | Time |
|------|------|
| Update `temporal-query-reference.md` with branch mode behavior | 15 min |
| Update API documentation | 15 min |
| **Documentation Subtotal** | **~30 min** |

**Total Estimated Effort:** ~5.5 hours

### Prerequisites

**Backend:**

- PostgreSQL 15+ with DISTINCT ON support
- Existing `BranchMode` enum in `app/core/versioning/enums.py`
- Existing test infrastructure (`pytest-asyncio`, fixtures)

**Frontend:**

- Existing `useTimeMachineStore` Zustand store
- Existing `ProjectBranchSelector` component
- Ant Design components (Radio.Group, Space)

---

## Related Documentation

- [ADR-005: Bitemporal Versioning](../../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [Time Travel & Branching Architecture](../../02-architecture/cross-cutting/temporal-query-reference.md)
- [Change Management User Stories](../../01-product-scope/change-management-user-stories.md)
- [Coding Standards](../../02-architecture/coding-standards.md)
