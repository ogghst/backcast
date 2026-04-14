# Testing Patterns

**Last Updated:** 2026-04-14
**Context:** Integration and temporal testing best practices

---

## Integration Test Patterns

### 1. Use Real Pydantic Schemas

**❌ Don't:** Create dynamic types with `type()` and `lambda`

```python
# BAD - No type safety, hard to debug
await service.create(
    change_order_in=type("ChangeOrderCreate", (), {
        "project_id": project_id,
        "model_dump": lambda self: {...}
    })(),
    actor_id=actor_id
)
```

**✅ Do:** Import and use actual Pydantic schemas

```python
# GOOD - Type-safe, catches errors early
from app.models.schemas.change_order import ChangeOrderCreate

create_schema = ChangeOrderCreate(
    project_id=project_id,
    code="CO-001",
    title="Test Change Order"
)

await service.create(
    change_order_in=create_schema,
    actor_id=actor_id
)
```

**Benefits:**

- Type checking catches errors at test time
- IDE autocomplete works
- Validation errors are clear
- Matches production code paths

---

### 2. Capture Service Return Values

**❌ Don't:** Pre-generate IDs and assume they match

```python
# BAD - Service generates its own ID
co_id = uuid4()
await service.create(...)
co = await service.get_current(co_id)  # Will fail!
```

**✅ Do:** Capture the returned entity and use its ID

```python
# GOOD - Use service-generated ID
created_co = await service.create(...)
co_id = created_co.change_order_id
co = await service.get_current(co_id)  # Works!
```

**Why:** Services may generate UUIDs internally or use different ID fields than expected.

---

## Temporal Testing Patterns

### 3. Time-Travel Testing with Explicit Delays

**❌ Don't:** Rely on implicit timing

```python
# BAD - Timestamps may be identical
before = datetime.now(timezone.utc)
await service.archive(...)
after = datetime.now(timezone.utc)
# before == after is possible!
```

**✅ Do:** Add explicit delays to ensure distinct timestamps

```python
# GOOD - Guaranteed distinct timestamps
import asyncio

await asyncio.sleep(0.1)  # Ensure past timestamp
before_archive = datetime.now(timezone.utc)
await asyncio.sleep(0.1)  # Ensure future timestamp

await service.archive(...)

# Time-travel query
entity_past = await service.get_as_of(entity_id, before_archive)
assert entity_past is not None
```

**Benefits:**

- Reliable time-travel queries
- No flaky tests due to timing
- Clear temporal boundaries

---

### 4. Verify Soft-Delete Behavior

**Pattern:** Test both active and historical access

```python
# 1. Verify entity is hidden from active queries
with pytest.raises(NoResultFound):
    await service.get_by_name(name, project_id)

# 2. Verify entity is visible in time-travel
entity_past = await service.get_as_of(entity_id, before_delete)
assert entity_past is not None
assert entity_past.deleted_at is None  # Was active in the past
```

---

## Service Testing Patterns

### 5. Check Base Class Signatures

**Before implementing:** Always view the base class to understand inherited methods.

```python
# Example: BranchService inherits from TemporalService
# Check TemporalService.soft_delete signature BEFORE calling

# TemporalService.soft_delete signature:
async def soft_delete(
    self,
    entity_id: UUID,  # Uses root_id, not composite key!
    actor_id: UUID,
    control_date: datetime | None = None
) -> None:
    ...

# Correct usage:
await branch_service.soft_delete(
    entity_id=branch.branch_id,  # Not (name, project_id)
    actor_id=actor_id
)
```

**Tip:** Use `view_code_item` or IDE "Go to Definition" to check base classes.

---

### 6. Test Status Validation

**Pattern:** Always test both valid and invalid state transitions

```python
# Test 1: Valid operation
async def test_archive_implemented_change_order():
    # Setup: Create CO and set to "Implemented"
    co.status = "Implemented"
    await service.archive(co_id, actor_id)
    # Assert: Success

# Test 2: Invalid operation
async def test_archive_active_change_order_fails():
    # Setup: CO in "Draft" status
    with pytest.raises(ValueError, match="Cannot archive active"):
        await service.archive(co_id, actor_id)
```

---

## Common Pitfalls

### 1. Forgetting to Commit DB Changes in Test Setup

```python
# BAD - Changes not visible to service
co.status = "Implemented"
db_session.add(co)
# Missing: await db_session.commit()

# GOOD
co.status = "Implemented"
db_session.add(co)
await db_session.commit()
await db_session.refresh(co)
```

### 2. Not Handling Async Context Properly

```python
# BAD - Missing await
entity = service.get_current(entity_id)  # Returns coroutine!

# GOOD
entity = await service.get_current(entity_id)
```

### 3. Hardcoding Branch Names

```python
# BAD - Assumes branch naming convention
branch_name = "BR-001"

# GOOD - Use service-returned value
created_co = await service.create(...)
branch_name = created_co.branch_name  # e.g., "BR-CO-001"
```

---

## Quick Reference

| Pattern | Key Takeaway |
| --- | --- |
| Schema Usage | Import real Pydantic schemas, not dynamic types |
| ID Capture | Use service-returned IDs, don't pre-generate |
| Time-Travel | Add `asyncio.sleep(0.1)` for distinct timestamps |
| Soft-Delete | Test both active (hidden) and historical (visible) |
| Base Classes | Check signatures before implementing |
| Validation | Test both valid and invalid state transitions |

---

## Related Documentation

- [TemporalService API](file:///home/nicola/dev/backcast_evs/backend/app/core/versioning/service.py)
- [BranchService API](file:///home/nicola/dev/backcast_evs/backend/app/services/branch_service.py)
- [Integration Test Examples](file:///home/nicola/dev/backcast_evs/backend/tests/integration/)
