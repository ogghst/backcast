# ADR-011: Generic EVM Metric System

## Status
✅ Accepted (2026-01-22)

## Context

The Earned Value Management (EVM) system initially supported only cost elements, with a dedicated schema (`EVMMetricsRead`) and API endpoint (`/api/v1/cost-elements/{id}/evm`). As the system evolved, we needed to support EVM calculations at multiple aggregation levels:

- **Cost Elements**: Individual budget line items (leaf level)
- **WBEs (Work Breakdown Elements)**: Groups of cost elements (mid-level)
- **Projects**: Groups of WBEs (top-level)

We faced several challenges:

1. **Code duplication**: Separate EVM calculation logic for each entity type
2. **Inconsistent schemas**: Different response formats for cost elements vs. aggregations
3. **Limited frontend reusability**: Components tightly coupled to cost element structure
4. **Scalability**: Adding new entity types would require repeating the same patterns

## Decision

We implemented a **generic EVM metric system** with the following characteristics:

### 1. Flat Response Schema

**Decision**: Use a flat response structure with all metrics explicitly defined, NOT a list of metric objects.

**Schema Definition**:
```python
class EVMMetricsResponse(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    bac: Decimal | None
    pv: Decimal | None
    ac: Decimal | None
    ev: Decimal | None
    cv: Decimal | None
    sv: Decimal | None
    cpi: Decimal | None
    spi: Decimal | None
    eac: Decimal | None
    vac: Decimal | None
    etc: Decimal | None
    control_date: datetime
    branch: str
    branch_mode: BranchMode
    progress_percentage: Decimal | None
    warning: str | None
```

**Rationale**:
- **Type safety**: Each metric has explicit type (Decimal | None)
- **API clarity**: Consumers know exactly which fields are available
- **Frontend simplicity**: Direct property access (`metrics.cpi`) vs. array lookup
- **OpenAPI documentation**: Each metric appears as a field with description

### 2. Polymorphic Entity Support

**Decision**: Use an `EntityType` enum to support multiple entity types through the same API.

**Implementation**:
```python
class EntityType(str, Enum):
    COST_ELEMENT = "cost_element"
    WBE = "wbe"
    PROJECT = "project"
```

**Generic API Routes**:
- `GET /api/v1/evm/{entity_type}/{entity_id}/metrics` - Single entity metrics
- `GET /api/v1/evm/{entity_type}/{entity_id}/timeseries` - Time-series data
- `POST /api/v1/evm/batch` - Batch aggregation

**Rationale**:
- **Single endpoint pattern**: One set of routes for all entity types
- **Frontend reusability**: Same components work for all entity types
- **Extensibility**: Adding new entity types requires minimal code changes
- **Consistency**: Uniform API surface across all aggregation levels

### 3. Hierarchical Aggregation Strategy

**Decision**: Implement hierarchical aggregation where child entities roll up to parent entities.

**Aggregation Rules**:

| Metric Type | Aggregation Method | Formula |
| ----------- | ------------------ | ------- |
| **Amounts** (BAC, PV, AC, EV, CV, SV, EAC, VAC, ETC) | **Sum** | `sum(child.metric)` |
| **Indices** (CPI, SPI) | **Weighted Average** | `sum(child.metric * child.BAC) / sum(child.BAC)` |

**Implementation**:
```python
async def _calculate_wbe_evm_metrics(
    self, wbe_ids: list[UUID], ...
) -> EVMMetricsResponse:
    # Fetch all child cost elements
    cost_elements = await ce_service.get_by_wbe_ids(wbe_ids, ...)

    # Calculate metrics for each child
    child_metrics = [
        await self.calculate_evm_metrics(ce.id, ...)
        for ce in cost_elements
    ]

    # Aggregate: sum for amounts, weighted avg for indices
    return self._aggregate_evm_metrics(child_metrics)
```

**Rationale**:
- **Mathematical correctness**: Weighted averages prevent bias from small cost elements
- **EVM standard compliance**: ANSI/EIA-748 specifies BAC-weighted indices
- **Intuitive sums**: Amount metrics naturally sum across children
- **Deterministic**: Same input always produces same output

### 4. Batch Query Support

**Decision**: Support batch queries for multiple entities with server-side aggregation.

**API Endpoint**:
```python
POST /api/v1/evm/batch
{
  "entity_type": "cost_element",
  "entity_ids": ["uuid1", "uuid2", "uuid3"],
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merge"
}
```

**Use Cases**:
- Calculate metrics for multiple cost elements in a single request
- Generate WBE/project metrics from child entities
- Reduce API calls for dashboard views

**Rationale**:
- **Performance**: Single query vs. N queries for N entities
- **Consistency**: Same aggregation logic used for single and batch
- **Frontend efficiency**: Fewer network requests for complex views

## Consequences

### Positive

