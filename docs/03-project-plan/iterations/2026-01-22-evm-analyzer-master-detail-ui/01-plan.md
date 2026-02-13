# Plan: EVM Analyzer with Master-Detail UI

**Created:** 2026-01-22
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 - Phased Implementation with Reusable Architecture
**Phases Included:** Phase 1 (Cost Element) + Phase 2 (WBE/Project Support)
**Phase 3 Status:** Deferred to Backlog

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 - Phased Implementation with Reusable Architecture
- **Architecture**: Generic EVM metric system supporting polymorphic entity types (cost elements, WBEs, projects) with reusable frontend components
- **Key Decisions**:
  1. **EVMMetric structure**: Flat response structure with all metrics explicitly defined (NOT a list of EVMMetricBase objects)
  2. **Phase 2 included**: WBE and project support in this implementation
  3. **Time-series granularity**: Pre-calculate server-side, new request when granularity changes
  4. **Chart zoom**: Use Ant Design built-in zoom capabilities
  5. **Gauge design**: Traditional semi-circle gauge (speedometer style)
  6. **Multi-entity aggregation**: Backend aggregation (not frontend)
  7. **Metric descriptions**: Static (hardcoded in frontend)
  8. **Default chart view**: Weekly granularity
  9. **Historical data**: Show empty state if no data available
  10. **Aggregation method**: Weighted by BAC for indices, sum for amounts
  11. **Time-series data range**: Context-dependent (cost element: zoomed to schedule range; project: from start to max(end, control_date))

### Success Criteria

#### Functional Criteria

**Phase 1 - Cost Element Support:**

- [ ] ForecastComparisonCard displays metrics organized by topic (Schedule, Cost, Variance, Performance, Forecast) VERIFIED BY: Visual inspection + unit tests
- [ ] "Advanced" button opens EVM Analyzer modal VERIFIED BY: E2E test
- [ ] Modal displays all metrics with enhanced visualizations VERIFIED BY: E2E test
- [ ] Modal displays semi-circle gauges for CPI/SPI (traditional EVM style) VERIFIED BY: Visual inspection + unit tests
- [ ] Modal displays two timeline charts (PV/EV/AC progression and Forecast vs Actual) VERIFIED BY: E2E test
- [ ] Timeline charts support day/week/month granularity selector VERIFIED BY: E2E test
- [ ] All queries respect TimeMachineContext (control_date, branch, mode) VERIFIED BY: Integration tests
- [ ] Components are generic (accept EntityType parameter) VERIFIED BY: Type checking + unit tests
- [ ] Backend endpoints support batch queries for multiple entities VERIFIED BY: API integration tests

**Phase 2 - WBE and Project Support:**

- [ ] WBE EVM metrics calculate correctly from child cost elements VERIFIED BY: Integration tests with known datasets
- [ ] Project EVM metrics calculate correctly from child WBEs VERIFIED BY: Integration tests with known datasets
- [ ] Multi-entity aggregation produces correct sums (amounts) and weighted averages (indices) VERIFIED BY: Unit tests
- [ ] UI seamlessly switches between entity types VERIFIED BY: E2E tests
- [ ] All Phase 1 criteria maintained VERIFIED BY: Regression tests

#### Technical Criteria

- [ ] Performance: Summary view renders in <500ms VERIFIED BY: Browser performance metrics
- [ ] Performance: Modal with charts renders in <2s VERIFIED BY: Browser performance metrics
- [ ] Performance: Time-series queries complete in <1s for 1-year range VERIFIED BY: Backend timing logs
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: TypeScript strict mode (zero errors) VERIFIED BY: CI pipeline
- [ ] Test Coverage: 80%+ for all new code VERIFIED BY: Coverage reports
- [ ] Accessibility: ARIA labels, keyboard navigation VERIFIED BY: Manual testing

#### Business Criteria

- [ ] User can understand EVM performance at a glance through organized metrics VERIFIED BY: User acceptance testing
- [ ] User can drill down into detailed analysis via modal VERIFIED BY: User acceptance testing
- [ ] User can track historical performance trends via charts VERIFIED BY: User acceptance testing

### Scope Boundaries

**In Scope:**

- Generic EVM metric schemas (backend) supporting cost elements, WBEs, and projects
- Multi-entity aggregation service layer (backend)
- Time-series data endpoints for PV/EV/AC and Forecast vs Actual charts
- Reusable EVM components (MetricCard, MetricCategorySection, EVMSummaryView, EVMGauge, EVMTimeSeriesChart, EVMAnalyzerModal)
- Custom hooks for EVM data fetching (useEVMMetrics, useEVMMetricsBatch, useEVMTimeSeries)
- Refactored ForecastComparisonCard using new generic components
- Generic API routes for all entity types (`/api/v1/evm/{entity_type}/{entity_id}/metrics`)
- WBE and project EVM calculations with child entity aggregation
- Time-travel support for all EVM queries via TimeMachineContext
- Documentation updates (API docs, component usage examples)

**Out of Scope (Phase 3 - Future Enhancement):**

