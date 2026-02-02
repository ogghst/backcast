# EVM Time-Travel Semantics

**Last Updated:** 2026-01-22
**Related Iteration:** [2026-01-22-evm-analyzer-master-detail-ui](../../03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/)

---

## Overview

The EVM system supports **Valid Time Travel** queries, allowing you to retrieve EVM metrics as they were at any point in the past. This is enabled by the bitemporal versioning system, which tracks both **valid time** (business time) and **transaction time** (system time) for all versioned entities.

---

## Bitemporal Versioning Basics

### Two Time Dimensions

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Valid Time** | When the fact was true in the real world | Budget effective from Jan 1 to Dec 31, 2026 |
| **Transaction Time** | When the fact was recorded in the system | Budget created on Dec 15, 2025 |

### Key Concepts

**Versioned Entities:**
- Cost Elements, WBEs, Projects, Schedule Baselines
- Have `valid_time` (TSTZRANGE) and `transaction_time` (TSTZRANGE)
- Support time-travel queries via `get_as_of(id, control_date)` methods

**Non-Versioned Entities (Global Facts):**
- Cost Registrations, Progress Entries, Forecasts
- No `valid_time` (not versioned)
- Always fetched as of current time (global facts)

---

## Valid Time Travel Semantics

### How It Works

When you specify a `control_date` in an EVM query:

1. **Versioned entities** are fetched as they were at `control_date` (Valid Time Travel)
2. **Global facts** are fetched as of current time (not time-traveled)
3. EVM metrics are calculated from the combination of both

### Example Scenario

```
Timeline:
- Dec 1, 2025: Cost element created with BAC = €100,000
- Jan 1, 2026: Cost registrations begin
- Jan 15, 2026: Progress updated to 50%
- Feb 1, 2026: Budget increased to €120,000
```

**Query at control_date = Jan 15, 2026:**

```json
{
  "bac": "100000.00",  // BAC as of Jan 15 (before increase)
  "ac": "30000.00",    // AC as of NOW (global fact, not time-traveled)
  "ev": "50000.00",    // EV = BAC × 50% (using progress from Jan 15)
  "control_date": "2026-01-15T00:00:00Z"
}
```

**Query at control_date = Feb 15, 2026:**

```json
{
  "bac": "120000.00",  // BAC as of Feb 15 (after increase)
  "ac": "30000.00",    // AC as of NOW (same global fact)
  "ev": "60000.00",    // EV = BAC × 50% (using progress from Feb 15)
  "control_date": "2026-02-15T00:00:00Z"
}
```

---

## EVM Query Parameters

### control_date

**Description:** Control date for Valid Time Travel query (ISO 8601 format)

**Default:** Current datetime (`datetime.now(tz=UTC)`)

**Behavior:**

- **Versioned entities**: Fetched as they were at `control_date`
- **Global facts**: Fetched as of current time (not affected by `control_date`)

**Example:**

```bash
# Get EVM metrics as of January 1, 2026
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-01T00:00:00Z

# Get EVM metrics as of current time (default)
GET /api/v1/evm/cost_element/{id}/metrics
```

### branch

**Description:** Branch name to query

**Default:** `"main"`

**Behavior:**

- Fetches entities from the specified branch
- Cost registrations and progress entries are **global facts** (not branched)

**Example:**

```bash
# Get EVM for main branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=main

# Get EVM for change order branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=co-001-feature-addition
```

### branch_mode

**Description:** Branch isolation mode

**Values:**
- `"merge"` (default): Fall back to parent branches if entity not in current branch
- `"strict"` or `"isolated"`: Only query current branch, no fallback

**Behavior:**

| Mode | Entity Found in Branch | Entity Not Found in Branch |
|------|------------------------|----------------------------|
| `merge` | Return entity | Search parent branches |
| `strict` | Return entity | Return 404 Not Found |

**Example:**

```bash
# Merge mode: Fall back to parent if not in branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=co-001&branch_mode=merge

# Strict mode: Only current branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=co-001&branch_mode=strict
```

---

## Use Cases

### 1. Historical Analysis

Query EVM metrics at past dates to see project performance at that point:

```bash
# Get EVM metrics month-over-month
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-01T00:00:00Z
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-02-01T00:00:00Z
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-03-01T00:00:00Z
```

**Use Cases:**
- Audit historical project performance
- Compare current vs. past performance
- Generate trend reports
- Identify performance degradation points

### 2. Branch Comparison

Compare EVM metrics across change order branches:

```bash
# Baseline budget (main branch)
GET /api/v1/evm/cost_element/{id}/metrics?branch=main

# Change order budget (co-001 branch)
GET /api/v1/evm/cost_element/{id}/metrics?branch=co-001-feature-addition
```

