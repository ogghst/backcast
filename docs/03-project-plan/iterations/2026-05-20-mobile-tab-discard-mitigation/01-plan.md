# Plan: Mobile Tab Discard Mitigation

**Created:** 2026-05-20
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 -- Progressive Enhancement (staleTime + IndexedDB persistence + persistent storage)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 from analysis -- Progressive Enhancement
- **Architecture**: Frontend-only change. Configure TanStack Query with global staleTime/gcTime defaults, persist its cache to IndexedDB via `@tanstack/react-query-persist-client` + `idb-keyval`, and request `navigator.storage.persist()` to protect IndexedDB from browser eviction.
- **Key Decisions**:
  1. Bundle all three items together in a single iteration (staleTime, IndexedDB persistence, persistent storage)
  2. Clear entire persisted cache on logout (no selective RBAC filtering during persistence -- instead, wipe on session boundary)
  3. Exclude AI chat queries (`queryKeys.ai.chat.*`) from persistence to avoid stale streaming state
  4. Exclude RBAC-sensitive queries (`queryKeys.users.me`, `queryKeys.adminRbac.*`, `queryKeys.roleAssignments.*`) from persistence via `dehydrateOptions.shouldDehydrateQuery` filter
  5. Time Machine state (branch/asOf/mode) requires NO special handling because query keys include context parameters, so mismatched context simply causes a cache miss and fresh fetch
  6. No PWA, no service worker, no manifest in this iteration

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: After a simulated mobile tab discard (full page reload), the UI renders meaningful content without a loading spinner for data that was previously fetched and is within the staleTime window. VERIFIED BY: manual test with Chrome DevTools "simulate tab discard" + Playwright reload test
- [ ] FC-2: Background revalidation updates the UI after cache restore when data is stale (beyond staleTime but within gcTime). VERIFIED BY: observe network requests after reload confirming refetch-on-mount behavior
- [ ] FC-3: On logout, the IndexedDB persisted cache is completely cleared. VERIFIED BY: inspect IndexedDB via DevTools after logout confirming empty state
- [ ] FC-4: AI chat query data is never persisted to IndexedDB. VERIFIED BY: inspect persisted cache content confirming absence of `ai.chat` keys
- [ ] FC-5: RBAC-sensitive query data (users.me, adminRbac, roleAssignments) is never persisted to IndexedDB. VERIFIED BY: inspect persisted cache content confirming absence of those keys
- [ ] FC-6: Existing mutation invalidation patterns continue to work correctly after persistence is active. VERIFIED BY: existing integration tests pass unchanged
- [ ] FC-7: Time Machine context changes (branch/asOf/mode) continue to trigger correct invalidation and fresh data loading. VERIFIED BY: manual Time Machine interaction test after persistence is active
- [ ] FC-8: `navigator.storage.persist()` is called once after authentication and the result is logged. VERIFIED BY: console log verification + DevTools Application > Storage > "Persistent" badge

**Technical Criteria:**

- [ ] TC-1: Bundle size increase is under 6KB gzipped (the two new dependencies). VERIFIED BY: `npm run build` comparison before/after
- [ ] TC-2: IndexedDB read on app startup completes under 100ms for typical cache sizes. VERIFIED BY: performance measurement in DevTools
- [ ] TC-3: Zero TypeScript errors (`npm run typecheck`). VERIFIED BY: CI pipeline
- [ ] TC-4: Zero ESLint errors (`npm run lint`). VERIFIED BY: CI pipeline
- [ ] TC-5: All existing tests pass (`npm test`). VERIFIED BY: test runner

**TDD Criteria:**

- [ ] TDD-1: Unit tests written for persistence filter logic before or alongside implementation
- [ ] TDD-2: Unit tests written for cache-clear-on-logout behavior
- [ ] TDD-3: Test coverage for new/modified files >= 80%

### Scope Boundaries

**In Scope:**

