# Analysis: EVM Summary S-Curve Centric Dashboard Redesign

**Created:** 2026-05-12
**Request:** Redesign EVMSummaryView from collapsible metric cards to a single cohesive "S-Curve Centric Dashboard" (Approach B) with compact S-curve, KPI dot strip, forecast comparison bar, and expandable detail section.

---

## Clarified Requirements

### Problem Statement

The current EVMSummaryView presents EVM metrics as four collapsible Ant Design Collapse panels (Schedule, Cost, Performance, Forecast), each containing MetricCard components in a grid. This layout forces users to scan text-heavy cards to assess project health. There is no at-a-glance visual indicator -- no S-curve shape, no color-coded health summary, no spatial comparison of budget vs. forecast. Both junior and senior PMs lack a "quick read" on whether the project is healthy.

### Functional Requirements

1. Replace the four-panel Collapse layout with a single cohesive Card
2. Lead with a compact S-curve area chart (~220px height) showing PV/EV/AC area fills with variance shading between curves
3. Add a KPI dot strip with 6 inline indicators (CPI, SPI, BAC, EAC, VAC, Progress) using status-colored dots and numeric values
4. Add a forecast comparison bar showing BAC vs EAC and AC vs ETC as horizontal bars for spatial budget comparison
5. Keep an expandable detail section for remaining metrics (SV, CV, AC, PV, EV, ETC) using existing MetricCard components
6. Preserve the "Advanced" button that opens EVMAnalyzerModal
7. Thread timeSeries data from ProjectEVMAnalysis page into EVMSummaryView (currently only metrics are passed)

### Non-Functional Requirements

- No new npm dependencies -- use existing ECharts + Ant Design
- Visual consistency with Backcast soft-light design system (Ant Design v6, muted status colors, Ubuntu font)
- Responsive layout -- works at 768px+ viewport width
- Performance: compact S-curve must render in <50ms (small dataset, no DataZoom)
- Accessibility: ARIA labels on KPI indicators, keyboard-navigable expandable section
- TypeScript strict mode compliance, ESLint clean

### Constraints

- EVMAnalyzerModal stays unchanged
- MetricCard component stays unchanged (reused in expandable detail section)
- EVMTimeSeriesChart stays unchanged (full interactive chart remains separate)
- EVM types (EVMMetricsResponse, EVMTimeSeriesResponse) stay unchanged
- All existing tests for MetricCard and EVMAnalyzerModal remain passing
- EVMSummaryView tests will need rewriting (currently 289 lines testing Collapse-based layout)

### Assumptions

1. The compact S-curve will use `transformEVMProgressionData()` from existing `dataTransformers.ts` -- same data transform, different ECharts config
2. The `EVMTimeSeriesResponse.points` array provides sufficient data for the compact chart (no additional API call needed)
3. The 6 KPI indicators in the dot strip are static selection (CPI, SPI, BAC, EAC, VAC, Progress) -- not user-configurable
4. The forecast comparison bar uses CSS-based horizontal bars (not ECharts) since it is a simple two-bar comparison
5. The expandable detail section uses Ant Design Collapse with a single panel, not the current four-panel layout
6. The `progress_percentage` field in `EVMMetricsResponse` represents the "Progress" KPI indicator
7. Null metric values display "N/A" with a neutral/warning dot status

---

## Context Discovery

### Product Scope

- **EVM Requirements (Section 8.1):** "Visual displays of CPI and SPI trending over time, Forecast EAC trending, EV vs. PV vs. AC curves" -- the S-curve directly addresses this requirement
- **EVM Requirements (Section 8.2):** "Dashboard Configuration with selectable visual representations: line graphs for trend analysis, bar charts for period comparisons, gauge displays for current performance indices" -- the KPI strip and forecast bar address this
- **EVM Requirements (Section 12.3):** "Training support on EVM principles, real-world scenarios simulation" -- the S-curve visual shape helps junior PMs learn EVM curve interpretation
- **Functional Requirements:** No specific user story directly maps to this redesign; it is a UX enhancement within the existing EVM Analysis page

