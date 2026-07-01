# EVM API Guide

**Last Updated:** 2026-07-01
**Related Iteration:** [2026-01-22-evm-analyzer-master-detail-ui](../../03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/)

---

## Overview

The EVM (Earned Value Management) API provides generic endpoints for calculating and retrieving EVM metrics across a 4-tier entity hierarchy: **Project → WBS Element → Control Account → Work Package → Cost Element**.

The budget holder is the **Work Package** (PMI semantics): BAC/PV/AC/EV are computed at the Work Package level, and every higher tier (Control Account, WBS Element, Project) rolls its descendant Work Packages up via the batch endpoint. A `cost_element` query resolves the owning Work Package and returns that Work Package's metrics.

Entity types accepted by the API (`EntityType` enum):

| `entity_type`     | Tier          | Role |
|-------------------|---------------|------|
| `cost_element`    | Leaf (EOC)    | Resolves the owning Work Package and returns its metrics |
| `work_package`    | Budget holder | BAC/PV/AC/EV computed directly here |
| `control_account` | WBS × Org Unit| Aggregates its child Work Packages |
| `wbs_element`     | Intermediate  | Aggregates all descendant Work Packages (recursively expanded) |
| `project`         | Root          | Aggregates all Work Packages under its WBS tree |

> **Note:** the literal `wbe` does **not** exist — use `wbs_element`. Sending an unknown `entity_type` yields a `422`.

All endpoints support:

- **Time-travel queries** via `control_date` parameter
- **Branch isolation** via `branch` and `branch_mode` parameters
- **Multi-entity aggregation** via batch endpoint
- **Time-series data** for chart visualization
- **Portfolio rollup** via the dedicated `/portfolio` endpoint

---

## Base URL

```
/api/v1/evm
```

---

## Authentication

EVM endpoints require authentication. The single-entity, time-series, and batch endpoints require the `evm-read` permission. The portfolio endpoint additionally requires `portfolio-read`:

```http
Authorization: Bearer <jwt_token>
```

> **Batch + Project scoping (G2):** when `entity_type=project` is used with `/batch`, the request is **membership-scoped** — project IDs the caller cannot access (resolved via RBAC `get_accessible_projects`) are silently dropped before aggregation. Non-project entity types keep their current behavior (no portfolio-membership concept).

---

## Endpoints

### 0. Portfolio EVM (Cross-Project Rollup)

Get rolled-up EVM metrics across the caller's **accessible** projects, with a per-project breakdown and an at-risk subset.

**Endpoint:**

```http
GET /api/v1/evm/portfolio
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `control_date` | datetime | No | now | Control date for the time-travel EVM query (ISO 8601). Monetary values are converted to the base currency at this date. |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merged` | Branch mode: `isolated` or `merged` |

**Permission:** `portfolio-read` (not `evm-read`).

**Membership scoping:** resolves the caller's accessible project set via unified RBAC (`get_accessible_projects`, same pattern as `/projects`) before computing EVM. A non-member sees only their own projects. If the caller has **no** accessible projects, the endpoint returns `404`.

**Response:** `PortfolioEVMResponse`

```json
{
  "summary": {
    "entity_type": "project",
    "entity_id": "00000000-0000-0000-0000-000000000000",
    "bac": "12000000.00",
    "pv": "4500000.00",
    "ac": "5200000.00",
    "ev": "4100000.00",
    "cv": "-1100000.00",
    "sv": "-400000.00",
    "cpi": 0.79,
    "spi": 0.91,
    "eac": "15100000.00",
    "vac": "-3100000.00",
    "etc": "9900000.00",
    "tcpi": 0.79,
    "control_date": "2026-07-01T00:00:00Z",
    "branch": "main",
    "branch_mode": "merged",
    "progress_percentage": 34.2,
    "warning": null
  },
  "projects": [
    {
      "project_id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Line Automation - Plant B",
      "status": "active",
      "cpi": 0.79,
      "spi": 0.88,
      "vac": "-3100000.00",
      "contract_value": "15000000.00",
      "bac": "12000000.00",
      "eac": "15100000.00",
      "currency": "EUR",
      "organizational_unit_id": "ab1c...",
      "project_manager_id": "cd2e...",
      "customer_id": "ef3a...",
      "at_risk": true,
      "delta_eac": 250000.0,
      "start_date": "2026-02-01T00:00:00Z",
      "end_date": "2026-12-15T00:00:00Z"
    }
  ],
  "at_risk_projects": [],
  "control_date": "2026-07-01T00:00:00Z"
}
```