- Configure `QueryClient` with `staleTime: 2 min`, `gcTime: 30 min` global defaults
- Install `@tanstack/react-query-persist-client` and `idb-keyval`
- Create IndexedDB persister module with `shouldDehydrateQuery` filter
- Integrate `persistQueryClient` into app initialization in `main.tsx`
- Add `navigator.storage.persist()` call in auth flow
- Clear persisted cache on logout via `persister.removeClient()`
- Unit tests for filter logic and cache clearing
- Update the 7 existing hooks with custom staleTime overrides to ensure they still make sense with the new global default (review only, no changes expected since they already express domain-specific overrides)

**Out of Scope:**

- PWA / Service Worker / Web App Manifest (Option 2 from analysis)
- Offline capability
- Persisting AI chat queries or messages
- Changes to the Time Machine store or context
- Backend changes
- Mobile-specific UI adaptations

---

## Time Machine Racing Investigation

**Question:** Could IndexedDB cache restoration race with Time Machine state restoration, causing stale/wrong data display?

**Finding:** No race condition exists. The concern is resolved safely by existing architecture.

**Reasoning:**

1. **Time Machine state** is persisted to `localStorage` (key: `time-machine-storage`) via Zustand's `persist` middleware. `localStorage` is synchronous and fully available before any async code runs.

2. **TanStack Query cache** is persisted to `IndexedDB` and restored asynchronously via `persistQueryClientRestore`. IndexedDB restoration always completes AFTER synchronous localStorage restoration.

3. **Query keys include context parameters.** For example, `queryKeys.costElements.detail(id, { asOf, branch, mode })` produces keys like `["cost-elements", "detail", id, { asOf: "...", branch: "BR-001", mode: "merged" }]`.

4. **Exact key matching** means: if the user changed Time Machine state before the tab was discarded, the restored IndexedDB cache contains entries keyed with OLD context values. The new session emits queries keyed with the localStorage-restored (current) context values. Since keys differ structurally, the old entries are simply never matched -- queries miss the cache and fetch fresh data.

5. **No special handling needed.** The existing query key factory design (ADR-010) is sufficient to prevent stale context data from being displayed.

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Install dependencies | `frontend/package.json` | none | `@tanstack/react-query-persist-client` and `idb-keyval` appear in dependencies; `npm ls` confirms resolution | Low |
| 2 | Configure QueryClient with global defaults | `frontend/src/main.tsx` | none | QueryClient constructed with `staleTime: 2 * 60 * 1000` and `gcTime: 30 * 60 * 1000`; existing tests pass; DevTools shows non-zero staleTime | Low |
| 3 | Create IndexedDB persister module with dehydrate filter | `frontend/src/api/queryPersister.ts` (new) | task 1 | Module exports `createPersister()` returning an IDB persister and `persistOptions` with `shouldDehydrateQuery` filter excluding AI chat, users.me, adminRbac, roleAssignments keys | Med |
| 4 | Integrate persistQueryClient into app initialization | `frontend/src/main.tsx` | tasks 2, 3 | `persistQueryClient` called with persister and maxAge: 24h; app starts without errors; DevTools shows IndexedDB entries after queries execute | Med |
| 5 | Clear persisted cache on logout | `frontend/src/stores/useAuthStore.ts`, `frontend/src/api/queryPersister.ts` | task 3 | On `logout()`, `persister.removeClient()` called; after logout, IndexedDB `reactQuery` store is empty | Low |
| 6 | Add navigator.storage.persist() call | `frontend/src/utils/storagePersistence.ts` (new), `frontend/src/App.tsx` or `frontend/src/main.tsx` | none | Function called after auth confirmation; console logs result; DevTools shows persistent storage granted | Low |
| 7 | Unit tests for persister filter logic | `frontend/src/api/__tests__/queryPersister.test.ts` (new) | task 3 | Tests cover: allowed keys persisted, AI chat excluded, RBAC keys excluded, empty filter passes through | Med |
| 8 | Unit tests for cache clear on logout | `frontend/src/stores/__tests__/useAuthStore.persistence.test.ts` (new) | task 5 | Test verifies logout triggers `removeClient` on the persister | Low |
| 9 | Review existing staleTime overrides for compatibility | none (review only) | task 2 | Confirm 7 existing hooks with custom staleTime remain correct: dashboard (5min), cost element types (5min), progress entries (1min), auth (5min), budget settings (5min), change order stats (5min), entity history (30s) -- all still appropriate with new 2min global default | Low |
| 10 | Build verification and bundle size check | none | all above | `npm run typecheck` clean, `npm run lint` clean, `npm run build` succeeds, bundle size increase under 6KB gzipped | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FC-3: Cache cleared on logout | T-001 | `frontend/src/stores/__tests__/useAuthStore.persistence.test.ts` | `logout()` calls `removeClient()`, IndexedDB store is empty afterward |
| FC-4: AI chat excluded from persistence | T-002 | `frontend/src/api/__tests__/queryPersister.test.ts` | `shouldDehydrateQuery` returns `false` for queries with key starting with `["ai", "chat"]` |
| FC-5: RBAC queries excluded | T-003 | `frontend/src/api/__tests__/queryPersister.test.ts` | `shouldDehydrateQuery` returns `false` for `["users", "me"]`, `["admin-rbac", ...]`, `["role-assignments", ...]` |
| FC-4/5: Allowed queries pass filter | T-004 | `frontend/src/api/__tests__/queryPersister.test.ts` | `shouldDehydrateQuery` returns `true` for project, WBE, cost element, dashboard, forecast keys |
| TC-3: TypeScript clean | T-005 | CI pipeline | `npm run typecheck` exits 0 |
| TC-4: ESLint clean | T-006 | CI pipeline | `npm run lint` exits 0 |
| TC-5: Existing tests pass | T-007 | CI pipeline | `npm test` exits 0 |

