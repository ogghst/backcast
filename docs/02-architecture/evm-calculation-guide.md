# EVM Calculation Guide

**Last Updated:** 2026-03-02
**Related Iteration:** [2026-01-18-evm-foundation](../../03-project-plan/iterations/2026-01-18-evm-foundation/)

---

## Overview

This guide explains **how EVM is implemented** in Backcast , including data sources, calculation flow, API usage, and time-travel capabilities.

> **For EVM formulas and definitions**, see the authoritative source: [EVM Requirements](../../01-product-scope/evm-requirements.md)
>
> **For EVM API endpoints**, see: [EVM API Guide](./evm-api-guide.md)

---

## Implementation in Backcast 

### Data Sources

Each EVM metric is calculated from specific domain entities:

```python
# BAC: From CostElement.budget_amount
bac = cost_element.budget_amount

# PV: From ScheduleBaseline + ProgressionStrategy
pv = bac × (progress_percentage from baseline progression)

# AC: From CostRegistration (sum of amounts)
ac = sum(cost_registration.amount for cost_element)

# EV: From ProgressEntry.progress_percentage
ev = bac × progress_percentage / 100
```

### Calculation Flow

```text
┌─────────────────┐
│ CostElement     │ ──► BAC (Budget at Completion)
│ - budget_amount │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ ScheduleBaseline│ ──► PV (Planned Value)
│ - progression   │      via ProgressionStrategy
│ - start_date    │      PV = BAC × Progress
│ - end_date      │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ ProgressEntry   │ ──► EV (Earned Value)
│ - percentage    │      EV = BAC × Percentage / 100
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ CostRegistration│ ──► AC (Actual Cost)
│ - amount        │      AC = Σ(amount)
└─────────────────┘
```

---

## API Usage

### Get EVM Metrics

**Endpoint:** `GET /api/v1/cost-elements/{cost_element_id}/evm`

**Query Parameters:**

- `control_date` (optional): Control date for time-travel query (ISO 8601)
- `branch` (optional): Branch name (default: "main")

**Request Example:**

```bash
curl -X GET "http://localhost:8020/api/v1/cost-elements/{cost_element_id}/evm?control_date=2026-01-15T00:00:00Z&branch=main" \
  -H "Authorization: Bearer {token}"
```

**Response Example:**

```json
{
  "bac": "100000.00",
  "pv": "25000.00",
  "ac": "30000.00",
  "ev": "20000.00",
  "cv": "-10000.00",
  "sv": "-5000.00",
  "cpi": 0.67,
  "spi": 0.80,
  "cost_element_id": "123e4567-e89b-12d3-a456-426614174000",
  "control_date": "2026-01-15T00:00:00Z",
  "progress_percentage": 20.0,
  "warning": null
}
```

**Interpretation:**

- Budget at Completion: $100,000
- Planned Value: $25,000 (work scheduled to be complete)
- Actual Cost: $30,000 (money spent to date)
- Earned Value: $20,000 (value of work actually completed)
- **Over budget by $10,000** (CV = -10000)
- **Behind schedule by $5,000** (SV = -5000)
- **Cost efficiency: 67%** (CPI = 0.67, spending $1.00 for every $0.67 of value)
- **Schedule efficiency: 80%** (SPI = 0.80, completing work at 80% of planned rate)

---

## Time-Travel Queries

Backcast  supports time-travel queries for all EVM metrics, enabling historical analysis and "what-if" scenarios.

### Historical EVM Analysis

Query EVM metrics as of a past date to see project performance at that point:

```bash
# Get EVM metrics as of January 15, 2026
GET /api/v1/cost-elements/{id}/evm?control_date=2026-01-15T00:00:00Z

# Get EVM metrics as of December 31, 2025
GET /api/v1/cost-elements/{id}/evm?control_date=2025-12-31T23:59:59Z
```

**Use Cases:**

- Audit historical project performance
- Compare current vs. past performance
- Generate trend reports
- Identify performance degradation points

