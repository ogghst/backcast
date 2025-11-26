# High-Level Analysis: Branch Selector Visibility Across Project Pages

**Task:** Make branch selector visible in all project, WBE, and cost element pages
**Status:** Analysis Phase
**Date:** 2025-01-27
**Analysis Code:** PLA001

---

## User Story

**As a** project manager
**I want to** see and switch branches at any time while viewing project, WBE, or cost element pages
**So that** I can easily navigate between different branch contexts (main branch vs change order branches) without needing to navigate to the change orders tab first.

---

## 1. CODEBASE PATTERN ANALYSIS

### Existing Implementation Patterns

#### Pattern 1: Branch Selector Component (Existing)
- **Location:** `frontend/src/components/Projects/BranchSelector.tsx` (33 lines)
- **Pattern:** Simple dropdown component using native HTML `<select>` element
- **Dependencies:** Uses `useBranch()` hook from `BranchContext`
- **Current Usage:** Only rendered in "Change Orders" tab of project detail page (line 528 of `projects.$id.tsx`)
- **Styling:** Inline styles using Chakra UI CSS variables, 200px width
- **Status:** ✅ Component exists and works, but limited visibility

#### Pattern 2: Branch Context Provider (Existing)
- **Location:** `frontend/src/context/BranchContext.tsx` (94 lines)
- **Pattern:** React Context API with Provider pattern
- **Features:**
  - Fetches available branches from change orders
  - Manages current branch state (defaults to "main")
  - Invalidates queries on branch change (wbes, cost-elements, change-orders)
  - Always includes "main" branch in available branches
- **Usage:** Already wraps:
  - Project detail page (`projects.$id.tsx` line 356)
  - WBE detail page (`projects.$id.wbes.$wbeId.tsx` line 375)
  - Cost element detail page via parent routes (line 368)
- **Status:** ✅ Context provider already in place for all target pages

#### Pattern 3: Page Header Structure (Consistent Pattern)
- **Location:** Multiple route files demonstrate consistent header pattern
- **Pattern:** Breadcrumbs → Heading → Tabs structure
- **Examples:**
  - `projects.$id.tsx`: Breadcrumbs (lines 358-372) → Heading (line 373) → Tabs (line 375+)
  - `projects.$id.wbes.$wbeId.tsx`: Breadcrumbs (lines 377-404) → Heading (lines 406-408) → Tabs (line 410+)
  - `projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx`: Breadcrumbs (lines 183-204) → Heading (lines 207-212) → Tabs (line 214+)
- **Action Button Placement:**
  - Within tab content: `<Flex justifyContent="space-between">` pattern (e.g., line 401-404 in projects.$id.tsx)
  - After heading, before tabs: Not currently used, but logical placement option
- **Status:** ✅ Consistent pattern across all pages

#### Pattern 4: Tab-Specific Header Sections
- **Location:** Individual tab content sections
- **Pattern:** Each tab has its own heading with action buttons in a Flex container
- **Example:** WBE tab (lines 399-407 in `projects.$id.tsx`):
  ```tsx
  <Flex alignItems="center" justifyContent="space-between" mb={4}>
    <Heading size="md">Work Breakdown Elements</Heading>
    <AddWBE projectId={project.project_id} />
  </Flex>
  ```
- **Status:** ✅ Common pattern for tab-specific actions

**Architectural layers to respect:**
- *Component structure*: Reusable components in `frontend/src/components/Projects/`
- *Context providers*: React Context for state management (BranchContext)
- *Route structure*: TanStack Router file-based routing
- *UI library*: Chakra UI components and styling patterns
- *Query management*: TanStack Query for data fetching and invalidation

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### Components to Modify

**1. Project Detail Page** (`frontend/src/routes/_layout/projects.$id.tsx`)
- **Current State:** BranchSelector only in "change-orders" tab (line 528)
- **Required Changes:**
  - Add BranchSelector to persistent header area (after heading, before tabs)
  - Ensure it's visible on all tabs, not just change-orders
- **Dependencies:** Already wrapped in BranchProvider (line 356)

**2. WBE Detail Page** (`frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`)
- **Current State:** No BranchSelector visible
- **Required Changes:**
  - Add BranchSelector to persistent header area (after heading, before tabs)
- **Dependencies:** Already wrapped in BranchProvider (line 375)

**3. Cost Element Detail Page** (`frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx`)
- **Current State:** No BranchSelector visible, BranchProvider only when on cost element route
- **Required Changes:**
  - Ensure BranchProvider wraps component (currently only wraps Outlet on child route, line 368)
  - Add BranchSelector to persistent header area (after heading, before tabs)
- **Dependencies:** Need to verify BranchProvider placement

### Component Enhancements (Optional)

