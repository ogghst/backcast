# Analysis: Contextual Navigation Component & Change Orders Page

**Created:** 2026-01-15
**Request:** The menu in AppLayout.tsx shall be a dedicated component showing contextual navigation information. It shall contain a list of configurable links and the active page shall send the links to the component to enhance the navigation experience. The first implementation shall be on the project detail page: instead of having the change order list in a table, it shall be in a separate page and the link shall be in the configurable link component.

---

## Clarified Requirements

### Functional Requirements

1. **Contextual Navigation Component**: A dedicated component that displays page-specific navigation links
2. **Dynamic Link Injection**: Pages should be able to provide/propagate links to the navigation component
3. **Change Orders Separate Page**: Move change orders from inline Card to a dedicated page
4. **Navigation Link**: Add a link to the change orders page in the contextual navigation
5. **Integration with AppLayout**: The component should be integrated into the existing layout

### Non-Functional Requirements

- **Maintainability**: Reusable component that can be used across different pages (WBE detail, project detail, etc.)
- **User Experience**: Clear navigation hierarchy with contextual awareness
- **Performance**: Minimal impact on rendering performance
- **Accessibility**: Proper ARIA labels and keyboard navigation

### Constraints

- Must work with existing React Router v6 setup
- Must integrate with existing AppLayout structure
- Should follow existing Ant Design patterns (Tabs, Menu components)
- Must maintain permission-based UI (using Can component)

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- Navigation enhancement for better UX when working with projects and change orders
- Separation of concerns: project detail overview vs. detailed change order management

**Business Requirements:**
- Users need to navigate between project details and related entities (WBEs, change orders)
- Change order management requires more screen real estate than a small Card allows

### Architecture Context

**Bounded Contexts Involved:**
- Project & WBE Management (project detail page)
- Change Order & Branching (change orders page)

**Existing Patterns to Follow:**
- Ant Design Tabs component (used in ImpactAnalysisDashboard)
- Card-based layout pattern (used throughout project pages)
- Breadcrumb navigation pattern (BreadcrumbBuilder component)
- Permission-based UI (Can component)

**Architectural Constraints:**
- React Router v6 for routing
- Zustand for client state management
- TanStack Query for server state
- Ant Design component library

### Codebase Analysis

**Backend:**
- No backend changes required for this feature
- Existing change order APIs will be reused

**Frontend:**

**Current Project Detail Page:**
- [ProjectDetailPage.tsx](frontend/src/pages/projects/ProjectDetailPage.tsx) - Displays project summary, root WBEs table, and change orders Card (lines 151-156)

**Change Order Components:**
- [ChangeOrderList.tsx](frontend/src/features/change-orders/components/ChangeOrderList.tsx) - Table component with columns: Code, Title, Status, Effective Date, Actions
- [ImpactAnalysisDashboard.tsx](frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) - Uses Tabs pattern for navigation

**Routing Structure:**
- [routes/index.tsx](frontend/src/routes/index.tsx) - Current routes include `/projects/:projectId` and `/projects/:projectId/change-orders/:changeOrderId/impact`

**Navigation Patterns:**
- [AppLayout.tsx](frontend/src/layouts/AppLayout.tsx) - Static sidebar Menu with Dashboard, Projects, Admin
- [BreadcrumbBuilder.tsx](frontend/src/components/hierarchy/BreadcrumbBuilder.tsx) - Hierarchical breadcrumb navigation
- Tabs pattern in ImpactAnalysisDashboard - good reference for tab-style navigation

---

## Solution Options

### Option 1: Context-Aware Secondary Navigation Bar

**Architecture & Design:**
- Create a `ContextualNavigation` component that renders a secondary navigation bar below the main header
- Use React Context (`NavigationContext`) to allow pages to inject navigation items
- Place component in AppLayout between Header and Content
- Use Ant Design `Menu` component in horizontal mode for consistency

**State Management:**
```tsx
// New context for navigation
interface NavigationContextValue {
  items: NavigationItem[];
  setItems: (items: NavigationItem[]) => void;
}

const NavigationContext = createContext<NavigationContextValue>({
  items: [],
  setItems: () => {},
});
```

**UX Design:**
- Horizontal navigation bar below header
- Active tab highlighted
- Context-aware: only shows when on project/WBE detail pages
- Breadcrumb remains above for full path context

**User Flow:**
1. User navigates to Project Detail page
2. Contextual navigation shows: "Overview | Change Orders | Settings"
3. User clicks "Change Orders" → navigates to change orders page
4. Contextual navigation updates to show active state

**Implementation:**
- **Key files to create:**
  - `frontend/src/components/navigation/ContextualNavigation.tsx`
  - `frontend/src/contexts/NavigationContext.tsx`
