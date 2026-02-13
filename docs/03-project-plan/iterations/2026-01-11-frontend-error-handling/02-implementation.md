# Implementation: Global Frontend Error Handling

## 1. Overview

Successfully implemented the global error handling fixes and resolved the Login crash/422 issues.

## 2. Changes

### 2.1. `src/utils/apiError.ts`

- Created a utility function `getErrorMessage(error: unknown): string`.
- Handles:
  - Axios response objects (`error.response.data.detail`).
  - Pydantic validation error arrays (formats them as "Field: Error Message").
  - Generic JS Error objects.
  - Fallback strings.

### 2.2. `src/api/client.ts`

- **Removed**: `axios.defaults.headers.common["Content-Type"] = "application/json"`.
  - _Rationale_: This global default was forcing JSON on `form-urlencoded` requests (like Login), causing 422s.
- **Updated**: Response interceptor now uses `getErrorMessage(error)` to display safe, readable toast notifications instead of crashing.

### 2.3. `src/pages/Login.tsx`

- **Updated**: `onFinish` handler now uses `getErrorMessage(error)` to set the local `errorMessage` state, preventing React rendering crashes when complex error objects are returned.

## 3. Verification

- **Backend Logic**: Confirmed via `curl` that the backend accepts `application/x-www-form-urlencoded` and returns 200 OK with valid credentials (`admin@backcast.org`).
- **Frontend Logic**: The removal of the global header allows the generated client's specific content-type header to take precedence, fixing the 422 error.

## 4. Next Steps

- Close this iteration.
- Monitor for any other endpoints that might have implicitly relied on the global JSON header (unlikely given generated code patterns).
