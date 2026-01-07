# IT-FE-01: Foundation Hardening - PLAN

**Iteration:** IT-FE-01  
**Created:** 2026-01-03  
**Status:** 🟡 Awaiting Approval  
**Approver:** TBD

---

## Phase 1: Context Analysis

### Documentation Review

**Product Scope:**

- User management (E02-U01) is partially implemented in frontend
- No major product features blocked by missing error handling, but UX suffers from white-screen crashes
- Quality improvements are in scope (current Sprint 2 goal: quality improvements + frontend alignment)

**Architecture:**

- [Frontend Core Architecture](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/01-core-architecture.md) mandates strict TypeScript with no `any` types
- [UI/UX Context](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/03-ui-ux.md) documents error boundaries and Sentry but not implemented
- [Quality & Testing](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/04-quality-testing.md) references error monitoring with Sentry ErrorBoundary

**Current Project Status:**

- Sprint 2 active: User Management Quality Improvements + Frontend Alignment (On Track)
- 31 frontend tests passing
- Lint-free codebase (100%)
- Only `users` feature implemented

### Codebase Analysis

**Current Patterns:**

- No error boundaries exist in codebase (`main.tsx` has no ErrorBoundary wrapper)
- React Query configured but DevTools not enabled
- No pre-commit hooks (no husky/lint-staged in `package.json`)
- Zustand stores use direct mutations (no immer middleware)

**Dependencies:**

- `@sentry/react: ^8.46.0` installed but not configured with ErrorBoundary
- `@tanstack/react-query-devtools: ^5.62.0` installed but not imported
- Missing: `react-error-boundary`, `husky`, `lint-staged`, `immer`

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** Frontend lacks defensive error handling and developer experience tooling, causing:

- White-screen crashes from unhandled errors (poor UX)
- No visibility into React Query cache state during development
- No automated quality gates on commit
- Verbose Zustand store updates prone to mutation bugs

**Why Now:**

- Before adding more features (Departments, Projects), we need robust error handling
- Current feature velocity will slow without better debugging tools
- Technical debt will compound as codebase grows

**Business Value:**

- **User Impact:** Prevents complete app crashes, improves perceived reliability
- **Developer Velocity:** Faster debugging, fewer mutation bugs, catch issues pre-commit

### 2. Success Criteria (Measurable)

**Functional Criteria:**
✅ Unhandled errors display fallback UI instead of white screen  
✅ Users can recover from error states via fallback UI  
✅ React Query cache is inspectable in browser DevTools

**Technical Criteria:**
✅ Pre-commit hooks block commits with lint/type errors  
✅ All Zustand stores use immer for immutable updates  
✅ No errors thrown during normal user flows  
✅ Test suite passes with new dependencies

**Quality Criteria:**
✅ 0 new lint errors introduced  
✅ 0 new type errors introduced  
✅ Test coverage maintained or improved

### 3. Scope Definition

**In Scope:**

- Install `react-error-boundary`, `immer`, `husky`, `lint-staged`
- Create `ErrorBoundary.tsx` wrapper component with fallback UI
- Wrap app root in ErrorBoundary in `main.tsx`
- Enable `ReactQueryDevtools` in `main.tsx`
- Configure husky pre-commit hook for `lint` + `tsc --noEmit`
- Refactor Zustand stores to use immer middleware
- Update documentation to reflect error handling patterns

**Out of Scope:**

- Sentry integration (already installed, configuration deferred)
- Custom error logging beyond console (future iteration)
- Error boundary at feature level (current scope: global only)
- Retry logic for failed queries (separate iteration)

---

## Phase 3: Implementation Options

| Aspect                   | Option A: Full Integration                                                  | Option B: Minimal Viable                                     | Option C: Deferred DX                              |
| ------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------- |
| **Approach Summary**     | Install all deps + fully configure                                          | Install only error boundary + DevTools                       | Error boundary only, defer hooks                   |
| **Error Boundary**       | Custom component + Sentry fallback                                          | `react-error-boundary` with simple UI                        | `react-error-boundary` basic                       |
| **DevTools**             | Enabled with custom position                                                | Enabled with defaults                                        | Not enabled                                        |
| **Pre-commit Hooks**     | Husky + lint-staged + type check                                            | Husky + lint only                                            | Deferred                                           |
| **Immer Middleware**     | All stores refactored                                                       | Only complex stores                                          | Deferred                                           |
| **Pros**                 | - Complete DX improvement<br>- Prevents future debt<br>- Best quality gates | - Faster completion<br>- Core value delivered<br>- Less risk | - Absolute minimum<br>- Very low risk              |
| **Cons**                 | - More test updates<br>- Higher complexity                                  | - Manual type checking<br>- Mutation bugs possible           | - No velocity improvement<br>- Missing key DX wins |
| **Test Strategy Impact** | Update store tests for immer                                                | Minimal test changes                                         | No test changes                                    |
| **Risk Level**           | Medium                                                                      | Low                                                          | Very Low                                           |
| **Estimated Complexity** | Moderate                                                                    | Simple                                                       | Simple                                             |

### Recommendation

**Option A: Full Integration** is recommended because:

