# PLAN Phase: Strategic Analysis and Iteration Planning

## Purpose

Address accumulated technical debt to improve system stability, maintainability, and test reliability, specifically focusing on backend service duplication and test failures designated in the previous Act phase.

---

## Phase 1: Context Analysis

### Documentation Review

- **Previous Act Phase**: `2026-01-05-hybrid-sprint2-3/04-act.md` identified critical debt in `TemporalService` duplication and remaining unit test failures.
- **Architecture**: The EVCS (Entity Version Control System) requires robust "Root ID vs Version ID" handling, which is currently duplicated/inconsistent across services.

### Codebase Analysis

- **Duplication**: `ProjectService` and `WBEService` both implement identical `get_by_root_id` logic to handle branching and validity.
- **Test Failures**: `tests/unit/core` and `test_integration_branch_service` failed in the last regression run, indicating issues with the core versioning logic or test setup.

---

## Phase 2: Problem Definition

### 1. Problem Statement

- **What**: `ProjectService` and `WBEService` duplicate complex query logic for retrieving current versions (Root ID + Branch + Validity). Unit tests for core versioning logic are failing.
- **Why**: Rapid component creation led to copy-paste reuse. Testing was focused on E2E/API, leaving unit tests behind.
- **Risk**: Logic drift between entities (bugs fixed in one place but not another), reduced confidence in refactoring due to failing unit tests.

### 2. Success Criteria (Measurable)

**Technical Criteria:**

- **Refactoring**: `TemporalService` implements a generic `get_current_version(root_id, branch)` method.
- **Usage**: `ProjectService` and `WBEService` consume the generic method; custom query logic is removed.
- **Tests**:
  - All Backend API tests pass (Regression).
  - All Backend Unit tests (`tests/unit/core`) pass (New/Fixed).
  - `test_integration_branch_service` passes.

### 3. Scope Definition

**In Scope:**

- Refactor `TemporalService` (Backend).
- Refactor `ProjectService` and `WBEService`.
- Fix failing unit and logical tests in `backend/tests`.

**Out of Scope:**

- Frontend technical debt (unless blocking).
- New feature development.

---

## Phase 3: Implementation Options

| Aspect       | Option A: Generic Temporal Service (Recommended)                         | Option B: Patch Tests Only                                         |
| :----------- | :----------------------------------------------------------------------- | :----------------------------------------------------------------- |
| **Approach** | Lift `get_by_root_id` logic into `TemporalService`. Fix tests to match.  | Fix unit tests to match current implementation. Leave duplication. |
| **Pros**     | DRY, Single Point of Truth for EVCS queries, Easier to add new entities. | Faster, less risk of breaking existing services.                   |
| **Cons**     | Requires careful generic typing and root field resolution.               | Technical debt remains and grows with next entity.                 |
| **Risk**     | Medium (Core service change).                                            | Low (Code change), High (Long term maintenance).                   |

**Recommendation**: **Option A**. The duplication caused bugs in the last sprint (404s). Centralizing this critical EVCS logic is mandatory for stability.

---

## Phase 4: Technical Design

### Implementation Strategy

1.  **Refactor `TemporalService`**:
    - Add `get_current_version(self, root_id: UUID, branch: str = "main") -> TVersionable | None`.
    - Implement dynamic Root Field resolution (or standardized attribute).
2.  **Update Services**:
    - Replace manual queries in `ProjectService.get_project` and `WBEService.get_wbe` with `super().get_current_version`.
3.  **Fix Unit Tests**:
    - Debug `tests/unit/core` failures (likely DB session/integrity issues similar to the API tests).
    - Ensure `conftest.py` fixes from previous sprint are compatible/applied to unit tests.

---

## Phase 5: Risk Assessment

| Risk Type      | Description                                     | Mitigation                                                               |
| :------------- | :---------------------------------------------- | :----------------------------------------------------------------------- |
| **Regression** | Breaking existing API endpoints.                | Run full API test suite after refactor.                                  |
| **Complexity** | SQLAlchemy Generic typing + Dynamic attributes. | Use simple inspection or explicit abstract property for root field name. |

---

## Phase 6: Effort Estimation

- **Development**: 2 hours
- **Testing**: 2 hours
- **Documentation**: 0.5 hours
- **Total**: ~0.5 - 1 Day

## Output

- `docs/03-project-plan/iterations/2026-01-06-tech-debt-cleanup/01-plan.md`
