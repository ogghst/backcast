# Analysis: Unified Change Order Page

**Created:** 2026-01-15
**Request:** Create a single change order page to handle both create and edit functions, with edit form section, workflow section, and impact analysis section, instead of the current multi-modal approach.

---

## Clarified Requirements

### Current State

The change order edit experience currently involves:
1. **Edit Modal** ([`ChangeOrderModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx)): Opens when clicking "Edit" button in the list
2. **Workflow Modal** ([`ChangeOrderWorkflowModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderWorkflowModal.tsx)): Opens on row click, showing workflow stepper and action buttons
3. **Impact Analysis Page** ([`ImpactAnalysisDashboard.tsx`](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx)): Separate page at `/projects/:projectId/change-orders/:changeOrderId/impact`

### User Intent

The user wants to consolidate these into a **single unified page** that:
- Handles both **create** and **edit** operations
- Displays **all relevant information** in one view
- Includes sections for:
  - Edit form (CO metadata)
  - Workflow section (stepper, action buttons, status guidance)
  - Impact analysis section (KPI cards, charts, entity changes)
- **Simplifies navigation** by removing modal stacking
- **Enhances UX** by showing comprehensive information at once

### Functional Requirements

1. Single page accessible via URL (e.g., `/projects/:projectId/change-orders/:changeOrderId` or `/new`)
2. Tab-based or section-based layout to organize:
   - Edit form (metadata editing)
   - Workflow management (status transitions, branch lock state)
   - Impact analysis (visual comparison dashboard)
3. Shareable URLs for each change order
4. Browser back/forward navigation support
5. Create mode with blank form
6. Edit mode with pre-populated form data
7. Branch lock indicator and warnings
8. Workflow action buttons (Submit, Approve, Reject, etc.)

### Non-Functional Requirements

- **Performance:** Page should load quickly, lazy-load charts if needed
- **Accessibility:** Keyboard navigation, screen reader support
- **Maintainability:** Reusable components, clear separation of concerns
- **Mobile Responsiveness:** Sections should stack appropriately on smaller screens
- **Type Safety:** Strict TypeScript, no `any` types

### Constraints

- Must follow existing [Navigation Patterns](../../../05-user-guide/navigation-patterns.md)
- Must align with [Coding Standards](../../../02-architecture/coding-standards.md)
- Must use existing change order workflow components
- Cannot break existing change order list page
- Must preserve all existing functionality (workflow actions, impact analysis, history)

---

## Context Discovery

### Product Scope

**Relevant User Stories** (from [change-management-user-stories.md](../../../01-product-scope/change-management-user-stories.md)):

1. **US 3.1 - Creation of a Change (and Branch Generation):** Create CO with automatic branch creation
2. **US 3.3 - Updating the Change Metadata:** Edit CO description, justification, effective date
3. **US 3.4 - Reviewing Change Impacts:** Visual comparison with KPI cards, waterfall charts, S-curves
4. **US 3.5 - Submitting the Change:** Submit for approval, lock branch
5. **US 3.6 - Accepting the Change (Merge):** Approve and merge change order
6. **US 3.8 - Toggling View Modes:** Isolated vs. Merged view (for future consideration)

**Workflow States:** Draft → Submitted → Approved/Rejected → Implemented

**Key Business Requirements:**
- Branch isolation for changes
- Lock branch on submission
- Impact analysis before approval
- Visual comparison (Main vs. Change branch)
- Change Control Board (CCB) workflow

### Architecture Context

**Bounded Contexts Involved:**

- **Context #7: Change Order Processing** ([01-bounded-contexts.md](../../../02-architecture/01-bounded-contexts.md#7-change-order-processing))
  - Branch creation, modification, comparison, merging
  - Automatic branch creation (`co-{id}`)
  - Branch locking/unlocking

- **Context F0: Core Architecture** (Frontend)
  - URL-driven navigation with React Router v6
  - Centralized route definitions

- **Context F1: State & Data Management**
  - TanStack Query for server state
  - API hooks in [`features/change-orders/api/`](../../../frontend/src/features/change-orders/api/)

**Existing Patterns to Follow:**

1. **PageNavigation Pattern** ([`PageNavigation.tsx`](../../../frontend/src/components/navigation/PageNavigation.tsx))
   - URL-driven tab navigation
   - Shareable URLs
   - Browser navigation support

2. **Nested Routing Pattern** ([ProjectLayout.tsx](../../../frontend/src/pages/projects/ProjectLayout.tsx))
   - Layout wrapper with `<Outlet />`
   - Nested routes for entity details

3. **Feature-Based Organization**
   - Components in `features/change-orders/components/`
   - Hooks in `features/change-orders/hooks/`
   - API in `features/change-orders/api/`

**Architectural Constraints:**

