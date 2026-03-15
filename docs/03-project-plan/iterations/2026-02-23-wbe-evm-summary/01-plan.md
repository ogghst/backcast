# PLAN Phase: WBE EVM Summary Implementation

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

- **Selected Option**: Option 2 (Dedicated EVM Analysis Tab)
- **Architecture**: Restructure `WBEDetailPage.tsx` to use Ant Design `Tabs`. Move existing overview content to an "Overview" tab. Add a new "EVM Analysis" tab that fetches and displays WBE-level EVM metrics and time-series data.
- **Key Decisions**: As requested by the user, ensure all cards/sections within the EVM Analysis tab are collapsible using Ant Design `Collapse` to maintain a consistent and clean layout.

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [ ] The WBE Detail Page successfully displays an "Overview" tab and an "EVM Analysis" tab. VERIFIED BY: Manual UI test.
- [ ] Navigating to the "EVM Analysis" tab successfully fetches and displays the WBE's EVM metrics and S-curve time series. VERIFIED BY: Manual UI test / Cypress E2E.
- [ ] All informational sections in the "EVM Analysis" tab (e.g., Summary, Historical Trends) are contained within collapsible panels. VERIFIED BY: Manual UI test.
- [ ] Time Machine controls (date and branch) correctly influence the fetched EVM data for the WBE. VERIFIED BY: Manual UI test.

**Technical Criteria:**

- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline (No backend changes expected, but frontend type-checking via `npm run type-check` or similar should pass).
- [ ] Component Reusability: Successfully reuses `EVMSummaryView` and `EVMTimeSeriesChart` from `features/evm`. VERIFIED BY: Code review.

### 1.3 Scope Boundaries

**In Scope:**

- Restructuring `WBEDetailPage.tsx` into a tabbed layout.
- Fetching WBE-level metrics using `useEVMMetrics` and `useEVMTimeSeries`.
- Displaying `EVMSummaryView` and a collapsible `EVMTimeSeriesChart`.

**Out of Scope:**

- Changes to backend generic EVM endpoints (already supported).
- Creating new chart types not already available in `features/evm`.

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| #   | Task                                   | Files                                       | Dependencies | Success Criteria                                                                                                          | Complexity |
| --- | -------------------------------------- | ------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Restructure `WBEDetailPage.tsx` Layout | `frontend/src/pages/wbes/WBEDetailPage.tsx` | None         | Page displays standard Ant Design tabs (Overview & EVM Analysis). Existing WBE details remain functional in Overview tab. | Medium     |
| 2   | Add EVM Data Fetching                  | `frontend/src/pages/wbes/WBEDetailPage.tsx` | Task 1       | `useEVMMetrics` and `useEVMTimeSeries` correctly fetch data for the current WBE.                                          | Low        |
| 3   | Implement EVM Analysis Tab Content     | `frontend/src/pages/wbes/WBEDetailPage.tsx` | Task 2       | "EVM Analysis" tab displays the `EVMSummaryView` and the `EVMTimeSeriesChart` wrapped in Antd `Collapse` panels.          | Medium     |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion                                | Test ID | Expected Behavior                                                        |
| --------------------------------------------------- | ------- | ------------------------------------------------------------------------ |
| Page displays an "Overview" and "EVM Analysis" tab. | T-001   | User sees two distinct tabs upon navigating to a WBE detail page.        |
| "EVM Analysis" fetch WBE's EVM metrics and S-curve. | T-002   | EVM summary and chart render with data matching the current WBE.         |
| All informational sections are collapsible.         | T-003   | Clicking panel headers toggles the visibility of the summary and charts. |

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

```text
├── E2E Tests (Cypress)
│   └── User navigates to WBE Detail Page, clicks "EVM Analysis" tab, verifies collapsible charts.
└── Manual UI Tests
    └── Verify responsive layout and adherence to Ant Design standards.
```

### 3.2 Test Cases

| Test ID | Test Name                                | Criterion | Type      | Expected Result                                          |
| ------- | ---------------------------------------- | --------- | --------- | -------------------------------------------------------- |
| T-001   | `test_wbe_page_displays_tabs`            | AC-1      | UI/Manual | Tabs "Overview" and "EVM Analysis" are visible           |
| T-002   | `test_wbe_evm_analysis_data_fetch`       | AC-2      | UI/Manual | Charts and metrics populate with realistic data          |
| T-003   | `test_evm_analysis_sections_collapsible` | AC-3      | UI/Manual | Metric categories and Historical Trends can be collapsed |

---

## Phase 4: Risk Assessment

| Risk Type | Description                                                                                                      | Probability | Impact | Mitigation                                                                                                                       |
| --------- | ---------------------------------------------------------------------------------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| Technical | The generic `useEVMMetrics` might throw 404/500 if the WBE has no cost elements or if metrics calculation fails. | Medium      | Medium | Wrap EVM components in error boundaries or handle empty states gracefully (e.g., `evmMetrics ? <EVMSummaryView /> : <Empty />`). |

---

## Output

**File**: `docs/03-project-plan/iterations/2026-02-23-wbe-evm-summary/01-plan.md`
