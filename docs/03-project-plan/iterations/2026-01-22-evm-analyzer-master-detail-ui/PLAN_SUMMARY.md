# PLAN Summary - EVM Analyzer with Master-Detail UI

**Quick Reference for DO Phase Executors**

---

## Overview

This plan implements **Option 2: Phased Implementation with Reusable Architecture** for an enhanced EVM Analysis feature with master-detail UI and advanced visualization modal.

**Scope**: Phase 1 (Cost Element) + Phase 2 (WBE/Project Support)
**Estimated Effort**: 40-55 hours with parallelization (60-80 hours sequential)
**Test Coverage**: 80%+ required for all new code

---

## Key User Decisions (Analysis Phase)

1. **EVMMetric structure**: Flat response (NOT list of EVMMetricBase)
2. **Phase 2 included**: WBE and project support in this iteration
3. **Time-series**: Pre-calculate server-side
4. **Chart zoom**: Ant Design built-in
5. **Gauge design**: Traditional semi-circle
6. **Aggregation**: Backend (not frontend)
7. **Descriptions**: Static/hardcoded
8. **Default granularity**: Weekly
9. **Empty data**: Show empty state
10. **Index aggregation**: Weighted by BAC

---

## Critical Success Criteria

### Must Have (Gates for Completion):
- [ ] All 27 tasks completed
- [ ] All acceptance criteria tests pass (T-BE-*, T-FE-*)
- [ ] Performance benchmarks met (<500ms summary, <2s modal, <1s queries)
- [ ] Zero MyPy/Ruff/ESLint errors
- [ ] 80%+ test coverage
- [ ] All tests run **sequentially** (database constraint)

### Phase 1 (Cost Element):
- [ ] ForecastComparisonCard organized by topic
- [ ] EVM Analyzer modal with gauges and charts
- [ ] Time-series data with granularity selector
- [ ] Generic components (EntityType polymorphism)

### Phase 2 (WBE/Project):
- [ ] WBE metrics from child cost elements
- [ ] Project metrics from child WBEs
- [ ] Multi-entity aggregation (sum + weighted avg)
- [ ] Entity type switching in UI

---

## Parallel Execution Strategy

### Can Run in Parallel (Same Time):
1. **Level 0**: BE-001 (schemas) + FE-001 (types after BE-001)
2. **Level 1**: FE-002, FE-003, FE-004, FE-005, FE-006 (components)
3. **Level 2**: BE-007, BE-008 (WBE/Project services)

### Must Run Sequentially:
1. **Backend tests**: BE-005 → BE-006 (database constraint)
2. **Frontend tests**: FE-009 → FE-010 → FE-011 (database constraint)
3. **All E2E tests**: FE-011 (must run last)

**Time Savings**: ~20-25 hours (33% reduction)

---

## Task Breakdown Highlights

### Backend (13 tasks):
1. **Schemas** (BE-001): Generic EVMMetric Pydantic models
2. **Service** (BE-002, BE-003): Multi-entity + time-series methods
3. **API** (BE-004): Generic routes `/api/v1/evm/{entity_type}/{id}/metrics`
4. **Tests** (BE-005, BE-006): Unit + integration (sequential)
5. **WBE/Project** (BE-007, BE-008, BE-009): Child entity aggregation
6. **Optimization** (BE-FE-001): Performance profiling

### Frontend (14 tasks):
1. **Types** (FE-001): TypeScript interfaces match backend
2. **Components** (FE-002 to FE-007): MetricCard, Gauge, Charts, Modal
3. **Hooks** (FE-008): useEVMMetrics, useEVMTimeSeries
4. **Refactor** (FE-009): ForecastComparisonCard uses new components
5. **Tests** (FE-010, FE-011): Component + E2E (sequential)
6. **WBE/Project** (FE-012, FE-013, FE-014): Entity switching

### Shared (2 tasks):
1. **Documentation** (BE-FE-002): API docs, ADR, examples
2. **Final Testing** (BE-FE-003): Integration, bug fixes, UAT

---

## Test Specifications

