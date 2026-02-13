# Request Analysis: Time Machine Component for Project Time Travel Navigation

**Created:** 2026-01-09  
**Status:** ✅ Approved  
**Selected Option:** Option 3 - Header Compact + Expandable Detail (Hybrid)

---

## User Decisions

| Question         | Decision                              |
| ---------------- | ------------------------------------- |
| Scope of events  | Project-level events only             |
| Branch support   | Required in Phase 1                   |
| Persistence      | LocalStorage sufficient (per-project) |
| Edit mode        | UI permits edits on historical view   |
| Timeline markers | Branch creations and merges only      |

**Additional Recommendations (Approved):**

- Make component flexible to display further event types in future
- Invalidate all fetched data when a new date is selected
- Document how APIs handle the selected control date (`as_of` parameter)

---

## Clarified Requirements

### User Intent

- Allow project managers and stakeholders to "time travel" through project history
- Visualize how project data (and all child entities: WBEs, Cost Elements) evolved over time
- Support the core product vision of "Git-style versioning with time-travel queries"

### Functional Requirements

1. **Timeline Display:** Show a visual timeline from project start_date to end_date (or current date)
2. **Zoom Capability:** Allow zoom in/out to navigate different time granularities (days, weeks, months)
3. **Point-in-Time Selection:** Click on timeline to select a specific moment
4. **Current Time Marker:** Display "now" indicator on the timeline
5. **Branch Markers:** Show branch creation/merge points on the timeline
6. **Context Awareness:** Only visible when a project is selected (in project detail pages)
7. **State Persistence:** Remember last selected time per project (localStorage)
8. **Global State Broadcast:** Inform frontend of selected time to filter all data queries
9. **Branch Selection:** Allow switching between branches (main, change orders)
10. **Edit Support:** UI allows edits even on historical views

### Non-Functional Requirements

- **Performance:** <200ms API response (existing standard)
- **Accessibility:** Keyboard navigation, screen reader support
- **Maintainability:** Follow existing patterns (TanStack Query, Zustand, Ant Design)
- **Extensibility:** Component architecture supports future event types

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories (from `docs/01-product-scope/vision.md`):**

- "Ability to time travel project at a specific date" (explicit requirement)
- "Git-Style Versioning: Complete entity history with time-travel queries"
- "Projects → WBEs → Cost Elements" hierarchy (all need time-travel support)

**Target Users:** Project Managers (daily), Department Managers, Project Controllers, Executives

### Architecture Context

**Bounded Contexts Involved:**

1. **EVCS Core (Backend)** - Bitemporal versioning framework with `get_as_of` queries
2. **Project & WBE Management (Backend)** - Time-travel capable entities
3. **Cost Element & Financial Tracking (Backend)** - Branch-aware temporal entities
4. **F0 Core Architecture (Frontend)** - App shell, AppLayout (header location)
5. **F1 State & Data Management (Frontend)** - Zustand stores, TanStack Query

**Existing Patterns:**

- **Bitemporal Model:** `valid_time` (business) + `transaction_time` (system) using PostgreSQL `TSTZRANGE`
- **Time Travel Query:** `TemporalService.get_as_of(entity_id, as_of: datetime)` already exists
- **State Management:** Zustand with immer for client state
- **Data Fetching:** TanStack Query with `createResourceHooks` pattern
- **UI Library:** Ant Design 6

### Codebase Analysis

**Backend - Existing APIs:**

- `GET /api/v1/projects/{project_id}/history` - Returns all versions
- `GET /api/v1/wbes/{wbe_id}/history` - Returns WBE version history
- `TemporalService.get_as_of(entity_id, as_of)` - Generic time-travel query

**Backend - Gap Analysis:**

- No endpoint exposing `as_of` parameter on list/detail endpoints
- No endpoint for branch metadata (when created, parent branch)
- Need to extend existing endpoints with `?as_of=` query parameter

**Frontend - Existing Components:**

- `AppLayout.tsx` (header location - currently shows only `UserProfile`)
- `useUserPreferencesStore.ts` (demonstrates Zustand pattern with persistence)
- `useAppStore.ts` (simple client state management)

---

## Selected Solution: Option 3 - Header Compact + Expandable Detail

