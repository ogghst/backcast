# High-Level Analysis: Project Detail Tabbed Layout Refactoring

## Business Objective

Convert the project detail page (`/projects/$id`) from a vertically stacked layout to a tabbed interface with four sections:
1. **Project Information** - Empty placeholder for future implementation
2. **Work Breakdown Elements** - Existing WBE table (default tab)
3. **Budget Summary** - Existing budget summary component
4. **Budget Timeline** - Existing budget timeline component with filters

This change will improve information organization and reduce vertical scrolling, making it easier for users to navigate between different aspects of project data.

---

## 1. CODEBASE PATTERN ANALYSIS

### Existing Implementation Patterns

**Pattern 1: Chakra UI Tabs Implementation (Settings Page)**

- **Location:** `frontend/src/routes/_layout/settings.tsx` (lines 36-49)
- **Pattern:** Uses Chakra UI compound component pattern with `Tabs.Root`, `Tabs.List`, `Tabs.Trigger`, and `Tabs.Content`
- **State Management:** Uses `defaultValue` prop for initial tab selection (no URL sync)
- **Structure:**
  ```tsx
  <Tabs.Root defaultValue="my-profile" variant="subtle">
    <Tabs.List>
      {tabs.map((tab) => (
        <Tabs.Trigger key={tab.value} value={tab.value}>
          {tab.title}
        </Tabs.Trigger>
      ))}
    </Tabs.List>
    {tabs.map((tab) => (
      <Tabs.Content key={tab.value} value={tab.value}>
        <tab.component />
      </Tabs.Content>
    ))}
  </Tabs.Root>
  ```
- **Status:** ✅ Working pattern, no URL synchronization

**Pattern 2: Current Project Detail Layout**

- **Location:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 283-354)
- **Pattern:** Vertically stacked sections using `Box` components with `mt={4}` spacing
- **Current Sections:**
  1. Breadcrumb navigation (lines 285-299)
  2. Project heading (line 300)
  3. Budget Summary (lines 301-303)
  4. Budget Timeline with filter (lines 304-345)
  5. Work Breakdown Elements table (lines 346-352)
- **State Management:**
  - Budget timeline filter state in component (lines 225-229)
  - Pagination state via URL search params (line 33-35, 155)
- **Status:** ✅ Functional but needs reorganization

**Pattern 3: URL Search Parameter Management**

- **Location:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 33-35, 66)
- **Pattern:** Uses Zod schema for search param validation via `validateSearch`
- **Current Usage:** Only `page` parameter for WBE table pagination
- **Pattern:**
  ```tsx
  const projectDetailSearchSchema = z.object({
    page: z.number().catch(1),
  })
  ```
- **Status:** ✅ Established pattern for URL state management

**Pattern 4: Child Route Handling**

- **Location:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 217-218, 279-281)
- **Pattern:** Uses `useRouterState` to detect child routes and conditionally render `<Outlet />`
- **Routes Detected:**
  - `/projects/$id/wbes/$wbeId` - WBE detail page
  - `/projects/$id/budget-timeline` - Full budget timeline page
- **Status:** ✅ Critical for maintaining nested route functionality

### Architectural Layers Identified

1. **UI Component Layer:** Chakra UI components (Tabs, Box, Container, Flex)
   - Imported from `@chakra-ui/react`
   - Uses compound component pattern for Tabs

2. **Routing Layer:** TanStack Router with file-based routing
   - Route definition: `createFileRoute("/_layout/projects/$id")`
   - Search param validation via Zod schemas
   - Child route detection via `useRouterState`

3. **State Management Layer:**
   - URL state: Search parameters (pagination)
   - Component state: Budget timeline filter state (useState)
   - Server state: React Query for data fetching

4. **Data Fetching Layer:**
   - React Query hooks with query options pattern
   - Separate query options functions for reusability
   - Conditional query enabling based on dependencies

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### Files Requiring Modification

**Primary File:**
- `frontend/src/routes/_layout/projects.$id.tsx`
  - **Changes Required:**
    1. Add `Tabs` import from `@chakra-ui/react`
    2. Extend `projectDetailSearchSchema` to include `tab` parameter (optional)
    3. Refactor `ProjectDetail` component layout to use tabs
    4. Move existing sections into tab content components
    5. Preserve child route detection logic (lines 217-218, 279-281)
    6. Maintain budget timeline filter state management

