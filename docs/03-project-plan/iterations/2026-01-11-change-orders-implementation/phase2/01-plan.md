# Phase 2: Branch Management & Entity Editing - Plan

**Date Created:** 2026-01-13
**Epic:** E006 (Branching & Change Order Management)
**Iteration:** Phase 2 - Branch Management & In-Branch Editing
**Status:** Planning Phase
**Related Docs:**
- [Phase 1 Implementation](../phase1/01-plan.md)
- [Change Management User Stories](../../../../01-product-scope/change-management-user-stories.md)
- [Product Backlog](../../../product-backlog.md)

---

## Phase 1 Completion Summary

Phase 1 successfully implemented the foundational Change Order system:

**Completed (Phase 1):**
- ✅ E06-U01: Create Change Orders with automatic branch creation
- ✅ E06-U02: Automatic Branch Creation (`co-{code}` pattern)
- ✅ Change Order CRUD API with full RBAC
- ✅ Change Order Service with BranchableService integration
- ✅ Frontend ChangeOrderList and ChangeOrderModal components
- ✅ BranchSelector component with Time Machine integration
- ✅ TimeMachineStore with branch/mode persistence
- ✅ Full bitemporal versioning support
- ✅ Status field in Change Order form (Select with Draft/Submitted/Under Review/Approved/Rejected/Implemented/Closed)

**Backend Infrastructure Ready:**
- `BranchableService[T]` with `get_current()`, `create_branch()`, `merge_branch()`, `soft_delete()`
- Branch mode filtering (STRICT vs MERGE) implemented in `_apply_branch_mode_filter()`
- Repository pattern with `get_by_branch()` and `get_active_version()` methods
- All entities use `BranchableMixin` with `branch` column (String(80), default "main")

**Frontend Infrastructure Ready:**
- `useTimeMachineStore` with `selectedBranch`, `viewMode` (merged/isolated)
- `useBranchParam()`, `useModeParam()` hooks for API integration
- BranchSelector component for branch switching

---

## Phase 2: Context Analysis

### Documentation Review

**Relevant User Stories from [change-management-user-stories.md](../../../../01-product-scope/change-management-user-stories.md):**

| Story | Description | Priority |
|-------|-------------|----------|
| 3.2 | Performing Work on a Change (In-Branch Editing) | **High** |
| 3.3 | Updating the Change Metadata | **High** |
| 3.5 | Submitting the Change (Branch Locking) | **High** |
| 3.6 | Accepting the Change (Merge) | Critical (Phase 4) |
| 3.7 | Rejecting or Deleting the Change | Critical (Phase 4) |
| 3.8 | Toggling View Modes (Isolated vs Merged) | **Medium** |

**Relevant Backlog Items from [product-backlog.md](../../../product-backlog.md):**

| Item | Story Points | Dependencies | Status |
|------|--------------|--------------|--------|
| E06-U03: Modify Entities in Branch | 8 | E06-U02 ✅ | **Ready** |
| E06-U06: Lock/Unlock Branches | 3 | E06-U02 ✅ | **Ready** |
| E06-U07: Merged View Showing Main + Branch | 5 | E06-U03 | Blocked |
| E06-U08: Delete/Archive Branches | 3 | E06-U05 | Blocked (Phase 4) |

**Total Effort:** 16 story points across 3 user stories (Phase 2)

### Architecture Context

**Bounded Contexts Involved:**
1. **E006 (Branching & Change Order Management)** - Primary context
2. **E004 (Project Structure Management)** - Projects, WBEs, Cost Elements (need branch awareness)
3. **E003 (Entity Versioning System)** - EVCS Core foundation (complete)

**Existing Patterns to Leverage:**
- **BranchableService[T]**: Generic branch operations already implemented
- **BranchMode Enum**: STRICT (isolated) vs MERGE (composite) filtering
- **TimeMachineStore**: Frontend state management for branch/mode selection
- **Command Pattern**: Create/Update/Delete commands with version chaining

### Codebase Analysis

#### Backend - Current State

**Existing Branch/Mode Implementation** ([`backend/app/api/routes/wbes.py`](../../../../../../backend/app/api/routes/wbes.py)):
- ✅ **ALREADY IMPLEMENTED**: `branch` query parameter (default: "main")
- ✅ **ALREADY IMPLEMENTED**: `mode` query parameter with "merged" or "isolated" values
- ✅ **ALREADY IMPLEMENTED**: `as_of` query parameter for time travel
- ✅ Parses mode to `BranchMode.MERGE` or `BranchMode.STRICT` enum
- ✅ Passes to service layer with `branch_mode` parameter

**Branching Infrastructure** ([`backend/app/core/branching/service.py`](../../../../../../backend/app/core/branching/service.py)):
- ✅ `_apply_branch_mode_filter()` implements STRICT vs MERGE logic
- ✅ `get_as_of()` supports time-travel with branch mode
- ✅ `get_current()` retrieves active version on specific branch
- ✅ `create_branch()` method exists for creating branches
- ⚠️ **Gap**: No `branches` table for tracking lock state
- ⚠️ **Gap**: No branch locking mechanism

**Entity Models** (from [`backend/app/models/mixins.py`](../../../../../../backend/app/models/mixins.py)):
- ✅ `BranchableMixin` provides `branch: Mapped[str]` column (String(80), default "main")
- ✅ All branchable entities (Project, WBE, CostElement, ChangeOrder) include this mixin
- ✅ Each entity version is tagged with its branch

**Entity Services** (Projects, WBEs, Cost Elements):
- ✅ `WBEService` **ALREADY** extends `BranchableService[T]` with branch support
- ✅ All services inherit `create_branch()`, `merge_branch()`, `update()` methods
- ✅ WBE list endpoint **ALREADY** has branch/mode/as_of parameters
- ⚠️ **Gap**: Projects and Cost Elements routes don't have branch/mode parameters yet
- ⚠️ **Gap**: No `branches` table for lock state tracking

**Change Order Service** ([`backend/app/services/change_order_service.py`](../../../../../../backend/app/services/change_order_service.py)):
- ⚠️ **CRITICAL GAP**: Branch creation is **NOT** in same transaction as CO creation
- ✅ `create_change_order()` creates CO on main branch only
- ✅ Has `create_branch()` method available via parent `BranchableService`
- ⚠️ **Gap**: No call to `create_branch()` in `create_change_order()` method
- ⚠️ **Gap**: No status workflow enforcement (Draft → Submitted = lock branch)
- ⚠️ **Gap**: Status change does not trigger branch locking
- ⚠️ **Gap**: Change Order list endpoint doesn't support branch/mode filtering

#### Frontend - Current State

**View Mode Selector** ([`frontend/src/components/time-machine/ViewModeSelector.tsx`](../../../../../../frontend/src/components/time-machine/ViewModeSelector.tsx)):
- ✅ **ALREADY IMPLEMENTED**: Segmented control for "merged" vs "isolated" mode
- ✅ Uses Ant Design `Segmented` component
- ✅ Icons: `MergeCellsOutlined` (merged) and `SplitCellsOutlined` (isolated)
- ✅ Calls `invalidateQueries()` on mode change to refresh data
- ✅ Supports `compact` prop for smaller displays