**Field semantics:**

- `summary`: rolled-up portfolio metrics via the industry-standard **"roll up, never average"** aggregation (CPI/SPI/TCPI re-derived from summed EV/AC/PV/BAC/EAC).
- `projects[]`: per-project breakdown. Each row carries the project's CPI/SPI/VAC/BAC/EAC plus `contract_value`, `delta_eac` (ΔEAC forecast drift), owning org unit / PM / customer, and dates.
- `at_risk_projects[]`: subset of `projects` where SPI is present and `< 0.9` (interim delayed/at-risk proxy).

**Currency / FX:** all monetary values are expressed in the project base currency (EUR). `convert_to_base` is applied per project at `control_date` before aggregation. Today every project is EUR, so conversion is a no-op pass-through; the path is wired for the multi-currency case.

**Performance:** resolves every accessible project's Work Packages in a constant number of queries (one recursive CTE per layer: WBS → descendants → Control Accounts → Work Packages), then computes EVM for the full Work Package set in a single batched pass — O(1) DB round-trips regardless of project count.

---

### 1. Get EVM Metrics

Get comprehensive EVM metrics for a single entity.

**Endpoint:**

```http
GET /api/v1/evm/{entity_type}/{entity_id}/metrics
```

**Path Parameters:**

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `entity_type` | string | Type of entity | `cost_element`, `work_package`, `control_account`, `wbs_element`, `project` |
| `entity_id` | UUID | Entity ID | Valid UUID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `control_date` | datetime | No | now | Control date for time-travel query (ISO 8601) |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merged` | Branch mode: `isolated` (only this branch) or `merged` (fall back to main/parent) |

**Response:** `EVMMetricsResponse`

```json
{
  "entity_type": "cost_element",
  "entity_id": "123e4567-e89b-12d3-a456-426614174000",
  "bac": "100000.00",
  "pv": "25000.00",
  "ac": "30000.00",
  "ev": "20000.00",
  "cv": "-10000.00",
  "sv": "-5000.00",
  "cpi": 0.67,
  "spi": 0.80,
  "eac": "150000.00",
  "vac": "-50000.00",
  "etc": "120000.00",
  "tcpi": 0.67,
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merged",
  "progress_percentage": 20.0,
  "warning": null
}
```

**Metrics Reference:**

| Metric | Type | Description | Formula |
|--------|------|-------------|---------|
| `bac` | Decimal | Budget at Completion | Total planned budget |
| `pv` | Decimal | Planned Value | Budgeted cost of work scheduled |
| `ac` | Decimal | Actual Cost | Cost incurred to date |
| `ev` | Decimal | Earned Value | Budgeted cost of work performed |
| `cv` | Decimal | Cost Variance | `ev - ac` (negative = over budget) |
| `sv` | Decimal | Schedule Variance | `ev - pv` (negative = behind) |
| `cpi` | Decimal | Cost Performance Index | `ev / ac` (< 1.0 = over budget) |
| `spi` | Decimal | Schedule Performance Index | `ev / pv` (< 1.0 = behind) |
| `eac` | Decimal | Estimate at Completion | From forecast |
| `vac` | Decimal | Variance at Completion | `bac - eac` |
| `etc` | Decimal | Estimate to Complete | `eac - ac` |
| `tcpi` | Decimal | To-Complete Performance Index | `bac / eac` (defaults to `1.0` when EAC is missing or zero) |
| `progress_percentage` | Decimal | Progress percentage | From latest progress entry |
| `warning` | string | Warning message | Null if no warning |

**Example Request:**

```bash
curl -X GET "http://localhost:8020/api/v1/evm/cost_element/123e4567-e89b-12d3-a456-426614174000/metrics?control_date=2026-01-15T00:00:00Z&branch=main" \
  -H "Authorization: Bearer ${TOKEN}"
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| `404` | Entity genuinely not found / unsupported type |
| `422` | Validation error (invalid UUID, `entity_type`) |

