# Architecture Documentation Audit Report

**Analysis Date:** 2026-04-11
**Analyst:** Claude (Architecture Analyst)
**Scope:** `docs/02-architecture/` — 65 files, ~820KB total

---

## Executive Summary

The architecture documentation is generally well-organized with strong cross-referencing and a clear ADR process. However, the audit identifies **9 concrete issues** (4 resolved as of 2026-04-11): one factual conflict, three significant overlap areas, two incomplete/outdated references, and three minor ambiguities.

The most urgent issue is ADR-009 being marked "Rejected" while fully implemented and in production.

---

## 1. Findings by Severity

### HIGH — Factual Conflict

#### 1.1 ADR-009 Status vs. Reality

**File:** `decisions/ADR-009-schedule-baseline-1to1-relationship.md`
**Also affected:** `decisions/adr-index.md`

ADR-009 is marked **"Rejected"** in its status field and in the ADR index. However, the document itself contains a detailed "Completed Implementation (2026-01-18)" section showing:

- Full database migration executed
- Service layer, API layer, and frontend changes shipped
- 39/41 tests passing (95.1%), ~95% coverage
- Ruff linting clean

The 1:1 schedule baseline relationship is **in production**. Anyone reading the ADR index would conclude the inversion was never done, which is incorrect.

**Recommendation:** Update ADR-009 status to `Accepted` (or `Superseded` if a follow-up ADR exists). Add a note explaining the initial rejection and subsequent implementation. Update `adr-index.md` accordingly.

---

### MEDIUM — Overlaps

#### 1.2 Widget/Dashboard Documentation Sprawl (6 files) ~~RESOLVED~~

~~Six files cover closely related widget/dashboard topics~~:

| File | Size | Focus |
|------|------|-------|
| ~~`widget-dashboard-guide.md`~~ | ~~36K~~ | ~~Merged into developer guide~~ |
| `widget-lifecycle-walkthrough.md` | 32K | Lifecycle walkthrough |
| `how-to-create-a-widget.md` | 25K | Developer how-to |
| `dashboard-developer-guide.md` | 43K | **Unified developer guide** (merged) |
| `dashboard-user-guide.md` | 22K | User guide (kept separate) |

**Resolution (2026-04-11):** Merged `widget-dashboard-guide.md` into `dashboard-developer-guide.md` as a single comprehensive developer guide. The merged document is organized into five parts: Backend, Frontend Architecture, Runtime Behavior, Advanced Features, and Reference. `dashboard-user-guide.md` remains separate for end-user documentation.

#### 1.3 EVCS Temporal Coverage Spread Across 4 Documents (82KB) ~~RESOLVED~~

The bitemporal versioning topic is covered by:

| File | Size | Role |
|------|------|------|
| `backend/contexts/evcs-core/architecture.md` | 38K | Conceptual architecture (no code) |
| `backend/contexts/evcs-core/evcs-implementation-guide.md` | 14K | Code patterns and service usage |
| `cross-cutting/temporal-query-reference.md` | 19K | Query semantics and filter behavior |
| `decisions/ADR-005-bitemporal-versioning.md` | 11K | Decision record |

**Resolution (2026-04-11):** Clarified the scope boundaries:
- `architecture.md` → conceptual model, entity types, protocols (removed detailed code)
- `evcs-implementation-guide.md` → code patterns, service usage, examples (added branch query patterns)
- `temporal-query-reference.md` → query semantics and filter behavior only (removed code-heavy sections)
- `ADR-005` → decision rationale (already clean)

Each document now has a clear scope note explaining what it covers and what it doesn't, with links to the appropriate related documents.

#### 1.4 EVM Temporal vs. General Temporal Overlap

`evm-time-travel-semantics.md` (15K) covers EVM-specific temporal behavior, but overlaps with:

- `cross-cutting/temporal-query-reference.md` (19K) — general temporal queries
- `backend/contexts/evcs-core/architecture.md` — time-travel query patterns

The boundary between "EVM temporal" and "general temporal" is not clearly defined. Readers may not know which document to consult for time-travel behavior in EVM contexts.

**Recommendation:** `evm-time-travel-semantics.md` should focus exclusively on EVM-specific semantics (control_date, PV recalculation, metric snapshots) and link to `temporal-query-reference.md` for the underlying query mechanics.

---

### MEDIUM — Incomplete/Outdated

#### 1.5 README.md Doesn't Reflect Actual Structure

**File:** `docs/02-architecture/README.md`

The folder structure section is incomplete:

- Widget files (`widget-*.md`, `how-to-create-a-widget.md`) not listed
- Dashboard files (`dashboard-*.md`) not listed
- `ai-chat-developer-guide.md` at root not shown
- `cross-cutting/api-response-patterns.md` not listed
- `code-review-checklist.md`, `error-codes.md`, `configuration.md` listed as "Reference" but not in folder tree
- `testing-patterns.md` at root overlaps with `testing/` directory

The ADR table lists only 7 of 13 ADRs. ADR-009 through ADR-013 (including schedule baseline, query key factory, EVM metrics, time-series, computed budget) are missing.

**Recommendation:** Update the folder structure diagram and ADR table to reflect current state. Add widget/dashboard and AI sections.

---

### LOW — Ambiguities

#### 1.6 ADR-007 Cross-Reference to Non-Existent RBAC ADR

**File:** `decisions/ADR-007-rbac-service.md`

ADR-007 mentions "Database-backed RBAC" as a future consideration. ADR-008 was referenced as if it might cover this, but ADR-008 is actually about "Server-Side Filtering, Search, and Sorting." The future RBAC ADR has never been created, and the reference creates confusion.

