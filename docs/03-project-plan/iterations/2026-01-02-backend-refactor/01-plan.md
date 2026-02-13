# PLAN Phase: Backend TODO Cleanup & Service Refactoring

**Date:** 2026-01-02
**Status:** Draft

## Phase 1: Context Analysis

### Documentation & Codebase Review

- **Codebase**: Several TODOs identified in `VersioningService` (`service.py`), `UserService`, and `AuthService`.
- **Architecture**: `TemporalService` is currently an unimplemented abstract class, but `commands.py` contains a full Command Pattern implementation for versioning operations. `User` model effectively uses a "duck typing" approach for protocols but has a commented-out relationship due to circular dependencies.
- **Gap Identified**:
  - `TemporalService` methods raise `NotImplementedError`.
  - `UserService` manually instantiates commands instead of leveraging a common service layer pattern where appropriate (though manual is acceptable, consistency is key).
  - `AuthService` performs direct DB queries, bypassing service logic.
  - `User` model has a commented-out `preference` relationship.

---

## Phase 2: Problem Definition

### 1. Problem Statement

The backend contains technical debt in the form of unimplemented base service methods (`TemporalService`), direct database access in `AuthService` (bypassing encapsulation), and a circular dependency in the `User` model prevents the `preference` relationship from being defined. This fragmentation makes the system harder to maintain and test.

### 2. Success Criteria (Measurable)

- **Functional**:
  - `TemporalService` implements `create`, `update`, `soft_delete`, `get_all`, `get_as_of` using `VersionedCommandABC` and TSTZRANGE operators.
  - `AuthService` uses `UserService` for user retrieval.
  - `User.preference` relationship is active and functional.
- **Technical**:
  - `mypy` passes strict checks.
  - `pytest` passes for all refactored services.

### 3. Scope Definition

**In Scope**:

- Refactoring `backend/app/core/versioning/service.py`
- Refactoring `backend/app/services/user.py` (alignment)
- Refactoring `backend/app/services/auth.py`
- Updating `backend/app/models/domain/user.py` (circular dependency fix)

**Out of Scope**:

- Frontend changes.
- Database schema migrations (unless required, but unlikely for these code-level refactors).

---

## Phase 3: Implementation Options

| Aspect      | Option A: Standardize on Command Pattern (Recommended)                                           | Option B: Ad-hoc Fixes                                   |
| :---------- | :----------------------------------------------------------------------------------------------- | :------------------------------------------------------- |
| **Summary** | Implement `TemporalService` using `commands.py` classes. Refactor services to use this standard. | Fix individual TODOs without unifying the service layer. |
| **Pros**    | High maintainability, consistent architecture, leverages existing code.                          | Faster, less risk of regression in short term.           |
| **Cons**    | Requires more careful refactoring of existing working code (`UserService`).                      | accumulates technical debt.                              |

### Recommendation

**Option A**. The Command Pattern is already implemented in `commands.py`. We should use it to ensure the "EVCS" (Entity Version Control System) architecture is actually respected.

---

## Phase 4: Technical Design

### Implementation Strategy

1.  **Core**: Implement `TemporalService` methods using `CreateVersionCommand`, `UpdateVersionCommand`, etc.
2.  **Models**: Use `TYPE_CHECKING` imports in `User` to fix circular dependency.
3.  **Services**: Switch `AuthService` to use `UserService.get_by_email`. Update `UserService` to ensure it aligns with `TemporalService` (or inherits properly).

### TDD Test Blueprint

1.  **`test_temporal_service.py`**:
    - Test `create` (delegates to command)
    - Test `update` (delegates to command)
    - Test `get_all` (verifies temporal filter)

---

## Phase 5: Risk Assessment

- **Risk**: Circular dependency fix might still trigger runtime errors if not handled carefully.
  - _Mitigation_: Use string forward references and `from __future__ import annotations`.

---

## Phase 6: Effort Estimation

- **Development**: 2 hours
- **Verification**: 30 mins