> **Pre-baseline / pre-version behavior (NOT a 404):** for `wbs_element` and `project`, if the entity exists in principle but has **no version valid as of `control_date`** (e.g. the project's `valid_time` starts after `control_date`), the endpoint returns `200` with an **empty, zeroed `EVMMetricsResponse`** and a `warning` such as `"No 'project' data available as of 2026-01-15"`. This is "no data yet", not an error. The `404` is reserved for genuinely-missing or unsupported types.

---

### 2. Get EVM Time-Series

Get historical EVM metrics as time-series data for charts.

**Endpoint:**

```http
GET /api/v1/evm/{entity_type}/{entity_id}/timeseries
```

**Path Parameters:**

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `entity_type` | string | Type of entity | `cost_element`, `work_package`, `control_account`, `wbs_element`, `project` |
| `entity_id` | UUID | Entity ID | Valid UUID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `granularity` | string | No | `week` | Time granularity: `day`, `week`, `month` |
| `control_date` | datetime | No | now | Control date for time-travel query (ISO 8601) |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merged` | Branch mode: `isolated` or `merged` |

**Response:** `EVMTimeSeriesResponse`

```json
{
  "granularity": "week",
  "points": [
    {
      "date": "2026-01-01T00:00:00Z",
      "pv": "5000.00",
      "ev": "4000.00",
      "ac": "6000.00",
      "forecast": "5000.00",
      "actual": "6000.00",
      "cpi": 0.67,
      "spi": 0.80
    },
    {
      "date": "2026-01-08T00:00:00Z",
      "pv": "10000.00",
      "ev": "8000.00",
      "ac": "12000.00",
      "forecast": "10000.00",
      "actual": "12000.00",
      "cpi": 0.67,
      "spi": 0.80
    }
  ],
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z",
  "total_points": 52
}
```

**Date Range Behavior:**

| Entity Type | Date Range |
|-------------|------------|
| **Cost Element / Work Package** | Linked ScheduleBaseline `start_date` → `end_date` |
| **Control Account / WBS Element** | Min → max of child Work Package baseline ranges |
| **Project** | `project.start_date` → `max(project.end_date, control_date)` |

**Granularity Options:**

| Granularity | Description | Use Case |
|-------------|-------------|----------|
| `day` | Daily data points | Short-term projects (< 3 months) |
| `week` | Weekly data points (default) | Balanced detail for most projects |
| `month` | Monthly data points | Long-term projects (> 1 year) |

**Period Boundaries:**

- **Daily**: 00:00:00 each day
- **Weekly**: Monday 00:00:00 (ISO 8601 week standard)
- **Monthly**: 1st 00:00:00 each month

**Example Request:**

```bash
curl -X GET "http://localhost:8020/api/v1/evm/cost_element/123e4567-e89b-12d3-a456-426614174000/timeseries?granularity=week&control_date=2026-01-15T00:00:00Z" \
  -H "Authorization: Bearer ${TOKEN}"
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| `404` | Entity not found |
| `422` | Validation error (invalid UUID, entity_type, granularity) |

---

### 3. Batch EVM Metrics

Get aggregated EVM metrics for multiple entities.

**Endpoint:**

```http
POST /api/v1/evm/batch
```

**Request Body:**

```json
{
  "entity_type": "wbs_element",
  "entity_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "223e4567-e89b-12d3-a456-426614174001",
    "323e4567-e89b-12d3-a456-426614174002"
  ],
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merged"
}
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity_type` | string | Yes | - | Type of entities (`cost_element`, `work_package`, `control_account`, `wbs_element`, `project`) |
| `entity_ids` | array[UUID] | Yes | - | List of entity IDs to aggregate |
| `control_date` | datetime | No | now | Control date for time-travel query |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merged` | Branch mode: `isolated` or `merged` |

**Response:** `EVMMetricsResponse` (aggregated)

```json
{
  "entity_type": "wbs_element",
  "entity_id": null,
  "bac": "300000.00",
  "pv": "75000.00",
  "ac": "90000.00",
  "ev": "60000.00",
  "cv": "-30000.00",
  "sv": "-15000.00",
  "cpi": 0.67,
  "spi": 0.80,
  "eac": "450000.00",
  "vac": "-150000.00",
  "etc": "360000.00",
  "tcpi": 0.67,
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merged",
  "progress_percentage": 20.0,
  "warning": null
}
```

**Aggregation Rules** (industry-standard **"roll up, never average"**):

| Metric Type | Aggregation Method | Formula |
| ----------- | ------------------ | ------- |
| **Amounts** (BAC, PV, AC, EV, EAC, VAC, ETC) | Sum | `sum(child.metric)` |
| **Variances** (CV, SV) | Re-derived from summed flows | `cv = ev - ac`, `sv = ev - pv` |
| **Indices** (CPI, SPI) | **Re-derived from summed EV/AC/PV** (never averaged) | `cpi = sum(ev) / sum(ac)`, `spi = sum(ev) / sum(pv)` |
| **TCPI** | Re-derived from summed BAC/EAC | `bac / eac` (defaults to `1.0` when EAC is missing/zero) |

> Indices are **re-derived from the rolled-up EV/AC/PV**, not averaged. Averaging CPI/SPI (even BAC-weighted) gives mathematically wrong portfolio indices; the code intentionally re-derives them so the rolled-up numbers are consistent with the summed flows.

**Special Cases:**

- **Empty entity_ids**: Returns zero metrics with warning
- **Single entity**: Returns identical metrics (no aggregation)
- **Null CPI/SPI**: When division by zero occurs (e.g., AC = 0, PV = 0)
- **`entity_type=project`**: request is membership-scoped — inaccessible project IDs are silently dropped before aggregation

**Example Request:**

```bash
curl -X POST "http://localhost:8020/api/v1/evm/batch" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "wbs_element",
    "entity_ids": ["123e4567-e89b-12d3-a456-426614174000", "223e4567-e89b-12d3-a456-426614174001"],
    "control_date": "2026-01-15T00:00:00Z"
  }'
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| `400` | Invalid request body (malformed JSON, invalid types) |
| `422` | Validation error (invalid entity_type, UUIDs) |

