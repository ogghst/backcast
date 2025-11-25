# E5-003 Change Order Branch Versioning - Comprehensive Implementation Plan

**Task:** E5-003 (Change Order Entry Interface - Git Branch Versioning Approach)
**Status:** Implementation Phase - Backend Foundation Complete
**Date:** 2025-11-24 (Plan Created), 2025-11-25 (Implementation Complete)
**Last Updated:** 2025-11-25 05:12:58+01:00 (Europe/Rome)
**Analysis Document:** `docs/analysis/e5-003-change-order-branch-versioning-analysis.md`
**Completion Report:** `docs/completions/e5-003-change-order-branch-versioning-completion.md`

## IMPLEMENTATION STATUS

**Completed Steps (Phase 1 & 2 - Backend Foundation):**
- ✅ Step 1: Create VersionStatusMixin Base Class
- ✅ Step 2: Create BranchVersionMixin for WBE and CostElement
- ✅ Step 3: Update WBE Model to Inherit BranchVersionMixin
- ✅ Step 4: Update CostElement Model to Inherit BranchVersionMixin
- ✅ Step 5: Update All Other Entity Models to Inherit VersionStatusMixin
- ✅ Step 6: Create Database Migration for Version/Status/Branch Columns
- ✅ Step 7: Implement Query Filtering for Branch and Status
- ✅ Step 8: Implement Version Service
- ✅ Step 9: Create Entity Versioning Helpers
- ✅ Step 10: Update WBE CRUD Endpoints for Branch/Version/Status
- ✅ Step 11: Update CostElement CRUD Endpoints for Branch/Version/Status
- ✅ Step 12: Update All Other Entity CRUD Endpoints for Soft Delete
- ✅ Step 13: Implement Branch Service - Merge Branch
- ✅ Step 14: Implement Branch Service - Delete Branch (Soft Delete)
- ✅ Step 15: Update ChangeOrder Model and Endpoints for Branch Integration
- ✅ Step 16: Implement Change Order CRUD API
- ✅ Step 17: Implement Change Order Workflow Status Transitions
- ✅ Step 18: Implement Change Order Line Items API

**Current Status:**
- Core versioning infrastructure: ✅ Complete
- All 19 entities updated: ✅ Complete
- All Public schemas updated: ✅ Complete
- Database migrations: ✅ Complete (3 migrations including change order branch)
- CRUD endpoints updated: ✅ Complete (14+ routes including change orders)
- Branch service: ✅ Complete (create, merge, delete)
- Change Order API: ✅ Complete (CRUD, transitions, line items)
- Test coverage: ✅ 489+ tests passing (22 new tests in this session)
- Remaining: Advanced backend features (Steps 19-26), frontend implementation (Phases 4-7)

---

## EXECUTION CONTEXT

- This plan will be implemented using TDD discipline with human supervision
- Implementation will occur in steps within this conversation thread
- Each step must have clear stop/go criteria
- Maximum 3 iteration attempts per step before stopping to ask for help
- Red-green-refactor cycle must be followed for each step

---

## TDD DISCIPLINE RULES

1. **Failing test MUST exist before any production code changes**
2. **Maximum 3 iteration attempts per step** before stopping to ask for help
3. **Red-green-refactor cycle** must be followed for each step:
   - Red: Write failing test
   - Green: Write minimal code to pass test
   - Refactor: Improve code while keeping tests passing
4. **Tests must verify behavior, not just compilation**
5. **All tests must pass before moving to next step**

---

## SCOPE BOUNDARIES

**COMPREHENSIVE SCOPE - All Features Included:**

**Backend Implementation:**
- ✅ Mixin classes (VersionStatusMixin, BranchVersionMixin)
- ✅ Model updates (WBE, CostElement, and all other entities)
- ✅ Database migrations (version, status, branch columns)
- ✅ Query filtering (branch and status filtering)
- ✅ Branch service (create, merge, delete operations)
- ✅ Version service (version number generation)
- ✅ CRUD endpoint updates (branch parameter support)
- ✅ Soft delete implementation (status='deleted')
- ✅ Version increment logic
- ✅ ChangeOrder CRUD API (complete implementation)
- ✅ ChangeOrder workflow status transitions
- ✅ ChangeOrder approval workflow
- ✅ ChangeOrder line items management
- ✅ ChangeOrder financial impact calculation
- ✅ Merge conflict detection and resolution (last-write-wins)
- ✅ Soft delete restore functionality
- ✅ Permanent delete (hard delete) functionality
- ✅ Soft delete retention policy enforcement
- ✅ Soft delete cleanup jobs
- ✅ Version history archival strategy
- ✅ Branch cleanup automation
- ✅ Query performance optimization
- ✅ Caching layer for branch queries
- ✅ Time-machine integration with branches
- ✅ Baseline integration with branches
- ✅ EVM calculation updates for branch support
- ✅ Report generation with branch filtering

**Frontend UI Components:**
- ✅ Branch selector UI component
- ✅ Branch comparison view (side-by-side main vs branch)
- ✅ Merge branch confirmation dialog
- ✅ Change order detail view with branch information
- ✅ Change Orders table component
- ✅ Add/Edit/Delete Change Order dialogs
- ✅ Change Order workflow status transition UI
- ✅ Version history viewer UI
- ✅ Version comparison UI
- ✅ Rollback to previous version UI
- ✅ Soft delete restore UI
- ✅ Branch management UI (list branches, view branch details)
- ✅ Branch diff visualization
- ✅ Branch history/audit trail UI
- ✅ Change Order line items table
- ✅ Financial impact display components

**Advanced Features:**
- ✅ Branch merging preview (before actual merge)
- ✅ Branch conflict resolution UI (manual resolution)
- ✅ Branch naming customization (user-defined names)
- ✅ Branch permissions/access control
- ✅ Branch templates (pre-configured branch structures)
- ✅ Branch cloning functionality
- ✅ Branch locking (prevent concurrent modifications)
- ✅ Branch notifications/alerts

**Testing & Documentation:**
- ✅ Frontend integration tests
- ✅ End-to-end tests with UI
- ✅ User documentation
- ✅ API documentation updates (OpenAPI schema updates)
- ✅ Developer documentation

**Note:** This is a comprehensive plan covering the complete feature set. Implementation will be done in phases with clear dependencies and checkpoints.

---

## ROLLBACK STRATEGY

**Safe Rollback Points:**
1. **After Step 2 (Mixin Classes):** Can revert mixin files, no database changes yet
2. **After Step 4 (Model Updates):** Can revert model files, migration not applied yet
3. **After Step 5 (Migration Created):** Can delete migration file, database unchanged
4. **After Step 5 (Migration Applied):** Can create rollback migration to remove columns

**Alternative Approach:**
- If branch versioning proves too complex, can fall back to staging project approach (E5-003 staging project analysis exists)
- Migration rollback: `alembic downgrade -1` to revert last migration

---

## IMPLEMENTATION STEPS

### Step 1: Create VersionStatusMixin Base Class

**Objective:** Create base mixin class with version and status fields for all entities.

**Test-First Requirement:**
- Create failing test: `backend/tests/models/test_version_status_mixin.py`
- Test: Mixin can be inherited by a test model
- Test: Mixin provides version and status fields with correct defaults
- Test: Mixin fields are accessible on model instances

**Acceptance Criteria:**
- ✅ `VersionStatusMixin` class exists in `backend/app/models/version_status_mixin.py`
- ✅ Mixin has `version: int` field with default=1
- ✅ Mixin has `status: str` field with default='active', max_length=20
- ✅ Mixin can be inherited by test model
- ✅ All tests pass

**Files to Create:**
- `backend/app/models/version_status_mixin.py`
- `backend/tests/models/test_version_status_mixin.py`

**Files to Modify:**
- `backend/app/models/__init__.py` (export VersionStatusMixin)

**Dependencies:**
- None (first step)

**Estimated Time:** 1 hour

---

### Step 2: Create BranchVersionMixin Extended Class

**Objective:** Create extended mixin that inherits from VersionStatusMixin and adds branch field.

**Test-First Requirement:**
- Create failing test: `backend/tests/models/test_branch_version_mixin.py`
- Test: BranchVersionMixin extends VersionStatusMixin
- Test: BranchVersionMixin includes version, status, and branch fields
- Test: BranchVersionMixin provides branch field with default='main'
- Test: Mixin can be inherited by a test model