### Components Requiring No Changes

**Existing Components (Reusable As-Is):**
- `BudgetSummary` component - Accepts `level="project"` and `projectId` props
- `BudgetTimeline` component - Accepts `costElements` and `viewMode` props
- `BudgetTimelineFilter` component - Accepts `projectId`, `context`, and `onFilterChange` props
- `WBEsTable` component - Accepts `projectId` prop
- `AddWBE` component - Accepts `projectId` prop

### State Management Touchpoints

**URL Search Parameters:**
- **Current:** `page` parameter for WBE table pagination
- **Proposed Addition:** `tab` parameter for active tab selection (optional)
- **Schema Update:** Extend `projectDetailSearchSchema` to include optional `tab` field

**Component State:**
- **Budget Timeline Filter:** Currently in component state (lines 225-229)
- **Decision Required:** Keep in component state or move to URL params for shareability?

**React Query State:**
- **No Changes Required:** Existing query keys and dependencies remain valid
- **Note:** Budget timeline query depends on filter state, which should remain accessible

### Route Structure Considerations

**Current Route Structure:**
- `/projects/$id` - Project detail page (to be refactored)
- `/projects/$id/wbes/$wbeId` - WBE detail (child route)
- `/projects/$id/budget-timeline` - Full budget timeline (child route)

**Impact:**
- Child route detection logic (lines 279-281) must be preserved
- Tabbed layout should only render when on exact `/projects/$id` route
- Child routes should continue rendering via `<Outlet />` pattern

### Configuration Patterns

**No Configuration Changes Required:**
- No new environment variables
- No new service dependencies
- No routing configuration changes

---

## 3. ABSTRACTION INVENTORY

### Reusable Abstractions Available

**1. Chakra UI Tabs Component Pattern**

- **Source:** `frontend/src/routes/_layout/settings.tsx`
- **Pattern:** Compound component structure with value-based content rendering
- **Reusable Elements:**
  - `Tabs.Root` with `defaultValue` and optional `variant`
  - `Tabs.List` for tab trigger container
  - `Tabs.Trigger` with `value` prop for each tab
  - `Tabs.Content` with matching `value` prop for content
- **Usage:** Can be directly applied to project detail page

**2. URL Search Parameter Validation Pattern**

- **Source:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 33-35, 66)
- **Pattern:** Zod schema with `validateSearch` in route definition
- **Reusable Elements:**
  - Schema definition with `.catch()` for defaults
  - `Route.useSearch()` hook for accessing validated search params
- **Usage:** Can extend existing schema to include tab parameter

**3. Component State Management Pattern**

- **Source:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 225-229, 250-256)
- **Pattern:** `useState` for local component state with typed interfaces
- **Reusable Elements:**
  - Filter state interface definition
  - Handler functions for state updates
- **Usage:** Budget timeline filter state can remain in component state

**4. Query Options Pattern**

- **Source:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 39-44, 46-62)
- **Pattern:** Separate functions returning query options objects
- **Reusable Elements:**
  - `queryFn` and `queryKey` structure
  - Conditional enabling via `enabled` prop
- **Usage:** No changes needed, existing queries remain valid

**5. Child Route Detection Pattern**

- **Source:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 214-218, 279-281)
- **Pattern:** `useRouterState` with pathname selection and conditional `<Outlet />` rendering
- **Reusable Elements:**
  - Route detection via `location.includes()` checks
  - Conditional rendering pattern
- **Usage:** Must be preserved to maintain nested route functionality

### Test Utilities Available

**Manual Testing Patterns:**
- Tab navigation: Click tab triggers → verify content switches
- URL state: Verify tab parameter in URL (if implemented)
- Child routes: Verify WBE detail and budget timeline routes still work
- State persistence: Verify budget timeline filter state persists across tab switches

**No existing automated tests found for tab navigation** - would need to establish pattern if required.

---

## 4. ALTERNATIVE APPROACHES

### Approach 1: Simple Tabs with Component State (Recommended)

**Description:** Use Chakra UI Tabs with local component state for active tab, no URL synchronization. Budget timeline filter state remains in component state.

