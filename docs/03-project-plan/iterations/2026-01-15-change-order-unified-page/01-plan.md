# Plan: Unified Change Order Page (Single-Page Layout)

**Created:** 2026-01-15
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 - Single-Page Scroll Layout

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 - Single-Page Scroll Layout
- **Architecture**: Single page component with collapsible sections (Form, Workflow, Impact) rendered sequentially. Anchor navigation for quick jumps between sections.
- **Key Decisions**:
  - No tab-based routing (simpler URL structure)
  - All sections load on page render (no lazy-loading)
  - Sticky sub-navigation with anchor links
  - Collapsible section headers for content organization
  - Form state persists when scrolling between sections

### Success Criteria

**Functional Criteria:**

- User can create new change order from `/projects/:projectId/change-orders/new` URL VERIFIED BY: E2E test
- User can edit existing change order from `/projects/:projectId/change-orders/:changeOrderId` URL VERIFIED BY: E2E test
- Form section displays all editable fields (code, title, description, justification, effective_date, status) VERIFIED BY: Integration test
- Workflow section displays stepper, action buttons, and status guidance VERIFIED BY: Unit test
- Impact section displays KPI cards, waterfall chart, and entity changes VERIFIED BY: Integration test
- Branch lock indicator shows when branch is locked VERIFIED BY: Unit test
- Form becomes read-only when branch is locked VERIFIED BY: Unit test
- Unsaved changes prompt appears when navigating away with dirty form VERIFIED BY: E2E test
- Create mode hides workflow and impact sections VERIFIED BY: Unit test
- Draft status shows workflow action buttons (Submit, Delete) VERIFIED BY: Unit test
- Submitted status shows approve/reject buttons VERIFIED BY: Unit test

**Technical Criteria:**

- Page load time < 2 seconds VERIFIED BY: Browser DevTools measurement
- TypeScript strict mode, zero `any` types VERIFIED BY: `tsc --noEmit`
- ESLint zero errors VERIFIED BY: `npm run lint`
- Test coverage ≥80% VERIFIED BY: `npm run test:coverage`
- No console errors or warnings VERIFIED BY: Browser console inspection
- Responsive layout on mobile (320px - 768px) VERIFIED BY: Visual regression test

**Business Criteria:**

- Single page view shows all relevant change order information VERIFIED BY: User acceptance testing
- Reduced navigation steps (from 3 clicks to 1) to view full CO details VERIFIED BY: Task analysis measurement

**TDD Criteria:**

- [ ] All tests written **before** implementation code VERIFIED BY: Git commit history
- [ ] Tests validate **all acceptance criteria** VERIFIED BY: Test-to-requirement traceability matrix
- [ ] Each test **failed first** (RED phase) VERIFIED BY: Do-prompt daily log
- [ ] Test coverage ≥80% VERIFIED BY: `vitest run --coverage` report
- [ ] Tests follow Arrange-Act-Assert pattern VERIFIED BY: Code review
- [ ] Fixtures used for shared test setup VERIFIED BY: Reference to test setup files

### Scope Boundaries

**In Scope:**

- Single page component for change order create/edit/view
- Collapsible sections: Form, Workflow, Impact Analysis
- Sticky sub-navigation with anchor links
- Form state management with dirty tracking
- Integration with existing workflow and impact components
- Routing for create (`/new`) and edit (`/:changeOrderId`) modes
- Responsive design for mobile devices
- Tests: Unit, Integration, E2E

**Out of Scope:**

- Backend API changes (use existing endpoints)
- History drawer (keep existing modal trigger)
- Version history display (keep separate)
- Isolated vs. Merged view toggle (deferred to future iteration)
- Real-time collaboration features
- Offline mode
- Print/export functionality

**Assumptions:**

- Existing API endpoints provide all required data
- User has appropriate permissions for change order operations
- Impact analysis data is available for non-Draft change orders

---

## Work Decomposition

### Task Breakdown

