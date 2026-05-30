# Frontend Navigation Patterns

This document describes the navigation patterns used in the Backcast  frontend application.

## Overview

The application uses a **URL-driven navigation** approach with React Router v6. This ensures:
- All pages are shareable via direct links
- Browser back/forward buttons work naturally
- Deep linking to specific views is supported

## Navigation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AppLayout                             │
├─────────────────────────────────────────────────────────────┤
│  Header (Logo, Time Machine, User Profile)                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            PageNavigation (Tabs)                    │    │
│  │  [Dashboard] [Overview] [Structure] ...             │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                       │    │
│  │                  <Outlet />                          │    │
│  │              (Nested Route Content)                  │    │
│  │                                                       │    │
│  └─────────────────────────────────────────────────────┘    │
│  Footer                                                   │
└─────────────────────────────────────────────────────────────┘
```

## PageNavigation Component

The `PageNavigation` component provides contextual tab-based navigation within a page.

### Location

`frontend/src/components/navigation/PageNavigation.tsx`

### Features

- **URL-driven**: Active tab is determined by current route
- **Shareable URLs**: Each tab has a unique URL
- **Browser Navigation**: Back/forward buttons work correctly
- **Layout Agnostic**: Can be placed in content area (default) or adapted for sidebar

### Props

```tsx
interface PageNavigationProps {
  items: NavigationItem[];
  variant?: "horizontal" | "sidebar"; // Default: "horizontal"
}

interface NavigationItem {
  key: string;
  label: string;
  path: string;
  icon?: React.ReactNode;
}
```

### Usage Example

```tsx
import { PageNavigation } from "@/components/navigation";