---

## Entity Type Behavior

EVM is computed at the **Work Package** (PMI budget holder) level and rolled up the hierarchy. The chain is:

```
Project → WBS Element → Control Account → Work Package → Cost Element
                                  ▲
                  BAC/PV/AC/EV computed here
```

### Cost Element (`cost_element`)

**Description:** Individual budget line items (leaf / EOC).

**Metrics Calculation:** the owning Work Package is resolved (`cost_element.work_package_id`) and **that Work Package's metrics are returned**. Cost Elements do not carry their own BAC/PV/AC/EV in the EVM model.

### Work Package (`work_package`)

**Description:** The PMI budget holder — where BAC/PV/AC/EV are actually computed.

**Metrics Calculation:**

- **BAC**: `work_package.budget_amount` (as of `control_date`)
- **PV**: `BAC × progress` from the linked `ScheduleBaseline` progression strategy (as of `control_date`)
- **AC**: Sum of `CostRegistration`s through the Work Package's Cost Elements (global facts — not branchable)
- **EV**: `BAC × progress_percentage / 100` from the latest `ProgressEntry` (as of `control_date`)
- **EAC**: `forecast.eac_amount` from the linked `Forecast` (as of `control_date`)
- **VAC / ETC / TCPI**: derived (`bac - eac`, `eac - ac`, `bac / eac`)