- **Key files to modify:**
  - `frontend/src/layouts/AppLayout.tsx` - Integrate navigation component
  - `frontend/src/pages/projects/ProjectDetailPage.tsx` - Remove change orders Card, add navigation context
  - `frontend/src/pages/projects/ProjectChangeOrdersPage.tsx` - NEW: Dedicated change orders page
  - `frontend/src/routes/index.tsx` - Add new route

**Technical Challenges:**
- Managing navigation state between page transitions
- Ensuring active state updates correctly on route change
- Preventing stale navigation items when navigating away from context

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | • Familiar pattern (similar to many admin dashboards)<br>• Clean separation of main and contextual navigation<br>• Scalable to other pages (WBE detail, etc.) |
| Cons | • Requires React Context setup (additional complexity)<br>• Two navigation levels may confuse users<br>• Takes up vertical space |
| Complexity | Medium |
| Maintainability | Good - reusable pattern |
| Performance | Good - minimal re-renders |

---

### Option 2: Tab-Based Navigation within Content Area

**Architecture & Design:**
- Create a `PageNavigation` component using Ant Design `Tabs`
- Each page (ProjectDetail, ChangeOrders) becomes a tab panel
- Use React Router nested routing to handle tab navigation
- Navigation state derived from URL route

**State Management:**
```tsx
// Route-based navigation (no context needed)
<Route path="/projects/:projectId" element={<ProjectLayout />}>
  <Route index element={<ProjectOverview />} />
  <Route path="change-orders" element={<ProjectChangeOrders />} />
</Route>
```

**UX Design:**
- Tabs positioned at top of content area (below header)
- Tab content scrolls independently
- URL updates when switching tabs
- Direct linking to specific tabs possible

**User Flow:**
1. User navigates to `/projects/123` → sees Overview tab
2. User clicks "Change Orders" tab → URL changes to `/projects/123/change-orders`
3. Page shows dedicated change orders page with full-width table
4. User can bookmark specific tab URLs

**Implementation:**
- **Key files to create:**
  - `frontend/src/components/navigation/PageNavigation.tsx` - Tabs wrapper
  - `frontend/src/pages/projects/ProjectLayout.tsx` - Outlet wrapper for tabs
  - `frontend/src/pages/projects/ProjectOverview.tsx` - Current detail content
  - `frontend/src/pages/projects/ProjectChangeOrdersPage.tsx` - NEW: Change orders page
- **Key files to modify:**
  - `frontend/src/routes/index.tsx` - Add nested routes
  - `frontend/src/pages/projects/ProjectDetailPage.tsx` - Refactor as layout or rename to Overview

**Technical Challenges:**
- Refactoring existing ProjectDetailPage to use nested routes
- Managing shared state (project data) between tabs
- Ensuring Time Machine context works across tab navigation

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | • URL-driven state (shareable links)<br>• Standard pattern (Ant Design Tabs)<br>• No additional context/state management<br>• Browser back button works naturally |
| Cons | • Requires significant ProjectDetailPage refactoring<br>• Nested routing adds complexity<br>• Tabs inside content area may be less discoverable |
| Complexity | Medium-High |
| Maintainability | Good - leverages React Router patterns |
| Performance | Excellent - route-based code splitting possible |

---

### Option 3: Hybrid Sidebar with Contextual Items

**Architecture & Design:**
- Enhance existing AppLayout Sider to show contextual items
- Pages can register secondary navigation items via Zustand store
- Contextual items appear below main menu items, visually separated
- Store resets to empty when navigating away from contextual pages

**State Management:**
```tsx
// Use existing or new Zustand store
interface NavigationStore {
  contextualItems: MenuItem[];
  setContextualItems: (items: MenuItem[]) => void;
  clearContextualItems: () => void;
}
```

**UX Design:**
- Sidebar expands to show contextual links
- Visual separator between main nav and contextual nav
- Contextual section shows "Project: [Project Code]" header
- Active item highlighted

**User Flow:**
1. User navigates to Project Detail
2. Sidebar shows contextual section: "Change Orders", "Settings"
3. User clicks "Change Orders" → main content area updates
4. When navigating to Dashboard, contextual section disappears

**Implementation:**
- **Key files to create:**
  - `frontend/src/stores/useNavigationStore.ts` - Zustand store for contextual items
  - `frontend/src/components/navigation/ContextualMenuSection.tsx` - Sidebar section
  - `frontend/src/pages/projects/ProjectChangeOrdersPage.tsx` - NEW: Change orders page
- **Key files to modify:**
  - `frontend/src/layouts/AppLayout.tsx` - Add contextual menu section
  - `frontend/src/pages/projects/ProjectDetailPage.tsx` - Remove change orders Card
  - `frontend/src/routes/index.tsx` - Add new route

