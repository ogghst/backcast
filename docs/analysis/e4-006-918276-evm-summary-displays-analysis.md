# High-Level Analysis: E4-006 EVM Summary Displays

**Task:** E4-006 - EVM Summary Displays
**Sprint:** Sprint 4 - Earned Value Recording and Core EVM Calculations
**Status:** Analysis Phase
**Date:** 2025-11-16
**Current Time:** 23:12 CET (Europe/Rome)

---

## User Story

As a project manager monitoring performance at a given control date,
I want to see a summary display of EVM performance indices (CPI, SPI, TCPI) and variances (CV, SV) at project, WBE, and cost element levels,
So that I can quickly assess project health and identify areas requiring attention without drilling into detailed reports.

---

## 1. CODEBASE PATTERN ANALYSIS

### 1.1 Existing Summary Display Components

1. **BudgetSummary Component – E2-006**
   - **Location:** `frontend/src/components/Projects/BudgetSummary.tsx`
   - **Architecture Layers:**
     - React component using Chakra UI (`Box`, `Grid`, `Heading`, `Text`, `VStack`)
     - React Query (`useQuery`) for data fetching with `BudgetSummaryService`
     - Time-machine integration via `useTimeMachine()` hook for control date
     - Chart.js visualization (Doughnut chart for revenue utilization, Bar chart for budget vs revenue)
   - **Patterns to respect:**
     - Grid layout with responsive columns (`base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(4, 1fr)"`)
     - Metric cards with consistent styling (border, padding, background)
     - Currency formatting using `toLocaleString` with EUR currency
     - Loading states with `SkeletonText` components
     - Color-coded status indicators (utilization percentages)
     - Control date display in subtitle
     - Level-based props (`level: "project" | "wbe"`) with conditional service calls

2. **CostSummary Component – E3-002**
   - **Location:** `frontend/src/components/Projects/CostSummary.tsx`
   - **Architecture Layers:**
     - Similar structure to BudgetSummary
     - Uses `CostSummaryService` with level-based endpoints
     - Color-coded status indicators based on cost percentage thresholds:
       - Green (< 50%): "Under Budget"
       - Blue (50-80%): "On Track"
       - Orange (80-100%): "Approaching Budget"
       - Red (≥ 100%): "Over Budget"
     - Icons from `react-icons/fi` (FiCheckCircle, FiTrendingUp, FiAlertCircle, FiXCircle)
   - **Patterns to respect:**
     - Status determination logic with thresholds
     - Icon + color + label pattern for visual feedback
     - Optional quality cost filtering with notice banner
     - Empty state handling (null checks)

3. **EarnedValueSummary Component – E4-002**
   - **Location:** `frontend/src/components/Projects/EarnedValueSummary.tsx`
   - **Architecture Layers:**
     - Uses `EarnedValueService` with level-based endpoints
     - Displays EV, BAC, and percent complete
     - Control date display in subtitle
     - Supports project, WBE, and cost-element levels
   - **Patterns to respect:**
     - Three-card layout (EV, BAC, Percent Complete)
     - Currency and percentage formatting helpers
     - Time-machine integration for control date
     - Level-based query key construction

4. **MetricsSummary Component – Integration Pattern**
   - **Location:** `frontend/src/components/Projects/MetricsSummary.tsx`
   - **Architecture Layers:**
     - Container component that composes multiple summary components
     - Conditional rendering based on level (cost-element excludes BudgetSummary)
     - Vertical spacing with `Box mt={6}` between sections
   - **Patterns to respect:**
     - Composition pattern for combining multiple summaries
     - Level-based conditional rendering
     - Consistent spacing and layout

### 1.2 Backend API Patterns

