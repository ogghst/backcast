# Plan: Configurable Change Order Workflow — Phase A (Core Config)

**Created:** 2026-05-05
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 3 (Hybrid: Relational Core + JSONB Extensions)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 3 — Hybrid Approach with relational tables for core config (impact levels, approval rules, SLA rules) and JSONB for extension points (notification rules, custom fields).
- **Architecture**: Parent `co_workflow_config` table with child relational tables for typed config and JSONB columns for flexible extensions. Per-project overrides via `project_id` FK (nullable = global default). Follows existing `ProjectBudgetSettingsService` pattern.
- **Key Decisions** (from analysis):
  - Fixed 4 impact levels (LOW/MEDIUM/HIGH/CRITICAL) with configurable parameters (D5)
  - Per-project overrides with all-or-nothing model (D17), lazy inheritance (D10)
  - Config snapshot on CO submission for historical integrity (D6, D13)
  - Expand to 5-role approval system (D3)
  - Optimistic locking via version column (D20)
  - Fail-loudly if config missing, no hardcoded fallbacks (D18)
  - Impact calculation weights configurable in Phase A scope (D14)
  - Simple audit log for config changes (D15)

### Success Criteria

**Functional Criteria:**

- [ ] FR-1: Admin can view and modify impact level parameters (threshold amounts, score boundaries) via API VERIFIED BY: integration test
- [ ] FR-2: Admin can view and modify financial thresholds per impact level via API VERIFIED BY: integration test
- [ ] FR-3: Admin can view and modify approval authority mapping (role-to-authority) via API VERIFIED BY: integration test
- [ ] FR-4: Admin can view and modify SLA deadlines per impact level via API VERIFIED BY: integration test
- [ ] FR-5: Config changes take effect on new change orders without restart VERIFIED BY: integration test
- [ ] FR-6: Historical COs retain config values active at submission time VERIFIED BY: unit test
- [ ] FR-7: `FinancialImpactService` reads thresholds from config, not class constants VERIFIED BY: unit test
- [ ] FR-8: `ApprovalMatrixService` reads authority mapping from config, not hardcoded dicts VERIFIED BY: unit test
- [ ] FR-9: `SLAService` reads deadlines from config, not hardcoded dict VERIFIED BY: unit test
- [ ] FR-10: `ChangeOrderService` uses config service for score-to-impact mapping, removes duplicated SLA_BUSINESS_DAYS VERIFIED BY: unit test
- [ ] FR-11: Per-project config overrides global defaults when present VERIFIED BY: integration test
- [ ] FR-12: "Reset to Global Defaults" deletes per-project config, falls back to global VERIFIED BY: integration test
- [ ] FR-13: Concurrent config updates detected via optimistic locking (version check) VERIFIED BY: unit test
- [ ] FR-14: Missing config causes clear error, not silent fallback VERIFIED BY: unit test
- [ ] FR-15: Frontend config page allows admin to edit all Phase A parameters VERIFIED BY: E2E test
- [ ] FR-16: Frontend dynamically renders impact level labels/colors from config VERIFIED BY: component test

**Technical Criteria:**

- [ ] MyPy strict mode passes VERIFIED BY: `uv run mypy app/`
- [ ] Ruff zero errors VERIFIED BY: `uv run ruff check .`
- [ ] Test coverage >= 80% on new and modified code VERIFIED BY: `uv run pytest --cov`
- [ ] Config lookup adds < 5ms to workflow operations VERIFIED BY: benchmark test
- [ ] ESLint clean, TypeScript strict passes VERIFIED BY: `npm run lint && npm run typecheck`

**Business Criteria:**

- [ ] Existing SLA inconsistency (SLAService vs ChangeOrderService) eliminated VERIFIED BY: both services read from same config source
- [ ] 3-role gap in approval matrix resolved with 5-role system VERIFIED BY: integration test

### Scope Boundaries

**In Scope (Phase A):**

- Database schema: `co_workflow_config`, `co_impact_level_config`, `co_approval_rule_config`, `co_sla_rule_config`, `co_config_audit_log` tables
- `config_snapshot` JSONB column on `change_orders` table
- `ChangeOrderConfigService` for config CRUD and lookup
- Admin API routes for config management (global + per-project)
- RBAC permission: `change-order-workflow-config:manage` (global), `change-order-workflow-config:override` (per-project)
- Modification of `FinancialImpactService`, `ApprovalMatrixService`, `SLAService`, `ChangeOrderService` to read from config
- Alembic migration creating tables and seeding from current hardcoded values
- Frontend admin config page (global settings)
- Frontend project-level config override UI
- Frontend dynamic rendering of impact levels, colors, SLA info from API
- Impact calculation weights (budget%, schedule%, revenue%, EVM%) and score boundaries configurable

