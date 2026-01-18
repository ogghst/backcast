# Analysis: Schedule Baseline Architecture - One Baseline Per Cost Element (Branchable)

**Created:** 2026-01-18
**Request:** Analyze architectural proposal for one-to-one relationship between Cost Elements and Schedule Baselines, making schedule baselines branchable entities
**Status:** In Progress

---

## Executive Summary

This analysis evaluates a proposal to simplify the relationship between Cost Elements and Schedule Baselines by establishing a **one-to-one branchable relationship**, eliminating the current confusion in Planned Value (PV) calculations caused by multiple schedule baselines per cost element.

---

## Clarified Requirements

### Problem Statement

**Current State:**
- Multiple schedule baselines can exist for a single cost element
- This creates ambiguity in determining which schedule baseline to use for Planned Value (PV) calculations at a specific control date
- Users must manually select or the system must apply complex logic to determine the "active" baseline
- What-if scenario analysis is unclear when multiple baselines exist

**Proposed Solution:**
- Enforce one schedule baseline per cost element
- Make schedule baseline a branchable entity (using EVCS for what-if scenarios)
- Eliminates ambiguity in PV calculations
- Leverages existing EVCS branching infrastructure

### Functional Requirements

From the functional requirements documentation, the system must support:

1. **Schedule Baseline Purpose** (Section 6.1.1):
   - Define versioned, branchable schedule registrations for planned work progression
   - Support CRUD operations while retaining historical entries
   - Capture business context through descriptions and registration dates
   - Support progression types: linear, gaussian, logarithmic

2. **PV Calculation Clarity** (Section 12.2):
   - PV = BAC × % Planned Completion
   - % Planned Completion determined from schedule baseline at control date
   - System must use "the schedule registration with the most recent registration date" for calculations
   - Interpolation rules for dates between registrations

3. **Baseline Management** (Section 10):
   - Support baseline creation at project milestones
   - Maintain historical baselines for comparison
   - Enable baseline vs actuals comparison
   - Baseline data includes schedule registration snapshots

4. **Change Order Support** (Section 8):
   - Branch isolation for change orders
   - Impact analysis before approval
   - Merged view for comparison

### Non-Functional Requirements

- **Performance**: PV calculations must complete in <500ms (Section 17.2)
- **Data Integrity**: No ambiguity in which baseline to use for calculations
- **Audit Trail**: Complete history of schedule changes
- **Usability**: Clear, intuitive interface for schedule management
- **Scalability**: Support 50 concurrent projects with 20 WBEs × 15 cost elements each

### Constraints

- **EVCS Architecture**: Must align with ADR-005 bitemporal versioning pattern
- **EVM Compliance**: Must comply with ANSI/EIA-748 standard
- **Existing Data**: Any migration must preserve existing schedule baseline data
- **Change Order Workflow**: Must integrate with existing branching infrastructure

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- **Section 6.1.1**: Cost Element Schedule Baseline - versioned, branchable schedule registrations
- **Section 10**: Baseline Management Requirements - historical baselines at milestones
- **Section 12.2**: EVM Calculations - PV calculation methodology
- **Section 8**: Change Order Management - branching for what-if scenarios

**Business Requirements:**
- Provide clear, unambiguous PV calculations for EVM reporting
- Support what-if scenario analysis without data confusion
- Maintain complete audit trail of schedule changes
- Enable comparison of current performance against historical baselines

### Architecture Context

**Bounded Contexts Involved:**
1. **Cost Element & Financial Tracking** (Context 6)
   - Primary owner of schedule baselines
   - Cost elements are branchable entities

2. **EVCS Core** (Context 0)
   - Provides branching and versioning framework
   - ADR-005: Bitemporal Single-Table Pattern
   - Generic commands and services for branchable entities

3. **Change Order Processing** (Context 7)
   - Creates branches for what-if scenarios
   - Manages branch lifecycle (draft → approved → merged)

4. **EVM Calculations & Reporting** (Context 8)
   - Consumer of schedule baselines for PV calculations
   - Requires unambiguous baseline selection