### Architecture Context

- **Bounded contexts:** EVM context (frontend feature module `features/evm/`)
- **Existing patterns to follow:**
  - ECharts chart pattern: `EChartsBaseChart` wrapper with `ResizeObserver`, theme integration via `useEChartsTheme()` hook
  - Component composition: new sub-components in `features/evm/components/`
  - Data transforms: `utils/dataTransformers.ts` provides `transformEVMProgressionData()` -- reusable for compact chart
  - ECharts config builders: `utils/echartsConfig.ts` provides `buildTimeSeriesOptions()` and lower-level builders
  - Theme: `utils/echartsTheme.ts` provides `useEChartsColors()`, `useEChartsTheme()`, and `antDesignTheme` color palette
  - Status calculation: `types.ts` provides `getMetricStatus()` returning "good" | "warning" | "bad"
  - Value formatting: `MetricCard.tsx` contains `formatValue()` utility (currency/percentage/number)
- **Architectural constraints:**
  - No repository pattern -- services access DB directly (backend, not relevant here)
  - No new dependencies
  - Must pass MyPy/Ruff/ESLint zero errors
  - Must maintain 80%+ test coverage on modified files

### Codebase Analysis

**Frontend:**

Key files examined:

| File | Role | Reuse Potential |
|------|------|----------------|
| `features/evm/components/EVMSummaryView.tsx` | Current summary view (193 lines) | Full rewrite target |
| `features/evm/components/MetricCard.tsx` | Individual metric card (202 lines) | Reused in expandable detail section |
| `features/evm/components/EVMTimeSeriesChart.tsx` | Full interactive chart wrapper (101 lines) | Unchanged |
| `features/evm/components/EVMAnalyzerModal.tsx` | Advanced modal (559 lines) | Unchanged |
| `features/evm/components/charts/EChartsBaseChart.tsx` | Base chart wrapper with ResizeObserver (344 lines) | Reused by compact S-curve |
| `features/evm/components/charts/EChartsTimeSeries.tsx` | Time series chart logic (462 lines) | Pattern reference, not directly reused |
| `features/evm/utils/dataTransformers.ts` | Data transform utilities (285 lines) | `transformEVMProgressionData()` reused directly |
| `features/evm/utils/echartsConfig.ts` | ECharts config builders (924 lines) | New builder needed for compact area chart |
| `features/evm/utils/echartsTheme.ts` | Theme hooks and palette (251 lines) | `useEChartsTheme()` and color constants reused |
| `features/evm/types.ts` | EVM types, METRIC_DEFINITIONS, getMetricStatus (489 lines) | Fully reused |
| `pages/projects/ProjectEVMAnalysis.tsx` | Page component (157 lines) | Minor modification to thread timeSeries prop |

**State management:**
- `useEVMMetrics()` and `useEVMTimeSeries()` hooks are already called in `ProjectEVMAnalysis.tsx`
- `timeSeries` data is fetched but NOT passed to `EVMSummaryView` -- only to `EVMTimeSeriesChart` and `EVMAnalyzerModal`
- The redesign requires threading `timeSeries` to `EVMSummaryView` as a new prop

**Existing test coverage:**
- `EVMSummaryView.test.tsx` (289 lines): Tests Collapse panels, metric categories, Advanced button, null handling, edge cases -- will need full rewrite
- `MetricCard.test.tsx`: Unchanged, continues passing
- `EVMAnalyzerModal.test.tsx`: Unchanged, continues passing

**Data availability:**
- `EVMMetricsResponse` provides: bac, pv, ac, ev, cv, sv, cpi, spi, eac, vac, etc, progress_percentage
- `EVMTimeSeriesResponse.points[]` provides: date, pv, ev, ac, forecast, actual, cpi, spi
- `getMetricStatus(key, value)` provides: "good" | "warning" | "bad"
- `METRIC_DEFINITIONS` provides: name, description, category, targetRanges, format for each metric
- `formatValue(value, format)` in MetricCard provides: currency/percentage/number formatting