**Out of Scope:**

- Phase B: Workflow states/transitions configuration, SLA escalation rules
- Phase C: Notification rules, custom fields, holiday calendars, multi-currency, config export/import
- Adding/removing impact levels (levels fixed at 4)
- Multi-approver chains
- Config versioning via EVCS (simple audit log instead)
- Migration of existing COs (config_snapshot remains null, UI uses current config for display)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|-------------------|------------|
| 1 | Create domain models for config tables | `backend/app/models/domain/change_order_config.py` (new) | None | All 5 tables modeled with correct columns, types, constraints | Low |
| 2 | Create Pydantic schemas for config API | `backend/app/api/schemas/change_order_config.py` (new) | Task 1 | Request/response schemas for all config sections, validation rules | Low |
| 3 | Create Alembic migration | `backend/alembic/versions/` (new) | Task 1 | Tables created, global config seeded with current hardcoded values, `config_snapshot` column added to change_orders | Med |
| 4 | Create `ChangeOrderConfigService` | `backend/app/services/change_order_config_service.py` (new) | Task 1 | CRUD for global + per-project config, get_active_config with fallback, snapshot generation, optimistic locking | High |
| 5 | Create `ChangeOrderConfigAuditService` | `backend/app/services/change_order_config_service.py` (with Task 4) | Task 1 | Audit log writes on every config change (old/new values as JSONB) | Low |
| 6 | Modify `FinancialImpactService` to use config | `backend/app/services/financial_impact_service.py` | Tasks 1, 4 | Removes `THRESHOLD_*` class constants, reads thresholds from config service | Med |
| 7 | Modify `ApprovalMatrixService` to use config | `backend/app/services/approval_matrix_service.py` | Tasks 1, 4 | Removes `ROLE_AUTHORITY`, `IMPACT_AUTHORITY`, `AUTHORITY_HIERARCHY` dicts, reads from config service. Expands to 5-role system | Med |
| 8 | Modify `SLAService` to use config | `backend/app/services/sla_service.py` | Tasks 1, 4 | Removes `SLA_BUSINESS_DAYS` dict, reads from config service | Med |
| 9 | Modify `ChangeOrderService` to use config | `backend/app/services/change_order_service.py` | Tasks 1, 4 | Removes 2 duplicated `SLA_BUSINESS_DAYS`, replaces `_map_score_to_impact_level` thresholds with config lookup, adds config snapshot on submission | High |
| 10 | Create admin API routes | `backend/app/api/v1/change_order_config.py` (new) | Tasks 2, 4 | GET/PUT for global config, GET/PUT/DELETE for per-project config, RBAC enforcement | Med |
| 11 | Register routes and dependencies | `backend/app/api/v1/router.py`, `backend/app/api/deps.py` | Task 10 | Routes accessible, dependency injection wired | Low |
| 12 | Add RBAC permissions for config management | `backend/app/` (seeding/migration) | Task 10 | `change-order-workflow-config:manage` and `change-order-workflow-config:override` permissions seeded | Low |
| 13 | Frontend: API client and TanStack Query hooks | `frontend/src/features/change-orders/api/` (new files) | Task 10 | `useGlobalConfig`, `useProjectConfig`, `useUpdateGlobalConfig`, `useUpdateProjectConfig`, `useResetProjectConfig` hooks | Med |
| 14 | Frontend: Admin config page (global) | `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` (new) | Task 13 | Tabbed form: Impact Levels, Financial Thresholds, Approval Matrix, SLA Rules, Score Weights. Save/Reset buttons. Confirmation dialogs | High |
| 15 | Frontend: Project-level config override UI | `frontend/src/features/change-orders/components/ProjectConfigPanel.tsx` (new) | Task 13 | "Use Global Defaults" toggle, override sections when toggled off, "Reset to Defaults" button | Med |
| 16 | Frontend: Dynamic impact level rendering | `ApprovalInfo.tsx`, `ChangeOrderRecoveryDialog.tsx`, `ImpactLevelChart.tsx`, `AgingItemsList.tsx`, `useCanApprove.ts`, `WorkflowConstants.ts` | Task 13 | Impact levels, colors, labels, SLA info loaded from config API | Med |
| 17 | Update business guide documentation | `docs/05-user-guide/change-order-business-guide.md` | Tasks 6-9 | Document configurable parameters, admin workflow, per-project override feature | Low |