1. **Unified EVM Metrics Endpoints – E4-005**
   - **Location:** `backend/app/api/routes/evm_aggregation.py`
   - **Endpoints:**
     - `GET /projects/{project_id}/evm-metrics/cost-elements/{cost_element_id}`
     - `GET /projects/{project_id}/evm-metrics/wbes/{wbe_id}`
     - `GET /projects/{project_id}/evm-metrics`
   - **Response Models:**
     - `EVMIndicesCostElementPublic`
     - `EVMIndicesWBEPublic`
     - `EVMIndicesProjectPublic`
   - **Data Provided:**
     - Core metrics: `planned_value`, `earned_value`, `actual_cost`, `budget_bac`
     - Performance indices: `cpi`, `spi`, `tcpi` (can be `None` or `"overrun"` for TCPI)
     - Variances: `cost_variance`, `schedule_variance`
     - Metadata: `level`, `control_date`, entity ID
   - **Patterns to respect:**
     - Time-machine control date dependency injection
     - Unified endpoint pattern (single endpoint provides all EVM metrics)
     - TypeScript types already generated in `frontend/src/client/types.gen.ts`
     - Service class `EvmMetricsService` available in `frontend/src/client/sdk.gen.ts`

2. **EVM Performance Indices Service – E4-003**
   - **Location:** `backend/app/services/evm_indices.py`
   - **Business Rules:**
     - CPI = EV/AC (None when AC = 0 and EV > 0)
     - SPI = EV/PV (None when PV = 0)
     - TCPI = (BAC-EV)/(BAC-AC) ('overrun' when BAC ≤ AC)
   - **Precision:** 4 decimal places for indices, 2 decimal places for monetary values

3. **Variance Calculations – E4-004**
   - **Business Rules:**
     - CV = EV - AC (negative = over-budget, positive = under-budget)
     - SV = EV - PV (negative = behind-schedule, positive = ahead-of-schedule)
   - **Precision:** 2 decimal places (monetary values)

### 1.3 Frontend Integration Points

1. **Project Detail Page**
   - **Location:** `frontend/src/routes/_layout/projects.$id.tsx`
   - **Integration:** "Metrics" tab contains `<MetricsSummary level="project" projectId={project.project_id} />`
   - **Pattern:** Tabbed layout with multiple tabs (info, wbes, metrics, timeline, baselines)

2. **WBE Detail Page**
   - **Location:** `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`
   - **Integration:** "Metrics" tab contains `<MetricsSummary level="wbe" projectId={projectId} wbeId={wbe.wbe_id} />`
   - **Pattern:** Similar tabbed layout

3. **Cost Element Detail Page**
   - **Location:** `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx`
   - **Integration:** "Metrics" tab contains `<MetricsSummary level="cost-element" ... />`
   - **Pattern:** Multiple tabs including dedicated "Earned Value" tab

### Architectural Layers to Respect

- **Frontend Component Layer (`frontend/src/components/Projects/…`)** for React components following Chakra UI patterns
- **Data Fetching Layer (`@tanstack/react-query`)** for API calls with query keys and caching
- **Service Layer (`@/client`)** for TypeScript-typed API client generated from OpenAPI
- **Time-Machine Integration (`@/context/TimeMachineContext`)** for control date propagation
- **Theme-Aware Styling (`@/components/ui/color-mode`)** for dark mode support

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### Backend Modules and Methods

- **EVM Metrics API Endpoints (Existing)**
  - `EvmMetricsService.getCostElementEvmMetricsEndpoint()` - Cost element level
  - `EvmMetricsService.getWbeEvmMetricsEndpoint()` - WBE level
  - `EvmMetricsService.getProjectEvmMetricsEndpoint()` - Project level
  - **Impact:** All endpoints already exist and return complete EVM metrics including indices and variances. No backend changes required for E4-006.

- **Response Models (Existing)**
  - `EVMIndicesCostElementPublic`, `EVMIndicesWBEPublic`, `EVMIndicesProjectPublic`
  - **Impact:** TypeScript types already generated. All required fields (CPI, SPI, TCPI, CV, SV, PV, EV, AC, BAC) are available.

