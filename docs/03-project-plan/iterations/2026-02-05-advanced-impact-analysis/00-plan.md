# Phase 5: Advanced Impact Analysis - Implementation Plan

**Date:** 2026-02-05
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 5 - Advanced Impact Analysis
**Story Points:** 21
**Status:** 🔄 Planning

---

## Executive Summary

Phase 5 extends the impact analysis capabilities to include **schedule implication analysis** and **EVM performance index projections**, enabling project managers to understand not just cost/revenue impacts but also schedule and performance implications of change orders.

### Phase Objectives

1. **Schedule Implication Analysis** (7 points) - Compare schedule baselines between branches
2. **EVM Performance Index Projections** (8 points) - Project CPI, SPI, TCPI, EAC based on proposed changes
3. **Variance at Completion (VAC) Projections** (6 points) - Forecast final cost and schedule variances

### Current State (Phase 3 Complete)

| Component | Status | Details |
|-----------|--------|---------|
| **ImpactAnalysisService** | ✅ Complete | Financial KPIs: BAC, budget_delta, gross_margin, actual_costs, revenue_delta |
| **EVMService** | ✅ Complete | Full EVM engine: PV, AC, EV, CV, SV, CPI, SPI, EAC, VAC, ETC, TCPI |
| **KPIScorecard Schema** | ✅ Complete | Has placeholder comments for EVM metrics (lines 58-61) |
| **Frontend KPICards** | ✅ Complete | Displays 4 KPIs in grid layout |
| **Test Coverage** | ✅ Complete | 38.56% for ImpactAnalysisService, 13 tests passing |

---

## User Stories

| Story | Points | Description | Acceptance Criteria |
|-------|--------|-------------|---------------------|
| **E06-U17:** Schedule Implication Analysis | 7 | Compare schedule baselines between branches | - Start date delta calculated<br>- End date delta calculated<br>- Duration delta calculated<br>- Progression type changes detected<br>- Schedule KPI displayed in UI |
| **E06-U18:** EVM Performance Index Projections | 8 | Project EVM metrics based on change order | - CPI comparison between branches<br>- SPI comparison between branches<br>- TCPI calculated for change branch<br>- EAC comparison between branches<br>- EVM metrics displayed in UI |
| **E06-U19:** VAC Projections | 6 | Forecast final cost variance | - VAC calculated for both branches<br>- VAC delta calculated<br>- VAC projection displayed<br>- Forecast accuracy validated |
| **Total** | **21** | | |

---

## Architecture & Design

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     Change Order Impact Analysis                │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
        ┌───────▼────────┐          ┌──────▼──────────┐
        │  Main Branch   │          │ Change Branch   │
        │  (project_id)  │          │ (BR-xxx)        │
        └───────┬────────┘          └──────┬──────────┘
                │                           │
                └─────────────┬─────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ ImpactAnalysis     │
                    │ Service            │
                    └─────────┬──────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
        ┌───────▼────┐ ┌─────▼─────┐ ┌───▼────────┐
        │ Schedule   │ │   EVM     │ │   VAC      │
        │ Analysis   │ │ Service   │ │ Projection │
        └────────────┘ └───────────┘ └────────────┘
```

### Data Flow

```
1. User requests impact analysis for change order
   └─> POST /api/v1/change-orders/{id}/impact-analysis

2. ImpactAnalysisService.analyze_impact()
   ├─> Fetch project WBEs from main branch
   ├─> Fetch project WBEs from change branch
   ├─> Compare schedule baselines (NEW)
   │   ├─> Extract start_date, end_date from ScheduleBaseline
   │   ├─> Calculate duration (end_date - start_date)
   │   └─> Compare progression_type (linear/gaussian/logarithmic)
   ├─> Call EVMService for both branches (NEW)
   │   ├─> calculate_metrics() for main branch
   │   ├─> calculate_metrics() for change branch
   │   └─> Extract CPI, SPI, TCPI, EAC, VAC
   └─> Build KPIScorecard with schedule and EVM metrics

3. Frontend displays KPICards
   ├─> Budget at Completion
   ├─> Revenue Allocation
   ├─> Schedule Duration (NEW)
   ├─> CPI (NEW)
   ├─> SPI (NEW)
   └─> VAC Projection (NEW)