**Task Dependency Graph:**

```
Task 1 (Models) ─┬─> Task 2 (Schemas) ─────> Task 10 (API Routes) ─> Task 11 (Registration)
                  |                                │
                  ├─> Task 3 (Migration)           ├─> Task 12 (RBAC)
                  |                                │
                  └─> Task 4+5 (ConfigService) ──┬─┘
                         │                        │
                         ├─> Task 6 (Financial)   └─> Task 13 (Frontend API hooks)
                         ├─> Task 7 (Approval)              │
                         ├─> Task 8 (SLA)                    ├─> Task 14 (Admin Config Page)
                         └─> Task 9 (ChangeOrder)            ├─> Task 15 (Project Config Panel)
                                                             └─> Task 16 (Dynamic Rendering)

Task 17 (Docs) ── depends on Tasks 6-9 completion
```

**Parallel Execution Opportunities:**

- Tasks 2 and 3 can run in parallel (both depend only on Task 1)
- Tasks 6, 7, 8 can run in parallel (all depend on Tasks 1+4)
- Tasks 14, 15, 16 can run in parallel (all depend on Task 13)

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FR-1: Impact level params configurable | T-001 | `tests/unit/services/test_change_order_config_service.py` | GET/PUT impact level params returns updated values |
| FR-2: Financial thresholds configurable | T-002 | `tests/unit/services/test_change_order_config_service.py` | Updated threshold saved and returned |
| FR-3: Approval authority configurable | T-003 | `tests/unit/services/test_change_order_config_service.py` | Role-authority mapping updated correctly |
| FR-4: SLA deadlines configurable | T-004 | `tests/unit/services/test_change_order_config_service.py` | SLA days per level updated correctly |
| FR-5: No restart needed | T-005 | `tests/integration/test_config_lifecycle.py` | Config update reflected in next CO workflow call |
| FR-6: Historical CO integrity | T-006 | `tests/unit/services/test_change_order_service_config.py` | Config snapshot matches active config at submission time |
| FR-7: FinancialImpactService uses config | T-007 | `tests/unit/services/test_financial_impact_service.py` | Classification uses config thresholds, not class constants |
| FR-8: ApprovalMatrixService uses config | T-008 | `tests/unit/services/test_approval_matrix_service.py` | Authority lookup uses config mapping, supports 5 roles |
| FR-9: SLAService uses config | T-009 | `tests/unit/services/test_sla_service.py` | Deadline calculation uses config days, not hardcoded dict |
| FR-10: ChangeOrderService uses config | T-010 | `tests/unit/services/test_change_order_service_config.py` | Score mapping and SLA use config, no duplicated constants |
| FR-11: Per-project override | T-011 | `tests/integration/test_config_lifecycle.py` | Project with override uses project config, not global |
| FR-12: Reset to defaults | T-012 | `tests/integration/test_config_lifecycle.py` | Delete per-project config, next lookup returns global |
| FR-13: Optimistic locking | T-013 | `tests/unit/services/test_change_order_config_service.py` | Concurrent update with stale version raises ConflictError |
| FR-14: Missing config fails loud | T-014 | `tests/unit/services/test_change_order_config_service.py` | No global config raises ConfigurationError with clear message |
| FR-15: Frontend admin config page | T-015 | `tests/e2e/test_config_admin.spec.ts` | Admin can navigate to config page, edit values, save |
| FR-16: Dynamic frontend rendering | T-016 | `src/features/change-orders/__tests__/test_dynamic_rendering.tsx` | Impact labels/colors render from config data |

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/
│   ├── services/
│   │   ├── test_change_order_config_service.py      # Config CRUD, fallback, snapshot, locking
│   │   ├── test_financial_impact_service.py          # Threshold lookup from config
│   │   ├── test_approval_matrix_service.py           # Authority lookup from config, 5-role
│   │   ├── test_sla_service.py                       # Deadline lookup from config
│   │   └── test_change_order_service_config.py       # Score mapping, SLA dedup, snapshot
│   └── api/
│       └── test_change_order_config_routes.py        # API contract tests
├── integration/
│   └── test_config_lifecycle.py                      # Full lifecycle: create, update, override, reset
└── frontend/
    └── src/features/change-orders/
        ├── __tests__/
        │   └── test_dynamic_rendering.tsx            # Config-driven rendering
        └── components/
            └── __tests__/
                └── ChangeOrderConfigPage.test.tsx     # Admin config page tests