const navigationItems = [
  { key: "overview", label: "Overview", path: `/projects/${projectId}` },
  { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
];

<PageNavigation items={navigationItems} />;
```

## Nested Routing Pattern

For entities with multiple related views (e.g., Project → Dashboard, Overview, Structure), use nested routing. This pattern applies to five entities: Project, WBSElement, ControlAccount, WorkPackage, and CostElement.

### Directory Structure

```
frontend/src/pages/projects/
├── ProjectLayout.tsx           # Layout wrapper with PageNavigation
├── ProjectOverview.tsx         # Overview tab content
├── ProjectChangeOrdersPage.tsx # Change Orders tab content
├── ProjectStructure.tsx        # WBS structure tab
├── ProjectSchedulePage.tsx     # Schedule tab
├── ProjectEVMAnalysis.tsx      # EVM Analysis tab
├── ProjectCOQAnalysis.tsx      # COQ Analysis tab
├── ProjectCostEvents.tsx       # Cost Events tab
├── ProjectMembers.tsx          # Members tab
├── ProjectDocuments.tsx        # Documents tab
├── ProjectChat.tsx             # AI Chat tab
├── ProjectAdminPage.tsx        # Admin tab
├── ProjectExplorer.tsx         # Explorer view
├── ProjectList.tsx             # Project listing page
```

### Route Configuration

```tsx
// routes/index.tsx (simplified — shows project subtree children)
{
  path: "/projects/:projectId",
  element: <ProjectLayout />,
  children: [
    { index: true, element: <ProjectOverview /> },
    { path: "dashboard", element: <ProjectDashboard /> },
    { path: "structure", element: <ProjectStructure /> },
    { path: "schedule", element: <ProjectSchedulePage /> },
    { path: "change-orders", element: <ProjectChangeOrdersPage /> },
    { path: "members", element: <ProjectMembers /> },
    { path: "evm-analysis", element: <ProjectEVMAnalysis /> },
    { path: "coq-analysis", element: <ProjectCOQAnalysis /> },
    { path: "cost-events", element: <ProjectCostEvents /> },
    { path: "documents", element: <ProjectDocuments /> },
    { path: "chat", element: <ProjectChat /> },
    { path: "admin", element: <ProjectAdminPage /> },
  ],
}
```

### Layout Component

```tsx
// ProjectLayout.tsx (simplified — shows navigation items)
import { Outlet, useParams } from "react-router-dom";
import { PageNavigation } from "@/components/navigation";

export const ProjectLayout = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const items = [
    { key: "dashboard", label: "Dashboard", path: `/projects/${projectId}/dashboard` },
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "structure", label: "Structure", path: `/projects/${projectId}/structure` },
    { key: "schedule", label: "Schedule", path: `/projects/${projectId}/schedule` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
    { key: "members", label: "Members", path: `/projects/${projectId}/members` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/evm-analysis` },
    { key: "coq-analysis", label: "COQ Analysis", path: `/projects/${projectId}/coq-analysis` },
    { key: "cost-events", label: "Cost Events", path: `/projects/${projectId}/cost-events` },
    { key: "documents", label: "Documents", path: `/projects/${projectId}/documents` },
    { key: "chat", label: "AI Chat", path: `/projects/${projectId}/chat` },
    { key: "admin", label: "Admin", path: `/projects/${projectId}/admin` },
  ];

  return (
    <>
      <PageNavigation items={items} />
      <Outlet />
    </>
  );
};
```

## Current Navigation Hierarchy

```
/ (Home/Dashboard)
├── /chat                              # Global AI Chat
├── /profile                           # User Profile
├── /login                             # Login page
├── /users                             # User List
├── /change-orders/:changeOrderId      # Change Order Redirect
│
├── /projects (Project List)
│   └── /projects/:projectId (ProjectLayout — 12 child routes)
│       ├── index (Overview)
│       ├── dashboard
│       ├── structure
│       ├── schedule
│       ├── change-orders
│       ├── members
│       ├── evm-analysis
│       ├── coq-analysis
│       ├── cost-events
│       ├── documents
│       ├── chat
│       └── admin
│
│   # Change Order standalone routes (project-scoped, not nested under ProjectLayout)
│   /projects/:projectId/change-orders/new                          # ChangeOrderUnifiedPage
│   /projects/:projectId/change-orders/:changeOrderId               # ChangeOrderUnifiedPage
│   /projects/:projectId/change-orders/:changeOrderId/impact        # ChangeOrderImpactAnalysisPage
│
│   # WBSElement detail subtree
│   /projects/:projectId/wbs-elements/:wbsElementId (WBSElementLayout)
│       ├── index (Overview)
│       ├── evm-analysis
│       ├── cost-history
│       ├── documents
│       └── chat
│
│   # ControlAccount detail
│   /projects/:projectId/control-accounts/:controlAccountId (ControlAccountOverview)
│
│   # WorkPackage detail subtree
│   /projects/:projectId/work-packages/:id (WorkPackageLayout — 6 child routes)
│       ├── index (Overview)
│       ├── cost-registrations
│       ├── cost-history
│       ├── evm-analysis
│       ├── documents
│       └── chat
│
├── /work-packages/:id (WorkPackageLayout — alternate top-level entry)
│
├── /cost-elements/:id (CostElementLayout — 5 child routes)
│   ├── index (Overview)
│   ├── cost-registrations
│   ├── cost-history
│   ├── documents
│   └── chat
│
└── /admin (Admin Menu)
    ├── /admin/users
    ├── /admin/organizational-units
    ├── /admin/cost-element-types
    ├── /admin/cost-event-types
    ├── /admin/ai-providers
    ├── /admin/ai-assistants
    ├── /admin/mcp-servers
    ├── /admin/rbac
    ├── /admin/role-assignments
    ├── /admin/change-order-config
    ├── /admin/projects
    └── /admin/wbs-elements
```

## When to Use PageNavigation

### Use PageNavigation when:

- An entity has multiple related views (Project, WBSElement, ControlAccount, WorkPackage, CostElement)
- Users need to switch between different aspects of the same entity
- Views should be accessible via shareable URLs
- Browser back/forward navigation is important

### Don't use PageNavigation when:

- Navigating between unrelated entities (use sidebar menu)
- Showing a simple list/detail drill-down (use breadcrumb + links)
- Displaying modal/overlay content (use Modal/Drawer)

## Future: Sidebar Variant

The `PageNavigation` component can be adapted for sidebar placement:

```tsx
<PageNavigation items={items} variant="sidebar" />
```

This will render vertical tabs suitable for placement in the AppLayout Sider. The same component and configuration can be used—only the container and variant prop need to change.

## Best Practices

1. **URL-First Design**: Always design navigation with URLs in mind
2. **Descriptive Paths**: Use clear, readable paths (e.g., `/projects/123/change-orders`)
3. **Consistent Naming**: Use consistent naming for similar navigation across entities
4. **Breadcrumb Support**: Include breadcrumbs for deeper navigation hierarchies
5. **Permission Awareness**: Hide navigation items based on user permissions when needed

## Migration Notes

### Old Pattern (Card-based)

```tsx
<Card title="Change Orders">
  <ChangeOrderList projectId={projectId} />
</Card>
```

### New Pattern (Tab-based)

```tsx
// ProjectOverview.tsx - no change orders card
// Change orders moved to dedicated page
```

Users accessing `/projects/123` see the Overview tab by default. Change Orders are accessed via the navigation tab.

## Related Components

- [AppLayout](frontend/src/layouts/AppLayout.tsx) - Main application layout
- [BreadcrumbBuilder](frontend/src/components/hierarchy/BreadcrumbBuilder.tsx) - Hierarchical navigation
- [ImpactAnalysisDashboard](frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) - Tab pattern example

## References

- React Router v6 Documentation: https://reactrouter.com/
- Ant Design Tabs: https://ant.design/components/tabs/
- Project Plan: [Contextual Navigation Iteration](../03-project-plan/iterations/2026-01-15-contextual-navigation/00-analysis.md) (historical — iteration completed, scope significantly exceeded)

---

*Last Updated: 2026-05-30*
