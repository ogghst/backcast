# Request Analysis: Merge & Isolation Strategies for Entity Retrieval

## Clarified Requirements

The goal is to ensure that API endpoints for retrieving entities (Projects, WBEs, Cost Elements) correctly implement **Merge** (Composite) and **Isolation** strategies as defined in the Branching Requirements and Change Management User Stories.

**Core Requirements:**

1. **Isolation Strategy**: When a user selects a specific branch (e.g., `BR-123`), they should be able to view _only_ the changes made in that branch ("Isolated View").
2. **Merge Strategy**: Users working in a branch often need to see the "Composite State" of the project: the baseline (`main` branch) overlayed with their branch changes ("Merged View").
3. **List & Single Item Support**: This logic must apply to both single entity retrieval (`get_by_id`) and list/search operations (`get_all`).
4. **API Exposure**: The API must allow clients to specify which strategy to use (defaulting to Merged View usually, or Isolated View for diffing).

## Context Discovery Findings

### Product Scope

- **Vision**: "Enable change order processing with impact analysis" and "Git-style versioning".
- **Branching Requirements**:
  - **Merge Strategy**: "Overwrites (source replaces target)".
  - **Branch Isolation Rules**: "Default to user's selected branch... Join with user preferences".
- **Change Management User Stories**:
  - **Story 3.8 (Toggling View Modes)**: Explicitly defines:
    - **Merged View (Default)**: Composite state (Source + Change Branch).
    - **Isolated View**: ONLY entities modified/created in the branch.

### Architecture Context

- **Bounded Context**: `evcs-core` (Entity Version Control System).
- **Pattern**: Single-Table Bitemporal Pattern (`entity_versions` table).
- **Service Layer**: `TemporalService` as base class, with `ProjectService`/`WBEService` extending it.

### Codebase Analysis

**Backend (Current State):**

1. **`TemporalService.get_as_of`** (service.py:135-191):
    - Fully supports `branch_mode` (`Strict` vs `Merge`).
    - Defaults to `BranchMode.STRICT` if not specified.
    - MERGE implementation: First tries requested branch, falls back to `main` if not found.
    - Correctly handles branch deletions via `_is_deleted_on_branch()`.
    - _Gap_: This capability is only exposed via `get_as_of()` for single entities, not for list operations.
2. **`ProjectService` / `WBEService` (List Methods)**:
    - **Strict Isolation Only**: `get_projects` and `get_wbes` query `WHERE branch = :branch`.
    - **Missing Logic**: No implementation for "Merged View" in list/search queries. If users query `branch=BR-1`, they receive _only_ items explicitly in `BR-1`, missing all unchanged background items from `main`.
3. **API Routes**:
    - Endpoints (e.g., `/wbes`) accept `branch` query param.
    - **No Mode Selection**: No parameter to toggle between "Isolated" and "Merged" views.
    - **Default Behavior**: Implicitly "Isolated" (Strict) due to underlying service implementation.

---

## Solution Options

### Option 1: Database-Level Composition (DISTINCT ON Strategy)

Use PostgreSQL's `DISTINCT ON` feature to efficiently fetch the latest version of each entity from a set of branches.

**Architecture & Design:**

- Modify `TemporalService.get_all` (and subclass list methods) to accept `branch_mode`.
- **Merged View Logic**:
  - Query entities where `branch IN ('main', :current_branch)`.
  - Use `DISTINCT ON (root_id) ORDER BY root_id, (branch=:current_branch) DESC, valid_time DESC`.
  - This effectively selects the version from the Current Branch if it exists; otherwise falls back to Main.
- **Isolated View Logic**: Keep existing `valid_time` and `branch = :branch` filtering.

**API Changes:**

- Add `mode: "merged" | "isolated" = "merged"` query parameter to list/get endpoints.

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | **Performance**: Single query, efficient pagination. <br> **Correctness**: Handles sorting and filtering correctly across the composite set. |
| **Cons** | **Complexity**: Slightly more complex SQL generation (filtering must happen in a subquery or wrapper to filter _after_ the distinct/precedence logic if filtering on mutable fields). |
| **Complexity** | Medium |
| **Maintainability** | High (Centralized in `TemporalService`) |
| **Performance** | High (Leverages DB optimization) |

### Option 2: Application-Level Merge (Two-Step Fetch)

Fetch data from both branches separately and merge in Python.

**Architecture & Design:**