**Technical Challenges:**
- Zustand store cleanup on page navigation
- Ensuring visual clarity between main and contextual nav
- Mobile responsiveness (sidebar collapses)

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | • Single navigation area (sidebar)<br>• Familiar pattern (admin dashboards)<br>• Reuses existing Zustand patterns<br>• Minimal layout changes |
| Cons | • Sidebar gets longer/complex<br>• Contextual items less discoverable (collapsed sidebar)<br>• Store cleanup edge cases<br>• Mobile experience concerns |
| Complexity | Low-Medium |
| Maintainability | Good - simple store pattern |
| Performance | Good - Zustand is efficient |

---

## Comparison Summary

| Criteria | Option 1: Context-Aware Nav Bar | Option 2: Tab-Based Navigation | Option 3: Hybrid Sidebar |
|----------|----------------------------------|--------------------------------|--------------------------|
| Development Effort | Medium | Medium-High | Low-Medium |
| UX Quality | Good - clear separation | Excellent - familiar tabs | Fair - sidebar clutter |
| Flexibility | High - dynamic injection | Medium - route-based | High - dynamic items |
| URL Shareability | Low - state-based | High - route-based | Low - state-based |
| Browser Nav Support | Poor - requires sync | Excellent - native | Poor - requires sync |
| Refactoring Required | Low | High (nested routes) | Low |
| Mobile Friendliness | Good | Good | Fair (collapsed sidebar) |
| Best For | Contextual tools/settings | Deep navigation hierarchies | Admin dashboards |

---

## Recommendation

**I recommend Option 2 (Tab-Based Navigation) because:**

1. **URL-Driven State**: Users can bookmark and share direct links to specific tabs (e.g., `/projects/123/change-orders`)
2. **Browser Navigation**: Back/forward buttons work naturally without complex state synchronization
3. **Standard Pattern**: Ant Design Tabs + nested routing is a well-established pattern with excellent documentation
4. **Scalability**: Easy to add more tabs in the future (Settings, History, Analytics, etc.)
5. **Code Splitting**: Route-based code splitting can load tab content on-demand

**Alternative consideration:** Choose Option 1 if you prefer not to refactor ProjectDetailPage for nested routing, or if you want the contextual navigation to be more of a "toolbar" than a "page switcher."

**Alternative consideration:** Choose Option 3 if you want the quickest implementation and are comfortable with sidebar-based navigation.

---

## Decision Questions

1. **Navigation Model**: Do you prefer URL-driven navigation (Option 2 - tabs shareable/bookmarkable) or state-driven navigation (Options 1 & 3)?

2. **Refactoring Tolerance**: Are you open to refactoring ProjectDetailPage to use nested routes (Option 2), or do you prefer minimal changes to existing page structure (Options 1 & 3)?

3. **Future Expansion**: Do you anticipate adding more navigation items beyond Change Orders (e.g., Settings, Analytics, History)? This would favor Options 1 or 2.

---

## APPROVED DECISION

**Approved Option:** Option 2 - Tab-Based Navigation

**Decision Date:** 2026-01-15

**Approved By:** User

### Key Decisions Made

1. **URL-Driven Navigation**: All navigation will be URL-based for shareability and browser back/forward button support
2. **Flexible Navigation Component**: Create a `PageNavigation` component using Ant Design Tabs that can be easily adapted for sidebar placement in the future
3. **ProjectDetailPage Refactoring**: Approved to refactor ProjectDetailPage to use nested routing with React Router v6
4. **Future Expansion Strategy**: New sections will be organized as tabs within the navigation component
5. **UI Documentation Update**: Update UI documentation to reflect this tab-based navigation strategy

### Implementation Notes

- Navigation component will accept configuration for tab items to allow easy adaptation to different layouts
- Default placement: Content area (below header)
- Future: Same component can be placed in AppLayout Sider by changing container/props
- All navigation state will be URL-based (React Router nested routes)

### Success Criteria for Plan Phase

- Navigation component is reusable and layout-agnostic
- All URLs are shareable (e.g., `/projects/123/change-orders`)
- Browser navigation works naturally
- Component can be moved to sidebar with minimal changes

---

## References

**Architecture Documentation:**
- [Bounded Contexts](../../02-architecture/01-bounded-contexts.md)
- [Coding Standards](../../00-meta/coding_standards.md)

**Existing Patterns:**
- [ImpactAnalysisDashboard.tsx](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) - Tabs pattern reference
- [BreadcrumbBuilder.tsx](../../../frontend/src/components/hierarchy/BreadcrumbBuilder.tsx) - Navigation pattern reference
- [AppLayout.tsx](../../../frontend/src/layouts/AppLayout.tsx) - Current layout structure

**Related Files:**
- [ProjectDetailPage.tsx](../../../frontend/src/pages/projects/ProjectDetailPage.tsx) - Current implementation
- [ChangeOrderList.tsx](../../../frontend/src/features/change-orders/components/ChangeOrderList.tsx) - Component to be reused
- [routes/index.tsx](../../../frontend/src/routes/index.tsx) - Routing configuration
