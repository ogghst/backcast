<!-- 4d94353e-cd95-4209-8116-5b5fd15471bb f51017f6-7c06-45d7-bc20-52a55c4752eb -->
# E1-003: Application Framework Setup Implementation Plan

## Overview

Implement full-stack CRUD operations for Projects, WBEs, and Cost Elements following TDD principles with entity-by-entity incremental delivery. Users will navigate hierarchically through nested detail views (Projects → Project Detail with WBEs → WBE Detail with Cost Elements). Includes bulk template import API.

## Implementation Strategy

**Approach:** Entity-by-entity (Project → WBE → Cost Element)

**Permissions:** All authenticated users can see/manage all projects

**Navigation:** Nested detail views (hierarchical drill-down)

**Client Generation:** After each entity backend completion

**Commit Size:** Target <100 lines, <5 files per commit

---

## Phase 1: Projects Backend (CRUD + Tests)

### 1.1 Add Projects List Schema

**File:** `backend/app/models/project.py`

- Add `ProjectsPublic` class after `ProjectPublic`:
```python
class ProjectsPublic(SQLModel):
    data: list[ProjectPublic]
    count: int
```


**File:** `backend/app/models/__init__.py`

- Export `ProjectsPublic` in imports and `__all__`

**Tests:** Verify schema imports correctly

---

### 1.2 Create Projects API Router

**File:** `backend/app/api/routes/projects.py` (NEW)

Implement endpoints following `items.py` pattern:

- `GET /api/v1/projects/` - List all projects with pagination (skip, limit)
- `GET /api/v1/projects/{id}` - Get single project by project_id
- `POST /api/v1/projects/` - Create new project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project (returns Message)

**Dependencies:** `SessionDep`, `CurrentUser`

**Validation:**

- Check UUID validity
- Verify project exists before update/delete
- Return 404 if not found

**No permission filtering** - all users see all projects

**File:** `backend/app/api/main.py`

- Import projects router
- Add `api_router.include_router(projects.router)` after items router

---

### 1.3 Backend Tests - Projects Model

**File:** `backend/tests/models/test_project.py` (EXISTS - enhance)

Add tests if missing:

- Create project with all fields
- Create project with minimal fields
- Verify relationships (project_manager)
- Test schema validation (ProjectCreate, ProjectUpdate, ProjectPublic)

---

### 1.4 Backend Tests - Projects API

**File:** `backend/tests/api/routes/test_projects.py` (NEW)

Implement TDD tests:

- `test_create_project` - POST with valid data
- `test_read_projects_list` - GET list with pagination
- `test_read_project_by_id` - GET single project
- `test_read_project_not_found` - GET invalid UUID returns 404
- `test_update_project` - PUT with valid changes
- `test_update_project_not_found` - PUT invalid UUID returns 404
- `test_delete_project` - DELETE existing project
- `test_delete_project_not_found` - DELETE invalid UUID returns 404

Follow pattern from `test_items.py` using fixtures.

---

### 1.5 Generate Frontend Client

**Command:** `./scripts/generate-client.sh`

Verify generated:

- `frontend/src/client/sdk.gen.ts` includes `ProjectsService`
- Methods: `readProjects`, `readProject`, `createProject`, `updateProject`, `deleteProject`

---

## Phase 2: Projects Frontend (UI Components)

### 2.1 Projects List Route

**File:** `frontend/src/routes/_layout/projects.tsx` (NEW)

Implement following `items.tsx` pattern:

- TanStack Router route with search params (page)
- `useQuery` for data fetching from `ProjectsService.readProjects`
- Pagination with `PaginationRoot`
- Table displaying: project_name, customer_name, contract_value, start_date, status
- Click row → navigate to `/projects/{id}` detail view
- Empty state when no projects
- Loading state with `PendingProjects` component

---

### 2.2 Projects Components - Add/Edit/Delete

**Directory:** `frontend/src/components/Projects/` (NEW)

**File:** `AddProject.tsx`

- Modal with form using React Hook Form
- Fields: project_name, customer_name, contract_value, project_code, pricelist_code, start_date, planned_completion_date, project_manager_id (dropdown of users), status, notes
- `useMutation` for `ProjectsService.createProject`
- Invalidate queries on success

**File:** `EditProject.tsx`

- Similar to AddProject, pre-fill form with existing data
- `useMutation` for `ProjectsService.updateProject`

**File:** `DeleteProject.tsx`

- Confirmation modal
- `useMutation` for `ProjectsService.deleteProject`

