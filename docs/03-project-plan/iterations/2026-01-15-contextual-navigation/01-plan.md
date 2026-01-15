# Plan: Contextual Navigation Component & Change Orders Page

**Created:** 2026-01-15
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 - Tab-Based Navigation

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 - Tab-Based Navigation
- **Architecture**: React Router v6 nested routes with Ant Design Tabs component for navigation
- **Key Decisions**:
  - URL-driven navigation for shareability
  - `PageNavigation` component that can be easily adapted for sidebar placement
  - ProjectDetailPage refactored to support nested routing
  - Future sections organized as tabs
  - UI documentation updated with navigation strategy

### Success Criteria

**Functional Criteria:**

- Clicking "Change Orders" tab navigates to `/projects/:projectId/change-orders` VERIFIED BY: Component test
- Change orders page displays the ChangeOrderList component VERIFIED BY: Component test
- Active tab is highlighted based on current route VERIFIED BY: Component test
- Browser back/forward buttons work correctly VERIFIED BY: Integration test
- URLs are shareable and bookmarkable VERIFIED BY: Manual test
- PageNavigation component can be adapted to sidebar layout VERIFIED BY: Component test with sidebar variant
- ProjectDetailPage still displays project summary and root WBEs VERIFIED BY: Regression test

**Technical Criteria:**

- Performance: Tab switches render without visible lag VERIFIED BY: React Testing Library async assertions
- Code Quality: TypeScript strict mode, ESLint clean VERIFIED BY: Quality gates
- Accessibility: Proper ARIA roles and keyboard navigation VERIFIED BY: Accessibility test (axe-core)
- Responsive: Tabs work on mobile (scrollable/swipable) VERIFIED BY: Visual regression test

**Business Criteria:**

- Users can efficiently navigate between project details and change orders VERIFIED BY: Manual UX review
- Navigation pattern is consistent for future tabs VERIFIED BY: Code review

**TDD Criteria:**

- [ ] All tests written **before** implementation code VERIFIED BY: Git commit history
- [ ] Tests validate **all acceptance criteria** VERIFIED BY: Test-to-requirement traceability matrix
- [ ] Each test **failed first** (RED phase) VERIFIED BY: Do-prompt daily log
- [ ] Test coverage ≥80% VERIFIED BY: `npm run test:coverage` report
- [ ] Tests follow Arrange-Act-Assert pattern VERIFIED BY: Code review
- [ ] UserEvent from Testing Library used for interactions VERIFIED BY: Reference to component tests

### Scope Boundaries

**In Scope:**

- Create `PageNavigation` component using Ant Design Tabs
- Create `ProjectChangeOrdersPage` as dedicated page for change orders
- Refactor `ProjectDetailPage` to use nested routing structure
- Add routes for nested navigation
- Move `ChangeOrderList` from ProjectDetailPage Card to dedicated page
- Update UI documentation with navigation strategy

**Out of Scope:**

- Adding other tabs beyond Change Orders (deferred to future iterations)
- Modifying the AppLayout Sider for sidebar navigation (deferred)
- Backend API changes (no changes needed)
- E2E tests with Playwright (deferred if not critical path)

**Assumptions:**

- React Router v6 supports the required nested routing pattern
- Ant Design Tabs component supports URL-based active state
- TanStack Query cache works correctly across route transitions

---

## Work Decomposition

### Task Breakdown (Test-First)

