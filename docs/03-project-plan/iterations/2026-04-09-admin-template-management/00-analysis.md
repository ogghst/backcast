# Analysis: Admin Template Management Modal

**Created:** 2026-04-09
**Request:** An admin role user shall have an additional option to save the current dashboard as a new or existing template, and to delete templates, via a modal panel accessible from the dashboard toolbar.

---

## Clarified Requirements

### Functional Requirements

- FR-1: Admin users see a "Manage Templates" action accessible from the dashboard toolbar
- FR-2: A modal panel opens allowing three operations:
  - FR-2a: **Save current dashboard as new template** -- user provides a name, the current widget layout is saved as a new system template
  - FR-2b: **Update existing template** -- user selects a template from the list, its widgets are overwritten with the current dashboard widgets
  - FR-2c: **Delete template** -- user selects a template from the list and confirms deletion
- FR-3: Only users with `dashboard-template-update` permission (admin role) can access this functionality
- FR-4: Regular (non-admin) users see no change to their existing template dropdown or toolbar
- FR-5: After save/update, the template list in the existing dropdown refreshes to reflect changes

### Non-Functional Requirements

- NFR-1: Modal follows the established Ant Design Modal pattern (see `DepartmentModal.tsx`)
- NFR-2: Permission gating uses the existing `<Can>` component or `usePermission` hook
- NFR-3: All mutations invalidate the relevant TanStack Query caches
- NFR-4: Destructive actions (delete, overwrite) require confirmation dialogs

### Constraints

- No backend changes required -- all endpoints exist and are RBAC-protected
- The `"dashboard-template-update"` permission must be added to the frontend `Permission` type union
- The admin template update uses `PUT /templates/{layout_id}` (not the regular `PUT /{layout_id}` which blocks template updates)
- Template deletion reuses the existing `DELETE /{layout_id}` endpoint (ownership-based: seeded templates are owned by admin user)
- Integration point is `DashboardToolbar.tsx` -- the modal trigger must live there

---

## Context Discovery

### Product Scope

- Widget dashboard system supports system templates (admin-managed) and user dashboards
- Templates are seeded on application startup and owned by the admin user (`admin@backcast.org`)
- Templates provide starting layouts users can clone via the "Apply Template" action

### Architecture Context

- **RBAC pattern**: `useAuthStore` provides `hasRole()` and `hasPermission()`. The `<Can>` component gates rendering. The `usePermission` hook provides imperative checks.
- **Modal pattern**: Ant Design `Modal` with `Form.useForm()`, controlled via `open`/`onCancel`/`onOk` props, `destroyOnHidden` for cleanup. See `DepartmentModal.tsx` as reference.
- **Mutation pattern**: TanStack Query mutations with `queryClient.invalidateQueries()` in `onSettled`. Existing hooks in `useDashboardLayouts.ts` follow this pattern.
- **State**: Dashboard composition lives in `useDashboardCompositionStore` (Zustand). Widget data is serialized via `WidgetConfig[]` type.

### Codebase Analysis

**Backend (no changes needed):**

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `POST /api/v1/dashboard-layouts` | Create | Any user | `is_template=true` creates a template |
| `PUT /templates/{layout_id}` | Update template | `dashboard-template-update` permission | Admin-only, no ownership check in service |
| `DELETE /{layout_id}` | Delete | Owner-scoped | Admin owns seeded templates, so works |
| `GET /templates` | List | Any user | Returns all templates |

**Frontend (changes needed):**

| File | Change |
|---|---|
| `frontend/src/types/auth.ts` | Add `"dashboard-template-update"` to `Permission` type union |
| `frontend/src/features/widgets/components/DashboardToolbar.tsx` | Add admin trigger button/item, render modal, pass current widgets |
| New: `frontend/src/features/widgets/components/TemplateManagementModal.tsx` | New modal component with three operations |
| `frontend/src/features/widgets/api/useDashboardLayouts.ts` | Add `layoutApi.updateTemplate()` function for the admin-specific `PUT /templates/{id}` endpoint; may add `useUpdateTemplateMutation` hook |

