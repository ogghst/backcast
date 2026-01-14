# Phase 3: Impact Analysis & Comparison - PLAN

**Date Created:** 2026-01-14
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 3 of 4 - Impact Analysis & Comparison
**Status:** Planning Phase
**Related Docs:**
- [Change Management User Stories](../../../../01-product-scope/change-management-user-stories.md)
- [EVM Requirements](../../../../01-product-scope/evm-requirements.md)
- [Phase 3 ANALYSIS](./00-analysis.md)
- [Phase 1 ACT](../phase1/04-act.md)
- [Phase 2 ACT](../phase2/04-act.md)
- [Coding Standards](../../../../02-architecture/coding-standards.md)
- [UI/UX Architecture](../../../../02-architecture/frontend/contexts/03-ui-ux.md) (echarts for data visualization)

---

## Phase 1: Context Analysis

### Documentation Review

**Documentation Guide** ([`docs/00-meta/README.md`](../../../../00-meta/README.md))
- Phase 3 follows iterative documentation pattern: ANALYSIS → PLAN → DO → CHECK → ACT
- All decisions must be documented with rationale and traceability

**Product Scope** ([`docs/01-product-scope/`](../../../../01-product-scope/))
- **Target User Story:** 3.4 Reviewing Change Impacts (Impact Analysis)
  - KPI Comparison: BAC, Budget Delta, Gross Margin (EVM metrics deferred to Sprint 8)
  - Delta Waterfall Chart: Cost bridge visualization
  - Time-Phased S-Curves: Budget comparison (weekly granularity)
  - Entity Impact Grid: Modified/added/removed entities (financial fields only)

**Architecture** ([`docs/02-architecture/`](../../../../02-architecture/))
- **Bounded Contexts:** E006 (Branching & Change Order Management) - Primary
- **Coding Standards:** Type safety (Pydantic/TypeScript), 80%+ test coverage, zero linting errors
- **Existing Patterns:**
  - `BranchableService[T]`: Branch-aware queries already implemented
  - `TemporalService[T]`: Time-travel queries already implemented
  - `BranchMode.MERGE`: Combines main + branch data
  - React Query: Server state management already in use

**Project Plan** ([`docs/03-project-plan/`](../../../../03-project-plan/))
- **Sprint 7 Active:** Current iteration focusing on change orders
- **Team Velocity:** ~21 points/sprint
- **Phase 3 Estimate:** 8 points (1 sprint)
- **Dependencies:** Phase 1 (CRUD) ✅, Phase 2 (Branch Management) ✅, Workflow UI ✅

### Codebase Analysis

**Backend Infrastructure:**
- Change Order API: [`app/api/routes/change_orders.py`](../../../../backend/app/api/routes/change_orders.py)
- Change Order Service: [`app/services/change_order_service.py`](../../../../backend/app/services/change_order_service.py)
- Branch Service: [`app/services/branch_service.py`](../../../../backend/app/services/branch_service.py)
- WBE Service: [`app/services/wbe_service.py`](../../../../backend/app/services/wbe_service.py) (branch-aware)
- Cost Element Service: [`app/services/cost_element_service.py`](../../../../backend/app/services/cost_element_service.py) (branch-aware)

**Frontend Infrastructure:**
- React Query available and configured
- **echarts** (via `@ant-design/charts`) installed for data visualization (per [UI/UX Architecture](../../../../02-architecture/frontend/contexts/03-ui-ux.md))
- Existing components: `BranchSelector`, `ViewModeSelector`, `StandardTable`
- Time Machine Context: `useTimeMachineParams()` for branch/mode/as_of

**Key Models:**
- `ChangeOrder`: [`app/models/domain/change_order.py`](../../../../backend/app/models/domain/change_order.py)
- `Project`: [`app/models/domain/project.py`](../../../../backend/app/models/domain/project.py)
- `WBE`: [`app/models/domain/wbe.py`](../../../../backend/app/models/domain/wbe.py)
- `CostElement`: [`app/models/domain/cost_element.py`](../../../../backend/app/models/domain/cost_element.py)

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What specific problem are we solving?**

Project Controllers need to visually understand the financial and schedule impact of a proposed Change Order before approving it. Currently, stakeholders must manually compare data between branches, which is error-prone and time-consuming.