**4. BranchSelector Component** (`frontend/src/components/Projects/BranchSelector.tsx`)
- **Current State:** Basic dropdown with inline styles
- **Potential Enhancements:**
  - Migrate to Chakra UI Select component for consistency
  - Add loading state indicator
  - Add visual indicator for non-main branches
  - Improve styling to match design system
- **Priority:** Low (can be done in follow-up improvement)

### Configuration and State Management

**5. BranchContext** (`frontend/src/context/BranchContext.tsx`)
- **Status:** ✅ No changes needed
- **Notes:** Already provides all necessary functionality:
  - `currentBranch` state
  - `setCurrentBranch` function
  - `availableBranches` array
  - `isLoading` state

**6. Query Invalidation Logic**
- **Status:** ✅ Already implemented
- **Current Behavior:** Branch change invalidates wbes, cost-elements, change-orders queries
- **Impact:** Data will automatically refresh when branch changes, ensuring UI shows correct branch data

### Route Dependencies

**7. Routing Structure**
- **Status:** ✅ No changes needed
- **Notes:** All target routes already exist and follow consistent patterns

---

## 3. ABSTRACTION INVENTORY

### Existing Abstractions to Leverage

**1. BranchContext Hook (`useBranch()`)**
- **Location:** `frontend/src/context/BranchContext.tsx`
- **Provides:** `currentBranch`, `setCurrentBranch`, `availableBranches`, `isLoading`
- **Usage:** Already used by BranchSelector component
- **Reusability:** ✅ Can be used anywhere BranchProvider is available

**2. BranchProvider Component**
- **Location:** `frontend/src/context/BranchContext.tsx`
- **Purpose:** Provides branch context to child components
- **Current Coverage:** Already wraps all target pages
- **Reusability:** ✅ No additional setup needed

**3. Chakra UI Flex Component**
- **Usage:** Consistent Flex container pattern for header layouts
- **Pattern:** `<Flex alignItems="center" justifyContent="space-between">`
- **Reusability:** ✅ Standard Chakra UI pattern

**4. Page Header Pattern**
- **Abstraction:** Consistent breadcrumbs → heading → action area → tabs structure
- **Reusability:** Could extract to shared component (future enhancement)

### Patterns for Implementation

- **Persistent Header Pattern:** Place BranchSelector in header area (after heading, before tabs) to ensure visibility across all tabs
- **Conditional Rendering:** BranchSelector can be conditionally rendered based on available branches count (hide if only "main" exists)
- **Responsive Design:** Consider mobile viewport behavior (dropdown should be accessible on small screens)

---

## 4. ALTERNATIVE APPROACHES

| Approach | Summary | Pros | Cons/Risks | Architectural Alignment | Complexity |
| --- | --- | --- | --- | --- | --- |
| **A. Persistent Header Placement (Recommended)** | Place BranchSelector in header area after page heading, before tabs. Visible on all tabs without duplication. | Single placement point; always visible; follows existing header pattern; consistent across all pages; minimal code changes | Requires 3 file modifications; need to ensure consistent styling; may need responsive adjustments | High - follows existing header structure pattern | Low (3 files, ~10 lines each) |
| **B. Tab-Specific Placement** | Add BranchSelector to each individual tab's header section (like change-orders tab currently does). | Reuses existing pattern; flexible per-tab styling; easy to implement incrementally | Duplication across tabs; not always visible (hidden when switching tabs); inconsistent user experience | Medium - reuses existing pattern but creates duplication | Medium (6+ file locations, ~20 lines total) |
| **C. Floating/Persistent Banner** | Create a sticky banner above tabs that persists while scrolling. Similar to notification banners. | Always visible regardless of scroll position; distinct visual separation; can include additional context | Requires new UI pattern; more complex styling; may interfere with other UI elements; over-engineered for this need | Low - introduces new UI pattern not used elsewhere | High (new component, z-index management, responsive design) |
| **D. Sidebar Integration** | Add BranchSelector to the existing sidebar component. | Persistent across all pages; centralized location; reduces page header clutter | Not page-specific (applies globally); may confuse users who expect page-scoped controls; requires sidebar modifications | Low - sidebar is global, branch context is project-scoped | Medium (sidebar modification, context scope concerns) |

### Recommended Approach: **Approach A (Persistent Header Placement)**

**Rationale:**
1. **Minimal Code Changes:** Only 3 files need modification
2. **Consistent Pattern:** Follows existing header structure
3. **Always Visible:** Branch selector accessible from any tab
4. **Project-Scoped:** Correct scope (project-specific, not global)
5. **Low Risk:** Simple placement, no new patterns or abstractions needed

**Implementation Details:**
- Add `<Flex>` container after heading, before `<Tabs.Root>`
- Include BranchSelector aligned to the right (consistent with other action buttons)
- Optional: Add label "Branch:" for clarity
- Ensure responsive behavior (stack on mobile if needed)

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### Principles Upheld

