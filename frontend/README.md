# Frontend Architecture

This project uses **React** with **Vite**, **TypeScript**, **Ant Design**, **Zustand**, and **React Query**.

## Directory Structure

The `src` directory is organized by function, with support for feature-based modularity:

| Directory | Purpose |
| :--- | :--- |
| `src/api` | API client configuration (Axios) and backend service definitions. |
| `src/assets` | Static assets (global CSS, images). |
| `src/components` | Shared, generic UI components (atoms/molecules). Not feature-specific. |
| `src/config` | Global configuration (Themes, Envs, Constants). |
| `src/features` | Vertical slices of functionality. Each folder (e.g., `projects`) contains its own routes, components, hooks, etc. |
| `src/hooks` | Shared custom React hooks. |
| `src/layouts` | Page layouts (e.g., `AppLayout`, `AuthLayout`). |
| `src/pages` | Route entry points (keep these minimal, delegated to features or components). |
| `src/routes` | Centralized router configuration (`react-router-dom`). |
| `src/stores` | Global state management (Zustand). |
| `src/types` | Shared TypeScript type definitions. |
| `src/utils` | Pure utility functions and helpers. |

## Key Concepts

- **Styling**: We use Ant Design's `ConfigProvider` for theming (`src/config/theme.ts`). Avoid inline styles; use Ant Design tokens or styled-components if needed.
- **Data Fetching**: Use `@tanstack/react-query` for all server state. Configure the client in `src/main.tsx`.
- **State Management**: Use `zustand` for client-side global state.
- **Routing**: Defined in `src/routes/index.tsx`.

## Commands

- `npm run dev`: Start development server.
- `npm run build`: Type-check and build for production.
- `npm run lint`: Run ESLint.
- `npm run format`: Format code with Prettier.