**Time Machine Store** ([`frontend/src/stores/useTimeMachineStore.ts`](../../../../../../frontend/src/stores/useTimeMachineStore.ts)):
- ✅ `selectedBranch`: Persisted per project
- ✅ `viewMode`: "merged" or "isolated" (BranchMode type)
- ✅ `useBranchParam()`, `useModeParam()` hooks for API calls
- ⚠️ **Gap**: No integration with entity CRUD operations

**Change Order Modal** ([`frontend/src/features/change-orders/components/ChangeOrderModal.tsx`](../../../../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx)):
- ✅ Status select box exists with all workflow states
- ✅ Auto-generates branch name from CO code
- ⚠️ **Gap**: Status change doesn't trigger branch lock/unlock

**Branch Selector** ([`frontend/src/components/time-machine/BranchSelector.tsx`](../../../../../../frontend/src/components/time-machine/BranchSelector.tsx)):
- ✅ Dropdown for branch selection
- ✅ Visual branch tags
- ⚠️ **Gap**: No lock/unlock indicators
- ⚠️ **Gap**: View mode toggle not integrated in TimeMachine container

**Entity Forms** (ProjectForm, WBEForm, CostElementForm):
- ✅ CRUD operations working
- ⚠️ **Gap**: No branch context awareness
- ⚠️ **Gap**: No branch switching prompts
- ⚠️ **Gap**: No visual indicators for branch isolation

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What specific problem are we solving?**

Users can create Change Orders with automatic branch creation (Phase 1), but they cannot:
1. **Edit entities (Projects, WBEs, Cost Elements) within the isolated branch context**
2. **Toggle between "Isolated" (changes only) and "Merged" (composite) view modes**
3. **Lock branches automatically when status changes to "Submitted"**
4. **See visual indicators when working in a change branch**

**Why is it important now?**

Phase 1 delivered the foundation, but without in-branch editing, the Change Management workflow is incomplete. Users need to:
- Define scope changes in isolation (create new WBEs, modify budgets, adjust schedules)
- Preview the merged state (main + branch changes) before submission
- Have branches automatically lock when submitted for review
- Toggle view modes to focus on specific changes

**What happens if we don't address it?**

