# Context: Core Architecture & Layout

## 1. Overview

The Core context defines the application shell, routing strategy, and foundational patterns that support all other features. It is responsible for the "skeleton" of the Single Page Application (SPA).

## 2. Technology Stack

- **Framework**: React 18
- **Build System**: Vite (SWC)
- **Routing**: React Router DOM v6
- **Language**: TypeScript 5+

## 3. Architecture

### 3.1 App Shell

The application is wrapped in a series of global providers in `src/main.tsx`:

1.  `QueryClientProvider`: Server state caching.
2.  `ConfigProvider`: Ant Design theming and locale.
3.  `RouterProvider`: Handling URL navigation.
4.  `ErrorBoundary` (Sentry): Catching unhandled exceptions.

### 3.2 Routing Strategy

Defined in `src/routes/`.

- **Centralized Config**: All routes are defined in a single router object (or gathered from feature modules).
- **Layouts**:
  - `AppLayout`: Authenticated dashboard view with Sidebar/Header.
  - `AuthLayout`: Public view for Login/Register.
- **Lazy Loading**: Route components should be lazy-loaded using `React.lazy` (pending implementation) to optimize bundle size.

### 3.3 Directory Structure

The `src/core` or root-level folders manage these concerns:

- `src/layouts/`: Component wrappers for pages.
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
