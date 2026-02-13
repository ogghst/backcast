# PLAN Phase: Strategic Analysis and Iteration Planning

## Purpose

Align frontend API client with Backend implementation using automated OpenAPI generation to ensure type safety and reduce maintenance burden.

---

## Phase 1: Context Analysis

### Documentation Review

- **Product Scope**: Project aims for robust versioning. Frontend must accurately reflect complex backend states (reversions, branches).
- **Architecture**: Backend uses FastAPI/Pydantic with strict typing. Frontend is React/TypeScript. Manual type synchronization is a violation of DRY and introduces regression risks.
- **Project Plan**: Sprint 2 goal is "Align Frontend implementation". This task is the enabler for that goal.

### Codebase Analysis

- **Current State**: `frontend/src/api/client.ts` uses manual Axios calls. `frontend/src/features/users/api/userService.ts` defines types manually.
- **Drift**: Backend recently added `UserPreference`, `BranchableService`, and strict schemas. Frontend is unaware of these or might match outdated specs.

---

## Phase 2: Problem Definition

### 1. Problem Statement

The Frontend codebase relies on manually defined TypeScript interfaces that are decoupling from the Backend's Pydantic models. As the Backend evolves (e.g., adding Entity Versioning), the Frontend is becoming brittle and prone to runtime errors due to mismatched contracts.

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- Frontend client code is automatically generated from Backend OpenAPI spec.
- User Management, Profile, and Authentication features function correctly with the new client.

**Technical Criteria:**

- `npm run build` passes with zero type errors.
- No manual `interface` definitions for API responses remain in `src/features/users`.
- `openapi-typescript-codegen` pipeline is established.

**Business Criteria:**

- Developer confidence in Frontend-Backend integration increases (qualitative).

### 3. Scope Definition

**In Scope:**

- Backend: Script to export `openapi.json`.
- Frontend: Setup `openapi-typescript-codegen`.
- Frontend: Refactor `UserService`, `Auth` to use generated client.
- Frontend: Update `UserList`, `UserProfile` components.

**Out of Scope:**

- Major UI redesigns (focus is on data layer).
- Implementing new features not already in Backend (e.g., full Branching UI).

---

## Phase 3: Implementation Options

| Aspect               | Option A: Manual Updates                             | Option B: `openapi-typescript-codegen`                        |
| -------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| **Approach Summary** | Update `types.ts` manually to match Pydantic models. | Generate TS service client from `openapi.json` automatically. |
| **Design Patterns**  | Manual DTOs                                          | Generated Service/Model pattern                               |
| **Pros**             | No new tooling. Full control over naming.            | Single source of truth. Instant updates.                      |
| **Cons**             | Error-prone. High maintenance.                       | generated code can be verbose.                                |
| **Test Strategy**    | Manual verification required.                        | Type checker verifies contract.                               |
| **Risk Level**       | High (Human Error)                                   | Low                                                           |
| **Complexity**       | Simple (Concept) / High (Labor)                      | Low (Setup)                                                   |

### Recommendation

**Option B**. It provides a robust, long-term solution to the "Backend-Frontend drift" problem, a critical architectural concern for a complex EVS system.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Frontend Type Check (tsc)
│   └── Verify generated types match component usage
├── Frontend Unit Tests (Vitest)
│   ├── UserList renders using Generated Client Mock
│   └── Auth Store handles generated Token Schema
└── Manual Integration
    └── Verify "Get Me" and "List Users" against running Backend
```

### Implementation Strategy

1.  **Backend**: Create `scripts/generate_openapi.py`.
2.  **Frontend**: Install `openapi-typescript-codegen`.
3.  **Frontend**: Create `npm run generate-client` script.
4.  **Frontend**: Run generation.
5.  **Refactor**: Iteratively replace `UserService` calls with `UserService.getUsers()`.

---

## Phase 5: Risk Assessment

| Risk Type   | Description                                                                 | Mitigation Strategy                                                        |
| ----------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Integration | Generated names might clash or differ slightly (e.g. `UserRead` vs `User`). | Use aliases or aliased imports during refactor.                            |
| Schedule    | Refactoring might expose hidden bugs.                                       | Timeboxed refactor; revert to manual if blocking critical path (unlikely). |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Backend Script**: 0.5 hours
- **Frontend Setup**: 0.5 hours
- **Refactoring**: 2.0 hours
- **Validation**: 1.0 hours
- **Total**: ~4 hours (0.5 days)

### Prerequisites

- Backend must run locally to export OpenAPI spec.