**Existing Patterns to Follow:**
- **Branchable Entities**: CostElement, Project, WBE all use `BranchableMixin` + `VersionableMixin`
- **BranchableService**: Generic service class for CRUD with branching
- **Generic Commands**: CreateVersionCommand, UpdateVersionCommand, SoftDeleteCommand
- **Branch Isolation**: Each branch has independent versions of entities

**Architectural Constraints:**
- **ADR-005**: Single-table bitemporal pattern with TSTZRANGE
- **EVCS Protocol**: Entities must satisfy `BranchableProtocol` and `VersionableProtocol`
- **Query Patterns**: Temporal queries use range operators (`@>`) for time-travel
- **Indexing**: GIST indexes for range queries, partial unique indexes for current versions

### Codebase Analysis

**Backend:**

**Current Schedule Baseline Implementation:**
- **Model**: `/backend/app/models/domain/schedule_baseline.py`
  - Already branchable: `class ScheduleBaseline(EntityBase, VersionableMixin, BranchableMixin)`
  - Has `schedule_baseline_id` (root ID), `cost_element_id` (FK), `name`, `start_date`, `end_date`, `progression_type`
  - **Current Issue**: No constraint preventing multiple baselines per cost element

- **Service**: `/backend/app/services/schedule_baseline_service.py`
  - Extends `BranchableService[ScheduleBaseline]`
  - Provides CRUD operations with branching support
  - Methods: `create_root()`, `get_current()`, `get_by_id()`, `soft_delete()`
  - **Current Issue**: No validation for one-to-one relationship

- **API Routes**: `/backend/app/api/routes/schedule_baselines.py`
  - Standard CRUD endpoints
  - **Current Issue**: Can create multiple baselines per cost element

**Cost Element Implementation:**
- **Model**: `/backend/app/models/domain/cost_element.py`
  - Branchable entity: `class CostElement(EntityBase, VersionableMixin, BranchableMixin)`
  - Has `cost_element_id`, `wbe_id`, `cost_element_type_id`, `budget_amount`
  - **No Reference**: Currently no direct reference to schedule baseline

**EVCS Infrastructure:**
- **Branching Service**: `/backend/app/core/branching/service.py`
  - `BranchableService[T]` base class with generic CRUD
  - Supports branch creation, merging, locking
  - Methods: `create_branch()`, `merge_branch()`, `get_current()`

- **Versioning Commands**: `/backend/app/core/versioning/commands.py`
  - `CreateVersionCommand`, `UpdateVersionCommand`, `SoftDeleteCommand`
  - Generic, type-safe command pattern

**Frontend:**

**State Management:**
- TanStack Query for server state caching
- Zustand for client state (branch selector, time machine)
- Branch selection persisted per user session

**Routing:**
- Schedule baselines likely accessed via cost element detail pages
- Need to support switching between branches for comparison

**Frontend:** (Comparable components to be reviewed)

---

## Solution Options

### Option 1: One Schedule Baseline Per Cost Element (Branchable) ✅ **PROPOSED**

**Architecture & Design:**

Enforce a strict one-to-one relationship between Cost Elements and Schedule Baselines, leveraging EVCS branching for what-if scenarios.

**Data Model Changes:**
1. Add `schedule_baseline_id` FK to `CostElement` entity (nullable for migration)
2. Add unique constraint: `cost_element_id` → `schedule_baseline_id` (1:1)
3. Make schedule baseline cascade delete when cost element is deleted
4. Add validation: Cannot create baseline if one exists for cost element

**Service Layer Changes:**
1. Modify `ScheduleBaselineService.create()` to check for existing baseline
2. Add `get_for_cost_element(cost_element_id, branch)` method
3. Add `ensure_exists(cost_element_id, branch)` method for automatic creation
4. Modify `CostElementService` to auto-create baseline on cost element creation
5. Update `soft_delete()` to prevent deletion if baseline exists

**API Layer Changes:**
1. Remove independent baseline creation endpoint
2. Add baseline management to cost element endpoints
3. GET `/api/v1/cost-elements/{id}/schedule-baseline` - retrieve
4. PUT `/api/v1/cost-elements/{id}/schedule-baseline` - update (create if not exists)
5. DELETE `/api/v1/cost-elements/{id}/schedule-baseline` - soft delete (with confirmation)

