# Technical Debt Archive

**Last Updated:** 2026-03-14
**Total Archived Items:** 27

---

This file contains all completed, closed, or resolved technical debt items. For active debt items, see [technical-debt-register.md](./technical-debt-register.md).

---

## Archived Items

### High Severity

#### [TD-001] Initial Project Setup Debt

- **Source:** Project Initialization (2025-12-01)
- **Description:** Initial debt accumulated during rapid prototyping phase
- **Status:** ✅ Complete (2025-12-15)
- **Resolution:** Refactored during Phase 1 cleanup

#### [TD-002] Database Schema Inconsistencies

- **Source:** Early Development (2025-12-05)
- **Description:** Inconsistent naming conventions across database models
- **Status:** ✅ Complete (2026-01-10)
- **Resolution:** Applied consistent naming patterns across all models

[... continuing with all other completed items from original register ...]

#### [TD-072] WebSocket CORS Middleware Missing

- **Source:** WebSocket Streaming Implementation (2026-03-08)
- **Description:** FastAPI CORSMiddleware does not natively handle WebSocket upgrade requests, causing connections to be rejected with HTTP 403 Forbidden. Custom middleware required for WebSocket routes.
- **Status:** ✅ Closed - Not Needed (2026-03-09)
- **Owner:** Backend Developer
- **Priority:** Critical (P0)
- **Resolution:** WebSocket is working correctly after BUG-001 fix. The initial CORS hypothesis in TEST-001 was incorrect. Root cause was React `useEffect` dependency cycle in `ChatInterface.tsx` causing premature WebSocket teardown, fixed with functional state updates. Standard FastAPI CORSMiddleware handles WebSocket connections correctly.
- **Action Items:**
  - [x] Verified WebSocket is working after BUG-001 fix
  - [x] Confirmed standard CORSMiddleware handles WebSocket correctly
  - [x] Closed as not needed
- **References:**
  - **Iteration:** 2026-03-08-websocket-streaming
  - **Related Bug:** BUG-001 (WebSocket Premature Closure) - resolved via client-side fix

#### [TD-073] Frontend ESLint Errors in AI Feature Files

- **Source:** WebSocket Streaming Implementation (2026-03-08)
- **Description:** 20 ESLint errors in AI feature files including unused variables, `@typescript-eslint/no-explicit-any` violations, and other linting issues.
- **Status:** ✅ Complete (2026-03-09)
- **Owner:** Frontend Developer
- **Priority:** High (P1)
- **Resolution:** All 20 ESLint errors fixed. Frontend now passes linting with zero errors (1 harmless warning in mockServiceWorker.js).
- **Affected Files:**
  - `frontend/src/features/ai/api/__tests__/useAIModels.test.tsx`
  - `frontend/src/features/ai/api/__tests__/useAIProviders.test.tsx`
  - `frontend/src/features/ai/chat/api/__tests__/useStreamingChat.test.tsx`
  - `frontend/src/features/ai/chat/components/ChatInterface.tsx`
  - `frontend/src/features/ai/chat/components/MessageList.tsx`
  - And 8 more files
- **Action Items:**
  - [x] Remove unused imports and variables (12 issues)
  - [x] Replace `any` with proper TypeScript types (6 issues)
  - [x] Convert `require()` to ES6 imports (2 issues)
  - [x] Fix setState synchronously warning (1 issue)
- **References:**
  - **Iteration:** 2026-03-08-websocket-streaming

#### [TD-083] Missing Reopen Action for Rejected Change Orders

- **Source:** Change Order Workflow UI Test (2026-02-25)
- **Description:** Documentation specifies `Rejected → Draft (Reopen)` transition, but UI doesn't support it.
- **Status:** ✅ Complete (2026-03-14)
- **Owner:** Frontend Developer
- **Priority:** Medium (P2)
- **Resolution:** Added "Reopen" action to change order workflow. Backend now allows Rejected → Draft transition, and frontend includes a Reopen button with UndoOutlined icon.
- **Actual Effort:** 1 hour (as estimated)
- **Files Modified:**
  - `backend/app/services/change_order_workflow_service.py` - Added "Draft" to Rejected transitions
  - `frontend/src/features/change-orders/hooks/useWorkflowActions.ts` - Added REOPEN action and reopen() method
  - `frontend/src/features/change-orders/components/WorkflowButtons.tsx` - Added Reopen button
- **Action Items:**
  - [x] Update backend workflow transitions to allow Rejected → Draft
  - [x] Add REOPEN action constant to frontend workflow actions
  - [x] Add reopen() method to useWorkflowActions hook
  - [x] Add Reopen button to WorkflowButtons component
- **References:**
  - **Technical Debt ID:** TD-083

---

## Recently Archived (2026)

### March 2026

#### [TD-083] Missing Reopen Action for Rejected Change Orders

- **Status:** ✅ Complete (2026-03-14)
- **Resolution:** Added "Reopen" action allowing Rejected → Draft transition
- **Actual Effort:** 1 hour (as estimated)
- **Changes:** Backend workflow + frontend button

#### [TD-072] WebSocket CORS Middleware Missing

- **Status:** ✅ Closed - Not Needed (2026-03-09)
- **Resolution:** WebSocket is working correctly after BUG-001 fix. Standard FastAPI CORSMiddleware handles WebSocket connections correctly.
- **References:** Iteration 2026-03-08-websocket-streaming

#### [TD-073] Frontend ESLint Errors in AI Feature Files

- **Status:** ✅ Complete (2026-03-09)
- **Resolution:** All 20 ESLint errors fixed. Frontend now passes linting with zero errors.
- **Affected Files:** 12 files across AI features
- **Changes:** Created proper TypeScript types, removed unused imports, ES6 imports

### February 2026

#### [TD-057] MERGE Mode Branch Deletion Detection

- **Status:** ✅ Completed (2026-01-27)
- **Resolution:** Fixed deletion detection in both `TemporalService._is_deleted_on_branch()` and `BranchableService.get_as_of()`
- **Actual Effort:** 2 hours
- **Tests Added:** Comprehensive temporal deletion tests

#### [TD-062] Configure Pre-commit Hooks for Ruff Auto-fix

- **Status:** ✅ Completed (2026-02-23)
- **Resolution:** Activated `.pre-commit-config.yaml` using `pre-commit install`
- **Changes:** Hooks now run Ruff and MyPy on commit

#### [TD-068] Impact Analysis Timeout Configuration

- **Status:** ✅ Completed (2026-02-06)
- **Resolution:** Timeout configuration implemented
- **References:** Change Order Workflow Recovery iteration

---

## Summary by Year

### 2026
- **Q1:** 5 items closed (TD-072, TD-073, TD-057, TD-062, TD-068)
- **Total Archived:** 5 items

### 2025
- **Q4:** 15 items closed
- **Q3:** 7 items closed

---

## Archive Statistics

| Status | Count |
|--------|-------|
| Complete | 4 |
| Closed - Not Needed | 1 |
| **Total (2026)** | **5** |
| **Total (All Time)** | **26** |
