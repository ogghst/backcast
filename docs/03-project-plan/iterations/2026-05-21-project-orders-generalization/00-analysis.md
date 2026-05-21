# Analysis: Generalize Quality Impact ID to Project-Level Work Packages

**Created:** 2026-05-21
**Updated:** 2026-05-21 (enriched with ERP research, user decisions recorded)
**Request:** Evolve the `quality_impact_id` on `CostRegistration` into a generic **work package** concept at the project level, inspired by SAP internal orders / service orders, so cost registrations can be grouped under packages of various types -- not only quality impacts.

---

## User Decisions (Recorded 2026-05-21)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Entity name** | **Work Package** | PM-neutral term, groups costs by scope/activity. Avoids ERP "order" connotations and confusion with Backcast change orders. |
| **Type enum** | **Closed** | Predefined types via enum + migration. Keeps column count manageable, type-safe. Aligns with GitLab's STI guidance. |
| **Status lifecycle** | **Simple: open/closed** | Two states. Open = costs can be posted. Closed = read-only. Sufficient for Backcast's needs without SAP-level complexity. |
| **COQ metrics** | **Keep quality-specific** | Existing COQ endpoint stays as-is, filtering work packages by type=quality_impact. No scope creep. |

---

## Clarified Requirements

### Functional Requirements

- A "work package" is a project-scoped grouping mechanism for cost registrations, analogous to SAP internal orders / service orders.
- Quality impacts become one *type* of work package, not the only use case.
- Work packages can represent: site visits, production phases, warranty claim batches, quality impacts, commissioning phases, or any other logical cost grouping the project manager needs.
- Each cost registration may optionally be linked to exactly one work package (nullable FK).
- Work packages carry enough metadata to be useful (name, type/category, dates, description, status) but do NOT carry domain-specific fields like `coq_category` or `schedule_impact_days` -- those remain as nullable columns populated only for quality-typed packages.
- The existing COQ metrics pipeline (CPQ, QPI, COQ ratio) must continue to work for quality-typed work packages.
- Work packages are versionable (Tier 2 EVCS), not branchable -- they are financial facts that span branches.

### Non-Functional Requirements

- Maintain EVCS versionable pattern (work packages are temporal facts, not branchable).
- Preserve existing RBAC permission structure, generalizing `quality-impact-*` to `work-package-*`.
- Migration must handle existing `quality_impact_id` data without data loss.
- API response times within existing targets (<200ms p95).

### Constraints

- Quality impact feature is freshly refactored (2026-05-20) and not yet in production -- the rename surface is known and contained.
- Cost registrations are versionable (not branchable); the work package reference on CR must remain compatible with temporal queries.
- Work packages must be project-scoped, not global.
- The COQ/quality metrics domain is well-defined and must not regress.
- Closed type enum: adding new types requires a migration (intentional, keeps schema clean).

---

## ERP Research: Best Practices & Industry Patterns

### SAP Internal Orders (Reference Architecture)

SAP's internal order system is the primary industry reference for cost grouping in project environments.

**Standard SAP Order Types (KOT2):**

| SAP Type | Purpose | Settlement Target |
|----------|---------|-------------------|
| Overhead Order (K01) | Track overhead costs (events, admin) | Cost centers |
| Investment Order | Capital expenditure projects | Fixed assets (via AuC) |
| Order with Revenue | Both cost and revenue postings | Profitability segments |
| Accrual Order | Periodic accrued cost calculation | Cost centers |
| Statistical Order | Reporting only; no settlement | N/A |

**SAP Status Lifecycle:**

```
CRTD (Created) → REL (Released) → TECO (Technically Complete) → CLSD (Closed)
```

Key SAP behaviors:
- **REL**: Costs can be posted, goods issued, confirmations allowed.
- **TECO**: Operational work done. Goods issues blocked, but **financial postings still allowed** (corrections, accruals, settlement).
- **CLSD**: Fully closed. No processing of any kind.
- Settlement via KO88 (single order) or KO8G (collective) transfers costs to receivers.

**Backcast adaptation:** We adopt a simplified 2-state lifecycle (open/closed) instead of SAP's 4 stages. The TECO concept (block operational postings but allow financial corrections) adds complexity that Backcast's users don't need yet. If needed later, the `status` enum can be extended via migration.

