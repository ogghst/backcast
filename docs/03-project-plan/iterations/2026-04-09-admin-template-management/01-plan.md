# Plan: Admin Template Management Modal

**Created:** 2026-04-09
**Based on:** `docs/03-project-plan/iterations/2026-04-09-admin-template-management/00-analysis.md`
**Approved Option:** Option 3 (Dedicated Admin Toolbar Button + Single-View Modal)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option 3 from analysis -- Dedicated admin-only toolbar button + single-view modal
- **Architecture:** Frontend-only changes. Add a `SettingOutlined` icon button to the dashboard toolbar, gated by `<Can permission="dashboard-template-update">`. The button opens a modal with two sections: (1) Save as Template form at the top, (2) Manage Templates list at the bottom. No backend changes required.
- **Key Decisions:**
  - Admin button visible in BOTH edit and view modes (template management is orthogonal to editing)
  - Template name is LOCKED when updating an existing template (only widgets overwritten), per user's approved approach
  - "Save as New" needs only a name input (no confirmation dialog beyond modal submit)
  - "Update Existing" uses a Select dropdown; once a template is selected, the name field is disabled/display-only
  - Destructive actions (delete, overwrite) require Popconfirm before execution

### Success Criteria

**Functional Criteria:**

- [ ] AC-1: Admin users see a "Manage Templates" button (SettingOutlined icon) in the toolbar in BOTH edit and view modes VERIFIED BY: unit test rendering toolbar with mocked admin permissions
- [ ] AC-2: Non-admin users see no new button in the toolbar VERIFIED BY: unit test rendering toolbar without admin permissions
- [ ] AC-3: Clicking the admin button opens the TemplateManagementModal VERIFIED BY: unit test verifying modal visibility toggle
- [ ] AC-4: "Save as New Template" section allows entering a name and saving the current dashboard widgets as a new template via `layoutApi.create({ is_template: true })` VERIFIED BY: unit test with mocked mutation
- [ ] AC-5: When "Update Existing Template" is selected, a Select dropdown shows all existing templates, the name field becomes locked/read-only, and clicking Save overwrites the template's widgets via `layoutApi.updateTemplate()` VERIFIED BY: unit test verifying updateTemplate is called with correct args
- [ ] AC-6: "Manage Templates" section lists all templates with name and widget count, each with a delete button VERIFIED BY: unit test verifying list rendering
- [ ] AC-7: Deleting a template requires Popconfirm and calls `layoutApi.delete()` VERIFIED BY: unit test with mocked delete mutation
- [ ] AC-8: After any mutation (create/update/delete), the templates query cache is invalidated so the toolbar dropdown reflects changes VERIFIED BY: unit test verifying `queryClient.invalidateQueries` is called
- [ ] AC-9: The `layoutApi.updateTemplate()` API function calls `PUT /api/v1/dashboard-layouts/templates/{id}` (not the regular `PUT /{id}` which blocks template updates) VERIFIED BY: code inspection and unit test

**Technical Criteria:**

- [ ] AC-10: `"dashboard-template-update"` is added to the `Permission` type union in `types/auth.ts` VERIFIED BY: TypeScript compilation succeeds with the new permission used in `<Can>` component
- [ ] AC-11: All modified files pass ESLint with zero errors VERIFIED BY: `npx eslint` on changed files
- [ ] AC-12: All modified files pass TypeScript strict type checking VERIFIED BY: `npx tsc --noEmit` (or lint) on changed files
- [ ] AC-13: New test file achieves 80%+ coverage on `TemplateManagementModal.tsx` VERIFIED BY: `npm run test:coverage`

**TDD Criteria:**

- [ ] AC-14: All test specifications are written before implementation code (documented in DO phase)
- [ ] AC-15: Each test failed first before passing (documented in DO phase log)
- [ ] AC-16: Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Add `"dashboard-template-update"` to `Permission` type union in `types/auth.ts`
- Add `layoutApi.updateTemplate()` API function and `useUpdateDashboardTemplate()` mutation hook in `useDashboardLayouts.ts`
- Create new `TemplateManagementModal.tsx` component with save/update/delete operations
- Create new `TemplateManagementModal.test.tsx` with unit tests
- Modify `DashboardToolbar.tsx` to add admin button and render the modal
- Update `DashboardToolbar.test.tsx` to cover the new admin button (visible for admin, hidden for non-admin)

**Out of Scope:**

