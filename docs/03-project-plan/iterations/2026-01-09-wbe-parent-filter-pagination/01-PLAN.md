# PLAN Phase: WBE Parent Filter Pagination

**Iteration**: `2026-01-09-wbe-parent-filter-pagination`
**Status**: 📝 Draft
**Date**: 2026-01-09

---

## Phase 1: Context Analysis

### Documentation Review

- **Product Scope**: WBE Management requires robust navigation and large-scale support.
- **Architecture**:
  - **API Conventions**: Use standard pagination for unbounded lists.
  - **Coding Standards**: Strict typing, Backend as source of truth.
- **Project Context**: This is a direct follow-up to the client-side pagination implementation to fully support server-side optimization.

### Codebase Analysis

- **Current Backend**: Hybrid logic in `read_wbes`. `get_by_parent` returns list, `get_wbes` returns paginated.
- **Current Frontend**: `UseWBEs` passes `parentWbeId` but currently expects array (though client code was just updated to handle pagination).
- **Patterns**: `Project.py` uses `PaginatedResponse`.

---

## Phase 2: Problem Definition

### 1. Problem Statement

The current WBE API treats `parent_wbe_id` filtering as a hierarchical, unpaginated query. This is risky for large projects where a single WBE might have thousands of children, leading to potential performance issues and difficult frontend rendering.

### 2. Success Criteria

**Functional Criteria:**

- Filtering by `project_id` ONLY returns an unpaginated array (hierarchical mode).
- Filtering by `parent_wbe_id` returns a `PaginatedResponse` (list mode).
- Filtering with NO hierarchical filters returns a `PaginatedResponse`.
- Frontend correctly renders child WBEs with pagination controls.

**Technical Criteria:**

- API response time < 200ms for large child sets (due to pagination).
- Strong typing maintained across backend and frontend.

### 3. Scope Definition

**In Scope:**

- Backend `WBEService` update.
- Backend `API` endpoint update.
- Frontend Client generation.
- Frontend `useWBEs` hook and `WBETable` integration.

**Out of Scope:**

- Changes to `project_id` filtering logic.
- Cost Element pagination (handled in separate iteration).

---

## Phase 3: Implementation Options

### Option A: Conditional Pagination (Selected)

Modify `get_wbes` endpoint to switch return type based on filters.

**Pros:**

- Consistent with existing pattern.
- Minimal code change.
- Reuses existing pagination service logic.

**Cons:**

- endpoint return type depends on input (union return type in Python, though OpenAPI helps distinguish).

### Recommendation

**Option A**. Detailed analysis confirms this is safe and aligns with the codebase standards.

---

## Phase 4: Technical Design

### TDD Test Blueprint

1.  **Backend Unit Tests (`tests/unit/services/test_wbe.py`)**:

    - `test_get_wbes_by_parent_pagination`: Verify `parent_wbe_id` returns paginated structure.
    - `test_get_wbes_project_only_no_pagination`: Verify protocol holds for project-only queries.

2.  **Frontend Integration Tests**:
    - Updates to `wbe_crud.spec.ts` are likely minimal as E2E tests often mock responses or simply verify visibility, but we will ensure the table navigates pages correctly.

### Implementation Strategy

1.  **Backend Service**: Update `WBEService.get_wbes` to accept `parent_wbe_id`.
2.  **Backend API**: Update `read_wbes` to route `parent_wbe_id` queries to `service.get_wbes`.
3.  **Frontend Client**: Regenerate client.
4.  **Frontend Logic**: Update `useWBEs` to pass pagination params.

---

## Phase 5: Risk Assessment

| Risk Type       | Description                                       | Mitigation                                                                      |
| :-------------- | :------------------------------------------------ | :------------------------------------------------------------------------------ |
| **Integration** | Frontend types mismatch after generation          | Regenerate client immediately and fix type errors.                              |
| **UX**          | Users lose "expand all" capability if not careful | Pagination is a standard pattern; "expand all" is less relevant for flat lists. |

---

## Phase 6: Effort Estimation

- **Development**: 1.5 hours
- **Testing**: 0.5 hours
- **Total**: 2 hours
