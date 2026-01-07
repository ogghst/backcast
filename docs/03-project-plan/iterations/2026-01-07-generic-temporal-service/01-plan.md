# PLAN: Generic TemporalService get_by_root_id

**Iteration:** 2026-01 Generic TemporalService
**Start Date:** 2026-01-07
**Estimated Duration:** 4-6 hours
**Status:** 🟡 Planning

---

## Objective

Eliminate code duplication in `ProjectService` and `WBEService` by adding a generic `get_by_root_id` method to `TemporalService[T]`. Currently, each service implements its own wrapper method (`get_project`, `get_wbe`) that simply calls the inherited `get_current_version` method, violating DRY principles.

**Success Criteria:**

- `TemporalService` has a generic `get_by_root_id(root_id, branch)` method
- `ProjectService.get_project` is removed (callers use `get_by_root_id` directly)
- `WBEService.get_wbe` is removed (callers use `get_by_root_id` directly)
- All existing tests pass without modification
- No breaking changes to API routes
- Technical debt item TD-001 is marked as resolved

---

## Context Analysis

### Documentation Review

- **Technical Debt Register** (`docs/03-project-plan/technical-debt-register.md`): TD-001 identifies duplication in root ID querying logic across services
- **Architecture** (`docs/02-architecture/`): EVCS system uses `TemporalService[T]` as the base for all versioned entities
- **Project Plan**: This is a high-severity debt item with 6-hour estimate, targeting completion by 2026-01-10

### Codebase Analysis

**Current State:**

1. **`TemporalService[T]`** ([service.py](../../../../../backend/app/core/versioning/service.py)): Has `get_current_version(root_id, branch)` method
2. **`ProjectService`** ([project.py](../../../../../backend/app/services/project.py)): Defines `get_project(project_id)` that calls `self.get_current_version(project_id)`
3. **`WBEService`** ([wbe.py](../../../../../backend/app/services/wbe.py)): Defines `get_wbe(wbe_id)` that calls `self.get_current_version(wbe_id)`

**Duplication Pattern:**

```python
# In ProjectService (lines 31-33)
async def get_project(self, project_id: UUID) -> Project | None:
    """Get project by root project_id (current version in main branch)."""
    return await self.get_current_version(project_id)

# In WBEService (lines 31-33)
async def get_wbe(self, wbe_id: UUID) -> WBE | None:
    """Get WBE by root wbe_id (current version in main branch)."""
    return await self.get_current_version(wbe_id)
```

**Existing Tests:**

- Unit tests in `tests/unit/test_project_service.py`
- Unit tests in `tests/unit/test_wbe_service.py`
- API route tests that use these service methods

---

## Problem Definition

### 1. Problem Statement

What specific problem are we solving?