1. **Long-term Value:** Pre-commit hooks prevent broken code from reaching CI
2. **Developer Velocity:** DevTools + immer save significant debugging time
3. **Aligned with Project Goals:** Sprint 2 explicitly targets "quality improvements"
4. **Low Risk:** All changes are additive, no breaking changes
5. **Future-Proof:** Sets patterns for remaining 3 iterations

**Trade-off Accepted:** Slightly higher complexity (~1 day vs ~0.5 days) for substantial DX gains.

> [!IMPORTANT] > **Human Decision Required:** Approve Option A or select alternative.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests
│   ├── ErrorBoundary component
│   │   ├── Renders children when no error
│   │   ├── Renders fallback UI when error caught
│   │   └── Provides reset functionality
│   ├── Zustand stores with immer
│   │   ├── Immutable updates work correctly
│   │   └── Nested object updates don't mutate
│
├── Integration Tests
│   ├── ErrorBoundary integration
│   │   ├── Catches component errors in tree
│   │   └── Recovery resets React Query cache
│   └── Pre-commit hook validation (manual)
│       └── Verify hooks block invalid commits
│
└── Visual Verification
    └── DevTools visible in browser
```

**First 5 Test Cases (simplest → complex):**

1. **ErrorBoundary renders children normally**

   - Mount ErrorBoundary with child component
   - Assert child renders without fallback

2. **ErrorBoundary catches thrown errors**

   - Child component throws error
   - Assert fallback UI displays

3. **ErrorBoundary reset functionality**

   - Trigger error, verify fallback
   - Click reset button
   - Assert children re-render

4. **Zustand immer middleware basic update**

   - Update simple field in store
   - Assert original state not mutated

5. **Zustand immer nested update**
   - Update nested object/array
   - Assert original state unchanged

### Implementation Strategy

**Approach:**

1. Install dependencies via npm
2. Create ErrorBoundary component with Ant Design Result for fallback UI
3. Wrap `<App />` in `main.tsx` with ErrorBoundary
4. Add `<ReactQueryDevtools />` inside QueryClientProvider
5. Configure husky with pre-commit hook
6. Add immer middleware to all Zustand stores
7. Update existing store tests

**Key Technologies:**

- `react-error-boundary` v4 (standard library)
- `immer` v10 (zustand middleware)
- `husky` v9 + `lint-staged` v15

**Integration Points:**

- `main.tsx` (ErrorBoundary wrapper, DevTools)
- All files in `src/stores/` (immer middleware)
- `package.json` (scripts, husky config)
- `.husky/pre-commit` (new file)

**Component Breakdown:**

```tsx
// src/components/ErrorBoundary.tsx
- Uses react-error-boundary's ErrorBoundary
- Custom fallback component with Ant Design Result
- Reset button to recover
- Error logging to console

// main.tsx updates
+ import { ErrorBoundary } from '@/components/ErrorBoundary'
+ import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
```

---

## Phase 5: Risk Assessment

| Risk Type         | Description                                          | Probability | Impact | Mitigation Strategy                                                              |
| ----------------- | ---------------------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------- |
| **Integration**   | Immer middleware breaks existing store tests         | Medium      | Medium | Write tests first, refactor incrementally, one store at a time                   |
| **Technical**     | ErrorBoundary doesn't catch errors in event handlers | Low         | Low    | Document limitation, add try-catch in critical handlers                          |
| **Schedule**      | Husky setup varies across dev environments           | Low         | Low    | Test on clean clone, document setup in README                                    |
| **DX**            | Pre-commit hooks too slow, frustrate developers      | Low         | Medium | Configure lint-staged to only check staged files, add `--no-verify` escape hatch |
| **Compatibility** | React Query DevTools increases bundle size in prod   | Very Low    | Low    | Verify DevTools tree-shakes in production build                                  |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Development:**

  - Install dependencies + ErrorBoundary component: 1 hour
  - Enable DevTools + test: 0.5 hours
  - Husky + lint-staged setup: 1 hour
  - Refactor 6 stores with immer: 2 hours
  - **Subtotal:** 4.5 hours

- **Testing:**

  - Write ErrorBoundary tests: 1 hour
  - Update store tests for immer: 1.5 hours
  - Manual verification (hooks, DevTools): 0.5 hours
  - **Subtotal:** 3 hours

- **Documentation:**

  - Update architecture docs with error handling pattern: 0.5 hours
  - README updates for husky setup: 0.5 hours
  - **Subtotal:** 1 hour

- **Review & Deployment:**
  - Code review preparation: 0.5 hours
  - Address feedback: 1 hour
  - **Subtotal:** 1.5 hours

**Total Estimated Effort:** 10 hours (~1.5 days)

### Prerequisites

- [x] `package.json` exists with npm scripts
- [ ] Decision on Option A vs B vs C
- [ ] Approval to install new dependencies
- [ ] Git hooks allowed in developer workflow

### Dependencies

- No blockers from other teams/features
- Backend API already stable for this work
- No infrastructure changes needed

---

## Approval

**Status:** ✅ Approved (Option A - Full Integration)  
**Reviewer:** User  
**Date Approved:** 2026-01-03

**Approval Checklist:**

- [x] Option selection confirmed (A/B/C)
- [x] Scope and success criteria clear
- [x] Risk mitigations acceptable
- [x] Effort estimation reasonable
- [x] Ready to proceed to DO phase