```

### Test Cases (First 8)

| Test ID | Test Name | Criterion | Type | Expected Result |
|---|---|---|---|---|
| T-001 | `test_get_global_config_returns_seeded_defaults` | FR-1 | Unit | Returns impact levels with correct threshold values from seed |
| T-002 | `test_update_financial_thresholds_persists` | FR-2 | Unit | PUT with new thresholds, GET returns updated values |
| T-003 | `test_update_approval_matrix_supports_5_roles` | FR-3 | Unit | PUT with 5-role mapping (viewer, editor_pm, dept_head, director, admin), GET returns all 5 |
| T-004 | `test_update_sla_deadlines_persists` | FR-4 | Unit | PUT with new SLA days, GET returns updated days |
| T-005 | `test_config_update_reflected_without_restart` | FR-5 | Integration | Update global config, submit CO, CO uses new thresholds |
| T-006 | `test_config_snapshot_captured_at_submission` | FR-6 | Unit | Submit CO, verify `config_snapshot` JSONB matches active config |
| T-007 | `test_financial_impact_uses_config_thresholds` | FR-7 | Unit | Set threshold LOW_MAX=20000, classify 15000 as LOW (not MEDIUM) |
| T-008 | `test_optimistic_locking_rejects_stale_update` | FR-13 | Unit | Fetch config v1, concurrent update to v2, update with v1 fails with 409 |

### Test Infrastructure Needs

- **Fixtures needed**: `global_config` fixture seeding the config tables, `project_config_override` fixture for per-project tests, `admin_user` fixture with config management permission
- **Mocks/stubs**: Config service mock for isolated service unit tests (FinancialImpact, ApprovalMatrix, SLA services)
- **Database state**: Alembic migration must run before integration tests; seed data fixture for global config

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Migration complexity: adding `config_snapshot` to existing `change_orders` table with data | Low | Medium | Migration adds nullable column; no backfill needed (D19) |
| Integration | Config service injection into 4 existing services changes their constructor signatures | Medium | Medium | Use FastAPI `Depends()` injection; constructor accepts optional config_service param for backward compat during migration |
| Data | Seeded global config must exactly match current hardcoded behavior | Medium | High | Integration test comparing seeded values against current hardcoded constants before migration ships |
| Performance | Config lookup on every CO operation adds DB query | Low | Medium | Cache active config per-request lifecycle (one query per request, not per service call) |
| Frontend | Dynamic rendering may break existing CO views if config fetch fails | Medium | Medium | Frontend falls back to hardcoded defaults during loading; error boundary for config fetch failure |
| Regression | Existing CO workflow tests depend on hardcoded values | Medium | Medium | Seed global config with exact current hardcoded values in test fixtures |

---

## Documentation References

### Required Reading

- Backend Coding Standards: `docs/02-architecture/backend/coding-standards.md`
- Entity Classification Guide: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- Change Order Business Guide: `docs/05-user-guide/change-order-business-guide.md`
- ProjectBudgetSettingsService pattern: `backend/app/services/project_budget_settings_service.py`

### Code References

- Precedent for per-project config: `backend/app/services/project_budget_settings_service.py`
- Precedent for DB-driven config: `backend/app/services/ai_config_service.py`
- Current hardcoded values: `backend/app/services/financial_impact_service.py` lines 39-42, `backend/app/services/approval_matrix_service.py` lines 47-67, `backend/app/services/sla_service.py` lines 38-43
- Frontend impact level rendering: `frontend/src/features/change-orders/components/ApprovalInfo.tsx`, `WorkflowConstants.ts`

---

## Prerequisites

### Technical

- [ ] Database migrations applied (Task 3)
- [ ] Dependencies installed (`uv sync`)
- [ ] Frontend dependencies installed (`npm install --legacy-peer-deps`)

### Documentation

- [x] Analysis phase approved (00-analysis.md)
- [ ] Architecture docs reviewed (entity classification, coding standards)
- [ ] Existing service implementations understood (all 4 services with hardcoded values)
