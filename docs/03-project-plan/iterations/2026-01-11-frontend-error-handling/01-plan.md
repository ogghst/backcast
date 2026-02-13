# Plan: Global Frontend Error Handling

## 1. Objective

Fix the critical bug where login fails with 422 errors and subsequently crashes the frontend app due to invalid React child errors. Implement a robust global error handling mechanism.

## 2. Root Cause Analysis

1.  **422 Error**: The `src/api/client.ts` file was setting a global default header `Content-Type: application/json`. This overrode the `application/x-www-form-urlencoded` header required by the `AuthenticationService.login` method (and correctly set by the generated client). The backend received JSON but expected form data, resulting in a validation error (422).
2.  **Frontend Crash**: The Global Interceptor and Login component were attempting to render the raw 422 error object (which contains arrays of Pydantic validation errors) directly into a `toast` or component. React cannot render objects as children, causing the crash.

## 3. Implementation Plan

### 3.1. Infrastructure

- [x] Create `src/utils/apiError.ts` to safely parse various error formats (Axios, Pydantic arrays, generic Errors) into a single string.

### 3.2. Fixes

- [x] **Remove Global Header**: Delete `axios.defaults.headers.common["Content-Type"] = "application/json"` from `src/api/client.ts`. Axios defaults will suffice, and generated clients will set specific headers as needed.
- [x] **Update Interceptor**: Modify `src/api/client.ts` to use `getErrorMessage()` for the global error toast.
- [x] **Update Login Page**: Modify `src/pages/Login.tsx` to use `getErrorMessage()` for local error state handling.

### 3.3. Verification

- [x] Verify backend login endpoint via cURL with correct content type.
- [ ] Manual verification of frontend login (completed by user/agent).

## 4. Risks & Mitigations

- **Risk**: Other endpoints might rely on the global JSON header if the generated client doesn't set it.
- **Mitigation**: The generated `request.ts` helper sets `Content-Type: application/json` by default when `body` is present and not FormData. See `getHeaders` function in `request.ts`.
