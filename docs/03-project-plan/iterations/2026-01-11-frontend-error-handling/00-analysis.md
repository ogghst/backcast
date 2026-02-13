# Request Analysis: Global Frontend Error Handling

## Clarified Requirements

The goal is to implement a **general and transparent error handling solution** for the frontend that:

1.  Intersects all backend requests.
2.  Detects "bad responses" (non-2xx status codes or network errors).
3.  Automatically displays a **toaster notification** (using `sonner`) to warn the user.
4.  Follows architectural standards and replaces ad-hoc error handling.

This solution must be **transparent**, meaning individual components or hooks shouldn't need to manually trigger the toaster for standard errors.

## Context Discovery Findings

**Architecture & Codebase Analysis:**

- **API Client Generation**: The project uses `openapi-typescript-codegen` to generate services (`ProjectsService`, etc.).
- **Request Logic**: The generated code uses `src/api/generated/core/request.ts`, which imports the **global** `axios` instance by default:
  ```typescript
  import axios from 'axios';
  // ...
  export const request = <T>(..., axiosClient: AxiosInstance = axios): ...
  ```
- **Current Configuration (`src/api/client.ts`)**:
  - Currently, `client.ts` creates a **custom** axios instance (`apiClient = axios.create(...)`) and adds interceptors (auth token injection, 401 handling) to _that specific instance_.
  - **CRITICAL FINDING**: The generated services (e.g., `ProjectsService`) DO NOT use this `apiClient`. They use the default global `axios` instance.
  - This means the existing 401 interceptor (and potentially the auth header injection, though `OpenAPI.TOKEN` handles that separately) is likely **inactive** for generated API calls.
- **Toast Library**: The project uses `sonner` (`<Toaster />` is present in `App.tsx`).
- **State Management**: `TanStack Query` is used for server state.

---

## Solution Options

### Option 1: Global Axios Configuration (Recommended)

Refactor `src/api/client.ts` to configure the **global** `axios` singleton instead of creating a separate `apiClient` instance. Attach the error handling interceptor directly to the global `axios` object.

**Architecture & Design:**

- Modify `client.ts` to import `axios` and apply `interceptors` to the default export.
- Add a response interceptor that:
  1.  Checks for error status.
  2.  Dispays a `toast.error()` with a user-friendly message.
  3.  Rejects the promise so specific catch blocks can still operate if needed.
- Retain (and fix) the 401 redirect logic in the same interceptor.

**UX Design:**

- Users see a consistent toast notification (e.g., "Server Error: Failed to save project") immediately upon failure.
- No changes to component code required.

**Implementation:**

- Edit `src/api/client.ts`
- Remove `axios.create()`.
- Apply settings/interceptors to `axios`.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| **Pros** | • **Fixes existing bug**: Ensures generated code uses the interceptors.<br>• **Universal**: Catches all requests, generated or custom.<br>• **Low Boilerplate**: One-time setup. |
| **Cons** | • **Global Mutation**: Modifying global `axios` can be cleaner with dependency injection, but the generated code defaults to global. |
| **Complexity** | Low. |
| **Maintainability** | High. Centralized logic. |

### Option 2: TanStack Query Global Callbacks

Configure the `QueryClient` with global `onError` callbacks in `mutationCache` and `queryCache`.

**Architecture & Design:**

- In `main.tsx` (or where `queryClient` is created), add `queryCache: new QueryCache({ onError: ... })` and `mutationCache: new MutationCache({ onError: ... })`.
- Trigger `toast.error` inside these callbacks.

**UX Design:**

- Same visual result for queries/mutations managed by React Query.

**Implementation:**

- Modify `src/main.tsx`.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| **Pros** | • **React Context**: Tightly integrated with the React lifecycle.<br>• **Granular**: Can be overridden per-query easily. |
| **Cons** | • **Incomplete Coverage**: Does NOT catch requests made outside of React Query (though strictly disallowed, they might exist).<br>• **Does Not Fix 401**: The generated client issues persist; we still need to fix `client.ts` separately. |
| **Complexity** | Low. |
| **Maintainability** | Good. |

### Option 3: Custom Request Wrapper

Modify the generated code or wrap every service call.

**Trade-offs:**

- **Cons**: Violates "Do not edit generated code" or requires massive boilerplate to wrap every service method. **Discarded.**

---

## Comparison Summary

| Criteria               | Option 1 (Global Axios)          | Option 2 (React Query)          |
| :--------------------- | :------------------------------- | :------------------------------ |
| **Development Effort** | Low (Fixes `client.ts`)          | Low (Configures `QueryClient`)  |
| **Coverage**           | **100% of HTTP Requests**        | React Query Hooks Only          |
| **Architectural Fix**  | **Fixes 401 interceptor bug**    | Ignores underlying client issue |
| **Best For**           | **Robust, system-wide handling** | React-only handling             |

## Recommendation

**I recommend Option 1.**

It solves two problems at once:

1.  It implements the requested **global error toaster**.
2.  It **fixes the critical architectural bug** where generated services were ignoring the existing authentication/error interceptors because they used a different `axios` instance.

## Questions for Decision

1.  Do you agree with the diagnosis regarding the unused `apiClient`?
2.  Should we suppress the toaster for specific error codes (e.g., 404s might be handled by UI "Not Found" states instead of toasts)?
