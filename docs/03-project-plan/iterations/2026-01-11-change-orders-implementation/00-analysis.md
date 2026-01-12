# Change Management Implementation - Analysis

**Date Created:** 2026-01-11
**Epic:** E006 (Branching & Change Order Management)
**Status:** Analysis Phase
**Related Docs:**
- [Change Management User Stories](../../../01-product-scope/change-management-user-stories.md)
- [Product Backlog](../../product-backlog.md)
- [EVCS Architecture](../../../02-architecture/backend/contexts/evcs-core/)

---

## Request Analysis: Implement Change Management System

### Clarified Requirements

The user requests implementation of the Change Management system as specified in the product documentation. The system must:

1. **Support Change Order Lifecycle**: Draft → Submitted → Approved/Rejected → Implemented → Archived
2. **Automatic Branch Creation**: Each Change Order (CO) spawns a dedicated branch (`co-{id}`)
3. **Isolated Development**: Users modify project data (WBEs, Cost Elements, Budgets) in the CO branch without affecting main
4. **Impact Analysis**: Visual comparison between CO branch and main branch before approval
5. **Merge Implementation**: Approved COs merge changes into target branch
6. **Branch Management**: Lock/unlock, archive, and delete branches
7. **View Modes**: Toggle between "Isolated" (changes only) and "Merged" (full project context) views

**Key Assumptions:**
- EVCS Core (bitemporal versioning + branching) is already implemented
- Project, WBE, and CostElement entities are fully branchable
- Basic ChangeOrderVersion model exists but needs workflow completion
- Frontend has BranchSelector and TimeMachine controls already

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories from [change-management-user-stories.md](../../../01-product-scope/change-management-user-stories.md):**

| Story | Description | Priority |
|-------|-------------|----------|
| 3.1 | Creation of Change (and Branch Generation) | Critical |
| 3.2 | Performing Work on a Change | High |
| 3.3 | Updating Change Metadata | High |
| 3.4 | Reviewing Change Impacts (Impact Analysis) | High |
| 3.5 | Submitting the Change | High |
| 3.6 | Accepting the Change (Merge) | Critical |
| 3.7 | Rejecting or Deleting the Change | Critical |
| 3.8 | Toggling View Modes (Isolated vs Merged) | Medium |

**Relevant Backlog Items from [product-backlog.md](../../product-backlog.md):**

| Item | Story Points | Ready for Iteration |
|------|--------------|---------------------|
| E06-U01: Create Change Orders | 5 | Yes |
| E06-U02: Automatic Branch Creation | 5 | No (blocked by U01) |
| E06-U03: Modify Entities in Branch | 8 | No (blocked by U02) |
| E06-U04: Compare Branch to Main | 8 | No (blocked by U01, U03-U04) |
| E06-U05: Merge Approved Change Orders | 13 | No (blocked by U01, U04) |
| E06-U06: Lock/Unlock Branches | 3 | No (blocked by U02) |
| E06-U07: Merged View Showing Main + Branch | 5 | No (blocked by U03) |
| E06-U08: Delete/Archive Branches | 3 | No (blocked by U05) |

**Total Effort:** 50 story points across 8 user stories

### Architecture Context

**Bounded Contexts Involved:**
1. **E006 (Branching & Change Order Management)** - Primary context
2. **E003 (Entity Versioning System)** - Provides EVCS Core foundation
3. **E004 (Project Structure Management)** - Projects, WBEs, Cost Elements
4. **E008 (EVM Calculations & Reporting)** - Impact metrics (BAC, EAC, margins)

**Existing Patterns:**
- **Protocol-Based Architecture**: `SimpleEntityProtocol`, `VersionableProtocol`, `BranchableProtocol`
- **Generic Services**: `TemporalService[T]`, `BranchableService[T]`
- **Command Pattern**: Create/Update/Delete commands with version chaining
- **RBAC Integration**: Role-based access control throughout
- **API Conventions**: Standardized response patterns with `ApiResponse` wrapper

### Codebase Analysis

#### Backend

**Existing Related APIs:**

| File | Description | Status |
|------|-------------|--------|
| `backend/app/api/routes/change_orders.py` | Change Order CRUD endpoints | Partial - needs workflow |
| `backend/app/services/change_order.py` | Change Order business logic | Partial - needs completion |
| `backend/app/api/routes/projects.py` | Project CRUD | Complete |
| `backend/app/api/routes/wbes.py` | WBE CRUD | Complete |
| `backend/app/api/routes/cost_elements.py` | Cost Element CRUD | Complete |
| `backend/app/core/branching/service.py` | Branch management | Complete |
| `backend/app/core/versioning/service.py` | Temporal versioning | Complete |

