# Context: Authentication & Authorization

## 1. Overview

This context handles user identity verification (Authentication) and access control (Authorization). It ensures that:

1.  Users are correctly identified via JWT tokens.
2.  Protected resources are only accessible to authorized users.
3.  The UI reacts dynamically to user permissions and roles.

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
    - Backend returns `access_token`.
    - Frontend stores token in `localStorage`.
4.  **Profile Fetch**:
    - Frontend calls `GET /api/v1/auth/me` with Bearer token.
    - Backend returns complete `UserPublic` profile, including a **flattened list of permissions**.
5.  **State Update**: `useAuthStore` updates `user` object and `permissions` array.
6.  **Redirect**: Router pushes user to `/` (Dashboard).

### 3.2 Authorization Flow (Access Check)

1.  **Request**: Component asks "Can user perform X?"
2.  **Resolution**:
    - `useAuthStore.getState().hasPermission('X')` checks the `permissions` array.
    - This array is populated by the Backend's RBAC service during the `/auth/me` call.
3.  **Enforcement**:
    - **Frontend**: Hides UI element via `<Can>` or redirects via `ProtectedRoute`.
    - **Backend**: API endpoints enforce the same check using `RoleChecker` dependency. This ensures security even if Frontend logic is bypassed.

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
  permission?: Permission; // e.g. "user-read"
  role?: Role; // e.g. "admin"
  match?: "all" | "any"; // Logic for multiple checks
  fallback?: React.ReactNode;
  children: React.ReactNode;
};
```

## 5. Security Considerations

- **Frontend vs Backend**: Frontend checks are for **UX only** (hiding unreachable buttons). All security is enforced by the Backend API.
- **Token Storage**: `localStorage` is used. XSS protection is handled by standard React escaping and Content Security Policy (CSP).