- Multi-entity comparison view (side-by-side comparison)
- Benchmarking against historical baselines
- AI-powered insights and recommendations
- Real-time metric updates via websockets
- Materialized views for performance optimization (implement if needed based on metrics)
- Custom zoom controls beyond Ant Design built-in
- Internationalization (i18n) for metric descriptions

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                 | Files                                                                                              | Dependencies        | Success Criteria                                                                                                                                                                                                                              | Complexity   | Agent Type        |
| --- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ----------------- |
| 1   | Create generic EVMMetric Pydantic schemas                            | `backend/app/models/schemas/evm.py`                                                                | None                | Schemas compile with MyPy strict mode; All fields properly typed; Flat response structure (not list of metrics); Support for entity_type polymorphism                                                        | Medium       | Backend           |
| 2   | Implement multi-entity EVM service methods                           | `backend/app/services/evm_service.py`                                                              | Task 1              | Service methods compile; Type-safe polymorphic entity handling; Aggregation logic (sum for amounts, weighted avg for indices); Time-travel support maintained                                                | High         | Backend           |
| 3   | Implement time-series data service methods                           | `backend/app/services/evm_service.py`                                                              | Task 2              | Methods return correct data structure; Date grouping works (day/week/month); Handles empty data gracefully; Efficient queries (<1s for 1-year)                                                              | High         | Backend           |
| 4   | Create generic EVM API routes                                        | `backend/app/api/routes/evm.py` (new)                                                              | Task 1, 2, 3        | All endpoints defined; OpenAPI docs generate correctly; Request validation works; Error handling comprehensive; Route testing passes                                                                       | Medium       | Backend           |
| 5   | Write backend unit tests for EVM service                             | `backend/tests/unit/services/test_evm_service.py`                                                  | Task 2, 3           | 80%+ coverage; All aggregation logic tested; Edge cases covered (empty data, division by zero); Time-travel scenarios tested; Mock dependencies correctly                                               | High         | Backend           |
| 6   | Write backend integration tests for EVM API                          | `backend/tests/api/test_evm_routes.py` (new)                                                       | Task 4              | All endpoints tested; Time-travel queries tested; Multi-entity queries tested; Error responses tested; Database cleanup works; Tests run sequentially (no parallel execution)                              | Medium       | Backend           |
| 7   | Create frontend EVM types and interfaces                             | `frontend/src/features/evm/types.ts` (new)                                                         | Task 1              | Types match backend schemas; EntityType enum defined; EVMMetric interface complete; Time-series interfaces defined; TypeScript strict mode passes                                                        | Low          | Frontend          |
| 8   | Create MetricCard component                                          | `frontend/src/features/evm/components/MetricCard.tsx` (new)                                        | Task 7              | Component renders metric correctly; Size variants work; Description toggle works; Color coding correct; Accessibility (ARIA) present; Unit tests pass                                                    | Low          | Frontend          |
| 9   | Create EVMGauge component (semi-circle)                              | `frontend/src/features/evm/components/EVMGauge.tsx` (new)                                          | Task 7              | Gauge renders semi-circle; CPI/SPI ranges correct (0-2+); Color zones (red/yellow/green); Labels show correct values; Responsive; Unit tests pass                                                       | Medium       | Frontend          |
| 10  | Create MetricCategorySection component                               | `frontend/src/features/evm/components/MetricCategorySection.tsx` (new)                             | Task 7, 8           | Groups metrics by category; Grid/list layouts work; Section titles correct; Renders MetricCard components; Unit tests pass                                                                               | Low          | Frontend          |
| 11  | Create EVMTimeSeriesChart component                                  | `frontend/src/features/evm/components/EVMTimeSeriesChart.tsx` (new)                                 | Task 7              | Renders dual charts (progression, accuracy); Granularity selector works; Ant Design zoom functional; Loading states work; Empty state displays; Unit tests pass                                          | Medium       | Frontend          |
| 12  | Create EVMSummaryView component                                      | `frontend/src/features/evm/components/EVMSummaryView.tsx` (new)                                    | Task 7, 10          | Organizes metrics by topic; "Advanced" button present; Responsive layout; Loading states; Error handling; Unit tests pass                                                                                 | Medium       | Frontend          |
| 13  | Create EVMAnalyzerModal component                                    | `frontend/src/features/evm/components/EVMAnalyzerModal.tsx` (new)                                  | Task 8, 9, 11, 12   | Modal opens/closes correctly; All metrics display with gauges; Both charts render; Granularity selector functional; Scrollable content; Responsive; Unit tests pass                                       | High         | Frontend          |
| 14  | Create custom EVM hooks (useEVMMetrics, useEVMTimeSeries, etc.)      | `frontend/src/features/evm/api/hooks.ts` (new)                                                     | Task 7              | Hooks fetch data correctly; TanStack Query caching works; Error handling present; Loading states; TimeMachineContext integration; Unit tests pass                                                        | Medium       | Frontend          |
| 15  | Refactor ForecastComparisonCard to use EVMSummaryView               | `frontend/src/features/forecasts/components/ForecastComparisonCard.tsx`                            | Task 12, 14         | Backward compatible; Uses new components; "Advanced" button triggers modal; Visual regression tests pass; Existing tests still pass                                                                    | Medium       | Frontend          |
| 16  | Write frontend component tests                                       | `frontend/src/features/evm/components/__tests__/`                                                  | Task 8-15           | 80%+ coverage; Components testable; Mock hooks correctly; User interactions tested; Accessibility tests pass; Tests run sequentially                                                                   | High         | Frontend          |
| 17  | Write frontend E2E tests                                             | `frontend/tests/e2e/evm-analyzer.spec.ts` (new)                                                    | Task 15, 16         | Critical user flows covered; Modal opens; Charts render; Granularity changes; Entity switching works; Time-travel tested; Tests run sequentially                                                          | Medium       | Frontend          |
| 18  | Implement WBE EVM service methods (child aggregation)                | `backend/app/services/evm_service.py`                                                              | Task 2              | Aggregates child cost elements; Returns correct WBE metrics; Time-travel works; Branch mode respected; Unit tests pass                                                                                    | High         | Backend           |
| 19  | Implement Project EVM service methods (child aggregation)            | `backend/app/services/evm_service.py`                                                              | Task 18             | Aggregates child WBEs; Returns correct project metrics; Time-travel works; Branch mode respected; Unit tests pass                                                                                        | High         | Backend           |
| 20  | Extend API routes for WBE and Project entities                       | `backend/app/api/routes/evm.py`                                                                    | Task 4, 18, 19      | WBE endpoints work; Project endpoints work; Polymorphic routing correct; Integration tests pass                                                                                                            | Medium       | Backend           |
| 21  | Write WBE and Project EVM tests                                      | `backend/tests/unit/services/test_evm_service_wbe_project.py` (new)                                | Task 18, 19, 20     | Aggregation logic tested; Known datasets validated; Edge cases covered; 80%+ coverage; Tests run sequentially                                                                                             | High         | Backend           |
| 22  | Update frontend hooks to support WBE and Project entities            | `frontend/src/features/evm/api/hooks.ts`                                                           | Task 14, 20         | EntityType parameter works; All entity types fetch correctly; Type-safe; TypeScript strict mode passes                                                                                                    | Medium       | Frontend          |
| 23  | Update frontend components to support entity switching               | `frontend/src/features/evm/components/`                                                            | Task 22             | Entity type selector works; Components adapt to entity type; WBE/Project views render correctly; Unit tests pass                                                                                         | Medium       | Frontend          |
| 24  | Write WBE and Project frontend tests                                 | `frontend/src/features/evm/components/__tests__/`                                                  | Task 23             | WBE view tested; Project view tested; Entity switching tested; 80%+ coverage maintained; Tests run sequentially                                                                                          | Medium       | Frontend          |
| 25  | Performance optimization and profiling                               | `backend/app/services/evm_service.py`, `frontend/src/features/evm/`                                 | Task 3, 11          | Time-series queries <1s; Summary render <500ms; Modal render <2s; Database indexes added if needed; No N+1 queries; Profiling logs reviewed                                                               | Medium       | Backend/Frontend  |
| 26  | Documentation updates                                                | `docs/`, API docs, Component stories                                                                | Task 1-25           | API documentation complete; Component usage examples; README updates; Architecture decision record (ADR) created; Time-travel semantics documented                                                        | Low          | Backend/Frontend  |
| 27  | Final integration testing and bug fixes                              | All files                                                                                          | Task 1-26           | All acceptance criteria met; All tests pass; Zero linting errors; Performance benchmarks met; User acceptance testing complete; Regression tests pass                                                      | High         | Backend/Frontend  |