**Acceptance Criteria:**
- ✅ `BranchVersionMixin` class exists in `backend/app/models/branch_version_mixin.py`
- ✅ BranchVersionMixin inherits from VersionStatusMixin
- ✅ Mixin has `branch: str` field with default='main', max_length=50
- ✅ Mixin includes all fields from VersionStatusMixin (version, status)
- ✅ All tests pass

**Files to Create:**
- `backend/app/models/branch_version_mixin.py`
- `backend/tests/models/test_branch_version_mixin.py`

**Files to Modify:**
- `backend/app/models/__init__.py` (export BranchVersionMixin)

**Dependencies:**
- Step 1 (VersionStatusMixin must exist)

**Estimated Time:** 1 hour

---

### Step 3: Update WBE Model to Use BranchVersionMixin

**Objective:** Update WBE model to inherit from BranchVersionMixin.

**Test-First Requirement:**
- Update existing test: `backend/tests/models/test_wbe.py`
- Test: WBE model has version, status, branch fields
- Test: WBE instances have default values (version=1, status='active', branch='main')
- Test: WBE can be created with custom version/status/branch values
- Test: WBE model still has all existing fields and relationships

**Acceptance Criteria:**
- ✅ WBE model inherits from BranchVersionMixin
- ✅ WBE model has version, status, branch fields accessible
- ✅ Existing WBE tests still pass
- ✅ New tests for version/status/branch pass
- ✅ No breaking changes to existing WBE functionality

**Files to Modify:**
- `backend/app/models/wbe.py`
- `backend/tests/models/test_wbe.py`

**Dependencies:**
- Step 2 (BranchVersionMixin must exist)

**Estimated Time:** 1 hour

---

### Step 4: Update CostElement Model to Use BranchVersionMixin

**Objective:** Update CostElement model to inherit from BranchVersionMixin.

**Test-First Requirement:**
- Update existing test: `backend/tests/models/test_cost_element.py`
- Test: CostElement model has version, status, branch fields
- Test: CostElement instances have default values (version=1, status='active', branch='main')
- Test: CostElement can be created with custom version/status/branch values
- Test: CostElement model still has all existing fields and relationships

**Acceptance Criteria:**
- ✅ CostElement model inherits from BranchVersionMixin
- ✅ CostElement model has version, status, branch fields accessible
- ✅ Existing CostElement tests still pass
- ✅ New tests for version/status/branch pass
- ✅ No breaking changes to existing CostElement functionality

**Files to Modify:**
- `backend/app/models/cost_element.py`
- `backend/tests/models/test_cost_element.py`

**Dependencies:**
- Step 2 (BranchVersionMixin must exist)

**Estimated Time:** 1 hour

---

### Step 5: Update All Other Entity Models to Use VersionStatusMixin

**Objective:** Update all remaining entity models to inherit from VersionStatusMixin.

**Test-First Requirement:**
- Update existing tests for each entity model
- Test: Each model has version and status fields
- Test: Each model instance has default values (version=1, status='active')
- Test: Each model can be created with custom version/status values
- Test: All existing tests still pass

**Acceptance Criteria:**
- ✅ All entity models inherit from VersionStatusMixin
- ✅ All models have version and status fields accessible
- ✅ All existing tests pass
- ✅ New tests for version/status pass
- ✅ No breaking changes to existing functionality

**Entities to Update:**
- Project, User, Forecast, AppConfiguration, VarianceThresholdConfig, ProjectPhase, QualityEvent, ProjectEvent, BudgetAllocation, ChangeOrder, EarnedValueEntry, CostRegistration, CostElementType, CostElementSchedule, Department, BaselineLog, BaselineCostElement, AuditLog

**Files to Modify:**
- All entity model files in `backend/app/models/`
- All corresponding test files in `backend/tests/models/`

**Dependencies:**
- Step 1 (VersionStatusMixin must exist)

**Estimated Time:** 3-4 hours (can be done incrementally, one entity at a time)

**Process Checkpoint:** After this step, pause and confirm:
- Are all models updated correctly?
- Do all tests pass?
- Should we continue with database migration?

---

### Step 6: Create Database Migration for Version/Status/Branch Columns

**Objective:** Create Alembic migration to add version, status, and branch columns to all tables.

**Test-First Requirement:**
- Create test: `backend/tests/migrations/test_add_version_status_branch_columns.py`
- Test: Migration can be applied (upgrade)
- Test: Migration can be rolled back (downgrade)
- Test: Existing records get default values (version=1, status='active', branch='main' for WBE/CostElement)
- Test: Existing records get default values (version=1, status='active' for other entities)
- Test: New records can be created with version/status/branch values

**Acceptance Criteria:**
- ✅ Migration file created: `backend/app/alembic/versions/XXXX_add_version_status_branch_columns.py`
- ✅ Migration adds `version INT NOT NULL DEFAULT 1` to all entity tables
- ✅ Migration adds `status VARCHAR(20) NOT NULL DEFAULT 'active'` to all entity tables
- ✅ Migration adds `branch VARCHAR(50) NOT NULL DEFAULT 'main'` to WBE and CostElement tables only
- ✅ Migration backfills existing records with default values
- ✅ Migration can be applied and rolled back
- ✅ All migration tests pass

**Migration Strategy:**
```python
def upgrade():
    # Add version and status to all entity tables
    for table in all_entity_tables:
        op.add_column(table, sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        op.add_column(table, sa.Column('status', sa.String(20), nullable=False, server_default='active'))

    # Add branch to WBE and CostElement only
    op.add_column('wbe', sa.Column('branch', sa.String(50), nullable=False, server_default='main'))
    op.add_column('costelement', sa.Column('branch', sa.String(50), nullable=False, server_default='main'))

    # Create indexes
    # Composite index for WBE/CostElement: (branch, status, entity_id)
    # Composite index for other entities: (status, entity_id)
    # Version lookup index: (entity_id, branch, version) for WBE/CostElement
    # Version lookup index: (entity_id, version) for other entities

    # Create unique constraints
    # WBE/CostElement: UNIQUE (entity_id, branch, version)
    # Other entities: UNIQUE (entity_id, version)

def downgrade():
    # Drop constraints and indexes
    # Drop columns in reverse order
```

**Files to Create:**
- `backend/app/alembic/versions/XXXX_add_version_status_branch_columns.py`
- `backend/tests/migrations/test_add_version_status_branch_columns.py`

**Dependencies:**
- Steps 3, 4, 5 (All models must be updated)

**Estimated Time:** 2-3 hours

**Process Checkpoint:** After this step, pause and confirm:
- Does migration apply successfully?
- Are default values set correctly?
- Should we continue with query filtering?

---

### Step 7: Implement Query Filtering for Branch and Status

**Objective:** Create query scoping utilities to filter by branch (WBE/CostElement) and status (all entities).

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_filtering.py`
- Test: `apply_branch_filters()` adds branch='main' and status='active' filters for WBE queries
- Test: `apply_branch_filters()` adds branch='co-001' and status='active' filters for CostElement queries
- Test: `apply_status_filters()` adds status='active' filter for other entity queries
- Test: Filtering works with select(), get(), joins
- Test: Filtering can be bypassed for admin queries (include deleted/merged)

**Acceptance Criteria:**
- ✅ `apply_branch_filters()` function exists in `backend/app/services/branch_filtering.py`
- ✅ `apply_status_filters()` function exists in `backend/app/services/branch_filtering.py`
- ✅ Functions work with SQLModel select() queries
- ✅ Functions work with session.get() (wrapper function)
- ✅ Functions respect default branch='main' and status='active'
- ✅ Functions support custom branch and status values
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/branch_filtering.py`
- `backend/tests/services/test_branch_filtering.py`

**Dependencies:**
- Step 6 (Migration must be applied, columns must exist)

**Estimated Time:** 2-3 hours

---

### Step 8: Implement Version Service

**Objective:** Create service for version number generation and management.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_version_service.py`
- Test: `get_next_version()` returns correct next version number per branch
- Test: `get_next_version()` increments version correctly for same entity in same branch
- Test: `get_next_version()` returns version 1 for new entity
- Test: `get_current_version()` returns active version for entity in branch
- Test: Version numbers are sequential per branch (independent sequences)

**Acceptance Criteria:**
- ✅ `VersionService` class exists in `backend/app/services/version_service.py`
- ✅ `get_next_version(entity_type, entity_id, branch)` function works correctly
- ✅ `get_current_version(entity_type, entity_id, branch)` function works correctly
- ✅ Version numbers are sequential per branch
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/version_service.py`
- `backend/tests/services/test_version_service.py`