- **Architectural Respect:** Approach A extends existing header pattern without introducing new abstractions
- **Incremental Change:** Can be implemented one page at a time (project → WBE → cost element)
- **DRY Principle:** Single BranchSelector component reused across pages, no duplication
- **Consistency:** Follows established UI patterns (Flex containers, header layout)

### Potential Violations

- **None identified** - The recommended approach (A) follows existing patterns and requires minimal changes

### Future Maintenance

- **Branch Selector Styling:** If BranchSelector is enhanced later (migrated to Chakra UI Select), changes automatically propagate to all pages
- **Responsive Design:** Header area may need responsive adjustments for mobile viewports
- **Accessibility:** Ensure branch selector is keyboard navigable and screen-reader friendly

### Testing Challenges

- **Component Visibility Tests:** Verify BranchSelector appears on all target pages
- **Branch Switching Tests:** Verify data refreshes correctly when branch changes
- **Context Availability Tests:** Verify BranchProvider wraps all pages correctly
- **Responsive Design Tests:** Verify branch selector works on mobile viewports
- **Query Invalidation Tests:** Verify queries invalidate and refetch on branch change

---

## Risks, Unknowns, and Ambiguities

### Design Decisions (CLARIFICATION NEEDED)

- **Branch Selector Styling:** Should BranchSelector be migrated to Chakra UI Select component for consistency, or keep current inline-styled native select?
  - **Recommendation:** Keep current implementation for minimal changes, migrate to Chakra UI Select in follow-up task

- **Empty State Handling:** Should BranchSelector be hidden when only "main" branch exists, or always shown?
  - **Recommendation:** Always show (displays "main" as only option), provides consistency and prepares for future branches

- **Label and Positioning:** Should BranchSelector have a "Branch:" label, and should it be left-aligned or right-aligned?
  - **Recommendation:** Right-aligned to match other action buttons, optional label can be added later

- **Mobile Responsive Behavior:** How should BranchSelector behave on mobile viewports (stack below heading, or inline)?
  - **Recommendation:** Flex container with responsive wrapping or stacking for mobile

### Implementation Details (CLARIFICATION NEEDED)

- **Cost Element Page BranchProvider:** Verify BranchProvider placement in cost element detail page - currently only wraps Outlet on child route, need to ensure it wraps main component
  - **Action Required:** Check if cost element detail page needs BranchProvider added to main component (not just child route)

- **Branch Selector Placement Precision:** Exact positioning relative to heading and tabs (spacing, alignment)
  - **Recommendation:** Follow existing spacing patterns (mb={2} or mb={4} between heading and tabs)

### Business Rules (CONFIRMED)

- **Branch Availability:** ✅ Confirmed - Branches are fetched from change orders, "main" is always available
- **Branch Context Scope:** ✅ Confirmed - Branch context is project-scoped (per projectId)
- **Query Invalidation:** ✅ Confirmed - Branch changes invalidate relevant queries (wbes, cost-elements, change-orders)

---

## Summary & Next Steps

- **What:** Make BranchSelector component visible on all tabs of project detail, WBE detail, and cost element detail pages by placing it in the persistent header area (after heading, before tabs).

- **Why:** Users need to switch branches at any time while working in project, WBE, or cost element pages. Currently, branch selector is only visible in the change orders tab, forcing users to navigate away to switch branches.

- **Recommended Approach:** Approach A (Persistent Header Placement) - Add BranchSelector to header area after page heading, before tabs, in all three target pages.

- **Next Steps:**
  1. ⏳ Clarify design decisions (styling, positioning, mobile behavior)
  2. ⏳ Verify BranchProvider placement in cost element detail page
  3. ⏳ Create failing tests for BranchSelector visibility on all pages
  4. ⏳ Implement BranchSelector in project detail page header
  5. ⏳ Implement BranchSelector in WBE detail page header
  6. ⏳ Implement BranchSelector in cost element detail page header (if BranchProvider placement is correct)
  7. ⏳ Test branch switching functionality across all pages
  8. ⏳ Test responsive behavior on mobile viewports

---

## Decision Log

*To be updated as decisions are made during implementation.*

---

## Appendix: File Locations Reference

### Files to Modify
1. `frontend/src/routes/_layout/projects.$id.tsx` - Project detail page
2. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` - WBE detail page
3. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx` - Cost element detail page

### Files Already in Place (No Changes Needed)
- `frontend/src/components/Projects/BranchSelector.tsx` - Branch selector component
- `frontend/src/context/BranchContext.tsx` - Branch context provider

### Current BranchSelector Usage
- `frontend/src/routes/_layout/projects.$id.tsx` line 528 (change-orders tab only)