### Control Account (`control_account`)

**Description:** WBS × Organizational Unit intersection.

**Aggregation:** resolves its child Work Packages (`work_package.control_account_id`) and rolls them up via `aggregate_evm_metrics`.

### WBS Element (`wbs_element`)

**Description:** Intermediate WBS node.

**Aggregation:** recursively expands **all descendant WBS Elements**, resolves the Control Accounts under that expanded set, then the Work Packages under those Control Accounts, and rolls the Work Packages up. On a non-main branch with `branch_mode=merged`, descendant resolution prefers the branch's version over `main` (and drops `main` rows shadowed by a branch deletion) — see `_get_descendants_merged` in `wbs_element_service.py`.

**Date Range (Time-Series):** `min(child.baseline.start_date)` → `max(child.baseline.end_date)`.

### Project (`project`)

**Description:** Root node.

**Aggregation:** fetches the project's WBS Elements, then delegates to the WBS Element aggregation path (which expands descendants → Control Accounts → Work Packages). Identical rollup math.

**Date Range (Time-Series):** `project.start_date` → `max(project.end_date, control_date)`.

---

## Time-Travel Queries

All EVM endpoints support time-travel queries via the `control_date` parameter.

### How It Works

When you specify a `control_date`, the API fetches all entities **as they were at that point in time**:

- **Valid Time Travel**: Uses the entity's `valid_time` range (bitemporal versioning)
- **Branch Isolation**: Respects `branch` and `branch_mode` parameters
- **Global Facts**: Cost registrations and progress entries are not versioned (global facts)

### Example: Historical Analysis

```bash
# Get EVM metrics as of January 1, 2026
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-01T00:00:00Z

# Get EVM metrics as of December 31, 2025
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2025-12-31T23:59:59Z
```

### Example: Branch Comparison

```bash
# Get EVM for main branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=main

# Get EVM for change order branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=BR-001-feature-addition

# Get EVM for change order with isolated mode (no fallback to parent)
GET /api/v1/evm/cost_element/{id}/metrics?branch=BR-001&branch_mode=isolated
```

### Branch Modes

The `BranchMode` enum has two members (literal values lowercase):

| Mode | Literal | Description | Use Case |
|------|---------|-------------|----------|
| `MERGED` | `merged` | Fall back to the `main` branch if an entity is not present on the current branch | Default for all EVM routes; most common |
| `ISOLATED` | `isolated` | Only query the current branch, no `main` fallback | Isolated change-order analysis |

> The EVM route default is `MERGED`. On a non-main branch in `MERGED` mode, descendant/version resolution prefers the branch's row over `main` (and excludes `main` rows shadowed by a branch deletion) — see `_get_descendants_merged` / `_expand_wbs_descendants_batch` in the WBS / EVM services.

---

## Performance Considerations

### Query Performance

| Operation | Performance Budget | Typical Performance |
|-----------|-------------------|---------------------|
| **Single entity metrics** | <500ms | 50-200ms |
| **Time-series (1-year, weekly)** | <1s | 300-500ms |
| **Batch metrics (10 entities)** | <1s | 200-400ms |

### Optimization Strategies

1. **Batch Queries**: Use `/batch` endpoint for multiple entities instead of individual requests
2. **Granularity Selection**: Use appropriate granularity for date range (month for long ranges, day for short)
3. **Caching**: Frontend should cache responses for 5-10 minutes (TanStack Query)
4. **Database Indexes**: EVM query patterns are indexed for optimal performance

### Database Indexes

Key indexes that optimize EVM queries (defined on the domain models):

- `ix_cr_cost_element_id_current` / `ix_cr_cost_registration_id_current` — partial current-version indexes on `cost_registrations`, speed up AC lookups and time-series
- `ix_work_packages_current_version` — partial current-version index on `work_packages`, speeds up Work Package batch resolution
- `ix_wbs_elements_current_version` — partial current-version index on `wbs_elements`, speeds up WBS descendant expansion for Project/Control Account aggregation

---

## Error Handling