**Data Models:**

| Model | File | Capabilities |
|-------|------|--------------|
| `ProjectVersion` | `models/domain/project.py` | Versioned + Branchable |
| `WBEVersion` | `models/domain/wbe.py` | Versioned + Branchable |
| `CostElementVersion` | `models/domain/cost_element.py` | Versioned + Branchable |
| `ChangeOrderVersion` | `models/domain/change_order.py` | Versioned + Branchable |
| `Branch` | `models/domain/branch.py` | Simple (non-versioned) |

**Similar Patterns:**
- All entities use `BranchableMixin` for branch isolation
- Repository layer provides `get_by_branch()` and `get_active_version()` methods
- Services inherit from `BranchableService[T]` for automatic branching support

#### Frontend

**Comparable Components:**

| Component | File | Reusability |
|-----------|------|-------------|
| `BranchSelector` | `components/time-machine/BranchSelector.tsx` | High - use as-is |
| `TimelineSlider` | `components/time-machine/TimelineSlider.tsx` | High - use as-is |
| `TimeMachineStore` | `stores/useTimeMachineStore.ts` | High - extend for CO context |
| `StandardTable` | `components/ui/StandardTable.tsx` | High - for CO list |
| `VersionHistoryDrawer` | `components/versioning/VersionHistoryDrawer.tsx` | Medium - adapt for CO history |
| `ProjectForm` | `features/projects/ProjectForm.tsx` | Medium - pattern reference |

**State Management:**
- **Server State**: TanStack Query for API data (existing pattern)
- **Client State**: Zustand for UI state (needs new CO workflow store)
- **Routing**: React Router v6 (needs CO routes)

**Routing Structure:**
```
/current: /projects, /projects/:id, /wbes, /wbes/:id, /cost-elements, /cost-elements/:id
/needed: /change-orders, /change-orders/:id, /change-orders/:id/impact
```

---

## Solution Options

### Option 1: Phased Rollout (Incremental Delivery)

**Architecture & Design:**
- **Phase 1**: Core Change Order CRUD + Auto-branch creation (E06-U01, U02)
- **Phase 2**: In-branch editing + Branch management (E06-U03, U06, U07, U08)
- **Phase 3**: Impact analysis engine (E06-U04)
- **Phase 4**: Merge workflow completion (E06-U05)

**Component Structure:**
```
Backend:
- app/services/change_order.py (extend existing)
- app/services/impact_analysis.py (new)
- app/api/routes/change_orders.py (extend)
- app/api/routes/impact_analysis.py (new)

Frontend:
- src/features/change-orders/
  - components/ChangeOrderList.tsx
  - components/ChangeOrderForm.tsx
  - components/ChangeOrderDetail.tsx
  - components/ImpactAnalysisDashboard.tsx
  - hooks/useChangeOrders.ts
```

**UX Design:**
- **Phase 1**: Simple CO list and create form, automatic branch switching prompt
- **Phase 2**: Branch isolation indicators, view mode toggle, lock/unlock controls
- **Phase 3**: Visual impact dashboard with charts (waterfall, S-curves)
- **Phase 4**: Merge confirmation modal, rollback capability

**Implementation:**
- Extend existing `ChangeOrderService` with workflow methods
- Add `ImpactAnalysisService` for branch comparison
- Create new change order feature module in frontend
- Reuse existing BranchSelector with CO status indicators
- Leverage existing chart library (if any) or add Recharts/Chart.js

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | - Early value delivery, incremental validation<br>- Lower risk per phase<br>- Easier to adjust based on feedback |
| Cons | - Longer total timeline<br>- Potential rework between phases<br>- Requires careful dependency management |
| Complexity | Medium |
| Maintainability | Good |
| Performance | Good (incremental optimization) |

---

### Option 2: Full Stack Implementation (Monolithic Sprint)

**Architecture & Design:**
- Single focused sprint implementing all 8 user stories
- Parallel development tracks: backend workflow + frontend UI
- Feature flags to enable capabilities as they complete

**Component Structure:**
```
Same as Option 1, but all implemented in one iteration

Additional:
- app/core/workflow/change_order_state_machine.py (new)
- src/features/change-orders/types/workflow.ts (new)
```

**UX Design:**
- Complete change management UI from day one
- Guided onboarding for first-time users
- Progressive disclosure of advanced features