**PV Calculation Logic:**
```python
# Simplified PV calculation
async def calculate_pv(
    cost_element_id: UUID,
    control_date: datetime,
    branch: str = "main"
) -> Decimal:
    # Get the ONE schedule baseline for this cost element
    baseline = await schedule_baseline_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch
    )

    if not baseline:
        raise NoScheduleBaselineError(cost_element_id)

    # Calculate planned completion % based on control date
    planned_pct = calculate_planned_completion(
        start_date=baseline.start_date,
        end_date=baseline.end_date,
        control_date=control_date,
        progression_type=baseline.progression_type
    )

    # PV = BAC × % Planned
    bac = await get_bac_for_cost_element(cost_element_id, branch)
    return bac * Decimal(str(planned_pct))
```

**Migration Strategy:**
1. Identify cost elements with multiple baselines
2. Select most recent baseline (by `created_at`) as primary
3. Archive other baselines (move to `baseline_history` table or soft delete)
4. Add FK constraint and unique index
5. Update frontend to use new API structure

**UX Design:**

- Schedule baseline management embedded in cost element detail view
- Single "Schedule" tab in cost element UI (no list of baselines)
- Branch selector controls which version to view/edit
- Clear indication when switching branches affects schedule
- Validation prevents creating duplicate baselines
- Warning when deleting baseline (requires confirmation)

**Branching Behavior:**

- Main branch: Operational schedule baseline
- Change order branch: Modified schedule for what-if analysis
- PV calculations automatically use baseline from selected branch
- Branch comparison shows schedule changes side-by-side

**Implementation:**

**Key Technical Details:**

1. **Database Migration**:
```sql
-- Add FK to cost_elements
ALTER TABLE cost_elements
ADD COLUMN schedule_baseline_id UUID REFERENCES schedule_baselines(schedule_baseline_id);

-- Migrate existing data (select most recent baseline per cost element)
UPDATE cost_elements ce
SET schedule_baseline_id = (
    SELECT sb.id
    FROM schedule_baselines sb
    WHERE sb.cost_element_id = ce.cost_element_id
      AND sb.branch = 'main'
      AND sb.deleted_at IS NULL
    ORDER BY sb.created_at DESC
    LIMIT 1
);

-- Add unique constraint
CREATE UNIQUE INDEX uq_cost_element_schedule_baseline
ON cost_elements (schedule_baseline_id)
WHERE schedule_baseline_id IS NOT NULL;

-- Remove old cost_element_id FK from schedule_baselines
ALTER TABLE schedule_baselines DROP CONSTRAINT schedule_baselines_cost_element_id_fkey;
```

2. **Service Validation**:
```python
class ScheduleBaselineService(BranchableService[ScheduleBaseline]):
    async def create_for_cost_element(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        **data: Any
    ) -> ScheduleBaseline:
        # Check if baseline already exists
        existing = await self.get_for_cost_element(cost_element_id, branch)
        if existing:
            raise BaselineAlreadyExistsError(cost_element_id)

        # Create new baseline
        return await self.create_root(...)

    async def get_for_cost_element(
        self,
        cost_element_id: UUID,
        branch: str = "main"
    ) -> ScheduleBaseline | None:
        # Query via cost element's schedule_baseline_id
        stmt = (
            select(ScheduleBaseline)
            .join(CostElement, CostElement.schedule_baseline_id == ScheduleBaseline.id)
            .where(
                CostElement.cost_element_id == cost_element_id,
                ScheduleBaseline.branch == branch,
                ScheduleBaseline.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

3. **Cost Element Auto-Creation**:
```python
class CostElementService(BranchableService[CostElement]):
    async def create_root(self, ...) -> CostElement:
        # Create cost element
        cost_element = await super().create_root(...)

        # Auto-create default schedule baseline
        await schedule_baseline_service.create_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            actor_id=actor_id,
            branch=branch,
            name="Default Schedule",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=90),
            progression_type="LINEAR"
        )

        return cost_element
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - **Unambiguous PV calculations** - always use the one baseline<br>- **Leverages existing EVCS branching** - no new infrastructure<br>- **Simplified data model** - clear 1:1 relationship<br>- **Better UX** - no confusion about which baseline to use<br>- **Consistent with Cost Element architecture** - both branchable<br>- **Automatic audit trail** - via EVCS versioning |
| Cons            | - **Migration complexity** - need to resolve existing duplicates<br>- **Loss of historical baselines** - unless archived separately<br>- **Less flexibility** - cannot have multiple "active" scenarios<br>- **Cascade delete risk** - deleting cost element deletes baseline |
| Complexity      | **Medium** - migration is main effort |
| Maintainability | **Excellent** - clear, simple relationship |
| Performance     | **Excellent** - single query for PV calculation (<100ms) |

