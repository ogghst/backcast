# Implementation Plan: Branch Routes and Selector

## Phase 1: Context Analysis

**Documentation Review:**

- **Architecture**: The EVCS Core uses a single-table bitemporal pattern where `branch` is a string column. Branches are effectively defined by `main` + active `ChangeOrders`.
- **Coding Standards**: Must strictly adhere to type safety (Pydantic, MyPy), async/await patterns, and split between Service/Repository layers. Frontend must use React functional components and hooks.

**Codebase Analysis:**

- **Backend**: `ChangeOrderService` already has logic to find Change Orders. We need to expose this as a list of "branches".
- **API**: `projects.py` is the logical home for `GET /projects/{id}/branches`, as the concept of a branch list is scoped to a project in this context.
- **Frontend**: `BranchSelector.tsx` exists but is disconnected. We need a `useProjectBranches` hook.

## Phase 2: Problem Definition

**Problem Statement:**
Users cannot currently see or select branches in the UI. The application lacks a dedicated API to retrieve the list of available branches for a project, and the frontend component is not yet integrated with the backend.

**Success Criteria:**

1.  **Backend**: `GET /api/v1/projects/{id}/branches` returns a list containing 'main' and all Change Order branches for that project.
2.  **Frontend**: The Branch Selector in the header populates with real data when a project is active.
3.  **Frontend**: Selecting a branch updates the global application state (or URL) to reflect the chosen branch. (Note: For this iteration, we focus on _selection_ and _listing_. The actual _filtering_ of data by branch is already handled by individual queries if they respect the branch param).

## Phase 3: Implementation Options

**Selected Approach: Option 1 (Dedicated Endpoint)**
As confirmed by the user, we will implement a dedicated backend endpoint.

**Design Patterns:**

- **Backend**: Service Layer extension (`ProjectService` calls `ChangeOrderService` or repository directly).
- **Frontend**: Container/Presenter pattern (`ProjectBranchSelector` container, `BranchSelector` presenter). Custom Hook (`useProjectBranches`).

## Phase 4: Technical Design

### TDD Test Blueprint

**Backend Unit Tests (`backend/tests/unit/services/test_project_service_branches.py`)**

1.  `test_get_branches_only_main`: Create project, no COs. Expect ['main'].
2.  `test_get_branches_with_active_cos`: Create project, 1 active CO. Expect ['main', 'co-CO-123'].
3.  `test_get_branches_filters_status`: Verify status mapping (Draft/Submitted -> Active).
4.  `test_get_branches_project_not_found`: Expect error.

**Backend API Tests (`backend/tests/api/routes/test_projects.py`)**

1.  `test_read_project_branches_authenticated`: Happy path.
2.  `test_read_project_branches_unauthorized`: 401/403.

**Frontend Tests (`frontend/src/hooks/useProjectBranches.test.ts`)**

1.  `it_should_fetch_branches_for_project`: Mock API response, verify hook state.
2.  `it_should_handle_errors`: Mock API error.

### Implementation Strategy

1.  **Backend Models**: Define `BranchInfo` Pydantic model.
2.  **Backend Service**: Implement `ProjectService.get_project_branches(project_id)`.
    - Need to import `ChangeOrderService` or access `ChangeOrder` model directly. Better to inject `ChangeOrderService` to avoid circular deps, or use a `BranchService` if we want to be purist.
    - _Decision_: `ProjectService` will query `ChangeOrder` table directly for read-only projection to avoid complex service dependencies, or we create a helper.
    - _Actually_, `ChangeOrderService` owns generic CO retrieval. `ProjectService` could depend on `ChangeOrderRepo`.
    - _Simpler_: Add `get_branches` to `ProjectService`. Query `ChangeOrder` model where `project_id=X`.
3.  **Backend API**: Add route to `app/api/routes/projects.py`.
4.  **Frontend API**: Update `frontend/src/api/projectService.ts`.
5.  **Frontend Hook**: Create `frontend/src/hooks/useProjectBranches.ts`.
6.  **Frontend UI**: Create `ProjectBranchSelector.tsx` and integrate into `AppLayout`.

## Phase 5: Risk Assessment

- **Risk**: Circular imports in backend services.
  - **Mitigation**: Use local imports inside methods if needed, or query models directly for simple aggregation queries.
- **Risk**: Frontend header context is tricky (global layout vs specific page).
  - **Mitigation**: `ProjectBranchSelector` will check URL parameters (React Router `useParams`) to see if `projectId` exists. If not, render nothing or disabled state.

## Phase 6: Effort Estimation

- **Backend**: 0.5 days
- **Frontend**: 0.5 days
- **Total**: 1 day