**Implementation:**
- All backend endpoints implemented upfront
- Frontend components built in order of dependency
- Integration testing after all components complete
- Single comprehensive release

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | - Complete feature set available sooner<br>- Consistent UI/UX across all capabilities<br>- Single testing/release cycle |
| Cons | - Higher upfront risk<br>- Larger code review burden<br>- Delayed value if blocked |
| Complexity | High |
| Maintainability | Good (coherent design) |
| Performance | Good (single optimization pass) |

---

### Option 3: Workflow-First (Backend-Driven)

**Architecture & Design:**
- Prioritize backend workflow engine and state machine
- Build minimal frontend UI for workflow progression
- Add rich visualization (impact analysis) in follow-up

**Component Structure:**
```
Backend Priority:
1. ChangeOrderStateMachine (state transitions, validation)
2. MergeOrchestrator (conflict resolution, rollback)
3. BranchLockingService (access control)

Frontend MVP:
- ChangeOrderList with status badges
- Simple action buttons (Submit, Approve, Reject)
- Basic merge confirmation dialog
```

**UX Design:**
- Functional workflow over visual polish
- CLI-style operations via UI initially
- Impact analysis as spreadsheet-style diff initially

**Implementation:**
- Focus on robust state machine and data integrity
- Use existing BranchSelector as primary UI
- Add status-based action enablement
- Impact analysis as simple data tables first

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | - Ensures data integrity first<br>- Lower UI development cost initially<br>- Faster backend validation |
| Cons | - Poor initial UX (workflow without visuals)<br>- May require UI overhaul later<br>- Risk of "good enough" mindset |
| Complexity | Low (backend), Low (UI MVP) |
| Maintainability | Fair (UI debt likely) |
| Performance | Good (minimal frontend overhead) |

---

## Comparison Summary

| Criteria | Option 1: Phased | Option 2: Full Stack | Option 3: Workflow-First |
|----------|------------------|----------------------|--------------------------|
| Development Effort | ~50 pts (4 sprints) | ~50 pts (2 sprints, parallel) | ~35 pts (2 sprints) |
| Time to First Value | Sprint 1 (CRUD) | Sprint 2 (all features) | Sprint 1 (workflow) |
| UX Quality | Good (iterative polish) | Excellent (coherent design) | Fair (functional initially) |
| Risk | Low (incremental) | Medium (large batch) | Low (backend focused) |
| Flexibility | High (pivot between phases) | Medium (must complete all) | Medium (UI debt) |
| Best For | Teams wanting incremental validation | Experienced team, clear requirements | Backend-focused teams |

---

## Recommendation

**I recommend Option 1: Phased Rollout** for the following reasons:

1. **Proven Pattern**: The project has successfully used incremental delivery (Sprint 2/3 hybrid approach)
2. **Dependency Management**: Clear dependency chain in backlog (U02 → U03 → U04 → U05) naturally phases the work
3. **Risk Mitigation**: Each phase delivers value and can be validated before proceeding
4. **Team Rhythm**: Aligns with existing sprint cadence and testing practices
5. **Stakeholder Communication**: Regular progress updates with working features

**Phase Breakdown:**

| Phase | Items | Points | Deliverable |
|-------|-------|--------|-------------|
| 1 | E06-U01, U02 | 10 | Create CO + Auto-branch |
| 2 | E06-U03, U06, U07, U08 | 24 | Branch management + In-branch editing |
| 3 | E06-U04 | 8 | Impact analysis visualization |
| 4 | E06-U05 | 13 | Merge workflow |

**Alternative consideration:** Choose **Option 2** if:
- Team has parallel frontend/backend capacity
- Stakeholders need complete feature set quickly
- Risk tolerance is higher

---

## Questions for Decision

1. **Team Capacity**: Do we have parallel frontend/backend developers, or should we sequence the work?

2. **Stakeholder Timeline**: Is there urgency to deliver the complete change management workflow, or is incremental delivery acceptable?

3. **Visualization Priority**: How critical is the visual impact analysis (charts/graphs) vs. tabular data comparison?

4. **Testing Strategy**: Should we implement automated E2E testing for the complete workflow before release, or test incrementally?

5. **Feature Flags**: Do we want the ability to enable change management per-project, or should it be system-wide from day one?

---

## Next Steps

Once this analysis is approved:

1. **Create iteration plan** with detailed tasks for Phase 1
2. **Set up database migration** for any new ChangeOrderVersion fields
3. **Define API contracts** for new endpoints
4. **Create frontend route structure** for change orders
5. **Set up testing strategy** for workflow state transitions

**Approval required from:** Product Owner, Tech Lead

---

**Document Status:** Ready for Review
**Next Document:** `01-plan.md` (after approval)
