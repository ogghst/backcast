# Analysis: Mitigate Mobile Browser Tab Discard Reloads

**Created:** 2026-05-20
**Request:** Analyze and implement mitigation strategies for frequent mobile browser tab discard reloads, covering TanStack Query cache persistence to IndexedDB, PWA service worker, increased staleTime, and persistent storage request.

---

## Clarified Requirements

### Problem Statement

On mobile browsers, switching between apps triggers OS-level memory management that discards background tabs. When the user returns, the browser reloads the tab from scratch, losing all in-memory TanStack Query cache. The user sees a blank/loading page while all data re-fetches. This is a UX degradation, not a data loss issue.

### Functional Requirements

- After a mobile tab discard+reload, the UI must render with cached data immediately (zero network round-trip before meaningful content)
- Background revalidation must update cached data once the network responds
- The app shell (HTML, JS, CSS) must load from local cache when possible, even on flaky connections
- Browser storage eviction under memory pressure must be prevented

### Non-Functional Requirements

- No stale-data integrity risk for EVCS versioned entities (branch context, time-travel state)
- No increase in bundle size beyond what is strictly necessary
- RBAC-sensitive data must not leak across user sessions
- Existing mutation invalidation patterns must remain fully functional
- Development experience must remain straightforward (HMR, devtools)

### Constraints

- No backend changes required; this is entirely a frontend concern
- Must not break the existing Time Machine context isolation (ADR-010)
- Must not conflict with existing Zustand persistence (auth store, time machine store use localStorage)
- Must not interfere with WebSocket-based AI chat streaming
- Must not interfere with the existing `visibilitychange` token refresh logic

---

## Context Discovery

### Product Scope

- No specific user stories address mobile browser tab discard behavior
- The system is designed for desktop-first use in office environments, but project managers increasingly use tablets/phones on the factory floor during end-of-line commissioning
- Data-integrity sensitivity: EVCS entities with bitemporal versioning and branch isolation require precise context (branch, asOf, mode) in query keys

### Architecture Context

**Bounded contexts involved:**
- Core EVCS (versioned entities with branch context)
- Authentication (RBAC, token refresh)
- AI Chat (WebSocket connections)
- All feature contexts that use TanStack Query (19 feature directories, 113 `useQuery` calls)

**Existing patterns to follow:**
- Query Key Factory (`src/api/queryKeys.ts`) -- centralized, type-safe, with context isolation for `{ branch, asOf, mode }` per ADR-010
- Zustand persistence using `zustand/middleware/persist` with localStorage for auth and time machine stores
- Token refresh on `visibilitychange` in `src/utils/tokenRefresh.ts`
- Dashboard data hook already uses `staleTime: 5 min`, `gcTime: 10 min`, `refetchOnWindowFocus: false`

**Architectural constraints:**
- Query keys include Time Machine context for versioned entities -- persisted cache must respect this
- Mutations trigger cascade invalidation across dependent query keys
- WebSocket streaming in AI chat manages its own state, not through TanStack Query

### Codebase Analysis

**Frontend:**

- **QueryClient configuration** (`src/main.tsx`): Bare `new QueryClient()` with all defaults (staleTime: 0, gcTime: 5 min, retry: 3, refetchOnMount: true, refetchOnWindowFocus: true)
- **No PWA setup at all**: No service worker, no manifest, no `vite-plugin-pwa`, no offline caching
- **Bundle size**: ~9.2 MB built dist
- **IndexedDB usage**: None currently
- **`navigator.storage` usage**: None currently
- **Custom staleTime overrides**: 7 hooks override defaults for specific use cases (dashboard 5min, cost element types 5min, progress entries 1min, auth 5min, project budget settings 5min, change order stats 5min, entity history 30s)
- **`visibilitychange` listeners**: token refresh hook and AI chat streaming hook
- **Zustand persistence**: `useAuthStore` and `useTimeMachineStore` use `persist` middleware with localStorage
- **Dependent invalidation**: Mutations for cost registrations, schedule baselines, and cost elements all cascade to `forecasts.all` and related keys

---

## Solution Options

### Option 1: Progressive Enhancement (staleTime + IndexedDB persistence + persistent storage)

**Architecture & Design:**

This option focuses on the data layer without adding PWA infrastructure. It addresses the core problem (cache loss on reload) by persisting TanStack Query cache to IndexedDB and setting sensible staleTime defaults, while requesting persistent storage to prevent eviction.

1. Configure `QueryClient` with global `staleTime: 2 min`, `gcTime: 30 min`
2. Use `@tanstack/react-query-persist-client` with `IndexedDB` persister (via `idb-keyval`)
3. Add `navigator.storage.persist()` call on app initialization (after auth)
4. No service worker, no manifest, no PWA

