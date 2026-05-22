# Plan: Generalize QualityImpact to WorkPackage

**Created:** 2026-05-21
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Polymorphic Work Package Entity (STI)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Single Table Inheritance -- rename `QualityImpact` to `WorkPackage`, add `package_type` discriminator + `name` + `description` + `status` columns
- **Architecture**: One polymorphic `work_packages` table with closed enum types. Quality-specific columns remain as nullable native columns.
- **Key Decisions**:
  - Entity renamed to "Work Package" (PM-neutral, no ERP baggage)
  - Closed enum for `package_type`: `quality_impact`, `site_visit`, `production_phase`, `warranty_batch`, `commissioning`
  - Simple status lifecycle: `open` / `closed`
  - COQ metrics continue working via `WHERE package_type = 'quality_impact'` filter
  - EVCS Tier 2: Versionable, NOT branchable

### Success Criteria

**Functional Criteria:**

- [ ] All existing quality impact CRUD operations work under new WorkPackage naming VERIFIED BY: backend integration tests
- [ ] `package_type` enum validation rejects invalid types VERIFIED BY: unit test
- [ ] `status` field enforces open/closed lifecycle VERIFIED BY: unit test
- [ ] `name` field is required and non-empty on create VERIFIED BY: unit test
- [ ] COQ metrics (CPQ, QPI, COQ ratio) return identical results to pre-migration when filtering by `package_type = 'quality_impact'` VERIFIED BY: integration test
- [ ] Cost registrations link to work packages via `work_package_id` (renamed from `quality_impact_id`) VERIFIED BY: integration test
- [ ] Existing data migrates cleanly: all quality_impact rows become `package_type = 'quality_impact'`, `status = 'open'` VERIFIED BY: migration test
- [ ] RBAC permissions work with new `work-package-*` naming VERIFIED BY: route permission tests
- [ ] Frontend displays Work Packages tab with type filtering and status toggle VERIFIED BY: manual UI verification
- [ ] Frontend create/edit modal includes type selector with conditional quality-specific fields VERIFIED BY: manual UI verification

**Technical Criteria:**

- [ ] Alembic migration applies cleanly with zero data loss VERIFIED BY: migration upgrade/downgrade
- [ ] MyPy strict mode: zero errors on renamed code VERIFIED BY: `uv run mypy app/`
- [ ] Ruff: zero errors on renamed code VERIFIED BY: `uv run ruff check .`
- [ ] Backend test coverage >= 80% for work_package module VERIFIED BY: `uv run pytest --cov`
- [ ] API response times < 200ms p95 (same as before) VERIFIED BY: manual observation
- [ ] Indexes on `work_package_id`, `package_type`, `(project_id, package_type)` composite VERIFIED BY: migration inspection

**Business Criteria:**

- [ ] Quality impact costs continue to be tracked and reported identically VERIFIED BY: COQ summary comparison
- [ ] New work package types can be created and viewed in the UI VERIFIED BY: manual verification

### Scope Boundaries

**In Scope:**

- Alembic migration: rename table, rename FK column, add new columns, backfill data, update indexes
- Backend: rename model/service/schemas/routes, add enums, add validation, update COQ queries, update RBAC
- Frontend: rename feature module, generalize UI, add type selector, add status toggle
- Seed data: rename and add new fields
- Tests: update all existing tests, add new tests for type validation, status transitions, COQ filtering

**Out of Scope:**

