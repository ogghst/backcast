# Context: Authentication & Authorization

**Last Updated:** 2026-07-01

## 1. Overview

This context handles user identity verification (Authentication) and access control (Authorization). It ensures that:

1.  Users are correctly identified via JWT tokens.
2.  Protected resources are only accessible to authorized users.
3.  The UI reacts dynamically to user permissions and scoped roles.

> **Note:** The backend uses the **Unified RBAC System** (ADR-014; supersedes ADR-007) with scoped role assignments (global/project/change_order). Frontend permission checks receive the user's expanded permission list for their global role.

## 2. Technical Patterns

### 2.1 Store-Based State Management

We use **Zustand** (`useAuthStore`) as the single source of truth for auth state.

- **Persistence**: Tokens and minimal user data are persisted to `localStorage` to survive refreshes.
- **Reactivity**: Components subscribe to specific slices of the store (e.g., `permissions`, `user.role`) to re-render automatically when access rights change.

### 2.2 Declarative Authorization (`<Can>`)

To avoid scattered `if` statements in JSX, we use the `<Can>` component for conditional rendering.

- **Pattern**: Render Props / Wrapper.
- **Usage**: `<Can permission="user-create">{children}</Can>`
- **Logic**: Checks if the current user has the specified permission. If yes, renders children; otherwise, renders `fallback` (or null).

### 2.3 Hook-Based Access (`usePermission`)

For logic outside of rendering (e.g., inside `useEffect` or event handlers), we use the `usePermission` hook.

- **Functionality**: Exposes `hasPermission(permission)` and `hasRole(role)`.
- **Subscription**: **Critical**: This hook explicitly subscribes to the `authStore` to ensure that consumers re-run when permissions change (e.g., after login/logout).

### 2.4 Route Protection (`ProtectedRoute`)

React Router wrapper that guards entire pages.

- **Logic**: Checks for valid token/user. If missing, redirects to `/login`.
- **Role Guards**: Can optionally enforce `requiredRoles`.

## 3. Flows

### 3.1 Authentication Flow (Login)

1.  **User Input**: User submits `LoginForm`.
2.  **API Call**: `POST /api/v1/auth/login` (Body: email, password).
3.  **Token Handling**:
    - Backend returns **both** an `access_token` (short-lived) and a `refresh_token` (default 30 days, `REFRESH_TOKEN_EXPIRE_DAYS` in `backend/app/core/config.py`).
    - Frontend stores both tokens in `localStorage`.
4.  **Profile Fetch**:
    - Frontend calls `GET /api/v1/auth/me` with Bearer access token.
    - Backend returns complete `UserPublic` profile, including the **expanded permission list** for the user's global role.
5.  **State Update**: `useAuthStore` updates `user` object and `permissions` array.
6.  **Redirect**: Router pushes user to `/` (Dashboard).

**Token Refresh:** When the access token nears expiry, `POST /api/v1/auth/refresh` (body: `{ refresh_token }`) mints a new access token from the still-valid refresh token. `POST /api/v1/auth/logout` revokes the refresh token (idempotent).

### 3.2 Authorization Flow (Access Check)

1.  **Request**: Component asks "Can user perform X?"
2.  **Resolution**:
    - `useAuthStore.getState().hasPermission('X')` checks the `permissions` array.
    - This array is populated by the Backend's `UnifiedRBACService` during the `/auth/me` call.
    - Permissions are flattened across all scopes (global + project + change_order) for the user.
3.  **Enforcement**:
    - **Frontend**: Hides UI element via `<Can>` or redirects via `ProtectedRoute`.
    - **Backend**: API endpoints enforce the same check using `RoleChecker` or `ProjectRoleChecker` dependencies, which delegate to `UnifiedRBACService`. This ensures security even if Frontend logic is bypassed.

> **Scoped Permissions Note:** The backend resolves permissions based on the request context (e.g., project ID in URL). The frontend receives all permissions but may not know which scope granted them. For project-scoped actions, the backend validates access to the specific project.

### 3.3 Permission Catalog (FE Gating Concerns)

Several permissions require explicit FE gating beyond the basic CRUD set:

- **`portfolio-read`** — Grants access to the global/portfolio dashboard route. Seeded to `admin`, `manager`, `cost-controller`, `pmo-director`, `ai-manager`, `ai-admin` (manager+ only, locked decision). **Deliberately NOT** granted to `viewer` / `ai-viewer` (`backend/app/db/seed_users_rbac.py`). The portfolio dashboard route must gate on this permission.

- **`role-assignment-{read,create,update,delete}`** — Admin-only permissions governing the role-assignment CRUD UI. Seed restricts these to the `admin` role only.

- **Admin wildcard convention (backend).** Internally, `UnifiedRBACService.get_user_permissions()` returns the literal `["*"]` for admin (`backend/app/core/rbac_unified.py:609-610`). However, the `/auth/me` path resolves permissions via `UserPublic.from_user_async()`, which sends the **expanded** admin permission list — so the FE never receives the bare `["*"]` token and the standard `hasPermission(p)` / `<Can permission="p">` checks work normally for admins. The FE does not need to special-case `["*"]`.

### 3.4 Any-Of Permission Mode (`required_permissions`)

The backend `RoleChecker` supports an any-of mode: `RoleChecker(required_permissions=["project-read", "portfolio-read"])` grants access if the user holds **any** listed permission (`backend/app/api/dependencies/auth.py:154-218`). The dashboard-layouts route uses this to serve both project-read and portfolio-read holders (`backend/app/api/routes/dashboard_layouts.py:38`).

The FE mirrors this with the `<Can>` component's array form: passing `permission={[...]}` requires ANY of the listed permissions (use `requireAll` to switch to ALL):

```tsx
<Can permission={["project-read", "portfolio-read"]}>
  <GlobalDashboardLink />
</Can>
```

## 4. Key Components

### `AuthStore`

```typescript
interface AuthState {
  token: string | null;
  user: UserPublic | null;
  permissions: string[]; // e.g. ["user-read", "department-write"]
  login: (token: string) => Promise<void>;
  logout: () => void;
  // ... helpers
}
```

### `<Can>` Component

```tsx
type CanProps = {
  permission?: Permission | Permission[]; // single, or array (ANY-of by default)
  role?: Role | Role[]; // single, or array (user role must be in list)
  requireAll?: boolean; // when permission is an array: require ALL (default: ANY)
  fallback?: React.ReactNode;
  children: React.ReactNode;
};
```

`<Can>` is implemented in `frontend/src/components/auth/Can.tsx` and delegates to the `hasPermission` / `hasAnyPermission` / `hasAllPermissions` / `hasRole` selectors on `useAuthStore`.

## 5. Security Considerations

- **Frontend vs Backend**: Frontend checks are for **UX only** (hiding unreachable buttons). All security is enforced by the Backend API.
- **Token Storage**: `localStorage` is used. XSS protection is handled by standard React escaping and Content Security Policy (CSP).