| Task | Description | Files | Dependencies | Success | Est. Complexity |
| ---- | ----------- | ------ | ------------- | -------- | --------------- |
| 1 | Create PageNavigation component with tests | `frontend/src/components/navigation/PageNavigation.tsx`<br>`frontend/src/components/navigation/PageNavigation.test.tsx` | None | Component renders tabs, active tab works, URL updates on click | Medium |
| 2 | Create ProjectLayout wrapper for nested routes | `frontend/src/pages/projects/ProjectLayout.tsx`<br>`frontend/src/pages/projects/ProjectLayout.test.tsx` | Task 1 | Layout renders Outlet, PageNavigation with config | Low |
| 3 | Extract ProjectOverview from ProjectDetailPage | `frontend/src/pages/projects/ProjectOverview.tsx`<br>`frontend/src/pages/projects/ProjectOverview.test.tsx` | Task 2 | Overview renders project summary, root WBEs, no change orders | Low |
| 4 | Create ProjectChangeOrdersPage | `frontend/src/pages/projects/ProjectChangeOrdersPage.tsx`<br>`frontend/src/pages/projects/ProjectChangeOrdersPage.test.tsx` | Task 2 | Page renders ChangeOrderList, breadcrumb, loading states | Low |
| 5 | Update routes for nested navigation | `frontend/src/routes/index.tsx`<br>`frontend/src/routes/index.test.tsx` | Task 3, 4 | Nested routes work, URL params passed correctly | Low |
| 6 | Integration test for navigation flow | `frontend/src/pages/projects/ProjectNavigation.integration.test.tsx` | Task 1-5 | Full flow: navigate, tabs work, browser nav works | Medium |
| 7 | Add sidebar variant to PageNavigation | `frontend/src/components/navigation/PageNavigation.tsx` (update)<br>`frontend/src/components/navigation/PageNavigation.test.tsx` (update) | Task 1 | Component accepts variant prop, renders correctly in sidebar | Low |
| 8 | Update UI documentation | `docs/05-user-guide/README.md` (or new file) | Task 1-7 | Documentation reflects new navigation pattern | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| -------------------- | ------- | --------- | ----------------- |
| Clicking "Change Orders" tab navigates correctly | T-001 | PageNavigation.test.tsx | Clicking tab calls navigate with correct path |
| Change orders page displays ChangeOrderList | T-002 | ProjectChangeOrdersPage.test.tsx | Component renders ChangeOrderList with projectId |
| Active tab highlighted based on route | T-003 | PageNavigation.test.tsx | Tab active={true} when route matches |
| Browser back/forward buttons work | T-004 | ProjectNavigation.integration.test.tsx | Navigation changes update active tab state |
| URLs are shareable | T-005 | (Manual) | Direct URL loads correct tab content |
| Sidebar variant works | T-006 | PageNavigation.test.tsx | variant="sidebar" renders vertical tabs |
| ProjectDetailPage regression | T-007 | ProjectOverview.test.tsx | Project summary and WBEs still render |
| Keyboard navigation | T-008 | PageNavigation.test.tsx | Tab key moves focus, Enter/Space activates |
| Loading states | T-009 | ProjectChangeOrdersPage.test.tsx | Shows skeleton when data loading |
| Error states | T-010 | ProjectChangeOrdersPage.test.tsx | Shows error message on fetch failure |

---

## Test Specification

### Test Hierarchy

```
├── Component Tests (Unit)
│   ├── PageNavigation component
│   │   ├── Renders tabs from items prop
│   │   ├── Highlights active tab based on current route
│   │   ├── Navigates to correct route on tab click
│   │   ├── Supports both horizontal and sidebar variants
│   │   └── Keyboard navigation (arrow keys, Enter, Space)
│   ├── ProjectLayout component
│   │   ├── Renders PageNavigation with configured items
│   │   ├── Renders Outlet for nested routes
│   │   └── Passes projectId to nested routes
│   ├── ProjectOverview component
│   │   ├── Renders project summary card
│   │   ├── Renders root WBEs table
│   │   ├── Does NOT render change orders (removed)
│   │   └── Loading and error states
│   └── ProjectChangeOrdersPage component
│       ├── Renders breadcrumb
│       ├── Renders page title
│       ├── Renders ChangeOrderList with projectId
│       ├── Loading state shows skeleton
│       └── Error state shows message
├── Integration Tests
│   └── ProjectNavigation flow
│       ├── User clicks tab → URL updates → content changes
│       ├── User navigates directly to URL → correct tab active
│       ├── Browser back button → previous tab active
│       └── Browser forward button → forward tab active
└── E2E Tests (Deferred)
    └── Critical user flows (if needed)
```

### Test Cases (First 5 - Simplest to Most Complex)

| Test ID | Test Name | Acceptance Criterion | Type | Verification |
| ------- | --------- | -------------------- | ---- | ------------ |
| T-001 | `test_page_navigation_renders_tabs_from_items_prop` | Basic rendering | Component | Renders correct number of tabs with labels |
| T-002 | `test_page_navigation_highlights_active_tab_from_route` | Active state | Component | Tab with matching path has active={true} |
| T-003 | `test_page_navigation_navigates_on_tab_click` | Navigation | Component | Clicking tab calls navigate() with correct path |
| T-004 | `test_project_navigation_flow_with_browser_back_button` | Browser nav | Integration | Back button updates URL and active tab |
| T-005 | `test_page_navigation_sidebar_variant_renders_vertical` | Sidebar variant | Component | variant="sidebar" renders Tabs with tabPosition="left" |