- Budget/allocation per work package
- Auto-creation of cost registrations for non-quality types
- Work package hierarchy (parent-child)
- Settlement rules (SAP-style)
- Branch support for work packages (remains Tier 2)
- Type-specific custom fields beyond existing quality-specific columns
- ERP integration endpoints

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 1 | Alembic migration: rename table + FK, add columns, backfill data | `backend/alembic/versions/` (new migration) | None | Migration upgrades/downgrades cleanly; existing rows have `package_type='quality_impact'`, `status='open'`, generated `name`; new indexes created | High |
| 2 | Backend model: rename QualityImpact to WorkPackage, add new fields | `backend/app/models/domain/quality_impact.py` -> `work_package.py`, `backend/app/models/domain/cost_registration.py` | Task 1 | Model class `WorkPackage` with all fields; `quality_impact_id` column renamed to `work_package_id`; MyPy clean | Med |
| 3 | Backend enums: add WorkPackageType and WorkPackageStatus | `backend/app/core/enums.py` | None | Closed enum with 5 types; status enum with open/closed; importable by service and schemas | Low |
| 4 | Backend schemas: rename and extend Pydantic schemas | `backend/app/models/schemas/quality_impact.py` -> `work_package.py` | Task 3 | All schemas renamed; `name` required on Create; `package_type` validated against enum; `status` field with default | Med |
| 5 | Backend service: rename and add type/status logic | `backend/app/services/quality_impact_service.py` -> `work_package_service.py` | Tasks 2, 3, 4 | Service renamed; COQ queries filter by `package_type='quality_impact'`; status transitions validated; allocations still work | High |
| 6 | Backend routes: rename and update endpoints | `backend/app/api/routes/quality_impacts.py` -> `work_packages.py`, `backend/app/api/routes/__init__.py`, `backend/app/main.py` | Task 5 | All endpoints renamed; RBAC uses `work-package-*`; API prefix `/work-packages`; operation_ids updated | Med |
| 7 | Backend RBAC: rename permissions | `backend/app/core/enums.py`, `backend/seed/rbac_roles.json` | Task 6 | All `quality-impact-*` permissions renamed to `work-package-*` in both enums and seed data | Low |
| 8 | Backend reseed: update table name | `backend/app/db/reseed.py` | Task 1 | `"quality_impacts"` entry renamed to `"work_packages"` | Low |
| 9 | Seed data: rename and add new fields | `backend/seed/quality_impacts.json` -> `work_packages.json` | Task 1 | File renamed; all entries have `name`, `package_type='quality_impact'`, `status='open'` | Low |
| 10 | Backend tests: rename and extend test suite | `backend/tests/services/test_quality_impact_service.py` -> `test_work_package_service.py` | Tasks 5, 6, 7 | All existing tests renamed and pass; new tests for type validation, status transitions, COQ filtering with type filter | High |
| 11 | Frontend: rename feature module | `frontend/src/features/quality-impact/` -> `work-package/`, `frontend/src/api/queryKeys.ts`, `frontend/src/pages/projects/ProjectQualityImpacts.tsx`, `frontend/src/routes/index.tsx`, `frontend/src/pages/projects/ProjectLayout.tsx` | Task 6 | All files renamed/relocated; barrel exports updated; routes point to `/work-packages`; query keys use `work-packages` | Med |
| 12 | Frontend: generalize UI components | `frontend/src/features/work-package/components/` | Task 11 | Type selector dropdown; conditional quality fields when type=quality_impact; status toggle on list items; summary card filters by type | High |
| 13 | Quality gate: lint, typecheck, tests | Backend + Frontend | Tasks 1-12 | `ruff check`, `mypy`, `ruff format`, frontend `lint`, `typecheck` all pass; backend tests pass | Med |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| CRUD under new naming | T-001 | `test_work_package_service.py` | Create/read/update/delete work package returns correct data |
| package_type enum validation | T-002 | `test_work_package_service.py` | Invalid type raises ValueError |
| name field required | T-003 | `test_work_package_service.py` | Create without name fails validation |
| status field defaults to open | T-004 | `test_work_package_service.py` | New work package has status='open' |
| status can be closed | T-005 | `test_work_package_service.py` | Update status to 'closed' succeeds |
| COQ metrics filter by type | T-006 | `test_work_package_service.py` | COQ metrics only include quality_impact typed packages |
| COQ summary unchanged | T-007 | `test_work_package_service.py` | Summary data matches pre-migration values |
| Cost registration FK renamed | T-008 | `test_work_package_service.py` | CR links via work_package_id; allocations work |
| RBAC permissions renamed | T-009 | Route-level tests | work-package-read/create/update/delete enforced |
| Migration backfill | T-010 | Migration test | Existing rows get package_type, status, generated name |
| Type list filtering | T-011 | `test_work_package_service.py` | Filter by package_type returns only matching types |
| Non-quality package CRUD | T-012 | `test_work_package_service.py` | Create site_visit type; no quality-specific fields required |

---

## Test Specification

### Test Hierarchy