- Change Orders cannot be practically used for scope definition
- The branching infrastructure remains unused beyond CO creation
- Users must manually manage branch context, leading to errors
- No workflow enforcement (branches don't lock on status change)

**Business Value:**

- **Isolated Development**: Enables parallel work on multiple change proposals without affecting production data
- **Impact Preview**: Merged view shows the "future state" before approval
- **Workflow Control**: Automatic branch locking on status change prevents unauthorized edits during review
- **User Confidence**: Visual indicators ensure users know their context (main vs branch)

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- ✅ Users can select a change branch from BranchSelector
- ✅ All entity CRUD (Projects, WBEs, Cost Elements) operations apply to the selected branch
- ✅ View mode toggle (Isolated/Merged) filters list results correctly (frontend-only)
- ✅ Branch locks automatically when Change Order status changes to "Submitted"
- ✅ Branch unlocks when Change Order status changes back to "Draft"
- ✅ Visual indicators show current branch context at all times
- ✅ Switching to a change branch prompts user with context information

**Technical Criteria:**

- API response time: <200ms for branch-aware queries (same as main)
- `branch` query parameter added to all list endpoints (Projects, CostElements, ChangeOrders)
- `mode` query parameter added to all list endpoints (Projects, CostElements, ChangeOrders)
- WBE endpoint already has branch/mode/as_of - use as reference pattern
- Zero data leakage between branches (repository-level enforcement via `branch` column)
- No breaking changes to existing API contracts (`branch` and `mode` parameters are optional)
- **CRITICAL**: Branch creation in SAME transaction as Change Order creation

**Business Criteria:**

- Users can create and modify at least 10 WBEs in a change branch without performance degradation
- Merged view accurately reflects the combined state of main + branch
- Branch locking prevents 100% of unauthorized edits during review

### 3. Scope Definition

**In Scope:**

1. **E06-U03: Modify Entities in Branch**

   - **MODIFY**: Add `branch` query parameter to Projects and Cost Elements list endpoints (WBE already has it)
   - **MODIFY**: Add `mode` query parameter to Projects and Cost Elements list endpoints (WBE already has it)
   - **MODIFY**: Change Order list endpoint - add branch/mode/as_of parameters (like WBE)
   - **MODIFY**: Entity CRUD hooks to use `useBranchParam()` and `useModeParam()`
   - **ADD**: Visual branch indicator to entity forms
   - **ADD**: Branch switching prompt when opening a Change Order

2. **E06-U06: Lock/Unlock Branches**

   - **CREATE**: `branches` table with composite PK (name, project_id) and `locked` boolean
   - **MODIFY**: `change_orders` table - add `branch_name` column
   - **CREATE**: `Branch` domain model and `BranchService` (lock/unlock operations)
   - **CREATE**: Branch API routes (`/api/v1/branches/`)
   - **CRITICAL FIX**: `ChangeOrderService.create_change_order()` - create branch in SAME transaction
   - **MODIFY**: `ChangeOrderService.update_change_order()` - trigger branch lock/unlock on status change
   - **MODIFY**: `BranchSelector` - add lock icon indicators
   - **EXTENSION** (New Sub-Iteration): **E06-U06-UI: Workflow-Aware Status Management**
     - See [`../workflow-ui/00-analysis.md`](../workflow-ui/00-analysis.md)
     - Backend: Add workflow metadata to ChangeOrderPublic schema (`available_transitions`, `can_edit_status`, `branch_locked`)
     - Frontend: Dynamic status dropdown based on current state and available transitions
     - Frontend: Disable status field when branch is locked or `can_edit_status` is false
     - Frontend: Show only "Draft" option on create mode

3. **E06-U07: Merged View Showing Main + Branch Changes**

   - **INTEGRATE**: Existing `ViewModeSelector` component into TimeMachine container
   - **MODIFY**: Entity list components to respect `useModeParam()` for display filtering
   - **ADD**: Visual diff indicators (badges showing delta from main)

4. **E06-U08: Delete/Archive Branches** (Deferred to Phase 4)

   - Backend `soft_delete()` exists but no API endpoint
   - No frontend UI for branch management
   - **Decision**: Defer to Phase 4 with merge workflow

**Out of Scope:**

- ❌ **E06-U04: Compare Branch to Main (Impact Analysis)** - Phase 3 (charts, waterfall, S-curves)
- ❌ **E06-U05: Merge Approved Change Orders** - Phase 4 (conflict resolution, rollback)
- ❌ Branch renaming (not in user stories)
- ❌ Branch permissions beyond RBAC (no branch-level ACLs)
- ❌ Automatic branch cleanup (manual deletion only)

**Assumptions:**

1. EVCS Core (bitemporal versioning + branching) is fully functional
2. WBE endpoint already has branch/mode/as_of implementation - use as pattern
3. `ViewModeSelector` component already exists - just needs integration
4. All entity services (Project, WBE, CostElement) extend `BranchableService[T]`
5. Frontend `useTimeMachineStore` is the single source of truth for branch/mode state
6. Branch names follow the pattern: `main` or `co-{code}`
7. Status workflow is already in Change Order form (select box), just needs enforcement
8. **CRITICAL**: Branch creation must be in SAME transaction as Change Order creation
9. **Workflow Flexibility**: ChangeOrderWorkflowService will be designed to be replaceable with full business process workflow engine in future iterations

---

## Alignment with Functional Requirements

This Phase 2 implementation aligns with the following requirements from [`functional-requirements.md`](../../../../../../docs/01-product-scope/functional-requirements.md):

### Change Order Management (Section 8)

| Requirement | Phase 2 Implementation | Reference |
|-------------|------------------------|----------|
| **8.1 Change Order Processing** - unique identifier, description, justification | ✅ Already implemented (Phase 1) | FR-8.1 |
| **8.2 Change Order Impact Analysis** - model change order impacts | ⚠️ Phase 3 (deferred) | FR-8.2 |
| **8.3 Change Order Approval Workflow** | 🔄 Phase 2 (workflow enforcement) | FR-8.3 |
| **8.4 Branching and Versioning System** | 🔄 Phase 2 (in-branch editing) | FR-8.4 |

### Change Order Workflow States (FR-8.3)

**Functional Requirement:**
> "The system shall track change order status through defined workflow states including draft, submitted for approval, under review, approved, rejected, and implemented."

**Phase 2 Implementation:**
- **Flexible Workflow Service**: `ChangeOrderWorkflowService` provides:
  - `get_next_status(current: str) -> str | None` - Returns next valid status from current
  - `get_available_transitions(current: str) -> List[str]` - All possible statuses from current
  - `should_lock_on_transition(from_status: str, to_status: str) -> bool` - Whether to lock branch
  - `should_unlock_on_transition(from_status: str, to_status: str) -> bool` - Whether to unlock branch
  - `can_edit_on_status(status: str) -> bool` - Whether modifications allowed

**Current Workflow States (from FR-8.3):**
```
Draft → Submitted for Approval → Under Review → Approved → Implemented
                                      ↘ Rejected
```

**Branch Locking Rules (Phase 2):**
- `Draft` → `Submitted for Approval`: **LOCK** branch (prevents edits during review)
- `Submitted for Approval` → `Under Review`: Branch remains **LOCKED**
- `Under Review` → `Rejected`: **UNLOCK** branch (allow revisions)
- `Under Review` → `Approved`: Branch remains **LOCKED** (until merge in Phase 4)
- `Rejected` → `Draft`: **UNLOCK** branch (allow revisions)
- `Approved` → `Implemented`: Branch soft-deleted/archived (Phase 4)

**Future Enhancement Path:**
The `ChangeOrderWorkflowService` is designed as a simple state machine that can be **replaced** with a full business process workflow engine (e.g., Camunda, Temporal) in a future iteration without changing the service interface.

### Branch Selector Requirements (Section 14.1.2)

**Functional Requirement:**
> "The interface shall include a persistent branch selector in the application header... The branch name shall be prominently displayed to indicate the current context. Branch status indicators (active, locked, merged) shall be visible in the selector. Locked branches shall be visually distinguished and prevent modification operations."

**Phase 2 Implementation:**
- ✅ BranchSelector already exists (Phase 1)
- 🔄 Add lock icon indicators (Phase 2)
- 🔄 Add visual distinction for locked branches (Phase 2)
- ✅ Branch switching already works (Phase 1)

### Branch Isolation Rules (Branching Requirements)

**From [`branching-requirements.md`](../../../../../../docs/02-architecture/cross-cutting/temporal-query-reference.md):

| Requirement | Phase 2 Implementation |
|-------------|------------------------|
| Repository Layer Enforcement | ✅ Already implemented via `branch` column filtering |
| Branch Isolation (project-scoped) | 🔄 Phase 2 (add `branches` table with `project_id`) |
| Write Validation (locked branches) | 🔄 Phase 2 (implement lock check) |
| Time Travel Queries | ✅ Already implemented via `as_of` parameter |

---

## Database Schema Design

### New `branches` Table

Since branches currently exist only as string values in entity `branch` columns (via `BranchableMixin`), we need a dedicated `branches` table to track branch metadata and locking state.

**Relationship Design:**

1. **`branches` table**: Stores branch metadata (lock state, type, project scope)
2. **`change_orders` table**: Add `branch_name` column to explicitly reference the branch
3. **Branch isolation**: Branch names are **project-scoped** (same branch name can exist in different projects)
4. **Change Order → Branch**: One-to-one relationship via `change_orders.branch_name → branches.name`

```sql
-- New branches table (for tracking branch metadata and lock state)
CREATE TABLE branches (
    name VARCHAR(80) NOT NULL,
    project_id UUID NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'main',  -- 'main' or 'change_order'
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(user_id),
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    metadata JSONB NULL,
    PRIMARY KEY (name, project_id),  -- Composite PK: branch name is unique within project
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

-- Add branch_name to change_orders table (migration required)
ALTER TABLE change_orders ADD COLUMN branch_name VARCHAR(80);

-- The FK to branches must include project_id for the composite key
-- This is enforced at application level, not DB constraint
-- (ChangeOrder.project_id + ChangeOrder.branch_name → Branches(name, project_id))

-- Indexes
CREATE INDEX ix_branches_type ON branches(type);
CREATE INDEX ix_branches_project_id ON branches(project_id);
CREATE INDEX ix_branches_deleted_at ON branches(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX ix_change_orders_branch_name ON change_orders(branch_name);
```

### Functional Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BRANCH ISOLATION ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────┐         ┌──────────────────────────────────┐
    │        branches          │         │      change_orders (main)        │
    ├──────────────────────────┤         ├──────────────────────────────────┤
    │ name (PK)                │    ┌────│ change_order_id (PK)            │
    │ project_id (PK)          │    │    │ code                            │
    │ type                     │    │    │ project_id ──────────────────┐   │
    │ locked                   │    │    │ branch_name ──────────────────┼───┘
    │ created_at               │    │    │ status                         │
    │ created_by               │    │    │ title                          │
    │ deleted_at               │    │    │ ...                            │
    └──────────────────────────┘    │    └──────────────────────────────────┘
                                    │
    ┌───────────────────────────┐   │
    │    Entity Versions        │   │
    │ (project_versions,        │   │
    │  wbe_versions, etc.)      │   │
    ├───────────────────────────┤   │
    │ id (PK)                   │   │
    │ {entity}_id               │   │
    │ branch (VARCHAR)          │◄──┼─────────────────────┐
    │ project_id (UUID)         │   │                     │
    │ valid_time (TSTZRANGE)    │   │                     │
    │ transaction_time (...)    │   │                     │
    │ deleted_at                │   │                     │
    │ parent_id                 │   │                     │
    └───────────────────────────┘   │                     │
                                    │                     │
    ┌───────────────────────────────────────────────────────────────────────┐
    │                         RELATIONSHIP RULES                            │
    │                                                                       │
    │ 1. Branch Creation (via Change Order)                                │
    │    - User creates ChangeOrder: code='CO-2026-001', project_id=P1     │
    │    - System generates branch_name: 'co-CO-2026-001'                  │
    │    - INSERT INTO branches (name, project_id, type)                   │
    │      VALUES ('co-CO-2026-001', P1, 'change_order')                   │
    │    - UPDATE change_orders SET branch_name='co-CO-2026-001'           │
    │      WHERE change_order_id=<co_id>                                   │
    │                                                                       │
    │ 2. Branch Isolation (Project-Scoped)                                 │
    │    - Branch names are unique WITHIN a project                        │
    │    - Same branch name can exist in different projects                │
    │    - Entity versions: (branch, project_id) tuple identifies context  │
    │                                                                       │
    │ 3. Branch Lock Check (Write Operations)                              │
    │    - On CREATE/UPDATE/DELETE: Check branches.locked                  │
    │    - WHERE name=<entity.branch> AND project_id=<entity.project_id>   │
    │    - If locked=TRUE → Return 403 Forbidden                           │
    │                                                                       │
    │ 4. Change Order → Branch Status Sync                                 │
    │    - Draft → Submitted: Lock branch                                  │
    │    - Submitted → Draft: Unlock branch                                │
    │    - Approved → Implemented: Merge (Phase 4)                         │
    │                                                                       │
    │ 5. Query Filtering                                                   │
    │    - SELECT * FROM wbe_versions                                       │
    │    - WHERE branch = 'co-CO-2026-001'                                 │
    │    - AND project_id = <current_project_id>                           │
    │    - AND deleted_at IS NULL                                          │
    │    - AND valid_time @> NOW()                                         │
    │                                                                       │
    └───────────────────────────────────────────────────────────────────────┘
```

### Branch Lifecycle

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          BRANCH LIFECYCLE                                   │
└────────────────────────────────────────────────────────────────────────────┘

    1. CREATION (Phase 1 - Complete, needs adjustment)
       ┌─────────────────────────────────────────────────────────────────────┐
       │ User creates ChangeOrder:                                          │
       │   - code='CO-2026-001'                                             │
       │   - project_id=P1                                                 │
       │   - status='Draft'                                                │
       │                                                                     │
       │ System actions:                                                     │
       │   1. Generate branch_name: 'co-CO-2026-001'                       │
       │   2. INSERT INTO branches (name, project_id, type)                 │
       │      VALUES ('co-CO-2026-001', P1, 'change_order')                 │
       │   3. UPDATE change_orders SET branch_name='co-CO-2026-001'         │
       │      WHERE change_order_id=<co_id>                                 │
       │   4. Entity versions created with branch='co-CO-2026-001'         │
       └─────────────────────────────────────────────────────────────────────┘

    2. ISOLATED EDITING (Phase 2 - This Iteration)
       ┌─────────────────────────────────────────────────────────────────────┐
       │ User selects branch from BranchSelector                             │
       │ → TimeMachineStore.selectBranch('co-CO-2026-001')                  │
       │ → Frontend: useBranchParam() returns 'co-CO-2026-001'              │
       │ → API: GET /api/v1/wbes?branch=co-CO-2026-001                      │
       │ → Service: Applies branch filter via BranchableService             │
       │ → Result: Only WBE versions with branch='co-CO-2026-001' returned  │
       │                                                                     │
       │ User creates/edits entities in branch:                             │
       │ → New versions created with branch='co-CO-2026-001'                │
       │ → Main branch remains untouched                                     │
       └─────────────────────────────────────────────────────────────────────┘

    3. LOCKING (Phase 2 - This Iteration)
       ┌─────────────────────────────────────────────────────────────────────┐
       │ User updates ChangeOrder status via form select box:               │
       │   Draft → Submitted                                                │
       │                                                                     │
       │ System trigger (in ChangeOrderService.update()):                   │
       │   1. Detect status change: Draft → Submitted                       │
       │   2. Get branch_name from ChangeOrder.branch_name                  │
       │   3. UPDATE branches                                                │
       │      SET locked=TRUE                                                │
       │      WHERE name='co-CO-2026-001'                                   │
       │        AND project_id=<change_order.project_id>                    │
       │   4. All subsequent write operations to branch return 403          │
       │                                                                     │
       │ Reverse (Submitted → Draft):                                       │
       │   → UPDATE branches SET locked=FALSE                               │
       └─────────────────────────────────────────────────────────────────────┘

    4. MERGING (Phase 4 - Future)
       ┌─────────────────────────────────────────────────────────────────────┐
       │ User updates ChangeOrder status: Approved → Implemented            │
       │                                                                     │
       │ System actions:                                                     │
       │   1. Execute merge via MergeBranchCommand                          │
       │      (copy branch versions to main, handle conflicts)               │
       │   2. UPDATE branches SET deleted_at=NOW()                          │
       │      WHERE name='co-CO-2026-001' AND project_id=P1                 │
       │      (soft delete / archive the branch)                            │
       │   3. ChangeOrder marked as 'Implemented'                          │
       └─────────────────────────────────────────────────────────────────────┘
```

### Entity Branch Association

All branchable entities have a `branch` column (from `BranchableMixin`):

```python
# From backend/app/models/mixins.py

class BranchableMixin:
    """Mixin for branching - compose with VersionableMixin."""

    branch: Mapped[str] = mapped_column(String(80), default="main")
    parent_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    merge_from_branch: Mapped[str | None] = mapped_column(String(80), nullable=True)
```

**Example: Complete Branch Isolation Scenario**

```
change_orders table (main branch):
┌──────────────────────────────────────────────────────────────────────────┐
│ change_order_id │ code          │ project_id │ branch_name    │ status    │
├──────────────────────────────────────────────────────────────────────────┤
│ co-xxx-uuid     │ CO-2026-001   │ prj-001    │ co-CO-2026-001 │ Draft     │
└──────────────────────────────────────────────────────────────────────────┘

branches table:
┌──────────────────────────────────────────────────────────────────────────┐
│ name            │ project_id │ type         │ locked │ deleted_at       │
├──────────────────────────────────────────────────────────────────────────┤
│ main            │ prj-001    │ main         │ FALSE  │ NULL             │
│ co-CO-2026-001  │ prj-001    │ change_order │ FALSE  │ NULL             │
└──────────────────────────────────────────────────────────────────────────┘

wbe_versions table (per-project isolation):
┌──────────────────────────────────────────────────────────────────────────┐
│ id │ wbe_id │ project_id │ branch          │ code    │ budget │ parent_id│
├──────────────────────────────────────────────────────────────────────────┤
│ 1  │ wbe-1  │ prj-001    │ main            │ WBE-001 │ 100k   │ NULL     │
│ 2  │ wbe-1  │ prj-001    │ main            │ WBE-001 │ 120k   │ 1        │ ← Main cur
│ 3  │ wbe-1  │ prj-001    │ co-CO-2026-001  │ WBE-001 │ 100k   │ NULL     │ ← Branch copy
│ 4  │ wbe-1  │ prj-001    │ co-CO-2026-001  │ WBE-001 │ 150k   │ 3        │ ← Modified
│ 5  │ wbe-2  │ prj-001    │ co-CO-2026-001  │ WBE-002 │ 50k    │ NULL     │ ← New in branch
│ 6  │ wbe-3  │ prj-002    │ main            │ WBE-003 │ 200k   │ NULL     │ ← Diff project!
│ 7  │ wbe-3  │ prj-002    │ co-CO-2026-001  │ WBE-003 │ 250k   │ 6        │ ← Same branch,
│                                                                            │   diff project
└──────────────────────────────────────────────────────────────────────────┘

Key observations:
- Branch 'co-CO-2026-001' exists in BOTH projects (prj-001 and prj-002)
- Same branch name, different project isolation
- Query filters by (branch, project_id) tuple

Query Examples:

1. GET /api/v1/wbes?branch=co-CO-2026-001&project=prj-001
   → Returns: wbe_versions.id IN (3, 4, 5)
   → Only WBEs in prj-001 on branch 'co-CO-2026-001'

2. GET /api/v1/wbes?branch=main&project=prj-001
   → Returns: wbe_versions.id IN (1, 2)
   → Only WBEs in prj-001 on main branch

3. GET /api/v1/wbes?branch=co-CO-2026-001&project=prj-002
   → Returns: wbe_versions.id IN (6, 7)
   → Completely different context (same branch, different project)

Write Operations with Locking:

1. User updates ChangeOrder status: Draft → Submitted
   → UPDATE branches SET locked=TRUE
      WHERE name='co-CO-2026-001' AND project_id='prj-001'
   → Only locks branch in prj-001

2. Attempt to create WBE on locked branch:
   → POST /api/v1/wbes (with branch=co-CO-2026-001, project_id=prj-001)
   → Service checks: branches.locked for (name, project_id)
   → Returns 403: "Branch 'co-CO-2026-001' in project 'prj-001' is locked"

3. Write to same branch in different project:
   → POST /api/v1/wbes (with branch=co-CO-2026-001, project_id=prj-002)
   → Service checks: branches.locked for (name, project_id)
   → SUCCEEDS (branch in prj-002 is NOT locked)
```

---

## Phase 2: Implementation Approach

### Architecture: Branch-Aware CRUD (Recommended)

**Approach Summary:**

Extend existing entity CRUD operations to be branch-aware by:
1. Adding `branch` query parameter to all list endpoints (NOT `mode` - that's frontend-only)
2. Updating entity services to respect `branch` parameter from request
3. Adding visual indicators to forms showing current branch context
4. Implementing automatic branch locking on Change Order status changes
5. Adding frontend view mode toggle (Isolated/Merged) that filters results client-side

**Design Patterns:**

- **Query Parameter Injection**: `branch` passed via query string (e.g., `?branch=co-CO-2026-001`)
- **Frontend State Management**: TimeMachineStore holds `viewMode` (merged/isolated) for client-side filtering
- **Repository Pattern**: `get_by_branch()` and `get_active_version()` already implemented
- **State Machine**: Change Order status change triggers branch lock/unlock
- **Visual Feedback**: Color-coded header (amber for change branches) + lock icons

**Component Structure:**

```
Backend:
├── Database Migration
│   └── alembic/versions/xxx_add_branches_table.py
│       ├── CREATE TABLE branches (name, project_id, type, locked, ...)
│       ├── ALTER TABLE change_orders ADD COLUMN branch_name VARCHAR(80)
│       └── INSERT INTO branches for existing COs (migration script)
├── Models
│   ├── app/models/domain/branch.py (NEW: Branch ORM model)
│   │   └── Branch with composite PK: (name, project_id)
│   ├── app/models/domain/change_order.py (MODIFY: add branch_name field)
│   │   └── Add branch_name: Mapped[str] field
│   └── app/models/schemas/branch.py (EXTEND: add BranchCreate, BranchUpdate)
├── Routes
│   ├── app/api/routes/branches.py (NEW: lock/unlock/get endpoints)
│   │   ├── GET /api/v1/branches/{name}/project/{project_id}
│   │   ├── POST /api/v1/branches/{name}/project/{project_id}/lock
│   │   └── POST /api/v1/branches/{name}/project/{project_id}/unlock
│   ├── app/api/routes/projects.py (MODIFY: add branch/mode params like WBE)
│   ├── app/api/routes/wbes.py (NO CHANGE: already has branch/mode/as_of)
│   ├── app/api/routes/cost_elements.py (MODIFY: add branch/mode params like WBE)
│   └── app/api/routes/change_orders.py (MODIFY: add branch/mode/as_of params)
│       └── Hook update() to trigger branch lock/unlock on status change
└── Services
    ├── app/services/branch_service.py (NEW: lock/unlock operations)
    │   ├── async def lock(name: str, project_id: UUID) -> Branch
    │   ├── async def unlock(name: str, project_id: UUID) -> Branch
    │   └── async def get_by_name_and_project(name: str, project_id: UUID) -> Branch
    ├── app/services/change_order_workflow_service.py (NEW: flexible workflow)
    │   ├── async def get_next_status(current: str) -> str | None
    │   ├── async def get_available_transitions(current: str) -> List[str]
    │   ├── async def should_lock_on_transition(from_status: str, to_status: str) -> bool
    │   ├── async def should_unlock_on_transition(from_status: str, to_status: str) -> bool
    │   └── async def can_edit_on_status(status: str) -> bool
    └── app/services/change_order_service.py (CRITICAL FIX)
        └── async def create_change_order() - ADD branch creation in SAME transaction
        └── async def update_change_order() - ADD branch lock/unlock triggers

Frontend:
├── Hooks (MODIFY: add branch/mode to API calls)
│   ├── src/features/projects/hooks/useProjects.ts (add branch/mode params)
│   ├── src/features/wbes/hooks/useWBEs.ts (NO CHANGE: already uses branch/mode)
│   └── src/features/cost-elements/hooks/useCostElements.ts (add branch/mode params)
├── Components (NEW)
│   ├── src/components/time-machine/BranchContextBanner.tsx (amber header)
│   └── src/features/change-orders/components/SwitchBranchPrompt.tsx
├── Components (MODIFY)
│   ├── src/components/time-machine/BranchSelector.tsx (add lock icons)
│   ├── src/features/change-orders/components/ChangeOrderModal.tsx (status triggers)
│   └── src/features/change-orders/components/ChangeOrderList.tsx (switch prompt)
└── Components (INTEGRATE - already exists)
    └── src/components/time-machine/ViewModeSelector.tsx (add to TimeMachine container)
```

**API Contract:**

```python
# Existing WBE implementation (pattern to follow):
GET /api/v1/wbes?branch=co-CO-2026-001&mode=isolated&as_of=2026-01-01T00:00:00Z

# Modify Projects endpoint (ADD branch/mode/as_of):
GET /api/v1/projects?branch=co-CO-2026-001&mode=isolated

# Modify Cost Elements endpoint (ADD branch/mode/as_of):
GET /api/v1/cost-elements?branch=co-CO-2026-001&mode=isolated

# Modify Change Orders endpoint (ADD branch/mode/as_of):
GET /api/v1/change-orders?branch=co-CO-2026-001&mode=isolated

# Note: branch is OPTIONAL - defaults to "main"
# Note: mode is OPTIONAL - defaults to "merged" (from WBE implementation)
# Note: as_of is OPTIONAL - defaults to null (current time)

# Branch management (NEW) - project-scoped:
GET /api/v1/branches/{name}/project/{project_id}
    → Get branch metadata and lock status

POST /api/v1/branches/{name}/project/{project_id}/lock
    → Lock branch (prevents writes)

POST /api/v1/branches/{name}/project/{project_id}/unlock
    → Unlock branch (allows writes)

# Example:
POST /api/v1/branches/co-CO-2026-001/project/prj-001-uuid/lock
    → Locks branch 'co-CO-2026-001' in project 'prj-001-uuid'
    → Does NOT affect 'co-CO-2026-001' in other projects
```

**Frontend Data Flow:**

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND DATA FLOW                                  │
└────────────────────────────────────────────────────────────────────────────┘

User Interaction:
┌─────────────────────────────────────────────────────────────────────────────┐
│ User selects "co-CO-2026-001" from BranchSelector                          │
│ → TimeMachineStore.selectBranch('co-CO-2026-001')                          │
│ → useBranchParam() returns 'co-CO-2026-001'                                │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
API Call:
┌─────────────────────────────────────────────────────────────────────────────┐
│ const branch = useBranchParam()  // 'co-CO-2026-001'                       │
│ const { data } = useProjects.useList({ branch })  // Query param            │
│ → GET /api/v1/projects?branch=co-CO-2026-001                               │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
Backend Processing:
┌─────────────────────────────────────────────────────────────────────────────┐
│ @router.get("/projects")                                                    │
│ async def list_projects(                                                   │
│     branch: str = Query(default="main"),  ← Extract from query             │
│     session: DBSession,                                                    │
│ ) -> List[Project]:                                                        │
│     return await project_service.list(branch=branch)  ← Pass to service    │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
Service Layer:
┌─────────────────────────────────────────────────────────────────────────────┐
│ class ProjectService(BranchableService[Project]):                          │
│     async def list(self, branch: str = "main") -> List[Project]:           │
│         stmt = select(Project).where(Project.branch == branch)  ← Filter   │
│         # ... additional bitemporal filters                                │
│         result = await self.session.execute(stmt)                          │
│         return result.scalars().all()                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
Frontend Display (View Mode):
┌─────────────────────────────────────────────────────────────────────────────┐
│ const viewMode = useModeParam()  // 'isolated' or 'merged'                 │
│                                                                            │
│ if (viewMode === 'isolated') {                                             │
│   // Show only entities where branch === selectedBranch                    │
│   displayList = projects.filter(p => p.branch === selectedBranch)         │
│ } else {  // merged                                                        │
│   // Show all entities: branch + main (with branch taking precedence)      │
│   displayList = mergeEntities(projects, selectedBranch)                    │
│ }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**UX Design:**

- **Branch Switching Prompt**: When user clicks "Edit" on a Draft CO, show modal:
  ```
  ┌─────────────────────────────────────────────────────────────┐
  │  Switch to Change Branch                                     │
  ├─────────────────────────────────────────────────────────────┤
  │  To edit this Change Order, switch to branch:               │
  │  co-CO-2026-001                                             │
  │                                                              │
  │  [Cancel]          [Switch & Edit]                          │
  └─────────────────────────────────────────────────────────────┘
  ```

- **Header Color Change**: When on change branch, header background becomes amber (`#F59E0B`)

- **View Mode Toggle**: Segmented control in Time Machine:
  ```
  ┌───────────────────────────────────┐
  │  [ Isolated  |  Merged ]          │
  └───────────────────────────────────┘
  ```

- **Lock Icon**: 🔒 appears next to locked branches in selector

- **Branch Context Banner** (when on change branch):
  ```
  ┌─────────────────────────────────────────────────────────────┐
  │  🟠 Working in: co-CO-2026-001  [Switch to Main]           │
  └─────────────────────────────────────────────────────────────┘
  ```

---

## Phase 2: Technical Design

### ChangeOrderWorkflowService Design

The `ChangeOrderWorkflowService` is a flexible state machine service that encapsulates all workflow logic for Change Orders. It is designed with a **clean interface** that can be replaced with a full business process workflow engine (e.g., Camunda, Temporal) in a future iteration without modifying the calling code.

#### Service Interface

```python
# backend/app/services/change_order_workflow_service.py
from typing import List
from uuid import UUID

class ChangeOrderWorkflowService:
    """Encapsulates Change Order workflow state transitions and business rules.

    This service is designed as a simple state machine that can be replaced
    with a full business process workflow engine in future iterations.

    Workflow States (from FR-8.3):
    Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented

    Future Migration: Replace implementation with Camunda/Temporal while keeping
    the same interface methods.
    """

    async def get_next_status(self, current: str) -> str | None:
        """Get the single next status if the workflow is linear from current state.

        Returns None if multiple transitions are possible (e.g., from "Under Review").
        Use get_available_transitions() for non-linear branches.

        Args:
            current: Current workflow status

        Returns:
            Next status str if linear, None if multiple options
        """

    async def get_available_transitions(self, current: str) -> List[str]:
        """Get all valid status transitions from the current state.

        Args:
            current: Current workflow status

        Returns:
            List of valid status strings that can be transitioned to
        """

    async def should_lock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Determine if a status transition should lock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be locked after this transition
        """

    async def should_unlock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Determine if a status transition should unlock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be unlocked after this transition
        """

    async def can_edit_on_status(self, status: str) -> bool:
        """Determine if Change Order details can be edited in this status.

        Args:
            status: Current workflow status

        Returns:
            True if CO fields can be modified, False if read-only
        """

    async def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Validate if a status transition is allowed.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if transition is valid per workflow rules
        """
```

#### Workflow State Machine Diagram

```
                    ┌─────────────────────────────────────────┐
                    │         Change Order Workflow           │
                    └─────────────────────────────────────────┘

    Draft (editable, unlocked)
        │
        │ [User submits for approval]
        ▼
    Submitted for Approval (read-only, LOCKED)
        │
        │ [Reviewer accepts]
        ▼
    Under Review (read-only, LOCKED)
        │
        │ ┌──────────────────────┐
        │ │                      │
    Approved                  Rejected
    (read-only, LOCKED)      (editable, UNLOCKED)
        │                      │
        │                      │ [User resubmits]
        │ └────────────────────┘──────────────┐
        │                                     ▼
        │                          Submitted for Approval
        │
        │ [Implementation complete]
        ▼
    Implemented (read-only, archived)
```

#### Phase 2 Implementation (Simple State Machine)

```python
# backend/app/services/change_order_workflow_service.py

class ChangeOrderWorkflowService:
    """Simple state machine implementation for Phase 2.

    Future: Replace with Camunda/Temporal workflow engine.
    """

    # Define valid transitions
    _TRANSITIONS: dict[str, list[str]] = {
        "Draft": ["Submitted for Approval"],
        "Submitted for Approval": ["Under Review"],
        "Under Review": ["Approved", "Rejected"],
        "Rejected": ["Submitted for Approval"],
        "Approved": ["Implemented"],
        "Implemented": [],  # Terminal state
    }

    # Define which transitions trigger branch lock
    _LOCK_TRANSITIONS: set[tuple[str, str]] = {
        ("Draft", "Submitted for Approval"),
    }

    # Define which transitions trigger branch unlock
    _UNLOCK_TRANSITIONS: set[tuple[str, str]] = {
        ("Under Review", "Rejected"),
    }

    # Define which statuses allow editing
    _EDITABLE_STATUSES: set[str] = {"Draft", "Rejected"}

    async def get_next_status(self, current: str) -> str | None:
        """Get next status if linear path."""
        options = self._TRANSITIONS.get(current, [])
        return options[0] if len(options) == 1 else None

    async def get_available_transitions(self, current: str) -> List[str]:
        """Get all valid transitions from current status."""
        return self._TRANSITIONS.get(current, []).copy()

    async def should_lock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Check if transition locks branch."""
        return (from_status, to_status) in self._LOCK_TRANSITIONS

    async def should_unlock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Check if transition unlocks branch."""
        return (from_status, to_status) in self._UNLOCK_TRANSITIONS

    async def can_edit_on_status(self, status: str) -> bool:
        """Check if CO is editable in this status."""
        return status in self._EDITABLE_STATUSES

    async def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Validate status transition."""
        valid_options = self._TRANSITIONS.get(from_status, [])
        return to_status in valid_options
```

#### Integration with ChangeOrderService

The `ChangeOrderService` calls the workflow service during status updates to trigger branch lock/unlock:

```python
# backend/app/services/change_order_service.py

class ChangeOrderService(BranchableService[ChangeOrder]):
    def __init__(
        self,
        session: AsyncSession,
        workflow_service: ChangeOrderWorkflowService,  # Dependency injection
    ):
        super().__init__(session)
        self.workflow = workflow_service

    async def update_change_order(
        self,
        root_id: UUID,
        actor_id: UUID,
        status: str | None = None,
        **kwargs,
    ) -> ChangeOrder:
        # Get current CO
        current = await self.get_by_root_id(root_id)
        old_status = current.status
        new_status = status or old_status

        # Validate transition via workflow service
        if old_status != new_status:
            is_valid = await self.workflow.is_valid_transition(
                old_status, new_status
            )
            if not is_valid:
                raise HTTPException(
                    400,
                    f"Invalid status transition: {old_status} → {new_status}",
                )

            # Check if editing is allowed
            can_edit = await self.workflow.can_edit_on_status(old_status)
            if kwargs and not can_edit:
                raise HTTPException(
                    400,
                    f"Cannot edit CO in status: {old_status}",
                )

        # Perform update
        updated_co = await self.update(
            root_id=root_id,
            actor_id=actor_id,
            status=status,
            **kwargs,
        )

        # Trigger branch lock/unlock based on status change
        if old_status != new_status:
            branch_name = updated_co.branch_name

            if await self.workflow.should_lock_on_transition(old_status, new_status):
                await branch_service.lock(branch_name, updated_co.project_id)

            elif await self.workflow.should_unlock_on_transition(old_status, new_status):
                await branch_service.unlock(branch_name, updated_co.project_id)

        return updated_co
```

#### Future Migration to Full Workflow Engine

When migrating to Camunda/Temporal in a future iteration, the service interface remains unchanged:

```python
# backend/app/services/change_order_workflow_service.py (future)

class ChangeOrderWorkflowService:
    """Camunda workflow engine integration.

    Replaces simple state machine while keeping same interface.
    """

    def __init__(self, camunda_client: CamundaClient):
        self.client = camunda_client

    async def get_available_transitions(self, current: str) -> List[str]:
        """Query Camunda for next valid transitions."""
        response = await self.client.get_next_transitions(current)
        return [t["name"] for t in response]

    async def should_lock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Check Camunda process variables for lock flag."""
        transition = await self.client.get_transition(from_status, to_status)
        return transition.get("lock_branch", False)

    # ... other methods with same signatures
```

**Key Point**: The calling code (`ChangeOrderService`) requires **ZERO changes** because the interface remains identical.

#### Branch Locking Flow

```
User Action: Submit CO for Approval
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ ChangeOrderService.update_change_order(                     │
│     root_id=...,                                            │
│     status="Submitted for Approval"                         │
│ )                                                           │
└─────────────────────────────────────────────────────────────┘
        │
        │ 1. Validate transition
        ▼
┌─────────────────────────────────────────────────────────────┐
│ workflow.is_valid_transition(                               │
│     from_status="Draft",                                    │
│     to_status="Submitted for Approval"                      │
│ ) → True                                                    │
└─────────────────────────────────────────────────────────────┘
        │
        │ 2. Update CO status
        ▼
┌─────────────────────────────────────────────────────────────┐
│ self.update(status="Submitted for Approval")                │
│ → CO record updated in database                             │
└─────────────────────────────────────────────────────────────┘
        │
        │ 3. Check if branch should lock
        ▼
┌─────────────────────────────────────────────────────────────┐
│ workflow.should_lock_on_transition(                         │
│     from_status="Draft",                                    │
│     to_status="Submitted for Approval"                      │
│ ) → True                                                    │
└─────────────────────────────────────────────────────────────┘
        │
        │ 4. Lock the branch
        ▼
┌─────────────────────────────────────────────────────────────┐
│ branch_service.lock(                                        │
│     name="co-CO-2026-001",                                  │
│     project_id=...                                          │
│ )                                                           │
│ → UPDATE branches SET locked = TRUE                         │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
    Branch locked! 🔒
    All further writes to this branch blocked
```

### TDD Test Blueprint

```
├── Unit Tests (isolated component behavior)
│   ├── Backend
│   │   ├── test_branch_model.py
│   │   │   ├── test_branch_creation
│   │   │   ├── test_branch_lock_prevents_writes
│   │   │   └── test_branch_unlock_allows_writes
│   │   ├── test_branchable_service_branch_filter.py
│   │   │   ├── test_branch_param_filters_results
│   │   │   ├── test_default_main_branch
│   │   │   └── test_branch_isolation
│   │   └── test_change_order_workflow.py
│   │       ├── test_status_submitted_locks_branch
│   │       ├── test_status_draft_unlocks_branch
│   │       └── test_locked_branch_rejects_updates
│   └── Frontend
│       ├── hooks/useBranchParam.test.ts
│       ├── hooks/useModeParam.test.ts
│       └── components/ViewModeToggle.test.ts
├── Integration Tests (component interactions)
│   ├── test_branch_aware_crud.py
│   │   ├── test_create_wbe_in_branch
│   │   ├── test_update_project_in_branch
│   │   ├── test_list_entities_with_branch_param
│   │   └── test_branch_isolation_enforcement
│   └── test_branch_locking_integration.py
│       ├── test_locked_branch_prevents_create
│       ├── test_locked_branch_prevents_update
│       └── test_status_change_triggers_lock
└── E2E Tests (Playwright)
    ├── branch-crud.spec.ts
    │   ├── test_switch_to_change_branch
    │   ├── test_create_wbe_in_change_branch
    │   ├── test_verify_main_unchanged
    │   └── test_lock_branch_on_status_change
    └── view-mode-toggle.spec.ts
        ├── test_isolated_mode_shows_only_changes
        └── test_merged_mode_shows_composite
```

**First 5 Test Cases (Ordered Simple → Complex):**

1. **test_branch_param_passed_to_list_endpoint**:
   ```python
   async def test_branch_param_filters_wbe_list(session):
       # Create WBE in main
       wbe_main = await wbe_service.create(..., branch="main")
       # Create WBE in branch
       wbe_branch = await wbe_service.create(..., branch="co-001")

       # Query with branch param
       result = await client.get("/api/v1/wbes?branch=co-001")

       assert len(result) == 1
       assert result[0]["id"] == str(wbe_branch.id)
   ```

2. **test_lock_branch_prevents_update**:
   ```python
   async def test_locked_branch_rejects_wbe_update(session):
       # Create branch and lock it
       await branch_service.lock("co-001")

       # Attempt update → expect 403
       response = await client.put(f"/api/v1/wbes/{wbe_id}?branch=co-001", ...)

       assert response.status_code == 403
       assert "locked" in response.json()["detail"].lower()
   ```

3. **test_change_order_status_locks_branch**:
   ```python
   async def test_status_submitted_locks_branch(session):
       # Create CO (Draft, branch unlocked)
       co = await change_order_service.create(..., status="Draft")

       # Update status to Submitted
       await change_order_service.update(co.change_order_id, status="Submitted")

       # Verify branch is locked
       branch = await branch_service.get_by_name("co-CO-2026-001")
       assert branch.locked is True
   ```

4. **test_view_mode_isolated_filters_list**:
   ```typescript
   test("isolated mode shows only branch entities", () => {
     const { result } = renderHook(() => useTimeMachineStore());

     // Set branch and mode
     act(() => {
       result.current.selectBranch("co-001");
       result.current.selectViewMode("isolated");
     });

     // Verify filtering
     const filtered = filterEntitiesByViewMode(entities, "co-001", "isolated");
     expect(filtered).toEqual([entities[1]]); // Only branch entity
   });
   ```

5. **test_view_mode_merged_shows_composite**:
   ```typescript
   test("merged mode shows main + branch", () => {
     const { result } = renderHook(() => useTimeMachineStore());

     act(() => {
       result.current.selectBranch("co-001");
       result.current.selectViewMode("merged");
     });

     const filtered = filterEntitiesByViewMode(entities, "co-001", "merged");
     expect(filtered).toHaveLength(3); // Main + branch (merged)
   });
   ```

### Implementation Strategy

**High-Level Approach:**

1. **Database Schema**: Create `branches` table with `locked` column
2. **Backend Branch API**: New `/api/v1/branches/` routes for lock/unlock
3. **Change Order Workflow**: Hook into status update to trigger branch lock/unlock
4. **Entity CRUD Integration**: Add `branch` query parameter to list endpoints
5. **Frontend Hooks**: Update API hooks to use `useBranchParam()`
6. **UI Components**: Add visual indicators (header color, lock icons, view toggle)

**Key Technologies/Patterns:**

- **FastAPI**: Query parameters, dependency injection for branch context
- **SQLAlchemy**: Filter queries by `branch` column
- **Alembic**: Database migration for `branches` table
- **Zustand**: TimeMachineStore for branch/mode state
- **TanStack Query**: API data fetching with branch context
- **Ant Design**: Segmented control (view toggle), badges (status)

**Integration Points:**

- **Change Order Service**: Status update triggers branch lock/unlock
- **Entity Services**: `list()` methods accept `branch` parameter
- **TimeMachineStore**: Single source of truth for branch/mode state
- **BranchSelector**: Shows lock status and view mode toggle

---

## Phase 2: Risk Assessment

### Risks and Mitigations

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Technical** | Branch mode filtering (MERGE) has edge cases with deleted entities | Medium | Medium | Comprehensive test coverage for deletion scenarios |
| **Technical** | Performance degradation with branch filtering (complex queries) | Low | Medium | Add database indexes on `branch` column, query optimization |
| **Integration** | Breaking changes to existing API contracts | Low | High | Make `branch` parameter optional (default: "main") |
| **Integration** | Frontend state desync (TimeMachineStore vs API) | Medium | Medium | Add validation, error boundaries, and re-sync logic |
| **User Experience** | Users confused about which branch they're editing | Medium | Medium | Prominent visual indicators (header color, lock icon) |
| **User Experience** | Accidental edits to main branch when intending branch | Low | High | Confirmation prompt when switching from branch to main |
| **Data Integrity** | Branch lock check bypassed in some code path | Low | High | Centralize lock check in dependency injection, add comprehensive tests |

---

## Phase 2: Effort Estimation

### Time Breakdown

| Task | Hours |
|------|-------|
| **Development** | |
| Database migration (branches table) | 3 |
| Branch model and service (lock/unlock) | 4 |
| Branch API routes (lock/unlock/get) | 3 |
| Change Order workflow (status → lock trigger) | 4 |
| Entity CRUD branch integration (3 entities × 2h) | 6 |
| Frontend hooks branch awareness (3 entities × 1h) | 3 |
| View mode toggle component | 2 |
| Branch context banner (amber header) | 2 |
| Lock indicators in BranchSelector | 2 |
| Switch branch prompt modal | 2 |
| **Total Development** | **31 hours** |
| **Testing** | |
| Unit tests (branch model, locking, workflow) | 6 |
| Integration tests (branch CRUD, isolation) | 4 |
| E2E tests (branch switching, view toggle, lock) | 4 |
| **Total Testing** | **14 hours** |
| **Documentation** | |
| Update API docs (OpenAPI auto-generated) | 1 |
| Update user guide (branch switching) | 2 |
| **Total Documentation** | **3 hours** |
| **Review & Deployment** | |
| Code review | 2 |
| Deployment & smoke testing | 1 |
| **Total Review** | **3 hours** |
| **TOTAL ESTIMATED EFFORT** | **51 hours (~6 days)** |

### Prerequisites

**Must Complete First:**
- ✅ Phase 1 complete (E06-U01, U02)
- ✅ All entity services extend `BranchableService[T]`
- ✅ TimeMachineStore with branch/mode state
- ✅ Change Order status field in form

**Documentation Updates:**
- API docs: Auto-generated from FastAPI (no manual work)
- User guide: Add "Working with Change Orders" section
- Architecture: Update branching diagram with lock status

**Infrastructure Needs:**
- Database migration script
- Test data with multiple branches
- E2E test environment with branch isolation

---

## Output Format

**File Created:** `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/phase2/01-plan.md`

**Next Steps:**

1. **Create Do Document**: `02-do.md` with detailed implementation tasks
2. **Begin Development**: Database migration → Backend API → Frontend components
3. **Testing**: Unit tests → Integration tests → E2E tests

---

**Document Status:** Ready for Implementation
**Next Document:** `02-do.md`