### Task Dependency Graph

```yaml
# Task Dependency Graph for Parallel Execution
# Tasks with empty dependencies can run in parallel (Level-0)
# Frontend UI components (8-13) can run in parallel with backend service (2-3)
# All tests MUST run sequentially due to database constraints

tasks:
  # Level 0: Can run immediately
  - id: BE-001
    name: "Create generic EVMMetric Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: []

  # Level 1: Depends on BE-001
  - id: BE-002
    name: "Implement multi-entity EVM service methods"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Implement time-series data service methods"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: FE-001
    name: "Create frontend EVM types and interfaces"
    agent: pdca-frontend-do-executor
    dependencies: [BE-001]

  # Level 2: Depends on BE-003 and FE-001
  - id: BE-004
    name: "Create generic EVM API routes"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: FE-002
    name: "Create MetricCard component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Create EVMGauge component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-004
    name: "Create MetricCategorySection component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-005
    name: "Create EVMTimeSeriesChart component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-006
    name: "Create EVMSummaryView component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-004]

  # Level 3: Depends on FE components
  - id: FE-007
    name: "Create EVMAnalyzerModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002, FE-003, FE-005, FE-006]

  - id: FE-008
    name: "Create custom EVM hooks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, BE-004]

  # Level 4: Integration and testing (SEQUENTIAL - must run after implementation)
  - id: BE-005
    name: "Write backend unit tests for EVM service"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-003]

  - id: BE-006
    name: "Write backend integration tests for EVM API"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]

  - id: FE-009
    name: "Refactor ForecastComparisonCard to use EVMSummaryView"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006, FE-008]

  - id: FE-010
    name: "Write frontend component tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-007, FE-009]

  # Level 5: E2E testing (SEQUENTIAL)
  - id: FE-011
    name: "Write frontend E2E tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-010, BE-006]

  # Level 6: WBE/Project support (can run in parallel with testing)
  - id: BE-007
    name: "Implement WBE EVM service methods"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-008
    name: "Implement Project EVM service methods"
    agent: pdca-backend-do-executor
    dependencies: [BE-007]

  - id: BE-009
    name: "Extend API routes for WBE and Project entities"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-008]

  - id: BE-010
    name: "Write WBE and Project EVM tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]

  # Level 7: Frontend WBE/Project support
  - id: FE-012
    name: "Update frontend hooks to support WBE and Project entities"
    agent: pdca-frontend-do-executor
    dependencies: [FE-008, BE-009]

  - id: FE-013
    name: "Update frontend components to support entity switching"
    agent: pdca-frontend-do-executor
    dependencies: [FE-012]

  - id: FE-014
    name: "Write WBE and Project frontend tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-013]

  # Level 8: Finalization (must be sequential)
  - id: BE-FE-001
    name: "Performance optimization and profiling"
    agent: pdca-backend-do-executor
    dependencies: [BE-010, FE-014, FE-011]

  - id: BE-FE-002
    name: "Documentation updates"
    agent: pdca-backend-do-executor
    dependencies: [BE-FE-001]

  - id: BE-FE-003
    name: "Final integration testing and bug fixes"
    agent: pdca-backend-do-executor
    dependencies: [BE-FE-002]
```