**Why is it important now?**

Phase 1 (Change Order CRUD) and Phase 2 (Branch Management) are complete. Users can create Change Orders and edit entities in isolation, but lack tools to assess impact before merging to main branch.

**What happens if we don't address it?**

- Risk of uninformed approval decisions
- Potential for costly errors to propagate to main branch
- Manual comparison process remains inefficient
- Change Order workflow cannot complete approval step effectively

**What is the business value?**

- **Decision Support:** Data-driven approval decisions
- **Risk Mitigation:** Identify negative impacts before merge
- **Efficiency:** Automated comparison vs manual spreadsheet work
- **Audit Trail:** Documented impact analysis for compliance

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] KPI Scorecard displays BAC, Budget Delta, and Gross Margin comparison between branches
- [ ] Waterfall Chart visualizes cost bridge from current margin → changes → new margin
- [ ] S-Curve Comparison overlays weekly budget data for main vs change branch
- [ ] Entity Impact Grid lists added/modified/removed WBEs and Cost Elements
- [ ] Only financial fields compared (budget_allocation, revenue_allocation, cost)
- [ ] Impact analysis accessible via `/change-orders/:id/impact` route
- [ ] API endpoint `/api/v1/change-orders/{id}/impact` returns complete comparison data

**Technical Criteria:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Backend Test Coverage | 80%+ | `pytest --cov=app/services/impact_analysis_service` |
| Frontend Test Coverage | 80%+ | `npm run test:coverage` |
| Backend Linting | Zero errors | `uv run ruff check .` |
| Backend Type Checking | Zero errors | `uv run mypy app/` |
| Frontend Linting | Zero errors | `npm run lint` |
| API Response Time | <500ms p95 | Measured via logs |

**Business Criteria:**

- Project Controllers can complete impact review in <2 minutes per Change Order
- Zero production bugs related to impact calculations
- User acceptance: Stakeholders confident in approval decisions based on dashboard

### 3. Scope Definition

**In Scope:**

| Feature | Description | Priority |
|---------|-------------|----------|
| KPI Scorecard | BAC, Budget Delta, Gross Margin comparison | Critical |
| Waterfall Chart | Cost bridge visualization | Critical |
| S-Curve Comparison | Weekly budget overlay | High |
| Entity Impact Grid | Financial field changes only | High |
| Backend API | `/api/v1/change-orders/{id}/impact` endpoint | Critical |
| Frontend Dashboard | Single-page tabbed interface | Critical |
| Caching | React Query with 5-minute stale time | High |

**Out of Scope:**

| Feature | Reason | Future Iteration |
|---------|--------|------------------|
| EVM Metrics (EAC, CPI, SPI) | Requires EVM calculation service | Sprint 8 |
| PV/EV/AC Calculations | Requires performance data integration | Sprint 8 |
| Redis Caching | React Query sufficient for current scale | Sprint 8+ if needed |
| Export to PDF/Excel | Not requested for MVP | Future sprint |
| Historical Impact Comparison | Current state vs baseline only | Future sprint |
| Drill-down to entity details | Entity Grid provides links | Already exists |

**Assumptions Requiring Validation:**

- Phase 1 and Phase 2 remain stable (no breaking changes)
- **echarts** (via `@ant-design/charts`) can handle weekly time-series data (~52 points/year) and waterfall visualization
- Single API call with complete data is performant enough (<500ms)
- Weekly granularity for S-curves is acceptable (vs daily/monthly)

---

## Phase 3: Implementation Options