**File:** `PendingProjects.tsx` (NEW)

- Loading skeleton similar to `PendingItems.tsx`

---

### 2.3 Project Detail Route (Parent View)

**File:** `frontend/src/routes/_layout/projects.$id.tsx` (NEW)

Layout:

- Display project header (name, customer, contract value, dates, status)
- Edit/Delete buttons for project
- **WBEs table** below project details
- "Add WBE" button
- Each WBE row clickable → navigate to `/projects/{projectId}/wbes/{wbeId}`

Components needed:

- Project detail card
- WBEs table (list WBEs for this project)
- Add WBE button/modal

---

### 2.4 Update Sidebar Navigation

**File:** `frontend/src/components/Common/SidebarItems.tsx`

Add to `items` array:

```typescript
{ icon: FiBriefcase, title: "Projects", path: "/projects" }
```

Position: After Dashboard, before Items

---

## Phase 3: WBEs Backend (CRUD + Tests)

### 3.1 Add WBEs List Schema

**File:** `backend/app/models/wbe.py`

- Add `WBEsPublic` class after `WBEPublic`:
```python
class WBEsPublic(SQLModel):
    data: list[WBEPublic]
    count: int
```


**File:** `backend/app/models/__init__.py`

- Export `WBEsPublic`

---

### 3.2 Create WBEs API Router

**File:** `backend/app/api/routes/wbes.py` (NEW)

Endpoints:

- `GET /api/v1/wbes/` - List all WBEs with pagination + optional `?project_id=` filter
- `GET /api/v1/wbes/{id}` - Get single WBE by wbe_id
- `POST /api/v1/wbes/` - Create new WBE (validate project_id exists)
- `PUT /api/v1/wbes/{id}` - Update WBE
- `DELETE /api/v1/wbes/{id}` - Delete WBE

**Validation:**

- Verify `project_id` exists in database before creating WBE
- Return 400 if parent project not found

**File:** `backend/app/api/main.py`

- Register wbes router

---

### 3.3 Backend Tests - WBEs API

**File:** `backend/tests/api/routes/test_wbes.py` (NEW)

Tests:

- Create WBE with valid project_id
- Create WBE with invalid project_id → 400 error
- Read WBEs list (all)
- Read WBEs filtered by project_id
- Read single WBE
- Update WBE
- Delete WBE
- Verify cascade delete when project deleted

---

### 3.4 Generate Frontend Client

**Command:** `./scripts/generate-client.sh`

Verify `WBEsService` generated.

---

## Phase 4: WBEs Frontend (UI Components)

### 4.1 WBE Detail Route (Parent View)

**File:** `frontend/src/routes/_layout/projects.$projectId.wbes.$wbeId.tsx` (NEW)

Layout:

- Breadcrumbs: Projects → {Project Name} → {WBE Machine Type}
- WBE details card (machine_type, serial_number, delivery date, revenue, status)
- Edit/Delete buttons for WBE
- **Cost Elements table** below WBE details
- "Add Cost Element" button
- Each Cost Element row shows: department_name, budget_bac, revenue_plan, status

---

### 4.2 WBEs Components - Add/Edit/Delete

**Directory:** `frontend/src/components/WBEs/` (NEW)

**File:** `AddWBE.tsx`

- Modal form with project_id passed as prop
- Fields: machine_type, serial_number, contracted_delivery_date, revenue_allocation, status, notes
- `useMutation` for `WBEsService.createWbe`

**File:** `EditWBE.tsx`

- Pre-fill existing WBE data
- `useMutation` for `WBEsService.updateWbe`

**File:** `DeleteWBE.tsx`

- Confirmation with cascade warning (will delete cost elements)
- `useMutation` for `WBEsService.deleteWbe`

---

## Phase 5: Cost Elements Backend (CRUD + Tests)

### 5.1 Add Cost Elements List Schema

**File:** `backend/app/models/cost_element.py`

- Add `CostElementsPublic` class:
```python
class CostElementsPublic(SQLModel):
    data: list[CostElementPublic]
    count: int
```


**File:** `backend/app/models/__init__.py`

- Export `CostElementsPublic`

---

### 5.2 Create Cost Elements API Router

**File:** `backend/app/api/routes/cost_elements.py` (NEW)

Endpoints:

- `GET /api/v1/cost-elements/` - List all with pagination + optional `?wbe_id=` filter
- `GET /api/v1/cost-elements/{id}` - Get single cost element
- `POST /api/v1/cost-elements/` - Create (validate wbe_id and cost_element_type_id exist)
- `PUT /api/v1/cost-elements/{id}` - Update
- `DELETE /api/v1/cost-elements/{id}` - Delete