```text
tests/
  services/
    test_work_package_service.py        # Renamed from test_quality_impact_service.py
      - CRUD happy path (renamed)
      - package_type validation (NEW)
      - status lifecycle (NEW)
      - name validation (NEW)
      - COQ metrics with type filter (UPDATED)
      - COQ summary (UPDATED)
      - Allocation operations (renamed)
      - Non-quality type CRUD (NEW)
      - List filtering by type (NEW)
  api/
    routes/
      quality_events/                   # Existing, unchanged
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | `test_create_work_package_happy_path` | AC-1 | Unit | WorkPackage created with all fields; returns WorkPackageRead |
| T-002 | `test_create_work_package_invalid_type_raises` | AC-2 | Unit | ValueError raised when package_type not in enum |
| T-003 | `test_create_work_package_without_name_fails` | AC-3 | Unit | ValidationError on empty/missing name |
| T-004 | `test_create_work_package_default_status_open` | AC-4 | Unit | New package has status='open' without explicit setting |
| T-005 | `test_update_work_package_status_to_closed` | AC-5 | Unit | Status update to 'closed' succeeds; new version created |
| T-006 | `test_coq_metrics_filters_by_quality_type_only` | AC-6 | Unit | COQ metrics ignore site_visit/production_phase packages |
| T-007 | `test_coq_summary_identical_after_rename` | AC-7 | Integration | Summary matches expected values for quality-typed packages |
| T-008 | `test_cost_registration_links_via_work_package_id` | AC-8 | Unit | CR.work_package_id references work package; allocations query works |
| T-009 | `test_rbac_uses_work_package_permissions` | AC-9 | Unit | work-package-read/create/update/delete enforced on routes |
| T-010 | `test_migration_backfills_existing_quality_impacts` | AC-10 | Integration | Migrated rows have package_type='quality_impact', status='open', non-empty name |
| T-011 | `test_list_work_packages_filter_by_type` | AC-11 | Unit | Filtering by package_type returns correct subset |
| T-012 | `test_create_site_visit_type_no_quality_fields` | AC-12 | Unit | Create site_visit without coq_category/schedule_impact_days succeeds |

### Test Infrastructure Needs

- **Fixtures needed**: Existing `db_session`, `test_user`, `test_project` fixtures. New: `quality_impact_work_package` fixture (creates a quality-typed WP), `site_visit_work_package` fixture.
- **Database state**: Migration must be applied before any tests run. Seed data provides quality-impact-typed work packages.
- **Mocks/stubs**: No new mocks required; all tests use real database.

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  # --- LEVEL 0: Can start immediately (no dependencies) ---

  - id: BE-001
    name: "Create Alembic migration: rename table, rename FK, add columns, backfill data"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add WorkPackageType and WorkPackageStatus enums to core/enums.py"
    agent: pdca-backend-do-executor
    dependencies: []

  # --- LEVEL 1: Depends on migration and enums ---

  - id: BE-003
    name: "Rename model: QualityImpact -> WorkPackage with new fields"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-004
    name: "Rename and extend Pydantic schemas for WorkPackage"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  # --- LEVEL 2: Depends on model + schemas ---

  - id: BE-005
    name: "Rename service: QualityImpactService -> WorkPackageService with type/status logic"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004]

  # --- LEVEL 3: Depends on service ---

  - id: BE-006
    name: "Rename routes, update API prefix, update RBAC permissions"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]

  # --- LEVEL 3: Independent of routes, depends on migration ---

  - id: BE-007
    name: "Update seed data and reseed table name"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  # --- LEVEL 4: Backend tests depend on all backend code ---

  - id: BE-008
    name: "Update and extend backend test suite (CRUD, type validation, status, COQ filtering)"
    agent: pdca-backend-do-executor
    dependencies: [BE-006, BE-007]
    kind: test

  # --- LEVEL 2: Frontend can start once routes are defined (API contract) ---

  - id: FE-001
    name: "Rename frontend feature module, update routes, query keys, page wrappers"
    agent: pdca-frontend-do-executor
    dependencies: [BE-006]

  # --- LEVEL 3: UI components depend on renamed module ---

  - id: FE-002
    name: "Generalize UI: add type selector, conditional quality fields, status toggle"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  # --- LEVEL 5: Quality gate depends on everything ---

  - id: QA-001
    name: "Quality gate: ruff, mypy, format, frontend lint/typecheck, full test run"
    agent: pdca-backend-do-executor
    dependencies: [BE-008, FE-002]
    kind: test
```

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Migration | Data loss during table/column rename | Low | Critical | Feature not in production; rename is mechanical; test downgrade path |
| Migration | Index recreation failures on rename | Low | High | Explicitly drop old indexes and create new ones in migration |
| Technical | COQ metrics regression after adding type filter | Low | High | Dedicated test comparing COQ output before/after; type filter is additive |
| Technical | RBAC permission mismatch during rename | Medium | Medium | Rename permissions in both `enums.py` and `rbac_roles.json` simultaneously; reseed DB |
| Integration | Frontend API client mismatch after rename | Medium | Medium | Update query keys, types, and API hooks together; regenerate OpenAPI client |
| Integration | Stale imports after rename | Medium | Low | Use IDE "find all references" + grep to catch all occurrences; verified in QA-001 |
| Technical | Frontend generated types out of sync | Medium | Medium | Run `npm run generate-client` after backend routes are renamed |