### Test Case Detail (T-001 Example)

```tsx
// frontend/src/components/navigation/PageNavigation.test.tsx

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageNavigation } from "./PageNavigation";
import { MemoryRouter } from "react-router-dom";

describe("PageNavigation", () => {
  it("test_page_navigation_renders_tabs_from_items_prop", () => {
    // Arrange
    const items = [
      { key: "overview", label: "Overview", path: "/projects/123" },
      { key: "change-orders", label: "Change Orders", path: "/projects/123/change-orders" },
    ];

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <PageNavigation items={items} />
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Change Orders" })).toBeInTheDocument();
  });
});
```

### Test Infrastructure

**Test Framework**: Vitest with React Testing Library

**Required Utilities** (from existing setup):

- `render` from @testing-library/react
- `screen` from @testing-library/react
- `userEvent` from @testing-library/user-event
- `MemoryRouter` from react-router-dom (for route testing)

**Custom Fixtures Needed**:

```tsx
// tests/frontend/navigation/fixtures.tsx
export const mockNavigationItems = [
  { key: "overview", label: "Overview", path: "/projects/123" },
  { key: "change-orders", label: "Change Orders", path: "/projects/123/change-orders" },
];

export const mockProject = {
  project_id: "123",
  code: "TEST-001",
  name: "Test Project",
  budget: 100000,
};
```

**Mock/Stub Requirements**:

- React Router's `useNavigate` - use vi.mock() or MemoryRouter
- `useLocation` - use MemoryRouter for controlled location
- API calls (TanStack Query) - use QueryClient's mock queries

### TDD Validation Checklist

**Before implementation:**