**Use Cases:**
- Compare baseline budget vs. change order budget
- Analyze cost impact of proposed changes
- Validate change order justifications
- "What-if" scenario analysis

### 3. Time-Series Analysis

Generate time-series charts with historical EVM data:

```bash
# Get weekly time-series for 2026
GET /api/v1/evm/cost_element/{id}/timeseries?granularity=week&control_date=2026-12-31T23:59:59Z
```

**Use Cases:**
- Visualize EVM trends over time
- Identify performance patterns
- Forecast completion based on historical data
- Generate S-curves for stakeholder reports

---

## Frontend Integration

### TimeMachineContext

The `TimeMachineContext` provides time-travel settings to all EVM components:

```tsx
interface TimeMachineState {
  asOf: Date;          // Control date
  branch: string;       // Branch name
  mode: BranchMode;     // Branch mode (ISOLATED or MERGE)
  isHistorical: boolean; // Whether asOf is in the past
}
```

**Usage Example:**

```tsx
import { TimeMachineProvider } from '@/contexts/TimeMachineContext';
import { EVMSummaryView } from '@/features/evm/components';

function App() {
  const [timeMachine, setTimeMachine] = useState({
    asOf: new Date('2026-01-15'),
    branch: 'main',
    mode: BranchMode.MERGE,
  });

  return (
    <TimeMachineProvider state={timeMachine} setState={setTimeMachine}>
      <CostElementPage costElementId="..." />
    </TimeMachineProvider>
  );
}

function CostElementPage({ costElementId }: Props) {
  // useEVMMetrics automatically uses TimeMachineContext
  const { data: evmMetrics } = useEVMMetrics(
    costElementId,
    EntityType.COST_ELEMENT
  );

  return <EVMSummaryView evmMetrics={evmMetrics} />;
}
```

### Automatic Query Parameters

All EVM hooks automatically inject TimeMachineContext parameters:

```typescript
// useEVMMetrics hook implementation
export function useEVMMetrics(
  entityId: string,
  entityType: EntityType
) {
  const { asOf, branch, mode } = useTimeMachineParams();

  return useQuery({
    queryKey: evmQueryKeys.metrics(entityType, entityId, asOf, branch, mode),
    queryFn: () => api.get(`/evm/${entityType}/${entityId}/metrics`, {
      params: {
        control_date: asOf.toISOString(),
        branch,
        branch_mode: mode.toLowerCase(),
      },
    }),
  });
}
```

### Cache Invalidation

When TimeMachineContext changes, all EVM queries are automatically invalidated:

```tsx
// User changes control date
setTimeMachine({ ...state, asOf: new Date('2026-02-01') });

// All EVM queries automatically refetch:
// - useEVMMetrics()
// - useEVMTimeSeries()
// - useEVMMetricsBatch()
```

---

## Backend Implementation

### Service Layer

All EVM service methods accept time-travel parameters:

```python
async def calculate_evm_metrics(
    self,
    cost_element_id: UUID,
    control_date: datetime,
    branch: str,
    branch_mode: BranchMode,
) -> EVMMetricsRead:
    # Fetch versioned entities with time-travel
    cost_element = await ce_service.get_as_of(
        cost_element_id,
        as_of=control_date,
        branch=branch,
        branch_mode=branch_mode,
    )

    schedule_baseline = await sb_service.get_by_cost_element_as_of(
        cost_element_id,
        as_of=control_date,
        branch=branch,
        branch_mode=branch_mode,
    )

    # Fetch global facts (no time-travel)
    cost_registrations = await cr_service.get_by_cost_element(
        cost_element_id,
    )

    progress_entry = await pe_service.get_latest_by_cost_element(
        cost_element_id,
    )

    # Calculate EVM metrics
    ...
```

### Repository Layer

Repository `get_as_of()` methods implement Valid Time Travel:

```python
async def get_as_of(
    self,
    entity_id: UUID,
    as_of: datetime,
    branch: str,
    branch_mode: BranchMode,
) -> CostElement | None:
    """Get entity as it was at as_of date (Valid Time Travel)."""
    stmt = (
        select(CostElement)
        .where(
            CostElement.id == entity_id,
            CostElement.branch == branch,
            CostElement.valid_time.contains(as_of),  # Valid Time Travel
            CostElement.transaction_time.contains(as_of),  # Transaction Time Travel
            CostElement.deleted_at.is_(None),
        )
    )

    if branch_mode == BranchMode.MERGE:
        # Add parent branch fallback logic
        ...

    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

---

## Edge Cases and Considerations

### 1. Future Control Dates

If `control_date` is in the future:

- Versioned entities: Fetched as of future date (may not exist yet)
- Global facts: Fetched as of current time (actual data)
- **Result**: EVM metrics may use "future" BAC with "current" AC/EV

**Recommendation**: Use `min(control_date, now())` for realistic queries

### 2. Pre-Creation Control Dates

If `control_date` is before entity creation:

- Versioned entities: Return `None` (entity didn't exist)
- **Result**: 404 Not Found response

**Recommendation**: Validate `control_date` is within entity's lifetime

### 3. Global Facts with Time-Travel

Cost registrations and progress entries are **not versioned**:

- Always fetched as of current time
- Not affected by `control_date` parameter
- **Rationale**: These are "global facts" that cannot be time-traveled

**Example**:
```
- Jan 1, 2026: Cost element created (BAC = €100,000)
- Feb 1, 2026: Cost registration of €10,000
- Mar 1, 2026: Budget increased to €120,000