**Validation:**

- Verify `wbe_id` exists
- Verify `cost_element_type_id` exists (reference data)
- Return 400 if parent not found

**File:** `backend/app/api/main.py`

- Register cost_elements router

---

### 5.3 Backend Tests - Cost Elements API

**File:** `backend/tests/api/routes/test_cost_elements.py` (NEW)

Tests:

- Create cost element with valid wbe_id
- Create with invalid wbe_id → 400
- List all cost elements
- List filtered by wbe_id
- Read single cost element
- Update cost element
- Delete cost element
- Verify cascade when WBE deleted

---

### 5.4 Generate Frontend Client

**Command:** `./scripts/generate-client.sh`

Verify `CostElementsService` generated.

---

## Phase 6: Cost Elements Frontend (UI Components)

### 6.1 Cost Elements Components - Add/Edit/Delete

**Directory:** `frontend/src/components/CostElements/` (NEW)

**File:** `AddCostElement.tsx`

- Modal form with wbe_id passed as prop
- Fields: department_code, department_name, cost_element_type_id (dropdown), budget_bac, revenue_plan, status, notes
- `useMutation` for `CostElementsService.createCostElement`

**File:** `EditCostElement.tsx`

- Pre-fill form
- `useMutation` for `CostElementsService.updateCostElement`

**File:** `DeleteCostElement.tsx`

- Simple confirmation (leaf node, no cascade)
- `useMutation` for `CostElementsService.deleteCostElement`

---

## Phase 7: Template Import API (Bulk Creation)

### 7.1 Template Import Endpoint

**File:** `backend/app/api/routes/projects.py`

Add endpoint:

- `POST /api/v1/projects/from-template`
- **Request body:** JSON with structure:
```python
class ProjectTemplate(SQLModel):
    project: ProjectCreate
    wbes: list[WBETemplateItem]

class WBETemplateItem(SQLModel):
    wbe: WBECreate (without project_id)
    cost_elements: list[CostElementCreate (without wbe_id)]
```


**Logic:**

1. Start database transaction
2. Create project
3. Loop through wbes, create each with project_id
4. Loop through cost_elements for each wbe, create with wbe_id
5. Commit transaction (atomic)
6. Return complete project with nested data

**Error handling:**

- Rollback on any error
- Return 400 with specific validation errors

---

### 7.2 Sample Template Document

**File:** `docs/project_template_sample.json` (NEW)

Create realistic example:

```json
{
  "project": {
    "project_name": "Automotive Assembly Line - Plant 3",
    "customer_name": "AutoCorp Manufacturing",
    "contract_value": 500000.00,
    "project_code": "PROJ-2025-001",
    "pricelist_code": "LISTINO 118",
    "start_date": "2025-01-15",
    "planned_completion_date": "2025-12-31",
    "project_manager_id": "{user_uuid}",
    "status": "active",
    "notes": "Full automation line with 3 robotic units"
  },
  "wbes": [
    {
      "wbe": {
        "machine_type": "Robotic Welding Station",
        "serial_number": "RWS-001",
        "contracted_delivery_date": "2025-06-30",
        "revenue_allocation": 200000.00,
        "status": "designing"
      },
      "cost_elements": [
        {
          "department_code": "MECH",
          "department_name": "Mechanical Engineering",
          "cost_element_type_id": "{type_uuid}",
          "budget_bac": 50000.00,
          "revenue_plan": 60000.00,
          "status": "planned"
        },
        {
          "department_code": "ELEC",
          "department_name": "Electrical Engineering",
          "cost_element_type_id": "{type_uuid}",
          "budget_bac": 40000.00,
          "revenue_plan": 50000.00,
          "status": "planned"
        }
      ]
    }
  ]
}
```

Include documentation explaining:

- How to get valid UUIDs (user_id, cost_element_type_id)
- Field requirements and validation rules
- How to use the endpoint

---

### 7.3 Template Import Tests

**File:** `backend/tests/api/routes/test_projects.py`

Add tests:

- `test_create_from_template_success` - Valid complete template
- `test_create_from_template_invalid_project` - Invalid project data
- `test_create_from_template_invalid_wbe` - One WBE fails
- `test_create_from_template_rollback` - Verify transaction rollback on error

---

## Phase 8: Integration & Polish

### 8.1 Common Components

**File:** `frontend/src/components/Common/ActionsMenu.tsx` (NEW)