### Architecture

**Tier 1 - Compact Header:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ [≡]    │ 📅 Jan 15, 2026 [▼] │ [Branch: main ▼]    │  UserProfile  │
└────────┴─────────────────────┴─────────────────────┴───────────────┘
```

**Tier 2 - Expanded View:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ [≡]    │ 📅 Jan 15, 2026 [▲] │ [Branch: main ▼]    │  UserProfile  │
├─────────────────────────────────────────────────────────────────────┤
│  ◀ ○────────●──────────────○─────────────○───●────────────○ ▶       │
│    Dec 1   Jan 1          Feb 1        Mar 1  NOW                   │
│            v1.0           BR-001        merge                       │
│                                                                      │
│  [Zoom: − +]  [Today]  [Quick: 1D | 1W | 1M | 3M | All]            │
└─────────────────────────────────────────────────────────────────────┘
```

### Components Structure

```
frontend/src/components/time-machine/
├── TimeMachineCompact.tsx     # Header display (Tier 1)
├── TimeMachineExpanded.tsx    # Expanded timeline (Tier 2)
├── TimelineSlider.tsx         # Ant Design Slider with custom marks
├── BranchSelector.tsx         # Dropdown for branch selection
├── QuickJumpButtons.tsx       # 1D, 1W, 1M presets
├── types.ts                   # TypeScript interfaces
└── hooks/
    ├── useTimeMachineStore.ts # Zustand state with localStorage
    ├── useProjectTimeline.ts  # TanStack Query for timeline data
    └── useAsOfContext.ts      # React Context for as_of propagation
```

### API Strategy (as_of Parameter Handling)

**Frontend → Backend Flow:**

1. User selects date/time in Time Machine → updates Zustand store
2. Store change triggers TanStack Query invalidation (`queryClient.invalidateQueries()`)
3. All data hooks include `as_of` from store in query key and API call
4. Backend receives `?as_of=2026-01-15T14:30:00Z` parameter

**Backend Implementation:**

```python
# Extend existing endpoints with optional as_of parameter
@router.get("/projects/{project_id}")
async def get_project(
    project_id: UUID,
    as_of: datetime | None = Query(None, description="Time travel to this timestamp"),
    service: ProjectService = Depends(get_project_service),
) -> ProjectRead:
    if as_of:
        project = await service.get_as_of(project_id, as_of)
    else:
        project = await service.get_by_root_id(project_id)
    ...
```

### State Management

```typescript
// useTimeMachineStore.ts
interface TimeMachineState {
  isExpanded: boolean;
  selectedTime: string | null; // ISO string, null = "now"
  selectedBranch: string;
  projectSettings: Record<
    string,
    {
      lastTime: string | null;
      lastBranch: string;
    }
  >;

  // Actions
  toggleExpanded: () => void;
  selectTime: (time: Date | null, projectId: string) => void;
  selectBranch: (branch: string, projectId: string) => void;
  resetToNow: (projectId: string) => void;
  getProjectSettings: (projectId: string) => {
    time: Date | null;
    branch: string;
  };
}
```

### Data Invalidation Strategy

When `selectedTime` or `selectedBranch` changes:

```typescript
// In useTimeMachineStore.ts
selectTime: (time, projectId) => {
  set((state) => { ... });

  // Invalidate all project-related queries
  queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
  queryClient.invalidateQueries({ queryKey: ['wbes'] });
  queryClient.invalidateQueries({ queryKey: ['cost-elements'] });
}
```

### Trade-offs

| Aspect          | Assessment                                                                         |
| --------------- | ---------------------------------------------------------------------------------- |
| Pros            | Progressive disclosure, minimal footprint, no external libs, existing API patterns |
| Cons            | Slider granularity limited, less visual than dedicated timeline library            |
| Complexity      | Medium                                                                             |
| Maintainability | Good                                                                               |
| Performance     | Good (uses existing endpoints with new parameter)                                  |

---

## Related Documentation

- [ADR-005: Bitemporal Versioning](../../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [Product Vision](../../01-product-scope/vision.md)
- [Coding Standards](../../02-architecture/coding-standards.md)
- [System Map](../../02-architecture/00-system-map.md)
