<!-- e265667e-87b3-4183-8a99-6cc76b77639a 21e0489f-f376-4d68-8931-6fe930370666 -->
# Full CRUD Operations: Projects, WBEs, and Cost Elements

## ANALYSIS PHASE SUMMARY

### 1. CODEBASE PATTERN ANALYSIS

**Existing CRUD Patterns Identified:**

**Backend (FastAPI):**

- All CRUD endpoints already exist and are fully tested:
  - `POST /api/v1/projects/`, `PUT /api/v1/projects/{id}`, `DELETE /api/v1/projects/{id}` ✅
  - `POST /api/v1/wbes/`, `PUT /api/v1/wbes/{id}`, `DELETE /api/v1/wbes/{id}` ✅
  - `POST /api/v1/cost-elements/`, `PUT /api/v1/cost-elements/{id}`, `DELETE /api/v1/cost-elements/{id}` ✅
- All endpoints have comprehensive test coverage (121/121 tests passing)
- Standard pattern: `{resource}.model_dump(exclude_unset=True)` for updates
- Deletion returns `Message` with success confirmation

**Frontend (React + TanStack):**

- **Create operations:** Fully implemented via `AddProject.tsx`, `AddWBE.tsx`, `AddCostElement.tsx` ✅
- **Read operations:** List and detail views working ✅
- **Update operations:** ❌ Not implemented (Missing: EditProject, EditWBE, EditCostElement)
- **Delete operations:** ❌ Not implemented (Missing: DeleteProject, DeleteWBE, DeleteCostElement)

**Reference Implementation Pattern (Users):**

- `EditUser.tsx`: Modal dialog with react-hook-form, pre-populated with existing data
- `DeleteUser.tsx`: Confirmation dialog with warning message
- `UserActionsMenu.tsx`: 3-dot menu component combining Edit + Delete
- Used in `admin.tsx` table with dedicated Actions column

### 2. INTEGRATION TOUCHPOINT MAPPING

**Files Requiring Modification:**

**New Component Files to Create:**

1. `frontend/src/components/Projects/EditProject.tsx` - Edit modal for projects
2. `frontend/src/components/Projects/DeleteProject.tsx` - Delete confirmation for projects
3. `frontend/src/components/Projects/ProjectActionsMenu.tsx` - Actions menu for projects
4. `frontend/src/components/Projects/EditWBE.tsx` - Edit modal for WBEs
5. `frontend/src/components/Projects/DeleteWBE.tsx` - Delete confirmation for WBEs
6. `frontend/src/components/Projects/WBEActionsMenu.tsx` - Actions menu for WBEs
7. `frontend/src/components/Projects/EditCostElement.tsx` - Edit modal for cost elements
8. `frontend/src/components/Projects/DeleteCostElement.tsx` - Delete confirmation for cost elements
9. `frontend/src/components/Projects/CostElementActionsMenu.tsx` - Actions menu for cost elements

**Existing Files to Modify:**

