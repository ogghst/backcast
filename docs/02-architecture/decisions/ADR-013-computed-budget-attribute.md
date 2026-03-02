# ADR-013: Computed Budget Attribute Pattern

## Status

Accepted

## Context

In the original WBE (Work Breakdown Element) design, the `budget_allocation` field was stored directly on the WBE entity. This created a data duplication problem:

1. Budgets were also stored at the `CostElement.budget_amount` level
2. This violated the Single Source of Truth principle
3. Data could become inconsistent between WBEs and their child CostElements
4. EVM calculations had to choose which source to trust

The system needed a way to:
- Maintain API compatibility (WBERead must include budget_allocation)
- Remove storage duplication
- Ensure budget data is always consistent

## Decision

We will use the **Computed Attribute Pattern** for WBE budgets:

1. **Storage**: Budgets are stored ONLY in `CostElement.budget_amount`
2. **Computation**: `WBE.budget_allocation` is computed on-the-fly as `SUM(child CostElement.budget_amount)`
3. **API Compatibility**: `WBERead` schema includes `budget_allocation` as a computed field
4. **Input Schemas**: `WBECreate` and `WBEUpdate` do NOT accept `budget_allocation` input

### Implementation Details

```python
# Model: Non-mapped attribute
class WBE(EntityBase, VersionableMixin, BranchableMixin):
    __allow_unmapped__ = True  # Allow non-mapped attributes

    # Computed attribute (not stored in DB)
    budget_allocation: Decimal | None = None

# Service: Population method
class WBEService(BranchableService[WBE]):
    async def _compute_wbe_budget(self, wbe_id: UUID, branch: str) -> Decimal:
        stmt = select(func.sum(CostElement.budget_amount)).where(...)
        return result.scalar() or Decimal("0")

    async def _populate_computed_budgets(self, wbes: list[WBE], branch: str) -> list[WBE]:
        for wbe in wbes:
            wbe.budget_allocation = await self._compute_wbe_budget(wbe.wbe_id, branch)
        return wbes
```

## Consequences

### Positive

- **Single Source of Truth**: Budgets exist in exactly one place (CostElement)
- **Data Consistency**: No possibility of WBE-CostElement budget mismatch
- **Simpler Updates**: Budget changes only need to update CostElement
- **EVM Accuracy**: All calculations use the same budget source

### Negative

- **Query Performance**: Budget computation requires additional database queries
- **Service Complexity**: All WBE-returning methods must call `_populate_computed_budgets()`
- **Historical Queries**: Historical budget reflects current cost elements (not time-traveled)

### Mitigations

- Performance: Can be optimized with bulk loading if needed
- Complexity: Documented pattern with helper method
- Historical: Future enhancement could add time-travel to cost elements

## Alternatives Considered

1. **Database View**: Create a database view for WBEs with computed budget
   - Rejected: Doesn't work well with SQLAlchemy ORM and bitemporal queries

2. **Hybrid Property**: Use SQLAlchemy `@hybrid_property` for computation
   - Rejected: Requires complex SQL generation for filtered queries

3. **Cached Budget**: Store computed budget with periodic refresh
   - Rejected: Reintroduces data duplication and consistency issues

## Notes

- Migration: `20260228_remove_wbe_budget_allocation.py` handles data migration
- Rollback: Migration includes `downgrade()` to restore the column
- Pattern Reusable: This pattern can be applied to other computed aggregations

**Date**: 2026-02-28
**Iteration**: 2026-02-28-remove-wbe-budget-allocation