---

## Solution Options

### Option 1: Proposed Approach B -- S-Curve Centric Dashboard (As Described)

**Architecture & Design Patterns:**

Create three new sub-components and rewrite EVMSummaryView:

1. `EVMCompactSCurve.tsx` -- New ECharts area chart component (~220px height)
   - Uses `EChartsBaseChart` wrapper for consistent lifecycle management
   - Uses `transformEVMProgressionData()` for PV/EV/AC data extraction
   - New builder function in `echartsConfig.ts`: `buildCompactSCurveOptions()` -- area fills with opacity, no DataZoom, no legend (too compact), minimal axes, tooltip on hover
   - Variance shading: visual map layer between EV and AC curves showing cost variance (green fill between EV>AC, red fill between AC>EV)
   - Accepts `EVMTimeSeriesResponse` as prop

2. `EVMKPIIndicator.tsx` -- Inline dot + label + value component
   - Pure CSS + Ant Design Typography
   - Props: label, value, status ("good" | "warning" | "bad"), format
   - Renders: colored dot (8px circle) + label text + formatted value
   - Uses `getMetricStatus()` for dot coloring via theme tokens (colorSuccess/colorWarning/colorError)
   - Uses `formatValue()` logic (extract to shared util or inline)

3. `EVMForecastBar.tsx` -- CSS-based horizontal comparison bars
   - Two bar pairs: BAC vs EAC (budget comparison), AC vs ETC (remaining work)
   - Pure CSS with inline styles, no ECharts
   - Uses theme tokens for colors: primary for BAC/ETC, warning for EAC, muted for AC
   - Width calculated as percentage of max(BAC, EAC) for each bar pair

4. Rewrite `EVMSummaryView.tsx` -- New layout:
   - Single Ant Design Card wrapping all sections
   - Header row: "EVM Summary" title + Advanced button
   - Section 1: Compact S-curve (full width, ~220px)
   - Section 2: KPI dot strip (horizontal flex row of 6 indicators)
   - Section 3: Forecast comparison bars (full width)
   - Section 4: Expandable Collapse with single panel "Detail Metrics" containing existing MetricCard grid
   - New prop: `timeSeries?: EVMTimeSeriesResponse` (optional for backward compatibility)

5. Minor update to `ProjectEVMAnalysis.tsx`:
   - Pass `timeSeries` to `EVMSummaryView` component

**UX Design:**

- Users see the S-curve immediately on page load -- visual shape conveys project health at a glance
- The EV curve below the PV curve = behind schedule (visual gap). The AC curve above the EV curve = over budget (shaded area).
- KPI dot strip below provides exact numbers with traffic-light coloring for quick triage
- Forecast bars show budget overspend visually (EAC bar extending past BAC bar)
- Expandable section available for detailed analysis without cluttering the primary view

**Implementation:**

- 5 files to create/modify (3 new components + 1 rewrite + 1 minor prop threading)
- New builder function in `echartsConfig.ts` for compact area chart options
- Extract `formatValue` to shared utility or inline in `EVMKPIIndicator`
- Full test rewrite for `EVMSummaryView.test.tsx`
- New test files for each sub-component

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Matches request exactly; strong visual-first UX; reuses existing ECharts infrastructure and data transforms; compact chart is lightweight (~220px, no zoom/interactivity); forecast bar uses pure CSS (fast); expandable section preserves MetricCard for detail; backward compatible (timeSeries prop is optional) |
| Cons            | 3 new components increases file count; variance shading in compact chart requires careful ECharts area series configuration; CSS-based forecast bar may need manual responsive adjustments; KPI indicator format logic duplicates MetricCard formatValue |
| Complexity      | Medium -- mostly frontend composition with one moderately complex ECharts config |
| Maintainability | Good -- each sub-component is single-responsibility; reuses existing theme/transform infrastructure |
| Performance     | Excellent -- compact chart renders small dataset with no zoom; CSS bars have zero rendering overhead; KPI strip is pure DOM |