**UX Design:**

- User switches away from tab, OS discards it
- User returns: browser reloads page, TanStack Query cache is restored from IndexedDB
- UI renders immediately with cached data (within staleTime window, no refetch triggers)
- If data is stale (beyond staleTime), renders cached data then silently refetches in background
- No visible change to the user experience during normal desktop usage

**Implementation:**

- Modify `src/main.tsx`: Configure `QueryClient` with non-default `staleTime` and `gcTime`
- Add `@tanstack/react-query-persist-client` and `idb-keyval` dependencies
- Create persistence setup using `persistQueryClient` with an IndexedDB persister
- Add `navigator.storage.persist()` call in auth flow
- Exclude RBAC-sensitive queries (users, permissions) from persistence via `persister` filter or separate QueryClient

**Trade-offs:**

| Aspect          | Assessment                                                       |
| --------------- | ---------------------------------------------------------------- |
| Pros            | Solves the primary problem (cache loss); minimal architecture change; no new infra; respects existing query key isolation |
| Cons            | Does not cache app shell (HTML/JS/CSS) -- reload still requires network for assets; IndexedDB persistence adds ~5KB to bundle; must carefully filter persisted queries |
| Complexity      | Low-Med                                                          |
| Maintainability | Good -- uses official TanStack persistence library               |
| Performance     | Fast data restore (~10-50ms IndexedDB read); app shell still needs network fetch |

---

### Option 2: Full PWA (Service Worker + Manifest + IndexedDB + staleTime + persistent storage)

**Architecture & Design:**

Complete PWA setup with service worker caching the app shell, manifest for installability, and all data-layer enhancements from Option 1.

1. Configure `QueryClient` with global `staleTime: 2 min`, `gcTime: 30 min`
2. Add `vite-plugin-pwa` with Workbox-based service worker for app shell caching
3. Persist TanStack Query cache to IndexedDB
4. Request persistent storage via `navigator.storage.persist()`
5. Generate web app manifest for "Add to Home Screen"

**UX Design:**

- Same data-layer benefits as Option 1
- Additionally: app shell loads from service worker cache even on flaky/absent network
- "Add to Home Screen" capability on mobile
- Near-instant full page load on discard+reload (both shell and data from cache)
- Potential for offline indicator UI when network is unavailable

**Implementation:**

- All Option 1 steps plus:
- Add `vite-plugin-pwa` to devDependencies
- Configure `VitePWA` plugin in `vite.config.ts` with `registerType: autoUpdate`, workbox config for precaching
- Generate `manifest.webmanifest` with app icons
- Handle service worker update notification UI
- Test service worker behavior with Vite dev server (requires `devOptions` config)
- Exclude API calls from service worker caching (only cache app shell assets)

**Trade-offs:**

| Aspect          | Assessment                                                       |
| --------------- | ---------------------------------------------------------------- |
| Pros            | Most complete solution; app shell cached for near-instant reload; enables offline capability; installable on mobile |
| Cons            | Significant complexity increase; service worker debugging is notoriously difficult; `vite-plugin-pwa` + Workbox add ~15-20KB to bundle; dev experience friction (SW caching during development); must ensure API responses are never cached by SW; versioning/deployment complexity (SW update lifecycle) |
| Complexity      | High                                                             |
| Maintainability | Fair -- service worker lifecycle adds deployment complexity      |
| Performance     | Best possible -- both shell and data cached locally              |

---

### Option 3: Minimal (staleTime increase only + persistent storage)

**Architecture & Design:**

The smallest possible change: increase staleTime defaults and request persistent storage. No cache persistence, no service worker.

1. Configure `QueryClient` with global `staleTime: 2 min`, `gcTime: 30 min`
2. Add `navigator.storage.persist()` call on auth initialization

**UX Design:**

- During normal use, reduces unnecessary refetches on mount and window focus
- Does NOT solve the tab discard problem (cache is still in-memory only, lost on reload)
- Only marginally improves the mobile experience
- `navigator.storage.persist()` alone does nothing for tab discard

**Implementation:**

- Modify `src/main.tsx`: 2-line change to `QueryClient` constructor
- Add `navigator.storage.persist()` in auth flow
- Review all hooks that override staleTime to ensure they still make sense with new defaults

**Trade-offs:**

| Aspect          | Assessment                                                       |
| --------------- | ---------------------------------------------------------------- |
| Pros            | Minimal effort; zero risk; no new dependencies; improves desktop experience too |
| Cons            | Does NOT solve the stated problem (tab discard reload); persistent storage alone does not help; false sense of progress |
| Complexity      | Very Low                                                         |
| Maintainability | Good                                                             |
| Performance     | No improvement for tab discard scenario                          |