| Aspect | Option A: API-First Impact Analysis | Option B: Client-Side Diff Calculation | Option C: Hybrid Approach |
|--------|-------------------------------------|----------------------------------------|---------------------------|
| **Approach Summary** | Dedicated `/impact` endpoint returns complete comparison data. Frontend consumes and visualizes. | Frontend fetches data from existing entity APIs and computes diffs client-side using multiple parallel calls. | Incremental backend endpoint starting with KPIs only, adding features over multiple sprints. |
| **Design Patterns** | - Service layer for diff logic<br>- Single API call<br>- Backend-driven calculations | - React Query composition<br>- Client-side diff utilities<br>- Multiple parallel API calls | - Iterative API design<br>- Feature flags<br>- Incremental data payload |
| **Pros** | - Single API call (efficient)<br>- Centralized diff logic<br>- Easier to test and optimize<br>- Consistent with existing patterns<br>- Better caching strategy | - No backend changes needed<br>- Frontend has full control<br>- Can incrementally load data<br>- Lower backend risk | - Early value delivery<br>- Lower risk per sprint<br>- Easier to adjust based on feedback |
| **Cons** | - Backend needs more work<br>- Larger API response<br>- Need to serialize complex nested data | - 4+ API round trips (slow)<br>- Diff logic duplicated on client<br>- Performance impact for large projects<br>- Harder to cache | - Unstable API during development<br>- More backend iterations<br>- Longer total timeline<br>- Integration complexity |
| **Test Strategy Impact** | - Unit tests for service methods<br>- Integration tests for API endpoint<br>- Frontend tests for visualization only | - Frontend tests must cover diff logic<br>- Integration tests more complex<br>- Mocking multiple API endpoints | - Tests must handle incremental API changes<br>- Regression testing across phases<br>- Feature flag testing |
| **Risk Level** | Low - Proven pattern from Phase 1/2 | High - Performance and complexity concerns | Medium - API stability risks |
| **Estimated Complexity** | Medium | High | Medium |
| **Estimated Effort** | 8 points (1 sprint) | 10 points (1-2 sprints) | 8 points (2 sprints) |

### Recommendation

**Recommended Option: Option A - API-First Impact Analysis**

**Justification:**

1. **Proven Pattern:** All existing features (Phase 1, Phase 2, Workflow UI) use backend-first approach successfully
2. **Performance:** Single API call (~200-500ms) vs 4+ parallel calls with client-side computation
3. **Consistency:** Aligns with existing API architecture, RBAC patterns, and service layer design
4. **Scalability:** Backend can optimize queries, add database indexes, and implement caching layers
5. **Maintainability:** Diff logic centralized in one place (service layer), not duplicated across frontend
6. **Type Safety:** Pydantic → TypeScript generation ensures end-to-end type safety
7. **Testability:** Easier to unit test business logic in isolation from UI

> [!IMPORTANT] > **Human Decision Point**: Option A (API-First) was confirmed in the ANALYSIS phase. Proceeding with implementation based on this approved approach.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests (isolated component behavior)
│   ├── Backend - ImpactAnalysisService
│   │   ├── test_compare_kpis_happy_path
│   │   ├── test_compare_kpis_no_changes
│   │   ├── test_compare_entities_added_wbe
│   │   ├── test_compare_entities_modified_wbe
│   │   ├── test_compare_entities_removed_wbe
│   │   ├── test_compare_entities_cost_elements
│   │   ├── test_build_waterfall_bridge
│   │   ├── test_generate_time_series_weekly
│   │   └── test_edge_cases_empty_branch
│   ├── Backend - API Endpoint
│   │   ├── test_get_impact_success
│   │   ├── test_get_impact_not_found
│   │   ├── test_get_impact_invalid_branch
│   │   └── test_get_impact_unauthorized
│   └── Frontend - Components
│       ├── test_kpi_cards_rendering
│       ├── test_waterfall_chart_data_binding
│       ├── test_scurve_comparison_overlay
│       ├── test_entity_grid_grouping
│       └── test_impact_dashboard_tabs
├── Integration Tests (component interactions)
│   ├── test_impact_analysis_end_to_end
│   ├── test_branch_comparison_with_real_data
│   ├── test_api_response_structure
│   └── test_react_query_caching_behavior
└── End-to-End Tests (critical user flows)
    ├── test_user_views_impact_analysis
    ├── test_user_navigates_between_tabs
    └── test_impact_data_refreshes_on_status_change