**Implementation Structure:**
```tsx
const [activeTab, setActiveTab] = useState("wbes") // default tab

<Tabs.Root value={activeTab} onValueChange={({ value }) => setActiveTab(value)}>
  <Tabs.List>
    <Tabs.Trigger value="info">Project Information</Tabs.Trigger>
    <Tabs.Trigger value="wbes">Work Breakdown Elements</Tabs.Trigger>
    <Tabs.Trigger value="summary">Budget Summary</Tabs.Trigger>
    <Tabs.Trigger value="timeline">Budget Timeline</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="info"><ProjectInfoPlaceholder /></Tabs.Content>
  <Tabs.Content value="wbes"><WBEsTable projectId={id} /></Tabs.Content>
  <Tabs.Content value="summary"><BudgetSummary ... /></Tabs.Content>
  <Tabs.Content value="timeline"><BudgetTimelineWithFilter ... /></Tabs.Content>
</Tabs.Root>
```

**Pros:**
- ✅ Simple implementation, follows existing settings.tsx pattern
- ✅ Minimal code changes
- ✅ No URL state management complexity
- ✅ Fast tab switching (no URL updates)
- ✅ Budget timeline filter state easily accessible

**Cons:**
- ⚠️ Tab selection not shareable via URL
- ⚠️ Tab selection lost on page refresh
- ⚠️ Browser back/forward doesn't navigate tabs

**Alignment:** ✅ **High alignment** - matches existing settings.tsx pattern exactly

**Estimated Complexity:** Low (2-3 hours)

**Risk Factors:** Low - well-established pattern in codebase

---

### Approach 2: URL-Synchronized Tabs with Search Parameters

**Description:** Use Chakra UI Tabs with URL search parameter synchronization. Active tab stored in URL via `tab` search parameter. Budget timeline filter state remains in component state.

**Implementation Structure:**
```tsx
// Extend search schema
const projectDetailSearchSchema = z.object({
  page: z.number().catch(1),
  tab: z.enum(["info", "wbes", "summary", "timeline"]).catch("wbes"),
})

// In component
const { tab } = Route.useSearch()
const navigate = useNavigate({ from: Route.fullPath })

<Tabs.Root
  value={tab}
  onValueChange={({ value }) => navigate({ search: (prev) => ({ ...prev, tab: value }) })}
>
  {/* Same structure as Approach 1 */}
</Tabs.Root>
```

**Pros:**
- ✅ Tab selection shareable via URL
- ✅ Tab selection persists on refresh
- ✅ Browser back/forward navigates tabs
- ✅ Better UX for bookmarking/sharing
- ✅ Follows existing URL state pattern (pagination)

**Cons:**
- ⚠️ More complex implementation (URL state management)
- ⚠️ Requires schema extension and navigation logic
- ⚠️ URL updates on every tab switch (may be unnecessary)

**Alignment:** ✅ **Medium alignment** - extends existing URL state pattern but adds complexity

**Estimated Complexity:** Medium (4-5 hours)

**Risk Factors:** Medium - requires careful URL state management to avoid conflicts with pagination

---

### Approach 3: Hybrid Approach - URL Sync Only for Budget Timeline

**Description:** Use component state for tabs, but sync budget timeline filter state to URL for shareability. Budget timeline is the only section that benefits from URL state (for filtering).

**Implementation Structure:**
```tsx
// Component state for tabs
const [activeTab, setActiveTab] = useState("wbes")

// URL state for budget timeline filters (when on timeline tab)
// Existing filter state management, but sync to URL when active

<Tabs.Root value={activeTab} onValueChange={({ value }) => setActiveTab(value)}>
  {/* Tab structure */}
</Tabs.Root>
```

**Pros:**
- ✅ Simple tab switching
- ✅ Budget timeline filters shareable (main use case)
- ✅ Less URL pollution (only filter params when needed)

