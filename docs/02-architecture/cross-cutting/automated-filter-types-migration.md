# Migration Path: Automated Filter Types via OpenAPI

**Status:** Proposed / Future
**Related:** TD-014 (Frontend Filter Type Safety)

---

## Overview

Currently, frontend filter types (`src/types/filters.ts`) are manually maintained and synchronised with backend whitelists. As the application grows, this manual synchronization creates a risk of drift.

This document outlines the strategy to transition from manual types to fully automated generation via the OpenAPI specification.

---

## 1. Backend Implementation

### Goal

Expose filterable fields in the OpenAPI schema so the client generator can consume them.

### Approach

Use Pydantic `json_schema_extra` to tag fields or a custom OpenAPI extension at the endpoint level.

#### Option A: Endpoint Extension (Recommended)

Decorate endpoints with `x-filterable-fields`:

```python
@router.get("",
    summary="List Projects",
    openapi_extra={
        "x-filterable-fields": ["status", "code", "name"]
    }
)
async def read_projects(...):
    ...
```

#### Option B: Model Tagging

If filters strictly match model fields:

```python
class ProjectRead(BaseModel):
    code: str = Field(..., json_schema_extra={"filterable": True})
```

---

## 2. OpenAPI Generator Enhancement

The current frontend client generation uses `openapi-typescript-codegen` (or similar). We need to hook into the generation process.

### Step 1: Extract Metadata

Create a script to parse `openapi.json` and extract `x-filterable-fields` for each operation ID.

### Step 2: Generate Interfaces

Generate TypeScript interfaces that map operation IDs (or resources) to their allowed filters.

```typescript
// api/generated/filters.ts
export interface ProjectFilters {
  status?: string | string[];
  code?: string | string[];
  name?: string | string[];
}
```

---

## 3. Frontend Integration

Refactor `useTableParams` to use these generated types.

### Current State (Manual)

```typescript
import { ProjectFilters } from "@/types/filters"; // Manual file
useTableParams<Project, ProjectFilters>();
```

### Future State (Automated)

```typescript
import { ProjectFilters } from "@/api/generated/filters"; // Generated file
useTableParams<Project, ProjectFilters>();
```

---

## 4. Migration Steps

1. **Tag Backend:** Update `FilterParser` or Route definitions to emit `x-filterable-fields` automatically based on the allowed whitelist.
2. **Update Generator:** Modify the `npm run generate-client` script to produce `filters.ts`.
3. **Switch Imports:** Update `src/types/filters.ts` to re-export from generated file (for backward compatibility) or update imports directly.
4. **Deprecate Manual Types:** Remove manual definitions in `src/types/filters.ts`.

---