### First 10 Critical Tests:
1. **T-BE-001**: Single cost element metrics calculation
2. **T-BE-002**: Multi-entity sum aggregation (amounts)
3. **T-BE-003**: Multi-entity weighted avg aggregation (indices)
4. **T-BE-004**: No progress returns EV=0 with warning
5. **T-BE-005**: Division by zero returns None for indices
6. **T-BE-006**: Time-travel respects control_date
7. **T-BE-007**: Time-series weekly grouping
8. **T-BE-008**: API GET metrics returns 200
9. **T-BE-009**: API GET metrics returns 404 for invalid ID
10. **T-BE-010**: API batch metrics aggregation

### Test Hierarchy:
- Backend Unit: `test_evm_service.py`, `test_evm_service_wbe_project.py`
- Backend Integration: `test_evm_routes.py`
- Frontend Unit: Component tests in `__tests__/`
- Frontend E2E: `evm-analyzer.spec.ts`

---

## Risk Mitigation

### High Priority Risks:
1. **Time-series performance** (Medium/High)
   - Add indexes on `cost_registrations.date`, `progress_entries.reported_at`
   - Cache query results with TanStack Query
   - Materialized view if >2s queries

2. **Multi-entity aggregation bugs** (Medium/High)
   - Unit tests with known datasets
   - Validate against Excel calculations
   - Use Decimal type for precision

3. **Sequential test time** (High/Medium)
   - Accept as constraint (documented)
   - Optimize cleanup (transaction rollback)
   - Partition tests (backend || frontend parallel)

---

## Architecture References

### Backend Patterns:
- **EVM Service**: `backend/app/services/evm_service.py` (extend)
- **EVM Schemas**: `backend/app/models/schemas/evm.py` (extend)
- **API Routes**: `backend/app/api/routes/cost_elements.py:529-546` (reference)

### Frontend Patterns:
- **Chart Component**: `frontend/src/features/change-orders/components/SCurveComparison.tsx`
- **SVG Chart**: `frontend/src/features/schedule-baselines/components/ProgressionPreviewChart.tsx`
- **Current EVM**: `frontend/src/features/forecasts/components/ForecastComparisonCard.tsx` (refactor)

### Test Patterns:
- **Backend**: `backend/tests/conftest.py` (fixtures)
- **Frontend**: `frontend/src/test/utils/testUtils.tsx` (render utilities)

---

## DO Phase Handoff

### What DO Phase Receives:
- ✅ 27 decomposed tasks with dependencies
- ✅ 20+ test specifications with expected behaviors
- ✅ Task dependency graph for parallel execution
- ✅ Risk register with mitigations
- ✅ Success criteria (measurable and verifiable)

### What DO Phase Must Do:
1. Implement test code **first** (RED phase)
2. Implement feature code to make tests pass (GREEN phase)
3. Refactor for clean code (REFACTOR phase)
4. Run tests **sequentially** (no parallel execution)
5. Document decisions in ADRs
6. Update OpenAPI spec after schema changes

### Critical Constraints:
- **Tests CANNOT run in parallel** (single database, data destruction)
- **Time-travel semantics** must use Valid Time Travel (not Transaction Time)
- **MyPy strict mode** required (zero errors)
- **TypeScript strict mode** required (zero errors)
- **80%+ coverage** for all new code

---

## Quick Commands

### Backend:
```bash
cd backend
uv run uvicorn app.main:app --reload
uv run pytest tests/unit/services/test_evm_service.py
uv run pytest tests/api/test_evm_routes.py
uv run mypy app/services/evm_service.py
uv run ruff check app/services/evm_service.py
```

### Frontend:
```bash
cd frontend
npm run dev
npm test -- EVMSummaryView
npm run test:e2e -- evm-analyzer.spec.ts
npm run lint
npm run generate-client  # After backend schema changes
```

### Full Quality Check:
```bash
# Backend
cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest

# Frontend
cd frontend && npm run lint && npm run test:coverage
```

---

## Next Steps

1. **DO Phase - Backend Executor**: Start with BE-001 (schemas)
2. **DO Phase - Frontend Executor**: Wait for BE-001, then start FE-001 (types)
3. **Parallel Execution**: Use task dependency graph to identify parallelizable tasks
4. **Testing**: Run all tests sequentially (use `pytest -v` for visibility)
5. **Progress Tracking**: Update task status in dependency graph

---

**Document**: `docs/03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/01-plan.md`
**Created**: 2026-01-22
**Status**: Ready for DO Phase Execution

---

*"This plan defines WHAT to build and HOW to verify success. The DO phase will determine HOW to implement it."*