| Task | Description | Files | Dependencies | Success | Est. Complexity |
| ---- | ----------- | ------ | ------------- | -------- | --------------- |
| 1 | Create page component structure and routing | `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx`, `frontend/src/routes/index.tsx` | None | Page renders at `/new` and `/:id` routes | Low |
| 2 | Create form section component (extract from modal) | `frontend/src/features/change-orders/components/ChangeOrderFormSection.tsx` | Task 1 | Form renders all fields, validates input | Medium |
| 3 | Create workflow section component | `frontend/src/features/change-orders/components/ChangeOrderWorkflowSection.tsx` | Task 1 | Workflow stepper and buttons render | Low |
| 4 | Create impact section component (embed dashboard) | `frontend/src/features/change-orders/components/ChangeOrderImpactSection.tsx` | Task 1 | Impact charts render with data | Medium |
| 5 | Implement sticky sub-navigation with anchors | `frontend/src/features/change-orders/components/ChangeOrderPageNav.tsx` | Task 1 | Anchor links scroll to sections | Low |
| 6 | Implement collapsible section headers | Modify section components | Task 2-4 | Sections collapse/expand on click | Low |
| 7 | Implement form dirty tracking and navigation prompt | `frontend/src/hooks/useFormDirty.ts`, page component | Task 2 | Unsaved changes prompt appears | Medium |
| 8 | Update ChangeOrderList to navigate to detail page | `frontend/src/features/change-orders/components/ChangeOrderList.tsx` | Task 1 | Row click navigates to detail page | Low |
| 9 | Handle create mode (hide workflow/impact) | Page component | Task 1,2,3,4 | Create mode shows form only | Low |
| 10 | Implement branch lock state handling | Form and workflow sections | Task 2,3 | Locked branch shows read-only form | Medium |

### Test-First Task Detail