- Step 1: Fetch all matching items from `current_branch`.
- Step 2: Fetch all matching items from `main` (excluding IDs found in Step 1).
- Step 3: Combine and Sort in memory.

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | **Simplicity**: Easier to write initial SQL queries. |
| **Cons** | **Pagination**: Breaks database-side pagination (cannot limit/offset correctly without fetching everything). <br> **Performance**: Transfers unnecessary data; memory intensive for large datasets. |
| **Complexity** | Low (code-wise) -> High (trying to fix pagination) |
| **Maintainability** | Poor |
| **Performance** | Poor (Unscalable) |

### Option 3: Fallback-Only (Lazy Loading)

Only implement fallback for `get_by_id`. Leave Lists as "Isolated Only".

**Architecture & Design:**

- Clients must manually fetch `main` list and `branch` list and merge them UI-side.

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | Minimal backend changes. |
| **Cons** | **UX**: Bad client performance; "flickering" UI; complex frontend logic. <br> **Inconsistency**: `get_by_id` behaves differently from `get_all`. |
| **Complexity** | Low (Backend) / High (Frontend) |
| **Maintainability** | Poor (Leaky abstraction) |

---

## Comparison Summary

| Criteria           | Option 1 (DB Composition) | Option 2 (App Merge) | Option 3 (Fallback Only) |
| :----------------- | :------------------------ | :------------------- | :----------------------- |
| **Scalability**    | High                      | Low                  | Low                      |
| **UX Consistency** | High                      | Medium               | Low                      |
| **Dev Effort**     | Medium                    | Low                  | Low (Backend)            |
| **Best For**       | Production Systems        | Prototypes           | MVP                      |

## Recommendation

**I recommend Option 1 (Database-Level Composition) because:**

1. **Requirement Compliance**: It directly satisfies the "Merged View" requirement for massive datasets without breaking pagination.
2. **Performance**: It delegates the heavy lifting to the database engine.
3. **Architecture**: It unifies the logic in `TemporalService`, making specific service implementations (WBE, CostElement) cleaner.

**Plan:**

1. Update `BranchableService` to implement `_apply_branch_mode_filter` using `DISTINCT ON` or equivalent window functions.
2. Update `WBEService`, `ProjectService`, etc., to pass `branch_mode` down to the query builder.
3. Update API Routes to accept `mode` (Merged/Isolated) query parameter.
4. Add frontend View Mode selector to Time Machine component.

---

## Frontend Implementation Strategy

### Context: Time Machine Component

The frontend has a `ProjectBranchSelector` component ([`frontend/src/components/time-machine/ProjectBranchSelector.tsx`](../../../../../frontend/src/components/time-machine/ProjectBranchSelector.tsx)) that allows users to switch between branches. The component uses:

- `useTimeMachineStore` from `frontend/src/stores/useTimeMachineStore.ts` - Zustand store for time/branch state
- `BranchSelector` component - Dropdown with branch options
- `useTimeMachineParams` hook from `TimeMachineContext` - Injects `asOf` and `branch` into API calls

### Required Changes

#### 1. Extend `useTimeMachineStore` with View Mode State

**File:** `frontend/src/stores/useTimeMachineStore.ts`

Add `viewMode` to the store interface:

```typescript
interface ProjectTimeMachineSettings {
  selectedTime: string | null;
  selectedBranch: string;
  viewMode: "merged" | "isolated";  // NEW
}

interface TimeMachineState {
  // ... existing ...

  // Actions
  selectBranch: (branch: string) => void;
  selectViewMode: (mode: "merged" | "isolated") => void;  // NEW
}
```

**Default:** `"merged"` (per User Story 3.8 requirements)

#### 2. Create View Mode Selector Component

**File:** `frontend/src/components/time-machine/ViewModeSelector.tsx`

New component with button group toggle:

```typescript
interface ViewModeSelectorProps {
  value: "merged" | "isolated";
  onChange: (mode: "merged" | "isolated") => void;
  disabled?: boolean;
  compact?: boolean;
}

// Two buttons:
// - "Merged" (default) - Shows composite icon (layers)
// - "Isolated" - Shows isolation icon (filter/branch)
```

**Visual Design:**

- Use Ant Design `<Radio.Group>` with `buttonStyle="solid"`
- Icons: `AppstoreOutlined` (Merged), `FilterOutlined` (Isolated)
- Only visible when selected branch != "main"
- Disabled on main branch (no meaningful view mode selection)

#### 3. Update `ProjectBranchSelector` to Include View Mode