### Branch Comparison

Compare EVM metrics across change order branches:

```bash
# Get EVM for main branch
GET /api/v1/cost-elements/{id}/evm?branch=main

# Get EVM for change order branch
GET /api/v1/cost-elements/{id}/evm?branch=BR-001-feature-addition
```

**Use Cases:**

- Compare baseline budget vs. change order budget
- Analyze cost impact of proposed changes
- Validate change order justifications

---

## Progress Tracking

### Create Progress Entry

**Endpoint:** `POST /api/v1/progress-entries`

**Request Body:**

```json
{
  "cost_element_id": "123e4567-e89b-12d3-a456-426614174000",
  "progress_percentage": 50.0,
  "reported_date": "2026-01-15T10:00:00Z",
  "reported_by_user_id": "user-uuid",
  "notes": "Foundation completed, framing started"
}
```

**Validation Rules:**

- `progress_percentage` must be between 0.00 and 100.00
- `cost_element_id` must reference an existing cost element
- `reported_by_user_id` must reference an existing user

### Progress Decrease Handling

Progress can be decreased (e.g., work undone), but requires justification in the `notes` field:

```json
{
  "cost_element_id": "123e4567-e89b-12d3-a456-426614174000",
  "progress_percentage": 40.0,
  "reported_date": "2026-01-20T10:00:00Z",
  "reported_by_user_id": "user-uuid",
  "notes": "Re-do required: inspection failed, framing must be corrected"
}
```

**Best Practices:**

- Always provide notes when decreasing progress
- Document the reason for the decrease
- Reference change orders or inspection reports if applicable

### Get Latest Progress

**Endpoint:** `GET /api/v1/progress-entries/cost-element/{cost_element_id}/latest`

**Response:**

```json
{
  "id": "uuid",
  "progress_entry_id": "uuid",
  "cost_element_id": "uuid",
  "progress_percentage": 50.0,
  "reported_date": "2026-01-15T10:00:00Z",
  "reported_by_user_id": "uuid",
  "notes": "Foundation completed, framing started",
  "created_by": "uuid"
}
```

### Get Progress History

**Endpoint:** `GET /api/v1/progress-entries/cost-element/{cost_element_id}/history`

**Query Parameters:**

- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)

**Use Case:** Generate progress trend charts

---

## Cost Aggregation

### Get Aggregated Costs

**Endpoint:** `GET /api/v1/cost-registrations/aggregated`

**Query Parameters:**

- `cost_element_id`: Cost Element ID to aggregate
- `period`: Aggregation period (`daily`, `weekly`, `monthly`)
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601, optional)
- `as_of`: Time-travel date (ISO 8601, optional)

**Request Example:**

```bash
# Get weekly costs for January 2026
GET /api/v1/cost-registrations/aggregated?cost_element_id={id}&period=weekly&start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T23:59:59Z
```

**Response Example:**

```json
[
  {
    "period_start": "2026-01-01T00:00:00Z",
    "total_amount": 15000.00
  },
  {
    "period_start": "2026-01-08T00:00:00Z",
    "total_amount": 22000.00
  },
  {
    "period_start": "2026-01-15T00:00:00Z",
    "total_amount": 18000.00
  },
  {
    "period_start": "2026-01-22T00:00:00Z",
    "total_amount": 25000.00
  },
  {
    "period_start": "2026-01-29T00:00:00Z",
    "total_amount": 20000.00
  }
]
```

**Period Boundaries:**

- **Daily**: 00:00:00 to 23:59:59 each day
- **Weekly**: Monday 00:00:00 to Sunday 23:59:59 (ISO week standard)
- **Monthly**: 1st 00:00:00 to last day 23:59:59

### Get Cumulative Costs

**Endpoint:** `GET /api/v1/cost-registrations/cumulative`

**Query Parameters:**

- `cost_element_id`: Cost Element ID
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601, optional)
- `as_of`: Time-travel date (ISO 8601, optional)