---

### Option 2: Multiple Baselines Per Cost Element with "Active" Flag

**Architecture & Design:**

Allow multiple schedule baselines per cost element, but designate one as "active" via a flag.

**Data Model Changes:**
1. Add `is_active` boolean flag to `ScheduleBaseline` entity
2. Add constraint: Only one baseline can be active per cost element per branch
3. Allow multiple inactive baselines for historical reference

**Service Layer Changes:**
1. Add `set_active(schedule_baseline_id, branch)` method
2. Add `get_active_baseline(cost_element_id, branch)` method
3. Modify `create()` to auto-set `is_active=True` if no active baseline exists
4. Add validation: Cannot set active if another baseline is already active

**API Layer Changes:**
1. POST `/api/v1/schedule-baselines` - create (auto-active if first)
2. PUT `/api/v1/schedule-baselines/{id}/activate` - set as active
3. GET `/api/v1/cost-elements/{id}/schedule-baseline` - returns active baseline
4. GET `/api/v1/cost-elements/{id}/schedule-baselines` - list all (active + inactive)

**PV Calculation Logic:**
```python
async def calculate_pv(cost_element_id, control_date, branch):
    # Get the ACTIVE schedule baseline
    baseline = await schedule_baseline_service.get_active_baseline(
        cost_element_id=cost_element_id,
        branch=branch
    )
    if not baseline:
        raise NoActiveBaselineError(cost_element_id)
    # Calculate PV...
```

**Migration Strategy:**
1. Add `is_active` column to `schedule_baselines`
2. For cost elements with multiple baselines, set most recent as active
3. Add partial unique index: `(cost_element_id, branch) WHERE is_active = true`
4. No data loss - all historical baselines preserved

**UX Design:**

- List all baselines in cost element UI
- Visual indicator for "active" baseline (badge, star, highlight)
- "Set as Active" button on each baseline
- Confirmation when switching active baseline
- Active baseline used for all PV calculations

**Branching Behavior:**

- Each branch has its own "active" baseline
- Switching branches changes which baseline is considered active
- Branch comparison shows active baselines side-by-side

**Implementation:**

**Key Technical Details:**

1. **Database Schema**:
```sql
ALTER TABLE schedule_baselines
ADD COLUMN is_active BOOLEAN DEFAULT false;

-- Set most recent baseline as active
UPDATE schedule_baselines sb1
SET is_active = true
WHERE sb1.id = (
    SELECT sb2.id
    FROM schedule_baselines sb2
    WHERE sb2.cost_element_id = sb1.cost_element_id
      AND sb2.branch = sb1.branch
      AND sb2.deleted_at IS NULL
    ORDER BY sb2.created_at DESC
    LIMIT 1
);

-- Partial unique index for active baseline
CREATE UNIQUE INDEX uq_schedule_baseline_active
ON schedule_baselines (cost_element_id, branch)
WHERE is_active = true AND deleted_at IS NULL;
```