---

### Option 2: Incremental Enhancement -- Add S-Curve to Existing Layout

**Architecture & Design Patterns:**

Keep the existing Collapse-based EVMSummaryView largely intact, but add a compact S-curve above the Collapse panels. Instead of a full redesign, layer the visual on top of the current structure.

1. Create `EVMCompactSCurve.tsx` -- same as Option 1
2. Modify `EVMSummaryView.tsx` to add the S-curve above the existing Collapse, plus a KPI summary row
3. No forecast bar, no new KPI indicator component -- use existing MetricCard in "small" size for KPI summary
4. Collapse panels remain unchanged (all four categories)

**UX Design:**

- S-curve at the top provides visual health assessment
- Below it, a row of small MetricCards for CPI, SPI, BAC, EAC, VAC, Progress
- Below that, the existing four Collapse panels with full metric breakdown
- Less radical change from current UX -- users who know the old layout feel less disoriented

**Implementation:**

- 1 new component + 1 modified file + 1 minor prop threading
- Simpler implementation -- no forecast bar, no expandable detail redesign
- Fewer tests to rewrite

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Smaller change scope; less risk; existing tests mostly survive with minor additions; preserves familiar four-panel structure for users who prefer text; faster to implement |
| Cons            | Does not achieve the "single cohesive card" goal; page remains visually busy with Collapse panels always visible; no forecast comparison bar; KPI summary is text-based (no traffic-light dots); does not fully address the "at-a-glance health" problem since text panels still dominate the viewport |
| Complexity      | Low -- add one component and a summary row |
| Maintainability | Good -- minimal change to existing structure |
| Performance     | Excellent -- same as Option 1 for the S-curve addition |

---

### Option 3: Widget-Based S-Curve Card (Dashboard Integration)

**Architecture & Design Patterns:**

Build the S-Curve Centric Dashboard as a dashboard widget using the existing widget system (`react-grid-layout`, widget registry, context bus). The widget can be placed on any dashboard page, not just the EVM Analysis page.

1. Create a new widget type `evm-summary` in the widget system
2. The widget renders the S-curve + KPI strip + forecast bar as a single draggable card
3. Replace EVMSummaryView on the EVM Analysis page with this widget
4. Widget can also be added to the project dashboard for at-a-glance health monitoring

**UX Design:**

- Same visual layout as Option 1 inside a draggable widget card
- Users can resize and reposition the EVM summary on their dashboard
- Can combine with other widgets (Gantt chart, cost breakdown, etc.) on a single dashboard view
- Widget persistence saves layout preferences

**Implementation:**

- Requires understanding the widget system (`docs/02-architecture/how-to-create-a-widget.md`, `dashboard-developer-guide.md`)
- Must register widget in the widget registry
- Must handle widget lifecycle (mount, resize, persist layout)
- More architectural work but enables future composability

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Maximum reusability; integrates with dashboard infrastructure; users can customize EVM widget placement; follows established widget pattern; enables project dashboard EVM monitoring |
| Cons            | Significantly more complex; requires widget registry integration; widget system may impose layout constraints on the S-curve; introduces coupling between EVM feature and dashboard feature; overkill if the widget is only ever used on the EVM Analysis page; testing scope expands to widget lifecycle |
| Complexity      | High -- widget system integration + all of Option 1's work |
| Maintainability | Fair -- introduces cross-feature dependency |
| Performance     | Good -- widget system adds minimal overhead, but react-grid-layout adds layout calculation cost |

---

## Comparison Summary