### Frontend Components and Methods

- **New Component (Proposed)**
  - **File:** `frontend/src/components/Projects/EVMSummary.tsx`
  - **Props Interface:**
    ```typescript
    interface EVMSummaryProps {
      level: "project" | "wbe" | "cost-element"
      projectId?: string
      wbeId?: string
      costElementId?: string
    }
    ```
  - **Data Fetching:**
    - Use `useQuery` with `EvmMetricsService` based on level
    - Query key: `["evm-metrics", level, entityId, controlDate]`
    - Enable query based on required IDs (same pattern as EarnedValueSummary)

- **MetricsSummary Component (Modification)**
  - **File:** `frontend/src/components/Projects/MetricsSummary.tsx`
  - **Impact:** Add `<EVMSummary />` component to the composition
  - **Placement:** After EarnedValueSummary, before closing Box
  - **Conditional:** Show for all levels (project, wbe, cost-element)

- **Detail Pages (No Changes Required)**
  - Project, WBE, and Cost Element detail pages already use `MetricsSummary`
  - EVM Summary will automatically appear in "Metrics" tabs

### System Dependencies and External Integrations

- **React Query:** Already configured and used throughout frontend
- **Chakra UI:** Already configured with theme support
- **Time-Machine Context:** Already implemented and used by other summary components
- **OpenAPI Client:** Already generated with EVM metrics types and services
- **Chart.js (Optional):** Already used in BudgetSummary for visualizations. Could be used for EVM trend visualization in future, but not required for E4-006 basic display.

### Configuration Patterns

- Reuse existing configuration for:
  - Time-machine control date (via `useTimeMachine()` hook)
  - Currency formatting (EUR, 2 decimal places)
  - Percentage formatting (2 decimal places for indices)
  - Color mode (dark/light theme support)
  - Responsive grid breakpoints

---

## 3. ABSTRACTION INVENTORY

### Existing Abstractions to Leverage