1. **Code Reusability**: Frontend components (EVMSummaryView, EVMAnalyzerModal, MetricCard) work for all entity types
2. **Type Safety**: Explicit schema fields enable MyPy strict mode compliance
3. **API Consistency**: Uniform endpoint structure reduces cognitive load
4. **Testability**: Generic service methods easier to test with known datasets
5. **Performance**: Batch queries reduce N+1 query problems
6. **Extensibility**: Adding new entity types requires:
   - Adding enum value to `EntityType`
   - Implementing child fetching logic
   - No changes to schemas or frontend components

### Negative

1. **Schema Rigidity**: Adding new metrics requires schema changes (vs. dynamic list)
2. **Frontend Coupling**: Frontend must import `EntityType` enum from backend types
3. **Documentation Overhead**: Flat schema requires documenting each field separately
4. **Aggregation Complexity**: Weighted average calculations require careful testing

## Alternatives Considered

### Alternative 1: List of Metric Objects

```python
class EVMMetricsResponse(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    metrics: list[EVMMetricBase]

class EVMMetricBase(BaseModel):
    name: str
    value: Decimal | None
    unit: str
```

**Pros**:
- Dynamic metric addition without schema changes
- Self-documenting (metric name + value + unit)

**Cons**:
- **Type safety**: Lost - consumers must cast values
- **API clarity**: Consumers must know which metrics exist
- **Frontend complexity**: Requires array lookup and type guards
- **OpenAPI docs**: Less specific (array of objects vs. explicit fields)

**Rejected**: Flat schema provides better type safety and API clarity

### Alternative 2: Separate Endpoints per Entity Type

```
GET /api/v1/cost-elements/{id}/evm
GET /api/v1/wbes/{id}/evm
GET /api/v1/projects/{id}/evm
```

**Pros**:
- Explicit endpoints for each entity type
- Independent schema evolution per type

**Cons**:
- **Code duplication**: Same logic repeated for each endpoint
- **Frontend duplication**: Separate hooks/components for each type
- **Inconsistency risk**: Endpoints may diverge over time

**Rejected**: Generic pattern reduces duplication and ensures consistency

### Alternative 3: Simple Sum for All Metrics

**Decision**: Sum all metrics (including CPI/SPI) when aggregating

**Pros**:
- Simpler implementation
- Faster calculation

**Cons**:
- **Mathematically incorrect**: CPI = sum(EV) / sum(AC), not sum(CPI)
- **EVM non-compliance**: Violates ANSI/EIA-748 standard
- **Misleading results**: Small cost elements skew results

**Rejected**: Weighted average is mathematically correct and EVM-compliant

## Implementation Notes

### Backend Implementation

**Service Layer** (`backend/app/services/evm_service.py`):
- `calculate_evm_metrics()`: Single entity calculation (cost element)
- `calculate_evm_metrics_batch()`: Multi-entity aggregation
- `_aggregate_evm_metrics()`: Aggregation logic (sum + weighted avg)
- `_calculate_wbe_evm_metrics()`: WBE-specific aggregation
- `_calculate_project_evm_metrics()`: Project-specific aggregation

**API Routes** (`backend/app/api/routes/evm.py`):
- Generic routes use `EntityType` enum for polymorphism
- Route handler dispatches to appropriate service method based on entity type
- All routes respect time-travel (control_date, branch, branch_mode)

### Frontend Implementation

**Components** (`frontend/src/features/evm/components/`):
- All components accept `entityType: EntityType` prop
- Components use `useEVMMetrics` and `useEVMTimeSeries` hooks
- Hooks automatically select correct endpoint based on entity type

**Hooks** (`frontend/src/features/evm/api/hooks.ts`):
```typescript
export function useEVMMetrics(
  entityId: string,
  entityType: EntityType
) {
  return useQuery({
    queryKey: evmQueryKeys.metrics(entityType, entityId),
    queryFn: () => api.get(`/evm/${entityType}/${entityId}/metrics`),
  });
}
```

## Migration Notes

**Backward Compatibility**:
- Legacy endpoint `/api/v1/cost-elements/{id}/evm` still functional
- Existing `EVMMetricsRead` schema preserved for cost-element-specific use cases
- Frontend can migrate incrementally to generic endpoints

**Future Migration Path**:
1. Deprecate legacy cost-element endpoint (add warning header)
2. Update all frontend components to use generic endpoints
3. Remove legacy endpoints after 6-month deprecation period

## References

- [EVM Calculation Guide](../evm-calculation-guide.md) - EVM formulas and interpretation
- [ADR-005: Bitemporal Versioning](./ADR-005-bitemporal-versioning.md) - Time-travel semantics
- [ADR-006: Protocol-based Type System](./ADR-006-protocol-based-type-system.md) - Type safety patterns
- [ANSI/EIA-748 Standard](https://www.pmi.org/about/learn-about-pmi/what-is-project-management/earned-value-management) - EVM industry standard

## Review Date

2026-07-01 (reassess after 6 months of production use)
