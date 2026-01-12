# Request Analysis: Implement Branching and Branch Selector

## Clarified Requirements

The user wants to operationalize the branching strategy defined in the Product Scope. Specifically:

1.  **Branch Attributes**: Ensure branches have attributes as per functional requirements (implicitly handled via Change Order metadata).
2.  **Branch Listing**: The frontend `BranchSelector` must dynamically query and list active branches for the _current project_.
3.  **Active Branches**: Defined as the "main" branch plus any active Change Order branches (`co-{code}`) derived from Change Orders that are not yet merged/closed (or perhaps all, depending on history requirements).

**Assumptions**:

- Branches are strictly tied to Projects (via Change Orders).
- The `BranchSelector` in the header needs to be context-aware (know the current project) or globally accessible (which raises scaling/UX questions). Given the request says "for the project", we assume a project context.
- "Active branches" implies branches that are candidates for viewing/editing.

## Context Discovery Findings

**Product Scope:**

- `functional-requirements.md`: "Dropdown lists all branches (main + active change order branches)".
- `branching-requirements.md`: Branch naming `co-{change_order_id}` (or code). Operation `GET /api/v1/projects/{project_id}?branch=...`.
- `epics.md`: Epic 6 (Branching & Change Order Management) covers this.

**Architecture Context:**

- **EVCS Core**: Uses a Single-Table Bitemporal Pattern. `branch` is a column (String).
- **No Physical Branch Table**: Branches are virtual, defined by the existence of a Change Order.
- **ChangeOrder Entity**: Contains `status` (Draft, Submitted, etc.) and `code`.
- **API**: `ChangeOrderPublic` schema exists.

**Codebase Analysis:**

- **Backend**:
  - `ChangeOrder` model (`backend/app/models/domain/change_order.py`) has `code` and `project_id`.
  - Routes (`backend/app/api/routes/change_orders.py`) allow listing COs for a project.
  - No dedicated `branches` endpoint exists.
- **Frontend**:
  - `BranchSelector.tsx` exists but is a dumb component (UI only).
  - It needs a data source.
  - Currently, no "BranchService" on frontend or "useBranches" hook.

---

## Solution Options

### Option 1: Dedicated Project-Scoped Branches Endpoint (Recommended)

Create a specific endpoint that aggregates `main` and all valid change order branches for a given project.

**Architecture & Design:**

- **Backend API**: `GET /api/v1/projects/{project_id}/branches`
- **Response**: List of objects `{ name: string, type: 'main' | 'change_order', change_order_id?: UUID, status?: string }`.
- **Logic**:
  1. Always return 'main'.
  2. Query `ChangeOrders` where `project_id` matches and `status` is active (Draft, Submitted, Under Review, Approved).
  3. Map COs to branch names `co-{code}`.

**UX Design:**

- The `BranchSelector` becomes a "smart" container or is wrapped by one (`ProjectBranchSelector`).
- It watches the URL for `projectId`.
- If `projectId` is present, it fetches branches.
- If not (e.g., Home page), it disables or shows only "main".

**Implementation:**

- Create `backend/app/api/routes/projects.py` endpoint `get_project_branches`.
- Frontend: Create `useProjectBranches(projectId)` hook.
- Frontend: Wrap `BranchSelector` in `Header` to be context-aware.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Clean API contract; Backend owns the logic of what constitutes a "branch"; optimized query. |
| Cons | Requires new endpoint; Frontend header needs access to project context (might need global state or router hooks). |
| Complexity | Low |
| Maintainability | High |
| Performance | Good (Single query to CO table) |

### Option 2: Client-Side Aggregation

Frontend queries Change Orders and constructs the branch list locally.

**Architecture & Design:**

- Frontend uses existing `GET /api/v1/change-orders?project_id={id}`.
- Logic in Frontend to manually append 'main' and format `co-{code}`.

**Implementation:**

- Use `useChangeOrders` hook in the header.
- Filter/Map results to `BranchOption[]`.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | No backend changes needed immediately. |
| Cons | Leaks business logic (naming convention `co-{code}`) to frontend; Over-fetches data (full CO details) just for a dropdown; "main" logic duplication. |
| Complexity | Low |
| Maintainability | Fair |
| Performance | Fair (Fetching full CO objects) |

### Option 3: Global Branches Endpoint

List all branches for all projects.

**Architecture & Design:**

- `GET /api/v1/branches` covers everything.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Simple usage if context is missing. |
| Cons | Does not scale; Security risk (listing all projects' COs); confusing UX (which 'main'?). |
| Complexity | Low |
| Maintainability | Poor |
| Performance | Poor |

---

## Comparison Summary

| Criteria               | Option 1 (Dedicated Endpoint)   | Option 2 (Client-Side) | Option 3 (Global) |
| :--------------------- | :------------------------------ | :--------------------- | :---------------- |
| **Development Effort** | Medium (New API + Hook)         | Low (Frontend only)    | Medium            |
| **UX Quality**         | High (Context sensitive)        | High                   | Low               |
| **Flexibility**        | High (Backend can change logic) | Low                    | Low               |
| **Best For**           | robust Production apps          | MVP / Prototypes       | Internal tools    |

## Recommendation

**I recommend Option 1** because it encapsulates the "definition of a branch" within the domain (backend). If the branch naming convention changes or if "archived" logic changes, the frontend remains untouched. It also creates a clear seam for permission checks (user can see branch X?).

## Questions for Decision

1.  Should the `BranchSelector` be visible/active when _not_ in a specific project context (e.g., Dashboard)? (Assumption: No, or just 'main').
2.  Should we include "Implemented" or "Closed" Change Orders in the branch list (read-only historical view)? (Assumption: Yes, for time-travel/audit, maybe separated visually).