**Cons:**
- ⚠️ More complex state management (two state sources)
- ⚠️ Inconsistent behavior (some tabs use URL, others don't)

**Alignment:** ⚠️ **Low alignment** - inconsistent patterns

**Estimated Complexity:** High (6+ hours)

**Risk Factors:** High - complex state synchronization logic

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### Architectural Principles

**Principles Followed:**
- ✅ **Component Composition:** Reuses existing components (BudgetSummary, BudgetTimeline, WBEsTable) without modification
- ✅ **Separation of Concerns:** UI structure change doesn't affect data fetching or business logic
- ✅ **Consistency:** Follows established Chakra UI Tabs pattern from settings.tsx
- ✅ **Type Safety:** Maintains TypeScript types for all props and state

**Potential Violations:**
- ⚠️ **URL State Consistency:** If using Approach 1 (component state), tabs won't be shareable, which may be inconsistent with other URL-state-driven features (pagination)

### Maintenance Burden

**Low Maintenance Areas:**
- Tab structure is straightforward and easy to modify
- Component reuse means changes to BudgetSummary, BudgetTimeline, etc. automatically reflect in tabs
- No new dependencies or complex abstractions

**Potential Maintenance Concerns:**
- **Tab State Management:** If using URL sync (Approach 2), need to maintain search schema and navigation logic
- **Child Route Handling:** Must preserve existing child route detection logic to avoid breaking nested routes
- **Budget Timeline Filter State:** Current component-state approach means filters reset on navigation away/back

### Testing Challenges

**Unit Testing:**
- Tab switching logic (if using component state)
- URL state synchronization (if using Approach 2)
- Search schema validation

**Integration Testing:**
- Tab content rendering for each tab
- Child route navigation still works (WBE detail, budget timeline full page)
- Budget timeline filter interactions within tab context

**E2E Testing:**
- Tab navigation flow
- Tab state persistence (if URL-synced)
- Navigation from tabbed view to child routes and back

### Future Considerations

**Potential Future Enhancements:**
1. **Project Information Tab:** Currently empty, will need implementation later
2. **Tab Persistence:** User preference for default tab (if not URL-synced)
3. **Deep Linking:** Direct navigation to specific tabs (requires URL sync)
4. **Tab Badges:** Show counts or indicators (e.g., number of WBEs, budget alerts)

**Migration Path:**
- Approach 1 can be upgraded to Approach 2 later if URL sync becomes needed
- Minimal refactoring required (just add URL state management)

### Risk Assessment

**Low Risk:**
- Component reuse means no breaking changes to existing components
- Tab structure is isolated to single file
- Child route handling can be preserved exactly as-is

**Medium Risk:**
- Budget timeline filter state management complexity (if moving to URL)
- Search parameter conflicts (tab + page parameters)
- Tab state persistence expectations (user may expect URL sync)

**Mitigation Strategies:**
- Start with Approach 1 (simplest), upgrade to Approach 2 if needed
- Preserve all existing child route logic
- Maintain existing query patterns and state management
- Test thoroughly with nested routes

---

## RECOMMENDATION

**Recommended Approach: Approach 1 (Simple Tabs with Component State)**

**Rationale:**
1. **Minimal Complexity:** Follows existing settings.tsx pattern exactly
2. **Low Risk:** Well-established pattern, no URL state complexity
3. **Quick Implementation:** Can be completed in 2-3 hours
4. **Easy Upgrade Path:** Can migrate to URL sync later if needed
5. **Preserves Functionality:** All existing features remain intact

**Implementation Priority:**
1. Preserve child route detection logic (critical for nested routes)
2. Implement tab structure with component state
3. Move existing sections into tab content
4. Test navigation to/from child routes
5. Verify all existing functionality works within tabs

---

## AMBIGUITIES AND MISSING INFORMATION

**Clarifications Needed:**
1. **Tab State Persistence:** Should tab selection persist across page refreshes? (If yes, use Approach 2)
2. **URL Shareability:** Do users need to share links to specific tabs? (If yes, use Approach 2)
3. **Budget Timeline Filter State:** Should filter state persist when switching tabs? (Currently unclear - may need user research)
4. **Project Information Tab:** What content will eventually go here? (Affects layout decisions)

**Unknown Factors:**
- User expectations for tab behavior (URL sync vs. component state)
- Performance impact of rendering all tab content vs. lazy loading
- Accessibility requirements for tab navigation (keyboard navigation, screen readers)

---

## NEXT STEPS

After approval of this analysis:
1. Get clarification on tab state persistence requirements
2. Create detailed implementation plan based on chosen approach
3. Implement failing tests (TDD approach)
4. Refactor component to tabbed layout
5. Verify child route functionality
6. Test all existing features within new tab structure
