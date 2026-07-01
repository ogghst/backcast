# Context: Core Architecture & Layout

**Last Updated:** 2026-07-01

## 1. Overview

The Core context defines the application shell, routing strategy, and foundational patterns that support all other features. It is responsible for the "skeleton" of the Single Page Application (SPA).

## 2. Technology Stack

- **Framework**: React 18
- **Build System**: Vite (SWC)
- **Routing**: React Router DOM v6
- **Language**: TypeScript 5+

## 3. Architecture

### 3.1 App Shell

The application is wrapped in a series of global providers. The wiring is split across two files:

**`src/main.tsx`** (bootstrap, outermost-first):

1.  `ErrorBoundary`: Local boundary (`src/components/ErrorBoundary.tsx`, built on `react-error-boundary`) — not Sentry; it renders an antd `Result` fallback and has a TODO to wire a monitoring service in production.
2.  `QueryClientProvider`: Server state caching, plus an IndexedDB-backed `persistQueryClient` persister (`createIDBPersister`, 24h maxAge) so the cache survives reloads.
3.  `TimeMachineProvider`: Global temporal-context provider (`src/contexts/TimeMachineContext`) for the Time-Machine panel.
4.  `ReactQueryDevtools`.

**`src/App.tsx`** (inside the above):

5.  `ConfigProvider`: Ant Design theming and locale, including dark-mode algorithm/tokens.
6.  `RouterProvider`: Handling URL navigation.

### 3.2 Routing Strategy

Defined in `src/routes/`.

- **Centralized Config**: All routes are defined in a single router object (or gathered from feature modules).
- **Layouts** (live in `src/layouts/`):
  - `AppLayout`: Authenticated application shell. The header no longer owns navigation or the account menu — both moved into a collapsible `AppSidebar` (rail vs expanded modes) backed by `useNavigationStore`. The shell also renders `WaveBackground`, a `MobileSidebarDrawer`, a `SearchDialog` (Ctrl+K), a `NotificationBell`, and an expandable Time-Machine panel (`TimeMachineCompact`/`TimeMachineExpanded`). The `Content` panel is intentionally transparent so the wave shows through and floats the page cards.
  - `AuthLayout`: Public view for Login/Register.
- **Lazy Loading**: Route components are lazy-loaded via `React.lazy` (~40 routes) in `src/routes/index.tsx`, fed into `createBrowserRouter`; `AppLayout` wraps each lazy `<Outlet />` in a `<Suspense>` spinner fallback.

### 3.3 Directory Structure

There is no `src/core`. The root-level folders managing these concerns are:

- `src/layouts/`: Layout shells (`AppLayout`, `AuthLayout`).
- `src/components/navigation/`: Application navigation — `AppSidebar`, `MobileSidebarDrawer`, `SidebarContent`, `SidebarFlyout`, `SidebarChatHistory`, and the nav-item builders (`entityNavItems`, `adminNavItems`, `accountMenuItems`).
- `src/components/layout/`: Page-chrome primitives shared by entity pages — `PageShell`, `PageWrapper`, `PageHeader`, `PageContent`, plus `CardTitleRow`, `StatusTag`, `NotFoundState`. (The project-scoped `ProjectPage` wrapper lives in `src/features/projects/components/`.)
- `src/config/`: Environment variables (`VITE_API_URL`) and static configuration.
- `src/types/`: Global strict TypeScript definitions.

### 3.4 Authentication & Authorization

Implemented via **Zustand** for global state and custom hooks for access control.

- **State Management**: `useAuthStore` handles user session, token storage (`localStorage`), and permission arrays.
- **Declarative Authorization**: `<Can permission="user-read">` component conditionally renders UI elements.
- **Programmatic Checks**: `usePermission()` hook provides `hasPermission` and subscribes to state changes for reactive UI updates (e.g., menu visibility).

## 4. Key Decisions

- **Vite over CRA**: Chosen for superior build performance (esbuild/swc).
- **Strict TypeScript**: No `any` allow-list to ensure robust interfaces between backend and frontend.

## 5. Strong Typing

Code shall enforce robustness and type safety. No `any` allow-list shall be used. All types shall be defined in the `src/types` folder.