2. **Service Validation**:
```python
class ScheduleBaselineService(BranchableService[ScheduleBaseline]):
    async def set_active(
        self,
        schedule_baseline_id: UUID,
        actor_id: UUID,
        branch: str = "main"
    ) -> ScheduleBaseline:
        # Deactivate current active baseline
        current_active = await self.get_active_baseline(
            cost_element_id=cost_element_id,
            branch=branch
        )
        if current_active:
            await self.update(
                root_id=current_active.schedule_baseline_id,
                updates={"is_active": False},
                branch=branch,
                actor_id=actor_id
            )

        # Activate new baseline
        return await self.update(
            root_id=schedule_baseline_id,
            updates={"is_active": True},
            branch=branch,
            actor_id=actor_id
        )
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - **Preserves historical baselines** - no data loss<br>- **Flexibility** - can switch active baseline<br>- **Clear migration path** - just add flag<br>- **Backward compatible** - existing API still works<br>- **Multiple scenarios** - can keep multiple "what-ifs" |
| Cons            | - **Ambiguity risk** - users may not know which is active<br>- **Complex validation** - ensure only one active<br>- **UI complexity** - need to manage multiple baselines<br>- **Query overhead** - need to filter by is_active flag<br>- **State management** - active flag can get out of sync |
| Complexity      | **Low** - simple flag addition |
| Maintainability | **Good** - but requires careful validation |
| Performance     | **Good** - indexed query (~100ms) |

---

### Option 3: Baseline as Cost Element Child (Non-Branchable)

**Architecture & Design:**

Make schedule baseline a child entity of cost element, not independently branchable. Inherits branch from cost element.

**Data Model Changes:**
1. Remove `BranchableMixin` from `ScheduleBaseline`
2. Keep `VersionableMixin` for history tracking
3. Add `cost_element_version_id` FK to link to specific cost element version
4. Add cascade delete from cost element to schedule baseline

**Service Layer Changes:**
1. Extend `TemporalService` (not `BranchableService`)
2. Add `get_for_cost_element_version(cost_element_version_id)` method
3. Remove branch parameter from all methods
4. Add validation: Cannot delete baseline if cost element exists

**API Layer Changes:**
1. Nest baseline endpoints under cost elements
2. GET `/api/v1/cost-elements/{id}/schedule` - retrieve baseline
3. PUT `/api/v1/cost-elements/{id}/schedule` - update baseline
4. Inherit branch from cost element context

**PV Calculation Logic:**
```python
async def calculate_pv(
    cost_element_id: UUID,
    control_date: datetime,
    branch: str = "main"
) -> Decimal:
    # Get cost element first (branch-aware)
    cost_element = await cost_element_service.get_current(
        root_id=cost_element_id,
        branch=branch
    )

    # Get schedule baseline linked to this cost element version
    baseline = await schedule_baseline_service.get_for_cost_element_version(
        cost_element_version_id=cost_element.id
    )

    if not baseline:
        raise NoScheduleBaselineError(cost_element_id)

    # Calculate PV...
```

**Migration Strategy:**
1. Remove `BranchableMixin` from `ScheduleBaseline` model
2. Add `cost_element_version_id` FK column
3. Migrate existing baselines to link to current cost element version
4. Remove branch-specific queries from service
5. Update API to nested structure

**UX Design:**

- Schedule embedded in cost element detail view
- No separate schedule management UI
- Branch selector controls cost element, schedule follows automatically
- Simpler UI - no independent schedule branching

**Branching Behavior:**

- Schedule baseline inherits branch from cost element
- When cost element is branched, baseline is automatically copied
- No independent branching of schedule
- Consistent with cost element lifecycle

**Implementation:**

**Key Technical Details:**

1. **Data Model**:
```python
class ScheduleBaseline(EntityBase, VersionableMixin):  # No BranchableMixin
    """Schedule Baseline - child of Cost Element."""

    __tablename__ = "schedule_baselines"

    schedule_baseline_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    cost_element_version_id: Mapped[UUID] = mapped_column(  # Links to specific version
        PG_UUID,
        ForeignKey("cost_elements.id"),
        nullable=False,
        unique=True  # One baseline per cost element version
    )

    # ... other fields ...