```

**First 5 Test Cases (Simplest to Most Complex):**

1. **`test_compare_kpis_no_changes`**
   - Setup: Create project with identical data in both branches
   - Action: Call `_compare_kpis()` method
   - Assert: All delta values are zero, delta_percent is 0

2. **`test_compare_entities_added_wbe`**
   - Setup: Add new WBE in change branch only
   - Action: Call `_compare_entities()` method
   - Assert: WBE appears in `wbes` list with `change_type="added"`

3. **`test_build_waterfall_bridge`**
   - Setup: Create KPI comparison with margin delta
   - Action: Call `_build_waterfall()` method
   - Assert: Returns 3 segments (current margin, delta, new margin)

4. **`test_get_impact_success`**
   - Setup: Create change order with branch data
   - Action: GET `/api/v1/change-orders/{id}/impact`
   - Assert: Returns 200 with complete `ImpactAnalysisResponse`

5. **`test_kpi_cards_rendering`**
   - Setup: Create mock `KPIScorecard` data
   - Action: Render `<KPICards kpiComparison={mock} />`
   - Assert: 5 cards render (BAC, Budget Delta, Gross Margin, CPI, SPI) with correct values

### Implementation Strategy

**High-Level Approach:**

1. **Backend First:** Implement service and API endpoint with comprehensive tests
2. **Schema Definition:** Create Pydantic models for type-safe API contracts
3. **Frontend Second:** Build dashboard components consuming typed API
4. **Incremental Features:** Start with KPI cards, add charts incrementally
5. **Quality Gates:** All tests passing, zero linting errors before moving to next step

**Key Technologies/Patterns:**

| Layer | Technology | Pattern |
|-------|-----------|---------|
| Backend | Python 3.12+ / FastAPI / SQLAlchemy | Service Layer + Repository Pattern |
| Database | PostgreSQL 15+ | Branch-aware queries using existing infrastructure |
| Frontend | React 18 / TypeScript / Vite | Feature-based architecture |
| Charts | **echarts** (via `@ant-design/charts`) | Enterprise-grade data visualization (per [UI/UX Architecture](../../../../02-architecture/frontend/contexts/03-ui-ux.md)) |
| State | TanStack Query (React Query) | Server state with caching |
| Types | Pydantic → OpenAPI → TypeScript | End-to-end type safety |

**Integration Points with Existing System:**

| Integration | Point | Impact |
|-------------|-------|--------|
| Change Orders | `app/api/routes/change_orders.py` | Add new `/impact` route |
| WBE Service | `app/services/wbe_service.py` | Use for branch-aware WBE queries |
| Cost Element Service | `app/services/cost_element_service.py` | Use for branch-aware CE queries |
| Branch Service | `app/services/branch_service.py` | Use for branch validation |
| Time Machine | `useTimeMachineParams()` context | Not needed (API handles branch) |
| Routing | `App.tsx` | Add `/change-orders/:id/impact` route |

**Component Breakdown:**

**Backend:**
```
app/
├── models/schemas/
│   └── impact_analysis.py (NEW)
│       ├── KPIMetric
│       ├── KPIScorecard
│       ├── EntityChange
│       ├── EntityChanges
│       ├── WaterfallSegment
│       ├── TimeSeriesPoint
│       ├── TimeSeriesData
│       └── ImpactAnalysisResponse
├── services/
│   └── impact_analysis_service.py (NEW)
│       └── ImpactAnalysisService
│           ├── analyze_impact()
│           ├── _compare_kpis()
│           ├── _compare_entities()
│           ├── _build_waterfall()
│           └── _generate_time_series()
└── api/routes/
    └── change_orders.py (MODIFY)
        └── GET /{change_order_id}/impact
```

**Frontend:**
```
src/features/change-orders/
├── components/
│   └── impact/ (NEW)
│       ├── ImpactAnalysisDashboard.tsx
│       ├── KPICards.tsx
│       ├── WaterfallChart.tsx
│       ├── SCurveComparison.tsx
│       └── EntityImpactGrid.tsx
├── hooks/
│   └── useImpactAnalysis.ts (NEW)
└── types/
    └── impact.ts (NEW - generated from OpenAPI)
