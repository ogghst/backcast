# Change Orders API

**Last Updated:** 2026-01-26
**Version:** 1.0
**Base Path:** `/api/v1/change-orders`

---

## Overview

Change Orders (COs) manage project modifications through isolated branch workflows. Each CO has an associated `co-{code}` branch where changes are developed before merging to the main branch.

**Key Features:**
- **Branch Isolation:** Automatic branch creation for each CO
- **Full Entity Merge:** Merges WBEs, CostElements, and the CO entity itself
- **Workflow Tracking:** Status transitions (Draft → Submitted → Approved → Implemented)
- **Conflict Detection:** Pre-merge validation for data conflicts
- **Audit Trail:** Complete history via version control

---

## Resources

### ChangeOrder Entity

```json
{
  "change_order_id": "uuid",
  "code": "CO-2026-001",
  "title": "Add New Automation Cell",
  "description": "Install new robotic arm",
  "project_id": "uuid",
  "status": "Approved",
  "branch": "main",
  "created_at": "2026-01-26T10:00:00Z",
  "updated_at": "2026-01-26T12:00:00Z",
  "available_transitions": ["Approved", "Rejected"],
  "can_edit_status": true,
  "branch_locked": false
}
```

**Status Values:**
- `Draft` - Initial state, editable
- `Submitted for Approval` - Pending review
- `Approved` - Ready for merge
- `Implemented` - Successfully merged to main
- `Rejected` - Changes declined

---

## Endpoints

### List Change Orders

**GET** `/api/v1/change-orders`

Retrieve paginated change orders for a project.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | UUID | Yes | Filter by project |
| `page` | integer | No | Page number (default: 1) |
| `per_page` | integer | No | Items per page (default: 20) |
| `branch` | string | No | Branch name (default: "main") |
| `search` | string | No | Search in code/title |
| `filters` | string | No | Format: `column:value;column:value1,value2` |
| `sort_field` | string | No | Field to sort by |
| `sort_order` | string | No | "asc" or "desc" (default: "asc") |
| `as_of` | datetime | No | Time travel query |

**Response:** `PaginatedResponse[ChangeOrderPublic]`

**Example:**
```bash
GET /api/v1/change-orders?project_id=123e4567-e89b-12d3-a456-426614174000&page=1&per_page=20
```

---

### Create Change Order

**POST** `/api/v1/change-orders`

Create a new change order with automatic branch creation.

**Request Body:**
```json
{
  "code": "CO-2026-001",
  "title": "Add New Automation Cell",
  "description": "Install new robotic arm in cell 4",
  "project_id": "uuid",
  "status": "Draft"
}
```

**Response:** `201 Created` + `ChangeOrderPublic`

**Behavior:**
1. Creates CO on `main` branch
2. Automatically creates `co-{code}` branch
3. Returns created CO with branch information

**Example:**
```bash
POST /api/v1/change-orders
{
  "code": "CO-2026-001",
  "title": "Add New Automation Cell",
  "description": "Install new robotic arm",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "Draft"
}
```

---

### Get Change Order

**GET** `/api/v1/change-orders/{change_order_id}`

Retrieve a specific change order by UUID.

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Query Parameters:**
- `branch` (string) - Branch name (default: "main")
- `as_of` (datetime) - Time travel query

**Response:** `200 OK` + `ChangeOrderPublic`

**Example:**
```bash
GET /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000
```

---

### Get Change Order by Code

**GET** `/api/v1/change-orders/by-code/{code}`

Retrieve a change order by business code.

**Path Parameters:**
- `code` (string) - Business code (e.g., "CO-2026-001")

**Query Parameters:**
- `branch` (string) - Branch name (default: "main")

**Response:** `200 OK` + `ChangeOrderPublic`

**Example:**
```bash
GET /api/v1/change-orders/by-code/CO-2026-001
```

---

### Update Change Order

**PUT** `/api/v1/change-orders/{change_order_id}`