```

2. **Service**:
```python
class ScheduleBaselineService(TemporalService[ScheduleBaseline]):
    """Service for Schedule Baseline (versionable, not branchable)."""

    async def get_for_cost_element_version(
        self,
        cost_element_version_id: UUID
    ) -> ScheduleBaseline | None:
        stmt = select(ScheduleBaseline).where(
            ScheduleBaseline.cost_element_version_id == cost_element_version_id,
            ScheduleBaseline.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - **Simpler model** - no independent branching<br>- **Consistent lifecycle** - follows cost element<br>- **Cleaner API** - nested endpoints<br>- **No ambiguity** - one baseline per cost element version<br>- **Less migration** - just remove branchable |
| Cons            | - **Loses independent branching** - cannot what-if schedule alone<br>- **Tight coupling** - schedule cannot exist without cost element<br>- **Reduced flexibility** - change orders affect entire cost element<br>- **Version coupling** - baseline linked to specific cost element version |
| Complexity      | **Low** - remove branching, add version FK |
| Maintainability | **Excellent** - simple parent-child relationship |
| Performance     | **Excellent** - direct join query (<100ms) |

---

### Option 4: Baseline Versioning Within Cost Element (Embedded)

**Architecture & Design:**

Embed schedule baseline data directly in cost element, with versioning tracked within cost element history.

**Data Model Changes:**
1. Add schedule baseline fields to `CostElement` entity
2. Add `schedule_baseline_version` field to track changes
3. Remove independent `ScheduleBaseline` entity
4. Use cost element versioning to track schedule changes

**Service Layer Changes:**
1. Add schedule fields to `CostElementService.update()` method
2. Add `get_schedule_history(cost_element_id, branch)` method
3. Remove `ScheduleBaselineService` entirely
4. Merge schedule validation into cost element service

**API Layer Changes:**
1. Include schedule fields in cost element DTOs
2. PUT `/api/v1/cost-elements/{id}` - includes schedule fields
3. GET `/api/v1/cost-elements/{id}/schedule-history` - version history
4. Remove all independent schedule baseline endpoints

**PV Calculation Logic:**
```python
async def calculate_pv(
    cost_element_id: UUID,
    control_date: datetime,
    branch: str = "main"
) -> Decimal:
    # Get cost element with schedule data
    cost_element = await cost_element_service.get_current(
        root_id=cost_element_id,
        branch=branch
    )

    if not cost_element.schedule_start_date or not cost_element.schedule_end_date:
        raise NoScheduleBaselineError(cost_element_id)

    # Calculate planned completion % from embedded schedule
    planned_pct = calculate_planned_completion(
        start_date=cost_element.schedule_start_date,
        end_date=cost_element.schedule_end_date,
        control_date=control_date,
        progression_type=cost_element.schedule_progression_type
    )

    # PV = BAC × % Planned
    return cost_element.budget_amount * Decimal(str(planned_pct))
```

**Migration Strategy:**
1. Add schedule columns to `cost_elements` table
2. Migrate existing schedule baseline data into cost elements
3. Drop `schedule_baselines` table entirely
4. Update all queries to use embedded schedule data
5. Update frontend to use cost element endpoints

**UX Design:**

- Schedule fields in cost element form
- No separate schedule management
- Schedule history accessible via cost element version history
- Simpler UI - one form for all cost element data

**Branching Behavior:**

- Schedule branches with cost element automatically
- No independent schedule branching
- Version history includes schedule changes
- Change orders affect entire cost element (including schedule)

**Implementation:**

**Key Technical Details:**

1. **Data Model**:
```python
class CostElement(EntityBase, VersionableMixin, BranchableMixin):
    """Cost Element with embedded schedule baseline."""

    # ... existing fields ...

    # Embedded schedule baseline fields
    schedule_start_date: Mapped[datetime] = mapped_column(nullable=True)
    schedule_end_date: Mapped[datetime] = mapped_column(nullable=True)
    schedule_progression_type: Mapped[str] = mapped_column(
        PROGRESSION_TYPE_ENUM,
        nullable=True,
        default="LINEAR"
    )
    schedule_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_baseline_version: Mapped[int] = mapped_column(default=0)
```

2. **Service Update**:
```python
class CostElementService(BranchableService[CostElement]):
    async def update_schedule(
        self,
        root_id: UUID,
        schedule_updates: dict,
        actor_id: UUID,
        branch: str = "main"
    ) -> CostElement:
        # Increment schedule version
        current = await self.get_current(root_id, branch)
        schedule_updates["schedule_baseline_version"] = (
            current.schedule_baseline_version + 1
        )

        # Update cost element with new schedule
        return await self.update(
            root_id=root_id,
            updates=schedule_updates,
            actor_id=actor_id,
            branch=branch
        )
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - **Maximum simplicity** - no separate entity<br>- **Atomic updates** - schedule and cost element update together<br>- **No ambiguity** - always use embedded schedule<br>- **Zero migration of relationships** - just move columns<br>- **Best performance** - no joins required |
| Cons            | - **Loses schedule independence** - cannot manage separately<br>- **Bloats cost element** - mixing concerns<br>- **Harder to query** - schedule-specific queries become complex<br>- **Version coupling** - any schedule change creates new cost element version<br>- **No separate schedule audit trail** - mixed with cost element history |
| Complexity      | **Low** - collapse entity, move fields |
| Maintainability | **Fair** - simple but violates SRP |
| Performance     | **Excellent** - single table query (<50ms) |

---

## Comparison Summary

| Criteria           | Option 1: Branchable 1:1 | Option 2: Active Flag | Option 3: Non-Branchable Child | Option 4: Embedded |
| ------------------ | ------------------------- | ---------------------- | ------------------------------ | ------------------ |
| **Development Effort** | Medium (migration + FK) | Low (add flag) | Low (remove branching) | Low (collapse entity) |
| **UX Quality** | Excellent (clear, single baseline) | Good (but requires active indicator) | Good (embedded) | Fair (bloats form) |
| **Flexibility** | Excellent (branching for what-if) | Good (multiple baselines) | Fair (tied to cost element) | Poor (no independence) |
| **Data Integrity** | Excellent (enforced 1:1) | Good (unique constraint) | Excellent (FK constraint) | Excellent (same table) |
| **Migration Complexity** | High (resolve duplicates) | Low (add flag) | Medium (remove branching) | Medium (move columns) |
| **Performance** | Excellent (<100ms) | Good (~100ms) | Excellent (<100ms) | Excellent (<50ms) |
| **Architectural Alignment** | Excellent (EVCS pattern) | Good (EVCS pattern) | Fair (child entity) | Poor (violates SRP) |
| **What-If Support** | Excellent (branches) | Excellent (multiple baselines) | Fair (via cost element) | Poor (via cost element) |
| **PV Calculation Clarity** | Excellent (unambiguous) | Good (filter by active) | Excellent (direct link) | Excellent (embedded) |
| **Audit Trail** | Excellent (EVCS versioning) | Good (multiple baselines) | Good (version history) | Fair (mixed history) |
| **Best For** | Production use (EVCS-aligned) | Transitional (preserve history) | Simpler systems (no independent schedule) | Minimum viable product |

---

## Recommendation

**I recommend Option 1: One Schedule Baseline Per Cost Element (Branchable)** because:

### Rationale

1. **Aligns with EVCS Architecture**:
   - Leverages existing `BranchableMixin` and `BranchableService` infrastructure
   - Consistent with how CostElement, Project, and WBE are implemented
   - Follows ADR-005 bitemporal versioning pattern
   - No new infrastructure required

2. **Solves the Core Problem**:
   - **Eliminates ambiguity in PV calculations** - there's only one baseline to use
   - **Clear what-if scenario support** - branches provide isolated experiments
   - **Intuitive for users** - one schedule per cost element, branch selector controls context

3. **Maintains Flexibility**:
   - **Change orders** can modify schedule in isolation via branches
   - **Impact analysis** via merged view service
   - **Historical comparison** via baseline snapshots (Section 10)
   - **No loss of functionality** - all requirements met

4. **Performance & Scalability**:
   - **Single query for PV calculation** (<100ms target)
   - **Efficient branching** - uses existing EVCS infrastructure
   - **Scalable to 50 projects × 20 WBEs × 15 cost elements**

5. **Data Integrity**:
   - **Enforced 1:1 relationship** via database constraints
   - **Complete audit trail** via EVCS versioning
   - **No orphaned baselines** - FK constraint ensures referential integrity

6. **Future-Proof**:
   - **Easy to extend** - can add schedule-specific fields later
   - **Independent lifecycle** - schedule can have its own business logic
   - **Clear separation of concerns** - schedule is not bloating cost element

### Trade-offs to Consider

1. **Migration Complexity**:
   - Need to resolve existing duplicate baselines
   - Must archive historical baselines (or soft delete)
   - Frontend changes required for new API structure

2. **Loss of Multiple Active Scenarios**:
   - Cannot have multiple "active" baselines in same branch
   - Users must create branches for what-if scenarios
   - Slightly more workflow steps for scenario analysis

3. **Tighter Coupling**:
   - 1:1 relationship means baseline cannot exist without cost element
   - Cascade delete risk (mitigated with soft delete)
   - Cannot share baselines across cost elements

### Alternative Consideration

**Choose Option 2 (Active Flag) if:**
- You need to preserve all existing historical baselines without archiving
- Migration complexity is a major concern
- You want a transitional approach before full 1:1 enforcement
- You need to support multiple "active" scenarios in the same branch

**Choose Option 3 (Non-Branchable Child) if:**
- Schedule should never be modified independently of cost element
- You want simpler model without independent branching
- Change orders always affect entire cost element anyway
- You're willing to lose independent schedule branching

**Choose Option 4 (Embedded) if:**
- You need minimum viable product quickly
- Schedule is always modified with cost element
- You want maximum performance (no joins)
- You're willing to violate single responsibility principle

---

## Decision Questions

1. **Is preserving all existing historical schedule baselines a requirement?**
   - If yes → Option 2 (Active Flag) preserves all baselines
   - If no → Option 1 (1:1 Branchable) can archive duplicates

2. **How important is independent schedule branching (separate from cost element)?**
   - If critical → Option 1 (1:1 Branchable) or Option 2 (Active Flag)
   - If not needed → Option 3 (Non-Branchable) or Option 4 (Embedded)

3. **What is the migration complexity tolerance?**
   - Low tolerance → Option 2 (Active Flag) or Option 4 (Embedded)
   - Medium tolerance → Option 1 (1:1 Branchable)
   - High tolerance → Option 3 (Non-Branchable Child)

4. **Should change orders be able to modify schedule independently of cost element budget?**
   - If yes → Option 1 (1:1 Branchable) or Option 2 (Active Flag)
   - If no → Option 3 (Non-Branchable) or Option 4 (Embedded)

5. **Is clarity of PV calculation (unambiguous baseline) more important than flexibility?**
   - If yes → Option 1 (1:1 Branchable), Option 3 (Non-Branchable), or Option 4 (Embedded)
   - If no → Option 2 (Active Flag) provides more flexibility

---

## References

### Architecture Documentation
- [ADR-005: Bitemporal Versioning Pattern](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [Bounded Contexts](/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md)
- [System Map](/home/nicola/dev/backcast_evs/docs/02-architecture/00-system-map.md)

### Functional Requirements
- [Functional Requirements - Section 6.1.1](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#611-cost-element-schedule-baseline) - Cost Element Schedule Baseline
- [Functional Requirements - Section 8](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#8-change-order-management-requirements) - Change Order Management
- [Functional Requirements - Section 10](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#10-baseline-management-requirements) - Baseline Management
- [Functional Requirements - Section 12.2](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#122-core-evm-metrics) - EVM Calculations (PV)
- [EVM Requirements](/home/nicola/dev/backcast_evs/docs/01-product-scope/evm-requirements.md) - Complete EVM specification

### Code References
- [ScheduleBaseline Model](/home/nicola/dev/backcast_evs/backend/app/models/domain/schedule_baseline.py) - Current implementation
- [ScheduleBaselineService](/home/nicola/dev/backcast_evs/backend/app/services/schedule_baseline_service.py) - Current service
- [CostElement Model](/home/nicola/dev/backcast_evs/backend/app/models/domain/cost_element.py) - Parent entity
- [BranchableService](/home/nicola/dev/backcast_evs/backend/app/core/branching/service.py) - Base class for branching
- [Versioning Commands](/home/nicola/dev/backcast_evs/backend/app/core/versioning/commands.py) - Generic command pattern

---

**Next Steps:**

Upon approval of this recommendation, proceed to **PLAN phase** to create detailed implementation plan including:
1. Database migration scripts
2. Service layer modifications
3. API endpoint changes
4. Frontend component updates
5. Test plan (unit, integration, E2E)
6. Rollback strategy