```

---

## Phase 5: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Technical** | API response size exceeds reasonable limits for large projects | Medium | Medium | - Implement pagination for entity changes<br>- Use field projection to limit data<br>- Monitor response times in production |
| **Technical** | Time-series query performance degradation with weekly granularity | Medium | Medium | - Add database indexes on temporal fields<br>- Consider caching time-series data<br>- Monitor query performance with logs |
| **Integration** | Breaking changes in Phase 1/2 APIs affect impact analysis | Low | High | - Use existing stable endpoints only<br>- Version impact analysis API independently<br>- Integration tests catch regressions |
| **Schedule** | echarts waterfall chart complexity (requires custom configuration) | Low | Medium | - Prototype waterfall chart early in sprint, use `@ant-design/charts` helpers for echarts integration, reference existing EVM graph implementations |
| **Integration** | Frontend type generation fails on complex nested schemas | Low | Medium | - Keep schemas flat where possible<br>- Test OpenAPI generation early<br>- Manual type fallback if needed |
| **Business** | Weekly granularity insufficient for detailed analysis | Low | Medium | - Design frontend to support aggregation<br>- Can increase to daily in future without schema change<br>- User feedback in CHECK phase |
| **Quality** | Test coverage below 80% threshold | Medium | Medium | - Write tests alongside implementation (TDD)<br>- Daily coverage checks<br>- Block PR if coverage drops |

---

## Phase 6: Effort Estimation

### Time Breakdown

| Phase | Tasks | Estimate |
|-------|-------|----------|
| **Backend - Schema** | Define Pydantic models for impact analysis | 2 hours |
| **Backend - Service** | Implement `ImpactAnalysisService` with all comparison methods | 6 hours |
| **Backend - API** | Add `/impact` endpoint to change_orders.py | 2 hours |
| **Backend - Tests** | Unit and integration tests for service and API | 4 hours |
| **Frontend - Hooks** | Create `useImpactAnalysis` hook with React Query | 1 hour |
| **Frontend - KPI Cards** | Implement KPICards component | 2 hours |
| **Frontend - Dashboard** | Create main dashboard layout with tabs | 2 hours |
| **Frontend - Waterfall** | Implement WaterfallChart with echarts (via `@ant-design/charts`) | 3 hours |
| **Frontend - S-Curves** | Implement SCurveComparison with time-series using echarts | 3 hours |
| **Frontend - Entity Grid** | Implement EntityImpactGrid with grouping | 2 hours |
| **Frontend - Tests** | Component tests and E2E tests | 3 hours |
| **Integration** | API type generation, route setup, error handling | 2 hours |
| **Documentation** | Update architecture docs, API comments | 1 hour |
| **Buffer** | Unexpected issues, refinements | 3 hours |
| **Total** | | **36 hours (~4.5 days)** |

**Story Point Estimate:** 8 points (based on ~1 sprint effort)

### Prerequisites

**Must Be Done First:**

1. ✅ Phase 1 complete (Change Order CRUD + Auto-branch creation)
2. ✅ Phase 2 complete (Branch management + In-branch editing)
3. ✅ Workflow UI complete (Status transitions + Branch locking)
4. ✅ Database migrations applied
5. ✅ Frontend dependencies installed (echarts via `@ant-design/charts` confirmed available)

**Documentation Updates:**

- [ ] Update bounded contexts document with Impact Analysis capability
- [ ] Add OpenAPI documentation for `/impact` endpoint
- [ ] Document impact analysis algorithm in architecture

**Infrastructure Needed:**

- None (existing infrastructure sufficient)

**Approvals Required:**

- ✅ Option A (API-First) approved in ANALYSIS phase
- ✅ EVM metrics deferred to Sprint 8 approved
- ✅ Weekly granularity for S-curves approved
- ✅ Financial fields only for entity diff approved

---

## Output Format

**File Created:** `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/phase3/01-plan.md`

**Next Steps:**

1. ✅ Begin implementation with backend schema definition
2. ✅ Implement `ImpactAnalysisService` following TDD approach
3. ✅ Add `/impact` API endpoint
4. ✅ Build frontend dashboard components incrementally
5. ✅ Run full test suite and quality checks
6. ✅ Create DO phase document: `02-do.md`

**Related Architecture Docs:**

- [Bounded Contexts](../../../../02-architecture/01-bounded-contexts.md)
- [Coding Standards](../../../../02-architecture/coding-standards.md)
- [Change Management User Stories](../../../../01-product-scope/change-management-user-stories.md)

---

**Plan Status:** ✅ Complete - Ready for DO Phase
**Approval:** Option A (API-First) confirmed in ANALYSIS phase
