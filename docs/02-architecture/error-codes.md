# Error Codes Reference

**Last Updated:** 2026-03-02
**Status:** Active

This document provides a comprehensive reference for error codes returned by the Backcast  API.

---

## Error Response Format

All API errors follow this structure:

```json
{
  "detail": "Human-readable error message",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR",
  "context": {
    "field": "budget_allocation",
    "constraint": "must_be_positive"
  }
}
```

---

## HTTP Status Codes

| Status | Meaning | When Used |
|--------|---------|-----------|
| 400 | Bad Request | Invalid input, validation errors |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource state conflict |
| 422 | Unprocessable Entity | Validation failure |
| 500 | Internal Server Error | Unexpected server error |

---

## Error Code Categories

### 1. Validation Errors (VAL-xxx)

| Code | HTTP Status | Description | Example |
|------|-------------|-------------|---------|
| `VAL-001` | 400 | Required field missing | `name is required` |
| `VAL-002` | 400 | Invalid format | `date must be ISO 8601` |
| `VAL-003` | 400 | Value out of range | `budget must be >= 0` |
| `VAL-004` | 400 | Invalid reference | `parent_wbe_id not found` |
| `VAL-005` | 400 | Duplicate value | `code already exists in project` |
| `VAL-006` | 400 | Invalid state transition | `Cannot approve draft change order` |

### 2. Authentication Errors (AUTH-xxx)

| Code | HTTP Status | Description | Example |
|------|-------------|-------------|---------|
| `AUTH-001` | 401 | Token missing | `Authorization header required` |
| `AUTH-002` | 401 | Token expired | `Token has expired` |
| `AUTH-003` | 401 | Token invalid | `Invalid token signature` |
| `AUTH-004` | 403 | Insufficient role | `Requires project_manager role` |
| `AUTH-005` | 403 | Resource access denied | `No access to this project` |

### 3. Business Logic Errors (BIZ-xxx)

| Code | HTTP Status | Description | Example |
|------|-------------|-------------|---------|
| `BIZ-001` | 409 | Branch locked | `Cannot modify locked branch` |
| `BIZ-002` | 409 | Merge conflict | `Conflicts detected during merge` |
| `BIZ-003` | 400 | Revenue mismatch | `Total revenue doesn't match contract value` |
| `BIZ-004` | 400 | Invalid operation | `Cannot delete WBE with cost elements` |
| `BIZ-005` | 409 | Concurrent modification | `Entity modified by another user` |
| `BIZ-006` | 400 | Invalid branch operation | `Cannot merge unapproved change order` |
| `BIZ-007` | 400 | Invalid workflow state | `Change order not in approved state` |

### 4. Temporal/Version Errors (TMP-xxx)

| Code | HTTP Status | Description | Example |
|------|-------------|-------------|---------|
| `TMP-001` | 400 | Invalid time range | `valid_from must be before valid_to` |
| `TMP-002` | 400 | Overlapping versions | `Entity already has version for this period` |
| `TMP-003` | 404 | Version not found | `No version exists at as_of date` |
| `TMP-004` | 400 | Branch not found | `Branch BR-001 does not exist` |
| `TMP-005` | 400 | Control date conflict | `control_date must be within valid_time` |
| `TMP-006` | 400 | Time travel limit | `Cannot query dates before project creation` |

### 5. EVM Errors (EVM-xxx)

| Code | HTTP Status | Description | Example |
|------|-------------|-------------|---------|
| `EVM-001` | 400 | No baseline data | `No schedule baseline for cost element` |
| `EVM-002` | 400 | No progress data | `No progress entries recorded` |
| `EVM-003` | 400 | Invalid progression type | `Unknown progression type: xyz` |
| `EVM-004` | 400 | Division by zero | `Cannot calculate CPI with AC=0` |
| `EVM-005` | 400 | Date range error | `as_of date outside project range` |

### 6. Database Errors (DB-xxx)

| Code | HTTP Status | Description | Example |
|------|-------------|-------------|---------|
| `DB-001` | 500 | Constraint violation | `Foreign key constraint failed` |
| `DB-002` | 500 | Connection error | `Database connection failed` |
| `DB-003` | 500 | Transaction failed | `Transaction rolled back` |
| `DB-004` | 500 | Query timeout | `Query exceeded timeout limit` |

---

## Common Error Scenarios

### Creating a WBE

```json
// Error: Duplicate code
{
  "detail": "WBE with code '1.2.3' already exists in this project",
  "status_code": 400,
  "error_code": "VAL-005",
  "context": {
    "field": "code",
    "value": "1.2.3"
  }
}
```

### Updating a Change Order

```json
// Error: Invalid state transition
{
  "detail": "Cannot approve change order in 'draft' state. Submit first.",
  "status_code": 400,
  "error_code": "VAL-006",
  "context": {
    "current_state": "draft",
    "requested_action": "approve"
  }
}
```

### Merging a Branch

```json
// Error: Branch locked
{
  "detail": "Branch 'BR-001' is locked and cannot be modified",
  "status_code": 409,
  "error_code": "BIZ-001",
  "context": {
    "branch": "BR-001",
    "locked_by": "user@example.com",
    "locked_at": "2026-03-01T10:00:00Z"
  }
}
```

### Revenue Allocation

```json
// Error: Revenue mismatch
{
  "detail": "Total revenue allocation (€150,000) does not match project contract value (€160,000)",
  "status_code": 400,
  "error_code": "BIZ-003",
  "context": {
    "total_revenue": 150000,
    "contract_value": 160000,
    "difference": 10000
  }
}
```

---

## Error Handling Best Practices

### For API Consumers

1. **Always check status_code first**
   - 4xx = Client error (fix your request)
   - 5xx = Server error (retry or contact support)

2. **Use error_code for programmatic handling**
   ```python
   if error.get("error_code") == "BIZ-001":
       # Handle locked branch
       show_unlock_dialog()
   ```

3. **Display detail to users**
   - The `detail` field contains user-friendly messages

4. **Check context for additional info**
   - Field-level errors include the problematic field
   - Constraint violations include the constraint name

### For API Developers

1. **Use appropriate HTTP status codes**
2. **Include error_code for all business errors**
3. **Provide actionable detail messages**
4. **Include relevant context**

---

## Related Documentation

- [API Conventions](./cross-cutting/api-conventions.md) - General API patterns
- [API Endpoints Reference](./api-endpoints.md) - Endpoint documentation