- Backend changes (all endpoints exist and are RBAC-protected)
- Template import/export functionality
- Template categories or visibility settings
- Template reordering within the management modal
- Renaming existing templates independently (name is only editable when creating new)
- Integration/E2E tests (unit tests are sufficient for this frontend-only feature)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Add `"dashboard-template-update"` to `Permission` type union | `frontend/src/types/auth.ts` | None | TypeScript compilation passes; `Can` component accepts the new permission | Low |
| 2 | Add `layoutApi.updateTemplate()` API function and `useUpdateDashboardTemplate()` mutation hook | `frontend/src/features/widgets/api/useDashboardLayouts.ts` | Task 1 | Function calls `PUT /templates/{id}`; hook invalidates template cache on settle; TypeScript clean | Low |
| 3 | Create `TemplateManagementModal` component | `frontend/src/features/widgets/components/TemplateManagementModal.tsx` | Task 2 | Renders save/update form and template list; calls correct API functions; handles loading/error states; Ant Design Modal/Form/Select/List pattern | Medium |
| 4 | Write unit tests for `TemplateManagementModal` | `frontend/src/features/widgets/components/TemplateManagementModal.test.tsx` | Task 3 (test spec) / parallel with Task 3 (TDD) | All test cases pass; 80%+ coverage | Medium |
| 5 | Add admin button and modal integration to `DashboardToolbar` | `frontend/src/features/widgets/components/DashboardToolbar.tsx` | Task 3 | Admin button visible in both modes; button gated by `<Can>`; modal opens/closes correctly | Medium |
| 6 | Update `DashboardToolbar.test.tsx` for admin button coverage | `frontend/src/features/widgets/components/DashboardToolbar.test.tsx` | Task 5 | Tests verify admin button visibility and modal trigger | Low |
| 7 | Run lint + type check on all modified files | All modified files | Tasks 1-6 | Zero ESLint errors; zero TypeScript errors | Low |

### Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: FE-001
    name: "Add dashboard-template-update permission type"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Add layoutApi.updateTemplate() and useUpdateDashboardTemplate() hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Write TemplateManagementModal test specifications (TDD RED)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-004
    name: "Implement TemplateManagementModal component (TDD GREEN)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-005
    name: "Add admin button and modal integration to DashboardToolbar"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004]

  - id: FE-006
    name: "Write DashboardToolbar admin button tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-005]

  - id: FE-007
    name: "Run lint + type check on all modified files"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006]
```

**Execution notes:** All tasks are frontend-only and sequential due to tight dependencies (each builds on the prior). FE-003 and FE-004 are the TDD RED/GREEN cycle for the modal. FE-007 is the final quality gate.

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| AC-1: Admin sees button | T-001 | `DashboardToolbar.test.tsx` | Button with "Manage templates" aria-label renders when admin permission is mocked |
| AC-2: Non-admin sees no button | T-002 | `DashboardToolbar.test.tsx` | No "Manage templates" button renders when permission is absent |
| AC-3: Modal opens on click | T-003 | `TemplateManagementModal.test.tsx` | `open=true` renders the modal title "Manage Templates" |
| AC-4: Save as new template | T-004 | `TemplateManagementModal.test.tsx` | Entering name and clicking Save calls `layoutApi.create` with `is_template: true` and current widgets |
| AC-5: Update existing template | T-005 | `TemplateManagementModal.test.tsx` | Selecting existing template locks name, clicking Save calls `layoutApi.updateTemplate` with template ID and widgets |
| AC-6: Template list renders | T-006 | `TemplateManagementModal.test.tsx` | Each template shows name and widget count |
| AC-7: Delete with confirm | T-007 | `TemplateManagementModal.test.tsx` | Delete button triggers Popconfirm; confirming calls `layoutApi.delete` with template ID |
| AC-8: Cache invalidation | T-008 | `TemplateManagementModal.test.tsx` | After create/update/delete, `queryClient.invalidateQueries` is called with template query key |
| AC-9: Correct API endpoint | T-009 | `TemplateManagementModal.test.tsx` | `layoutApi.updateTemplate` calls `PUT /dashboard-layouts/templates/{id}` (verified via mock assertion) |

---

## Test Specification

### Test Hierarchy

```
frontend/src/features/widgets/
  TemplateManagementModal.test.tsx
  ├── Rendering tests
  │   ├── Modal renders when open=true
  │   ├── Modal does not render when open=false
  │   ├── Template list renders with name + widget count
  │   └── Empty state when no templates exist
  ├── Save as New Template tests
  │   ├── Name input is visible when "New template" is selected
  │   ├── Save calls create mutation with correct payload
  │   ├── Save shows loading state during mutation
  │   └── Save requires non-empty name
  ├── Update Existing Template tests
  │   ├── Select dropdown shows existing templates
  │   ├── Name field is locked when existing template selected
  │   ├── Update calls updateTemplate mutation with correct ID and widgets
  │   └── Update shows success message
  ├── Delete Template tests
  │   ├── Delete button renders per template
  │   ├── Popconfirm appears on delete click
  │   └── Confirming delete calls delete mutation
  └── Cache invalidation tests
      ├── Create invalidates template cache
      ├── Update invalidates template cache
      └── Delete invalidates template cache

  DashboardToolbar.test.tsx (updated)
  ├── Admin button rendering
  │   ├── Button visible when user has dashboard-template-update permission
  │   └── Button hidden when user lacks dashboard-template-update permission
  ├── Button present in both edit and view mode
  └── Clicking button opens TemplateManagementModal