---

## Verification Checklist (for CHECK phase)

- [ ] `alembic upgrade head` succeeds with no errors
- [ ] `alembic downgrade -1` succeeds (downgrade path works)
- [ ] All existing quality_impact rows migrated to work_packages with correct defaults
- [ ] `uv run ruff check .` -- zero errors
- [ ] `uv run ruff format .` -- zero changes
- [ ] `uv run mypy app/` -- zero errors
- [ ] `uv run pytest backend/tests/services/test_work_package_service.py` -- all pass
- [ ] COQ metrics test: values match expected for quality-typed packages
- [ ] Non-quality package CRUD test: create/read site_visit succeeds
- [ ] Type validation test: invalid package_type rejected
- [ ] Status test: open->closed transition works
- [ ] `npm run lint` -- zero errors
- [ ] `npm run typecheck` -- zero errors
- [ ] Frontend renders Work Packages tab with type filter
- [ ] Frontend create modal shows conditional quality fields

---

## Documentation References

### Required Reading

- Entity Classification Guide: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- Quality Impact Memory: `~/.claude/projects/-home-nicola-dev-backcast/memory/11-quality-impact-refactor.md`
- Analysis Document: `docs/03-project-plan/iterations/2026-05-21-project-orders-generalization/00-analysis.md`

### Code References

- Current model: `backend/app/models/domain/quality_impact.py`
- Current service: `backend/app/services/quality_impact_service.py`
- Current schemas: `backend/app/models/schemas/quality_impact.py`
- Current routes: `backend/app/api/routes/quality_impacts.py`
- Cost Registration FK: `backend/app/models/domain/cost_registration.py` (line 66-68)
- RBAC enums: `backend/app/core/enums.py` (lines 91-145)
- RBAC seed: `backend/seed/rbac_roles.json`
- Reseed table list: `backend/app/db/reseed.py` (line 35)
- Previous migration: `backend/alembic/versions/631a7bb0fe04_replace_quality_events_with_quality_.py`
- FK migration: `backend/alembic/versions/cc19af7150e4_add_quality_impact_id_to_cost_.py`
- Frontend feature: `frontend/src/features/quality-impact/`
- Frontend routes: `frontend/src/routes/index.tsx` (lines 36, 168-169)
- Frontend query keys: `frontend/src/api/queryKeys.ts` (lines 352-366)
- Frontend page wrapper: `frontend/src/pages/projects/ProjectQualityImpacts.tsx`
- Frontend layout nav: `frontend/src/pages/projects/ProjectLayout.tsx` (line 18)
- Seed data: `backend/seed/quality_impacts.json`
- Backend tests: `backend/tests/services/test_quality_impact_service.py`

---

## Prerequisites

### Technical

- [ ] PostgreSQL running and accessible
- [ ] Backend virtual environment activated with current dependencies
- [ ] Frontend dependencies installed (`npm install --legacy-peer-deps`)
- [ ] Current migrations applied (`alembic upgrade head`)

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed (EVCS entity classification, STI pattern)
- [x] Codebase surface area fully inventoried