Create generic actions menu for Projects/WBEs/CostElements (similar to `ItemActionsMenu.tsx`):

- Edit action
- Delete action
- View details action

---

### 8.2 Breadcrumbs Component

**File:** `frontend/src/components/Common/Breadcrumbs.tsx` (NEW)

Reusable breadcrumb navigation:

- Projects → Project Detail → WBE Detail
- Used in nested detail views

---

### 8.3 End-to-End Manual Testing

- Create project via UI
- Add WBEs to project
- Add cost elements to WBE
- Edit entities
- Delete cost element → verify only that deleted
- Delete WBE → verify cascades to cost elements
- Delete project → verify cascades to all children
- Import from template → verify complete structure created

---

## Success Criteria

**Backend:**

- ✅ All CRUD endpoints operational for Projects, WBEs, Cost Elements
- ✅ Template import endpoint creates complete hierarchies
- ✅ All tests passing (model + API tests)
- ✅ Proper validation and error handling
- ✅ No authentication/permission issues

**Frontend:**

- ✅ Hierarchical navigation: Projects list → Detail → WBE Detail
- ✅ All CRUD modals functional
- ✅ Client auto-generated and synced
- ✅ Sidebar navigation updated
- ✅ Loading and empty states implemented

**Documentation:**

- ✅ Sample template JSON with instructions

**Quality Gates Met:**

- ✅ All commits <100 lines (target)
- ✅ All commits <5 files (target)
- ✅ TDD followed: tests before implementation
- ✅ No compilation errors
- ✅ Architectural patterns respected

---

## File Summary

**Backend Files Created/Modified:**

1. `backend/app/models/project.py` - Add ProjectsPublic
2. `backend/app/models/wbe.py` - Add WBEsPublic
3. `backend/app/models/cost_element.py` - Add CostElementsPublic
4. `backend/app/models/__init__.py` - Export new schemas
5. `backend/app/api/routes/projects.py` - NEW router
6. `backend/app/api/routes/wbes.py` - NEW router
7. `backend/app/api/routes/cost_elements.py` - NEW router
8. `backend/app/api/main.py` - Register routers
9. `backend/tests/api/routes/test_projects.py` - NEW tests
10. `backend/tests/api/routes/test_wbes.py` - NEW tests
11. `backend/tests/api/routes/test_cost_elements.py` - NEW tests

**Frontend Files Created/Modified:**

12. `frontend/src/routes/_layout/projects.tsx` - NEW
13. `frontend/src/routes/_layout/projects.$id.tsx` - NEW
14. `frontend/src/routes/_layout/projects.$projectId.wbes.$wbeId.tsx` - NEW
15. `frontend/src/components/Projects/AddProject.tsx` - NEW
16. `frontend/src/components/Projects/EditProject.tsx` - NEW
17. `frontend/src/components/Projects/DeleteProject.tsx` - NEW
18. `frontend/src/components/Projects/PendingProjects.tsx` - NEW
19. `frontend/src/components/WBEs/AddWBE.tsx` - NEW
20. `frontend/src/components/WBEs/EditWBE.tsx` - NEW
21. `frontend/src/components/WBEs/DeleteWBE.tsx` - NEW
22. `frontend/src/components/CostElements/AddCostElement.tsx` - NEW
23. `frontend/src/components/CostElements/EditCostElement.tsx` - NEW
24. `frontend/src/components/CostElements/DeleteCostElement.tsx` - NEW
25. `frontend/src/components/Common/SidebarItems.tsx` - MODIFY
26. `frontend/src/components/Common/ActionsMenu.tsx` - NEW
27. `frontend/src/components/Common/Breadcrumbs.tsx` - NEW
28. `frontend/src/client/*` - REGENERATE (3 times)

**Documentation:**

29. `docs/project_template_sample.json` - NEW

**Total: ~29 files, delivered incrementally across 15-20 commits**

### To-dos

- [x] Implement Projects backend (list schema, API router, tests)
- [ ] Implement Projects frontend (list route, detail route, components, navigation)
- [x] Implement WBEs backend (list schema, API router with project validation, tests)
- [ ] Implement WBEs frontend (detail route with WBEs table, components)
- [x] Implement Cost Elements backend (list schema, API router with WBE validation, tests)
- [ ] Implement Cost Elements frontend (detail route with cost elements table, components)
- [x] Implement template import endpoint with transaction handling and sample JSON doc
- [ ] Create common components (ActionsMenu, Breadcrumbs) and perform end-to-end testing
