# PLAN Phase: Strategic Analysis and Iteration Planning

## Purpose

Structure iteration planning by analyzing requirements, architectural constraints, and generating implementation options for human decision.

---

## Phase 1: Context Analysis

### Documentation Review

- **Product Scope**: Need consistent UI for entity management (Users, Departments, etc.) and deep support for the EVCS system (time travel capability).
- **Architecture**: Existing frontend is feature-heavy but lacks generalized abstractions. Backend has powerful bitemporal capabilities that are currently "invisible" to the frontend user.
- **Previous Iteration**: `2026-01-fe-03-user-management` started migrating user tables. This iteration builds on that by standardizing the table component itself.

### Codebase Analysis

- **Patterns**: Currently using `Zustand` for async state (anti-pattern) and manual API wrappers.
- **Dependencies**: `TanStack Query` is installed but underutilized. `Ant Design` is the core UI lib.
- **Gaps**: Boilerplate for pagination, no standardized error handling, no versioning UI.

---

## Phase 2: Problem Definition

### 1. Problem Statement

The frontend architecture lacks reusable abstractions for core patterns (CRUD, Tables, Versioning), leading to code duplication, type safety leaks, and an inconsistent user experience. Additionally, the backend's unique "Time Travel" features are inaccessible to users.

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] `StandardTable` component supports pagination, sorting, and custom tools with < 30 lines of implementation code.
- [ ] `VersionHistory` drawer correctly displays a list of past versions for an entity.
- [ ] `useCrud` hooks successfully handle Create, Read, Update, Delete with automatic cache invalidation.

**Technical Criteria:**

- [ ] Boilerplate reduction: New features require 50% less code for basic CRUD.
- [ ] Type Safety: No `any` casting in Service layers.

**Business Criteria:**

- [ ] Users can view and navigate entity history (audit trail visibility).

### 3. Scope Definition

**In Scope:**

- `StandardTable` component.
- `VersionHistory` component (Drawer + List).
- `useCrud` generic hooks factory.
- Refactoring `UserList` to use new components.
- Syncing Table state to URL Query Params.

**Out of Scope:**

- Full migration of other modules (Projects, Departments) - only Users for this POC.
- Complex "Diff" visualization (text diffing) - minimal UI for now.

---

## Phase 3: Implementation Options

| Aspect               | Option A: Generalized Composition (Recommended)                        | Option B: Copy-Paste Patterns                                | Option C: Third-Party Libs (ProComponents)                                    |
| -------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| **Approach Summary** | Build generic `StandardTable` and `useCrud` hooks to compose features. | Keep current manual pattern but enforce strict style guides. | Use `@ant-design/pro-components`.                                             |
| **Design Patterns**  | HOC / Composition, Custom Hooks (Factory Pattern).                     | WET (Write Everything Twice).                                | CONFIG-driven.                                                                |
| **Pros**             | Type-safe, tailored to our backend, flexible.                          | Lowest abstraction cost.                                     | Very fast initial setup.                                                      |
| **Cons**             | Initial setup effort.                                                  | High maintenance burden.                                     | Locked into ProComponents opinionated structure; User deprecated it recently. |
| **Risk Level**       | Low                                                                    | Medium (Technical Debt)                                      | Medium (Dependency Risk)                                                      |

### Recommendation

**Option A**. It aligns with the user's explicit preference to avoid `ProComponents` while solving the boilerplate issue. It provides the most control over the unique "time travel" UX requirements.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests
│   ├── useTableParams.test.ts (URL sync logic)
│   ├── useCrud.test.tsx (Mocked QueryClient interactions)
│   └── StandardTable.test.tsx (Pagination callbacks)
├── Integration Tests
│   └── UserList.test.tsx (Verify Refactor doesn't break existing flows)
```

### Implementation Strategy

1.  **Foundation**: Create `hooks/useTableParams` and `hooks/useCrud`.
2.  **UI Components**: Build `StandardTable` (wrapping AntD Table) and `VersionHistory` (Drawer).
3.  **Refactor**: Apply to `UserList` features.
4.  **Verify**: Run tests and Storybook.

---

## Phase 5: Risk Assessment

| Risk Type   | Description                                                                        | Probability | Impact | Mitigation Strategy                                      |
| ----------- | ---------------------------------------------------------------------------------- | ----------- | ------ | -------------------------------------------------------- |
| Technical   | Generic hooks might be too rigid for complex edge cases.                           | Medium      | High   | Allow "escape hatches" (pass raw props, override hooks). |
| Integration | Backend Pagination names (`skip`/`limit`) differ from AntD (`current`/`pageSize`). | High        | Low    | Handle mapping transparently in `StandardTable` / Hooks. |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Development**: 2 days (Components & Hooks)
- **Refactoring**: 1 day (User Module)
- **Testing**: 1 day
- **Total Estimated Effort**: 4 days

### Prerequisites

- None.

---

## Output Format

- **Approval**: Approved by User (via Chat).
- **Date**: 2026-01-03