Update change order metadata (creates new version).

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Request Body:**
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "status": "Submitted for Approval",
  "branch": "co-CO-2026-001"
}
```

**Response:** `200 OK` + `ChangeOrderPublic`

**Behavior:**
- Creates new version on specified branch
- Auto-forks from main if no version exists on target branch

**Example:**
```bash
PUT /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000
{
  "title": "Updated Title",
  "status": "Approved",
  "branch": "co-CO-2026-001"
}
```

---

### Delete Change Order

**DELETE** `/api/v1/change-orders/{change_order_id}`

Soft delete a change order (marks current version as deleted).

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Query Parameters:**
- `control_date` (datetime) - Optional control date for deletion

**Response:** `204 No Content`

**Example:**
```bash
DELETE /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000
```

---

### Get Change Order History

**GET** `/api/v1/change-orders/{change_order_id}/history`

Get complete version history for a change order.

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Response:** `200 OK` + `list[ChangeOrderPublic]`

**Behavior:**
- Returns all versions across all branches
- Shows complete audit trail

**Example:**
```bash
GET /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000/history
```

---

### Get Merge Conflicts

**GET** `/api/v1/change-orders/{change_order_id}/merge-conflicts`

Check for merge conflicts between source and target branches.

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Query Parameters:**
- `source_branch` (string) - Source branch name (e.g., "co-CO-2026-001")
- `target_branch` (string) - Target branch name (default: "main")

**Response:** `200 OK` + `list[dict]` (conflict details) or empty list

**Example:**
```bash
GET /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000/merge-conflicts?source_branch=co-CO-2026-001&target_branch=main
```

---

### Merge Change Order

**POST** `/api/v1/change-orders/{change_order_id}/merge`

Merge a Change Order's branch into the target branch.

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Request Body:**
```json
{
  "target_branch": "main",
  "comment": "Approved by steering committee"
}
```

**Response:** `200 OK` + `ChangeOrderPublic`

**Behavior:**
1. Infers source branch from CO code (e.g., `co-{code}`)
2. Checks for merge conflicts (returns 409 if conflicts exist)
3. Orchestrates full branch merge:
   - **WBEs:** All Work Breakdown Elements from source branch
   - **CostElements:** All Cost Elements from source branch
   - **Change Order:** The CO entity itself
4. Updates CO status to "Implemented"
5. Stores merge comment in audit log (if provided)

**Status Codes:**
- `200 OK` - Merge successful
- `404 Not Found` - Change Order not found
- `409 Conflict` - Merge conflicts detected
- `400 Bad Request` - Invalid request or locked branch

**Example:**
```bash
POST /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000/merge
{
  "target_branch": "main",
  "comment": "Approved by steering committee"
}
```

**Merge Details:**

The enhanced merge orchestrates all branchable entities:

| Entity Type | Merge Behavior | Service Used |
|-------------|----------------|--------------|
| **WBEs** | Merge each WBE from source to target | `WBEService.merge_branch()` |
| **CostElements** | Merge each CostElement from source to target | `CostElementService.merge_branch()` |
| **ChangeOrder** | Merge CO entity and update status | `ChangeOrderService.merge_branch()` |

**Soft-Delete Handling:**
- Entities soft-deleted on source branch are soft-deleted on target
- Maintains data integrity across branches

**Transactional Integrity:**
- All merges succeed or all fail (atomic operation)
- Rollback on any error

**Related Services:**
- `EntityDiscoveryService` - Discovers all entities in source branch
- `BranchableService` - Provides merge_branch capability for each entity
- `ChangeOrderService` - Orchestrates the full merge workflow

---

### Revert Change Order

**POST** `/api/v1/change-orders/{change_order_id}/revert`

Revert a change order to its previous version.

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Query Parameters:**
- `branch` (string) - Branch to revert on (default: "main")

**Response:** `200 OK` + `ChangeOrderPublic`

**Example:**
```bash
POST /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000/revert?branch=main
```

---

### Get Change Order Impact

**GET** `/api/v1/change-orders/{change_order_id}/impact`

Get impact analysis by comparing branches.

**Path Parameters:**
- `change_order_id` (UUID) - Root ID of the change order

**Query Parameters:**
- `branch_name` (string) - Branch to compare (e.g., "co-CO-2026-001")

**Response:** `200 OK` + `ImpactAnalysisResponse`

**Includes:**
- KPI Scorecard (BAC, Budget Delta, Gross Margin)
- Entity Changes (Added/Modified/Removed WBEs and CostElements)
- Waterfall Chart (cost bridge visualization)
- Time Series (weekly S-curve budget comparison)

**Example:**
```bash
GET /api/v1/change-orders/123e4567-e89b-12d3-a456-426614174000/impact?branch_name=co-CO-2026-001
```

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes

| Status | Description | Example |
|--------|-------------|---------|
| `200 OK` | Request successful | Merge completed |
| `201 Created` | Resource created | New CO created |
| `204 No Content` | Successful deletion | CO soft-deleted |
| `400 Bad Request` | Invalid request | Locked branch |
| `404 Not Found` | Resource not found | CO doesn't exist |
| `409 Conflict` | Merge conflicts | Conflicts detected |

---

## Permissions

All endpoints require specific permissions:

| Permission | Endpoints |
|------------|-----------|
| `change-order-read` | GET endpoints |
| `change-order-create` | POST /change-orders |
| `change-order-update` | PUT, merge, revert |
| `change-order-delete` | DELETE |

---

## Related Services

### Backend Services

- **ChangeOrderService** (`app/services/change_order_service.py`)
  - Orchestrates merge workflow
  - Manages CO lifecycle
  - Handles versioning

- **EntityDiscoveryService** (`app/services/entity_discovery_service.py`)
  - Discovers WBEs in branch
  - Discovers CostElements in branch
  - Filters soft-deleted entities

- **WBEService** (`app/services/wbe.py`)
  - Merges WBE entities between branches
  - Handles WBE versioning

- **CostElementService** (`app/services/cost_element_service.py`)
  - Merges CostElement entities between branches
  - Handles CostElement versioning

### Architecture Documentation

- [API Conventions](/docs/02-architecture/cross-cutting/api-conventions.md)
- [Branching System](/docs/02-architecture/evcs-core/branching.md)
- [Change Management](/docs/02-architecture/01-bounded-contexts.md#change-management)

---

## Changelog

### 2026-01-26 - v1.0
- **Enhanced Merge Behavior:** Merge endpoint now orchestrates ALL branch content (WBEs, CostElements, ChangeOrder)
- **Entity Discovery:** Added `EntityDiscoveryService` for discovering entities in branches
- **Soft-Delete Propagation:** Soft-deleted entities are properly merged to target branch
- **Status Update:** CO status automatically transitions to "Implemented" after successful merge
- **Transactional Integrity:** All merges succeed or all fail with rollback
- **Conflict Detection:** Pre-merge validation for data conflicts

---

## OpenAPI Specification

Interactive API documentation available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`