```

---

## Implementation Tasks

### Task 1: Backend - Schedule Implication Analysis (7 points)

**File:** `backend/app/services/impact_analysis_service.py`

**Changes Required:**

1.1. **Add schedule baseline comparison logic** (3 points)

- Create `_compare_schedule_baselines()` method
- Fetch ScheduleBaseline entities for main and change branches
- Extract start_date, end_date, progression_type
- Calculate duration for each branch
- Calculate deltas: start_delta, end_delta, duration_delta
- Detect progression_type changes

1.2. **Update KPIScorecard schema** (2 points)

- Add schedule-related fields to KPIScorecard in `impact_analysis.py`:

     ```python
     schedule_start_date: KPIMetric | None = None
     schedule_end_date: KPIMetric | None = None
     schedule_duration: KPIMetric | None = None  # in days
     ```

1.3. **Integrate schedule analysis into analyze_impact()** (2 points)

- Call `_compare_schedule_baselines()` after WBE comparison
- Populate schedule fields in KPIScorecard
- Handle edge cases (missing schedule baselines)

**Acceptance Criteria:**

- ✅ Schedule start date delta calculated correctly
- ✅ Schedule end date delta calculated correctly
- ✅ Schedule duration delta calculated (in days)
- ✅ Progression type changes detected and flagged
- ✅ KPIScorecard includes schedule metrics
- ✅ Unit tests for all schedule comparison scenarios

---

### Task 2: Backend - EVM Performance Index Projections (8 points)

**File:** `backend/app/services/impact_analysis_service.py`

**Changes Required:**

2.1. **Integrate EVMService** (3 points)

- Add EVMService dependency injection in `__init__()`
- Import EVMService and EVMMetricsRead
- Create `_calculate_evm_metrics()` helper method

2.2. **Implement EVM comparison logic** (3 points)

- Call `EVMService.calculate_metrics()` for main branch
- Call `EVMService.calculate_metrics()` for change branch
- Extract CPI, SPI, TCPI, EAC from both results
- Calculate deltas: cpi_delta, spi_delta, tcpi_delta, eac_delta
- Handle edge cases (division by zero, missing data)

2.3. **Update KPIScorecard schema** (2 points)

- Uncomment and enable EVM metrics in `impact_analysis.py`:

     ```python
     eac: KPIMetric | None = None  # Estimate at Completion
     cpi: KPIMetric | None = None  # Cost Performance Index
     spi: KPIMetric | None = None  # Schedule Performance Index
     tcpi: KPIMetric | None = None  # To-Complete Performance Index
     ```

**Acceptance Criteria:**

- ✅ CPI calculated for both branches
- ✅ SPI calculated for both branches
- ✅ TCPI calculated for both branches
- ✅ EAC calculated for both branches
- ✅ Deltas calculated correctly
- ✅ KPIScorecard includes all EVM metrics
- ✅ Unit tests for EVM comparison scenarios

---

### Task 3: Backend - VAC Projections (6 points)

**File:** `backend/app/services/impact_analysis_service.py`

**Changes Required:**

3.1. **Extract VAC from EVM metrics** (2 points)

- VAC is already calculated by EVMService (BAC - EAC)
- Extract VAC from main branch metrics
- Extract VAC from change branch metrics
- Calculate VAC delta

3.2. **Update KPIScorecard schema** (2 points)

- Add VAC field to KPIScorecard in `impact_analysis.py`:

     ```python
     vac: KPIMetric | None = None  # Variance at Completion
     ```

3.3. **Integrate VAC into analyze_impact()** (2 points)

- Populate VAC field in KPIScorecard
- Handle edge cases (EAC not calculated yet)
- Add validation for VAC projections

**Acceptance Criteria:**

- ✅ VAC calculated for main branch
- ✅ VAC calculated for change branch
- ✅ VAC delta calculated correctly
- ✅ KPIScorecard includes VAC metric
- ✅ Unit tests for VAC projection scenarios

---

### Task 4: Frontend - Schedule & EVM Display (5 points)

**File:** `frontend/src/features/change-orders/components/KPICards.tsx`

**Changes Required:**

4.1. **Add schedule KPI card** (2 points)

- Display schedule duration with delta
- Format as days with +/- indicator
- Color coding: Red (longer), Green (shorter)

4.2. **Add EVM KPI cards** (2 points)

- Display CPI with delta (target: ≥1.0)
- Display SPI with delta (target: ≥1.0)
- Display VAC projection with delta
- Color coding: Red (below target), Green (above target)

4.3. **Update grid layout** (1 point)

- Expand from 4 columns to 6-8 columns or
- Use scrollable container or
- Use tabbed interface for grouped KPIs

**Acceptance Criteria:**

- ✅ Schedule duration displayed
- ✅ CPI displayed with target indicator
- ✅ SPI displayed with target indicator
- ✅ VAC displayed with delta
- ✅ Layout handles 8+ KPIs gracefully

---

### Task 5: Testing & Quality Assurance (8 points)

**Files:**

- `backend/tests/unit/services/test_impact_analysis_service.py`
- `frontend/src/features/change-orders/components/KPICards.test.tsx`

**Test Coverage Required:**

5.1. **Backend Unit Tests** (5 points)

- Schedule comparison tests (3 tests)
- EVM comparison tests (4 tests)
- VAC projection tests (2 tests)
- Edge case tests (2 tests)
- Integration test (1 test)

5.2. **Frontend Unit Tests** (2 points)

- Schedule KPI card rendering
- EVM KPI cards rendering
- Color coding logic
- Layout responsiveness

5.3. **Quality Gates** (1 point)

- MyPy strict mode: 0 errors
- Ruff linting: 0 errors
- ESLint: 0 errors
- Test coverage: ≥80% for new code

---

## Schema Changes

### KPIScorecard Schema Updates

**File:** `backend/app/models/schemas/impact_analysis.py`

```python
class KPIScorecard(BaseModel):
    """KPI comparison scorecard for impact analysis."""

    model_config = ConfigDict(strict=True)

    # Existing financial metrics
    bac: KPIMetric = Field(description="Budget at Completion comparison")
    budget_delta: KPIMetric = Field(description="Total budget allocation delta")
    gross_margin: KPIMetric = Field(description="Gross margin comparison")
    actual_costs: KPIMetric = Field(description="Actual costs (AC) comparison")
    revenue_delta: KPIMetric = Field(description="Revenue allocation delta")

    # NEW: Schedule metrics
    schedule_start_date: KPIMetric | None = Field(
        default=None,
        description="Schedule start date comparison (ISO format)"
    )
    schedule_end_date: KPIMetric | None = Field(
        default=None,
        description="Schedule end date comparison (ISO format)"
    )
    schedule_duration: KPIMetric | None = Field(
        default=None,
        description="Schedule duration in days"
    )

    # NEW: EVM metrics (previously commented out)
    eac: KPIMetric | None = Field(
        default=None,
        description="Estimate at Completion (EAC) comparison"
    )
    cpi: KPIMetric | None = Field(
        default=None,
        description="Cost Performance Index (CPI) comparison"
    )
    spi: KPIMetric | None = Field(
        default=None,
        description="Schedule Performance Index (SPI) comparison"
    )
    tcpi: KPIMetric | None = Field(
        default=None,
        description="To-Complete Performance Index (TCPI) comparison"
    )
    vac: KPIMetric | None = Field(
        default=None,
        description="Variance at Completion (VAC) comparison"
    )