```text
├── Task 1: Create page component structure and routing
│   ├── Test-First Subtask 1.1: Write routing test
│   │   ├── File: frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.test.tsx
│   │   ├── Success: Test verifies routes render correct component
│   │   └── Prerequisite: Test infrastructure setup
│   ├── Implementation Subtask 1.2: Implement page component and routes
│   │   ├── Files: ChangeOrderUnifiedPage.tsx, routes/index.tsx
│   │   ├── Dependencies: Test 1.1 written and failing
│   │   ├── Success: Test 1.1 passes, component renders
│   │   └── Refactor: Extract layout logic if needed
│   └── Estimated: Low
│
├── Task 2: Create form section component
│   ├── Test-First Subtask 2.1: Write form component tests
│   │   ├── File: ChangeOrderFormSection.test.tsx
│   │   ├── Success: Tests verify form rendering, validation, submission
│   │   └── Prerequisite: Mock form data
│   ├── Implementation Subtask 2.2: Implement form section
│   │   ├── Files: ChangeOrderFormSection.tsx
│   │   ├── Dependencies: Test 2.1 written and failing
│   │   ├── Success: Test 2.1 passes, form works
│   │   └── Refactor: Extract validation logic
│   └── Estimated: Medium
│
├── Task 3: Create workflow section component
│   ├── Test-First Subtask 3.1: Write workflow component tests
│   │   ├── File: ChangeOrderWorkflowSection.test.tsx
│   │   ├── Success: Tests verify stepper and buttons render
│   │   └── Prerequisite: Mock change order data
│   ├── Implementation Subtask 3.2: Implement workflow section
│   │   ├── Files: ChangeOrderWorkflowSection.tsx
│   │   ├── Dependencies: Test 3.1 written and failing
│   │   ├── Success: Test 3.1 passes, workflow displays
│   │   └── Refactor: Extract action button logic
│   └── Estimated: Low
│
├── Task 4: Create impact section component
│   ├── Test-First Subtask 4.1: Write impact component tests
│   │   ├── File: ChangeOrderImpactSection.test.tsx
│   │   ├── Success: Tests verify charts render with data
│   │   └── Prerequisite: Mock impact data
│   ├── Implementation Subtask 4.2: Implement impact section
│   │   ├── Files: ChangeOrderImpactSection.tsx
│   │   ├── Dependencies: Test 4.1 written and failing
│   │   ├── Success: Test 4.1 passes, impact displays
│   │   └── Refactor: Extract chart component logic
│   └── Estimated: Medium
│
├── Task 5: Implement sticky sub-navigation
│   ├── Test-First Subtask 5.1: Write navigation component tests
│   │   ├── File: ChangeOrderPageNav.test.tsx
│   │   ├── Success: Tests verify anchor links work
│   │   └── Prerequisite: Test scrolling behavior
│   ├── Implementation Subtask 5.2: Implement navigation
│   │   ├── Files: ChangeOrderPageNav.tsx
│   │   ├── Dependencies: Test 5.1 written and failing
│   │   ├── Success: Test 5.1 passes, anchors scroll
│   │   └── Refactor: Extract scroll handler
│   └── Estimated: Low
│
├── Task 6: Implement collapsible sections
│   ├── Test-First Subtask 6.1: Write collapse tests
│   │   ├── Files: Section component tests
│   │   ├── Success: Tests verify toggle behavior
│   │   └── Prerequisite: Section components exist
│   ├── Implementation Subtask 6.2: Implement collapse
│   │   ├── Files: Modify section components
│   │   ├── Dependencies: Test 6.1 written and failing
│   │   ├── Success: Test 6.1 passes, sections collapse
│   │   └── Refactor: Extract collapse hook
│   └── Estimated: Low
│
├── Task 7: Implement form dirty tracking
│   ├── Test-First Subtask 7.1: Write dirty tracking tests
│   │   ├── File: hooks/useFormDirty.test.ts
│   │   ├── Success: Tests verify dirty state tracking
│   │   └── Prerequisite: Mock form instance
│   ├── Implementation Subtask 7.2: Implement dirty tracking
│   │   ├── Files: hooks/useFormDirty.ts
│   │   ├── Dependencies: Test 7.1 written and failing
│   │   ├── Success: Test 7.1 passes, dirty tracking works
│   │   └── Refactor: Optimize re-renders
│   └── Estimated: Medium
│
├── Task 8: Update ChangeOrderList navigation
│   ├── Test-First Subtask 8.1: Write navigation tests
│   │   ├── File: ChangeOrderList.test.tsx (modify)
│   │   ├── Success: Tests verify navigation to detail page
│   │   └── Prerequisite: Routes exist
│   ├── Implementation Subtask 8.2: Update list component
│   │   ├── Files: ChangeOrderList.tsx
│   │   ├── Dependencies: Test 8.1 written and failing
│   │   ├── Success: Test 8.1 passes, navigation works
│   │   └── Refactor: Extract navigation handler
│   └── Estimated: Low
│
├── Task 9: Handle create mode
│   ├── Test-First Subtask 9.1: Write create mode tests
│   │   ├── File: ChangeOrderUnifiedPage.test.tsx (extend)
│   │   ├── Success: Tests verify create mode hides sections
│   │   └── Prerequisite: Page component exists
│   ├── Implementation Subtask 9.2: Implement create mode logic
│   │   ├── Files: ChangeOrderUnifiedPage.tsx
│   │   ├── Dependencies: Test 9.1 written and failing
│   │   ├── Success: Test 9.1 passes, create mode works
│   │   └── Refactor: Extract mode detection logic
│   └── Estimated: Low
│
├── Task 10: Handle branch lock state
│   ├── Test-First Subtask 10.1: Write lock state tests
│   │   ├── Files: Form and workflow section tests
│   │   ├── Success: Tests verify lock state behavior
│   │   └── Prerequisite: Mock locked change order
│   ├── Implementation Subtask 10.2: Implement lock state handling
│   │   ├── Files: Section components
│   │   ├── Dependencies: Test 10.1 written and failing
│   │   ├── Success: Test 10.1 passes, lock state works
│   │   └── Refactor: Extract lock state hook
│   └── Estimated: Medium
```

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| -------------------- | ------- | --------- | ----------------- |
| User can create new change order from `/new` URL | T-001 | ChangeOrderUnifiedPage.test.tsx | Page renders in create mode |
| User can edit existing change order from `/:id` URL | T-002 | ChangeOrderUnifiedPage.test.tsx | Page renders in edit mode with data |
| Form section displays all editable fields | T-003 | ChangeOrderFormSection.test.tsx | All form fields render correctly |
| Workflow section displays stepper and buttons | T-004 | ChangeOrderWorkflowSection.test.tsx | Stepper and buttons render |
| Impact section displays KPI cards and charts | T-005 | ChangeOrderImpactSection.test.tsx | Impact data renders in charts |
| Branch lock indicator shows when locked | T-006 | ChangeOrderWorkflowSection.test.tsx | Lock indicator visible |
| Form becomes read-only when branch locked | T-007 | ChangeOrderFormSection.test.tsx | Form fields disabled |
| Unsaved changes prompt appears | T-008 | useFormDirty.test.tsx, E2E | Prompt shows on navigation with dirty form |
| Create mode hides workflow and impact | T-009 | ChangeOrderUnifiedPage.test.tsx | Only form section visible |
| Draft status shows Submit/Delete buttons | T-010 | ChangeOrderWorkflowSection.test.tsx | Correct buttons for Draft status |
| Submitted status shows Approve/Reject buttons | T-011 | ChangeOrderWorkflowSection.test.tsx | Correct buttons for Submitted status |
| Anchor links scroll to sections | T-012 | ChangeOrderPageNav.test.tsx | Click scrolls to target section |
| Sections collapse on header click | T-013 | Section component tests | Content toggles visibility |
| Page load time < 2 seconds | T-014 | Performance test | Load time measured |
| Mobile responsive layout | T-015 | Visual regression test | Layout at 320px-768px |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (write first - drive interface design)
│   ├── Component Tests
│   │   ├── ChangeOrderUnifiedPage.test.tsx - Page routing and layout
│   │   ├── ChangeOrderFormSection.test.tsx - Form rendering and validation
│   │   ├── ChangeOrderWorkflowSection.test.tsx - Workflow display
│   │   ├── ChangeOrderImpactSection.test.tsx - Impact chart rendering
│   │   ├── ChangeOrderPageNav.test.tsx - Anchor navigation
│   │   └── CollapsibleSection.test.tsx - Collapse behavior
│   ├── Hook Tests
│   │   ├── useFormDirty.test.ts - Form dirty tracking
│   │   └── useChangeOrderMode.test.ts - Create/edit mode detection
│   └── Happy path, edge cases, error handling for each
│
├── Integration Tests (write after unit tests pass)
│   ├── ChangeOrderUnifiedPage.integration.test.tsx
│   │   ├── Full page render with data
│   │   ├── Form submission workflow
│   │   ├── Workflow action integration
│   │   └── Impact data loading
│   └── Navigation integration
│
└── End-to-End Tests (write last - critical flows)
    └── change-order-unified-page.spec.ts (Playwright)
        ├── Create new change order flow
        ├── Edit existing change order flow
        ├── View workflow and impact sections
        ├── Branch lock state behavior
        └── Unsaved changes prompt