- **Currency Formatting Helper**
  - Pattern from `EarnedValueSummary.tsx`:
    ```typescript
    const formatCurrency = (value: string | number | null | undefined): string => {
      if (value === null || value === undefined) return "N/A"
      const numValue = typeof value === "string" ? Number(value) : value
      if (Number.isNaN(numValue)) return "N/A"
      return `€${numValue.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`
    }
    ```
  - **Reuse:** Can be extracted to shared utility or copied to EVMSummary

- **Percentage Formatting Helper**
  - Pattern from `EarnedValueSummary.tsx`:
    ```typescript
    const formatPercent = (value: string | number | null | undefined): string => {
      if (value === null || value === undefined) return "N/A"
      const numValue = typeof value === "string" ? Number(value) : value
      if (Number.isNaN(numValue)) return "N/A"
      return `${(numValue * 100).toFixed(2)}%`
    }
    ```
  - **Reuse:** For displaying CPI/SPI/TCPI as percentages (multiply by 100)

- **Status Indicator Pattern**
  - Pattern from `CostSummary.tsx`:
    ```typescript
    const getCostStatus = (percent: number) => {
      if (percent < 50) return { color: "green.500", icon: FiCheckCircle, label: "Under Budget" }
      if (percent < 80) return { color: "blue.500", icon: FiTrendingUp, label: "On Track" }
      // ... more thresholds
    }
    ```
  - **Reuse:** Can create similar helper for EVM indices:
    - CPI/SPI: < 1.0 = red (poor), 1.0 = yellow (on target), > 1.0 = green (good)
    - TCPI: Similar thresholds, but 'overrun' is special case (red)
    - CV/SV: Negative = red (over-budget/behind-schedule), Zero = yellow, Positive = green

- **Card Component Pattern**
  - Consistent Box structure with:
    - `p={4}`, `borderWidth="1px"`, `borderRadius="md"`, `borderColor`, `bg`
    - `VStack align="stretch" gap={1}` for content
    - `Text fontSize="sm"` for label, `fontSize="xl" fontWeight="bold"` for value, `fontSize="xs"` for description

- **Loading State Pattern**
  - SkeletonText in Grid layout matching final card count
  - Pattern from all existing summary components

- **Query Key Construction Pattern**
  - Pattern: `["entity-type", level, entityId, controlDate]`
  - **Reuse:** Follow same pattern for EVM metrics query

- **Time-Machine Integration**
  - `useTimeMachine()` hook provides `controlDate`
  - Include in query key and display in subtitle
  - Pattern from `EarnedValueSummary.tsx`

### Testing Utilities

- **Component Testing Patterns**
  - Existing theme tests in `frontend/src/components/Projects/__tests__/`
  - Pattern: `BudgetSummary.theme.spec.tsx`, `CostSummary.theme.spec.tsx`, `EarnedValueSummary.theme.spec.tsx`
  - **Reuse:** Create `EVMSummary.theme.spec.tsx` following same pattern

- **Playwright E2E Tests**
  - Existing tests in `frontend/tests/` for project detail pages
  - **Reuse:** Can extend existing tests to verify EVM Summary appears in Metrics tab

---

## 4. ALTERNATIVE APPROACHES

### Approach A – Dedicated EVMSummary Component (Recommended)

- **Summary:** Create a new `EVMSummary.tsx` component following the exact pattern of `EarnedValueSummary.tsx`, displaying CPI, SPI, TCPI, CV, and SV in a grid of metric cards with color-coded status indicators.

- **Layout:**
  - **Card 1:** CPI (Cost Performance Index) with status indicator
  - **Card 2:** SPI (Schedule Performance Index) with status indicator
  - **Card 3:** TCPI (To-Complete Performance Index) with status indicator
  - **Card 4:** CV (Cost Variance) with currency formatting and status indicator
  - **Card 5:** SV (Schedule Variance) with currency formatting and status indicator
  - **Optional Card 6:** Summary status (overall health indicator)

- **Visual Design:**
  - Color coding:
    - **CPI/SPI:** Green (≥ 1.0), Yellow (0.95-1.0), Red (< 0.95)
    - **TCPI:** Green (≤ 1.0), Yellow (1.0-1.1), Red (> 1.1 or 'overrun')
    - **CV/SV:** Green (positive), Yellow (zero), Red (negative)
  - Icons: FiTrendingUp (good), FiMinus (neutral), FiTrendingDown (poor)
  - Status labels: "On Target", "Under Budget", "Over Budget", "Ahead of Schedule", "Behind Schedule", etc.

- **Pros:**
  - Follows established component patterns exactly
  - Clear separation of concerns (dedicated component for EVM metrics)
  - Easy to test and maintain
  - Consistent with other summary components
  - Can be easily extended with additional metrics or visualizations
  - Reuses existing API endpoints (no backend changes)
  - Natural integration into MetricsSummary composition

- **Cons/Risks:**
  - Adds another component to maintain
  - May feel redundant if users want all metrics in one view (but composition pattern addresses this)

- **Architectural Alignment:** High – follows established patterns, respects component composition, maintains consistency

- **Estimated Complexity:** Low-Medium – straightforward component creation following existing patterns, estimated 8-12 hours

- **Risk Factors:**
  - Need to handle edge cases (None values for CPI/SPI, 'overrun' string for TCPI)
  - Color threshold selection may need business input (currently using standard EVM thresholds)

### Approach B – Extend EarnedValueSummary Component

- **Summary:** Add CPI, SPI, TCPI, CV, and SV cards to the existing `EarnedValueSummary.tsx` component, expanding it from 3 cards to 8 cards.

- **Pros:**
  - Single component for all earned value related metrics
  - Fewer components to maintain
  - All EVM metrics in one place

- **Cons/Risks:**
  - Violates single responsibility principle (component becomes too large)
  - Mixes different concerns (earned value calculation vs. performance indices)
  - Harder to test and reason about
  - May become cluttered with too many cards
  - Less flexible for future extensions

- **Architectural Alignment:** Low – violates separation of concerns, makes component harder to maintain

- **Estimated Complexity:** Medium – requires refactoring existing component, risk of breaking changes

- **Risk Factors:**
  - Breaking existing EarnedValueSummary usage
  - Component becomes too complex

### Approach C – Tabbed EVM Metrics View

- **Summary:** Create a new tab in project/WBE/cost element detail pages specifically for "EVM Performance" with a more detailed view including charts and trend analysis.

- **Pros:**
  - More space for detailed visualization
  - Can include charts and trend analysis
  - Clear separation from other metrics

- **Cons/Risks:**
  - Requires UI changes to detail pages (adds new tab)
  - More complex than basic summary display
  - May be overkill for Sprint 4 basic requirement
  - Users may miss it if it's in a separate tab

- **Architectural Alignment:** Medium – valid approach but exceeds basic requirement

- **Estimated Complexity:** High – requires tab changes, more complex layout, potential chart integration

- **Risk Factors:**
  - Scope creep beyond basic summary display
  - May conflict with future E4-009 (Project Performance Dashboard)

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### Principles Followed (for Approach A)

- **Single Responsibility:** EVMSummary component focused solely on displaying EVM performance indices and variances
- **Component Composition:** Integrates into MetricsSummary following established pattern
- **Reusability:** Can be used at project, WBE, and cost element levels
- **Consistency:** Follows exact patterns from BudgetSummary, CostSummary, EarnedValueSummary
- **Separation of Concerns:** Backend provides data, frontend displays it
- **Time-Machine Consistency:** Respects control date for all calculations

### Potential Maintenance Burden

- **Color Threshold Configuration:**
  - Currently hardcoded thresholds (CPI/SPI < 0.95 = red, etc.)
  - May need to make configurable if business rules change
  - Consider extracting to constants or configuration

- **Edge Case Handling:**
  - None values for CPI/SPI need clear "N/A" or "Not Available" display
  - 'overrun' string for TCPI needs special handling
  - Zero values for CV/SV need appropriate display (not just "€0.00")

- **Future Extensions:**
  - E4-009 (Project Performance Dashboard) may want to reuse EVM Summary component
  - E4-007 (Cost Performance Report) may want to include EVM Summary data
  - Consider making component flexible enough for reuse in different contexts

### Testing Challenges

- **Edge Cases to Test:**
  - CPI = None (AC = 0)
  - SPI = None (PV = 0)
  - TCPI = 'overrun' (BAC ≤ AC)
  - TCPI = None (BAC = AC = 0)
  - CV = 0 (on budget)
  - SV = 0 (on schedule)
  - CV < 0 (over-budget)
  - SV < 0 (behind-schedule)
  - Large positive/negative variances

- **Visual Testing:**
  - Color coding correctness for different threshold ranges
  - Icon selection for different statuses
  - Responsive layout (mobile, tablet, desktop)
  - Dark mode theme support

- **Integration Testing:**
  - Component appears in MetricsSummary at all levels
  - Time-machine control date updates trigger re-fetch
  - Loading states display correctly
  - Error states handled gracefully

- **Data Consistency:**
  - Verify displayed values match API response
  - Verify formatting (currency, percentages) is correct
  - Verify control date is displayed and matches time-machine

---

## Risks, Unknowns, and Ambiguities

### Business Rules Clarified

- ✅ **CPI Display:** Show as decimal (e.g., "0.95") or percentage (e.g., "95%")? **Recommendation:** Decimal with 2 decimal places (e.g., "0.95") to match standard EVM practice, with optional percentage in description.
- ✅ **SPI Display:** Same as CPI - decimal format recommended.
- ✅ **TCPI Display:** Show as decimal or 'overrun' string? **Recommendation:** Display 'overrun' as text when applicable, otherwise decimal format.
- ✅ **CV/SV Display:** Currency format (e.g., "€-5,000.00") with color coding for positive/negative.
- ✅ **Color Thresholds:** Standard EVM thresholds:
  - CPI/SPI: < 0.95 (red), 0.95-1.0 (yellow), ≥ 1.0 (green)
  - TCPI: ≤ 1.0 (green), 1.0-1.1 (yellow), > 1.1 or 'overrun' (red)
  - **Note:** May need business confirmation on exact thresholds.

### Performance Considerations

- **API Calls:** Single API call per level (cost element, WBE, project) - efficient
- **Caching:** React Query will cache responses based on query key (level, entityId, controlDate)
- **Re-renders:** Component will re-render when control date changes (expected behavior)
- **Bundle Size:** Minimal impact - reuses existing Chakra UI and React Query

### Data Quality Risks

- **Missing Data:** If CPI/SPI are None, need clear indication that metric is not available
- **Zero Values:** Need to distinguish between "zero" (on target) and "None" (not calculable)
- **Negative Variances:** Valid and expected - UI must handle appropriately with red color coding

### Integration with Existing Components

- **MetricsSummary Integration:** Need to verify spacing and layout when EVMSummary is added
- **Tab Layout:** Metrics tab may become longer - consider if scrolling is acceptable or if tabs need reorganization
- **Mobile Responsiveness:** Grid layout should adapt to smaller screens (already handled by Chakra UI Grid)

### Future Considerations

- **E4-007 (Cost Performance Report):** May want to include EVM Summary data in tabular format
- **E4-009 (Project Performance Dashboard):** May want to reuse EVMSummary component or extract shared logic
- **E4-011 (Time Machine):** Already integrated via context - no additional work needed

---

## Summary & Next Steps

- **What:** Create EVM Summary Display component that shows current performance indices (CPI, SPI, TCPI) and variances (CV, SV) at project, WBE, and cost element levels, integrated into the existing MetricsSummary composition.

- **Why:** Provide project managers with a quick visual assessment of project health using industry-standard EVM metrics, complementing existing budget, cost, and earned value summaries.

- **Recommended Approach:** **Approach A – Dedicated EVMSummary Component**, following the exact patterns established by BudgetSummary, CostSummary, and EarnedValueSummary. This maintains consistency, follows single responsibility principle, and enables easy testing and maintenance.

- **Business Rules Confirmed:**
  - CPI/SPI displayed as decimals (2 decimal places)
  - TCPI displayed as decimal or 'overrun' string
  - CV/SV displayed as currency with color coding
  - Color thresholds: CPI/SPI < 0.95 (red), 0.95-1.0 (yellow), ≥ 1.0 (green)
  - TCPI thresholds: ≤ 1.0 (green), 1.0-1.1 (yellow), > 1.1 or 'overrun' (red)
  - CV/SV: Positive (green), Zero (yellow), Negative (red)

- **Implementation Scope:**
  - Frontend component only (backend APIs already exist via E4-005)
  - Integration into MetricsSummary component
  - Theme support (dark/light mode)
  - Responsive layout
  - Loading and error states
  - Edge case handling (None values, 'overrun' string)

- **Next Steps:** Proceed to detailed planning with TDD-focused implementation plan, explicit component structure, color threshold constants, and comprehensive test scenarios covering all edge cases.

---

**Reference:** This analysis follows the PLA-1 high-level analysis template and leverages existing summary component patterns (E2-006, E3-002, E4-002), EVM aggregation endpoints (E4-005), and time-machine integration (E4-011). Context7's React Chart.js documentation confirms that Chart.js is already used in the codebase (BudgetSummary), but E4-006 basic display does not require charts - simple metric cards are sufficient for Sprint 4 deliverable.