---

## Test Specification

### Test Hierarchy

```
frontend/src/
├── api/__tests__/
│   └── queryPersister.test.ts          -- Unit: shouldDehydrateQuery filter logic
├── stores/__tests__/
│   └── useAuthStore.persistence.test.ts -- Unit: logout clears persisted cache
└── utils/__tests__/
    └── storagePersistence.test.ts       -- Unit: navigator.storage.persist wrapper
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
|---|---|---|---|---|
| T-001 | `test_logout_calls_removeClient_on_persister` | FC-3 | Unit | `removeClient` mock called once during `logout()` |
| T-002 | `test_shouldDehydrateQuery_excludes_ai_chat_keys` | FC-4 | Unit | Returns `false` for any query with key matching `["ai", "chat", ...]` |
| T-003 | `test_shouldDehydrateQuery_excludes_rbac_keys` | FC-5 | Unit | Returns `false` for `["users", "me"]`, `["admin-rbac", ...]`, `["role-assignments", ...]` |
| T-004 | `test_shouldDehydrateQuery_allows_entity_keys` | FC-4/5 | Unit | Returns `true` for `["projects", ...]`, `["wbes", ...]`, `["cost-elements", ...]`, `["dashboard", ...]` |
| T-005 | `test_shouldDehydrateQuery_only_persists_successful_queries` | FC-1 | Unit | Returns `false` for queries with `state.status !== "success"` |
| T-006 | `test_navigator_storage_persist_called_on_auth` | FC-8 | Unit | `navigator.storage.persist` called; result logged |

### Test Infrastructure Needs

- **Mocks/stubs**: `idb-keyval` module mocked in persister tests; `navigator.storage.persist` mocked in storage tests; `queryClient` and persister mocks in logout tests
- **Fixtures**: Sample query objects with various key structures for filter tests (can use `queryKeys` factory directly)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | IndexedDB serialization fails for complex query response types | Low | Med | Use `shouldDehydrateQuery` to only persist `status === "success"` queries; TanStack handles serialization of standard JSON automatically |
| Technical | `navigator.storage.persist()` denied by browser | Med | Low | Feature degrades gracefully -- persistence still works but may be evicted under extreme memory pressure. Log the denial and move on. |
| Integration | Mutation invalidation breaks after persistence active | Low | High | Existing integration tests cover mutation cascades; verify they pass unchanged. The persistence layer does not intercept invalidation. |
| Integration | Cache restore interferes with `visibilitychange` token refresh | Low | Med | Token refresh runs on `visibilitychange`, not on page load. Cache restore runs on page load. No overlap in trigger conditions. |
| UX | User sees briefly stale data after tab discard reload | Med | Low | This is the intended behavior -- stale data renders immediately, then background refetch updates. The staleTime of 2 min bounds staleness. |

---

## Documentation References

### Required Reading

- TanStack Query Persistence: `https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient`
- ADR-010 Query Key Factory: `docs/02-architecture/decisions/ADR-010-query-key-factory.md`
- Frontend Coding Standards: `docs/02-architecture/frontend/coding-standards.md`
- State Management: `docs/02-architecture/frontend/contexts/02-state-data.md`

### Code References

- QueryClient initialization: `frontend/src/main.tsx`
- Query Key Factory: `frontend/src/api/queryKeys.ts`
- Auth store with logout: `frontend/src/stores/useAuthStore.ts`
- Time Machine store: `frontend/src/stores/useTimeMachineStore.ts`
- Time Machine context provider: `frontend/src/contexts/TimeMachineContext.tsx`
- Token refresh: `frontend/src/utils/tokenRefresh.ts`
- Dashboard hooks with existing staleTime: `frontend/src/features/dashboard/hooks/useDashboardData.ts`

---

## Prerequisites

### Technical

- [ ] `npm install @tanstack/react-query-persist-client idb-keyval --legacy-peer-deps` completed
- [ ] Dev environment running with `npm run dev`

### Documentation

- [x] Analysis phase approved (Option 1)
- [x] Architecture docs reviewed (query key factory, Time Machine context)
- [x] Time Machine racing investigation completed (no race condition)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
# Mobile Tab Discard Mitigation -- Option 1 Progressive Enhancement

tasks:
  - id: FE-001
    name: "Install @tanstack/react-query-persist-client and idb-keyval"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Configure QueryClient with global staleTime (2min) and gcTime (30min)"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-003
    name: "Create IndexedDB persister module with shouldDehydrateQuery filter"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-004
    name: "Integrate persistQueryClient into app initialization (main.tsx)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002, FE-003]

  - id: FE-005
    name: "Clear persisted cache on logout via removeClient"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-006
    name: "Add navigator.storage.persist() utility and call on auth"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-007
    name: "Unit tests: persister filter logic (shouldDehydrateQuery)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-008
    name: "Unit tests: cache clear on logout"
    agent: pdca-frontend-do-executor
    dependencies: [FE-005]

  - id: FE-009
    name: "Unit tests: navigator.storage.persist wrapper"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006]

  - id: FE-010
    name: "Review existing staleTime overrides for compatibility with new defaults"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-011
    name: "Build verification: typecheck, lint, build, bundle size check"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004, FE-005, FE-006, FE-007, FE-008, FE-009, FE-010]
```