1. `frontend/src/routes/_layout/projects.tsx` - Add Actions column to ProjectsTable
2. `frontend/src/routes/_layout/projects.$id.tsx` - Add Actions column to WBEsTable
3. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` - Add Actions column to CostElementsTable

**Backend Files (Enhancement for Safe Delete):**

1. `backend/app/api/routes/projects.py` - Add child count check before deletion
2. `backend/app/api/routes/wbes.py` - Add child count check before deletion
3. `backend/tests/api/routes/test_projects.py` - Add test for blocked deletion
4. `backend/tests/api/routes/test_wbes.py` - Add test for blocked deletion

### 3. ABSTRACTION INVENTORY

**Reusable Components:**

- `DialogRoot`, `DialogContent`, `DialogHeader`, etc. from `@/components/ui/dialog`
- `useForm` from `react-hook-form` with `Controller` for controlled inputs
- `useMutation` + `useQueryClient` from `@tanstack/react-query`
- `useCustomToast` hook for success/error notifications
- `handleError` utility from `@/utils`
- `IconButton` with `BsThreeDotsVertical` for action menus
- `MenuRoot`, `MenuTrigger`, `MenuContent` from `@/components/ui/menu`

**Reusable Patterns:**

- Form validation with `mode: "onBlur"` and `criteriaMode: "all"`
- Query invalidation pattern: `queryClient.invalidateQueries({ queryKey: [...] })`
- Modal state management: `const [isOpen, setIsOpen] = useState(false)`
- Form reset on success: `reset()` then `setIsOpen(false)`

**Test Utilities (Backend):**

- `create_random_project()`, `create_random_wbe()`, `create_random_cost_element()`
- Standard test pattern for CRUD operations already established

### 4. ALTERNATIVE APPROACHES

**Approach 1: Inline Action Buttons (USER SELECTED - SAFEST)**

- **Pros:**
  - Direct and discoverable actions
  - Consistent with user's request for "inline in tables"
  - Clean separation of concerns (separate Edit/Delete components)
  - No cascade delete = data integrity preserved
- **Cons:**
  - Takes slightly more horizontal space in tables
  - More components to create (9 new components)
- **Alignment:** Follows UserActionsMenu pattern but with inline buttons instead of menu
- **Complexity:** Medium (need to check for children before allowing deletion)
- **Risk:** Low - well-established patterns

**Approach 2: Context Menu with Cascade Delete (NOT SELECTED)**

- **Pros:** Compact UI, familiar pattern
- **Cons:** HIGH RISK - cascade deletion could accidentally delete large hierarchies, violates user's "safe approach" requirement
- **Risk:** HIGH - data loss risk

**Approach 3: Edit/Delete on Detail Pages Only (NOT SELECTED)**

- **Pros:** More space for forms, less cluttered tables
- **Cons:** Extra navigation steps, doesn't meet "inline in tables" requirement
- **Risk:** Low but doesn't meet requirements

### 5. ARCHITECTURAL IMPACT ASSESSMENT

**Principles Followed:**

- ✅ **Separation of Concerns:** Each operation (Edit/Delete) in separate component
- ✅ **Consistency:** Follows existing Add{Resource} pattern and EditUser/DeleteUser patterns
- ✅ **Data Integrity:** Safe delete prevents orphaned records
- ✅ **User Experience:** Inline actions for quick access, modal forms for focused editing
- ✅ **Test Coverage:** Maintain TDD discipline with comprehensive tests

**Maintenance Considerations:**

- Each entity (Project/WBE/CostElement) has 3 components (Add/Edit/Delete)
- Total: 9 components × 3 entities = 9 new components (Edit + Delete only, Add exists)
- Pattern is highly consistent, making future maintenance straightforward

**Testing Challenges:**

- Backend: Need to add tests for blocked deletion (when children exist)
- Frontend: Consider adding Playwright tests for edit/delete flows (future enhancement)
- Integration: Verify query invalidation triggers proper table refreshes

**Future Extension Points:**

- Could add bulk operations (multi-select + delete)
- Could add soft delete (archive) instead of hard delete
- Could add audit trail for edit history

---

## IMPLEMENTATION PLAN

### Phase 1: Backend - Safe Delete Logic (TDD)

**1.1 Add child count validation to Projects DELETE endpoint**

- Write failing test: `test_delete_project_with_wbes_should_fail()`
- Modify `backend/app/api/routes/projects.py` delete endpoint to check for WBEs
- Return 400 error with message: "Cannot delete project with existing WBEs"
- Verify test passes

**1.2 Add child count validation to WBEs DELETE endpoint**

- Write failing test: `test_delete_wbe_with_cost_elements_should_fail()`
- Modify `backend/app/api/routes/wbes.py` delete endpoint to check for Cost Elements
- Return 400 error with message: "Cannot delete WBE with existing cost elements"
- Verify test passes

### Phase 2: Frontend - Delete Components (TDD Approach)

**2.1 Create DeleteProject component**

- Model after `DeleteUser.tsx` pattern
- Add check for child WBEs warning in dialog message
- Invalidate queries: `["projects"]`
- Add to `ProjectsTable` with inline button

**2.2 Create DeleteWBE component**

- Similar pattern to DeleteProject
- Add check for child Cost Elements warning
- Invalidate queries: `["wbes"]`
- Add to `WBEsTable` with inline button

**2.3 Create DeleteCostElement component**

- Simplest case (no children to check)
- Standard delete confirmation
- Invalidate queries: `["cost-elements"]`
- Add to `CostElementsTable` with inline button

### Phase 3: Frontend - Edit Components

**3.1 Create EditProject component**

- Model after `EditUser.tsx` and `AddProject.tsx` patterns
- Pre-populate form with existing project data
- Include all 10 fields (same as AddProject)
- Handle date fields properly (convert to string for input)
- Invalidate queries: `["projects"]` and specific project `["projects", id]`

**3.2 Create EditWBE component**

- Model after AddWBE.tsx pattern
- Pre-populate all 7 fields
- Handle optional date field for contracted_delivery_date
- Invalidate queries: `["wbes"]` and specific project's WBEs

**3.3 Create EditCostElement component**

- Model after AddCostElement.tsx pattern
- Pre-populate all 8 fields including department auto-fill logic
- Keep cost_element_type_id selector functional
- Invalidate queries: `["cost-elements"]` and specific WBE's cost elements

### Phase 4: Frontend - Table Integration

**4.1 Update ProjectsTable in projects.tsx**

- Add "Actions" column header
- Add Table.Cell with Edit and Delete buttons (inline)
- Stop row onClick navigation when clicking action buttons (e.preventDefault)
- Maintain row click-to-navigate for rest of row

**4.2 Update WBEsTable in projects.$id.tsx**

- Add "Actions" column header
- Add inline Edit and Delete buttons
- Handle onClick propagation

**4.3 Update CostElementsTable in projects.$id.wbes.$wbeId.tsx**

- Add "Actions" column header
- Add inline Edit and Delete buttons
- Handle onClick propagation

### Phase 5: Testing and Verification

**5.1 Backend Tests**

- Run existing 121 tests - ensure all pass
- Run new safe delete tests
- Verify error messages are clear

**5.2 Frontend Manual Testing**

- Test Edit flow for each entity (Project/WBE/CostElement)
- Test Delete flow with and without children
- Verify query invalidation refreshes tables
- Test validation errors display properly
- Verify toast notifications appear

**5.3 Integration Testing**

- Create Project → Edit → Delete (should work)
- Create Project → Add WBE → Try Delete Project (should fail)
- Create WBE → Add Cost Element → Try Delete WBE (should fail)
- Edit operations should preserve relationships

---

## TECHNICAL SPECIFICATIONS

### Backend API Changes

```python
# projects.py - delete_project()
# Add before session.delete(project):
wbes_count = session.exec(
    select(func.count()).select_from(WBE).where(WBE.project_id == id)
).one()
if wbes_count > 0:
    raise HTTPException(
        status_code=400,
        detail=f"Cannot delete project with {wbes_count} existing WBE(s). Delete WBEs first."
    )

