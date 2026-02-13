# Table Harmonization - Phase 2: Server-Side Implementation

**Iteration:** 2026-01-08-table-harmonization-phase2  
**Status:** 📋 Planning  
**Created:** 2026-01-08

---

## Overview

Phase 2 migrates the **three-level filtering system** from client-side to server-side for Projects, WBEs, and Cost Elements, enabling:

- **Global search** across entire datasets (not just current page)
- **Scalable filtering** for datasets > 1000 records
- **Zero UX regression** - identical user experience as Phase 1

---

## Phase 1 Recap

Phase 1 (completed) implemented client-side filtering with:

- ✅ Global search input (toolbar)
- ✅ Per-column text filters (text columns)
- ✅ Categorical filters (dropdown checkboxes)
- ✅ Column sorting (all columns)
- ✅ URL state synchronization

**Limitation:** Search was per-page only (not global across dataset).

---

## Phase 2 Goals

### Primary Objective

Enable **global search** and **server-side filtering** for:

1. Projects
2. WBEs
3. Cost Elements

### Success Criteria

- ✅ Global search works across entire dataset
- ✅ All Phase 1 filters work server-side
- ✅ **Identical UX** to Phase 1 (zero regression)
- ✅ Backend response time < 200ms (p95) with 10,000 records

---

## Documents

| Document         | Purpose                                                  | Status      |
| ---------------- | -------------------------------------------------------- | ----------- |
| `00-analysis.md` | Problem analysis, technical options, architecture design | ✅ Complete |
| `01-plan.md`     | Detailed task breakdown, timeline, testing strategy      | ✅ Complete |
| `02-do.md`       | Implementation log (created during execution)            | ⏭️ Pending  |
| `02-check.md`    | Verification results, findings, metrics                  | ⏭️ Pending  |
| `03-act.md`      | Retrospective, improvements, next steps                  | ⏭️ Pending  |

---

## Key Technical Decisions

### Filter Format (Unchanged)

**URL Format:**

```
?search=alpha&filters=status:active;branch:main,dev&sort_field=name&sort_order=asc
```

**Backend Parsing:**

- Input: `"status:active;branch:main,dev"`
- Output: `WHERE status = 'active' AND branch IN ('main', 'dev')`

### Architecture

- **Backend:** Generic `FilterParser` class converts URL format to SQLAlchemy filters
- **Frontend:** No changes to UX; TanStack Query passes params to backend
- **Migration:** Projects, WBEs, Cost Elements → server-side; Users, Departments → remain client-side

---

## Timeline

**Estimated Duration:** 4-5 days

| Phase    | Tasks                           | Duration   |
| -------- | ------------------------------- | ---------- |
| Backend  | Filter parser + service updates | 2 days     |
| Frontend | Remove client-side logic        | 1 day      |
| Testing  | Unit + E2E + performance        | 1-1.5 days |
| Docs     | Architecture + API docs         | 0.5 days   |

---

## Next Steps

1. ✅ Review and approve `00-analysis.md`
2. ✅ Review and approve `01-plan.md`
3. ⏭️ Begin implementation (create `02-do.md`)
4. ⏭️ Execute tasks per plan
5. ⏭️ Verify with CHECK phase
6. ⏭️ Complete with ACT phase

---

## Related Documents

- **Phase 1:** `../00-analysis.md`, `../01-plan.md`, `../02-check.md`, `../03-act.md`
- **Amendment:** `../00-amendment-per-column-filters.md`
- **Coding Standards:** `docs/02-architecture/coding-standards.md`
- **Sprint Backlog:** `docs/03-project-plan/sprint-backlog.md`

---

**Last Updated:** 2026-01-08