### Common Error Responses

**404 Not Found:**

```json
{
  "detail": "Cost element with id '123e4567-e89b-12d3-a456-426614174000' not found"
}
```

**422 Validation Error:**

```json
{
  "detail": [
    {
      "loc": ["path", "entity_id"],
      "msg": "Invalid UUID format",
      "type": "uuid_parsing"
    }
  ]
}
```

**400 Bad Request (Batch):**

```json
{
  "detail": "Invalid request body: Invalid entity_type: wbe"
}
```

### Warning Messages

The API may return warning messages in the `warning` field:

| Warning | Cause | Action |
|---------|-------|--------|
| `"No progress reported for this work package"` | No progress entries exist | Create a progress entry to enable EV calculation |
| `"No work packages found for WBS Elements"` | WBS Element has no descendant Work Packages | Add Work Packages under the WBS tree |
| `"No WBS Elements found for project"` | Project has no WBS Elements | Add WBS Elements to the project |
| `"No 'project' data available as of <date>"` | Project exists but no version is valid as of `control_date` (pre-baseline) | Use a later `control_date`, or backdate the project version |
| `"No 'wbe' data available as of <date>"` | WBS Element exists but no version is valid as of `control_date` | Use a later `control_date` |

---

## OpenAPI Documentation

Auto-generated OpenAPI documentation is available at:

```
http://localhost:8020/docs
```

The Swagger UI includes:

- Interactive API testing
- Request/response schemas
- Authentication examples
- Parameter descriptions

---

## References

- [ADR-011: Generic EVM Metric System](./decisions/ADR-011-generic-evm-metric-system.md) - Architecture decisions
- [ADR-012: EVM Time-Series Data Strategy](./decisions/ADR-012-evm-time-series-data-strategy.md) - Time-series architecture
- [EVM Calculation Guide](./evm-calculation-guide.md) - EVM formulas and interpretation
- [ADR-005: Bitemporal Versioning](./decisions/ADR-005-bitemporal-versioning.md) - Time-travel semantics

---

## Changelog

### 2026-01-22

- Added generic EVM API endpoints (`/api/v1/evm/{entity_type}/{entity_id}/metrics`)
- Added time-series endpoint (`/api/v1/evm/{entity_type}/{entity_id}/timeseries`)
- Added batch endpoint (`POST /api/v1/evm/batch`)
- Added WBE and Project entity type support
- Added time-travel query support
- Added performance optimization (batch queries, database indexes)

### 2026-07-01

- **Corrected `entity_type` enum** (was the biggest source of `422`s): `wbe` removed; `wbs_element`, `control_account`, `work_package` added. Full set is now `cost_element`, `work_package`, `control_account`, `wbs_element`, `project`.
- **Documented the 4-tier aggregation chain** (Project → WBS Element → Control Account → Work Package → Cost Element) with Work Package as the PMI budget holder where BAC/PV/AC/EV are computed.
- **Fixed the batch aggregation rule**: indices (CPI/SPI/TCPI) are **re-derived from summed EV/AC/PV/BAC/EAC** (industry-standard "roll up, never average"), not BAC-weighted averages.
- **Added `tcpi`** (`bac / eac`, defaults to `1.0` when EAC is missing/zero) to the metrics table and all response examples.
- **Added the `GET /api/v1/evm/portfolio` endpoint** (cross-project rollup, `portfolio-read`, FX conversion, at-risk subset, O(1) batched resolution).
- **Corrected pre-baseline behavior**: a missing-as-of-`control_date` version for `wbs_element`/`project` now returns `200` with empty zeroed metrics + warning (not `404`); `404` is reserved for genuinely-missing/unsupported types.
- **Aligned `branch_mode` literals** with the `BranchMode` enum: `merged`/`isolated` (the old `merge`/`strict` were wrong). EVM route default is `MERGED`.
- **RBAC notes**: `portfolio-read` for `/portfolio`; `/batch` with `entity_type=project` is membership-scoped (inaccessible project IDs silently dropped).