```

### Test Cases

| Test ID | Test Name | Acceptance Criterion | Type | Verification |
| ------- | --------- | -------------------- | ---- | ------------ |
| T-001 | test_unified_page_renders_in_create_mode_at_new_route | User can create new change order from `/new` URL | Unit | Component renders, mode is create |
| T-002 | test_unified_page_renders_in_edit_mode_with_id_route | User can edit existing change order from `/:id` URL | Unit | Component renders, data loaded |
| T-003 | test_form_section_renders_all_editable_fields | Form section displays all editable fields | Unit | All fields present and correct |
| T-004 | test_form_section_validates_required_fields | Form validation works | Unit | Required field validation triggers |
| T-005 | test_form_section_submits_on_save | Form submission works | Unit | Submit callback called with data |
| T-006 | test_workflow_section_renders_stepper | Workflow section displays stepper | Unit | Stepper component renders |
| T-007 | test_workflow_section_renders_action_buttons | Workflow section displays action buttons | Unit | Buttons render for status |
| T-008 | test_workflow_section_shows_lock_indicator_when_locked | Branch lock indicator shows when locked | Unit | Lock indicator visible |
| T-009 | test_form_section_read_only_when_branch_locked | Form becomes read-only when branch locked | Unit | Fields disabled when locked |
| T-010 | test_form_section_disabled_fields_when_locked | Locked branch disables form fields | Unit | Disabled attribute on inputs |
| T-011 | test_impact_section_renders_kpi_cards | Impact section displays KPI cards | Unit | KPICards component renders |
| T-012 | test_impact_section_renders_waterfall_chart | Impact section displays waterfall chart | Unit | WaterfallChart component renders |
| T-013 | test_impact_section_shows_loading_state | Impact section loading state | Unit | Spinner shows when loading |
| T-014 | test_impact_section_handles_error_state | Impact section error handling | Unit | Error message displays |
| T-015 | test_page_nav_renders_anchor_links | Sticky sub-navigation renders | Unit | Anchor links present |
| T-016 | test_page_nav_scrolls_to_section_on_click | Anchor links scroll to sections | Unit | Scroll handler called |
| T-017 | test_collapsible_section_toggles_on_header_click | Sections collapse on header click | Unit | Content visibility toggles |
| T-018 | test_collapsible_section_expands_by_default | Sections expanded by default | Unit | Content visible initially |
| T-019 | test_use_form_dirty_tracks_changes | Form dirty tracking works | Unit | Dirty state updates on change |
| T-020 | test_use_form_dirty_resets_on_submit | Dirty state resets on submit | Unit | Dirty false after submit |
| T-021 | test_create_mode_hides_workflow_and_impact_sections | Create mode hides workflow and impact | Unit | Only form section visible |
| T-022 | test_draft_status_shows_submit_and_delete_buttons | Draft status shows Submit/Delete buttons | Unit | Correct buttons for Draft |
| T-023 | test_submitted_status_shows_approve_and_reject_buttons | Submitted status shows Approve/Reject buttons | Unit | Correct buttons for Submitted |
| T-024 | test_unified_page_loads_change_order_data | Page loads CO data on mount | Integration | API called, data rendered |
| T-025 | test_unified_page_handles_load_error | Page handles load error | Integration | Error state displayed |
| T-026 | test_unified_page_refreshes_after_workflow_action | Page refreshes after action | Integration | Data refetched after action |
| T-027 | test_navigation_list_to_detail | List navigates to detail page | E2E | Click navigates, detail page loads |
| T-028 | test_create_change_order_flow | Create new CO flow | E2E | Navigate, fill form, save, verify |
| T-029 | test_edit_change_order_flow | Edit CO flow | E2E | Navigate, edit, save, verify |
| T-030 | test_unsaved_changes_prompt_on_navigation | Unsaved changes prompt | E2E | Edit form, navigate, prompt shows |

### Test Infrastructure

**Framework**: Vitest for unit/integration, Playwright for E2E

**Required Fixtures** (create new):

```typescript
// frontend/src/test/fixtures/changeOrders.ts
export const mockChangeOrder: ChangeOrderPublic = {
  change_order_id: "test-co-id",
  code: "CO-2026-001",
  title: "Test Change Order",
  description: "Test description",
  justification: "Test justification",
  effective_date: "2026-01-15",
  status: "Draft",
  branch: "co-CO-2026-001",
  branch_locked: false,
  available_transitions: ["submit", "delete"],
  project_id: "test-project-id",
};