### Test-to-Requirement Traceability

| Acceptance Criterion                                                         | Test ID  | Test File                                                         | Expected Behavior                                                                                                                                                                                                                              |
| ---------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ForecastComparisonCard displays metrics organized by topic**              | T-FE-001 | `frontend/src/features/evm/components/__tests__/EVMSummaryView.test.tsx` | Component renders 5 category sections (Schedule, Cost, Variance, Performance, Forecast); Metrics grouped correctly; Category titles display                                                                  |
| **"Advanced" button opens EVM Analyzer modal**                               | T-FE-002 | `frontend/tests/e2e/evm-analyzer.spec.ts`                         | Clicking button opens modal; Modal displays with correct title; Close button works; Backdrop click closes modal                                                                                             |
| **Modal displays all metrics with enhanced visualizations**                  | T-FE-003 | `frontend/tests/e2e/evm-analyzer.spec.ts`                         | All 11 metrics display; Gauges show for CPI/SPI; Descriptions visible; Values formatted correctly (€ currency, decimals)                                                                                   |
| **Modal displays semi-circle gauges for CPI/SPI**                            | T-FE-004 | `frontend/src/features/evm/components/__tests__/EVMGauge.test.tsx`     | Gauge renders semi-circle SVG; CPI shows 0-2 range; SPI shows 0-2 range; Color zones: red (<0.9), yellow (0.9-1.1), green (>1.1); Labels show values                                                        |
| **Modal displays two timeline charts**                                       | T-FE-005 | `frontend/tests/e2e/evm-analyzer.spec.ts`                         | Chart 1 shows PV/EV/AC lines; Chart 2 shows Forecast/Actual lines; Both charts have legends; Tooltips show values; Charts responsive                                                                       |
| **Timeline charts support day/week/month granularity**                      | T-FE-006 | `frontend/tests/e2e/evm-analyzer.spec.ts`                         | Granularity selector renders; Selecting day updates charts; Selecting week updates charts; Selecting month updates charts; State persists across modal open/close                                           |
| **All queries respect TimeMachineContext**                                   | T-BE-001 | `backend/tests/api/test_evm_routes.py`                            | Request with as_of param returns metrics at control_date; Request with branch param uses correct branch; Request with mode param respects ISOLATED/MERGE                                                   |
| **Components are generic (accept EntityType parameter)**                    | T-FE-007 | `frontend/src/features/evm/components/__tests__/EVMSummaryView.test.tsx` | Component accepts entityType prop; Cost element type works; WBE type works; Project type works; TypeScript types validate                                                                                    |
| **Backend endpoints support batch queries**                                  | T-BE-002 | `backend/tests/api/test_evm_routes.py`                            | POST /evm/cost_element/metrics/batch accepts entity_ids array; Returns aggregated metrics; Weighted average correct for indices; Sum correct for amounts; Handles empty list                              |
| **WBE EVM metrics calculate correctly from child cost elements**             | T-BE-003 | `backend/tests/unit/services/test_evm_service_wbe_project.py`    | WBE BAC = sum(child BACs); WBE AC = sum(child ACs); WBE EV = sum(child EVs); WBE CPI = weighted avg by BAC; WBE SPI = weighted avg by BAC; Time-travel works for WBE                                       |
| **Project EVM metrics calculate correctly from child WBEs**                  | T-BE-004 | `backend/tests/unit/services/test_evm_service_wbe_project.py`    | Project BAC = sum(child WBE BACs); Project AC = sum(child WBE ACs); Project EV = sum(child WBE EVs); Project CPI = weighted avg by BAC; Project SPI = weighted avg by BAC; Time-travel works for project |
| **Multi-entity aggregation produces correct sums/averages**                  | T-BE-005 | `backend/tests/unit/services/test_evm_service.py`                | Single entity returns identical metrics; Multiple entities sum amounts; Multiple entities weight indices by BAC; Edge case: empty list returns zero metrics; Edge case: one entity returns its metrics       |
| **UI seamlessly switches between entity types**                              | T-FE-008 | `frontend/tests/e2e/evm-analyzer.spec.ts`                         | EntityType selector renders; Switching to WBE shows WBE metrics; Switching to Project shows project metrics; Switching to Cost Element shows cost element metrics; URL updates with entity type           |
| **Performance: Summary view renders in <500ms**                              | T-PERF-01 | Performance benchmark                                             | Render time measured from mount to complete; 10 runs average <500ms; 95th percentile <600ms; Tested with typical dataset (8 metrics)                                                                          |
| **Performance: Modal with charts renders in <2s**                            | T-PERF-02 | Performance benchmark                                             | Render time measured from mount to complete; 10 runs average <2s; 95th percentile <2.5s; Tested with 1-year weekly time-series data                                                                               |
| **Performance: Time-series queries <1s for 1-year range**                    | T-PERF-03 | Backend performance log                                           | Query time logged for 1-year weekly granularity; 10 runs average <1s; 95th percentile <1.2s; Database query plan shows index usage                                                                              |
| **MyPy strict mode (zero errors)**                                          | T-QA-01  | CI pipeline                                                       | `uv run mypy app/` exits with code 0; No errors in EVM service; No errors in EVM schemas; No errors in EVM routes                                                                                             |
| **Ruff linting (zero errors)**                                              | T-QA-02  | CI pipeline                                                       | `uv run ruff check .` exits with code 0; No linting errors in EVM files                                                                                                                                          |
| **TypeScript strict mode (zero errors)**                                    | T-QA-03  | CI pipeline                                                       | `npm run lint` exits with code 0; No TS errors in EVM components; No TS errors in EVM hooks; No TS errors in EVM types                                                                                           |
| **Test Coverage: 80%+ for all new code**                                    | T-QA-04  | Coverage report                                                   | `uv run pytest --cov=app/services/evm_service` shows 80%+; `npm run test:coverage` shows 80%+ for EVM components; Gaps documented and justified                                                              |