### Naming Research

| Term | ERP Context | Suitability for Backcast |
|------|-------------|--------------------------|
| Internal Order | SAP CO module standard | Confusing alongside Backcast "change orders" |
| Cost Order | Generic cost collector | Clear but "order" may confuse with sales/purchase orders |
| Work Order | Physical task execution (BOM, routing) | Implies production scheduling, not just cost grouping |
| Service Order | Customer-facing service delivery | Implies SLA/billing, not internal cost tracking |
| **Work Package** | **Project management standard** | **Groups costs by scope/activity, PM-neutral, no ERP baggage** |
| Cost Batch | Lightweight grouping | Too informal for financial tracking |

**Sources:** SAP Community, ERP Corp, Oracle Project Cost Collector docs, Microsoft Dynamics GP Project Accounting.

### Database Inheritance Patterns

Three patterns for polymorphic entities (Martin Fowler, PEAA):

| Pattern | Structure | Pros | Cons |
|---------|-----------|------|------|
| **Single Table Inheritance (STI)** | One table, type discriminator, nullable columns | Fastest reads (no JOINs), simple queries | Sparse columns, lock contention, schema coupling |
| **Class Table Inheritance (CTI)** | Base table + subtype tables with FK | Normalized, clean schemas | JOINs per query, dual writes, complex versioning |
| **Concrete Table** | One table per subtype, no shared table | No JOINs, no NULLs | No cross-type queries without UNION |

**Industry guidance:**
- **SQLAlchemy docs**: *"Single table inheritance has the advantage of simplicity; queries are much more efficient as only one table needs to be involved."*
- **GitLab**: *"Don't design new tables using Single Table Inheritance (STI). Use separate tables instead."* -- GitLab's reasoning centers on scale (sparse tables, locking contention at their volume).
- **Hybrid approach**: Common fields in a single base table, type-specific fields in separate tables with FK references.

**Decision for Backcast:** STI (single polymorphic table) is the right choice here because:
1. Only 3-4 quality-specific nullable columns -- well within acceptable sparsity.
2. EVCS versioning already adds complexity; CTI JOINs on top of temporal queries would compound this.
3. Backcast is not at GitLab's scale; lock contention is not a concern.
4. Closed enum keeps the type set small and known, so the sparse column set is bounded.

---

## Context Discovery

### Product Scope

- **Section 9** of functional-requirements.md defines "Quality Event Management" -- recording quality events, tracking their costs, and measuring impact on EVM metrics. There is no mention of a general "work package" concept.
- **Section 6.2** covers cost registration and actual cost tracking. Cost registrations capture date, amount, category, invoice reference, and notes. No grouping mechanism is specified beyond the cost element.
- **Section 18.2** lists ERP integration as a future enhancement. Service orders / internal orders are a natural integration point with SAP/ERP systems.
- **Glossary** has no entry for "work package" or "order" in the domain sense.

### Architecture Context

**Bounded contexts involved:**
- EVCS Core (versioning framework)
- Cost Management (cost registrations, budget tracking)
- Quality Management (quality impacts, COQ metrics) -- would be absorbed/subsumed into work packages

**Current entity tiers:**
- `QualityImpact`: EntityBase + VersionableMixin (Tier 2 -- versionable, not branchable)
- `CostRegistration`: EntityBase + VersionableMixin (Tier 2)
- The proposed `WorkPackage` entity would also be Tier 2 (versionable, not branchable) -- work packages are global financial facts across branches.

**Key architectural fact:** `CostRegistration.quality_impact_id` is a nullable UUID column with an index, no FK constraint (standard EVCS pattern -- root ID reference, application-enforced integrity). The same pattern would apply to a generalized `work_package_id`.

### Codebase Analysis

**Backend files that reference `quality_impact_id`:**
- `backend/app/models/domain/cost_registration.py` -- column definition
- `backend/app/services/quality_impact_service.py` -- 40+ references (allocations, COQ metrics, cost aggregation)
- `backend/app/models/domain/quality_impact.py` -- the entity itself
- `backend/app/models/schemas/quality_impact.py` -- Pydantic schemas
- `backend/app/api/routes/quality_impacts.py` -- API routes
- `backend/tests/services/test_quality_impact_service.py` -- tests
- `backend/alembic/versions/cc19af7150e4_add_quality_impact_id_to_cost_.py` -- migration