export const mockLockedChangeOrder: ChangeOrderPublic = {
  ...mockChangeOrder,
  status: "Submitted",
  branch_locked: true,
  available_transitions: ["approve", "reject"],
};

export const mockImpactData: ImpactAnalysisResponse = {
  kpi_scorecard: { /* ... */ },
  waterfall: { /* ... */ },
  time_series: [],
  entity_changes: [],
  branch_name: "co-CO-2026-001",
};
```

**Mock/Stub Requirements**:

- API hooks: Mock `useChangeOrder`, `useUpdateChangeOrder`, `useCreateChangeOrder`, `useImpactAnalysis`
- Navigation: Mock `useNavigate`, `useParams`
- Form: Mock `Form.useForm`
- Time-dependent logic: Use fixed dates in tests

**Test Setup Files**:

```typescript
// frontend/src/test/setup.ts
import { vi } from 'vitest';

// Mock TanStack Query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(),
}));

// Mock React Router
vi.mock('react-router-dom', () => ({
  useNavigate: vi.fn(),
  useParams: vi.fn(),
  Link: vi.fn(),
}));

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();
```

### TDD Validation Checklist

Before implementation:

- [ ] Test file created following naming convention
- [ ] Test written with AAA structure (Arrange-Act-Assert)
- [ ] Test runs and fails with **expected error** (not pre-existing bug)
- [ ] Test failure reason documented in do-prompt log
- [ ] Test name clearly describes expected behavior

After implementation:

- [ ] New test passes
- [ ] All existing tests still pass (no regressions)
- [ ] Coverage report shows ≥80% (or 100% for critical paths)
- [ ] Code passes TypeScript strict and ESLint checks

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
| --------- | ----------- | ----------- | ------ | ------------------- |
| Technical | Section collapse state management complexity | Medium | Medium | Use well-tested collapsible component pattern, extract custom hook |
| Technical | Form dirty tracking may cause performance issues | Low | Medium | Implement efficient comparison, debounced checks |
| Integration | Impact data loading may be slow for large projects | Medium | Medium | Show loading state, consider virtualization for entity grid |
| Integration | Workflow action state synchronization | Low | High | Refetch CO data after actions, use optimistic updates |
| UX | Long scroll page may be overwhelming | Medium | Medium | Collapsible sections, sticky nav, clear section headers |
| Schedule | Task dependencies may cause delays | Low | Medium | Test-first approach reduces integration risk, parallel test writing |
| Schedule | Scope creep with additional features | Low | Medium | Strict adherence to out-of-scope list |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**

- Coding Standards: [`docs/02-architecture/coding-standards.md`](../../02-architecture/coding-standards.md)
- Navigation Patterns: [`docs/05-user-guide/navigation-patterns.md`](../../05-user-guide/navigation-patterns.md)
- Bounded Contexts: [`docs/02-architecture/01-bounded-contexts.md`](../../02-architecture/01-bounded-contexts.md) (Context #7: Change Order Processing)

**Domain & Requirements:**

- Change Management User Stories: [`docs/01-product-scope/change-management-user-stories.md`](../../01-product-scope/change-management-user-stories.md)
- Functional Requirements: [`docs/01-product-scope/functional-requirements.md`](../../01-product-scope/functional-requirements.md)

**Project Context:**

- Current Iteration: [`docs/03-project-plan/current-iteration.md`](../../03-project-plan/current-iteration.md)
- Analysis Document: [`docs/03-project-plan/iterations/2026-01-15-change-order-unified-page/00-analysis.md`](./00-analysis.md)

### Code References

**Existing Patterns to Follow:**

**Frontend Layout Pattern:**
- [`frontend/src/pages/projects/ProjectLayout.tsx`](../../../frontend/src/pages/projects/ProjectLayout.tsx) - Layout wrapper pattern
- [`frontend/src/pages/projects/ProjectOverview.tsx`](../../../frontend/src/pages/projects/ProjectOverview.tsx) - Page component structure

**Frontend Components:**
- [`frontend/src/features/change-orders/components/ChangeOrderModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx) - Form logic extraction
- [`frontend/src/features/change-orders/components/ChangeOrderWorkflowModal.tsx`](../../../frontend/src/features/change-orders/components/ChangeOrderWorkflowModal.tsx) - Workflow integration
- [`frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx`](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx) - Impact section source
- [`frontend/src/components/navigation/PageNavigation.tsx`](../../../frontend/src/components/navigation/PageNavigation.tsx) - Navigation pattern reference