**Existing hooks that can be reused directly:**
- `useDashboardLayoutTemplates` -- lists all templates (already used in toolbar)
- `useCreateDashboardLayout` -- create with `is_template: true`
- `useDeleteDashboardLayout` -- delete by ID
- `layoutApi.update()` -- exists but calls `PUT /{id}` which blocks templates. Need new `layoutApi.updateTemplate()` calling `PUT /templates/{id}`

**Key architectural note:** The regular `PUT /{layout_id}` endpoint explicitly blocks template updates (service raises `ValueError("Cannot modify a template layout")`). The admin-specific `PUT /templates/{layout_id}` bypasses this check. The frontend API layer currently only has `layoutApi.update()` pointing to the regular endpoint, so a new API function is needed for template updates.

---

## Solution Options

### Option 1: Single Modal with Tabbed Interface

**Architecture & Design:**

A single modal with two Ant Design `Tabs`: "Save as Template" and "Manage Templates". The first tab handles creating new templates and updating existing ones. The second tab shows a list of all templates with delete actions.

**UX Design:**

- Admin sees a "Manage Templates" item at the bottom of the existing template dropdown (or as a separate toolbar button with a SettingOutlined icon)
- Clicking it opens the modal
- Tab 1 "Save as Template":
  - Text input for template name
  - Option A: "Create New" radio -- saves with the entered name
  - Option B: "Update Existing" radio -- shows a Select dropdown of existing templates, name field pre-fills but remains editable
  - Save button
- Tab 2 "Manage Templates":
  - Table/list of all templates with name, widget count, last updated
  - Delete button per row with Popconfirm
- Cancel/Close button

**Implementation:**

- New file: `TemplateManagementModal.tsx`
- Modify: `DashboardToolbar.tsx` to add trigger and render modal
- Modify: `useDashboardLayouts.ts` to add `layoutApi.updateTemplate()`
- Modify: `types/auth.ts` to add permission string
- The modal reads current widgets from `useDashboardCompositionStore.getState().activeDashboard`

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Single entry point for all template management; clean separation via tabs; familiar UX pattern |
| Cons            | Two-tab modal is slightly heavier; more component code in a single file |
| Complexity      | Medium                     |
| Maintainability | Good                       |
| Performance     | No concerns                |

---

### Option 2: Extended Template Dropdown with Inline Actions

**Architecture & Design:**

Extend the existing template dropdown in the toolbar with an admin section. The dropdown gains a divider and an "Admin: Manage Templates" item that opens a lightweight drawer/modal. Additionally, each template in the "System Templates" group gets inline edit/delete icons (visible only to admins).

**UX Design:**

- No new toolbar button needed
- Existing dropdown gains:
  - Inline delete icon (red) next to each system template name (admin only)
  - A divider and "Save as Template..." item at the bottom (admin only)
- "Save as Template..." opens a small modal with:
  - Name input
  - "Save as New" / "Update Existing" toggle (if update, shows Select)
  - Save/Cancel buttons

**Implementation:**

- Same new files and modifications as Option 1, but the modal is simpler (no tab management)
- More logic in `DashboardToolbar.tsx` for inline delete actions in the dropdown menu items
- Admin-only items conditionally rendered via `<Can>` component wrapping individual menu items

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | No new toolbar button; actions are contextual to where templates already appear; lighter modal |
| Cons            | Dropdown becomes more complex; mixing navigation (apply template) with management (delete template) in same UI; dropdown menu items are limited in space for confirmation UX |
| Complexity      | Medium                     |
| Maintainability | Fair -- concerns mixing concerns in one dropdown |
| Performance     | No concerns                |

---

### Option 3: Dedicated Admin Toolbar Button + Minimal Modal

**Architecture & Design:**

Add a dedicated "Manage Templates" button (icon-only, SettingOutlined) to the toolbar, visible only to admins. Clicking it opens a modal with a single cohesive view: a list of existing templates at the top, a "Save Current as Template" form section at the bottom.

**UX Design:**

- New icon-only button in toolbar (after the Templates dropdown button), gated by `<Can permission="dashboard-template-update">`
- Button visible in both edit and view modes (template management is orthogonal to editing)
- Modal layout:
  - Top section: scrollable list of templates with name, widget count, delete button
  - Bottom section: divider, then "Save Current Dashboard as Template" form with name input and "Save as New" / select existing + "Update" buttons