**Response Example:**

```json
[
  {
    "registration_date": "2026-01-05T10:00:00Z",
    "amount": 5000.00,
    "cumulative_amount": 5000.00
  },
  {
    "registration_date": "2026-01-10T14:30:00Z",
    "amount": 8000.00,
    "cumulative_amount": 13000.00
  },
  {
    "registration_date": "2026-01-15T09:00:00Z",
    "amount": 7000.00,
    "cumulative_amount": 20000.00
  }
]
```

**Use Case:** Generate S-curve charts for cumulative cost tracking

---

## Edge Cases and Warnings

### No Progress Reported

If no progress entry exists for a cost element, the EVM API returns:

```json
{
  "bac": "100000.00",
  "pv": "25000.00",
  "ac": "30000.00",
  "ev": "0.00",
  "cv": "-30000.00",
  "sv": "-25000.00",
  "cpi": 0.0,
  "spi": 0.0,
  "cost_element_id": "uuid",
  "control_date": "2026-01-15T00:00:00Z",
  "progress_percentage": null,
  "warning": "No progress reported for this cost element"
}
```

**Impact:**

- EV = 0 (no earned value)
- CV = -AC (all actual cost is variance)
- CPI = 0 (zero cost efficiency)

**Recommendation:** Create a progress entry to enable accurate EVM calculations.

### Division by Zero

When calculating CPI and SPI, the system handles division by zero:

- **CPI = None** if AC = 0 (no costs incurred yet)
- **SPI = None** if PV = 0 (no planned value yet)

This prevents math errors and indicates insufficient data for the metric.

### No Schedule Baseline

If no schedule baseline exists for the cost element:

- PV = 0 (no planned value)
- SPI = None (cannot calculate schedule performance)

**Recommendation:** Create a schedule baseline to enable PV and SPI calculations.

---

## Best Practices

### 1. Regular Progress Updates

Update progress entries regularly (e.g., weekly) to ensure accurate EVM metrics:

```bash
# Weekly progress update
POST /api/v1/progress-entries
{
  "cost_element_id": "...",
  "progress_percentage": 25.0,
  "reported_date": "2026-01-15T10:00:00Z",
  "notes": "Weekly update: framing 25% complete"
}
```

### 2. Time-Travel for Audits

Use time-travel queries for retrospective analysis:

```bash
# Compare EVM metrics month-over-month
GET /api/v1/cost-elements/{id}/evm?control_date=2026-01-01T00:00:00Z
GET /api/v1/cost-elements/{id}/evm?control_date=2026-02-01T00:00:00Z
GET /api/v1/cost-elements/{id}/evm?control_date=2026-03-01T00:00:00Z
```

### 3. Branch Comparisons

Compare EVM metrics across change order branches:

```bash
# Main branch baseline
GET /api/v1/cost-elements/{id}/evm?branch=main

# Change order branch
GET /api/v1/cost-elements/{id}/evm?branch=BR-001-feature-addition
```

### 4. Cost Trend Analysis

Use aggregated costs for trend analysis:

```bash
# Monthly cost trends
GET /api/v1/cost-registrations/aggregated?cost_element_id={id}&period=monthly&start_date=2026-01-01T00:00:00Z&end_date=2026-12-31T23:59:59Z
```

### 5. Cumulative S-Curves

Generate S-curve charts using cumulative costs:

```bash
# Cumulative costs for S-curve
GET /api/v1/cost-registrations/cumulative?cost_element_id={id}&start_date=2026-01-01T00:00:00Z
```

---

## References

- [Earned Value Management (Wikipedia)](https://en.wikipedia.org/wiki/Earned_value_management)
- [EVM Formulas Guide (PMI)](https://www.pmi.org/about/learn-about-pmi/what-is-project-management/earned-value-management)
- [ADR-005: Bitemporal Versioning](../decisions/adr-005-bitemporal-versioning.md)
- [Cost Element & Financial Tracking Context](../01-bounded-contexts.md)