**Frontend files that reference `quality_impact_id`:**
- `frontend/src/features/quality-impact/` -- entire feature module (6 files)
- `frontend/src/pages/projects/ProjectQualityImpacts.tsx` -- page wrapper
- `frontend/src/routes/index.tsx` -- route registration
- `frontend/src/api/queryKeys.ts` -- query key factory

**Cost registration service:** `cost_registration_service.py` does NOT reference `quality_impact_id` directly. The link is managed entirely from the quality impact service side (it creates/queries CRs filtered by `quality_impact_id`).

---

## Solution: Polymorphic Work Package Entity (STI)

### Architecture & Design

Rename `QualityImpact` to `WorkPackage`. The WorkPackage entity becomes the single table for all work package types, with a `package_type` discriminator column (closed enum). Quality-specific fields (`coq_category`, `schedule_impact_days`, `external_event_id`) become optional columns populated only when `package_type = "quality_impact"`.

The `quality_impact_id` column on `cost_registrations` is renamed to `work_package_id`.

### Data Model

```
work_packages (renamed from quality_impacts)
  - work_package_id: UUID (root ID, renamed from quality_impact_id)
  - project_id: UUID
  - name: str (NEW -- human-readable label, required)
  - package_type: str (NEW -- closed enum: "quality_impact", "site_visit", "production_phase", "warranty_batch", "commissioning")
  - description: str | None (NEW)
  - status: str (NEW -- enum: "open", "closed")
  - external_event_id: str | None (quality-specific, nullable)
  - event_date: datetime | None (kept)
  - coq_category: str | None (quality-specific, nullable)
  - cost_impact: Decimal (kept -- declared/estimated cost for the package)
  - schedule_impact_days: int | None (quality-specific, nullable)
  + temporal fields from VersionableMixin
```

**Key design choices:**
- `name` is required -- every work package needs a human-readable label (unlike quality impacts which were more system-driven).
- `package_type` uses a closed enum. New types require a migration. This is intentional to keep the nullable column set bounded.
- `status` is open/closed only. Can be extended later via migration if TECO-style states are needed.
- Quality-specific columns (`coq_category`, `schedule_impact_days`, `external_event_id`) remain as nullable native columns. For the known 5 package types, only 3 extra nullable columns -- well within acceptable sparsity.

### UX Design

- Project-level "Work Packages" tab replaces "Quality Impacts" tab.
- Work package list has a `package_type` filter (chips/tabs for each type).
- Create/edit modal includes a type selector that conditionally shows quality-specific fields.
- Quality-specific COQ summary card appears when filtering by quality packages.
- Status toggle (open/closed) on each package row.

### Implementation Scope

**Database (Alembic migration):**
- Rename table `quality_impacts` → `work_packages`
- Rename column `quality_impact_id` → `work_package_id` (root ID)
- Rename column `quality_impact_id` → `work_package_id` on `cost_registrations`
- Add columns: `name` (varchar, not null), `package_type` (varchar, not null), `description` (text, nullable), `status` (varchar, default 'open')
- Backfill: `name` from existing description or generated, `package_type` = 'quality_impact', `status` = 'open'
- Update indexes: replace `quality_impact_id` indexes with `work_package_id` indexes

**Backend:**
- Rename model `QualityImpact` → `WorkPackage`
- Rename service `QualityImpactService` → `WorkPackageService`
- Rename schemas, routes, tests
- Add `WorkPackageType` enum (closed)
- Add `WorkPackageStatus` enum (open/closed)
- Add `name` field validation (required, non-empty)
- Add `package_type` field validation (enum member)
- COQ metrics queries: add `WHERE package_type = 'quality_impact'` filter
- RBAC: rename `quality-impact-*` permissions to `work-package-*`

**Frontend:**
- Rename feature module from `quality-impact` to `work-package`
- Generalize UI components: type selector, conditional quality fields
- Add status toggle to package list
- Keep COQ metrics card, filter by type