- [ ] Test file created following naming convention: `ComponentName.test.tsx`
- [ ] Test written with AAA structure (Arrange-Act-Assert)
- [ ] Test runs and fails with **expected error** (import error, component doesn't exist)
- [ ] Test failure reason documented in daily log
- [ ] Test name clearly describes expected behavior

**After implementation:**

- [ ] New test passes
- [ ] All existing tests still pass (no regressions)
- [ ] Coverage report shows ≥80%
- [ ] Code passes ESLint and TypeScript checks
- [ ] Component accepts ref for forwardRef pattern (if needed)

---

## File Change List

| File Path | Action | Purpose |
| --------- | ------ | ------- |
| `frontend/src/components/navigation/PageNavigation.tsx` | Create | Reusable tab navigation component with sidebar variant support |
| `frontend/src/components/navigation/PageNavigation.test.tsx` | Create | Component tests for PageNavigation |
| `frontend/src/components/navigation/index.ts` | Create | Barrel export for navigation components |
| `frontend/src/pages/projects/ProjectLayout.tsx` | Create | Layout wrapper for project nested routes |
| `frontend/src/pages/projects/ProjectLayout.test.tsx` | Create | Component tests for ProjectLayout |
| `frontend/src/pages/projects/ProjectOverview.tsx` | Create | Extracted overview content from ProjectDetailPage |
| `frontend/src/pages/projects/ProjectOverview.test.tsx` | Create | Component tests for ProjectOverview |
| `frontend/src/pages/projects/ProjectChangeOrdersPage.tsx` | Create | Dedicated page for change orders |
| `frontend/src/pages/projects/ProjectChangeOrdersPage.test.tsx` | Create | Component tests for ProjectChangeOrdersPage |
| `frontend/src/pages/projects/ProjectNavigation.integration.test.tsx` | Create | Integration test for full navigation flow |
| `frontend/src/routes/index.tsx` | Modify | Add nested routes for project navigation |
| `frontend/src/routes/index.test.tsx` | Modify | Update route tests for nested routing |
| `docs/05-user-guide/navigation-patterns.md` | Create | Document navigation strategy and patterns |
| `docs/05-user-guide/README.md` | Modify | Update user guide with navigation section |

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
| --------- | ----------- | ----------- | ------ | ------------------- |
| Technical | React Router nested routing may have URL param conflicts | Low | Medium | Test URL params thoroughly in integration tests |
| Technical | TanStack Query cache invalidation on route change | Medium | Low | Verify cache behavior, use queryClient.clear() if needed |
| Integration | Time Machine context may not work across nested routes | Low | Medium | Ensure projectId passed through route context |
| Integration | Existing links to ProjectDetailPage may break | Medium | Medium | Add redirect from old route to overview tab |
| Schedule | Refactoring ProjectDetailPage may take longer than estimated | Low | Low | Extract incrementally, keep existing working until verified |
| UX | Users may be confused by new navigation | Low | Medium | Maintain familiar UI, add transition hints if needed |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**

- Coding Standards: `docs/02-architecture/coding-standards.md`
- Frontend Testing: `frontend/README.md` (testing section)
- Component Patterns: (to be documented in navigation-patterns.md)

**Domain & Requirements:**

- Change Order Management: `docs/01-product-scope/06-change-orders.md` (if exists)
- Project Management: `docs/01-product-scope/04-project-wbe-management.md` (if exists)

**Project Context:**

- Current Iteration: `docs/03-project-plan/current-iteration.md`
- Related Iterations: Change order integration iterations

### Code References

**Existing Patterns to Follow:**

- Tabs Pattern: [ImpactAnalysisDashboard.tsx](../../../frontend/src/features/change-orders/components/ImpactAnalysisDashboard.tsx)
- Breadcrumb Pattern: [BreadcrumbBuilder.tsx](../../../frontend/src/components/hierarchy/BreadcrumbBuilder.tsx)
- Layout Pattern: [AppLayout.tsx](../../../frontend/src/layouts/AppLayout.tsx)

**Frontend Test References:**

- Component Test Pattern: [BranchLockIndicator.test.tsx](../../../frontend/src/features/change-orders/components/BranchLockIndicator.test.tsx)
- Hook Test Pattern: [useWorkflowActions.test.tsx](../../../frontend/src/features/change-orders/hooks/useWorkflowActions.test.tsx)

**Database Schema:**

- No changes required for this iteration

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Frontend development environment set up (Vite, React, TypeScript)
- [x] Test environment configured (Vitest, React Testing Library)
- [x] Existing components accessible (ChangeOrderList, ProjectSummaryCard, WBETable)

### Documentation Prerequisites

- [x] Analysis phase approved
- [x] Architecture docs reviewed (coding standards)
- [x] Existing patterns understood (Tabs from ImpactAnalysisDashboard)

---

## TDD Quick Reference

### Test-First Command Sequence

```bash
# 1. Create test file
touch frontend/src/components/navigation/PageNavigation.test.tsx

# 2. Write test (AAA pattern)
# Edit: test_page_navigation_renders_tabs_from_items_prop()

# 3. Run test - confirm FAILS
cd frontend && npm test -- PageNavigation.test.tsx

# 4. Implement minimal code
# Create PageNavigation.tsx with basic render

# 5. Run test - confirm PASSES
npm test -- PageNavigation.test.tsx

# 6. Refactor
# Extract types, improve structure

# 7. Run all tests
npm test

# 8. Run coverage
npm run test:coverage
```

### Common Test Patterns

**Component Pattern (Testing Library)**:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

describe("ComponentName", () => {
  it("test_component_with_input_shows_expected_output", () => {
    // Arrange
    const props = { /* ... */ };

    // Act
    render(<ComponentName {...props} />);

    // Assert
    expect(screen.getByText("Expected Text")).toBeInTheDocument();
  });
});
```

**User Interaction Pattern**:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

it("test_clicking_button_performs_action", async () => {
  // Arrange
  const user = userEvent.setup();
  const mockFn = vi.fn();

  // Act
  render(<Button onClick={mockFn} />);
  await user.click(screen.getByRole("button"));

  // Assert
  expect(mockFn).toHaveBeenCalledOnce();
});
```

**Navigation Pattern**:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

it("test_tab_click_navigates_to_route", async () => {
  // Arrange
  const user = userEvent.setup();

  // Act
  render(
    <MemoryRouter initialEntries={["/projects/123"]}>
      <PageNavigation items={items} />
    </MemoryRouter>
  );
  await user.click(screen.getByRole("tab", { name: "Change Orders" }));

  // Assert - check navigate was called or URL changed
  // (Implementation depends on navigation approach)
});
```