---

## Test Specification

### Test Hierarchy

```
├── Backend Unit Tests (backend/tests/unit/services/)
│   ├── test_evm_service.py
│   │   ├── Happy path: Single cost element metrics
│   │   ├── Happy path: Multi-entity aggregation
│   │   ├── Edge case: No progress reported (EV = 0)
│   │   ├── Edge case: Division by zero (AC = 0, PV = 0)
│   │   ├── Edge case: Empty entity list
│   │   ├── Edge case: Entity not found
│   │   ├── Time-travel: Control date in past
│   │   ├── Time-travel: Control date in future
│   │   ├── Branch mode: ISOLATED vs MERGE
│   │   └── Aggregation: Weighted average by BAC
│   ├── test_evm_service_wbe_project.py
│   │   ├── Happy path: WBE aggregation from children
│   │   ├── Happy path: Project aggregation from WBEs
│   │   ├── Edge case: WBE with no children
│   │   ├── Edge case: Project with no WBEs
│   │   └── Nested aggregation correctness
│   └── test_evm_schemas.py
│       ├── Schema validation: EVMMetricsResponse
│       ├── Schema validation: EVMTimeSeriesResponse
│       ├── Serialization: Decimal to float
│       └── Polymorphism: EntityType validation
│
├── Backend Integration Tests (backend/tests/api/)
│   └── test_evm_routes.py
│       ├── GET /evm/cost_element/{id}/metrics
│       ├── POST /evm/cost_element/metrics/batch
│       ├── GET /evm/wbe/{id}/metrics
│       ├── GET /evm/project/{id}/metrics
│       ├── GET /evm/{entity_type}/{id}/timeseries
│       ├── Query params: as_of, branch, mode, granularity
│       ├── Error responses: 404, 400, 500
│       └── Time-travel integration
│
├── Frontend Unit Tests (frontend/src/features/evm/components/__tests__/)
│   ├── MetricCard.test.tsx
│   │   ├── Renders metric value
│   │   ├── Renders description when showDescription=true
│   │   ├── Applies correct color based on favorable/unfavorable
│   │   ├── Size variants (small, medium, large)
│   │   └── Accessibility: ARIA labels
│   ├── EVMGauge.test.tsx
│   │   ├── Renders semi-circle SVG
│   │   ├── Displays correct value
│   │   ├── Color zones (red, yellow, green)
│   │   ├── CPI range (0-2+)
│   │   ├── SPI range (0-2+)
│   │   └── Labels and tick marks
│   ├── MetricCategorySection.test.tsx
│   │   ├── Groups metrics by category
│   │   ├── Renders section title
│   │   ├── Grid layout
│   │   └── List layout
│   ├── EVMTimeSeriesChart.test.tsx
│   │   ├── Renders progression chart
│   │   ├── Renders accuracy chart
│   │   ├── Granularity selector
│   │   ├── Ant Design zoom
│   │   ├── Loading state
│   │   └── Empty state
│   ├── EVMSummaryView.test.tsx
│   │   ├── Organizes metrics by topic
│   │   ├── Renders "Advanced" button
│   │   ├── Loading state
│   │   └── Error state
│   └── EVMAnalyzerModal.test.tsx
│       ├── Modal opens/closes
│       ├── Displays all metrics
│       ├── Displays gauges for CPI/SPI
│       ├── Displays both charts
│       ├── Granularity selector works
│       └── Responsive layout
│
└── Frontend E2E Tests (frontend/tests/e2e/)
    └── evm-analyzer.spec.ts
        ├── Critical flow: Open modal from summary
        ├── Critical flow: View metrics with gauges
        ├── Critical flow: Change granularity
        ├── Critical flow: Switch entity types
        ├── Time-travel: Change control date
        ├── Time-travel: Change branch
        ├── Performance: Summary render time
        ├── Performance: Modal render time
        └── Accessibility: Keyboard navigation
```

### Test Cases (First 10)

