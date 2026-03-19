# PLAN Phase: TD-067 Coding Standards Update

**Date:** 2026-03-19
**Author:** AI Agent (PDCA Orchestrator)
**Iteration:** 2026-03-19-td-067-coding-standards-update
**Status:** DRAFT

---

## 1. Objective

Close out TD-067 by documenting the bitemporal FK pattern in backend coding standards and updating the technical debt register. The underlying bug was fixed in 2026-02-07, but the action items for documentation and audit completion were never addressed.

## 2. Background

TD-067 identified that `ChangeOrder.assigned_approver_id` incorrectly referenced `users.id` (version ID) instead of `users.user_id` (business key). This was fixed in iteration 2026-02-07-td-067-fk-business-keys, but:

1. The **coding standards** were never updated to document the correct pattern
2. The **technical debt register** was never updated to close the item
3. The **audit of all temporal entities** was never formally completed

### Code Audit Results (2026-03-19)

All temporal entities now follow the correct pattern:

| Entity | FK Pattern | Status |
|--------|-----------|--------|
| ChangeOrder | `ForeignKey("users.user_id")` | ✅ Correct |
| WBE | No FK (uses `project_id`, has explanatory comment) | ✅ Correct |
| CostElement | No FK (uses `wbe_id`, `cost_element_type_id`, has comments) | ✅ Correct |
| ScheduleBaseline | No FK (uses `project_id`, has explanatory comment) | ✅ Correct |
| CostRegistration | No FK (uses `project_id`, `wbe_id`, has comment) | ✅ Correct |
| ProgressEntry | No FK (uses `wbe_id`, has explanatory comment) | ✅ Correct |
| Branch | No FK (uses `project_id`, has explanatory comment) | ✅ Correct |
| User | No FKs (root entity for users) | ✅ N/A |
| Project, Department, Forecast, etc. | No FKs to other temporal entities | ✅ Correct |
| AI entities | SimpleEntityBase (non-versioned) | ✅ Correct |

## 3. Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-1 | Coding standards document bitemporal FK pattern | `docs/02-architecture/backend/coding-standards.md` updated |
| SC-2 | TD-067 marked as resolved in register | `docs/03-project-plan/technical-debt-register.md` updated |
| SC-3 | Audit formally documented | This PLAN phase serves as audit record |

## 4. Implementation Plan

### Task 1: Update Coding Standards

**File:** `docs/02-architecture/backend/coding-standards.md`

**Add section:**
```markdown
## Foreign Key Constraints for Temporal Entities

**Pattern:** Temporal entities (using `VersionableMixin`) should NOT use database-level FK constraints to other temporal entities' root IDs (e.g., `project_id`, `user_id`, `wbe_id`).

**Rationale:**
- Root IDs are NOT UNIQUE in bitemporal tables (multiple versions share the same root ID)
- PostgreSQL FK constraints require UNIQUE target columns
- Referential integrity is enforced at the application/service layer

**Implementation:**
- Use explicit comments: `# NOTE: No database-level ForeignKey constraint because [field] is a root ID`
- Service layer validates existence before setting FK fields
```

### Task 2: Update Technical Debt Register

**File:** `docs/03-project-plan/technical-debt-register.md`

**Action:** Move TD-067 to archive with completion note:
- Source: Change Order Workflow Recovery (2026-02-06)
- Fixed: 2026-02-07 (iteration 2026-02-07-td-067-fk-business-keys)
- Audit completed: 2026-03-19
- Coding standards updated: 2026-03-19

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| None identified | N/A | N/A | N/A |

## 6. Estimate

| Task | Estimate |
|------|----------|
| Update coding standards | 15 minutes |
| Update TD register | 10 minutes |
| **Total** | **25 minutes** |

---

**Ready for DO phase:** ✅ Yes (documentation-only changes)
