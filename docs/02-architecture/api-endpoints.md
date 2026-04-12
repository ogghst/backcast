# API Endpoints Reference

**Last Updated:** 2026-03-02
**Status:** Active

> **Scope:** Quick reference catalog of all API endpoints in Backcast.
>
> **Purpose:**
> - Browseable endpoint index without running the backend
> - Human-readable overview of available resources
> - Quick lookup of path parameters, query parameters, and response types
> - Notes on domain-specific behaviors (e.g., computed fields, workflow actions)
>
> **Authoritative Source:**
> This document is a **companion** to the auto-generated OpenAPI documentation. For the most up-to-date endpoint definitions, request/response schemas, and interactive testing, use the live Swagger UI at `/docs` or the OpenAPI spec at `/openapi.json` when the backend is running.
>
> **Related:**
> - [API Conventions](./cross-cutting/api-conventions.md) — Protocol-level patterns (HTTP methods, context parameters, authentication)
> - [API Response Patterns](./cross-cutting/api-response-patterns.md) — Server-side filtering, pagination, implementation patterns

---

## Endpoint Overview

| Context | Base Path | Description |
|---------|-----------|-------------|
| Projects | `/api/v1/projects` | Project management |
| WBEs | `/api/v1/wbes` | Work breakdown elements |
| Cost Elements | `/api/v1/cost-elements` | Cost element management |
| Change Orders | `/api/v1/change-orders` | Change order processing |
| EVM | `/api/v1/evm` | Earned value metrics |
| Users | `/api/v1/users` | User management |
| Departments | `/api/v1/departments` | Department management |

---

## 1. Projects

### List Projects
```
GET /api/v1/projects
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 100 | Max results |
| `status` | string | - | Filter by status |
| `branch` | string | "main" | Branch context |
| `as_of` | datetime | now | Time-travel timestamp |

**Response:** `ProjectListResponse`

### Get Project
```
GET /api/v1/projects/{project_id}
```

**Path Parameters:**
- `project_id` (UUID): Project root ID

**Response:** `ProjectRead`

### Create Project
```
POST /api/v1/projects
```

**Request Body:** `ProjectCreate`

**Response:** `ProjectRead` (201)

### Update Project
```
PUT /api/v1/projects/{project_id}
```

**Request Body:** `ProjectUpdate`

**Response:** `ProjectRead`

### Delete Project
```
DELETE /api/v1/projects/{project_id}
```

**Response:** 204 No Content

### Get Project History
```
GET /api/v1/projects/{project_id}/history
```

**Response:** `List[ProjectRead]`

---

## 2. WBEs (Work Breakdown Elements)

### List WBEs
```
GET /api/v1/wbes
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | UUID | required | Filter by project |
| `branch` | string | "main" | Branch context |
| `as_of` | datetime | now | Time-travel timestamp |
| `parent_wbe_id` | UUID | - | Filter by parent |
| `level` | int | - | Filter by level |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 100 | Max results |

**Response:** `WBEListResponse`

### Get WBE
```
GET /api/v1/wbes/{wbe_id}
```

**Response:** `WBERead`

> **Note:** `budget_allocation` is computed from child cost elements.

### Create WBE
```
POST /api/v1/wbes
```

**Request Body:** `WBECreate`
- `budget_allocation` is NOT accepted (computed from cost elements)

**Response:** `WBERead` (201)

### Update WBE
```
PUT /api/v1/wbes/{wbe_id}
```

**Request Body:** `WBEUpdate`
- `budget_allocation` is NOT accepted (computed from cost elements)

**Response:** `WBERead`

### Delete WBE
```
DELETE /api/v1/wbes/{wbe_id}
```

**Response:** 204 No Content

### Get WBE History
```
GET /api/v1/wbes/{wbe_id}/history
```

**Response:** `List[WBERead]`

---

## 3. Cost Elements