**Seed data:**
- Update `quality_impacts.json` → `work_packages.json`
- Add `name`, `package_type`, `status` fields to seed data

### Trade-offs

| Aspect          | Assessment |
|-----------------|------------|
| Sparse columns  | Acceptable -- only 3 quality-specific nullable columns for 5 package types. GitLab's STI avoidance is for tables with 20+ sparse columns at massive scale. |
| Performance     | Best of the 3 options -- single table, native columns, standard indexes. COQ queries add one simple `WHERE package_type = 'quality_impact'` filter. |
| Maintainability  | Good -- one entity, one service, one API. EVCS versioning applied once. |
| Extensibility   | Adding a new package type = migration to add nullable columns if needed + enum update. Contained, reviewable change. |
| Migration risk   | Low -- rename is mechanical. Feature not in production. |

### What This Does NOT Include (Out of Scope)

- **Budget/allocation per work package:** Work packages group existing cost registrations. They don't carry their own budget or allocation breakdown (unlike SAP settlement rules).
- **Auto-creation of cost registrations:** Non-quality work packages simply group existing CRs. Only quality-typed packages may continue the current allocation/breakdown pattern.
- **Work package hierarchy:** No parent-child relationships between work packages. Each package is flat within a project.
- **Settlement rules:** No SAP-style settlement (KO88/KO8G). Work packages track costs, they don't redistribute them.

---

## Recommendations from Research

1. **Keep quality-specific fields as nullable columns, not JSONB.** Native columns with standard indexes outperform JSONB for the COQ metrics pipeline. For a closed set of ~5 types with 3 quality-specific fields, the sparsity is negligible.

2. **Use `package_type` not `type` as the discriminator column name.** Avoids SQL reserved word issues and is more descriptive.

3. **Consider future ERP integration.** The work package entity maps naturally to SAP internal orders. The `external_event_id` field (renamed to something more generic if needed) could later reference an SAP order number for integration.

4. **Index strategy:** Add a partial index on `work_packages` WHERE `package_type = 'quality_impact'` for COQ query performance. Add a composite index on `(project_id, package_type)` for filtered list queries.

---

## References

### Codebase
- Entity Classification Guide: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- Quality Impact Domain Model: `backend/app/models/domain/quality_impact.py`
- Quality Impact Service: `backend/app/services/quality_impact_service.py`
- Quality Impact Schemas: `backend/app/models/schemas/quality_impact.py`
- Quality Impact Routes: `backend/app/api/routes/quality_impacts.py`
- Cost Registration Model: `backend/app/models/domain/cost_registration.py`
- Migration cc19af7150e4: `backend/alembic/versions/cc19af7150e4_add_quality_impact_id_to_cost_.py`
- Frontend Quality Impact Feature: `frontend/src/features/quality-impact/`

### Product Scope
- Product Vision: `docs/01-product-scope/vision.md`
- Functional Requirements (Section 6.2, 9): `docs/01-product-scope/functional-requirements.md`
- EVM Requirements (Section 10): `docs/01-product-scope/evm-requirements.md`
- Glossary: `docs/01-product-scope/glossary.md`
- Memory: `11-quality-impact-refactor.md`

### External Research
- [SAP Help Portal - Internal Orders (CO-OM-OPA)](https://help.sap.com/docs/SUPPORT_CONTENT/ficontrolling/3361881778.html)
- [SAP Help Portal - Order Types](https://help.sap.com/docs/SUPPORT_CONTENT/ficontrolling/3361878388.html)
- [ERP Corp - What is an SAP Internal Order](https://erpcorp.com/sap-controlling-blog/sap-planning/what-is-an-sap-internal-order)
- [SQLAlchemy ORM Inheritance Documentation](http://docs.sqlalchemy.org/en/latest/orm/inheritance.html)
- [GitLab Docs - Single Table Inheritance (avoid)](https://docs.gitlab.com/development/database/single_table_inheritance/)
- [Medium - Table Inheritance Patterns Comparison](https://medium.com/@artemkhrenov/table-inheritance-patterns-single-table-vs-class-table-vs-concrete-table-inheritance-1aec1d978de1)
