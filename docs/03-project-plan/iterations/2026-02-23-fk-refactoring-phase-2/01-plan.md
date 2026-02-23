# Plan: TD-067 FK Constraint Refactoring (Phase 2)

**Status**: [DRAFT]
**Date**: 2026-02-23
**Author**: Antigravity (AI Architect)
**Iteration**: 2026-02-23-fk-refactoring-phase-2

---

## 1. Scope & Success Criteria

### 1.1 Approved Approach Summary

**Selected Option:** Option 1 (Standard Application-Level Integrity)

We will refactor 8 entities to remove incorrect database Foreign Key constraints that reference non-unique root IDs in bitemporal tables. This aligns with the "Application-Level Integrity" pattern established in Phase 1 and ensures the system handles bitemporal versioning correctly without schema-level errors.

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Relationships (e.g., WBE -> Project, CostElement -> WBE) remain navigatable via root IDs. VERIFIED BY: Integration Tests
- [ ] Orphaned version rows can be queried if they correctly point to a root ID, regardless of the target's current version. VERIFIED BY: Bitemporal Query Tests
- [ ] Service layer validates parent existence during creation. VERIFIED BY: Service Tests

**Technical Criteria:**

- [ ] All 8 identified invalid DB FK constraints are REMOVED. VERIFIED BY: `backend/alembic/versions/` check
- [ ] Models updated to include descriptive comments about application-level integrity. VERIFIED BY: Code Audit
- [ ] MyPy strict mode and Ruff checks pass (no regressions). VERIFIED BY: `uv run ruff` and `uv run mypy`

**TDD Criteria:**

- [ ] Regression tests for entity navigation pass after FK removal.
- [ ] New tests for "bitemporal link stability" (similar to Phase 1) added for core entities (WBE, CostElement).

### 1.3 Scope Boundaries

**In Scope:**

- Removal of FK constraints for: `WBE`, `CostElement`, `Department`, `CostElementType`, `CostRegistration`, `ScheduleBaseline`, `ProgressEntry`.
- Database migration (ALEMBIC).
- SQLAlchemy model updates.
- Service layer validation updates for these entities.

**Out of Scope:**

- Refactoring entities NOT identified in the Phase 2 audit.
- Large-scale data migrations (unlike Phase 1, most of these already point to root IDs, just with invalid DB-level constraints).

---

## 2. Work Decomposition

### 2.1 Task Breakdown

| #   | Task                        | Files                                               | Dependencies | Success Criteria                                    | Complexity |
| :-- | :-------------------------- | :-------------------------------------------------- | :----------- | :-------------------------------------------------- | :--------- |
| 1   | **Create Regression Tests** | `tests/integration/test_td067_phase2_regression.py` | None         | Verify current functionality works with existing DB | Low        |
| 2   | **Database Migration**      | `backend/alembic/versions/XXXX_drop_invalid_fks.py` | Task 1       | Constraints dropped in DB                           | Medium     |
| 3   | **Model Refactoring**       | `backend/app/models/domain/*.py`                    | Task 2       | `ForeignKey` directives removed/updated             | Medium     |
| 4   | **Service Validation**      | `backend/app/services/*.py`                         | Task 3       | Explicit parent checks in `create()`                | Medium     |
| 5   | **Documentation**           | `docs/03-project-plan/iterations/.../04-act.md`     | Task 4       | Iteration closed and tech debt register updated     | Low        |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion          | Test ID | Test File                                     | Expected Behavior                                                          |
| :---------------------------- | :------ | :-------------------------------------------- | :------------------------------------------------------------------------- |
| WBE links to Project root     | T-001   | `tests/integration/test_wbe.py`               | Creating WBE with `project_id` works; updating Project doesn't break link. |
| CostElement links to WBE root | T-002   | `tests/integration/test_cost_element.py`      | Creating CostElement with `wbe_id` works.                                  |
| Parent validation in Service  | T-003   | `tests/unit/app/services/test_wbe_service.py` | Rejects non-existent `project_id`.                                         |

---

## 3. Test Specification

### 3.1 Test Hierarchy

```text
├── Integration Tests (tests/integration/)
│   └── test_td067_phase2_regression.py
│       ├── test_wbe_project_link_stability
│       ├── test_cost_element_wbe_link_stability
│       └── test_department_manager_link_stability
└── Unit Tests (tests/unit/app/services/)
    ├── test_wbe_service_validation
    └── test_cost_element_service_validation
```

### 3.2 Test Cases

| Test ID | Test Name                         | Criterion | Type | Expected Result                                                                                                                                     |
| :------ | :-------------------------------- | :-------- | :--- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-001   | `test_wbe_project_link_stability` | AC-1      | Int  | 1. Create Project.<br>2. Create WBE.<br>3. Update Project (creates new version).<br>4. Fetch WBE.<br>5. Assert WBE still linked to Project root ID. |
| T-003   | `test_wbe_service_validation`     | AC-3      | Unit | 1. Attempt to create WBE with random UUID for `project_id`.<br>2. Expect `EntityNotFoundError`.                                                     |

---

## 4. Risk Assessment

| Risk Type     | Description                                                  | Probability | Impact | Mitigation                                                                            |
| :------------ | :----------------------------------------------------------- | :---------- | :----- | :------------------------------------------------------------------------------------ |
| **Logic**     | Implicit ORM joins might fail without `ForeignKey` directive | Medium      | High   | Use `relationship(..., foreign_keys=[...])` and audit service layer for joined loads. |
| **Integrity** | Manual ID insertion via SQL could bypass validation          | Low         | Medium | Standardize use of Services for all writes.                                           |

---

## 5. Prerequisites & Dependencies

- [x] Analysis phase approved
- [ ] Local dev environment updated with latest migrations