**Dependencies:**
- Step 7 (Query filtering must work to query existing versions)

**Estimated Time:** 2 hours

---

### Step 9: Implement Branch Service - Create Branch

**Objective:** Create service function to create new branches for change orders.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_service.py`
- Test: `create_branch(change_order_id)` generates branch name 'co-001' format
- Test: `create_branch()` returns unique branch name
- Test: Branch name follows naming convention 'co-{short_id}'
- Test: Branch creation links to change order

**Acceptance Criteria:**
- ✅ `BranchService` class exists in `backend/app/services/branch_service.py`
- ✅ `create_branch(change_order_id)` function exists
- ✅ Function generates branch name in format 'co-{short_id}'
- ✅ Function returns unique branch name
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/branch_service.py` (create file, add create_branch function)
- `backend/tests/services/test_branch_service.py`

**Dependencies:**
- Step 6 (ChangeOrder model must have branch field - update in Step 5)

**Estimated Time:** 1 hour

---

### Step 10: Update WBE CRUD Endpoints for Branch Support

**Objective:** Update WBE CRUD endpoints to support branch parameter and version increment.

**Test-First Requirement:**
- Update existing tests: `backend/tests/api/routes/test_wbes.py`
- Test: CREATE endpoint accepts branch parameter (defaults to 'main')
- Test: CREATE endpoint sets version=1, status='active', branch={branch}
- Test: UPDATE endpoint creates new version (increments version, preserves old)
- Test: UPDATE endpoint works in specified branch
- Test: DELETE endpoint sets status='deleted' (soft delete)
- Test: GET endpoints filter by branch and status='active' by default
- Test: All existing WBE API tests still pass

**Acceptance Criteria:**
- ✅ WBE CREATE endpoint supports branch parameter
- ✅ WBE UPDATE endpoint creates new version in branch
- ✅ WBE DELETE endpoint performs soft delete (status='deleted')
- ✅ WBE GET endpoints filter by branch and status
- ✅ All existing WBE API tests pass
- ✅ New branch-related tests pass

**Files to Modify:**
- `backend/app/api/routes/wbes.py`
- `backend/tests/api/routes/test_wbes.py`

**Dependencies:**
- Step 7 (Query filtering must work)
- Step 8 (Version service must work)

**Estimated Time:** 2-3 hours

---

### Step 11: Update CostElement CRUD Endpoints for Branch Support

**Objective:** Update CostElement CRUD endpoints to support branch parameter and version increment.

**Test-First Requirement:**
- Update existing tests: `backend/tests/api/routes/test_cost_elements.py`
- Test: CREATE endpoint accepts branch parameter (defaults to 'main')
- Test: CREATE endpoint sets version=1, status='active', branch={branch}
- Test: UPDATE endpoint creates new version (increments version, preserves old)
- Test: UPDATE endpoint works in specified branch
- Test: DELETE endpoint sets status='deleted' (soft delete)
- Test: GET endpoints filter by branch and status='active' by default
- Test: All existing CostElement API tests still pass

**Acceptance Criteria:**
- ✅ CostElement CREATE endpoint supports branch parameter
- ✅ CostElement UPDATE endpoint creates new version in branch
- ✅ CostElement DELETE endpoint performs soft delete (status='deleted')
- ✅ CostElement GET endpoints filter by branch and status
- ✅ All existing CostElement API tests pass
- ✅ New branch-related tests pass

**Files to Modify:**
- `backend/app/api/routes/cost_elements.py`
- `backend/tests/api/routes/test_cost_elements.py`

**Dependencies:**
- Step 7 (Query filtering must work)
- Step 8 (Version service must work)

**Estimated Time:** 2-3 hours

---

### Step 12: Update All Other Entity CRUD Endpoints for Soft Delete

**Objective:** Update all other entity CRUD endpoints to support version increment and soft delete.

**Test-First Requirement:**
- Update existing tests for each entity's CRUD endpoints
- Test: CREATE endpoint sets version=1, status='active'
- Test: UPDATE endpoint creates new version (increments version, preserves old)
- Test: DELETE endpoint sets status='deleted' (soft delete)
- Test: GET endpoints filter by status='active' by default
- Test: All existing API tests still pass

**Acceptance Criteria:**
- ✅ All entity CREATE endpoints set version=1, status='active'
- ✅ All entity UPDATE endpoints create new version
- ✅ All entity DELETE endpoints perform soft delete (status='deleted')
- ✅ All entity GET endpoints filter by status='active'
- ✅ All existing API tests pass
- ✅ New version/status tests pass

**Endpoints to Update:**
- Projects, Users, Forecasts, AppConfiguration, VarianceThresholdConfig, ProjectPhase, QualityEvent, ProjectEvent, BudgetAllocation, ChangeOrder, EarnedValueEntry, CostRegistration, CostElementType, CostElementSchedule, Department, BaselineLog, BaselineCostElement, AuditLog

**Files to Modify:**
- All CRUD route files in `backend/app/api/routes/`
- All corresponding test files in `backend/tests/api/routes/`

**Dependencies:**
- Step 7 (Query filtering must work)
- Step 8 (Version service must work)

**Estimated Time:** 4-6 hours (can be done incrementally)

**Process Checkpoint:** After this step, pause and confirm:
- Do all CRUD endpoints work correctly?
- Is soft delete working for all entities?
- Should we continue with branch merge functionality?

---

### Step 13: Implement Branch Service - Merge Branch

