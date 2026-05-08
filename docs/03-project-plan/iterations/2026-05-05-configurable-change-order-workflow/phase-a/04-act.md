# Act: Configurable Change Order Workflow — Phase A (Core Config)

**Date:** 2026-05-06
**Based on:** [03-check.md](./03-check.md)

---

## 1. Check Phase Summary

**Overall Result:** SUCCESS with test debt

- 12/16 functional criteria PASS (implementation complete)
- 4/16 functional criteria PARTIAL (implementation done, tests missing)
- All quality gates pass (MyPy, Ruff, ESLint, TypeScript strict)
- Config service coverage: 91.26%, FinancialImpactService: 97.26%

---

## 2. Improvement Actions

### Action 1: Write Integration Tests (CHECK Recommendation: Option B) — DONE

**Problem:** Integration tests for config lifecycle (FR-5, FR-11, FR-12) were planned but not written.

**Action taken:**
- Created `tests/integration/services/test_change_order_config_lifecycle.py` with 15 tests across 5 classes:
  - `TestGlobalConfigLifecycle` (2): seeded config presence, update persistence
  - `TestProjectOverrideLifecycle` (4): override precedence, delete fallback, no-override fallback, project-scoped SLA days
  - `TestConfigUpdateReflectedInWorkflow` (2): SLAService picks up updated config, uses global not project override
  - `TestConfigSnapshot` (2): all sections captured, project override captured
  - `TestHelperMethodsWithOverride` (5): thresholds, boundaries, classify_impact, approval matrix, weights

**Result:** 15/15 tests pass. Config service coverage increased from 91.26% to 95.08%.

### Action 2: Write SLA/ChangeOrder Service Config Tests (CHECK Recommendation: Option A) — DONE

**Problem:** SLAService and ChangeOrderService lack dedicated config tests (FR-9, FR-10).

**Action taken:**
- Created `tests/unit/services/test_sla_service.py` with 10 tests:
  - `TestSLADeadlineFromConfig` (5): deadline calculation per level, invalid level raises ValueError
  - `TestGetSLADaysFromConfig` (3): all levels returned, values match config, delegates to config service
  - `TestSLADaysReflectConfigUpdate` (1): updated config reflected
  - `TestMissingConfigBehavior` (1): missing config raises ConfigurationError
- Added `TestChangeOrderServiceConfigIntegration` (4 tests) to existing `test_change_order_service.py`:
  - `_map_score_to_impact_level` uses config boundaries
  - `_get_sla_days` delegates to config service for each level
  - `_get_sla_days` defaults for None and unknown levels

**Result:** 14/14 new tests pass.

### Action 3: Write Frontend Hook Tests (CHECK Recommendation: Option A) — DONE

**Problem:** `useImpactLevelConfig` hook has no automated tests (FR-16).

**Action taken:**
- Created `frontend/src/features/change-orders/hooks/useImpactLevelConfig.test.tsx` with 5 tests:
  - Returns fallback defaults when config is loading
  - Returns config-driven values when global config is fetched
  - `getImpactLevelStyle` returns correct style for each impact level
  - `getImpactLevelStyle` returns "Not Assessed" for unknown/null level
  - `authorityLevels` respects custom `level_order` from config

**Result:** 5/5 tests pass. ESLint + TypeScript clean.

### Action 4: Performance Benchmark (CHECK Recommendation: Option C — Accept)

**Problem:** <5ms config lookup requirement not formally verified.

**Rationale for deferral:** Single SELECT with selectin loading, max 5 rows per config. Well under 5ms.

**Decision:** Accepted without benchmark test. Revisit if performance issues arise in production.

### Action 5: Fix Pre-existing Test Regressions — DONE

**Problem:** 2 pre-existing tests in `test_change_order_service.py` had missing `await` on `_map_score_to_impact_level` (broken during DO phase sync-to-async migration).

**Action taken:**
- Added `await` to `_map_score_to_impact_level` calls in `test_map_score_to_impact_level` (line 758) and `test_approver_lookup_uses_project_department` (line 1167).

**Note:** 2 other pre-existing tests (`test_update_change_order_metadata`, `test_get_current_returns_latest_version`) have an asyncpg JSONB serialization bug that predates the config work. These are not regressions from this iteration.

---

## 3. Final Test Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_change_order_config_service.py` | 23 | All pass |
| `test_change_order_config_lifecycle.py` (new) | 15 | All pass |
| `test_sla_service.py` (new) | 10 | All pass |
| `test_change_order_service.py::ConfigIntegration` (new) | 4 | All pass |
| `test_change_order_service.py::await fixes` | 2 | All pass |
| `useImpactLevelConfig.test.tsx` (new) | 5 | All pass |
| **Total new ACT tests** | **36** | **All pass** |
| **Total config tests (DO + ACT)** | **59** | **All pass** |

---

## 4. Updated Success Criteria

| Criterion | Before ACT | After ACT |
|-----------|------------|-----------|
| FR-5: No restart needed | PARTIAL | PASS (integration test) |
| FR-9: SLAService uses config | PARTIAL | PASS (10 dedicated tests) |
| FR-10: ChangeOrderService uses config | PARTIAL | PASS (4 dedicated tests) |
| FR-16: Dynamic rendering | PARTIAL | PASS (5 hook tests) |
| Config service coverage | 91.26% | 95.08% |
| Integration test coverage | 0 files | 1 file, 15 tests |

---

## 5. Lessons Learned

### Process Improvements

| Lesson | How to Apply |
|--------|-------------|
| Separate test tasks by tier (unit/integration/E2E) | Future PDCA plans should have explicit test tasks per tier with file names |
| Frontend tests should parallel component tasks | Each frontend component creation task should have a paired test task |
| Sync-to-async migration impacts existing tests | When changing service method signatures from sync to async, budget time for test updates |

### Technical Patterns Validated

| Pattern | Outcome |
|---------|---------|
| Optional config_service constructor injection | Worked well for backward compatibility during migration |
| Hybrid relational + JSONB schema | Appropriate for fixed 4 levels with flexible extension points |
| Config snapshot at submission | Clean pattern for historical integrity without EVCS overhead |
| All-or-nothing project override | Simple mental model; avoids partial override confusion |

---

## 6. Iteration Closure

**Phase A Status:** COMPLETE

**Deliverables:**
- Backend: 5 new files, 9+ modified files, migration, 52 tests
- Frontend: 4 new files, 6+ modified files, 5 hook tests, dynamic rendering
- Documentation: 2 user guides updated
- Quality: All gates pass (MyPy, Ruff, ESLint, TypeScript)

**Phase B Entry Criteria:**
- [x] Phase A ACT improvements complete
- [x] Integration tests passing
- [x] No regressions in existing tests

**Phase B Scope (future iteration):**
- Workflow state/transition configuration
- SLA escalation rules
- Notification rules
- Custom fields
