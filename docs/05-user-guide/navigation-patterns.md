# Frontend Navigation Patterns

This document describes the navigation patterns used in the Backcast EVS frontend application.

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
│  │  [Overview] [Change Orders] [Settings] ...          │    │
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

For entities with multiple related views (e.g., Project → Overview, Change Orders, Settings), use nested routing:

### Directory Structure

```
frontend/src/pages/projects/
├── ProjectLayout.tsx          # Layout wrapper with PageNavigation
├── ProjectOverview.tsx        # Overview tab content
└── ProjectChangeOrdersPage.tsx # Change Orders tab content
```

### Route Configuration

```tsx
// routes/index.tsx
{
  path: "/projects/:projectId",
  element: <ProjectLayout />,
  children: [
    { index: true, element: <ProjectOverview /> },
    { path: "change-orders", element: <ProjectChangeOrdersPage /> },
  ],
}
```

### Layout Component

```tsx
// ProjectLayout.tsx
import { Outlet, useParams } from "react-router-dom";
import { PageNavigation } from "@/components/navigation";

export const ProjectLayout = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const items = [
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
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
/ (Dashboard)
├── /projects (Project List)
│   └── /projects/:projectId
│       ├── /projects/:projectId (Overview - index)
│       ├── /projects/:projectId/change-orders (Change Orders)
│       └── /projects/:projectId/change-orders/:changeOrderId/impact (Impact Analysis)
├── /admin (Admin Menu)
│   ├── /admin/users
│   ├── /admin/departments
│   └── /admin/cost-element-types
└── /projects/:projectId/wbes/:wbeId (WBE Detail - legacy, may be refactored)
```

## When to Use PageNavigation

### Use PageNavigation when:

- An entity has multiple related views (Project, WBE)
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

- [AppLayout](../../../frontend/src/layouts/AppLayout.tsx) - Main application layout
- [BreadcrumbBuilder](../../../frontend/src/components/hierarchy/BreadcrumbBuilder.tsx) - Hierarchical navigation
- [ImpactAnalysisDashboard](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) - Tab pattern example

## References

- React Router v6 Documentation: https://reactrouter.com/
- Ant Design Tabs: https://ant.design/components/tabs/
- Project Plan: [Contextual Navigation Iteration](../03-project-plan/iterations/2026-01-15-contextual-navigation/00-analysis.md)