| Test ID | Test Name                                                                 | Criterion | Type          | Verification                                                                                                                                                                                                                                                                |
| ------- | ------------------------------------------------------------------------- | --------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-BE-001| test_evm_service_single_cost_element_returns_correct_metrics              | AC-1      | Backend Unit  | Call calculate_evm_metrics() with valid cost_element_id; Assert all 11 metrics calculated; Assert BAC matches cost_element.budget_amount; Assert CPI = EV / AC; Assert SPI = EV / PV; Assert no warning thrown                                                          |
| T-BE-002| test_evm_service_multi_entity_aggregates_amounts_by_sum                    | AC-2      | Backend Unit  | Call calculate_evm_metrics_batch() with 3 cost_elements; Assert returned BAC = sum(child BACs); Assert returned AC = sum(child ACs); Assert returned EV = sum(child EVs); Assert aggregation_type = "sum" for amount fields                                          |
| T-BE-003| test_evm_service_multi_entity_aggregates_indices_by_weighted_avg          | AC-2      | Backend Unit  | Call calculate_evm_metrics_batch() with 3 cost_elements; Calculate expected CPI = sum(EV) / sum(AC); Assert returned CPI matches expected (within 0.001); Assert returned SPI = sum(EV) / sum(PV); Assert aggregation_type = "weighted" for index fields                    |
| T-BE-004| test_evm_service_no_progress_returns_ev_zero_with_warning                 | AC-1      | Backend Unit  | Create cost_element with no progress entries; Call calculate_evm_metrics(); Assert EV = 0; Assert warning = "No progress reported for this cost element"; Assert CPI and SPI are None                                                                      |
| T-BE-005| test_evm_service_division_by_zero_returns_none_for_indices                | AC-1      | Backend Unit  | Mock AC = 0, PV = 0; Call calculate_evm_metrics(); Assert CPI is None; Assert SPI is None; Assert no exception thrown                                                                                                                                                  |
| T-BE-006| test_evm_service_time_travel_respects_control_date                         | AC-3      | Backend Unit  | Set control_date to 2024-01-01; Create cost_element modified on 2024-02-01; Call calculate_evm_metrics(); Assert BAC reflects value as of 2024-01-01 (not modified value); Set control_date to 2024-02-01; Assert BAC reflects modified value                               |
| T-BE-007| test_evm_timeseries_weekly_groups_by_week                                 | AC-4      | Backend Unit  | Create cost_registrations across 3 months; Call get_evm_timeseries() with granularity="week"; Assert data_points length = ~13 weeks; Assert each point's date is Monday; Assert AC sum correct per week                                          |
| T-BE-008| test_evm_api_get_metrics_returns_200_with_valid_id                         | AC-5      | API Integration | GET /api/v1/evm/cost_element/{id}/metrics; Assert status = 200; Assert response body has all 11 metrics; Assert response body matches EVMMetricsResponse schema                                                                                                       |
| T-BE-009| test_evm_api_get_metrics_returns_404_with_invalid_id                       | AC-5      | API Integration | GET /api/v1/evm/cost_element/{invalid_id}/metrics; Assert status = 404; Assert response body has error message                                                                                                                                                         |
| T-BE-010| test_evm_api_batch_metrics_aggregates_correctly                            | AC-5      | API Integration | POST /api/v1/evm/cost_element/metrics/batch with body = {entity_ids: [id1, id2, id3]}; Assert status = 200; Assert response BAC = sum(individual BACs); Assert response CPI = weighted average                                                               |

### Test Infrastructure Needs

**Backend Fixtures (backend/tests/conftest.py):**

- `db_session`: Async database session with rollback
- `test_cost_element`: Factory for creating test cost elements
- `test_wbe`: Factory for creating test WBEs
- `test_project`: Factory for creating test projects
- `test_schedule_baseline`: Factory for creating test baselines
- `test_progress_entry`: Factory for creating progress entries
- `test_cost_registration`: Factory for creating cost registrations
- `test_forecast`: Factory for creating forecasts
- `authenticated_client`: FastAPI test client with JWT token

**Frontend Fixtures (frontend/src/test/utils/testUtils.tsx):**

- `renderWithProviders`: Wrapper with TanStack Query, TimeMachineContext
- `mockEVMMetrics`: Mock EVM metrics data
- `mockTimeSeries`: Mock time-series data
- `mockUseEVMMetrics`: Mock hook for EVM metrics
- `mockUseEVMTimeSeries`: Mock hook for time-series

**Mocks/Stubs:**

- External services: None (all internal)
- Time-dependent logic: Use fixed dates in tests (2024-01-01, 2024-06-01)
- Database: Use test database with transaction rollback

**Database State:**

- Seed data: Minimal test dataset (3 cost_elements, 2 WBEs, 1 project)
- Cleanup: Transaction rollback after each test
- Isolation: Each test runs in isolation (sequential execution)

---

## Risk Assessment