Query with control_date = Jan 15, 2026:
- BAC = €100,000 (as of Jan 15, before increase)
- AC = €10,000 (current cost registration, NOT time-traveled)
```

### 4. Branch Isolation

Change order branches can modify versioned entities but not global facts:

- **Versioned in branch**: Cost element, schedule baseline
- **Global facts**: Cost registrations, progress entries (same across branches)

**Example**:
```
Main branch: BAC = €100,000
co-001 branch: BAC = €120,000 (change order)

Cost registrations are SHARED across branches:
- AC is the same in both branches
- EV is the same in both branches (uses shared progress)
```

---

## Performance Considerations

### Query Performance

Time-travel queries use PostgreSQL `TSTZRANGE` contains operator:

```sql
WHERE valid_time @> :control_date
  AND transaction_time @> :control_date
```

**Performance**: <50ms for single entity queries (with indexes)

### Indexes

The following indexes optimize time-travel queries:

- `ix_cost_elements_valid_time` - Speeds up Valid Time Travel
- `ix_cost_elements_transaction_time` - Speeds up Transaction Time Travel
- `ix_schedule_baselines_valid_time` - Speeds up baseline time-travel

### Caching

Frontend TanStack Query cache includes time-travel parameters:

```typescript
queryKey: [
  'evm',
  'metrics',
  entityType,
  entityId,
  asOf,      // Cache key includes control date
  branch,    // Cache key includes branch
  mode,      // Cache key includes branch mode
]
```

**Result**: Different time-travel settings = different cache entries

---

## Best Practices

### 1. Validate Control Dates

Always validate `control_date` is reasonable:

```typescript
const controlDate = new Date(userInput);

// Ensure date is not too far in the past
if (controlDate < new Date('2020-01-01')) {
  throw new Error('Control date must be after 2020-01-01');
}

// Ensure date is not too far in the future
if (controlDate > new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)) {
  throw new Error('Control date cannot be more than 1 year in the future');
}
```

### 2. Use ISO 8601 Format

Always use ISO 8601 format for `control_date`:

```bash
# ✅ GOOD: ISO 8601 format
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-15T00:00:00Z

# ❌ BAD: Non-standard format
GET /api/v1/evm/cost_element/{id}/metrics?control_date=01/15/2026
```

### 3. Document Time-Travel Queries

When generating reports, document the time-travel settings:

```tsx
function EVMReport({ evmMetrics }: { evmMetrics: EVMMetricsResponse }) {
  return (
    <div>
      <h3>EVM Analysis Report</h3>
      <p>
        Generated on: {new Date().toLocaleString()}
        <br />
        Control date: {new Date(evmMetrics.control_date).toLocaleString()}
        <br />
        Branch: {evmMetrics.branch} ({evmMetrics.branch_mode})
      </p>
      {/* ... metrics ... */}
    </div>
  );
}
```

### 4. Handle Missing Entities Gracefully

Always handle 404 responses for invalid time-travel queries:

```tsx
const { data, error, isLoading } = useEVMMetrics(entityId, entityType);

if (isLoading) return <Spin />;
if (error) {
  if (error.response?.status === 404) {
    return <Empty description="Entity did not exist at control date" />;
  }
  return <Alert message={error.message} type="error" />;
}
if (!data) return <Empty />;
```

---

## References

- [ADR-005: Bitemporal Versioning](./decisions/ADR-005-bitemporal-versioning.md) - Detailed bitemporal architecture
- [EVM API Guide](./evm-api-guide.md) - API endpoint documentation
- [EVCS Core Architecture](./backend/contexts/evcs-core/architecture.md) - Versioning system implementation
- [TimeMachineContext](../../frontend/src/contexts/TimeMachineContext.tsx) - Frontend time-travel integration

---

## Changelog

### 2026-01-22
- Documented Valid Time Travel semantics for EVM queries
- Documented branch isolation modes (merge vs. strict)
- Documented frontend integration with TimeMachineContext
- Documented edge cases and best practices
