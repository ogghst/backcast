# Plan: Phase B - SLA Escalation Rules + Configurable Workflow Transitions

**Created:** 2026-05-08
**Status:** In Progress
**Analysis:** `00-analysis.md`

---

## Decisions (from analysis questions)

1. **Escalation mode:** Manual API endpoint + background scheduler method
2. **RBAC permission:** New `change-order-escalate` permission
3. **Workflow tab UI:** Simple table with status dropdowns
4. **Fallback strategy:** Fail loudly if no config record exists; use hardcoded defaults only when config exists but `workflow_transitions` column is NULL

---

## Task Breakdown

### Backend — SLA Escalation (3 tasks)

**Task 1: Add ESCALATED status and escalation methods**
Files:
- `backend/app/models/domain/change_order.py` — Add `ESCALATED = "escalated"` to SLAStatus
- `backend/app/services/sla_service.py` — Add `check_escalation_eligible()`, `get_escalatable_change_orders()`, `escalate_change_order()`, update `calculate_sla_status()`
- `backend/app/services/change_order_config_service.py` — Update `generate_snapshot()` and `_config_to_dict()` to include `escalation_trigger_pct`

**Task 2: Add escalation API endpoint**
Files:
- `backend/app/api/routes/change_orders.py` — `POST /{change_order_id}/escalate`
- Permission seed: add `change-order-escalate`

**Task 3: Write escalation tests**
Files:
- Add escalation tests to `backend/tests/unit/services/test_sla_service.py`
- New `backend/tests/integration/services/test_sla_escalation_lifecycle.py`

### Backend — Configurable Workflow Transitions (4 tasks)

**Task 4: Domain model + migration for workflow_transitions**
Files:
- `backend/app/models/domain/change_order_config.py` — Add `workflow_transitions` JSONB column
- New `backend/alembic/versions/20260508_add_workflow_transitions_config.py`

**Task 5: Pydantic schemas + config service updates**
Files:
- `backend/app/models/schemas/change_order_config.py` — `WorkflowTransitionsSchema`, update request/response
- `backend/app/services/change_order_config_service.py` — `get_workflow_transitions()`, update CRUD, update snapshot
- `backend/app/api/routes/change_order_config.py` — Forward `workflow_transitions` in PUT handlers

**Task 6: Refactor WorkflowService for config-driven transitions**
Files:
- `backend/app/services/change_order_workflow_service.py` — Config injection, fallback to defaults
- `backend/app/services/change_order_service.py` — Wire config injection at line 60

**Task 7: Write workflow transitions tests**
Files:
- Update `backend/tests/unit/services/test_change_order_workflow_service.py`
- Update `backend/tests/unit/services/test_change_order_config_service.py`
- Update `backend/tests/integration/services/test_change_order_config_lifecycle.py`

### Frontend (2 tasks)

**Task 8: Update types + add Workflow tab**
Files:
- `frontend/src/features/change-orders/api/useWorkflowConfig.ts` — Add `WorkflowTransitionsConfig` type
- `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` — Add "Workflow" tab

**Task 9: Escalation UI + frontend quality**
Files:
- `frontend/src/features/change-orders/components/ApprovalInfo.tsx` — Add ESCALATED badge
- Add escalation mutation hook
- Run `npm run lint && npm run typecheck`

---

## Success Criteria

- [ ] `SLAStatus.ESCALATED` exists and escalation logic works
- [ ] `POST /api/v1/change-orders/{id}/escalate` returns 200
- [ ] `GET /api/v1/change-order-config/global` returns `workflow_transitions` field
- [ ] `ChangeOrderWorkflowService` reads transitions from config when available
- [ ] Config page shows 5 tabs including "Workflow"
- [ ] All new code has 80%+ test coverage
- [ ] MyPy strict, Ruff clean, TypeScript strict, ESLint clean
