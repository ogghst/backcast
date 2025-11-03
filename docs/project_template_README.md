# Project Template Import Guide

## Overview

The project template import endpoint allows you to create a complete project structure in a single API call. This includes the project, all Work Breakdown Elements (WBEs), and all Cost Elements, all within a transactional operation.

## Endpoint

```
POST /api/v1/projects/from-template
```

## Request Body Structure

The request must follow this JSON structure:

```json
{
  "project": {
    // ProjectCreate schema fields
    "project_name": "string",
    "customer_name": "string",
    "contract_value": number,
    "start_date": "YYYY-MM-DD",
    "planned_completion_date": "YYYY-MM-DD",
    "project_manager_id": "uuid",
    "status": "active|on-hold|completed|cancelled",
    "project_code": "string (optional)",
    "pricelist_code": "string (optional)",
    "notes": "string (optional)"
  },
  "wbes": [
    {
      "wbe": {
        // WBECreate schema fields
        "machine_type": "string",
        "revenue_allocation": number,
        "status": "designing|in-production|shipped|commissioning|completed",
        "serial_number": "string (optional)",
        "contracted_delivery_date": "YYYY-MM-DD (optional)",
        "notes": "string (optional)"
      },
      "cost_elements": [
        {
          // CostElementCreate schema fields
          "department_code": "string",
          "department_name": "string",
          "cost_element_type_id": "uuid",
          "budget_bac": number,
          "revenue_plan": number,
          "status": "planned|active|completed|cancelled",
          "notes": "string (optional)"
        }
      ]
    }
  ]
}
```

## Prerequisites

Before importing a template, you need to have:

1. **A valid User ID** for `project_manager_id` - Get this from the `/api/v1/users/` endpoint
2. **A valid Cost Element Type ID** for each cost element - Get this from the cost element types lookup table

### Getting Valid UUIDs

**Get User ID:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Get Cost Element Type ID:**
Cost Element Types are reference data that should be pre-seeded in the database or created before import.

## Example Usage

See `project_template_sample.json` for a complete realistic example.

### Using curl

```bash
curl -X POST "http://localhost:8000/api/v1/projects/from-template" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @project_template_sample.json
```

### Using Python

```python
import requests
import json

headers = {"Authorization": "Bearer YOUR_TOKEN"}

with open("project_template_sample.json") as f:
    template = json.load(f)

# Replace placeholder UUIDs with valid ones
template["project"]["project_manager_id"] = "your-user-uuid"
template["wbes"][0]["cost_elements"][0]["cost_element_type_id"] = "your-type-uuid"
# ... repeat for all cost elements

response = requests.post(
    "http://localhost:8000/api/v1/projects/from-template",
    headers=headers,
    json=template
)

print(response.json())
```

## Response

On success, returns a `ProjectPublic` object with the created project:

```json
{
  "project_id": "uuid",
  "project_name": "string",
  "customer_name": "string",
  "contract_value": "string (decimal)",
  ...
  "project_manager_id": "uuid"
}
```

All associated WBEs and Cost Elements are created in the database but not returned in the response.

## Transaction Semantics

- **Atomic Operation**: All entities are created in a single database transaction
- **Rollback on Error**: If any entity fails validation or creation, the entire operation is rolled back
- **No Partial Success**: You will never end up with a project that has some WBEs missing

## Validation

The endpoint validates:

1. **Project data**: All required fields must be present and valid
2. **WBE data**: Each WBE must have required fields
3. **Foreign key constraints**: `project_manager_id` must exist in User table
4. **Cost Element data**: Each cost element must have valid `cost_element_type_id` and `wbe_id` is auto-assigned
5. **Foreign key constraints**: `cost_element_type_id` must exist in CostElementType table

## Error Handling

- **400 Bad Request**: Validation errors or foreign key constraint violations
- **422 Unprocessable Entity**: JSON schema validation errors
- **500 Internal Server Error**: Unexpected database errors

On error, the response includes details:

```json
{
  "detail": "Failed to create project from template: <specific error message>"
}
```

## Best Practices

1. **Validate UUIDs First**: Query your database to get valid user and cost element type IDs
2. **Start Simple**: Test with a minimal template (1 project, 1 WBE, 1 cost element) first
3. **Check References**: Ensure all referenced foreign keys exist before import
4. **Use Realistic Data**: For testing, use `project_template_sample.json` as a starting point
5. **Handle Errors**: Always catch and inspect error messages to understand validation failures

## Sample Template

See `project_template_sample.json` for a complete working example with:
- 1 project (Automotive Assembly Line)
- 2 WBEs (Robotic Welding Station, Assembly Robot)
- 8 cost elements total across various departments

Remember to replace the placeholder UUIDs with valid ones from your database!