- No tabs -- single scrollable view

**Implementation:**

- Same file changes as other options
- Modal is a single component with list + form sections
- Simpler state management (no active tab)
- Button placement: between Templates dropdown and the Reset/Customize buttons in view mode, or between Templates and Add Widget in edit mode

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Clear admin-only affordance via dedicated button; single-view modal is simpler; no tabs; template management is independent of edit mode |
| Cons            | Adds a new button to toolbar (slight visual increase); button always visible to admins even when not needed |
| Complexity      | Low-Medium                 |
| Maintainability | Good -- clean separation of concerns |
| Performance     | No concerns                |

---

## Comparison Summary

| Criteria           | Option 1 (Tabbed Modal)  | Option 2 (Inline Dropdown) | Option 3 (Dedicated Button) |
| ------------------ | ------------------------ | -------------------------- | --------------------------- |
| Development Effort | Medium (new modal + tabs) | Medium (dropdown refactor + small modal) | Low-Medium (new modal, no tabs) |
| UX Quality         | Good (clear sections)    | Fair (cluttered dropdown)  | Good (clear affordance)     |
| Flexibility        | Good (tabs scale well)   | Fair (dropdown constrained)| Good (modal extensible)     |
| Best For           | Feature-rich management  | Quick inline actions       | Clean admin workflow         |
| Toolbar Impact     | None or +1 button        | None (extend existing)     | +1 admin-only button        |

---

## Recommendation

**I recommend Option 3 (Dedicated Admin Toolbar Button + Minimal Modal) because:**

1. **Clean separation**: Template management is a distinct admin concern and deserves its own entry point, rather than being crammed into the existing template dropdown or requiring tab navigation.
2. **Low complexity**: A single-view modal (list + form) is simpler to build, test, and maintain than a tabbed interface. No tab state management needed.
3. **Edit-mode independence**: Template management is orthogonal to dashboard editing. Admins should be able to save/update templates regardless of whether they are in edit mode or view mode. A dedicated toolbar button supports this naturally.
4. **Established patterns**: The dedicated button gated by `<Can permission="dashboard-template-update">` follows the exact same RBAC pattern used throughout the admin pages (see `DepartmentManagement.tsx` which wraps create/delete actions in `<Can>` blocks).
5. **Minimal backend impact**: Zero backend changes required. The only API-layer addition is `layoutApi.updateTemplate()` for the admin-specific `PUT /templates/{id}` endpoint.

**Alternative consideration:** Choose Option 1 (Tabbed Modal) if you anticipate template management growing significantly in the future (e.g., template categories, visibility settings, import/export). The tab structure provides more room for expansion.

---

## Decision Questions

1. **Trigger location**: Should the admin button appear in both edit and view modes, or only in view mode? (Recommendation: both modes, since saving a template from the current dashboard is useful at any time.)

2. **Update behavior**: When updating an existing template, should the name be editable or locked to the original? (Recommendation: editable -- admins may want to rename during update.)

3. **Confirmation on save**: Should "Save as New Template" require confirmation, or is the name input sufficient? (Recommendation: no extra confirmation for save, but yes for update and delete since they are destructive.)

---

## References

- `frontend/src/features/widgets/components/DashboardToolbar.tsx` -- integration point
- `frontend/src/features/widgets/api/useDashboardLayouts.ts` -- API hooks (needs `updateTemplate`)
- `frontend/src/stores/useDashboardCompositionStore.ts` -- widget state source
- `frontend/src/components/auth/Can.tsx` -- permission gating component
- `frontend/src/hooks/usePermission.ts` -- imperative permission hook
- `frontend/src/types/auth.ts` -- Permission type (needs `"dashboard-template-update"`)
- `frontend/src/features/departments/components/DepartmentModal.tsx` -- modal pattern reference
- `backend/app/api/routes/dashboard_layouts.py` -- backend routes (no changes)
- `backend/app/services/dashboard_layout_service.py` -- service methods (no changes)
- `backend/config/rbac.json` -- RBAC configuration (no changes)