| Criteria           | Option 1 (S-Curve Centric) | Option 2 (Incremental)   | Option 3 (Widget-Based) |
| ------------------ | -------------------------- | ------------------------ | ----------------------- |
| Development Effort | Medium (3-4 days)          | Low (1-2 days)           | High (5-7 days)         |
| UX Quality         | High -- cohesive dashboard | Medium -- layered add-on | High -- if used as widget |
| Flexibility        | Medium -- fixed layout     | Low -- constrained by existing | High -- dashboard composable |
| Best For           | Focused EVM page redesign  | Quick visual enhancement | Cross-page EVM monitoring |
| Risk               | Medium -- full rewrite of SummaryView | Low -- additive change | High -- cross-feature coupling |
| Test Rewrite Scope | Full EVMSummaryView rewrite + 3 new component tests | Minor test additions | Full rewrite + widget tests |

---

## Recommendation

**I recommend Option 1 (S-Curve Centric Dashboard as described in the feature request) because:**

1. The request is well-defined with clear visual layout specifications. Option 1 implements exactly what is asked.
2. The existing ECharts infrastructure (EChartsBaseChart, echartsTheme, dataTransformers, echartsConfig) provides strong reusable foundations. The compact S-curve is essentially a new ECharts config builder using existing data transforms -- low risk.
3. The forecast comparison bar using pure CSS avoids additional chart rendering overhead and is straightforward to implement.
4. The KPI indicator component is trivially simple (dot + text + value) and provides clear visual communication.
5. Backward compatibility is preserved via the optional `timeSeries` prop -- if timeSeries is undefined, the S-curve section can show a skeleton or empty state.

**Alternative consideration:** If timeline is constrained or the team wants to de-risk the change, Option 2 provides a quick win (S-curve added above existing panels) that can be iterated into Option 1 in a follow-up cycle. However, this results in two layout changes in quick succession, which may confuse users.

Option 3 is attractive architecturally but introduces cross-feature coupling that is not justified unless there is a concrete requirement to place EVM summaries on the project dashboard page. That should be a separate iteration if needed.

---

## Decision Questions

1. **Variance shading detail:** Should the compact S-curve show variance shading between EV and AC curves (cost variance), between EV and PV curves (schedule variance), or both? This affects the visual complexity of the chart. Recommendation: shade between EV and AC only (cost variance is the most actionable signal), since schedule variance is harder to show as an area fill without visual clutter at 220px.

2. **Forecast bar thresholds:** Should the forecast comparison bar show percentage labels (e.g., "EAC is 104% of BAC") in addition to the currency values? This adds readability but increases the visual density of that section.

3. **TimeSeries optional behavior:** When `timeSeries` is undefined (e.g., API error or loading), should the compact S-curve section: (a) show an empty placeholder, (b) be hidden entirely, or (c) show a skeleton loader? This affects the layout stability of the card. Recommendation: show a skeleton loader with the same height to prevent layout shift.

4. **KPI dot strip -- which 6 indicators?** The request specifies CPI, SPI, BAC, EAC, VAC, Progress. An alternative set could include CV and SV (variance absolute values) instead of BAC and VAC. BAC is a static baseline value that never changes color. Should BAC be replaced with a more dynamic metric like TCPI (To Complete Performance Index) or CV?

---

## References

- [EVM Components Guide](../../02-architecture/evm-components-guide.md) -- component architecture and integration patterns
- [EVM Calculation Guide](../../02-architecture/evm-calculation-guide.md) -- data sources and API usage
- [EVM Requirements](../../01-product-scope/evm-requirements.md) -- Section 8 (Trend Analysis and Dashboards)
- [Frontend Coding Standards](../../02-architecture/frontend/coding-standards.md) -- TypeScript strict mode, component patterns
- [ADR-011: Generic EVM Metric System](../../02-architecture/decisions/ADR-011-generic-evm-metric-system.md) -- metric system architecture decisions
- [ADR-012: EVM Time-Series Data Strategy](../../02-architecture/decisions/ADR-012-evm-time-series-data-strategy.md) -- time-series data approach