**Frontend Hooks:**
- [`frontend/src/features/change-orders/hooks/useWorkflowActions.ts`](../../../frontend/src/features/change-orders/hooks/useWorkflowActions.ts) - Workflow action pattern
- [`frontend/src/features/change-orders/api/useChangeOrders.ts`](../../../frontend/src/features/change-orders/api/useChangeOrders.ts) - Data fetching pattern

**Frontend Tests:**
- [`frontend/src/features/change-orders/components/WorkflowButtons.test.tsx`](../../../frontend/src/features/change-orders/components/WorkflowButtons.test.tsx) - Test pattern reference
- [`frontend/src/pages/projects/ProjectOverview.test.tsx`](../../../frontend/src/pages/projects/ProjectOverview.test.tsx) - Page test pattern

**API Contracts:**

- **GET** `/api/v1/change-orders/{id}` - Fetch change order
- **POST** `/api/v1/change-orders` - Create change order
- **PUT** `/api/v1/change-orders/{id}` - Update change order
- **GET** `/api/v1/change-orders/{id}/impact` - Fetch impact analysis

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [ ] Node.js 18+ and npm installed
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Vitest and Playwright configured
- [ ] Test fixtures created in `frontend/src/test/fixtures/`
- [ ] Existing API endpoints operational (no backend changes needed)