# wbes.py - delete_wbe()
# Add before session.delete(wbe):
ce_count = session.exec(
    select(func.count()).select_from(CostElement).where(CostElement.wbe_id == id)
).one()
if ce_count > 0:
    raise HTTPException(
        status_code=400,
        detail=f"Cannot delete WBE with {ce_count} existing cost element(s). Delete cost elements first."
    )
```

### Frontend Component Structure

**Pattern for Edit Components:**

```typescript
interface Edit{Resource}Props {
  {resource}: {Resource}Public  // e.g., project: ProjectPublic
}

// Pre-populate defaultValues with existing data
// Use same form fields as Add{Resource}
// mutation uses {Resource}Service.update{Resource}()
// Invalidate both list and detail queries
```

**Pattern for Delete Components:**

```typescript
interface Delete{Resource}Props {
  id: string
  name: string  // For display in confirmation
  // Optional: childCount for warning message
}

// Show warning if children exist
// mutation uses {Resource}Service.delete{Resource}()
// Invalidate queries to refresh tables
```

**Pattern for Table Actions Column:**

```typescript
<Table.ColumnHeader w="xs">Actions</Table.ColumnHeader>
// In body:
<Table.Cell onClick={(e) => e.stopPropagation()}>
  <Flex gap={2}>
    <Edit{Resource} {resource}={item} />
    <Delete{Resource} id={item.id} name={item.name} />
  </Flex>
</Table.Cell>
```

---

## SUCCESS CRITERIA

1. ✅ All backend tests pass (including new safe delete tests)
2. ✅ All 3 entities (Project/WBE/CostElement) have working Edit functionality
3. ✅ All 3 entities have working Delete with proper validation
4. ✅ Delete operations properly block when children exist with clear error messages
5. ✅ Edit/Delete appear as inline actions in all 3 tables
6. ✅ Query invalidation refreshes tables after mutations
7. ✅ Toast notifications work for success and error cases
8. ✅ Form validation prevents invalid data submission
9. ✅ No compilation errors or linter warnings
10. ✅ TDD discipline maintained throughout (test-first where applicable)

---

## RISKS AND MITIGATIONS

| Risk | Impact | Mitigation |

|------|--------|------------|

| Accidental data deletion | HIGH | ✅ Safe delete checks prevent deletion with children |

| Query invalidation issues | MEDIUM | Follow established pattern, test thoroughly |

| Form validation complexity | MEDIUM | Reuse existing patterns from Add components |

| UI/UX consistency | LOW | Follow EditUser/DeleteUser patterns strictly |

| Propagation of onClick events | LOW | Use e.stopPropagation() on action buttons |

---

## DEPENDENCIES

- Backend APIs (already implemented) ✅
- OpenAPI client regeneration (if schema changes) - NOT NEEDED, schemas already support updates
- All existing Add{Resource} components ✅
- React Hook Form, TanStack Query ✅

---

## ESTIMATED EFFORT

- Backend safe delete: ~1 hour (2 tests + 2 endpoint modifications)
- Frontend Delete components: ~2 hours (3 components + table integration)
- Frontend Edit components: ~3 hours (3 complex components with pre-population)
- Table integration: ~1 hour (3 tables, stop propagation)
- Testing and verification: ~1 hour
- **Total: ~8 hours of focused development**

### To-dos

- [ ] Add safe delete validation to Projects endpoint - block deletion when WBEs exist
- [ ] Add safe delete validation to WBEs endpoint - block deletion when Cost Elements exist
- [ ] Write tests for blocked deletion scenarios (projects with WBEs, WBEs with cost elements)
- [ ] Create DeleteProject component with confirmation dialog
- [ ] Create DeleteWBE component with confirmation dialog
- [ ] Create DeleteCostElement component with confirmation dialog
- [ ] Create EditProject component - modal form with pre-populated data (10 fields)
- [ ] Create EditWBE component - modal form with pre-populated data (7 fields)
- [ ] Create EditCostElement component - modal form with pre-populated data (8 fields)
- [ ] Add Actions column to ProjectsTable with inline Edit/Delete buttons
- [ ] Add Actions column to WBEsTable with inline Edit/Delete buttons
- [ ] Add Actions column to CostElementsTable with inline Edit/Delete buttons
- [ ] Run all tests, verify CRUD operations, test edge cases (delete with children, edit validation)