---

## Comparison Summary

| Criteria           | Option 1: Progressive Enhancement | Option 2: Full PWA              | Option 3: Minimal               |
| ------------------ | --------------------------------- | ------------------------------- | ------------------------------- |
| Development Effort | 1-2 days                          | 3-5 days                        | 0.5 days                        |
| Solves Tab Discard | Yes (data layer)                  | Yes (data + shell)              | No                              |
| UX Quality         | Good                              | Best                            | Marginal                        |
| Bundle Size Impact | +5KB                              | +20-25KB                        | 0                               |
| Risk Level         | Low                               | Medium-High                     | None                            |
| Dev Experience     | Unchanged                         | Some friction (SW in dev)       | Unchanged                       |
| Flexibility        | Can upgrade to Option 2 later     | Full feature set                | Must upgrade for real solution  |
| Best For           | Solving the stated problem cleanly | Long-term mobile strategy       | Quick win while planning more   |

---

## Recommendation

**I recommend Option 1 (Progressive Enhancement) because:**

It directly solves the stated problem (TanStack Query cache loss on mobile tab discard) with minimal architectural change, low risk, and a clear upgrade path to full PWA later. The EVCS system's data-integrity requirements (branch context, time-travel) are respected because query keys already include context parameters in the cached data. The existing query key factory (ADR-010) ensures that persisted cache entries are context-isolated.

**Key design decisions within Option 1:**

1. **staleTime: 2 minutes globally** -- balances freshness with reduced refetching. The 7 existing hooks with custom staleTime overrides (5min, 1min, 30s) remain unchanged as they already express domain-specific freshness needs.
2. **gcTime: 30 minutes** -- ensures persisted cache entries survive the typical "switch apps and return" window. The current 5-minute default is too short for meaningful persistence.
3. **IndexedDB persistence via `@tanstack/react-query-persist-client`** -- the official persistence adapter, well-maintained, respects query key structure.
4. **Exclude auth/permission queries** from persistence -- the `users.me` and `adminRbac` query keys contain permission data that must not survive across sessions. Filter these at the persister level.
5. **`navigator.storage.persist()`** -- single async call on auth initialization to prevent browser eviction of IndexedDB data.
6. **`maxAge` on persisted cache** -- set to 24 hours to prevent extremely stale data from being used after extended absence.

**Alternative consideration:** If the project later decides to pursue "Add to Home Screen" or true offline capability, Option 1 cleanly upgrades to Option 2 by adding `vite-plugin-pwa` on top of the existing persistence setup.

---

## Decision Questions

1. **RBAC data isolation**: Should the persisted cache be cleared entirely on logout (recommended), or should we rely on query key filtering to exclude permission-sensitive data? Clearing on logout is simpler and safer.

2. **Time Machine state**: The Time Machine store (branch, asOf, mode) is already persisted to localStorage via Zustand. After tab discard+reload, the restored cache will match the restored Time Machine state because query keys include context. Are there edge cases where the Time Machine state might change before IndexedDB restoration completes?

3. **Phasing priority**: Should staleTime changes be deployed first (immediate improvement for all users including desktop) with IndexedDB persistence as a follow-up, or should both ship together as a single unit?

4. **WebSocket / AI Chat**: The AI chat uses its own streaming state management outside TanStack Query. No persistence concern here, but should we consider persisting the list of chat sessions (which IS a TanStack Query) so users see their recent conversations immediately after tab discard?

---

## References

- Frontend main entry: `frontend/src/main.tsx` -- QueryClient initialization
- Query Key Factory: `frontend/src/api/queryKeys.ts` -- centralized key structure (ADR-010)
- Token Refresh: `frontend/src/utils/tokenRefresh.ts` -- existing `visibilitychange` handler
- Auth Store: `frontend/src/stores/useAuthStore.ts` -- existing Zustand localStorage persistence
- Time Machine Store: `frontend/src/stores/useTimeMachineStore.ts` -- persisted branch/asOf state
- Time Machine Context: `frontend/src/contexts/TimeMachineContext.tsx` -- query invalidation on context change
- Dashboard Data: `frontend/src/features/dashboard/hooks/useDashboardData.ts` -- existing staleTime override
- API Client: `frontend/src/api/client.ts` -- Axios interceptors, token refresh queue
- ADR-010: `docs/02-architecture/decisions/ADR-010-query-key-factory.md`
- State Management: `docs/02-architecture/frontend/contexts/02-state-data.md`
- Frontend Coding Standards: `docs/02-architecture/frontend/coding-standards.md`
- Package manifest: `frontend/package.json` -- current dependencies
- Vite config: `frontend/vite.config.ts` -- current build configuration