### Documentation Prerequisites

- [x] Analysis phase approved (Option 2 selected)
- [x] Plan phase document reviewed
- [ ] Development team briefed on approach

---

## File Change List

| File Path | Action | Purpose |
| --------- | ------ | ------- |
| `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx` | Create | Main page component |
| `frontend/src/features/change-orders/components/ChangeOrderFormSection.tsx` | Create | Form section component |
| `frontend/src/features/change-orders/components/ChangeOrderWorkflowSection.tsx` | Create | Workflow section component |
| `frontend/src/features/change-orders/components/ChangeOrderImpactSection.tsx` | Create | Impact section component |
| `frontend/src/features/change-orders/components/ChangeOrderPageNav.tsx` | Create | Sticky sub-navigation |
| `frontend/src/features/change-orders/components/CollapsibleSection.tsx` | Create | Collapsible section wrapper |
| `frontend/src/hooks/useFormDirty.ts` | Create | Form dirty tracking hook |
| `frontend/src/hooks/useChangeOrderMode.ts` | Create | Create/edit mode detection hook |
| `frontend/src/routes/index.tsx` | Modify | Add new routes for detail page |
| `frontend/src/features/change-orders/components/ChangeOrderList.tsx` | Modify | Update navigation to detail page |
| `frontend/src/features/change-orders/components/index.ts` | Modify | Export new components |
| `frontend/src/test/fixtures/changeOrders.ts` | Create | Test fixtures |
| `frontend/src/test/setup.ts` | Modify | Add test setup mocks |
| `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.test.tsx` | Create | Page component tests |
| `frontend/src/features/change-orders/components/ChangeOrderFormSection.test.tsx` | Create | Form section tests |
| `frontend/src/features/change-orders/components/ChangeOrderWorkflowSection.test.tsx` | Create | Workflow section tests |
| `frontend/src/features/change-orders/components/ChangeOrderImpactSection.test.tsx` | Create | Impact section tests |
| `frontend/src/features/change-orders/components/ChangeOrderPageNav.test.tsx` | Create | Navigation tests |
| `frontend/src/hooks/useFormDirty.test.ts` | Create | Dirty tracking tests |
| `frontend/src/hooks/useChangeOrderMode.test.ts` | Create | Mode detection tests |
| `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.integration.test.tsx` | Create | Integration tests |
| `frontend/tests/e2e/change-order-unified-page.spec.ts` | Create | E2E tests |

---

## TDD Quick Reference

### Test-First Command Sequence

```bash
# 1. Create test file
touch frontend/src/features/change-orders/components/ChangeOrderFormSection.test.tsx

# 2. Write test (AAA pattern)
# Edit: test_form_section_renders_all_fields()

# 3. Run test - confirm FAILS
npm test -- ChangeOrderFormSection.test.tsx

# 4. Implement minimal code
# Edit: ChangeOrderFormSection.tsx

# 5. Run test - confirm PASSES
npm test -- ChangeOrderFormSection.test.tsx

# 6. Refactor
# Extract logic, improve names

# 7. Run all tests
npm test

# 8. Run coverage
npm run test:coverage
```

### Frontend Test Pattern

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ChangeOrderFormSection } from "./ChangeOrderFormSection";