### Execution Order Visualization

```
Level 0 (parallel):    FE-001 (install)     FE-002 (QueryClient)     FE-006 (storage.persist)
                         |                      |                         |
Level 1:              FE-003 (persister)       |                         |
                         |  \                   |                         |
Level 2:              FE-004 (integrate)       |                         |
                       /    |                   |                         |
Level 1 (cont):   FE-005 (logout)          FE-010 (review)          FE-009 (test persist)
                    |                        |                         |
Level 2 (cont):  FE-007 (test filter)       |                         |
                    |                        |                         |
Level 3:          FE-008 (test logout)       |                         |
                    |                        |                         |
Level 4 (final):  FE-011 (build verify)  <---+--- all tasks ----------+
```

### Notes on Parallelization

- FE-001, FE-002, and FE-006 have zero dependencies and can run in parallel
- FE-003 depends on FE-001 (needs the installed package to import types)
- FE-004 depends on both FE-002 and FE-003 (needs configured QueryClient AND persister)
- FE-005 depends on FE-003 (needs persister module to call removeClient)
- FE-007 and FE-008 depend on their respective implementation tasks
- FE-010 depends on FE-002 (needs to know the new defaults to review against)
- FE-011 is the final gate, depending on all other tasks
- All tasks are frontend-only; single agent execution is expected but the graph allows splitting test tasks to a second agent if desired
