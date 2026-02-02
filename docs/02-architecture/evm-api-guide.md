# EVM API Guide

**Last Updated:** 2026-01-22
**Related Iteration:** [2026-01-22-evm-analyzer-master-detail-ui](../../03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/)

---

## Overview

The EVM (Earned Value Management) API provides generic endpoints for calculating and retrieving EVM metrics across multiple entity types: **Cost Elements**, **WBEs** (Work Breakdown Elements), and **Projects**.

All endpoints support:
- **Time-travel queries** via `control_date` parameter
- **Branch isolation** via `branch` and `branch_mode` parameters
- **Multi-entity aggregation** via batch endpoint
- **Time-series data** for chart visualization

---

## Base URL

```
/api/v1/evm
```

---

## Authentication

All EVM endpoints require authentication with the `evm-read` permission:

```http
Authorization: Bearer <jwt_token>
```

---

## Endpoints

### 1. Get EVM Metrics

Get comprehensive EVM metrics for a single entity.

**Endpoint:**
```http
GET /api/v1/evm/{entity_type}/{entity_id}/metrics
```

**Path Parameters:**

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `entity_type` | string | Type of entity | `cost_element`, `wbe`, `project` |
| `entity_id` | UUID | Entity ID | Valid UUID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `control_date` | datetime | No | now | Control date for time-travel query (ISO 8601) |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merge` | Branch mode: `strict` (only this branch) or `merge` (fall back to parent) |

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
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merge",
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
| `404` | Entity not found |
| `422` | Validation error (invalid UUID, entity_type) |

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
| `entity_type` | string | Type of entity | `cost_element`, `wbe`, `project` |
| `entity_id` | UUID | Entity ID | Valid UUID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `granularity` | string | No | `week` | Time granularity: `day`, `week`, `month` |
| `control_date` | datetime | No | now | Control date for time-travel query (ISO 8601) |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merge` | Branch mode: `strict` or `merge` |

**Response:** `EVMTimeSeriesResponse`

```json
{
  "entity_type": "cost_element",
  "entity_id": "123e4567-e89b-12d3-a456-426614174000",
  "granularity": "week",
  "points": [
    {
      "date": "2026-01-01T00:00:00Z",
      "bac": "100000.00",
      "pv": "5000.00",
      "ac": "6000.00",
      "ev": "4000.00",
      "cv": "-2000.00",
      "sv": "-1000.00",
      "cpi": 0.67,
      "spi": 0.80,
      "eac": null,
      "vac": null,
      "etc": null
    },
    {
      "date": "2026-01-08T00:00:00Z",
      "bac": "100000.00",
      "pv": "10000.00",
      "ac": "12000.00",
      "ev": "8000.00",
      "cv": "-4000.00",
      "sv": "-2000.00",
      "cpi": 0.67,
      "spi": 0.80,
      "eac": null,
      "vac": null,
      "etc": null
    }
  ],
  "total_points": 52
}
```

**Date Range Behavior:**

| Entity Type | Date Range |
|-------------|------------|
| **Cost Element** | Schedule baseline start_date to end_date |
| **WBE** | Earliest child cost element start to latest end |
| **Project** | Project start_date to max(target_end_date, control_date) |

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
  "entity_type": "cost_element",
  "entity_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "223e4567-e89b-12d3-a456-426614174001",
    "323e4567-e89b-12d3-a456-426614174002"
  ],
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merge"
}
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity_type` | string | Yes | - | Type of entities (`cost_element`, `wbe`, `project`) |
| `entity_ids` | array[UUID] | Yes | - | List of entity IDs to aggregate |
| `control_date` | datetime | No | now | Control date for time-travel query |
| `branch` | string | No | `main` | Branch name to query |
| `branch_mode` | string | No | `merge` | Branch mode: `strict` or `merge` |

**Response:** `EVMMetricsResponse` (aggregated)

```json
{
  "entity_type": "cost_element",
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
  "control_date": "2026-01-15T00:00:00Z",
  "branch": "main",
  "branch_mode": "merge",
  "progress_percentage": 20.0,
  "warning": null
}
```

**Aggregation Rules:**

| Metric Type | Aggregation Method | Formula |
| ----------- | ------------------ | ------- |
| **Amounts** (BAC, PV, AC, EV, CV, SV, EAC, VAC, ETC) | Sum | `sum(child.metric)` |
| **Indices** (CPI, SPI) | Weighted Average by BAC | `sum(child.metric × child.BAC) / sum(child.BAC)` |

**Special Cases:**

- **Empty entity_ids**: Returns zero metrics with warning
- **Single entity**: Returns identical metrics (no aggregation)
- **Null CPI/SPI**: When division by zero occurs (e.g., AC = 0, PV = 0)

**Example Request:**

```bash
curl -X POST "http://localhost:8020/api/v1/evm/batch" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "cost_element",
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

### Cost Element (`cost_element`)

**Description:** Individual budget line items (leaf level)

**Metrics Calculation:**
- **BAC**: From `cost_element.budget_amount`
- **PV**: From schedule baseline progression strategy
- **AC**: Sum of cost registrations for this cost element
- **EV**: BAC × progress_percentage / 100
- **EAC, VAC, ETC**: From latest forecast

**Aggregation:**
- Single entity (no child aggregation)

### WBE (`wbe`)

**Description:** Work Breakdown Elements (groups of cost elements)

**Metrics Calculation:**
- Aggregates from all child cost elements
- Uses hierarchical aggregation (sum + weighted avg)

**Aggregation:**
- Fetches all cost elements where `cost_element.wbe_id = wbe.id`
- Calculates metrics for each child cost element
- Aggregates using sum for amounts, weighted avg for indices

**Date Range (Time-Series):**
- Start: `min(child.baseline.start_date)`
- End: `max(child.baseline.end_date)`

### Project (`project`)

**Description:** Projects (groups of WBEs)

**Metrics Calculation:**
- Aggregates from all child WBEs
- Uses hierarchical aggregation (sum + weighted avg)

**Aggregation:**
- Fetches all WBEs where `wbe.project_id = project.id`
- Calculates WBE metrics (which aggregate from cost elements)
- Aggregates WBE metrics using sum for amounts, weighted avg for indices

**Date Range (Time-Series):**
- Start: `project.start_date`
- End: `max(project.target_end_date, control_date)`

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
GET /api/v1/evm/cost_element/{id}/metrics?branch=co-001-feature-addition

# Get EVM for change order with strict mode (no fallback to parent)
GET /api/v1/evm/cost_element/{id}/metrics?branch=co-001&branch_mode=strict
```

### Branch Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `merge` | Fall back to parent branches if entity not in current branch | Default, most common |
| `strict` | Only query current branch, no fallback | Isolated change order analysis |

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

The following indexes optimize EVM queries:

- `ix_cost_registrations_cost_element_date` - Speeds up AC time-series
- `ix_progress_entries_cost_element_reported_date` - Speeds up EV time-series
- `ix_wbes_project_id` - Speeds up WBE aggregation for projects

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
  "detail": "Invalid request body: entity_type must be one of: cost_element, wbe, project"
}
```

### Warning Messages

The API may return warning messages in the `warning` field:

| Warning | Cause | Action |
|---------|-------|--------|
| `"No progress reported for this cost element"` | No progress entries exist | Create progress entry to enable EV calculation |
| `"WBE has no child cost elements"` | WBE has no children | Add cost elements to WBE |
| `"Project has no child WBEs"` | Project has no WBEs | Add WBEs to project |

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