```

### Test Cases (first 10)

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_toolbar_renders_admin_button_when_permission_granted` | AC-1 | Unit | Button with admin aria-label is in the document |
| T-002 | `test_toolbar_hides_admin_button_when_permission_absent` | AC-2 | Unit | No admin button in the document |
| T-003 | `test_modal_renders_when_open_true` | AC-3 | Unit | Modal title "Manage Templates" is visible |
| T-004 | `test_save_new_template_calls_create_mutation` | AC-4 | Unit | `layoutApi.create` called with `{ name, is_template: true, widgets: currentWidgets }` |
| T-005 | `test_update_existing_template_calls_update_template_api` | AC-5 | Unit | `layoutApi.updateTemplate` called with `{ id, data: { widgets } }` |
| T-006 | `test_template_list_renders_name_and_widget_count` | AC-6 | Unit | Each template name and "(N)" widget count rendered |
| T-007 | `test_delete_template_calls_delete_mutation_after_confirm` | AC-7 | Unit | `layoutApi.delete` called with template ID after Popconfirm confirm |
| T-008 | `test_create_invalidates_template_cache` | AC-8 | Unit | `queryClient.invalidateQueries` called with dashboard-layouts key |
| T-009 | `test_update_template_uses_correct_endpoint` | AC-9 | Unit | API function URL matches `/api/v1/dashboard-layouts/templates/{id}` |
| T-010 | `test_name_field_locked_when_existing_template_selected` | AC-5 | Unit | Name input is disabled after selecting from dropdown |

### Test Infrastructure Needs

- **Fixtures needed:**
  - Mock template data (array of `DashboardLayoutRead` objects with `is_template: true`)
  - Mock dashboard state with widget instances (from `useDashboardCompositionStore`)
  - Mock auth state with/without `dashboard-template-update` permission (from `useAuthStore`)
- **Mocks/stubs:**
  - `@/features/widgets/api/useDashboardLayouts` -- mock `useDashboardLayoutTemplates`, `useCreateDashboardLayout`, `useDeleteDashboardLayout`, `useUpdateDashboardTemplate`
  - `@/stores/useDashboardCompositionStore` -- mock `activeDashboard` with known widgets
  - `@/stores/useAuthStore` -- mock `hasPermission` to return true/false for admin gating
  - `@/components/auth/Can` -- or mock the auth store so `Can` works naturally
  - `antd` -- mock `message.useMessage()` for success/error callbacks (follow existing DashboardToolbar test pattern)
- **Database state:** None required (frontend unit tests only)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | `layoutApi.updateTemplate` calls wrong endpoint URL (`PUT /{id}` instead of `PUT /templates/{id}`), causing 403 or "Cannot modify template" error | Low | High | T-009 explicitly verifies the URL path; code review of API function |
| Technical | `<Can>` component does not recognize the new permission string because TypeScript type union is stale | Low | Medium | Task 1 adds the type first; `hasPermission` already accepts `string` so runtime works even if type is missed |
| Integration | Cache invalidation misses cause stale template list in toolbar dropdown after mutations | Low | Medium | T-008 verifies invalidation; all mutation hooks follow existing `onSettled` pattern with `queryKeys.dashboardLayouts.all` |
| UX | Modal form state does not reset correctly between opens (stale name, wrong template selection) | Medium | Low | Use `destroyOnHidden` on Modal (follows DepartmentModal pattern); useEffect to reset form on `open` change |
| Technical | `useDashboardCompositionStore.getState().activeDashboard` is null when modal opens (no dashboard loaded) | Medium | Low | Guard with null check; disable Save button when no active dashboard or no widgets |

---

## Documentation References

### Required Reading

- Analysis document: `docs/03-project-plan/iterations/2026-04-09-admin-template-management/00-analysis.md`
- Permission gating pattern: `frontend/src/components/auth/Can.tsx`
- Modal pattern reference: `frontend/src/features/departments/components/DepartmentModal.tsx`
- Existing API hooks: `frontend/src/features/widgets/api/useDashboardLayouts.ts`

### Code References

- Backend template update endpoint: `backend/app/api/routes/dashboard_layouts.py` (line 188-214)
- Backend RBAC config: `backend/config/rbac.json` (line 62: `"dashboard-template-update"`)
- Dashboard composition store: `frontend/src/stores/useDashboardCompositionStore.ts`
- Existing toolbar tests: `frontend/src/features/widgets/components/DashboardToolbar.test.tsx`
- Query keys: `frontend/src/api/queryKeys.ts` (line 280-289: `dashboardLayouts`)

---

## Prerequisites

### Technical

- [x] Backend endpoints exist and are RBAC-protected (no changes needed)
- [x] Frontend dependencies installed (Ant Design, TanStack Query already in use)
- [x] Existing `layoutApi` object and mutation hooks provide the pattern to follow

### Documentation

- [x] Analysis phase approved (Option 3 selected)
- [x] Architecture docs reviewed (RBAC pattern, Modal pattern, Mutation pattern)
- [x] Existing test patterns understood (DashboardToolbar.test.tsx structure)