- Must use existing workflow components ([`WorkflowStepper.tsx`](../../../frontend/src/features/change-orders/components/WorkflowStepper.tsx), [`WorkflowButtons.tsx`](../../../frontend/src/features/change-orders/components/WorkflowButtons.tsx))
- Must use existing impact analysis components ([`KPICards.tsx`](../../../frontend/src/features/change-orders/components/KPICards.tsx), [`WaterfallChart.tsx`](../../../frontend/src/features/change-orders/components/WaterfallChart.tsx), etc.)
- Must preserve API contracts (no backend changes required)
- Must follow RBAC permissions (`<Can>` component)

### Codebase Analysis

**Backend:**

- **Change Order Model:** [`backend/app/models/domain/change_order.py`](../../../backend/app/models/domain/change_order.py)
  - Fields: code, title, description, justification, effective_date, status, branch, branch_locked, available_transitions
  - Workflow states: Draft, Submitted, Approved, Rejected, Implemented

- **Change Order Service:** [`backend/app/services/change_order_service.py`](../../../backend/app/services/change_order_service.py)
  - CRUD operations
  - Workflow transitions
  - Branch management

- **API Routes:** [`backend/app/api/routes/change_orders.py`](../../../backend/app/api/routes/change_orders.py)
  - GET /change-orders/{id} - Fetch single CO
  - POST /change-orders - Create CO
  - PUT /change-orders/{id} - Update CO
  - POST /change-orders/{id}/transition - Workflow transition
  - GET /change-orders/{id}/impact - Impact analysis data

**Frontend:**

**Existing Related Components:**