### List Cost Elements
```
GET /api/v1/cost-elements
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `wbe_id` | UUID | required | Filter by WBE |
| `branch` | string | "main" | Branch context |
| `as_of` | datetime | now | Time-travel timestamp |
| `cost_element_type_id` | UUID | - | Filter by type |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 100 | Max results |

**Response:** `CostElementListResponse`

### Get Cost Element
```
GET /api/v1/cost-elements/{cost_element_id}
```

**Response:** `CostElementRead`

### Create Cost Element
```
POST /api/v1/cost-elements
```

**Request Body:** `CostElementCreate`
- `budget_amount` is set here (THIS is where budget lives)

**Response:** `CostElementRead` (201)

### Update Cost Element
```
PUT /api/v1/cost-elements/{cost_element_id}
```

**Request Body:** `CostElementUpdate`

**Response:** `CostElementRead`

### Delete Cost Element
```
DELETE /api/v1/cost-elements/{cost_element_id}
```

**Response:** 204 No Content

### Get Cost Element EVM
```
GET /api/v1/cost-elements/{cost_element_id}/evm
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `branch` | string | "main" | Branch context |
| `as_of` | datetime | now | Time-travel timestamp |

**Response:** `EVMMetricsResponse`

---

## 4. Change Orders

### List Change Orders
```
GET /api/v1/change-orders
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | UUID | required | Filter by project |
| `status` | string | - | Filter by status |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 100 | Max results |

**Response:** `ChangeOrderListResponse`

### Get Change Order
```
GET /api/v1/change-orders/{change_order_id}
```

**Response:** `ChangeOrderRead`

### Create Change Order
```
POST /api/v1/change-orders
```

**Request Body:** `ChangeOrderCreate`

**Response:** `ChangeOrderRead` (201)

### Update Change Order
```
PUT /api/v1/change-orders/{change_order_id}
```

**Request Body:** `ChangeOrderUpdate`

**Response:** `ChangeOrderRead`

### Change Order Workflow Actions

```
POST /api/v1/change-orders/{change_order_id}/submit
POST /api/v1/change-orders/{change_order_id}/approve
POST /api/v1/change-orders/{change_order_id}/reject
POST /api/v1/change-orders/{change_order_id}/merge
POST /api/v1/change-orders/{change_order_id}/archive
```

**Request Body (optional):**
```json
{
  "comment": "string"
}
```

**Response:** `ChangeOrderRead`

### Get Impact Analysis
```
GET /api/v1/change-orders/{change_order_id}/impact-analysis
```

**Response:** `ImpactAnalysisResponse`

---

## 5. EVM Analysis

### Get Project EVM Summary
```
GET /api/v1/evm/projects/{project_id}/summary
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `branch` | string | "main" | Branch context |
| `as_of` | datetime | now | Time-travel timestamp |

**Response:** `EVMSummaryResponse`

### Get Project EVM Time Series
```
GET /api/v1/evm/projects/{project_id}/time-series
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `branch` | string | "main" | Branch context |
| `start_date` | date | - | Start of range |
| `end_date` | date | - | End of range |
| `granularity` | string | "weekly" | daily/weekly/monthly |

**Response:** `EVMTimeSeriesResponse`

---

## 6. Users

### List Users
```
GET /api/v1/users
```

**Response:** `UserListResponse`

### Get User
```
GET /api/v1/users/{user_id}
```

**Response:** `UserRead`

### Create User
```
POST /api/v1/users
```

**Request Body:** `UserCreate`

**Response:** `UserRead` (201)

### Update User
```
PUT /api/v1/users/{user_id}
```

**Request Body:** `UserUpdate`

**Response:** `UserRead`

### Delete User
```
DELETE /api/v1/users/{user_id}
```

**Response:** 204 No Content

---

## 7. Departments

### List Departments
```
GET /api/v1/departments
```

**Response:** `DepartmentListResponse`

### Get Department
```
GET /api/v1/departments/{department_id}
```

**Response:** `DepartmentRead`

### Create Department
```
POST /api/v1/departments
```

**Request Body:** `DepartmentCreate`

**Response:** `DepartmentRead` (201)

---

## Common Patterns

### Pagination
All list endpoints support:
- `skip` - Offset for pagination
- `limit` - Maximum results (default: 100, max: 1000)

### Branch Context
All endpoints support:
- `branch` - Branch name (default: "main")
- `as_of` - Time-travel timestamp

See: [API Conventions](./cross-cutting/api-conventions.md)

### Error Responses
All endpoints return consistent error structure:
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

See: [Error Codes Reference](./error-codes.md)

---

## Related Documentation

- [API Conventions](./cross-cutting/api-conventions.md) - Parameters, pagination, errors
- [EVM API Guide](./evm-api-guide.md) - EVM-specific endpoints
- [Temporal Query Reference](./cross-cutting/temporal-query-reference.md) - Time-travel patterns