**Objective:** Create service function to merge branch into main branch using last-write-wins strategy.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_service_merge.py`
- Test: `merge_branch(branch, change_order_id)` copies active versions from branch to main
- Test: Merge creates new versions in main branch (doesn't overwrite existing versions)
- Test: Merge uses last-write-wins (branch values overwrite main values)
- Test: Merge sets branch entities status='merged' after merge
- Test: Merge handles CREATE operations (new entities in branch)
- Test: Merge handles UPDATE operations (modified entities)
- Test: Merge handles DELETE operations (deleted entities in branch)
- Test: Merge is transactional (all or nothing)

**Acceptance Criteria:**
- ✅ `merge_branch(branch, change_order_id)` function exists in BranchService
- ✅ Function copies active versions from branch to main
- ✅ Function creates new versions in main (preserves history)
- ✅ Function uses last-write-wins strategy
- ✅ Function sets branch entities status='merged' after merge
- ✅ Function handles CREATE, UPDATE, DELETE operations
- ✅ Function is transactional
- ✅ All tests pass

**Files to Modify:**
- `backend/app/services/branch_service.py` (add merge_branch function)
- `backend/tests/services/test_branch_service.py` (add merge tests)

**Dependencies:**
- Step 9 (Branch service must exist)
- Step 10, 11 (WBE/CostElement CRUD must work)

**Estimated Time:** 3-4 hours

---

### Step 14: Implement Branch Service - Delete Branch (Soft Delete)

**Objective:** Create service function to soft delete branch after merge or cancellation.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_service_delete.py`
- Test: `delete_branch(branch)` sets status='deleted' for all branch entities
- Test: Soft delete preserves all versions (doesn't hard delete)
- Test: Soft deleted branch entities don't appear in normal queries
- Test: Soft deleted branch entities can be queried with include_deleted flag

**Acceptance Criteria:**
- ✅ `delete_branch(branch)` function exists in BranchService
- ✅ Function sets status='deleted' for all branch entities
- ✅ Function preserves all versions (soft delete)
- ✅ Function works correctly
- ✅ All tests pass

**Files to Modify:**
- `backend/app/services/branch_service.py` (add delete_branch function)
- `backend/tests/services/test_branch_service.py` (add delete tests)

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 1 hour

---

### Step 15: Update ChangeOrder Model and Endpoints for Branch Integration

**Objective:** Update ChangeOrder model to include branch field and integrate with branch service.

**Test-First Requirement:**
- Update test: `backend/tests/models/test_change_order.py`
- Test: ChangeOrder model has branch field
- Test: ChangeOrder creation automatically creates branch
- Test: ChangeOrder approval triggers merge operation
- Test: ChangeOrder cancellation triggers branch soft delete

**Acceptance Criteria:**
- ✅ ChangeOrder model has branch field
- ✅ ChangeOrder CREATE endpoint creates branch automatically
- ✅ ChangeOrder approval endpoint triggers merge
- ✅ ChangeOrder cancellation endpoint triggers branch soft delete
- ✅ All tests pass

**Files to Modify:**
- `backend/app/models/change_order.py` (add branch field in Step 5)
- `backend/app/api/routes/change_orders.py` (integrate branch service)
- `backend/tests/api/routes/test_change_orders.py`

**Dependencies:**
- Step 9, 13, 14 (Branch service must be complete)
- Step 5 (ChangeOrder model must have branch field)

**Estimated Time:** 2-3 hours

---

### Step 16: Implement Change Order CRUD API

**Objective:** Create complete CRUD API for Change Orders with branch integration.

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_change_orders.py`
- Test: CREATE endpoint creates change order and automatically creates branch
- Test: READ endpoint returns change order with branch information
- Test: UPDATE endpoint updates change order (only in 'design' status)
- Test: DELETE endpoint soft deletes change order and branch
- Test: LIST endpoint returns all change orders for project
- Test: Change order number auto-generation (format: 'CO-{short_id}')
- Test: Financial impact calculation from branch changes

**Acceptance Criteria:**
- ✅ Change Order CRUD API exists in `backend/app/api/routes/change_orders.py`
- ✅ CREATE endpoint creates change order and branch automatically
- ✅ READ endpoint includes branch information
- ✅ UPDATE endpoint validates status (only 'design' can be edited)
- ✅ DELETE endpoint performs soft delete
- ✅ LIST endpoint supports filtering and pagination
- ✅ Change order number auto-generation works
- ✅ Financial impact calculated from branch changes
- ✅ All tests pass

**Files to Create:**
- `backend/app/api/routes/change_orders.py`
- `backend/tests/api/routes/test_change_orders.py`

**Files to Modify:**
- `backend/app/models/change_order.py` (add branch field in Step 5)

**Dependencies:**
- Step 9, 13, 14 (Branch service must be complete)
- Step 5 (ChangeOrder model must have branch field)

**Estimated Time:** 4-5 hours

---

### Step 17: Implement Change Order Workflow Status Transitions

**Objective:** Create API endpoints for change order status transitions (design → approve → execute).

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_change_order_workflow.py`
- Test: Transition design → approve creates 'before' baseline
- Test: Transition approve → execute merges branch and creates 'after' baseline
- Test: Invalid transitions are rejected
- Test: Status transitions update timestamps and user references
- Test: Branch is locked after transition to 'approve'

**Acceptance Criteria:**
- ✅ Status transition endpoint exists
- ✅ Transition design → approve creates baseline
- ✅ Transition approve → execute merges branch
- ✅ Invalid transitions are rejected with proper error messages
- ✅ Status transitions update timestamps and user references
- ✅ Branch locking works correctly
- ✅ All tests pass

**Files to Modify:**
- `backend/app/api/routes/change_orders.py` (add transition endpoint)
- `backend/tests/api/routes/test_change_orders.py` (add workflow tests)

**Dependencies:**
- Step 13 (Merge branch must work)
- Step 16 (Change Order CRUD must exist)

**Estimated Time:** 3-4 hours

---

### Step 18: Implement Change Order Line Items API

**Objective:** Create API endpoints for managing change order line items (auto-generated from branch changes).

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_change_order_line_items.py`
- Test: Line items are auto-generated from branch vs main comparison
- Test: Line items can be read (GET endpoint)
- Test: Line items list endpoint returns all line items for change order
- Test: Line items include operation_type, target_type, staging_target_id, actual_target_id
- Test: Line items include calculated budget_change and revenue_change

**Acceptance Criteria:**
- ✅ Change Order Line Items API exists
- ✅ Line items are auto-generated from branch comparison
- ✅ GET endpoint returns line items for change order
- ✅ Line items include all required fields
- ✅ Financial impact calculated correctly
- ✅ All tests pass

**Files to Create:**
- `backend/app/api/routes/change_order_line_items.py`
- `backend/tests/api/routes/test_change_order_line_items.py`

**Dependencies:**
- Step 13 (Branch merge/comparison must work)
- Step 16 (Change Order CRUD must exist)

**Estimated Time:** 3-4 hours

---

### Step 19: Implement Soft Delete Restore Functionality

**Objective:** Create API endpoints to restore soft-deleted entities.

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_soft_delete_restore.py`
- Test: Restore endpoint sets status='active' for soft-deleted entity
- Test: Restore works for all entity types
- Test: Restore preserves version history
- Test: Restore validates entity exists and is deleted

**Acceptance Criteria:**
- ✅ Restore endpoint exists for all entities
- ✅ Restore sets status='active'
- ✅ Restore preserves version history
- ✅ Restore validates entity state
- ✅ All tests pass

**Files to Create:**
- `backend/app/api/routes/restore.py` (or add to existing routes)
- `backend/tests/api/routes/test_restore.py`

**Dependencies:**
- Step 12 (Soft delete must be implemented)

**Estimated Time:** 2-3 hours

---

### Step 20: Implement Permanent Delete (Hard Delete) Functionality

**Objective:** Create API endpoints for permanent deletion of soft-deleted entities (admin only).

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_hard_delete.py`
- Test: Hard delete endpoint permanently removes entity
- Test: Hard delete requires admin role
- Test: Hard delete removes all versions
- Test: Hard delete validates entity is soft-deleted first

**Acceptance Criteria:**
- ✅ Hard delete endpoint exists (admin only)
- ✅ Hard delete permanently removes entity
- ✅ Hard delete requires admin role
- ✅ Hard delete removes all versions
- ✅ All tests pass

**Files to Create:**
- `backend/app/api/routes/hard_delete.py` (or add to existing routes)
- `backend/tests/api/routes/test_hard_delete.py`

**Dependencies:**
- Step 19 (Soft delete restore must exist)

**Estimated Time:** 2 hours

---

### Step 21: Implement Version History API

**Objective:** Create API endpoints to retrieve version history for entities.

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_version_history.py`
- Test: Version history endpoint returns all versions for entity
- Test: Version history includes version number, status, branch, timestamps
- Test: Version history can be filtered by branch
- Test: Version history supports pagination

**Acceptance Criteria:**
- ✅ Version history endpoint exists for all entities
- ✅ Endpoint returns all versions with metadata
- ✅ Endpoint supports branch filtering (WBE/CostElement)
- ✅ Endpoint supports pagination
- ✅ All tests pass

**Files to Create:**
- `backend/app/api/routes/version_history.py` (or add to existing routes)
- `backend/tests/api/routes/test_version_history.py`

**Dependencies:**
- Step 6 (Migration must be applied)

**Estimated Time:** 2-3 hours

---

### Step 22: Implement Branch Comparison API

**Objective:** Create API endpoint to compare main branch with change order branch.

**Test-First Requirement:**
- Create test: `backend/tests/api/routes/test_branch_comparison.py`
- Test: Comparison endpoint returns differences between branches
- Test: Comparison identifies creates, updates, deletes
- Test: Comparison includes financial impact summary
- Test: Comparison includes detailed change information

**Acceptance Criteria:**
- ✅ Branch comparison endpoint exists
- ✅ Endpoint returns structured comparison data
- ✅ Endpoint identifies all change types
- ✅ Endpoint includes financial impact
- ✅ All tests pass

**Files to Create:**
- `backend/app/api/routes/branch_comparison.py`
- `backend/tests/api/routes/test_branch_comparison.py`

**Dependencies:**
- Step 13 (Branch merge must work)

**Estimated Time:** 2-3 hours

---

### Step 23: Implement Performance Optimizations

**Objective:** Optimize queries and add caching for branch operations.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_performance.py`
- Test: Query performance is acceptable with indexes
- Test: Caching layer works correctly
- Test: Cache invalidation works on updates

**Acceptance Criteria:**
- ✅ Database indexes are optimized
- ✅ Caching layer implemented (if needed)
- ✅ Query performance is acceptable
- ✅ Cache invalidation works
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/cache_service.py` (if needed)
- `backend/tests/services/test_cache.py`

**Dependencies:**
- Step 7 (Query filtering must work)

**Estimated Time:** 3-4 hours

---

### Step 24: Implement Time-Machine Integration with Branches

**Objective:** Integrate time-machine control date with branch filtering.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_time_machine_branch.py`
- Test: Time-machine filtering works with branch filtering
- Test: Control date affects branch queries correctly
- Test: Historical branch state can be queried

**Acceptance Criteria:**
- ✅ Time-machine filtering integrated with branch filtering
- ✅ Control date affects branch queries
- ✅ Historical branch state queryable
- ✅ All tests pass

**Files to Modify:**
- `backend/app/services/branch_filtering.py` (integrate time-machine)
- `backend/app/services/time_machine.py` (add branch support)
- `backend/tests/services/test_time_machine_branch.py`

**Dependencies:**
- Step 7 (Query filtering must work)

**Estimated Time:** 2-3 hours

---

### Step 25: Implement Baseline Integration with Branches

**Objective:** Integrate baseline creation with branch state.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_baseline_branch.py`
- Test: Baseline can be created from branch state
- Test: Baseline captures branch version of entities
- Test: Baseline comparison works with branches

**Acceptance Criteria:**
- ✅ Baseline creation supports branch parameter
- ✅ Baseline captures branch state
- ✅ Baseline comparison works with branches
- ✅ All tests pass

**Files to Modify:**
- `backend/app/services/baseline_service.py` (add branch support)
- `backend/tests/services/test_baseline_branch.py`

**Dependencies:**
- Step 6 (Migration must be applied)

**Estimated Time:** 2-3 hours

---

### Step 26: Implement EVM Calculation Updates for Branch Support

**Objective:** Update EVM calculations to support branch filtering.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_evm_branch.py`
- Test: EVM calculations work with branch parameter
- Test: EVM metrics calculated from branch state
- Test: EVM comparison between branches works

**Acceptance Criteria:**
- ✅ EVM calculations support branch parameter
- ✅ EVM metrics calculated from branch state
- ✅ EVM comparison works
- ✅ All tests pass

**Files to Modify:**
- `backend/app/services/evm_service.py` (add branch support)
- `backend/tests/services/test_evm_branch.py`

**Dependencies:**
- Step 7 (Query filtering must work)

**Estimated Time:** 3-4 hours

---

### Step 27: Regenerate OpenAPI Client

**Objective:** Regenerate frontend OpenAPI client with new API endpoints.

**Test-First Requirement:**
- Verify: OpenAPI client includes new endpoints
- Verify: TypeScript types are generated correctly
- Verify: Client can be imported in frontend

**Acceptance Criteria:**
- ✅ OpenAPI client regenerated
- ✅ New endpoints included
- ✅ TypeScript types generated
- ✅ Client imports work in frontend

**Files to Modify:**
- `frontend/src/client/` (regenerated)

**Dependencies:**
- Steps 16-22 (All API endpoints must exist)

**Estimated Time:** 30 minutes

---

## FRONTEND IMPLEMENTATION STEPS

### Step 28: Create Branch Selector Component

**Objective:** Create reusable branch selector dropdown component.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchSelector.test.tsx`
- Test: Component renders branch dropdown
- Test: Component shows current branch
- Test: Component allows switching branches
- Test: Component updates query on branch change

**Acceptance Criteria:**
- ✅ BranchSelector component exists
- ✅ Component uses Chakra UI Select component
- ✅ Component integrates with TanStack Query
- ✅ Component updates branch context
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchSelector.tsx`
- `frontend/src/components/Projects/BranchSelector.test.tsx`
- `frontend/src/context/BranchContext.tsx` (branch context provider)

**Dependencies:**
- Step 27 (OpenAPI client must be regenerated)

**Estimated Time:** 2-3 hours

---

### Step 29: Create Change Orders Table Component

**Objective:** Create table component to display change orders for a project.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/ChangeOrdersTable.test.tsx`
- Test: Component renders change orders table
- Test: Component uses DataTable component
- Test: Component shows all required columns
- Test: Component supports pagination
- Test: Component supports filtering by status

**Acceptance Criteria:**
- ✅ ChangeOrdersTable component exists
- ✅ Component uses DataTable pattern
- ✅ Component displays all change order fields
- ✅ Component supports pagination
- ✅ Component supports filtering
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/ChangeOrdersTable.tsx`
- `frontend/src/components/Projects/changeOrderColumns.tsx`
- `frontend/src/components/Projects/ChangeOrdersTable.test.tsx`

**Dependencies:**
- Step 27 (OpenAPI client must be regenerated)
- Step 28 (Branch selector must exist)

**Estimated Time:** 3-4 hours

---

### Step 30: Create Add Change Order Dialog

**Objective:** Create dialog component for creating new change orders.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/AddChangeOrder.test.tsx`
- Test: Component renders form with all fields
- Test: Component validates required fields
- Test: Component submits change order creation
- Test: Component shows auto-generated change order number
- Test: Component creates branch automatically

**Acceptance Criteria:**
- ✅ AddChangeOrder component exists
- ✅ Component uses Chakra UI Dialog
- ✅ Component uses React Hook Form
- ✅ Component validates all fields
- ✅ Component creates change order and branch
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/AddChangeOrder.tsx`
- `frontend/src/components/Projects/AddChangeOrder.test.tsx`

**Dependencies:**
- Step 27 (OpenAPI client must be regenerated)

**Estimated Time:** 3-4 hours

---

### Step 31: Create Edit Change Order Dialog

**Objective:** Create dialog component for editing change orders (only in 'design' status).

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/EditChangeOrder.test.tsx`
- Test: Component renders form with pre-filled data
- Test: Component only allows editing in 'design' status
- Test: Component validates fields
- Test: Component submits updates

**Acceptance Criteria:**
- ✅ EditChangeOrder component exists
- ✅ Component pre-fills form with existing data
- ✅ Component validates status (only 'design' editable)
- ✅ Component updates change order
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/EditChangeOrder.tsx`
- `frontend/src/components/Projects/EditChangeOrder.test.tsx`

**Dependencies:**
- Step 30 (AddChangeOrder must exist)

**Estimated Time:** 2-3 hours

---

### Step 32: Create Change Order Detail View

**Objective:** Create detailed view component for change orders with branch information.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/ChangeOrderDetailView.test.tsx`
- Test: Component displays all change order details
- Test: Component shows branch information
- Test: Component shows line items
- Test: Component shows financial impact
- Test: Component shows workflow history

**Acceptance Criteria:**
- ✅ ChangeOrderDetailView component exists
- ✅ Component displays complete change order information
- ✅ Component shows branch name and status
- ✅ Component shows line items table
- ✅ Component shows financial impact summary
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/ChangeOrderDetailView.tsx`
- `frontend/src/components/Projects/ChangeOrderDetailView.test.tsx`

**Dependencies:**
- Step 29 (ChangeOrdersTable must exist)

**Estimated Time:** 4-5 hours

---

### Step 33: Create Branch Comparison View Component

**Objective:** Create side-by-side comparison view for main vs branch.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchComparisonView.test.tsx`
- Test: Component renders side-by-side comparison
- Test: Component highlights differences (green/yellow/red)
- Test: Component shows financial impact summary
- Test: Component is responsive

**Acceptance Criteria:**
- ✅ BranchComparisonView component exists
- ✅ Component shows side-by-side comparison
- ✅ Component uses visual indicators for changes
- ✅ Component shows financial impact
- ✅ Component is responsive
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchComparisonView.tsx`
- `frontend/src/components/Projects/BranchComparisonView.test.tsx`

**Dependencies:**
- Step 22 (Branch comparison API must exist)
- Step 28 (Branch selector must exist)

**Estimated Time:** 5-6 hours

---

### Step 34: Create Merge Branch Dialog

**Objective:** Create confirmation dialog for merging branch into main.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/MergeBranchDialog.test.tsx`
- Test: Component shows merge confirmation
- Test: Component displays merge summary
- Test: Component shows conflict warnings if any
- Test: Component executes merge on confirm

**Acceptance Criteria:**
- ✅ MergeBranchDialog component exists
- ✅ Component shows merge confirmation
- ✅ Component displays merge summary
- ✅ Component handles conflicts
- ✅ Component executes merge
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/MergeBranchDialog.tsx`
- `frontend/src/components/Projects/MergeBranchDialog.test.tsx`

**Dependencies:**
- Step 33 (Branch comparison view must exist)

**Estimated Time:** 3-4 hours

---

### Step 35: Create Change Order Status Transition Component

**Objective:** Create component for changing change order status (design → approve → execute).

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/ChangeOrderStatusTransition.test.tsx`
- Test: Component shows available transitions
- Test: Component validates transition rules
- Test: Component executes transition
- Test: Component shows confirmation for approve → execute

**Acceptance Criteria:**
- ✅ ChangeOrderStatusTransition component exists
- ✅ Component shows available transitions
- ✅ Component validates transition rules
- ✅ Component executes transitions
- ✅ Component shows confirmations
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/ChangeOrderStatusTransition.tsx`
- `frontend/src/components/Projects/ChangeOrderStatusTransition.test.tsx`

**Dependencies:**
- Step 17 (Status transition API must exist)

**Estimated Time:** 3-4 hours

---

### Step 36: Create Change Order Line Items Table Component

**Objective:** Create table component to display change order line items.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/ChangeOrderLineItemsTable.test.tsx`
- Test: Component renders line items table
- Test: Component shows all line item fields
- Test: Component displays operation types correctly
- Test: Component shows financial impacts

**Acceptance Criteria:**
- ✅ ChangeOrderLineItemsTable component exists
- ✅ Component displays all line items
- ✅ Component shows operation types
- ✅ Component shows financial impacts
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/ChangeOrderLineItemsTable.tsx`
- `frontend/src/components/Projects/ChangeOrderLineItemsTable.test.tsx`

**Dependencies:**
- Step 18 (Line items API must exist)

**Estimated Time:** 2-3 hours

---

### Step 37: Create Version History Viewer Component

**Objective:** Create component to display version history for entities.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/VersionHistoryViewer.test.tsx`
- Test: Component renders version history
- Test: Component shows all versions
- Test: Component highlights current version
- Test: Component allows viewing version details

**Acceptance Criteria:**
- ✅ VersionHistoryViewer component exists
- ✅ Component displays version history
- ✅ Component highlights current version
- ✅ Component shows version details
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/VersionHistoryViewer.tsx`
- `frontend/src/components/Projects/VersionHistoryViewer.test.tsx`

**Dependencies:**
- Step 21 (Version history API must exist)

**Estimated Time:** 4-5 hours

---

### Step 38: Create Version Comparison Component

**Objective:** Create component to compare two versions of an entity.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/VersionComparison.test.tsx`
- Test: Component shows side-by-side version comparison
- Test: Component highlights differences
- Test: Component shows field-by-field changes

**Acceptance Criteria:**
- ✅ VersionComparison component exists
- ✅ Component shows side-by-side comparison
- ✅ Component highlights differences
- ✅ Component shows field changes
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/VersionComparison.tsx`
- `frontend/src/components/Projects/VersionComparison.test.tsx`

**Dependencies:**
- Step 37 (Version history viewer must exist)

**Estimated Time:** 4-5 hours

---

### Step 39: Create Rollback to Previous Version Component

**Objective:** Create component to rollback entity to previous version.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/RollbackVersion.test.tsx`
- Test: Component shows rollback confirmation
- Test: Component displays version to rollback to
- Test: Component executes rollback
- Test: Component creates new version with rollback values

**Acceptance Criteria:**
- ✅ RollbackVersion component exists
- ✅ Component shows rollback confirmation
- ✅ Component executes rollback
- ✅ Component creates new version
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/RollbackVersion.tsx`
- `frontend/src/components/Projects/RollbackVersion.test.tsx`

**Dependencies:**
- Step 37 (Version history viewer must exist)

**Estimated Time:** 3-4 hours

---

### Step 40: Create Soft Delete Restore UI Component

**Objective:** Create UI component to restore soft-deleted entities.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/RestoreEntity.test.tsx`
- Test: Component shows restore button for deleted entities
- Test: Component shows restore confirmation
- Test: Component executes restore

**Acceptance Criteria:**
- ✅ RestoreEntity component exists
- ✅ Component shows restore option
- ✅ Component executes restore
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/RestoreEntity.tsx`
- `frontend/src/components/Projects/RestoreEntity.test.tsx`

**Dependencies:**
- Step 19 (Restore API must exist)

**Estimated Time:** 2-3 hours

---

### Step 41: Create Branch Management UI Component

**Objective:** Create component to list and manage branches for a project.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchManagement.test.tsx`
- Test: Component lists all branches
- Test: Component shows branch status
- Test: Component allows viewing branch details
- Test: Component allows soft deleting branches

**Acceptance Criteria:**
- ✅ BranchManagement component exists
- ✅ Component lists all branches
- ✅ Component shows branch information
- ✅ Component supports branch operations
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchManagement.tsx`
- `frontend/src/components/Projects/BranchManagement.test.tsx`

**Dependencies:**
- Step 14 (Branch delete service must exist)

**Estimated Time:** 3-4 hours

---

### Step 42: Create Branch Diff Visualization Component

**Objective:** Create component to visualize differences between branches.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchDiffVisualization.test.tsx`
- Test: Component visualizes branch differences
- Test: Component uses color coding for changes
- Test: Component shows detailed diff information

**Acceptance Criteria:**
- ✅ BranchDiffVisualization component exists
- ✅ Component visualizes differences
- ✅ Component uses appropriate color coding
- ✅ Component shows detailed changes
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchDiffVisualization.tsx`
- `frontend/src/components/Projects/BranchDiffVisualization.test.tsx`

**Dependencies:**
- Step 33 (Branch comparison view must exist)

**Estimated Time:** 4-5 hours

---

### Step 43: Create Branch History/Audit Trail Component

**Objective:** Create component to display branch history and audit trail.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchHistory.test.tsx`
- Test: Component displays branch history
- Test: Component shows audit trail
- Test: Component shows user actions and timestamps

**Acceptance Criteria:**
- ✅ BranchHistory component exists
- ✅ Component displays branch history
- ✅ Component shows audit trail
- ✅ Component shows user actions
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchHistory.tsx`
- `frontend/src/components/Projects/BranchHistory.test.tsx`

**Dependencies:**
- Step 21 (Version history API must exist)

**Estimated Time:** 3-4 hours

---

### Step 44: Integrate Change Orders Tab into Project Detail Page

**Objective:** Add Change Orders tab to project detail page and integrate all components.

**Test-First Requirement:**
- Create test: `frontend/src/routes/_layout/projects.$id.test.tsx`
- Test: Change Orders tab appears in project detail page
- Test: Tab shows ChangeOrdersTable
- Test: Tab integrates with branch selector
- Test: Tab navigation works correctly

**Acceptance Criteria:**
- ✅ Change Orders tab added to project detail page
- ✅ Tab shows ChangeOrdersTable
- ✅ Tab integrates with branch selector
- ✅ Tab navigation works
- ✅ All tests pass

**Files to Modify:**
- `frontend/src/routes/_layout/projects.$id.tsx` (add Change Orders tab)
- `frontend/src/routes/_layout/projects.$id.test.tsx`

**Dependencies:**
- Step 29 (ChangeOrdersTable must exist)
- Step 28 (Branch selector must exist)

**Estimated Time:** 2-3 hours

---

### Step 45: Update WBE/CostElement Forms for Branch Support

**Objective:** Update WBE and CostElement forms to support branch parameter.

**Test-First Requirement:**
- Update test: `frontend/src/components/Projects/AddWBE.test.tsx`
- Test: Form includes branch selector
- Test: Form creates entities in selected branch
- Test: Form defaults to 'main' branch

**Acceptance Criteria:**
- ✅ WBE forms support branch parameter
- ✅ CostElement forms support branch parameter
- ✅ Forms include branch selector
- ✅ Forms default to 'main' branch
- ✅ All tests pass

**Files to Modify:**
- `frontend/src/components/Projects/AddWBE.tsx`
- `frontend/src/components/Projects/EditWBE.tsx`
- `frontend/src/components/Projects/AddCostElement.tsx`
- `frontend/src/components/Projects/EditCostElement.tsx`
- All corresponding test files

**Dependencies:**
- Step 28 (Branch selector must exist)
- Step 10, 11 (WBE/CostElement CRUD must support branch)

**Estimated Time:** 3-4 hours

---

### Step 46: Create Branch Merging Preview Component

**Objective:** Create component to preview merge before execution.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchMergePreview.test.tsx`
- Test: Component shows merge preview
- Test: Component displays conflicts if any
- Test: Component shows merge summary
- Test: Component allows proceeding with merge

**Acceptance Criteria:**
- ✅ BranchMergePreview component exists
- ✅ Component shows merge preview
- ✅ Component displays conflicts
- ✅ Component shows merge summary
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchMergePreview.tsx`
- `frontend/src/components/Projects/BranchMergePreview.test.tsx`

**Dependencies:**
- Step 33 (Branch comparison view must exist)

**Estimated Time:** 4-5 hours

---

### Step 47: Create Manual Merge Conflict Resolution UI

**Objective:** Create UI for manually resolving merge conflicts.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/MergeConflictResolution.test.tsx`
- Test: Component shows conflicts
- Test: Component allows selecting resolution strategy
- Test: Component executes conflict resolution

**Acceptance Criteria:**
- ✅ MergeConflictResolution component exists
- ✅ Component shows conflicts
- ✅ Component allows manual resolution
- ✅ Component executes resolution
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/MergeConflictResolution.tsx`
- `frontend/src/components/Projects/MergeConflictResolution.test.tsx`

**Dependencies:**
- Step 46 (Branch merge preview must exist)

**Estimated Time:** 5-6 hours

---

### Step 48: Create Branch Naming Customization UI

**Objective:** Create UI to allow user-defined branch names (optional feature).

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchNaming.test.tsx`
- Test: Component allows custom branch names
- Test: Component validates branch name format
- Test: Component checks branch name uniqueness

**Acceptance Criteria:**
- ✅ BranchNaming component exists
- ✅ Component allows custom names
- ✅ Component validates names
- ✅ Component checks uniqueness
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchNaming.tsx`
- `frontend/src/components/Projects/BranchNaming.test.tsx`

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 2-3 hours

---

### Step 49: Create Branch Permissions/Access Control UI

**Objective:** Create UI for managing branch permissions and access control.

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchPermissions.test.tsx`
- Test: Component shows branch permissions
- Test: Component allows updating permissions
- Test: Component validates user roles

**Acceptance Criteria:**
- ✅ BranchPermissions component exists
- ✅ Component shows permissions
- ✅ Component allows updates
- ✅ Component validates roles
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchPermissions.tsx`
- `frontend/src/components/Projects/BranchPermissions.test.tsx`

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 3-4 hours

---

### Step 50: Create Branch Templates Component

**Objective:** Create UI for managing branch templates (pre-configured branch structures).

**Test-First Requirement:**
- Create test: `frontend/src/components/Projects/BranchTemplates.test.tsx`
- Test: Component lists branch templates
- Test: Component allows creating templates
- Test: Component allows applying templates

**Acceptance Criteria:**
- ✅ BranchTemplates component exists
- ✅ Component manages templates
- ✅ Component allows applying templates
- ✅ All tests pass

**Files to Create:**
- `frontend/src/components/Projects/BranchTemplates.tsx`
- `frontend/src/components/Projects/BranchTemplates.test.tsx`

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 4-5 hours

---

### Step 51: Create Branch Cloning Functionality

**Objective:** Create UI and API for cloning branches.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_clone.py`
- Test: Clone branch creates new branch with same structure
- Test: Clone branch copies all versions
- Test: Clone branch generates new branch name

**Acceptance Criteria:**
- ✅ Branch cloning API exists
- ✅ Clone creates new branch
- ✅ Clone copies structure
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/branch_service.py` (add clone_branch function)
- `backend/tests/services/test_branch_service.py` (add clone tests)
- `frontend/src/components/Projects/CloneBranch.tsx`
- `frontend/src/components/Projects/CloneBranch.test.tsx`

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 3-4 hours

---

### Step 52: Create Branch Locking Functionality

**Objective:** Create API and UI for locking branches to prevent concurrent modifications.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_locking.py`
- Test: Lock branch prevents modifications
- Test: Unlock branch allows modifications
- Test: Lock shows user who locked it

**Acceptance Criteria:**
- ✅ Branch locking API exists
- ✅ Lock prevents modifications
- ✅ Lock shows user information
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/branch_service.py` (add lock/unlock functions)
- `backend/tests/services/test_branch_locking.py`
- `frontend/src/components/Projects/BranchLocking.tsx`
- `frontend/src/components/Projects/BranchLocking.test.tsx`

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 3-4 hours

---

### Step 53: Create Branch Notifications/Alerts System

**Objective:** Create notification system for branch events (merge, conflicts, etc.).

**Test-First Requirement:**
- Create test: `backend/tests/services/test_branch_notifications.py`
- Test: Notifications created on branch events
- Test: Notifications sent to relevant users
- Test: Notifications include event details

**Acceptance Criteria:**
- ✅ Branch notification system exists
- ✅ Notifications created on events
- ✅ Notifications sent to users
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/branch_notifications.py`
- `backend/tests/services/test_branch_notifications.py`
- `frontend/src/components/Notifications/BranchNotifications.tsx`
- `frontend/src/components/Notifications/BranchNotifications.test.tsx`

**Dependencies:**
- Step 9 (Branch service must exist)

**Estimated Time:** 4-5 hours

---

### Step 54: Implement Soft Delete Retention Policy Enforcement

**Objective:** Create background job to enforce soft delete retention policies.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_retention_policy.py`
- Test: Retention policy job runs on schedule
- Test: Job identifies entities exceeding retention period
- Test: Job permanently deletes expired entities

**Acceptance Criteria:**
- ✅ Retention policy job exists
- ✅ Job runs on schedule
- ✅ Job enforces retention policies
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/retention_policy_service.py`
- `backend/app/jobs/retention_policy_job.py`
- `backend/tests/services/test_retention_policy.py`

**Dependencies:**
- Step 20 (Hard delete must exist)

**Estimated Time:** 3-4 hours

---

### Step 55: Implement Soft Delete Cleanup Jobs

**Objective:** Create background jobs for cleaning up soft-deleted entities.

**Test-First Requirement:**
- Create test: `backend/tests/jobs/test_cleanup_jobs.py`
- Test: Cleanup job runs on schedule
- Test: Job identifies entities to cleanup
- Test: Job performs cleanup operations

**Acceptance Criteria:**
- ✅ Cleanup jobs exist
- ✅ Jobs run on schedule
- ✅ Jobs perform cleanup
- ✅ All tests pass

**Files to Create:**
- `backend/app/jobs/cleanup_jobs.py`
- `backend/tests/jobs/test_cleanup_jobs.py`

**Dependencies:**
- Step 20 (Hard delete must exist)

**Estimated Time:** 2-3 hours

---

### Step 56: Implement Version History Archival Strategy

**Objective:** Create archival system for old versions.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_version_archival.py`
- Test: Archival job identifies old versions
- Test: Archival job moves versions to archive
- Test: Archived versions can be restored

**Acceptance Criteria:**
- ✅ Version archival system exists
- ✅ Archival job works
- ✅ Archived versions accessible
- ✅ All tests pass

**Files to Create:**
- `backend/app/services/version_archival_service.py`
- `backend/app/jobs/version_archival_job.py`
- `backend/tests/services/test_version_archival.py`

**Dependencies:**
- Step 8 (Version service must exist)

**Estimated Time:** 4-5 hours

---

### Step 57: Implement Branch Cleanup Automation

**Objective:** Create automated cleanup for merged/cancelled branches.

**Test-First Requirement:**
- Create test: `backend/tests/jobs/test_branch_cleanup.py`
- Test: Cleanup job identifies branches to cleanup
- Test: Cleanup job soft deletes old branches
- Test: Cleanup job respects retention period

**Acceptance Criteria:**
- ✅ Branch cleanup job exists
- ✅ Job identifies branches to cleanup
- ✅ Job performs cleanup
- ✅ All tests pass

**Files to Create:**
- `backend/app/jobs/branch_cleanup_job.py`
- `backend/tests/jobs/test_branch_cleanup.py`

**Dependencies:**
- Step 14 (Branch delete must exist)

**Estimated Time:** 2-3 hours

---

### Step 58: Implement Report Generation with Branch Filtering

**Objective:** Update report generation to support branch filtering.

**Test-First Requirement:**
- Create test: `backend/tests/services/test_report_branch.py`
- Test: Reports can be generated for specific branch
- Test: Reports show branch-specific data
- Test: Reports compare branches

**Acceptance Criteria:**
- ✅ Report generation supports branch filtering
- ✅ Reports show branch data
- ✅ Reports support comparison
- ✅ All tests pass

**Files to Modify:**
- `backend/app/services/report_service.py` (add branch support)
- `backend/tests/services/test_report_branch.py`

**Dependencies:**
- Step 7 (Query filtering must work)

**Estimated Time:** 3-4 hours

---

### Step 59: Create Frontend Integration Tests

**Objective:** Create comprehensive integration tests for frontend components.

**Test-First Requirement:**
- Create test: `frontend/src/tests/integration/changeOrders.test.tsx`
- Test: Complete change order creation flow
- Test: Branch switching and modification flow
- Test: Merge branch flow
- Test: Version history viewing flow

**Acceptance Criteria:**
- ✅ Integration tests exist
- ✅ Tests cover main user flows
- ✅ Tests use React Testing Library
- ✅ All tests pass

**Files to Create:**
- `frontend/src/tests/integration/changeOrders.test.tsx`
- `frontend/src/tests/integration/branchOperations.test.tsx`
- `frontend/src/tests/integration/versionHistory.test.tsx`

**Dependencies:**
- Steps 28-47 (All frontend components must exist)

**Estimated Time:** 6-8 hours

---

### Step 60: Create End-to-End Tests with UI

**Objective:** Create E2E tests using Playwright for complete user workflows.

**Test-First Requirement:**
- Create test: `frontend/e2e/change-orders.spec.ts`
- Test: Complete change order workflow (create, modify, approve, merge)
- Test: Branch operations workflow
- Test: Version history workflow

**Acceptance Criteria:**
- ✅ E2E tests exist
- ✅ Tests cover complete workflows
- ✅ Tests use Playwright
- ✅ All tests pass

**Files to Create:**
- `frontend/e2e/change-orders.spec.ts`
- `frontend/e2e/branch-operations.spec.ts`
- `frontend/e2e/version-history.spec.ts`

**Dependencies:**
- Step 59 (Integration tests must exist)

**Estimated Time:** 8-10 hours

---

### Step 61: Create User Documentation

**Objective:** Create comprehensive user documentation for change order branch versioning.

**Test-First Requirement:**
- Verify: Documentation covers all features
- Verify: Documentation includes examples
- Verify: Documentation is clear and complete

**Acceptance Criteria:**
- ✅ User documentation exists
- ✅ Documentation covers all features
- ✅ Documentation includes examples
- ✅ Documentation is complete

**Files to Create:**
- `docs/user-guide/change-orders.md`
- `docs/user-guide/branch-versioning.md`
- `docs/user-guide/version-history.md`

**Dependencies:**
- Steps 1-60 (All features must be implemented)

**Estimated Time:** 4-6 hours

---

### Step 62: Create Developer Documentation

**Objective:** Create developer documentation for branch versioning implementation.

**Test-First Requirement:**
- Verify: Documentation covers architecture
- Verify: Documentation includes code examples
- Verify: Documentation explains design decisions

**Acceptance Criteria:**
- ✅ Developer documentation exists
- ✅ Documentation covers architecture
- ✅ Documentation includes examples
- ✅ Documentation explains design

**Files to Create:**
- `docs/developer-guide/branch-versioning-architecture.md`
- `docs/developer-guide/mixin-patterns.md`
- `docs/developer-guide/branch-service.md`

**Dependencies:**
- Steps 1-60 (All features must be implemented)

**Estimated Time:** 4-6 hours

---

## PROCESS CHECKPOINTS

**Checkpoint 1: After Step 5 (All Models Updated)**
- ✅ Are all models updated correctly?
- ✅ Do all tests pass?
- ✅ Should we continue with database migration?

**Checkpoint 2: After Step 6 (Migration Applied)**
- ✅ Does migration apply successfully?
- ✅ Are default values set correctly?
- ✅ Should we continue with query filtering?

**Checkpoint 3: After Step 12 (All CRUD Endpoints Updated)**
- ✅ Do all CRUD endpoints work correctly?
- ✅ Is soft delete working for all entities?
- ✅ Should we continue with branch merge functionality?

**Checkpoint 4: After Step 15 (Complete Implementation)**
- ✅ Is branch versioning working correctly?
- ✅ Are all tests passing?
- ✅ Is the implementation ready for frontend integration?

---

## ESTIMATED TOTAL TIME

**Backend Implementation:** 25-35 hours
- Mixin classes: 2 hours
- Model updates: 5-6 hours
- Database migration: 2-3 hours
- Query filtering: 2-3 hours
- Version service: 2 hours
- Branch service: 5-6 hours
- CRUD endpoint updates: 8-12 hours
- ChangeOrder integration: 2-3 hours

**Testing:** Included in above estimates (TDD approach)

---

## SUCCESS CRITERIA

**Backend Implementation Complete When:**
- ✅ All mixin classes created and tested
- ✅ All models updated and tested
- ✅ Database migration created and applied
- ✅ Query filtering working for all entities
- ✅ Version service working correctly
- ✅ Branch service (create, merge, delete, clone, lock) working
- ✅ All CRUD endpoints support version/status/branch
- ✅ Soft delete working for all entities
- ✅ ChangeOrder CRUD API complete
- ✅ ChangeOrder workflow complete
- ✅ Line items API complete
- ✅ Version history API complete
- ✅ Branch comparison API complete
- ✅ All integrations (time-machine, baseline, EVM, reports) complete
- ✅ Performance optimizations implemented
- ✅ Cleanup jobs and archival working
- ✅ All tests passing
- ✅ No breaking changes to existing functionality

**Frontend Implementation Complete When:**
- ✅ All UI components created and tested
- ✅ Change Orders tab integrated into project detail page
- ✅ Branch selector working in all relevant components
- ✅ Change order CRUD UI complete
- ✅ Branch comparison view working
- ✅ Merge branch functionality complete
- ✅ Version history viewer working
- ✅ Soft delete restore UI working
- ✅ All advanced features UI complete
- ✅ All integration tests passing
- ✅ All E2E tests passing
- ✅ Responsive design working
- ✅ Accessibility requirements met

**Documentation Complete When:**
- ✅ User documentation complete
- ✅ Developer documentation complete
- ✅ API documentation updated
- ✅ Code examples provided

---

## IMPLEMENTATION PHASES

**Phase 1: Core Backend (Steps 1-15)** - Foundation
- Mixin classes, models, migrations, query filtering, services, CRUD updates
- **Estimated Time:** 25-35 hours
- **Priority:** Critical

**Phase 2: Change Order Backend (Steps 16-18)** - Change Order Management
- Change Order CRUD API, workflow, line items
- **Estimated Time:** 10-13 hours
- **Priority:** Critical

**Phase 3: Advanced Backend Features (Steps 19-26)** - Advanced Functionality
- Soft delete restore, hard delete, version history, branch comparison, optimizations, integrations
- **Estimated Time:** 18-24 hours
- **Priority:** High

**Phase 4: Core Frontend (Steps 27-36)** - Essential UI
- OpenAPI client, branch selector, change orders table, dialogs, detail view, comparison, merge
- **Estimated Time:** 35-45 hours
- **Priority:** Critical

**Phase 5: Advanced Frontend Features (Steps 37-53)** - Advanced UI
- Version history, rollback, branch management, conflict resolution, advanced features
- **Estimated Time:** 45-60 hours
- **Priority:** High

**Phase 6: Background Jobs & Cleanup (Steps 54-58)** - Maintenance
- Retention policies, cleanup jobs, archival, report generation
- **Estimated Time:** 14-18 hours
- **Priority:** Medium

**Phase 7: Testing & Documentation (Steps 59-62)** - Quality Assurance
- Integration tests, E2E tests, user docs, developer docs
- **Estimated Time:** 20-25 hours
- **Priority:** High

---

## NOTES

- **Comprehensive Plan:** This plan includes ALL features (previously out-of-scope items are now in scope)
- **Phased Implementation:** Plan is organized into 7 phases with clear priorities
- **Dependencies:** Each step clearly lists dependencies
- **TDD Discipline:** All steps follow TDD approach with failing tests first
- **Best Practices:** Plan uses Context7 research for TanStack Query and Chakra UI patterns
- **Time Estimates:** Total estimated time: 160-205 hours (comprehensive implementation)

---

**Plan Status:** Comprehensive Plan Complete - Ready for Phased Implementation
**Next Action:** Begin Phase 1, Step 1 - Create VersionStatusMixin Base Class
