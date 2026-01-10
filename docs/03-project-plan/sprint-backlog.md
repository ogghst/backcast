# Current Iteration

**Iteration:** Control Date Implementation
**Start Date:** 2026-01-10
**End Date:** 2026-01-10
**Status:** ✅ **COMPLETE** (ACT Phase)

---

## Goal

Enable users to perform Create, Update, and Delete operations on entities (Project, WBE, Cost Element) at a specific point in time ("Control Date"), ensuring that the validity of the data reflects that chosen date rather than the current clock time.

**Key Focus Areas:**

1.  **Backend Commands**: Update commands to accept and utilize `control_date`.
2.  **Service Layer**: Refactor services to propagate `control_date` to commands.
3.  **API Schema**: Expose `control_date` in creation/update payloads and delete query parameters.
4.  **Frontend Integration**: Update React Hooks to inject `control_date` from the global Time Machine context automatically.

---

## Stories in Scope

| Story                               | Points | Priority | Status     | Actual Time | Dependencies |
| ----------------------------------- | ------ | -------- | ---------- | ----------- | ------------ |
| Backend: Command Updates            | 2h     | High     | ✅ Done    | 2h          | None         |
| Service: Refactor for Temporal      | 2h     | High     | ✅ Done    | 2h          | Backend      |
| API: Schema & Route Updates         | 2h     | High     | ✅ Done    | 2h          | Service      |
| Frontend: Hook Implementation       | 3h     | High     | ✅ Done    | 3h          | API          |
| Tests: Backend Integration          | 2h     | High     | ✅ Done    | 2h          | API          |
| Tests: Frontend Unit                | 1h     | Medium   | ✅ Done    | 1h          | Frontend     |

**Total Estimated Effort:** 12 hours

---

## Success Criteria

- [x] Backend commands (Create/Update/SoftDelete) accept `control_date`. ✅
- [x] API endpoints accept `control_date` in body (Create/Update) or query (Delete). ✅
- [x] Frontend hooks (`useWBEs`, `useProjects`, `useCostElements`) inject `control_date` from `TimeMachineContext`. ✅
- [x] Integration tests verify correct bitemporal valid_time setting based on `control_date`. ✅
- [x] Frontend unit tests verify hook behavior. ✅

---

## Iteration Records

- **ANALYSIS:** [00-ANALYSIS.md](iterations/2026-01-10-control-date-crud/00-ANALYSIS.md)
- **PLAN:** [01-PLAN.md](iterations/2026-01-10-control-date-crud/01-PLAN.md)
- **DO:** [02-DO.md](iterations/2026-01-10-control-date-crud/02-DO.md)
- **CHECK:** [03-CHECK.md](iterations/2026-01-10-control-date-crud/03-CHECK.md)
- **ACT:** [04-ACT.md](iterations/2026-01-10-control-date-crud/04-ACT.md)

---

## Previous Iterations

- **[2026-01-10] Time Machine Production Hardening:** ✅ Complete (100%)
- **[2026-01-09] Time Machine Component:** ✅ Complete (100%)
- **[2026-01-09] Page-Level Adapters Refactoring:** ✅ Complete (100%)
