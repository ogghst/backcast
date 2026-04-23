# ANALYSIS: E06-U07 Merged View Showing Main + Branch Changes

**Iteration**: E06-U07
**Date**: 2026-04-23
**Status**: 🔄 In Progress
**Analyst**: Claude (PDCA Orchestrator)

---

## Phase 1: Requirements Clarification

### User Intent
Implement a merged view that shows the combined state of main branch + branch changes, allowing users to preview the result of merging a change order before actually executing the merge.

### Functional Requirements
From product backlog [`E06-U07`](../product-backlog.md#e06-u07-merged-view-showing-main--branch-changes--⏸️-deferred):

- Show main + branch changes combined
- Highlight conflicts
- Preview of merged state
- Support decision-making for change order approval

### User Stories
**As a** Project Manager reviewing a change order  
**I want to** see a preview of how the merged state will look  
**So that** I can understand the impact before approving the merge

### Non-Functional Requirements
- **Performance**: Response time < 2 seconds for typical projects
- **Accuracy**: Must show exact post-merge state
- **Clarity**: Conflicts must be visually distinct
- **Maintainability**: Follow existing EVCS patterns

### Constraints
- Must work with existing EVCS temporal querying
- Must integrate with current change order workflow
- Must respect branch isolation patterns
- Backend must be branchable (temporal versioning)

---

## Phase 2: Context Discovery

### 2.1 Documentation Review

**Product Scope Analysis**:
- Epic E006 (Branching & Change Order Management) is complete except for this story
- Previous phases implemented: change orders, auto-branch creation, in-branch editing, impact analysis, merge workflow
- This story fills the preview gap before merge execution

**Architecture Context**:
- **Bounded Context**: Change Order Management (Epic E06)
- **Core Patterns**: EVCS with branchable entities, temporal queries, TimeMachine control
- **Existing Services**: `ChangeOrderService`, `BranchableService`, merge orchestration
- **Frontend**: Change order workflow components, impact analysis views

**Project Plan Context**:
- Recent completions: E06-U06 (branch locking), E06-U06-UI (workflow-aware status)
- Current focus: Quality and UX improvements for change order workflow
- Dependencies: E06-U03 (in-branch editing) ✅ complete, E06-U05 (merge) ✅ complete

### 2.2 Codebase Analysis

**Backend Analysis**:

Existing merge functionality:
- `ChangeOrderService.merge_change_order()` - executes actual merge
- `BranchableService._detect_merge_conflicts()` - conflict detection
- Impact comparison: `get_branch_comparison()` returns main vs branch diff

Key entities involved:
- `ChangeOrder` - workflow state, branch_id
- `Project`, `WorkBreakdownElement`, `CostElement` - all branchable
- Temporal versioning with `TSTZRANGE`

**Frontend Analysis**:

Existing components:
- `ChangeOrderWorkflowSection` - workflow actions (merge, approve)
- Impact analysis routes: `/projects/:projectId/change-orders/:id/impact`
- Side-by-side diff components exist for comparison
- TimeMachineContext integration for temporal queries

**Gap Analysis**:
- ✅ Can compare main vs branch (impact analysis)
- ✅ Can detect conflicts
- ✅ Can execute merge
- ❌ Missing: Preview of merged state before execution
- ❌ Missing: Visual distinction of conflicts in merged view

---

## Phase 3: Solution Design

### Option 1: Backend Computed Merged State with Frontend Preview

#### Architecture & Design Patterns
- **Backend**: New API endpoint `GET /change-orders/{id}/merged-preview`
- **Service Layer**: `ChangeOrderService.preview_merge()` computes merged state
- **Computation**: In-memory merge of main + branch changes without persisting
- **Frontend**: New preview tab/section in change order detail view

#### User Experience Design
- **Access**: "Preview Merge" button in change order detail (available when branch has changes)
- **Display**: Tab-based layout with "Current", "Changes", "Preview" tabs
- **Visual Hierarchy**: 
  - Preview shows merged state with conflict highlighting
  - Green checkmarks for clean merges
  - Red warnings for conflicts
- **Navigation**: Breadcrumbs: Projects → Change Orders → [CO-123] → Preview

#### Technical Implementation
**Backend**:
- New endpoint: `GET /api/v1/change-orders/{id}/merged-preview`
- Service method: `preview_merge(change_order_id)` returns merged entities
- Algorithm:
  1. Fetch main branch entities at as_of date
  2. Fetch branch entities
  3. Apply branch changes on top of main (in-memory)
  4. Detect conflicts (same entity modified in both)
  5. Return merged state with conflict markers

**Frontend**:
- Component: `MergePreviewTab.tsx` - displays merged state
- Route: Add to existing change order detail page
- Reuse: `ProjectTree`, `WBETreeWidget` with merged data
- Highlighting: CSS classes for conflict markers

#### Trade-offs Analysis
| Aspect          | Assessment                                |
| --------------- | ----------------------------------------- |
| Pros            | Accurate preview, server-side computation, follows EVCS patterns |
| Cons            | Additional backend complexity, duplicate merge logic |
| Complexity      | Medium (backend) + Low (frontend)         |
| Maintainability | Good (reuses existing patterns)            |
| Performance     | Good (< 2s for typical projects)          |

---

### Option 2: Frontend-Side Merge Computation

#### Architecture & Design Patterns
- **Backend**: Expose main and branch data separately (already exists)
- **Frontend**: Client-side merge computation using impact analysis data
- **State**: Merged state computed in React state/memo
- **Display**: Same preview UI as Option 1

#### User Experience Design
- **Identical to Option 1**: Same user workflow, same visual layout
- **Loading State**: Client-side computation might show spinner

#### Technical Implementation
**Backend**:
- No new endpoints (reuse existing comparison endpoint)
- Optimize: `GET /change-orders/{id}/impact` returns structured diff

**Frontend**:
- Merge computation logic in `useMergePreview()` hook
- Algorithm: Combine main entities + branch changes in memory
- Conflict detection: Compare entity versions in frontend
- Display: Same preview UI as Option 1

#### Trade-offs Analysis
| Aspect          | Assessment                                |
| --------------- | ----------------------------------------- |
| Pros            | No backend changes, faster iteration, client-side flexibility |
| Cons            | Less accurate (complex business logic in JS), performance issues with large datasets, security concerns |
| Complexity      | Low (backend) + Medium (frontend)         |
| Maintainability | Fair (business logic in frontend)         |
| Performance     | Poor for large projects (client-side load) |

---

### Option 3: Database Temporary Merge Branch

#### Architecture & Design Patterns
- **Backend**: Create temporary merge branch in database
- **Service**: Copy main → temp branch, apply changes, query merged state
- **Lifecycle**: Temp branch deleted after preview session
- **Frontend**: Query temp branch like any other branch

#### User Experience Design
- **Identical to Option 1**: Same user workflow
- **Session**: Preview creates temporary session, auto-cleanup after 5 minutes

#### Technical Implementation
**Backend**:
- Endpoint: `POST /change-orders/{id}/create-preview-branch`
- Service: Create `PREVIEW-{change_order_id}` branch
- Algorithm: Database-level merge operations
- Cleanup: Background task to delete old preview branches

**Frontend**:
- Switch TimeMachineContext to preview branch
- Reuse all existing components (they already support branches)
- No special merge display logic

#### Trade-offs Analysis
| Aspect          | Assessment                                |
| --------------- | ----------------------------------------- |
| Pros            | Reuses all existing components, true database state, accurate |
| Cons            | Database pollution, cleanup complexity, performance overhead, branch name conflicts |
| Complexity      | High (backend branch management)           |
| Maintainability | Poor (cleanup edge cases, temp state management) |
| Performance     | Fair (branch creation overhead)            |

---

## Phase 4: Recommendation & Decision

### Comparison Summary

| Criteria           | Option 1 (Backend) | Option 2 (Frontend) | Option 3 (Temp Branch) |
| ------------------ | ------------------ | ------------------- | ---------------------- |
| Development Effort | Medium             | Low                 | High                   |
| UX Quality         | High               | High                | High                   |
| Flexibility        | Fair               | High                | Low                    |
| Performance        | Good               | Poor (large sets)   | Fair                   |
| Maintainability    | Good               | Fair                | Poor                   |
| Accuracy           | High               | Medium              | High                   |

### Recommendation

**I recommend Option 1 (Backend Computed Merged State)** because:

1. **Architectural Alignment**: Follows EVCS patterns with server-side business logic
2. **Performance**: Backend computation is optimized for database queries
3. **Accuracy**: Server-side merge logic ensures business rule compliance
4. **Maintainability**: Centralized merge logic, easier to test and debug
5. **Security**: No sensitive business logic exposed to client
6. **User Experience**: Fast, accurate preview with proper conflict detection

**Implementation Priority**: This is the right balance of complexity, maintainability, and user value.

### Alternative Consideration

Choose **Option 2 (Frontend)** only if:
- Development speed is critical and dataset sizes are small
- Team is more comfortable with React than backend logic
- Preview accuracy is less critical than development velocity

Choose **Option 3 (Temp Branch)** only if:
- You need to support complex merge scenarios that require full database state
- Performance is acceptable with branch creation overhead
- You can invest in robust cleanup automation

### Questions for Decision

1. **Dataset Size**: What's the typical number of entities per project? (If < 100, Option 2 becomes viable)
2. **Merge Complexity**: Are there complex business rules in merge logic? (If yes, Option 1 or 3)
3. **Development Timeline**: Is this needed ASAP or can we invest in proper backend implementation? (ASAP → Option 2, Proper → Option 1)
4. **Performance Requirements**: Is < 2 second response time critical? (If yes, avoid Option 2 for large projects)

---

## Decision Required

**Please select an option (1, 2, or 3) or provide feedback on the analysis.**

Once approved, this analysis will proceed to the PLAN phase to create detailed implementation tasks.

**Current Status**: Awaiting user decision on recommended approach.

---

## Documentation References

- Product Backlog: [`E06-U07`](../product-backlog.md#e06-u07-merged-view-showing-main--branch-changes--⏸️-deferred)
- Epic E006: Branching & Change Order Management
- EVCS Architecture: `docs/02-architecture/backend/contexts/evcs-core/`
- Change Order Service: `backend/app/services/change_order_service.py`
- Frontend Components: `frontend/src/features/change-orders/`