Each service extending `TemporalService[T]` implements its own wrapper method for getting the current version by root ID. This is unnecessary boilerplate that:
- Violates DRY (Don't Repeat Yourself)
- Increases maintenance burden (changes must be synchronized)
- Creates inconsistent naming (`get_project` vs `get_wbe` vs potentially others)
- Adds no value over the base `get_current_version` method

Why is it important now?

- **High severity debt**: TD-001 is marked as high priority
- **Growing pain**: As more versioned entities are added, duplication will multiply
- **Upcoming work**: E03-U06 implementation will benefit from cleaner patterns

What happens if we don't address it?

- Continued code duplication across all temporal services
- Inconsistent API patterns as new services are added
- Maintenance burden increases with each new entity

What is the business value?

- Reduced maintenance overhead
- Cleaner, more consistent codebase
- Foundation for future entity services

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- `TemporalService.get_by_root_id()` works for all entity types (Project, WBE, CostElement, etc.)
- All existing tests pass without modification
- API routes continue to work identically
- Type safety is maintained (generic return type)

**Technical Criteria:**

- Zero breaking changes to public API
- Test coverage remains at 80%+
- MyPy strict mode passes
- Ruff linting passes

**Code Quality Criteria:**

- Lines of code reduced (wrapper methods removed)
- Consistent naming across services
- Documentation updated

### 3. Scope Definition

**In Scope:**

- Add `get_by_root_id(root_id, branch)` method to `TemporalService[T]`
- Remove `get_project()` from `ProjectService`
- Remove `get_wbe()` from `WBEService`
- Update all callers to use `get_by_root_id()` directly
- Update unit tests
- Run full test suite to verify no regressions

**Out of Scope:**

- Refactoring other service methods (e.g., `get_by_code`, `get_projects`)
- Changing `TemporalService.get_current_version` (keep as is for backward compatibility)
- Frontend changes (this is backend-only)
- Database migrations (no schema changes)

---

## Implementation Options

| Aspect | Option A: Add Alias Method | Option B: Rename & Deprecate | Option C: Service-Specific Mixin |
|--------|---------------------------|------------------------------|---------------------------------|
| **Approach Summary** | Add `get_by_root_id` as new method alongside `get_current_version`. Keep both, update services to use new name. | Rename `get_current_version` to `get_by_root_id`, add `get_current_version` as deprecated alias. | Create a mixin trait with `get_by_root_id` that services can optionally use. |
| **Design Patterns** | Simple additive change, backward compatible | Deprecation pattern for migration | Trait/mixin pattern |
| **Pros** | - Cleanest API<br>- No deprecation warnings<br>- Clear intent<br>- Both methods available for different use cases | - Single canonical method<br>- Migration path for existing code<br>- Eventually cleaner API | - Maximum flexibility<br>- Services can opt-in |
| **Cons** | - Two methods for same operation (potential confusion) | - Deprecation period adds complexity<br>- Need to manage deprecation lifecycle | - More complex<br>- Overkill for simple case |
| **Test Strategy Impact** | Update service tests to call new method, verify same behavior | Update all callers, verify deprecation warnings | More test cases needed |
| **Risk Level** | Low (additive change) | Medium (deprecation churn) | Low-Medium (added complexity) |
| **Estimated Complexity** | Simple | Moderate | Moderate |

### Recommendation

**Option A: Add Alias Method**

Rationale:
1. **Backward Compatibility**: Zero breaking changes - `get_current_version` remains available
2. **Clear Intent**: `get_by_root_id` is more semantic for service-level callers
3. **Low Risk**: Additive change only, easy to revert if needed
4. **Consistent with Python**: Both `dict.get()` and `dict.__getitem__()` coexist for different use cases
5. **Future Flexibility**: `get_current_version` could be enhanced for time-travel scenarios

> [!IMPORTANT] **Human Decision Point**: This plan recommends Option A (add new `get_by_root_id` method). The approach maintains backward compatibility while providing clearer semantics. Ready to proceed unless you prefer a different option.

---

## Technical Design

### TDD Test Blueprint

```
├── Unit Tests (TemporalService)
│   ├── Test get_by_root_id returns same result as get_current_version
│   ├── Test get_by_root_id with different branches
│   ├── Test get_by_root_id returns None for non-existent root_id
│   └── Test get_by_root_id type safety (Project vs WBE)
├── Integration Tests (Service callers)
│   ├── Verify API routes work with updated service calls
│   ├── Verify ProjectService callers updated correctly
│   └── Verify WBEService callers updated correctly
└── Regression Tests
    └── Run full test suite to ensure no behavioral changes
```

**First 3 Test Cases (ordered simplest to most complex):**

1. **Test `get_by_root_id` mirrors `get_current_version`**:
   - Create a project
   - Call both `get_current_version` and `get_by_root_id` with same root_id
   - Assert results are identical

2. **Test `get_by_root_id` returns None for missing entity**:
   - Call with non-existent UUID
   - Assert returns None

3. **Test `get_by_root_id` respects branch parameter**:
   - Create project in "main" branch
   - Create branch with modified project
   - Assert `get_by_root_id(root_id, "feature")` returns feature version

### Implementation Strategy

1. **Add method to `TemporalService`**:
   - Add `async def get_by_root_id(self, root_id: UUID, branch: str = "main") -> TVersionable | None`
   - Implementation: `return await self.get_current_version(root_id, branch)`
   - Add docstring explaining purpose

2. **Update `ProjectService`**:
   - Remove `get_project` method
   - Search/replace callers to use `get_by_root_id`

3. **Update `WBEService`**:
   - Remove `get_wbe` method
   - Search/replace callers to use `get_by_root_id`

4. **Update tests**:
   - Modify service tests to call `get_by_root_id` instead
   - Verify behavior unchanged

5. **Verification**:
   - Run full test suite
   - Run MyPy and Ruff

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Breaking Changes** | API route tests fail due to method removal | Low | High | Add `get_by_root_id` before removing wrappers; run tests before removal |
| **Type Safety** | Generic typing breaks with new method | Low | Medium | Verify with MyPy strict mode; use same type hints as `get_current_version` |
| **Missing Callers** | Some callers not updated, causing runtime errors | Medium | Medium | Use IDE "Find Usages" to ensure all callers updated; comprehensive testing |
| **Documentation Out of Sync** | API docs reference old methods | Low | Low | Update OpenAPI docs if needed; verify auto-generation works |

---

## Effort Estimation

### Time Breakdown

- **Planning & Analysis**: 0.5 hours (completed in this PLAN phase)
- **Implementation**: 1.5 hours
  - Add method to `TemporalService`: 15 min
  - Update `ProjectService`: 20 min
  - Update `WBEService`: 20 min
  - Update callers and tests: 35 min
- **Testing**: 1.5 hours
  - Run unit tests: 30 min
  - Run API tests: 30 min
  - Manual verification: 30 min
- **Documentation**: 0.5 hours
- **Buffer**: 1 hour

**Total Estimated Effort:** 4-5 hours (within 6-hour estimate from TD-001)

### Prerequisites

- Backend development environment running
- PostgreSQL database available
- All tests passing before starting
- Git branch created for this work

---

## Related Files

**To Modify:**

- [backend/app/core/versioning/service.py](../../../../../backend/app/core/versioning/service.py) - Add `get_by_root_id` method
- [backend/app/services/project.py](../../../../../backend/app/services/project.py) - Remove `get_project`, update callers
- [backend/app/services/wbe.py](../../../../../backend/app/services/wbe.py) - Remove `get_wbe`, update callers
- [backend/tests/unit/test_project_service.py](../../../../../backend/tests/unit/test_project_service.py) - Update tests
- [backend/tests/unit/test_wbe_service.py](../../../../../backend/tests/unit/test_wbe_service.py) - Update tests

**To Verify:**

- [backend/app/api/routes/projects.py](../../../../../backend/app/api/routes/projects.py) - Verify callers updated
- [backend/app/api/routes/wbes.py](../../../../../backend/app/api/routes/wbes.py) - Verify callers updated

---

## Definition of Done

- [ ] `get_by_root_id` method added to `TemporalService[T]`
- [ ] `ProjectService.get_project` removed
- [ ] `WBEService.get_wbe` removed
- [ ] All callers updated to use `get_by_root_id`
- [ ] All unit tests pass
- [ ] All API tests pass
- [ ] MyPy strict mode passes (zero errors)
- [ ] Ruff linting passes (zero errors)
- [ ] Test coverage remains at 80%+
- [ ] Technical debt TD-001 marked as resolved in register
- [ ] Code reviewed and merged

---

**Status:** 🟡 Ready to Start
**Assigned:** Backend Developer
**Start Date:** 2026-01-07
**Target Completion:** 2026-01-07