| Risk Type   | Description                                                                 | Probability | Impact       | Mitigation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------- | --------------------------------------------------------------------------- | ----------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | Time-series query performance degrades with large datasets                  | Medium      | High         | - Add database indexes on cost_registrations.date and progress_entries.reported_at<br>- Implement query result caching with TanStack Query<br>- Add pagination for long time ranges<br>- Create materialized view if metrics show >2s queries<br>- Use EXPLAIN ANALYZE to optimize query plans                                                                                                                                                                                                                                                                    |
| Technical   | Gauge component complexity exceeds estimates                                 | Low         | Medium       | - Reference ProgressionPreviewChart SVG pattern closely<br>- Keep gauge design simple (semi-circle, 3 color zones)<br>- Reuse Ant Design theming tokens<br>- Unit test SVG path calculations<br>- Consider using existing gauge library if implementation exceeds 1 day                                                                                                                                                                                                                                                                            |
| Technical   | Multi-entity aggregation bugs in weighted average calculations              | Medium      | High         | - Comprehensive unit tests with known datasets<br>- Validate calculations against manual Excel spreadsheets<br>- Add integration tests with 1, 10, 100 entities<br>- Use Decimal type for precision (avoid float errors)<br>- Add logging for aggregation steps<br>- Peer review of aggregation logic                                                                                                                                                                                                                                                              |
| Integration | Frontend-backend schema mismatch (TypeScript vs Python)                     | Low         | Medium       | - Generate OpenAPI spec from backend<br>- Run `npm run generate-client` to auto-generate TypeScript types<br>- Validate types in CI pipeline<br>- Use Zod for runtime validation<br>- Keep schema changes synchronized between backend/frontend                                                                                                                                                                                                                                                                                                             |
| Integration | Time-travel semantics inconsistent across services                          | Medium      | High         | - Document time-travel semantics in ADR<br>- Add integration tests for control_date variations<br>- Review all service.get_as_of() calls<br>- Ensure Valid Time Travel semantics (not Transaction Time)<br>- Test edge cases: future dates, past dates, entity creation dates                                                                                                                                                                                                                                                                             |
| Testing     | Flaky E2E tests due to timing issues                                        | Medium      | Medium       | - Use explicit waits (not fixed timeouts)<br>- Mock API responses in component tests<br>- Keep E2E tests focused on critical flows only<br>- Run E2E tests sequentially (not parallel)<br>- Add retry logic for network-dependent tests<br>- Use test database with consistent seed data                                                                                                                                                                                                                                                                   |
| Testing     | Sequential test execution significantly increases CI time                    | High        | Medium       | - Accept sequential execution as constraint (document in plan)<br>- Optimize test cleanup (use transaction rollback)<br>- Partition tests by feature (run backend/frontend in parallel)<br>- Use test caching (pytest --cache-show)<br>- Run unit tests in parallel (safe), only integration/e2e sequential<br>- Set expectations with stakeholders (CI may take 15-20 min)                                                                                                                                                                           |
| Performance  | Modal render time exceeds 2s with 1-year time-series data                   | Low         | Medium       | - Implement virtualization for long time-series<br>- Use data point reduction (max 100 points per chart)<br>- Lazy load chart data after modal opens<br>- Add skeleton loading states<br>- Profile with React DevTools and Chrome Performance<br>- Optimize chart rendering (use memo, useMemo)                                                                                                                                                                                                                                                           |
| Scope       | Feature creep during implementation (adding Phase 3 features)               | Medium      | Medium       | - Strict phase boundaries in plan<br>- Document Phase 3 as backlog items (not in scope)<br>- Product Owner reviews any new requirements<br>- Create ADR for any scope changes<br>- Use "parking lot" for future ideas<br>- Weekly scope review meetings                                                                                                                                                                                                                                                                                              |
| User        | Gauge visualization not intuitive for users                                 | Low         | Low          | - Use traditional semi-circle (industry standard)<br>- Add color zones (red/yellow/green)<br>- Include labels and tick marks<br>- Add tooltip explaining values<br>- User acceptance testing before release<br>- Document gauge interpretation in user guide                                                                                                                                                                                                                                                                                                 |
| Data        | Missing historical data for time-series charts                              | Medium      | Low          | - Show empty state with message "No historical data available"<br>- Display explanation of why data is missing<br>- Provide guidance on how to populate data (create progress entries, cost registrations)<br>- Gracefully handle null values in charts<br>- Don't show charts if no data (avoid confusion)                                                                                                                                                                                                                                            |
| Architecture| Generic EVMMetric system becomes overly complex                             | Low         | High         | - Keep schemas flat (not nested list of metrics)<br>- Use TypeScript discriminated unions for type safety<br>- Document EVMMetric system in ADR<br>- Peer review of schema design<br>- Avoid over-abstraction (YAGNI principle)<br>- Keep WBE/Project aggregation simple (sum, weighted avg)                                                                                                                                                                                                                                                              |

---

## Documentation References

### Required Reading

**Coding Standards:**
- Backend: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md` - Protocol-based type system, service layer patterns, command pattern
- Frontend: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md` - Feature-based structure, TanStack Query, TypeScript strict mode

**Domain Knowledge:**
- EVM Requirements: `/home/nicola/dev/backcast_evs/docs/01-product-scope/evm-requirements.md` - ANSI/EIA-748 standard, metric definitions, aggregation rules
- Bounded Contexts: `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md` - Cost Element & Financial Tracking, EVM Calculations & Reporting

**Time-Travel Architecture:**
- Versioning System: `/home/nicola/dev/backcast_evs/backend/app/core/versioning/` - Bitemporal tracking, Valid Time Travel semantics
- TimeMachineContext: `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx` - Frontend time-travel integration

### Code References

**Backend Patterns:**
- EVM Service: `/home/nicola/dev/backcast_evs/backend/app/services/evm_service.py` - Existing EVM calculation logic (extend with multi-entity)
- EVM Schemas: `/home/nicola/dev/backcast_evs/backend/app/models/schemas/evm.py` - Existing Pydantic models (extend with generic types)
- Service Layer Pattern: `/home/nicola/dev/backcast_evs/backend/app/services/cost_element_service.py` - Example service to follow
- API Routes: `/home/nicola/dev/backcast_evs/backend/app/api/routes/cost_elements.py` - Example API structure (lines 529-546 for EVM endpoint)

