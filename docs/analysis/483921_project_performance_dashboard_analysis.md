# 483921 Project Performance Dashboard Analysis

**Timestamp:** 2025-11-19 09:24 CET
**User Story:** As a program performance lead, I want a single dashboard that overlays portfolio-level EV/PV/AC curves with key CPI/SPI/CV/SV/TCPI indicators and drill-down navigation so I can quickly spot problem WBEs without hopping across multiple reports.

---

## 1. Codebase Pattern Analysis

1. **Time-Phased Visualization (`frontend/src/components/Projects/BudgetTimeline.tsx`)**
   - Uses `react-chartjs-2` with explicit `ChartJS.register(...)`, Chakra layout primitives, and helper utilities (`aggregateTimelines`, `generateTimeSeries`, EV overlay build).
   - Respects the architectural pattern of delegating heavy calculations to utility modules under `frontend/src/utils/` and pulling authoritative data via typed client services (`CostTimelineService`, `EarnedValueEntriesService`).

2. **Metric Card Grid (`frontend/src/components/Projects/EarnedValueSummary.tsx`)**
   - Fetches data through `useQuery` hooks hitting `EarnedValueService` & `EvmMetricsService`, hydrates Chakra `Grid`/`VStack` cards with shared formatting helpers, and uses status indicator utilities to colorize KPI tiles.
   - Demonstrates layering: context (`useTimeMachine`) → data services (`client`) → presentation (cards) → icons from `react-icons`.

3. **Report + DataTable Layout (`frontend/src/components/Reports/CostPerformanceReport.tsx`, `VarianceAnalysisReport.tsx`)**
   - Standardizes report shells with heading plus filter controls, `DataTable` for drillable rows, and shared formatting functions living in-component.
   - Depends on `ReportsService` endpoints, `useNavigate` for route transitions, and Chakra theming via `useColorModeValue`.

**Architectural Layers Observed:**
UI (Chakra components, DataTable) → Client SDK (`@/client`) → FastAPI routes → SQLModel services. React Query manages data flow, TimeMachineContext injects the global control-date filter, and utility modules house aggregation math. New features should slot into this layering without bypassing abstractions.

---

## 2. Integration Touchpoint Mapping

- **Frontend Modules to Extend:**
  - `frontend/src/components/Reports/` namespace for dashboard shell + shared report styling.
  - `frontend/src/components/Projects/EarnedValueSummary.tsx` and `BudgetTimeline.tsx` for potential composition or shared helpers.
  - `frontend/src/context/TimeMachineContext.tsx` (read-only) to ensure the dashboard honors the global control date.

- **Backend / Client Services:**
  - `ReportsService` (likely add `/project-performance-dashboard` API or reuse aggregated endpoints).
  - `EvmMetricsService`, `CostTimelineService`, `EarnedValueService`, `CostAggregationService` (existing) provide inputs; assess whether new aggregation endpoints are required for combined data payloads.
  - Authentication/session layers unchanged; rely on existing FastAPI routers under `backend/app/api/routes`.

- **External Dependencies & Config:**
  - `react-chartjs-2` + `chart.js` already in use; follow tree-shakable registration per Context7 guidance (register only required controllers/elements, ensure refs for gradients if needed).
  - Theme tokens and spacing from Chakra Design System; colors align with tokens (no hard-coded values outside palette except when matching precedent).
  - Any new settings (e.g., dashboard thresholds) belong in `backend/app/core/config.py` and `.env` templates if they become user-configurable.

---

## 3. Abstraction Inventory

- **Visualization Helpers:** `buildEarnedValueTimeline`, `aggregateTimelines`, `generateTimeSeries`, progression calculators under `frontend/src/utils` for turning backend payloads into chart datasets.
- **Status Indicator Helpers:** Patterns in `EarnedValueSummary` for CPI/SPI/TCPI and in `VarianceAnalysisReport` for severity badges—can refactor into shared utility (`evmStatusHelpers.ts`) instead of duplicating.
- **Data Fetching Patterns:** React Query hooks with deterministic `queryKey` arrays, each respecting `useTimeMachine` control date; `DataTable` component handles column config, filtering, resizing.
- **Testing Utilities:** Vitest specs under `frontend/src/components/Projects/__tests__/` and Playwright suites (e.g., `frontend/tests/project-cost-element-tabs.spec.ts`) provide fixtures for ensuring charts render with legends/toggles.
- **Routing and Layout:** Navigation handled via TanStack Router; dashboards typically live under `/projects/:id/...` or `/reports/...` routes defined in `frontend/src/routes`.

---

## 4. Alternative Approaches

| Approach | Description | Pros | Cons | Complexity | Risks |
| --- | --- | --- | --- | --- | --- |
| **A. Composite Dashboard Page** | Build a dedicated `ProjectPerformanceDashboard` component that composes existing `BudgetTimeline`, `EarnedValueSummary`, and a new KPI trend widget, orchestrated via a single `/reports/project-performance-dashboard` route. | Reuses proven components; minimal new logic; consistent UI. | Data duplication (multiple queries); limited cross-widget interaction; may need extra glue for filters. | Medium | Higher network cost; tight coupling between cards without shared store. |
| **B. Backend Aggregated Endpoint + Custom Visualization** | Create a new API aggregating PV/EV/AC curves + KPI snapshots in one payload, then render a bespoke multi-series chart (stacked area + sparkline cards). | Single network call; deterministic alignment of metrics; easier to cache. | Requires backend service orchestration; new DTOs/tests; larger change surface. | High | Increased backend complexity; risk of duplicating business logic already in other services. |
| **C. Extend Existing Reports with Dashboard Mode** | Add a "Dashboard" tab to the Cost Performance Report route that switches layout from table to visual summary using shared hooks. | Shares routing/nav; reduces new navigation work; leverages existing permissions. | Might overload existing report context; requires conditional rendering logic; tab may be overlooked. | Medium-Low | UI clutter; potential regressions in current report behavior/tests. |

**Alignment Notes:** Approach A aligns best with incremental change and reuses abstractions; Approach B offers cleaner data contracts but touches more layers; Approach C is simplest but risks UX dilution.

---

## 5. Architectural Impact Assessment

- **Principles Observed:** Continue using React Query for server state, respect Time Machine control date propagation, and keep visualization logic in utilities rather than components. Maintain separation between FastAPI services and SQLModel operations (no raw queries in routers).
- **Future Maintenance:** Introducing another bespoke KPI widget without shared helpers could reintroduce duplication of formatting/status logic—mitigate by extracting utilities. Ensure dashboard remains configurable so adding new metrics doesn’t require rewiring multiple files.
- **Testing Challenges:** Need Vitest coverage for chart config builders (snapshot-friendly), React Testing Library for control toggles, and likely a Playwright spec verifying dashboard tabs render under various control dates. Backend additions require Pytest service + API tests to uphold TDD.

---

## Ambiguities & Unknowns

- Scope of “Project Performance Dashboard” (single project vs. portfolio) is implied but not explicitly stated—assumed per epic description to live under Reports.
- Required interactivity (filtering by WBE, drill-down navigation) needs confirmation.
- Threshold customization (for CPI/SPI color rules) currently hard-coded; unclear if dashboard should allow user-defined targets.

---

## Summary

E4-009 should deliver a composed dashboard page that reuses existing timeline and metric abstractions, respects React Query + TimeMachine patterns, and possibly introduces a lightweight aggregation layer for KPI cards. The recommended next step is to confirm scope (project-level vs. portfolio) and select Approach A unless backend stakeholders prefer a consolidated payload.
