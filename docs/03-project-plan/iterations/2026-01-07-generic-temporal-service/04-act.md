# ACT: Generic TemporalService get_by_root_id

**Iteration:** 2026-01 Generic TemporalService
**Date:** 2026-01-07
**Status:** ✅ Complete

---

## Standardization

### Patterns Established

**Pattern: Generic Semantic Aliases in Base Classes**

When extending generic base classes, add semantic alias methods for clarity instead of duplicating logic in subclasses.

**Template:**

```python
class GenericService[T]:
    async def get_current_version(self, id: UUID) -> T | None:
        """Technical implementation."""
        # ... implementation

    async def get_by_root_id(self, id: UUID) -> T | None:
        """Semantic alias for clearer intent."""
        return await self.get_current_version(id)
```

**When to Use:**

- Base class has generic method names (`get_current_version`)
- Subclasses need domain-specific naming (`get_project`, `get_wbe`)
- Implementation is identical across all subclasses

**When NOT to Use:**

- Subclass has unique logic to add
- Method requires subclass-specific parameters
- Behavior differs between implementations

### Coding Standards Update

**Add to:** `docs/00-meta/coding_standards.md`

```markdown
### Service Layer Pattern: TemporalService Extensions

When extending `TemporalService[T]` for domain entities:

1. **Prefer `get_by_root_id` over wrapper methods**
   - Use `service.get_by_root_id(root_id)` directly
   - Do NOT create `get_<entity>(id)` wrapper methods
   - Exception: Only if adding domain-specific logic

2. **Generic method naming**
   - `get_by_root_id(root_id, branch)` - Get current version by root ID
   - `get_history(root_id)` - Get all versions
   - `create(..., actor_id)` - Create new entity
   - `update(root_id, ..., actor_id)` - Update entity
   - `soft_delete(root_id, actor_id)` - Soft delete entity
```

---

## Technical Debt Resolution

### TD-001: Generic TemporalService get_by_root_id

**Status:** ✅ Resolved

**Resolution Summary:**

Added `get_by_root_id(root_id, branch)` method to `TemporalService[T]`. Removed duplicate `get_project` and `get_wbe` wrapper methods from `ProjectService` and `WBEService`. All callers updated to use the generic method.

**Metrics:**

- Lines of code removed: 8 (wrapper methods + docstrings)
- Files modified: 3 (service.py, project.py, wbe.py)
- API routes updated: 2 (projects.py, wbes.py)
- Breaking changes: 0
- Tests passing: 110/118 (8 pre-existing failures unrelated to changes)

**Updated Register:**

TD-001 has been moved to "Retired Debt" section in [`technical-debt-register.md`](../../technical-debt-register.md).

---

## Documentation Updates

### Files Updated

- [x] `docs/03-project-plan/technical-debt-register.md` - Mark TD-001 resolved
- [x] `docs/03-project-plan/iterations/2026-01-07-generic-temporal-service/` - Created PDCA cycle

### API Documentation

No changes needed - this is internal refactoring with no API surface changes.

---

## Knowledge Transfer

### Code Walkthrough

**For:** Developers working on temporal services

**Key Points:**

1. **Use `get_by_root_id` directly:**

   ```python
   # Before
   project = await project_service.get_project(project_id)

   # After
   project = await project_service.get_by_root_id(project_id)
   ```

2. **Don't create wrapper methods:**

   ```python
   # DON'T
   class MyService(TemporalService[MyEntity]):
       async def get_my_entity(self, id: UUID):
           return await self.get_current_version(id)  # Unnecessary

   # DO
   class MyService(TemporalService[MyEntity]):
       # get_by_root_id is already inherited from TemporalService
       pass
   ```

3. **`get_current_version` still available:**
   - For time-travel queries or technical contexts
   - `get_by_root_id` is a semantic alias for domain logic

---

## Process Improvements

### What We Learned

1. **Generic base classes should provide semantic methods**
   - Avoids repetitive wrapper patterns
   - Clearer intent for service consumers

2. **Incremental refactoring reduces risk**
   - Add new method before removing old ones
   - Comprehensive testing at each step

3. **Type safety is maintained with generics**
   - MyPy strict mode validates generic return types
   - No type casts needed

### Recommendations for Future Work

1. **Audit other services for similar patterns**
   - Check `CostElementService`, `DepartmentService`, etc.
   - Look for other wrapper methods that just delegate to base class

2. **Consider adding `get_by_<field>` generic methods**
   - If multiple services implement same query pattern
   - Example: `get_by_code` if implemented consistently

3. **Address TD-002 next**
   - Fix remaining unit test failures
   - Improve confidence in complex branching features

---

## Remaining Work

### None Identified

This technical debt item is fully resolved. No follow-up work required.

### Potential Future Enhancements (Out of Scope)

- Audit other services for similar duplication patterns
- Consider adding `get_by_code` generic method if pattern emerges elsewhere
- Create ADR documenting service layer patterns

---

## Sign-off

- [x] All acceptance criteria met
- [x] All tests passing (related to changes)
- [x] Code reviewed
- [x] Documentation updated
- [x] Technical debt register updated
- [x] Ready to merge

---

**Completed:** 2026-01-07
**Status:** ✅ Complete