**Frontend Patterns:**
- Chart Component: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/SCurveComparison.tsx` - @ant-design/charts Line usage
- SVG Chart: `/home/nicola/dev/backcast_evs/frontend/src/features/schedule-baselines/components/ProgressionPreviewChart.tsx` - Custom SVG chart pattern
- Current EVM Display: `/home/nicola/dev/backcast_evs/frontend/src/features/forecasts/components/ForecastComparisonCard.tsx` - Refactor target
- Data Fetching: `/home/nicola/dev/backcast_evs/frontend/src/features/cost-elements/api/useCostElements.ts` - useCostElementEvmMetrics hook pattern
- TimeMachineContext: `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx` - Time-travel integration

**Test Patterns:**
- Backend Tests: `/home/nicola/dev/backcast_evs/backend/tests/conftest.py` - Shared fixtures, db_session setup
- Frontend Tests: `/home/nicola/dev/backcast_evs/frontend/src/test/utils/testUtils.tsx` - Render utilities, mock patterns
- E2E Tests: `/home/nicola/dev/backcast_evs/frontend/tests/e2e/` - Playwright patterns

### Architecture Decision Records (ADRs)

**New ADR Required:**
- Generic EVM Metric System - Document flat schema design, polymorphic entity support, aggregation strategy
- Time-Series Data Strategy - Document on-the-fly calculation vs materialized views, caching strategy

**Existing ADRs to Reference:**
- Bitemporal Versioning - Valid Time Travel semantics for EVM queries
- Branch Isolation - ISOLATED vs MERGE modes for EVM calculations
- Service Layer Pattern - Orchestration and transaction management

---

## Prerequisites

### Technical Prerequisites

- [x] Database migrations applied (PostgreSQL 15+ running)
- [x] Dependencies installed (backend: `uv sync`, frontend: `npm install`)
- [x] Environment configured (`.env` files set up)
- [x] Docker Compose PostgreSQL running
- [x] Backend dev server accessible (`uv run uvicorn app.main:app --reload`)
- [x] Frontend dev server accessible (`npm run dev`)
- [ ] Database indexes added for time-series queries (to be done in Task 25)
- [ ] OpenAPI spec regenerated after schema changes (to be done in Task 4)

### Documentation Prerequisites

- [x] Analysis phase approved (`00-analysis.md` complete)
- [x] Architecture docs reviewed (bounded contexts, coding standards)
- [x] EVM requirements document understood (metric definitions, formulas)
- [x] Time-travel semantics reviewed (Valid Time Travel, branch modes)
- [ ] ADR created for Generic EVM Metric System (to be done in Task 26)
- [ ] API documentation updated (to be done in Task 26)

### Development Environment

- [ ] Python 3.12+ installed with uv package manager
- [ ] Node.js 18+ installed with npm
- [ ] PostgreSQL 15+ accessible via Docker Compose
- [ ] Git workspace clean (no uncommitted changes in critical files)
- [ ] IDE configured (VS Code with Python, TypeScript extensions)
- [ ] Test runner configured (pytest for backend, vitest/playwright for frontend)

### Skills Required

**Backend Developer:**
- FastAPI and Pydantic schemas
- SQLAlchemy async sessions and queries
- Bitemporal versioning system (Valid Time Travel)
- Service layer pattern and dependency injection
- pytest with async fixtures and transaction rollback
- MyPy strict mode type checking
- Time-series data aggregation (SQL GROUP BY, date truncation)

**Frontend Developer:**
- React 18 with TypeScript strict mode
- TanStack Query (React Query) for data fetching
- Ant Design components and @ant-design/charts
- SVG chart rendering (custom gauges)
- TimeMachineContext integration
- Vitest for unit testing, Playwright for E2E
- Performance profiling (React DevTools, Chrome Performance)

---

## Output

**File**: `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/01-plan.md`

**Template**: [`docs/04-pdca-prompts/_templates/01-plan-template.md`](/home/nicola/dev/backcast_evs/docs/04-pdca-prompts/_templates/01-plan-template.md)

---

## Key Principles Applied

1. **Define WHAT, not HOW**: Test specifications define expected behaviors, not implementation code
2. **Measurable**: All success criteria objectively verifiable (quantitative metrics, visual inspection, test results)
3. **Sequential with Parallel Opportunities**: Task dependency graph identifies parallelizable work (Level-0, Level-1, Level-2)
4. **Traceable**: Every requirement maps to test specifications with unique IDs (T-BE-*, T-FE-*, T-PERF-*, T-QA-*)
5. **Testing Constraints**: Sequential test execution documented and accommodated in estimates
6. **Risk Management**: 13 risks identified with probability, impact, and mitigation strategies
7. **Scope Boundaries**: Phase 1 and 2 in scope, Phase 3 explicitly deferred to backlog

---

## Parallel Execution Strategy

### Backend Parallelization (Level 0-2):
- **BE-001** (schemas) can start immediately
- **BE-002, BE-003** (service methods) run sequentially after BE-001
- **BE-004** (API routes) depends on BE-003

### Frontend Parallelization (Level 1-3):
- **FE-001** (types) can start immediately after BE-001
- **FE-002, FE-003, FE-004, FE-005, FE-006** (components) can run in parallel after FE-001
- **FE-007** (modal) depends on FE-002, FE-003, FE-005, FE-006
- **FE-008** (hooks) can run in parallel with FE-002-FE-007 after BE-004

### Testing Parallelization (Level 4-5):
- **BE-005, BE-006** (backend tests) run sequentially (database constraint)
- **FE-009, FE-010** (frontend tests) run sequentially (database constraint)
- **FE-011** (E2E tests) runs sequentially after all implementation complete

### WBE/Project Support (Level 6-7):
- **BE-007, BE-008** can run in parallel after BE-002
- **FE-012, FE-013** can run in parallel after FE-008, BE-009

### Expected Time Savings:
- Without parallelization: ~60-80 hours
- With parallelization: ~40-55 hours
- **Savings: ~20-25 hours (33-30% reduction)**

---

> **Note to DO Phase Executors**: This plan focuses on WHAT to build and HOW to verify success. The DO phase will implement the actual code following RED-GREEN-REFACTOR TDD cycle. Tests specified here (e.g., "test_evm_service_single_cost_element_returns_correct_metrics") will be implemented by DO phase, not by PLAN phase.
>
> **Critical Constraint**: All tests MUST run sequentially due to single database and data destruction. No parallel test execution in CI pipeline.
