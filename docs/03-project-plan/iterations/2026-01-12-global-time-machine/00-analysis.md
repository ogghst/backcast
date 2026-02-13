# Request Analysis: Global Time Machine

## Clarified Requirements

The user wants to promote the "Time Machine" functionality from being a project-specific feature to a **global application-level feature**.

- **Scope**: The time travel context (selected timestamp and potentially branch) must be available globally, not just within a Project context.
- **Impact**: It must affect ALL versionable entities (Projects, WBEs, Cost Elements, _Users_, _Departments_, etc.).
- **UI**: The Time Machine control should be accessible from the main application layout, irrespective of the current route.

## Context Discovery Findings

**Product Scope:**

- Relevant User Stories: Time Travel is a core feature for auditing and "what-if" analysis.
- The current implementation focuses on Project-level "Current Knowledge" vs "System Time Travel".

**Architecture Context:**

- **Bounded Contexts**: All contexts dealing with versioned entities (Project Management, User Management, etc.).
- **Existing Patterns**:
  - `TemporalService` provides the base logic.
  - `_apply_bitemporal_filter` is used for lists.
  - **GAP**: `TemporalService.get_all` (used by `UserService.get_users` etc.) _does not_ support `as_of`. It hardcodes a "current version" check.
  - **GAP**: API endpoints for Users, Departments, etc. do not accept `as_of` query parameters.

**Codebase Analysis:**

**Backend:**

- `Generic TemporalService`:
  - `get_all()`: Hardcoded to `upper(valid_time) IS NULL` (current versions only). **Needs Refactoring**.
  - `_apply_bitemporal_filter()`: Correctly implements the logic but is only used by services that override `get_all` manually (like `ProjectService`).
- `UserService`:
  - Inherits `TemporalService`.
  - `get_users()` calls `get_all()`, which ignores time travel.
  - `get_user_as_of()` exists but is for single entity only.
- `API Routes`:
  - `projects.py`, `wbes.py`, `cost_elements.py`: Likely support `as_of` (to be verified).
  - `users.py`, `departments.py` (assumed): Do NOT support `as_of` query param.

**Frontend:**

- `useTimeMachineStore`:
  - State is nested under `projectSettings: Record<string, ...>`.
  - Depends on `currentProjectId`.
- `TimeMachineContext`:
  - Derives `as_of` from `currentProjectId`.
- `AppLayout.tsx`:
  - Conditionally renders `TimeMachineCompact` only when `projectId` is present in URL.

---

## Solution Options

### Option 1: True Global State with Project Overrides

Promote Time Machine to be fundamentally global.

**Architecture & Design:**

- **Frontend**:
  - Refactor `useTimeMachineStore` to have a `globalSettings` state (selectedTime, selectedBranch).
  - `TimeMachineContext` provider returns the global setting by default.
  - (Optional) Keep `projectSettings` as an override if a project needs a specific view different from global (complexity tradeoff).
  - Move `TimeMachine` UI to the global Header (always visible).
- **Backend**:
  - Add `as_of` param to `TemporalService.get_all()`.
  - Refactor `UserService.get_users` and `DepartmentService.get_departments` to pass `as_of` down.
  - Update all List API endpoints (`/users`, `/departments`, etc.) to accept `as_of` query param.

**UX Design:**

- The Time Machine bar is always visible in the top header.
- Setting a date puts the _entire application_ into that past state.
- Users list, Departments list, etc., all reflect the state at that time.

**Trade-offs:**

- **Pros**: Consistent mental model ("I am in 2025 mode"). Simplifies navigation between entities.
- **Cons**: Highest refactoring effort (changing store structure).
- **Complexity**: Medium-High.

### Option 2: Context-Aware Global UI (Hybrid)

Keep the implementation "Project-Centric" in the store but expose it globally in the UI, defaulting to "Global" when outside a project.

**Architecture & Design:**

- **Frontend**:
  - Keep `projectSettings` but add a `globalSettings` fallback.
  - If `currentProjectId` is null (e.g. User List page), use `globalSettings`.
  - If `currentProjectId` is set, user can choose to "Sync with Global" or having independent state.
  - **Simplification**: Just use one single global state for the MVP. Remove `projectSettings` map entirely.
- **Backend**: Same as Option 1 (required regardless).

**Trade-offs:**

- **Pros**: Simpler store request (remove the map).
- **Cons**: Loss of per-project granularity (navigating between two projects resets the time).
- **Complexity**: Medium.

---

## Recommendation

**I recommend Option 1 (Modified for Simplicity)**:
Refactor the Store to be **Global Only** for now (removing per-project state). It is confusing for users if Project A is in 2022 and Project B is in 2024. A "Global Time Machine" implies the user is travelling in time for the whole system.

**Plan:**

1.  **Frontend**:
    - Refactor `useTimeMachineStore` to remove `projectSettings` and `currentProjectId` dependency. Use simple `selectedTime` and `selectedBranch`.
    - Update `TimeMachineContext` to serve this global state.
    - Update `AppLayout` to always render `TimeMachineCompact`.
    - Update `TimeMachineCompact` props (remove projectId dependency).
    - Verify all existing Project hooks still work (they just consume the context).
2.  **Backend**:
    - Refactor `TemporalService.get_all` to support `as_of` using `_apply_bitemporal_filter`.
    - Update `UserService`, `DepartmentService`, `CostElementTypeService` to propagate `as_of`.
    - Update API controllers (`users.py`, `departments.py`, etc.) to add `as_of` query param.

## Questions for Decision

1.  Do we agree that "Global" means effectively removing the per-project isolation of time travel? (i.e. if I set date to 2020 in Project A, then navigate to Project B, I am still in 2020). **Assumption: YES.**
2.  Which entities exactly need to be time-travelable? User request says "all versionable entities". This implies Users, Departments, CostElementTypes, etc.
