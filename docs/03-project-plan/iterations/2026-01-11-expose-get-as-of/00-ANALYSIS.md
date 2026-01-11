# Request Analysis: Expose get_as_of in Service Interfaces

**Date Created:** 2026-01-11
**Related Technical Debt:** [TD-026](../../technical-debt-register.md#td-026-expose-get_as_of-in-service-interfaces)
**Related Documentation:**
- [Time Travel Architecture](../../../02-architecture/cross-cutting/time-travel.md)
- [ADR-005: Bitemporal Versioning](../../../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [Coding Standards](../../../02-architecture/coding-standards.md)

---

## Clarified Requirements

**Problem Statement:**
The `TemporalService.get_as_of()` method is fully implemented with comprehensive bitemporal support (System Time Travel semantics, STRICT/MERGE branch modes, proper zombie deletion handling), but individual service classes (`ProjectService`, `WBEService`, `CostElementService`, `CostElementTypeService`, `DepartmentService`, `UserService`) do not expose this method in their public interfaces.

**Impact:**
- Developers cannot query entity state at specific timestamps via service layer
- Must either use `TemporalService` directly (breaking abstraction) or rely on list endpoints with `as_of` parameter (less ergonomic for single-entity queries)
- Inconsistent API: time travel available for lists but not for single entity retrieval via services

**Functional Requirements:**
1. Each service extending `TemporalService` should expose a `get_as_of()` method
2. Method signature must include: `entity_id`, `as_of`, `branch` (default: "main"), `branch_mode` (optional)
3. Method must use System Time Travel semantics (as implemented in base class)
4. Method must support STRICT and MERGE branch modes
5. Return type: Entity | None

**Non-Functional Requirements:**
- **Type Safety:** 100% type hint coverage, MyPy strict mode compliance
- **Code Quality:** Zero Ruff errors, Google-style docstrings
- **Testing:** 100% coverage for new methods, including zombie check pattern tests
- **Documentation:** Update time-travel.md to document which services support time-travel queries

**Constraints:**
- Must maintain backward compatibility (no breaking changes to existing service methods)
- Must follow existing service patterns (e.g., `get_project_history` wrapper pattern)
- Must comply with coding standards (strict typing, functional/stateless where possible)

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories:**
- Time Machine / Time Travel: Query system state as of historical timestamp
- Change Order Management: Preview changes in isolated branch before merging
- Audit Trail: Reproduce exact system state at specific point in time

**Domain Concepts:**
- **Bitemporal Model:** Two time dimensions (valid_time, transaction_time)
- **System Time Travel:** Query exact historical state (transaction_time @> as_of)
- **Branch Modes:** STRICT (only specified branch), MERGE (fallback to main)
- **Zombie Deletion:** Soft-deleted entities respect temporal boundaries

### Architecture Context

**Bounded Contexts Involved:**
- EVCS Core (Entity Version Control System)
- All versioned entity services (Project, WBE, CostElement, CostElementType, Department, User)

**Existing Patterns:**
- Services extend `TemporalService[T]` for versioned entities
- Services delegate to generic commands (CreateVersionCommand, UpdateVersionCommand)
- Services expose domain-specific methods (e.g., `get_by_code`, `get_project_history`)
- List methods already support `as_of` parameter using `_apply_bitemporal_filter`

**Key Architectural Decisions:**
- **ADR-005:** Bitemporal Single-Table Pattern with TSTZRANGE
- **ADR-003:** Command Pattern for state changes
- **ADR-007:** RBAC Service (permissions may apply to time-travel queries)

### Codebase Analysis

**Backend:**

**Base Implementation** ([`backend/app/core/versioning/service.py:135-191`](../../../backend/app/core/versioning/service.py#L135-L191)):

`TemporalService.get_as_of()` is fully implemented with:
- Bitemporal filtering using `_apply_bitemporal_filter_for_time_travel()`
- STRICT and MERGE branch mode support
- Explicit branch deletion check (`_is_deleted_on_branch()`)
- Complete docstring explaining System Time Travel semantics

**Existing Related Services:**

| Service | Entity | Extends TemporalService | Has `as_of` in List Methods | Exposes `get_as_of` |
|---------|--------|------------------------|----------------------------|-------------------|
| ProjectService | Project | ✅ | ✅ | ❌ |
| WBEService | WBE | ✅ | ✅ | ❌ |
| CostElementService | CostElement | ✅ | ✅ | ❌ |
| CostElementTypeService | CostElementType | ✅ | ✅ | ❌ |
| DepartmentService | Department | ✅ | ❌ | ❌ |
| UserService | User | ✅ | ❌ | ❌ |

**Existing API Endpoints with get_as_of:**
- [`backend/app/api/routes/projects.py`](../../../backend/app/api/routes/projects.py) - uses `get_as_of` directly
- [`backend/app/api/routes/cost_elements.py`](../../../backend/app/api/routes/cost_elements.py) - uses `get_as_of` directly
- [`backend/app/api/routes/wbes.py`](../../../backend/app/api/routes/wbes.py) - uses `get_as_of` directly

**Pattern Observation:**
API routes currently call `TemporalService.get_as_of()` directly, bypassing service abstraction. This works but breaks layer boundaries (API layer should use service methods, not base class methods).

**Existing Tests:**
- [`backend/tests/unit/core/versioning/test_base_coverage.py`](../../../backend/tests/unit/core/versioning/test_base_coverage.py) - includes `get_as_of` tests for base class
- No service-level tests for `get_as_of` functionality

**Frontend:**

No direct impact on frontend (this is backend-only change). Frontend consumes API endpoints, which already support time travel via `as_of` query parameter on list endpoints.

**Data Models:**
All entities follow `VersionableProtocol` with:
- `valid_time: TSTZRANGE`
- `transaction_time: TSTZRANGE`
- `deleted_at: datetime | None`
- `branch: str`

---

## Solution Options

### Option 1: Thin Wrapper Pattern (Recommended)

**Architecture & Design:**

Add thin wrapper methods to each service that delegate to base class `get_as_of()`. Follow existing pattern used for `get_history()`:

```python
class ProjectService(TemporalService[Project]):
    async def get_project_as_of(
        self,
        project_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> Project | None:
        """Get project as it was at specific timestamp.

        Delegates to TemporalService.get_as_of() for System Time Travel semantics.
        """
        return await self.get_as_of(project_id, as_of, branch, branch_mode)
```

**UX Design:**
- Method name follows existing convention: `get_{entity}_as_of`
- Parameters consistent across all services
- Docstring references base class for detailed semantics

**Implementation:**

**Files to Modify:**
1. `backend/app/services/project.py` - add `get_project_as_of()`
2. `backend/app/services/wbe.py` - add `get_wbe_as_of()`
3. `backend/app/services/cost_element_service.py` - add `get_cost_element_as_of()`
4. `backend/app/services/cost_element_type_service.py` - add `get_cost_element_type_as_of()`
5. `backend/app/services/department.py` - add `get_department_as_of()`
6. `backend/app/services/user.py` - add `get_user_as_of()`

**Tests to Add:**
- Service-level tests for each `get_{entity}_as_of` method
- Zombie check TDD pattern tests (Create → Delete → Query Past)
- Branch mode tests (STRICT vs MERGE)

**Documentation Updates:**
- Update `time-travel.md` to list services supporting time-travel queries
- Mark TD-026 as complete

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Minimal code change, follows existing pattern, maintains abstraction, no breaking changes |
| Cons | Slight boilerplate (6 methods x ~10 lines each) |
| Complexity | Low - thin wrappers, well-understood pattern |
| Maintainability | Excellent - consistent with existing codebase |
| Performance | No impact - direct delegation |

---

### Option 2: Generic Mixin Approach

**Architecture & Design:**

Create a mixin class that automatically exposes `get_as_of` with domain-specific naming:

```python
class TimeTravelMixin[T]:
    """Mixin to expose get_as_of with domain-specific naming."""

    def _get_entity_name(self) -> str:
        """Derive entity name from service class (e.g., ProjectService -> Project)."""
        # ... introspection logic ...

    async def get_as_of_named(self, entity_id: UUID, as_of: datetime, **kwargs) -> T | None:
        """Generic method with auto-generated docstring."""
        return await self.get_as_of(entity_id, as_of, **kwargs)

class ProjectService(TimeTravelMixin[Project], TemporalService[Project]):
    # Inherit get_as_of_named from mixin
    pass
```

**UX Design:**
- Single method name: `get_as_of_named()`
- Less ergonomic than domain-specific names
- Auto-generated docstrings may be less clear

**Implementation:**

**Files to Create:**
1. `backend/app/core/versioning/mixins.py` - new `TimeTravelMixin`

**Files to Modify:**
1. All service classes - add mixin to inheritance chain

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | DRY principle, centralized logic |
| Cons | Complex introspection, unclear method names, harder to discover, potential MRO issues |
| Complexity | Medium - requires careful Python MRO understanding |
| Maintainability | Fair - adds abstraction layer to understand |
| Performance | Negligible impact - method lookup overhead |

---

### Option 3: Direct Base Class Usage (Status Quo)

**Architecture & Design:**

Continue using `TemporalService.get_as_of()` directly from API routes. No service-level exposure.

**UX Design:**
- API layer breaks abstraction boundary
- Service layer incomplete (missing time-travel single-entity queries)
- Inconsistent with service layer philosophy

**Implementation:**

No code changes required.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Zero code change, works today |
| Cons | Breaks layer boundaries, inconsistent API, harder to test, violates service layer pattern |
| Complexity | N/A - existing pattern |
| Maintainability | Poor - non-idiomatic, confuses developers |
| Performance | No impact |

---

## Comparison Summary

| Criteria | Option 1: Thin Wrappers | Option 2: Generic Mixin | Option 3: Status Quo |
|----------|------------------------|-------------------------|----------------------|
| Development Effort | ~30 min | ~2 hours | 0 min |
| Code Quality | Excellent - follows existing pattern | Fair - clever but complex | Poor - breaks abstraction |
| API Consistency | High - domain-specific names | Medium - generic names | Low - no service API |
| Type Safety | 100% - explicit types | 100% - generic types | N/A |
| Testability | Excellent - easy to mock/verify | Fair - complex to test | Poor - requires base class mocking |
| Maintainability | Excellent - clear, simple | Fair - requires Python MRO knowledge | Poor - non-idiomatic |
| Best For | **Production code, team clarity** | Framework/library code | Quick prototyping (not recommended) |

---

## Recommendation

**I recommend Option 1 (Thin Wrapper Pattern) because:**

1. **Follows Existing Patterns:** Matches `get_project_history()`, `get_user_history()` wrapper pattern already in use
2. **Maintains Abstraction:** API layer uses service methods, not base class methods
3. **Type Safety:** Explicit return types (`Project | None`) enable full MyPy checking
4. **Testability:** Easy to mock and verify at service level
5. **Discoverability:** Domain-specific names (`get_project_as_of`) are easy to find via autocomplete
6. **Documentation:** Each method can have entity-specific docstring with examples
7. **Zero Breaking Changes:** Additive only, no existing code affected

**Alternative consideration:** Choose Option 2 only if building a reusable framework/library for external consumption. For internal application code, Option 1 is superior.

---

## Questions for Decision

1. **Confirm:** Should we follow the existing `get_{entity}_history()` naming pattern (e.g., `get_project_as_of`) or use a shorter name (e.g., `get_as_of_project`)?

   *Recommendation:* Use `get_project_as_of` to match existing `get_project_history` pattern.

2. **BranchMode Import:** Should we import `BranchMode` enum in each service or use string literal with type alias?

   *Recommendation:* Import enum from `app.core.versioning.enums` for type safety.

3. **Test Coverage:** Should we test all branch modes (STRICT, MERGE) for each service, or test once in base class and verify delegation in services?

   *Recommendation:* Test delegation in services + zombie check TDD pattern for each entity. Branch mode logic tested in base class.

4. **Documentation Detail Level:** How extensive should docstrings be? Reference base class or duplicate semantics?

   *Recommendation:* Brief docstring with parameter descriptions, reference to `TemporalService.get_as_of()` for detailed semantics.

---

## Next Steps

Upon approval, proceed to **PLAN phase** to create detailed implementation plan including:
- Exact method signatures for each service
- Test cases (zombie check TDD pattern)
- Documentation updates
- Verification checklist