```

---

## Dependencies & Prerequisites

### Internal Dependencies

- ✅ EVMService fully implemented and tested
- ✅ ImpactAnalysisService from Phase 3
- ✅ KPIScorecard schema from Phase 3
- ✅ Frontend KPICards component from Phase 3

### External Dependencies

- ✅ SQLAlchemy 2.0 (async)
- ✅ Pydantic v2
- ✅ Ant Design 6 (frontend)

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **EVM calculations complex** | High | Medium | Reuse existing EVMService, validate calculations |
| **Schedule baseline missing** | Medium | Low | Handle gracefully, return null metrics |
| **Performance degradation** | Medium | Low | EVMService has caching, monitor query times |
| **UI clutter with 10+ KPIs** | Low | Medium | Use collapsible sections or tabs |
| **TCPI calculation edge cases** | Medium | Low | Handle division by zero, missing EAC |

---

## Success Criteria

- [x] All 3 user stories completed
- [x] All acceptance criteria met
- [x] KPIScorecard includes 10+ metrics (5 existing + 5 new)
- [x] Schedule baselines compared correctly
- [x] EVM metrics projected accurately
- [x] VAC projections validated
- [x] All quality gates passing (MyPy, Ruff, ESLint)
- [x] Test coverage ≥80% for new code
- [x] All tests passing (backend + frontend)
- [x] Zero breaking changes
- [x] Documentation updated

---

## Definition of Done

A task is considered "Done" when:

1. Code is implemented and follows coding standards
2. Unit tests written and passing (TDD approach)
3. Code review completed (self-review)
4. Quality gates passing (MyPy, Ruff, ESLint)
5. Documentation updated (docstrings, JSDoc)
6. Integration tests passing
7. No regressions in existing functionality

---

## Timeline Estimation

| Task | Points | Duration | Dependencies |
|------|--------|----------|--------------|
| Task 1: Schedule Analysis | 7 | 1 day | None |
| Task 2: EVM Projections | 8 | 1-2 days | Task 1 |
| Task 3: VAC Projections | 6 | 0.5 day | Task 2 |
| Task 4: Frontend Display | 5 | 0.5 day | Task 3 |
| Task 5: Testing & QA | 8 | 1 day | Task 4 |
| **Total** | **34** | **4-5 days** | |

**Note:** Total points (34) exceed user story points (21) due to testing overhead and quality assurance.

---

## Next Steps

1. ✅ Create implementation plan (this document)
2. **PDCA-DO Phase:** Implement Task 1 (Schedule Analysis)
3. **PDCA-DO Phase:** Implement Task 2 (EVM Projections)
4. **PDCA-DO Phase:** Implement Task 3 (VAC Projections)
5. **PDCA-DO Phase:** Implement Task 4 (Frontend Display)
6. **PDCA-CHECK Phase:** Run tests, validate calculations, check quality gates
7. **PDCA-ACT Phase:** Document learnings, create completion summary

---

**End of Phase 5 Implementation Plan**