| File | Purpose | Reuse Potential |
|------|---------|-----------------|
| [`ChangeOrderModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx) | Form for create/edit | Extract form logic |
| [`ChangeOrderWorkflowModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderWorkflowModal.tsx) | Workflow stepper + buttons | Use components directly |
| [`ImpactAnalysisDashboard.tsx`](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) | Full impact analysis | Embed as section/tab |
| [`ChangeOrderDetailsSection.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderDetailsSection.tsx) | Metadata display | Use in read-only mode |
| [`WorkflowStepper.tsx`](../../../frontend/src/features/change-orders/components/WorkflowStepper.tsx) | Visual stepper | Use directly |
| [`WorkflowButtons.tsx`](../../../frontend/src/features/change-orders/components/WorkflowButtons.tsx) | Action buttons | Use directly |
| [`BranchLockIndicator.tsx`](../../../frontend/src/features/change-orders/components/BranchLockIndicator.tsx) | Lock status | Use directly |

**API Hooks:** [`frontend/src/features/change-orders/api/useChangeOrders.ts`](../../../frontend/src/features/change-orders/api/useChangeOrders.ts)
- `useChangeOrder(id)` - Fetch single CO
- `useCreateChangeOrder()` - Create mutation
- `useUpdateChangeOrder()` - Update mutation
- `useImpactAnalysis(id, branch)` - Impact data

**Current Routing:** ([`frontend/src/routes/index.tsx`](../../../frontend/src/routes/index.tsx))
```tsx
{
  path: "/projects/:projectId/change-orders/:changeOrderId/impact",
  element: <ImpactAnalysisDashboard />,
}
```

**Comparable Patterns:**

- [`ProjectLayout.tsx`](../../../frontend/src/pages/projects/ProjectLayout.tsx) - Nested routing with PageNavigation
- [`ProjectChangeOrdersPage.tsx`](../../../frontend/src/pages/projects/ProjectChangeOrdersPage.tsx) - Tab-based organization

---

## Solution Options

### Option 1: Tab-Based Layout with URL Routing

**Architecture & Design:**

- **Component Structure:**
  - `ChangeOrderDetailPage.tsx` - Main page component with PageNavigation
  - `ChangeOrderFormSection.tsx` - Form for editing (extracted from modal)
  - `ChangeOrderWorkflowSection.tsx` - Workflow stepper + buttons
  - `ChangeOrderImpactSection.tsx` - Impact analysis (reusing dashboard components)

- **State Management:**
  - TanStack Query for data fetching
  - Ant Design Form for form state
  - URL params for tab navigation

- **Data Flow:**
  ```
  Route Params (projectId, changeOrderId?)
    → useChangeOrder() hook
    → Page state (form values, active tab)
    → Section components
  ```

- **Routing:**
  ```tsx
  // Edit existing
  /projects/:projectId/change-orders/:changeOrderId
    → ChangeOrderDetailPage (with form, workflow, impact tabs)

  // Create new
  /projects/:projectId/change-orders/new
    → ChangeOrderDetailPage (create mode, form tab only)
  ```

**UX Design:**

- **User Stories Supported:** All US 3.1-3.6
- **Navigation Flow:**
  1. From change order list, click row or "View Details" → Navigate to detail page
  2. Details tab shows metadata, workflow tab shows actions, impact tab shows charts
  3. "New Change Order" button → Navigate to `/new` route with pre-filled form
- **Visual Hierarchy:**
  - Page header: CO code, title, status badge, branch lock indicator
  - PageNavigation: Form | Workflow | Impact | History
  - Active tab content area
- **Accessibility:**
  - Semantic HTML for tabs
  - Keyboard navigation between tabs
  - ARIA labels for actions
- **Edge Cases:**
  - New CO: No workflow/impact tabs (disabled or hidden)
  - Locked branch: Form becomes read-only, workflow buttons show appropriate actions
  - Deleted CO: Show "Not Found" state

**Technical Implementation:**

- **Key Files:**
  - Create: `frontend/src/pages/projects/change-orders/ChangeOrderDetailPage.tsx`
  - Create: `frontend/src/pages/projects/change-orders/ChangeOrderFormSection.tsx`
  - Modify: `frontend/src/routes/index.tsx` (add routes)
  - Modify: `frontend/src/features/change-orders/components/ChangeOrderModal.tsx` (extract form)

- **Integration Points:**
  - Reuse all existing workflow components
  - Reuse impact analysis dashboard as section
  - Update ChangeOrderList to navigate instead of opening modal

- **Technical Challenges:**
  - Form state management when switching tabs
  - Handling unsaved changes on tab navigation
  - URL management for create vs. edit mode
  - Permission-based tab visibility

- **Testing Approach:**
  - Unit tests for each section component
  - Integration tests for page navigation
  - E2E tests for create/edit workflow

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | - Clean URL structure (/change-orders/123)<br>- Shareable links to specific tabs<br>- Browser back/forward works naturally<br>- Follows established PageNavigation pattern<br>- Progressive disclosure of information |
| **Cons** | - More files to create (page + sections)<br>- URL management complexity<br>- Need to handle tab state in URL |
| **Complexity** | Medium (follows existing patterns) |
| **Maintainability** | Good (clear separation, reusable sections) |
| **Performance** | Good (can lazy-load tab content) |

---

### Option 2: Single-Page Scroll Layout

**Architecture & Design:**

- **Component Structure:**
  - `ChangeOrderUnifiedPage.tsx` - Single page with collapsible sections
  - Sections render sequentially on one long page
  - Anchor navigation for jumping between sections

- **State Management:**
  - Similar to Option 1
  - Additional state for collapsed/expanded sections

- **Data Flow:** Same as Option 1

- **Routing:** Same URL structure, but no tab param

**UX Design:**

- **User Stories Supported:** All US 3.1-3.6
- **Navigation Flow:**
  1. Click row in list → Navigate to unified page
  2. All sections visible, scroll to navigate
  3. Anchor links in sticky header for quick jumps
- **Visual Hierarchy:**
  - Sticky sub-navigation: Form | Workflow | Impact | History
  - Sections with collapsible headers
  - Impact charts at bottom (heavy content)
- **Accessibility:**
  - Skip links for main sections
  - Semantic sections with headings
- **Edge Cases:** Same as Option 1

**Technical Implementation:**

- **Key Files:**
  - Create: `ChangeOrderUnifiedPage.tsx`
  - Simpler structure (no separate section files needed)

- **Integration Points:** Same as Option 1

- **Technical Challenges:**
  - Scroll position management on navigation
  - Long page may feel overwhelming
  - Impact charts heavy to render

- **Testing Approach:** Similar to Option 1

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | - Simpler component structure<br>- All information visible at once<br>- No URL state management<br>- Easier to implement |
| **Cons** | - Long scrolling page can be overwhelming<br>- Heavy content (charts) loads immediately<br>- Harder to share specific sections<br>- Mobile experience may be poor |
| **Complexity** | Low (simpler structure) |
| **Maintainability** | Fair (single large component) |
| **Performance** | Medium (all content loads) |

---

### Option 3: Hybrid Layout (Form + Workflow in Modal, Impact Separate)

**Architecture & Design:**

- Keep current modal approach but consolidate edit + workflow into one modal
- Keep impact analysis as separate page (link from modal)
- Minimal changes to existing structure

**UX Design:**

- **Navigation Flow:**
  1. Click row → Opens consolidated modal (form + workflow tabs)
  2. "View Impact Analysis" button → Navigate to impact page
- **Visual Hierarchy:**
  - Modal with internal tabs: Edit | Workflow
  - External link to full impact analysis page

**Technical Implementation:**

- **Key Files:**
  - Modify: `ChangeOrderModal.tsx` (add workflow tab)
  - Keep: `ImpactAnalysisDashboard.tsx` (no change)
  - Remove: `ChangeOrderWorkflowModal.tsx` (consolidated)

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | - Minimal code changes<br>- Modal pattern familiar to users<br>- Impact analysis gets full page |
| **Cons** | - Doesn't solve the modal stacking issue<br>- Still multiple clicks to see everything<br>- No shareable URL for CO details<br>- Breaks URL-driven navigation principle |
| **Complexity** | Low (minimal changes) |
| **Maintainability** | Fair (modal complexity increases) |
| **Performance** | Good (lazy modal content) |

---

## Comparison Summary

| Criteria | Option 1: Tab-Based | Option 2: Single-Page Scroll | Option 3: Hybrid Modal |
|----------|---------------------|------------------------------|------------------------|
| **Development Effort** | Medium | Low | Low |
| **UX Quality** | High | Medium | Low-Medium |
| **Flexibility** | High (can hide/disable tabs) | Medium | Low |
| **URL Sharing** | ✅ Yes (/change-orders/123) | ❌ No (just page URL) | ❌ No (modal) |
| **Browser Navigation** | ✅ Full support | Partial | ❌ Modal breaks history |
| **Mobile Experience** | Good (stack tabs) | Poor (long scroll) | Good (modal) |
| **Pattern Consistency** | ✅ Follows PageNavigation | ⚠️ Different from other pages | ⚠️ Modal pattern |
| **Best For** | **Modern, shareable detail pages** | Simple internal tools | Quick edits only |

---

## Recommendation & Decision

User Selected: Option 2 - Single-Page Scroll Layout

### Rationale for Selection

The user chose Option 2 for the following reasons:

1. **Development Speed:** Lower complexity and faster implementation
2. **Information Visibility:** All relevant information visible at once without clicking tabs
3. **Simplicity:** No URL state management for tab navigation
4. **Single View:** Users can see the complete change order context (form, workflow, impact) in one scrollable page

### Acknowledged Trade-offs

By selecting Option 2, the following trade-offs are accepted:

- **No URL sharing for specific sections** - Users can share the change order URL but not specific sections
- **All content loads at once** - Impact charts load immediately (may affect initial page load)
- **Longer page** - Users must scroll to see all content
- **Mobile experience** - Longer scroll on mobile devices

### Implementation Decision

Final Choice: Option 2 - Single-Page Scroll Layout

This decision is recorded and will guide the PLAN and DO phases.

---

## Decision Questions

1. **Is URL sharing important?** Should users be able to share links to specific change orders?
   - If **Yes**: Option 1 is the clear choice
   - If **No**: Option 2 or 3 could work

2. **How do users typically interact with change orders?**
   - **Quick edits only**: Option 3 might suffice
   - **Full review workflow**: Option 1 provides better experience

3. **Should the impact analysis charts be visible by default?**
   - **Yes**: Option 2 (scroll layout)
   - **No (load on demand)**: Option 1 (tab-based)

4. **Is mobile optimization a priority?**
   - **Yes**: Option 1 (tabs stack on mobile)
   - **No**: All options work on desktop

---

> [!IMPORTANT] > **Human Decision Point**: Please review the options above and confirm which approach you prefer. Once approved, I will proceed to the PLAN phase to create detailed implementation steps.

---

## References

- [Change Management User Stories](../../../01-product-scope/change-management-user-stories.md)
- [Navigation Patterns Guide](../../../05-user-guide/navigation-patterns.md)
- [Coding Standards](../../../02-architecture/coding-standards.md)
- [Bounded Contexts: Change Order Processing](../../../02-architecture/01-bounded-contexts.md#7-change-order-processing)
- [Analysis Phase Prompt](../../../04-pdca-prompts/analysis-prompt.md)

---

## Current State Summary

**Files Involved:**

| File | Current Role | Planned Change |
|------|--------------|----------------|
| [`ChangeOrderList.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderList.tsx) | List view with modal actions | Navigate to detail page |
| [`ChangeOrderModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx) | Create/Edit form | Extract form, reuse in page |
| [`ChangeOrderWorkflowModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderWorkflowModal.tsx) | Workflow modal | Remove (use components) |
| [`ImpactAnalysisDashboard.tsx`](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) | Separate page | Embed as section/tab |
| [`routes/index.tsx`](../../../frontend/src/routes/index.tsx) | Current routing | Add detail routes |

**Current Routes:**
```
/projects/:projectId/change-orders                          → List page
/projects/:projectId/change-orders/:changeOrderId/impact  → Impact page (only)
```

**Proposed Routes (Option 2 - Selected):**
```
/projects/:projectId/change-orders                          → List page (unchanged)
/projects/:projectId/change-orders/new                     → Create new CO
/projects/:projectId/change-orders/:changeOrderId          → Detail page (all sections, scrollable)
/projects/:projectId/change-orders/:changeOrderId/impact  → Legacy redirect to detail page
```

**Route Differences from Option 1:**

- No tab state in URL (simpler routing)
- All sections render on same page (no lazy-loading by tab)
- Anchor links for in-page navigation (not route navigation)
