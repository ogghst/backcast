# IT-FE-02: Testing Infrastructure - PLAN

**Status:** ✅ Approved
**Created:** 2026-01-03
**Approver:** User (Option B)

---

## Phase 1: Context Analysis

### Documentation Review

- **Architecture**: `docs/02-architecture/frontend/contexts/04-quality-testing.md` specifies MSW for mocking and Playwright for E2E (E2E deferred).
- **Project Plan**: IT-FE-01 completed, establishing the foundation. This iteration builds the infrastructure for reliable testing and component development.

### Codebase Analysis

- **Current Stack**: Vite, Vitest, React Testing Library.
- **Missing Infrastructure**:
  - No `msw` for network mocking (tests currently rely on manual mocks or partial integration).
  - No `storybook` for isolated component development.
- **Dependencies**: `package.json` confirms `vite`, `vitest`, `typescript` are present. Need to add `msw` and `@storybook/*`.

---

## Phase 2: Problem Definition

### 1. Problem Statement

**Problem:** The frontend currently lacks a robust mechanism for mocking API calls, leading to brittle tests or dependency on a running backend. Additionally, there is no environment for developing UI components in isolation, slowing down UI iteration.

**Importance:**

- **Reliability:** Tests should not fail because the backend is down or data changed.
- **Velocity:** UI developers need to work on components without navigating complex app flows.
- **Documentation:** Component library documentation is non-existent.

### 2. Success Criteria

**Functional Criteria:**

- MSW intercepts API requests in unit tests (`vitest`).
- MSW intercepts API requests in development (optional/configurable).
- Storybook runs and renders basic components.
- Storybook integrates with MSW to mock data for components.

**Technical Criteria:**

- **Test Coverage:** Existing tests pass with MSW enabled.
- **Performance:** Test suite duration remains under acceptable limits (<30s).

### 3. Scope Definition

**In Scope:**

- Installing and configuring MSW (Mock Service Worker).
- Creating basic handlers for User/Auth endpoints.
- Installing and configuring Storybook (latest version).
- Integrating Storybook with MSW.
- Documenting usage patterns.

**Out of Scope:**

- Migrating _all_ existing manual mocks (if any) to MSW (will do pilot only).
- Visual regression testing (Snapshot testing).
- E2E Testing (Playwright).

---

## Phase 3: Implementation Options

| Aspect          | Option A: Basic Setup                                                                    | Option B: Full Integration (Recommended)                                                          |
| --------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Approach**    | Install MSW for Node (tests) only. Install Storybook standalone.                         | MSW for Node (tests) AND Browser (worker). Storybook with MSW addon.                              |
| **Pros**        | Simpler setup, less boilerplate.                                                         | Consistent mocking across Tests, Dev, and Storybook. Visual verification of loading/error states. |
| **Cons**        | Duplicated logic if we want to mock in dev later. Storybook components can't fetch data. | Higher initial configuration effort.                                                              |
| **Risk**        | Low                                                                                      | Low/Medium (potential configuration nuances with Vite)                                            |
| **Est. Effort** | 0.5 Days                                                                                 | 1 Day                                                                                             |

**Recommendation: Option B (Full Integration)**
This provides the most value:

1.  **Unified Mocks:** Write handlers once, use them in Vitest, Storybook, and even local dev (off-line mode).
2.  **Component Stories:** We can write stories for "Loading", "Error", and "Success" states by reusing MSW handlers.

---

## Phase 4: Technical Design

### Directory Structure

```
frontend/src/mocks/
├── handlers.ts       # Shared Request Handlers
├── server.ts         # Node setup (for Vitest)
└── browser.ts        # Browser setup (for Storybook/Dev)
```

### Storybook Integration

- Use `msw-storybook-addon` to serve mocks in stories.
- `.storybook/preview.tsx` wraps stories with providers (QueryClient, Theme, Router).

### TDD Test Blueprint

1.  **Verify MSW in Tests:**

    - Create a test that fetches data from a mocked endpoint.
    - Assert that the data returned matches the mock, not the real backend.

2.  **Verify Storybook MSW:**
    - Create a Story for a data-fetching component (e.g., `UserList`).
    - Define a specific MSW handler override for that story.
    - Verify the component renders the mocked data.

---

## Phase 5: Risk Assessment

| Risk Type   | Description                                  | Mitigation Strategy                                                             |
| ----------- | -------------------------------------------- | ------------------------------------------------------------------------------- |
| Technical   | MSW conflict with generic `fetch` or `axios` | Use MSW's standard setup; verified compatibility with Axios via `http` handler. |
| Technical   | Storybook build failure with Vite            | Use `storybook-builder-vite` (default in SB 7/8).                               |
| Integration | `node_modules` bloated                       | Use dev dependencies properly; ignore storybook-static in build.                |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Dependencies & Setup (MSW):** 2 hours
- **Dependencies & Setup (Storybook):** 2 hours
- **Integration (Storybook + MSW):** 2 hours
- **Pilot Implementation (Handlers + 1 Story):** 2 hours
- **Documentation:** 1 hour
- **Total:** ~1.5 Days (assuming 6h effective work/day)

### Prerequisites

- IT-FE-01 completion (Done).