**File:** `frontend/src/components/time-machine/ProjectBranchSelector.tsx`

Add ViewModeSelector alongside BranchSelector:

```typescript
export const ProjectBranchSelector: React.FC<ProjectBranchSelectorProps> = ({
  projectId,
}) => {
  const { data: branches = [], isLoading } = useProjectBranches(projectId);
  const selectedBranch = useTimeMachineStore((state) => state.getSelectedBranch());
  const viewMode = useTimeMachineStore((state) => state.getViewMode()); // NEW
  const selectBranch = useTimeMachineStore((state) => state.selectBranch);
  const selectViewMode = useTimeMachineStore((state) => state.selectViewMode); // NEW

  const isMainBranch = selectedBranch === "main";
  const showViewMode = !isMainBranch;

  return (
    <Space size="small">
      <BranchSelector value={selectedBranch} branches={options} onChange={selectBranch} compact />
      {showViewMode && (
        <ViewModeSelector
          value={viewMode}
          onChange={selectViewMode}
          compact
        />
      )}
    </Space>
  );
};
```

#### 4. Update `TimeMachineContext` to Inject `mode` Parameter

**File:** `frontend/src/contexts/TimeMachineContext.tsx`

Add `mode` to the params returned by `useTimeMachineParams`:

```typescript
export const useTimeMachineParams = (): {
  asOf: string | undefined;
  branch: string;
  mode: "merged" | "isolated";  // NEW
} => {
  // ... get from store ...
};
```

#### 5. Update API Hooks to Pass `mode` Parameter

**File:** `frontend/src/features/projects/api/useProjects.ts`

Update `useProjects` hook to include `mode`:

```typescript
export const useProjects = (params?: ProjectListParams) => {
  const { asOf, branch, mode } = useTimeMachineParams();  // Add mode

  return useQuery<PaginatedResponse<ProjectRead>>({
    queryKey: ["projects", params, { asOf, branch, mode }],
    queryFn: async () => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/projects",
        query: {
          ...serverParams,
          as_of: asOf || undefined,
          branch: branch,
          mode: mode,  // NEW
        },
      }) as Promise<PaginatedResponse<ProjectRead>>;
    },
  });
};
```

**Apply same pattern to:**

- `frontend/src/features/wbes/api/useWbes.ts`
- Any other list hooks

### Component Hierarchy

```text
ProjectBranchSelector
├── BranchSelector (existing)
│   └── Select dropdown with branch options
└── ViewModeSelector (NEW)
    └── Radio.Group (Merged | Isolated)
        ├── Only shown when branch !== "main"
        └── Default: "merged"
```

### Key Implementation Details

1. **Persistence:** `viewMode` stored in `projectSettings` (localStorage via zustand persist)
2. **Default:** `"merged"` per User Story 3.8
3. **Conditional Visibility:** Hidden on `main` branch (no meaningful view mode)
4. **API Integration:** Passed as `mode` query parameter to all list endpoints
5. **React Query Cache:** Different `mode` values create separate query keys for proper cache invalidation

### UX Guidelines (from User Story 3.8)

**Merged View (Default):**

- Shows Composite State: base entities + branch changes
- Represents "Future State" if branch were merged
- Unchanged entities appear normally
- Modified entities show their new state

**Isolated View:**

- Shows ONLY entities modified/created in branch
- Hides "inherited" unchanged entities
- Clean workspace to verify exact scope of Change Order

## Questions for Decision

1. Should the default API behavior changed to `Merged` (as implied by user stories) or stay `Isolated` (current behavior) to avoid breaking existing clients (if any)?
    _Assumption: Since we are in development, we can change the default to `Merged` if it improves UX._

---

## Verification Status

**Date Validated:** 2026-01-12

**Validation Method:** Codebase exploration using Task agent (thorough search)

**Key File Locations:**

- `backend/app/core/versioning/enums.py` - BranchMode enum definition
- `backend/app/core/versioning/service.py:135-191` - TemporalService.get_as_of() with MERGE support
- `backend/app/services/project.py:88-90` - get_projects() (STRICT only)
- `backend/app/services/wbe.py:199-200` - get_wbes() (STRICT only)
- `backend/app/api/routes/projects.py` - Projects API (no mode parameter)
- `backend/app/api/routes/wbes.py` - WBEs API (no mode parameter)

**Validation Result:** Analysis document is accurate. No corrections needed beyond clarification of get_as_of() implementation status.
