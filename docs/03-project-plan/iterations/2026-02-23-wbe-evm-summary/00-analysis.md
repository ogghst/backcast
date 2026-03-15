# ANALYSIS: WBE EVM Summary & Advanced Analysis

## Phase 1: Requirements Clarification

**User Intent**: Enhance the `WBEDetailPage` to provide comprehensive Earned Value Management (EVM) insights, similar to those available for Cost Elements but adjusted for hierarchical aggregation.

**Functional Requirements**:

1. Display core EVM metrics (BAC, PV, AC, EV, CPI, SPI, EAC, VAC, etc.) for the current WBE.
2. Provide visualization of status (at-a-glance health).
3. Offer "Advanced Analysis" (historical trends, progress curves).
4. Integrate with Time Machine for period-specific analysis.

**Non-Functional Requirements**:

1. Consistency with existing EVM dashboard patterns.
2. Performance: Avoid redundant calculations by using generic EVM endpoints.
3. Maintainability: Reuse components from `features/evm`.

---

## Phase 2: Context Discovery

### 2.1 Documentation & Codebase Review

- **Backend**: `EVMService` (`evm_service.py`) already provides `calculate_evm_metrics_batch` which supports `EntityType.WBE`. It aggregates child cost elements' data correctly.
- **Frontend Hooks**: `useEVMMetrics` and `useEVMTimeSeries` in `features/evm/api/useEVMMetrics.ts` are already generic and support `wbe` and `project` entity types.
- **Frontend Components**:
  - `EVMSummaryView`: A comprehensive dashboard showing metrics by category (Schedule, Cost, Performance, Forecast).
  - `EVMTimeSeriesChart`: A sophisticated Apache ECharts-based chart for S-curves and cost bridges.
  - `EVMAnalyzerModal`: A full-screen analysis dashboard.

---

## Phase 3: Solution Design

### Option 1: Inline Overview Dashboard

Integrate the `EVMSummaryView` directly into the "Overview" section of the `WBEDetailPage`, potentially replacing or enhancing the current `WBESummaryCard`.

- **UX**: Metrics are immediately visible when the page loads.
- **Implementation**:
  - Add `EVMSummaryView` to `WBEDetailPage`.
  - Fetch metrics using `useEVMMetrics('wbe', wbeId)`.
- **Pros**: High visibility, follows `CostElementDetailPage` "Overview" pattern but with more detail.
- **Cons**: Can make the page very long if many other sections (Child WBEs, Cost Elements) are present.

### Option 2: Dedicated "EVM Analysis" Tab

Add a new tab to the `WBEDetailPage` specifically for performance analysis.

- **UX**: Keeps the main overview clean; allows deep dive without cluttering the management view.
- **Implementation**:
  - Introduce `Tabs` component to `WBEDetailPage`.
  - Tab 1: Overview (current layout).
  - Tab 2: EVM Analysis (Summary + Charts).
- **Pros**: Best for complex hierarchical analysis; allows showing both summary and large charts without scrolling issues.
- **Cons**: Requires an extra click to see performance data.

### Option 3: Summary + Analysis Drawer/Modal

Keep the current `WBESummaryCard` but add a "Performance View" or "Advanced Analysis" button that opens a drawer or the existing `EVMAnalyzerModal`.

- **UX**: Fast access to details without leaving the context.
- **Implementation**:
  - Add a button to `WBESummaryCard` or `WBEDetailPage` header.
  - Use `EVMAnalyzerModal` from `features/evm`.
- **Pros**: Lowest implementation effort; reuses the most mature component (`EVMAnalyzerModal`).
- **Cons**: Performance data is "hidden" behind a button.

---

## Phase 4: Recommendation & Decision

### Comparison Summary

| Criteria           | Option 1 (Inline) | Option 2 (Tabs)       | Option 3 (Modal)  |
| :----------------- | :---------------- | :-------------------- | :---------------- |
| Development Effort | Low               | Medium                | Very Low          |
| UX Quality         | High (Direct)     | Excellent (Deep Dive) | Good (Contextual) |
| Flexibility        | Fair              | High                  | High              |
| Best For           | Simple WBEs       | High-level tracking   | Quick checks      |

### Recommendation

I recommend **Option 2 (Dedicated EVM Analysis Tab)** because it aligns best with the "Advanced Analysis" requirement. WBEs are often high-level containers where users want to see cumulative performance trends (S-curves) which require significant screen real estate.

**Alternative**: If a "Master-Detail" feel is preferred, **Option 1** with a collapsible card could also work well.

### Questions for Decision

1. Do you prefer the EVM metrics to be visible immediately on page load, or organized into a specific "Performance" tab?
2. Should the historical trend chart (S-curve) be visible by default, or only on demand?

> [!IMPORTANT]
> **Human Decision Point**: Please select a solution option (1, 2, or 3) to proceed to the PLAN phase.