describe("ChangeOrderFormSection", () => {
  it("should render all form fields", () => {
    // Arrange
    const mockProps = {
      changeOrder: mockChangeOrder,
      onSave: vi.fn(),
      onCancel: vi.fn(),
      isLocked: false,
    };

    // Act
    render(<ChangeOrderFormSection {...mockProps} />);

    // Assert
    expect(screen.getByLabelText("Code")).toHaveValue("CO-2026-001");
    expect(screen.getByLabelText("Title")).toHaveValue("Test Change Order");
    expect(screen.getByLabelText("Description")).toHaveValue("Test description");
  });

  it("should disable form fields when branch is locked", () => {
    // Arrange
    const mockProps = {
      changeOrder: mockLockedChangeOrder,
      onSave: vi.fn(),
      onCancel: vi.fn(),
      isLocked: true,
    };

    // Act
    render(<ChangeOrderFormSection {...mockProps} />);

    // Assert
    expect(screen.getByLabelText("Code")).toBeDisabled();
    expect(screen.getByLabelText("Title")).toBeDisabled();
  });
});
```

### E2E Test Pattern

```typescript
import { test, expect } from "@playwright/test";

test.describe("Change Order Unified Page", () => {
  test("should create new change order", async ({ page }) => {
    // Arrange
    await page.goto("/projects/test-project/change-orders/new");

    // Act
    await page.getByLabel("Code").fill("CO-2026-999");
    await page.getByLabel("Title").fill("E2E Test Change Order");
    await page.getByLabel("Description").fill("Test description with enough characters");
    await page.getByRole("button", { name: "Create" }).click();

    // Assert
    await expect(page).toHaveURL(/\/change-orders\/[^/]+$/);
    await expect(page.getByText("CO-2026-999")).toBeVisible();
  });

  test("should show unsaved changes prompt", async ({ page }) => {
    await page.goto("/projects/test-project/change-orders/test-co-id");
    await page.getByLabel("Title").fill("Modified Title");
    await page.getByRole("link", { name: "Back to List" }).click();

    // Assert prompt appears
    await expect(page.getByText("You have unsaved changes")).toBeVisible();
  });
});
```

---

## Implementation Notes

### Component Hierarchy

```
ChangeOrderUnifiedPage (Page)
├── PageHeader (Title, Status, Lock Indicator)
├── ChangeOrderPageNav (Sticky Anchor Navigation)
│   └── [Form] [Workflow] [Impact]
└── main content area
    ├── CollapsibleSection (Form)
    │   └── ChangeOrderFormSection
    ├── CollapsibleSection (Workflow)
    │   └── ChangeOrderWorkflowSection
    │       ├── WorkflowStepper
    │       └── WorkflowButtons
    └── CollapsibleSection (Impact)
        └── ChangeOrderImpactSection
            ├── KPICards
            ├── WaterfallChart
            ├── SCurveComparison
            └── EntityImpactGrid
```

### Routing Structure

```
/projects/:projectId/change-orders              → List page (existing)
/projects/:projectId/change-orders/new         → Create new CO (new)
/projects/:projectId/change-orders/:coId       → Detail/edit page (new)
/projects/:projectId/change-orders/:coId/impact → Legacy redirect (add)
```

### State Management

- **Server State**: TanStack Query (`useChangeOrder`, `useImpactAnalysis`)
- **Form State**: Ant Design Form (`Form.useForm`)
- **UI State**: `useState` for collapsed sections, `useFormDirty` for dirty tracking
- **Navigation State**: React Router (`useNavigate`, `useParams`)

### Key Decisions

1. **No URL tab state**: Simplifies routing, all sections always present
2. **Collapsible by default**: Sections expanded initially for visibility
3. **Sticky navigation**: Always accessible anchor links
4. **Form dirty tracking**: Prevents accidental data loss
5. **Create mode simplification**: Hide workflow/impact sections (not applicable)
6. **Legacy route support**: Redirect `/impact` to main page with anchor scroll

---

## Next Steps

Once this plan is approved:

1. Proceed to **DO phase** following TDD workflow
2. Start with Task 1 (page routing) - write tests first
3. Follow RED-GREEN-REFACTOR cycle for each task
4. Update [02-do.md](./02-do.md) daily with progress
5. Run full test suite after each task completion
6. Create CHECK phase document when implementation complete

---

**Approval Required:** Please review and approve this plan before proceeding to implementation.