**Recommendation:** Either remove the forward reference or add a note that database-backed RBAC remains an open consideration with no ADR.

#### 1.7 ADR-002 Gap Unexplained ~~RESOLVED~~

The ADR sequence jumps from ADR-001 to ADR-003. The `adr-index.md` states "Gaps okay if ADRs deleted before acceptance" but did not explain what ADR-002 was about. This made decision history harder to trace.

**Resolution (2026-04-11):** Added a "Gaps" section to `adr-index.md` documenting that ADR-002 was "Entity Versioning Pattern (Composite Primary Key with head/version tables)" which was superseded by ADR-005 "Bitemporal Versioning" on 2026-01-01.

#### 1.8 API Pattern Boundary Unclear (3 documents) ~~RESOLVED~~

~~Three documents cover API patterns:~~

| File | Size | Focus |
|------|------|-------|
| `cross-cutting/api-conventions.md` | 12K | **Protocol-level patterns** (REST, context params, auth) |
| `cross-cutting/api-response-patterns.md` | 14K | **Implementation patterns** (filtering, pagination, frontend integration) |
| `api-endpoints.md` | 8.1K | **Quick reference catalog** (companion to live OpenAPI docs) |

~~The boundary between "conventions" and "response patterns" is not self-evident from the file names. Additionally, `api-endpoints.md` as a static endpoint list will drift from the actual codebase over time.~~

**Resolution (2026-04-11):** Added scope notes at the top of each file:
- `api-conventions.md` → Authoritative reference for protocol-level API patterns (REST, HTTP methods, context parameters, status codes, authentication)
- `api-response-patterns.md` → Implementation patterns for server-side filtering/search/sort (response formats, FilterParser usage, frontend/backend integration)
- `api-endpoints.md` → Quick reference catalog, positioned as a companion to the live OpenAPI docs at `/docs` (provides browsable index without running backend, plus domain-specific notes not in auto-generated specs)

Each scope note includes cross-references to the other two documents and clarifies when to use each.

#### 1.9 Automated Filter Types Migration — Stale ~~RESOLVED~~

**File:** `cross-cutting/automated-filter-types-migration.md`

Marked "Proposed / Future" with no clear timeline or active status. Related to TD-014 but it's unclear whether this is actively planned or abandoned.

**Resolution (2026-04-11):** Created PDCA analysis at `docs/03-project-plan/iterations/2026-04-11-automated-filter-types/00-analysis.md`. The feature is NOT implemented — filter types remain manually synchronized between backend and frontend. Analysis recommends Option 1 (OpenAPI Extension + Post-Processing) with 3-day implementation effort. Awaiting decision on whether to proceed to PLAN phase or defer.

---

## 2. Document Inventory

### 2.1 Files by Area

| Area | Files | Total Size |
|------|-------|------------|
| EVCS Core (backend) | 4 | ~78K |
| ADRs | 13 | ~85K |
| AI/Chat | 7 | ~167K |
| EVM | 6 | ~67K |
| Widget/Dashboard | 4 | ~122K |
| Cross-Cutting | 6 | ~61K |
| Frontend Contexts | 7 | ~30K |
| Backend (non-EVCS) | 3 | ~21K |
| Testing | 3 | ~27K |
| Reference | 6 | ~40K |
| Root (system map, bounded contexts) | 2 | ~26K |
| Archive | 3 | ~50K |

### 2.2 ADR Status Summary

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-001 | Technology Stack | Accepted | 2025-12-27 |
| ADR-003 | Command Pattern | Accepted | 2025-12-28 |
| ADR-004 | Quality Standards | Accepted | 2025-12-27 |
| ADR-005 | Bitemporal Versioning | Accepted | 2026-01-01 |
| ADR-006 | Protocol-Based Type System | Accepted | 2026-01-02 |
| ADR-007 | RBAC Service | Accepted | 2026-01-04 |
| ADR-008 | Server-Side Filtering | Accepted | 2026-01-08 |
| ADR-009 | Schedule Baseline 1:1 | **Rejected (conflict — implemented)** | 2026-01-18 |
| ADR-010 | Query Key Factory | Accepted | 2026-01-19 |
| ADR-011 | Generic EVM Metric System | Accepted | 2026-01-22 |
| ADR-012 | EVM Time-Series Data | Accepted | 2026-01-22 |
| ADR-013 | Computed Budget Attribute | Accepted | 2026-02-28 |

---

## 3. Recommended Actions

| Priority | Action | Effort | Status |
|----------|--------|--------|--------|
| 1 | Fix ADR-009 status from "Rejected" to "Accepted" | 5 min | Pending |
| 2 | Update README.md folder structure and ADR table | 30 min | Pending |
| ~~3~~ | ~~Audit overlap between `widget-dashboard-guide.md` and `dashboard-developer-guide.md`~~ | ~~1 hr~~ | **Done** |
| ~~4~~ | ~~Clarify scope boundaries in EVCS temporal docs (4 files)~~ | ~~1 hr~~ | **Done** |
| 5 | Clarify EVM temporal vs. general temporal boundary | 30 min | Pending |
| ~~6~~ | ~~Add ADR-002 gap note to `adr-index.md`~~ | ~~5 min~~ | **Done** |
| 7 | Clarify or remove ADR-007 forward reference to DB-backed RBAC | 10 min | Pending |
| 8 | Decide fate of `automated-filter-types-migration.md` | 10 min | **Done** — PDCA analysis created, awaiting decision |
| ~~9~~ | ~~Add scope notes to API pattern docs~~ | ~~15 min~~ | **Done** |
