# Functional Dashboards — Analysis: From Project-Scoped EVM to a Portfolio & Functional Reporting Layer

**Iteration:** 2026-06-28-functional-dashboards
**Status:** ANALYSIS ONLY (research + gap analysis). No code changes. Every gap below is an **open question for product owners** (implement vs. defer), not a commitment or a plan.
**Author method:** Codebase capability mapping (first-hand + Explore agents) → industry best-practices research (web, per role) → per-role gap analysis → **adversarial verification of every gap claim against the actual code** → synthesis.

---

## Document Status

This document is a **product/functional analysis**, not an implementation plan. It exists to answer one question:

> *Backcast is strong at the project level but has no functional (role-based, cross-project) perspective — a cost controller cannot see cost performance by cost element across the portfolio, a PM director cannot see how many projects are delayed, a CEO cannot see portfolio margin. What would it take to deliver thematic, application-wide **functional dashboards** with custom filtering, and where are the real gaps?*

The deliverable is a **gap register + open questions** that product owners can triage. Where the analysis recommends sequencing, it is one option among several and is explicitly gated on PO decisions.

---

## 1. Executive Summary

Backcast today is a strong **project-scoped** Earned Value Management and change-management system. Per project it computes CPI, SPI, the BAC/EAC-based `cpi_forecast`, CV, SV, VAC, ETC, and EAC (from `Forecast.eac_amount`); it versions every entity under EVCS with branch isolation for change orders; and it exposes RBAC-aware per-project analytics for cost registrations, COQ (Cost of Quality), change-order reporting (with SLA aging), schedule baselines, Gantt, and a composable widget dashboard. **Every reporting endpoint found in the codebase — EVM metrics, change-order stats, document lists, cost-registration aggregation, the dashboard — is anchored to a single `project_id`.** Backcast's strength is *depth-per-project*; its weakness is that **there is no functional or portfolio layer on top of that depth.**

The gap pattern is **identical and structural across all five roles** examined (Cost Controlling, PM Director, CEO/Executive, Backoffice, Production Director). Six root-cause gaps block every functional dashboard:

1. **No cross-project/portfolio aggregation endpoint.** `POST /api/v1/evm/batch` *does* correctly roll multiple `project_id`s into one aggregated `EVMMetricsResponse` (the rollup math `ΣEV/ΣAC`, `ΣEV/ΣPV` is correct — despite a stale docstring claiming "not yet implemented"), but it returns a **single blob labelled `project_ids[0]`**: no per-project breakdown array, no ranking, no RAG bucketing, no breach list.
2. **No functional RBAC roles.** Only six coarse privilege tiers ship (`admin`, `manager`, `viewer`, `ai-viewer`, `ai-manager`, `ai-admin`). None maps to *Cost Controller*, *PMO Director*, *Executive*, *Backoffice/Finance*, or *Production Director*.
3. **No global, cross-page filter bar.** `DashboardContextBus` requires a *single* `projectId`, so portfolio-level filters (date range, org unit, PM, customer, RAG) are impossible — there is nowhere to put them.
4. **`FilterParser` supports only equality and IN.** No `gte`/`lte`/`between`/date-range operators, so "CPI < 0.90", "contract value bands", and **"current year only" / monthly-close** filters cannot be expressed server-side.
5. **No delay / slippage / forecast-finish concept.** `Forecast` is **cost-only** (`eac_amount`); `Project` has no actual/forecast finish date; the only "overdue"/"at_risk" logic in the entire codebase is **Change-Order SLA status**. (The dashboard's `ev_status` is a non-functional stub that always returns `on_track`.)
6. **`Project` has no `organizational_unit_id`, `project_manager_id`, `customer_id`, or `risk_level`.** Portfolio scoping by business unit / PM / customer is blocked at the **data** level — the dimensions do not exist.

Supporting blockers: no committed/PO or invoiced-to-date layer (`CostRegistration` carries only actuals; budget lives solely on `WorkPackage.budget_amount` as the BAC), no contingency/management-reserve bucket, and currency is never normalized in aggregation.

**One security/scope finding worth flagging immediately (independent of any dashboard work):** the batch EVM route checks only the flat `evm-read` permission and **never calls `get_accessible_projects`**, so any user with `evm-read` (including the generic `viewer` tier) can read EVM for arbitrary projects they are not a member of. This should be closed before any portfolio endpoint ships. (See G2.)

The **recommendation framing is deliberately minimum-viable and PO-driven**: if POs choose to build a functional reporting layer, the minimum spine is (a) global-filter infrastructure + `FilterParser` range operators, (b) a thin portfolio aggregation service + per-project breakdown endpoint (reusing the *already-correct* rollup math), and (c) functional RBAC roles + role-scoped landing dashboards. Deeper domain modeling (milestone gates, committed/invoiced layers, capacity, contingency) is large and cross-cutting and should be **deferred and decided per persona** — it does not belong to a "dashboards" initiative unless the PO explicitly funds it.

---

## 2. Goals & Non-Goals

### Goals
- Establish, with code-level evidence, **what Backcast can and cannot do** today for functional/portfolio reporting.
- Research **what these dashboards should contain** for five named roles, grounded in EVM/EPC/capital-project practice.
- Surface the **custom-filter requirement** (date range like "current year", org unit, PM, status) that the user specifically called out, and explain why it is currently impossible.
- Produce a **gap register** and a set of **open questions** product owners can triage as *implement vs. defer*.

### Non-Goals
- Implementing anything. This is analysis only.
- Prescribing exact KPI thresholds (RAG bands, CPI floors) — those are **PO/finance policy decisions**.
- Designing final UI. Widget/route proposals are illustrative, not specifications.
- Re-deriving the EVM math (verified correct and reusable) or the EVCS/RBAC architecture (documented elsewhere).

---

## 3. Methodology

1. **Capability mapping (first-hand + Explore agents).** Routes, services, models, RBAC, and the filter layer were inspected directly. Key facts (FilterParser operators, Project fields, role set, route inventory) were **read first-hand and are cited by file:line**.
2. **Industry research (web, parallelized per role).** 7 research agents (one per role + two cross-cutting: portfolio/EVM standards and global-filter UX) each ran 4–6 targeted web searches and synthesized authoritative practice (PMI, NDIA/ANSI-748, AACE, vendor references: Primavera P6, Deltek, Procore, Acumatica, Smartsheet; plus BI filter-UX references).
3. **Per-role gap analysis.** Each role's research was mapped against the verified capability map to classify every need as `exists` / `partial` / `missing` / `impossible`, with evidence.
4. **Adversarial verification.** 5 verifier agents (one per role) re-checked every gap claim **against the actual code**, defaulting to *refute* absent evidence. This corrected two material points (see §4.4) and confirmed the rest with file:line citations.
5. **Synthesis.** A final agent produced the executive summary, role chapters, cross-cutting themes, the 26-entry gap register, the 15 open questions, and the optional 4-phase sequencing.

> **Notable corrections from adversarial verification** (these prevented false conclusions):
> - The `evm.py:311` docstring claiming multi-project aggregation is *"not yet implemented"* is **stale and wrong** — `_calculate_project_evm_metrics` + `aggregate_evm_metrics` *do* produce a correct weighted rollup. The real gap is the **shape of the response** (one blob, no breakdown) and the **missing RBAC scoping**, not the math.
> - A claim that managers "only see projects they are individually assigned to" was **refuted**: global-scope roles see all projects via `get_accessible_projects`. (This is precisely *why* there is no intermediate, org-unit-scoped tier — see G5.)

---

## 4. Current State: Backcast's Dashboard & Data Foundation

### 4.1 What exists today (and is reusable)

| Capability | Where | Scope |
|---|---|---|
| Composable widget dashboard (21 widgets) | `frontend/src/features/widgets/` → `/projects/:projectId/dashboard` | **Single project** |
| EVM metrics (CPI/SPI/CV/SV/EAC/ETC/VAC/progress) | `evm_service.py`; `/evm/metrics`, `/evm/metrics/batch`, `/evm/timeseries` | WP / WBS / Control Account / **Project** |
| EVM time-series (DAY/WEEK/MONTH) | `evm_service.get_evm_timeseries` | **Single entity** |
| Cost budget status (budget/used/remaining/%) | `cost_registration_service.get_*_budget_status` | Cost element / WBS / **Project** |
| Cost aggregation by period / cumulative | `get_aggregated_costs_by_entity`, `/cost-registrations/aggregated-by-period` | cost element / WBS / **Project** |
| COQ (CPQ, CPIq, QPI, COQ ratio, trend) | `cost_event_service.get_summary` | **Project** |
| Change-order analytics (by status/impact, trend, exposure, aging, approval workload) | `change_order_reporting_service.get_change_order_stats` → `/change-orders/stats` | **Project (mandatory `project_id`)** |
| Schedule baseline + Gantt | `schedule_baseline_service`, `gantt` route | **Project** |
| RBAC-aware project visibility | `rbac_unified.get_accessible_projects(user_id)` | Per-user project set |
| Org-unit model (hierarchical, with `manager_id`) | `organizational_unit.py` | Used in Control-Account matrix (WBS × OrgUnit) |
| FilterParser (server-side) | `core/filtering.py` | eq + IN only (6 endpoints) |
| 3 default dashboard templates | `dashboard_layout_service._TEMPLATES` | **Single project** |

**The rollup math is correct and reusable.** `aggregate_evm_metrics` sums EV/AC/PV and re-derives indices (`cpi = ΣEV/ΣAC`, `spi = ΣEV/ΣPV`) — the industry-standard "roll up, never average" pattern (§5.1). A portfolio layer does **not** need to reinvent EVM; it needs to *expose* this math across the accessible project set with a per-project breakdown.

### 4.2 The single-project ceiling

- **Every analytics route is project-scoped.** `/change-orders/stats` takes `project_id: UUID = Query(...)` (mandatory). `/dashboard/recent-activity` returns a single "project spotlight" + recent activity. There is **no** `/portfolio`, `/reports`, `/analytics`, `/kpis`, or `/executive` route — backend or frontend (confirmed: `ls backend/app/api/routes/` and `grep` of `frontend/src/routes`).
- **The widget dashboard cannot be mounted globally.** `DashboardContextBus` requires `projectId: string` (not optional); every widget early-returns without it. There is no portfolio context.
- **The project list (`/projects`) is basic:** filter by `status` (draft/active/completed/on_hold), search, sort. No EVM health, no delay flag, no margin, no RAG — nothing a director needs at a glance.
- **A naming collision to avoid confusion:** Backcast already ships a dashboard template *named* **"Cost Controller"** (`_TEMPLATES["Cost Controller"]`). It is a **single-project widget layout** (project-header, budget-status, cost-registrations, change-orders-list, change-order-analytics, forecast). It is **not** a functional cost-controlling dashboard. The functional dashboard this analysis scopes is *cross-project*; the existing template is *per-project*.

### 4.3 Existing data assets a portfolio layer could reuse

- Correct per-project EVM (the hard part — already done).
- `get_accessible_projects(user_id)` — the scoping primitive for any portfolio query.
- `ChangeOrderReportingService` — a portfolio wrapper can reuse per-project CO analytics.
- `CostEventService` COQ computation — reusable for a portfolio COQ rollup.
- `custom_fields` JSONB on Project — could absorb `customer_id`/`risk_level`/`program_id` if the PO prefers to avoid a migration for those (see G6).

### 4.4 Two findings to act on regardless of the initiative

1. **G2 — RBAC scoping gap on the batch EVM route (security).** The route checks `evm-read` only; it never calls `get_accessible_projects`. Close it before any portfolio endpoint ships. *(Effort S; ships independently.)*
2. **Stale `evm.py:311` docstring.** Claims multi-project aggregation is "not yet implemented"; it is. Fix the comment to prevent future confusion. *(Trivial.)*

---

## 5. Industry Best Practices — What Functional Dashboards Should Present

Synthesized from the per-role and cross-cutting web research (sources in §12). These are the standards any functional/portfolio dashboard in an EVM/capital-project context is measured against.

### 5.1 Portfolio & functional-dashboard principles

- **Single source of truth.** Every metric, RAG colour, and KPI definition computes from one canonical model so executives and functional leads never see conflicting numbers. *Standardize terminology and KPI definitions before expanding scope.*
- **Role-scoped views off one shared metric core.** The same portfolio data is sliced per persona (executive, PM, cost engineer, finance, controls) — **not recomputed per role**. Primavera P6, Deltek, and Procore all standardize on role-based interfaces over one underlying dataset.
- **Roll up, never average.** Portfolio KPIs sum the underlying EVM quantities (EV/AC/PV) across projects and **re-derive** the index — *not* the mean of per-project indices — so large projects correctly weight the portfolio number. (Backcast already does this correctly; the gap is exposure, not math.)
- **Drill-down symmetry.** Every rolled-up number must be navigable down the WBS/contract/project/period hierarchy to its contributing line items (treemap + matrix structures).
- **Standardize before complexity.** Fixed cadence (weekly/monthly), a small agreed KPI set, and consistent RAG thresholds — *then* advanced analytics.

### 5.2 Standard portfolio KPIs (the "what should be there" baseline)

Portfolio CPI · Portfolio SPI · **Composite Health (CPI × SPI)** · **% Projects On-Budget / On-Time** · **Total Committed vs Actual (exposure)** · **Portfolio Margin / Forecast-at-Completion Variance** · **At-Risk Project Count & Value** · **Total Change-Order / Contingency Exposure**. These are the metrics every reference treats as table-stakes for a portfolio/executive view.

### 5.3 Global-filter UX principles (directly answers the user's "avoid the full dataset" requirement)

- **Scope-then-read.** A persistent global filter bar lets the user narrow scope (date, org unit, PM, status) *before* the dashboard loads full data. **The full unfiltered dataset should never be the default view.**
- **Date-range control *with presets*.** Must offer both relative presets (This Month / Quarter / **FY / YTD** / Last 12 Months / Rolling N) **and** a manual calendar — "Current FY" / "current year" is the 80% case, so a bare calendar is insufficient.
- **Custom fiscal-year support.** "Current FY" presets must respect a configurable FY start date, not assume Jan–Dec.
- **Multi-select with search** for high-cardinality dimensions (PM, Customer, Cost Category, Status).
- **Cascading/dependent filters** (Division → BU → Team; Customer → Project) to avoid empty-result combinations.
- **Hierarchical org-unit drill-down** — pick a node and implicitly include descendants.
- **Persist & share.** Encode filters in the URL (refresh/bookmark/share reproduces the exact view); support **saved named presets** for recurring reviews.
- **Role-aware defaults via RBAC/row-level security** — each user lands on a narrow, relevant slice (their BU, their FY), not the whole portfolio.

> **Match against Backcast today:** of the eight filter-UX principles above, Backcast satisfies **zero at a portfolio level**. It has no global bar, no date-range operator (`FilterParser` is eq/IN only), no fiscal-period concept, no multi-select portfolio slicers, no saved views, and no org-unit/PM/customer dimensions on `Project`. This is the sharpest expression of the gap.

---

## 6. The Custom-Filter Requirement (deep dive)

The user's requirement: *"a functional dashboard shall have custom filter capabilities, to avoid working with the full set of data — e.g., cost controlling or PM directors could analyze only current-year data."*

**Today this is impossible for three independent reasons, any one of which is sufficient:**

1. **`FilterParser` has no range/date operators.** `build_sqlalchemy_filters` (`core/filtering.py:320–325`) emits only `column == value` or `column.in_(values)`. There is no `between`, no `gte`/`lte`, no date-range. So `registration_date` for "current year", `cpi < 0.90`, `contract_value` bands, and `SPI < 0.9` cannot be expressed. (The dedicated `/cost-registrations/aggregated` endpoint does accept `start_date`/`end_date` separately, but the generic list endpoints do not.)
2. **There is no global filter surface.** `DashboardContextBus` is single-project; there is no place to host a portfolio-wide (period + org + PM + RAG) context. Frontend filters are per-feature/per-page only.
3. **The slicer dimensions don't exist on `Project`.** No `org_unit_id`, no `project_manager_id`, no `customer_id`. You cannot filter "my business unit's projects, this year" because projects carry no business-unit or PM attribution.

**Minimum-viable path to satisfy the requirement (open question G3 + G4 + G6):**
- Extend `FilterParser` with range operators on whitelisted numeric/date columns (effort **S–M**).
- Add `organizational_unit_id` + `project_manager_id` (+ optionally `customer_id`) to `Project` (effort **M**, a migration) — *the single highest-leverage data-model decision*.
- Build a global `FilterBar` + filter-context store + URL persistence + RBAC-scoped defaults on a new portfolio route (effort **L**), co-delivered with the portfolio endpoint.

These three are **co-dependent**: the filter bar is useless without the endpoint to query, and both are useless without the attribution columns. They should land together (Phase 1 in §11).

---

## 7. Cross-Cutting Gaps (the six root causes)

| # | Theme | Current | Gap | Recommendation (open question) |
|---|---|---|---|---|
| **G1** | Portfolio aggregation layer | `evm/batch` rolls up correctly but returns **one blob** (`project_ids[0]`); no breakdown/ranking/RAG/breach; caller must supply IDs; **no RBAC scoping** | No portfolio endpoint with per-project breakdown + auto-resolved accessible set | **Investigate→implement** a thin `GET /evm/portfolio` reusing `aggregate_evm_metrics`. *Keystone gap* — most role KPIs depend on it. |
| **G2** | RBAC scoping (security) | Batch EVM route checks `evm-read` only, never `get_accessible_projects` | Any `viewer` can read arbitrary projects' EVM | **Implement** (S). Close before any portfolio endpoint. |
| **G3** | Global filter bar | None; `DashboardContextBus` is single-project | No portfolio-wide (period+org+PM+RAG) context | **Investigate→implement** (L). Co-dependent with G1/G4. |
| **G4** | FilterParser range ops | eq + IN only | No date-range/bands/thresholds | **Investigate→implement** (S–M operators; M–L to make *computed* CPI/SPI/VAC filterable). |
| **G5** | Functional RBAC roles | 6 privilege tiers only | No cost-controller/pmo/executive/backoffice/production roles; no org-unit-scoped tier | **Investigate** (M). Persona→permission matrix is a PO decision; gated on G6. |
| **G6** | Project attribution | `Project` has no org_unit/PM/customer/risk | "By BU / by PM / by customer" impossible at data level | **Investigate→implement** (M). *Highest-leverage data-model decision.* |

Plus domain-depth gaps deferred by default (see Gap Register §9): no committed/PO/invoice layer (G8), no contingency bucket (G9), no per-CostElement budget (G10), no forecast finish / milestone-gate (G14/G15), no document-compliance model (G21), no capacity/resource/defect entities (G24), no currency normalization (G19), no portfolio EVM time-series (G20).

---

## 8. Role-by-Role Analysis

For each role: what the dashboard should show (industry), what Backcast delivers today, the KPI-level gap, and the top gaps. Status legend: ✅ exists · ◐ partial · ✗ missing · 🚫 impossible (needs new domain modeling).

### 8.1 Cost Controlling (Controlling Analyst)

**Needs:** a *cost-distress* portfolio view — which projects have CPI below an action threshold, ranked by VAC, with committed-vs-actual exposure and CV decomposed by cost category. A controller must avoid working the full set; they want "this year, my BU, CPI < 0.90".

| Need | Backcast | Gap | Priority |
|---|---|---|---|
| Portfolio CPI/SPI rollup (weighted) | ◐ (single blob) | No dedicated endpoint, no breakdown, no RBAC scoping | High |
| CPI action-threshold / cost-distress governance | ✗ | `warning_threshold_percent` is *consumption*%, not CPI; no threshold-count endpoint | High |
| Per-project CPI/VAC exception list (ranked, breach) | ✗ | Batch collapses to one object; no ranked array | High |
| Committed (PO) vs Actual vs ETC exposure | ✗ | No committed/PO/contingency fields anywhere | High |
| CV decomposed by cost element/category | 🚫 | BAC lives on WorkPackage, not CostElement; no category axis | Medium |
| ΔEAC / forecast-drift history | ◐ | Forecast-history endpoint is **410 GONE**; no EAC history read path | Medium |
| TCPI in standard EVM response | ✗ | TCPI exists only in CO impact analysis, not `EVMMetricsResponse` | Medium |
| Functional cost-controller role | ✗ | Only 6 system roles; EVM gated by flat `evm-read` | High |
| Inequality/date-range filtering (CPI<0.90, current year) | ✗ | `FilterParser` is eq/IN only | High |

**Top gaps:** no per-project breakdown endpoint (collapses to `project_ids[0]`) · no CPI-threshold governance (the only threshold is 80% budget *consumption*, not a CPI band) · no committed/PO or contingency concept (so "exposure = actuals + committed + ETC" is uncomputable) · CV cannot be split by cost element (structural) · no inequality/date-range filtering · no cost-controller role.

### 8.2 Project Management Director (PMO Director)

**Needs:** portfolio governance — PM workload & performance scorecards, % projects on-budget/on-time, CO pipeline (count/value/aging/mean cycle) rolled up, one global filter context (period + org + PM + RAG) across all charts.

| Need | Backcast | Gap | Priority |
|---|---|---|---|
| Portfolio EVM summary list `[{project_id,cpi,spi,vac,contract_value,rag}]` | ✗ | No per-project tuple endpoint | High |
| PM workload & performance scorecard | 🚫 | No `manager_id` on Project, no capacity on User, no forecast finish/milestone | High |
| % Projects On-Time | 🚫 | No forecasted finish, no milestone/stage-gate | High |
| % Projects On-Budget (VAC≥0 count) | ✗ | No endpoint counts VAC≥0 across portfolio | Medium |
| Portfolio CO pipeline (count/value/aging/cycle/%-of-BAC) | ✗ | Every CO endpoint requires single `project_id` | High |
| RAG / health_status concept | ✗ | No stored field, no derived bands, no RAG distribution | High |
| Capacity / effort model | ✗ | User has no capacity/effort/available-hours | High |
| Functional PMO-director role | ◐ | Global roles see all, but no functional role / no org-scoped tier | Medium |
| Global cross-page filter bar | ✗ | `DashboardContextBus` is single-project | High |

**Top gaps:** no PM-to-project assignment (`manager_id`) and no capacity model (PM scorecards impossible) · "% on time" impossible at every level (no forecast finish, no milestone entity) · no portfolio CO pipeline · no RAG/health concept (so "show only red" can't be a filter) · no per-project summary-list endpoint (N+1 fan-out today) · no global filter bar.

### 8.3 CEO / Executive Leadership

**Needs:** top-down portfolio visibility for capital allocation — at-a-glance health scorecard (portfolio CPI, SPI, **composite CPI×SPI**, margin/VAC), at-risk count & value, a treemap sized by contract value, a breach list ranked by |VAC|, and cash-flow/capital-deployment by fiscal period.

| Need | Backcast | Gap | Priority |
|---|---|---|---|
| Portfolio CPI/SPI/composite scorecard tiles | ◐ (math correct) | No dedicated endpoint, no RAG banding, no breakdown | High |
| Per-project breakdown (treemap / breach list) | ✗ | Batch returns single object; no ranking by |VAC| | High |
| RAG banding config (Green/Amber/Red) | ✗ | No server-side thresholds; `ev_status` is a stub | High |
| Portfolio margin / FAC variance | ✗ | `contract_value` never joined to EAC; no margin endpoint | High |
| At-risk count & value (CPI×SPI < threshold) | ✗ | No count, no $-weighting, no breach detection | High |
| Cash-flow / capital deployment by fiscal period | ✗ | ETC is a point value; Forecast has no dates to phase | Medium |
| **RBAC scoping on batch EVM route** | ✗ | Checks `evm-read` only — **security gap** | High |
| Portfolio time-series of CPI/SPI | ✗ | `get_evm_timeseries` is single-entity only | Medium |

**Top gaps:** **the batch route's missing RBAC scoping is a security issue that must precede any executive endpoint** · no dedicated portfolio endpoint / no breakdown array (treemaps & breach lists impossible) · no RAG banding / `ev_status` is a stub · margin never computed (`contract_value` − EAC not joined) · no cash-flow phasing · no portfolio time-series · currency never normalized in aggregation.

### 8.4 Backoffice (Finance Ops / Administration / Document Control)

**Needs:** a cross-project approvals & processing queue — approvals/aging with multiple time buckets and %within-SLA across *all* approval types, invoice/cost reconciliation (committed-vs-invoiced bridge), document completeness/compliance + overdue/rejected worklists, throughput/FTE attribution.

| Need | Backcast | Gap | Priority |
|---|---|---|---|
| Portfolio approvals/aging (multi-bucket, %within-SLA, all types) | ✗ | CO-only, single-project, single-threshold, current-user-only | High |
| Committed (PO) vs Invoiced vs Actual reconciliation | ✗ | No committed/invoiced/PO/Invoice layer | High |
| Document completeness / compliance rate | ✗ | No mandatory-deliverable catalog, no required/approval status | High |
| Overdue/rejected deliverables worklist | ✗ | No `due_date`, no "rejected" status, no review timestamps | High |
| Invoices-awaiting-processing backlog | ✗ | No Invoice entity; `invoice_number` is free-text on CostRegistration | High |
| Cost-registration data-quality / validity ratio | ✗ | No `validation_status`/data-quality field | Medium |
| Throughput/FTE attribution across portfolio | ✗ | Aggregation requires exactly one entity; no FTE field | Medium |
| Functional backoffice/finance role | ✗ | Only 6 roles; `manager` is far too broad | High |
| Cross-project/org-unit queue slicing | ✗ | No `org_unit_id` on Project/CO/CostRegistration/Document | High |

**Top gaps:** no committed/PO/invoice layer (blocks reconciliation + exposure across roles) · no portfolio approvals/aging (CO reporting is single-project, single-threshold, current-user-only) · document compliance impossible (no deliverable catalog, no review/rejection state) · no backoffice role (`manager` grants project create/delete + full CRUD — too broad) · no org-unit/FTE dimension on queue entities · monthly-close impossible via list endpoints (no date-range operator).

### 8.5 Production Director (Operations / Delivery)

**Needs:** delivery-execution visibility — SPI distribution & ranking across the portfolio, **milestone/gate adherence** (FAT/SAT/SHIP/INSTALL/COMMISSIONING) with MAR, % on time, physical-vs-planned progress divergence, forward-load/weeks-of-work-on-hand, and a cross-project gate/milestone timeline.

| Need | Backcast | Gap | Priority |
|---|---|---|---|
| SPI portfolio distribution / ranking / count SPI<0.9 | ✗ | Batch returns single blob; no per-project SPI list | High |
| Milestone/Gate entity (FAT/SAT/SHIP, planned/actual/forecast, pass/fail) | 🚫 | No gate entity; `ScheduleBaseline` is WP-spanning only | High |
| MAR / FAT-SAT pass rate / overdue-gate count | 🚫 | Blocked on gate entity | High |
| % On-Time / Forecast-Finish vs baseline | 🚫 | Forecast has no finish; Project has no actual finish | High |
| Physical/measurement progress vs planned (divergence) | ◐ | `ProgressEntry` is self-reported % only | Medium |
| Forward-load / weeks-of-work-on-hand | 🚫 | Needs gate ship dates **and** capacity entity | High |
| Work-Center / Resource / Capacity / Utilization | ✗ | No capacity/resource entity | High |
| Punch-list / Snag / Defect (severity/age) | ✗ | No defect/issue entity | Medium |
| Portfolio-average S-curve (cumulative PV/EV/AC) | ✗ | EVM timeseries is single-entity | Medium |
| Functional production-director role | ✗ | Only 6 system roles | High |

**Top gaps:** no milestone/gate entity anywhere (MAR, gate pass-rate, overdue-gate counts impossible) · Forecast is cost-only (no forecast finish) so % on-time is impossible at every level · no Work-Center/Resource/Capacity entity (utilization/forward-load impossible) · no SPI distribution/ranking · no Punch-list/Defect entity · no production-director role and no Project↔OrgUnit link.

---

## 9. Gap Register (master)

`Decision`: **I** = implement · **D** = defer · **Inv** = investigate (PO-gated). `Effort`: S / M / L / XL.

| ID | Gap | Role | Severity | Status | Decision | Effort |
|---|---|---|---|---|---|---|
| **G1** | No portfolio EVM endpoint with per-project breakdown/ranking/breach; batch collapses to one blob | cross-cutting | blocker | missing | I | M |
| **G2** | Batch EVM route does **no** RBAC membership scoping (security) | cross-cutting | blocker | missing | I | S |
| **G3** | No global cross-page filter bar / portfolio filter context | cross-cutting | blocker | missing | I | L |
| **G4** | `FilterParser` is eq/IN only — no range/date operators | cross-cutting | major | missing | I | M |
| **G5** | No functional RBAC roles | cross-cutting | major | missing | Inv | M |
| **G6** | `Project` has no org_unit/PM/customer/program/risk | cross-cutting | blocker | missing | I | M |
| **G7** | No CPI action-threshold / cost-distress governance | Cost Controller | blocker | missing | Inv | S |
| **G8** | No committed/PO or invoiced layer; no Invoice/PO entity | cross-cutting | blocker | missing | D | XL |
| **G9** | No contingency/management-reserve bucket; budget only on WP (BAC) | Cost Controller | blocker | missing | D | L |
| **G10** | CV not decomposable by cost element/category (structural) | Cost Controller | major | missing | D | L |
| **G11** | No ΔEAC/forecast-drift endpoint; Forecast history is 410 GONE | Cost Controller | major | partial | Inv | M |
| **G12** | TCPI absent from `EVMMetricsResponse` (only in CO impact) | cross-cutting | minor | partial | I | S |
| **G13** | No PM-to-project assignment (`manager_id`) + no capacity model | PMO Director | blocker | missing | Inv | M |
| **G14** | No forecasted finish / EACt on Forecast; no actual finish on Project | cross-cutting | blocker | missing | D | L |
| **G15** | No Milestone/Gate entity (FAT/SAT/SHIP/…) | Production | blocker | missing | D | XL |
| **G16** | No RAG/health_status concept (no field, no bands) | cross-cutting | major | missing | Inv | M |
| **G17** | No portfolio CO pipeline (count/value/aging/cycle) | PMO Director | blocker | missing | Inv | M |
| **G18** | No portfolio gross-margin endpoint (contract_value∉EAC) | CEO | major | missing | I | S |
| **G19** | Currency not normalized in aggregation | cross-cutting | minor | missing | D | L |
| **G20** | No portfolio EVM time-series | cross-cutting | major | missing | D | L |
| **G21** | No document completeness/compliance catalog; no review/rejection state | Backoffice | blocker | missing | D | XL |
| **G22** | No portfolio approvals/aging (multi-bucket, %within-SLA, all types) | Backoffice | major | missing | Inv | M |
| **G23** | No cost-registration data-quality/validity dimension | Backoffice | major | missing | D | M |
| **G24** | No Work-Center/Resource/Capacity entity; no Punch-list/Defect entity | Production | blocker | missing | D | XL |
| **G25** | No "on time"/delayed/at-risk detection outside CO SLA; `ev_status` is a stub | cross-cutting | minor | partial | Inv | S |
| **G26** | No org-unit/FTE dimension on backoffice queue entities | Backoffice | major | missing | Inv | M |

**Read of the register:** 8 *blockers* — but only **G1, G2, G3, G6** are "implement-now" blockers (the portfolio spine + security + attribution). The other blockers (G8/G9/G14/G15/G21/G24) are **domain-depth** gaps explicitly **deferred** — they are large, belong to procurement/finance/delivery modules, and are *not* prerequisites for a first functional-dashboard layer. An **interim SPI<0.9 slippage proxy** (G25) gives a usable "at-risk" signal *without* G14/G15.

---

## 10. Open Questions for Product Owners (implement vs. defer)

1. **Portfolio endpoint (G1+G2):** Build `GET /api/v1/evm/portfolio` resolving accessible projects, returning a per-project breakdown `[{project_id,name,cpi,spi,vac,contract_value}]`, enforcing RBAC scoping, and fixing the stale docstring? *Tradeoff:* the keystone unlocking most role KPIs, reusing correct math — but the first real cross-project query path to maintain.
2. **Global filter bar vs. per-page filters (G3):** Invest in a persistent global `FilterBar` (date range, org unit, PM, customer, RAG) with URL-persisted + saved-view state? *Tradeoff:* prerequisite for any director/executive dashboard and an industry standard — but L-effort frontend infra that only pays off if a portfolio route also ships.
3. **FilterParser range ops + filterable EVM indices (G4):** Extend `FilterParser` with range/date operators, and should CPI/SPI/VAC become filterable/sortable? *Tradeoff:* operators are S–M; making *computed* indices filterable needs materializing/specialized-querying them (the deeper sub-question: persist EVM snapshots?).
4. **Functional RBAC roles (G5):** Seed cost-controller/pmo/executive/backoffice/production-director as permission bundles? *Tradeoff:* cheap to seed, but the persona→permission matrix is a product decision, and roles without org-unit scoping can't express portfolio spans — gated on G6.
5. **Project attribution columns (G6):** Add `organizational_unit_id` + `project_manager_id` + `customer_id` (+ optionally program_id/contract_type/risk_level) to `Project`? *Tradeoff:* the single highest-leverage data-model decision; M-effort migration. Could customer_id/risk_level go into `custom_fields` JSONB instead?
6. **Cost-distress CPI threshold (G7):** Add a configurable CPI action-threshold (distinct from the consumption-based `warning_threshold_percent`) + a count endpoint? *Tradeoff:* small once G1 exists; threshold values are a PO/finance policy decision.
7. **TCPI in standard metrics (G12):** Surface TCPI=(BAC−EV)/(BAC−AC) in `EVMMetricsResponse`? *Tradeoff:* trivial (S), industry-standard, low risk.
8. **Portfolio gross-margin endpoint (G18):** Compute Σ(contract_value − EAC)/Σcontract_value? *Tradeoff:* both fields exist; small join once G1 returns contract_value. Defer if margin isn't an executive priority.
9. **Portfolio CO pipeline (G17):** Wrap `ChangeOrderReportingService` for a cross-project CO pipeline? *Tradeoff:* per-project service exists (moderate effort), but the route currently swallows all exceptions in HTTP 500 — hardening required; non-CO approval types need new entities (deferred).
10. **Committed/invoiced/contingency layers (G8/G9/G10):** Model PurchaseOrder/Invoice/committed_value, a contingency bucket, and per-CostElement budget? *Tradeoff:* unblock committed-vs-actual exposure, CV-by-category, reconciliation — but L–XL domain modeling that belongs to a procurement/finance module.
11. **Milestone/Gate entity + forecast finish (G14/G15):** Model gates (FAT/SAT/SHIP/INSTALL/COMMISSIONING) and add `forecasted_finish_date`? *Tradeoff:* unblock MAR, gate pass-rate, % on-time, forward-load — but the largest efforts (L–XL); interim SPI<0.9 proxy works without them.
12. **Document compliance + review workflow (G21):** Add a mandatory-deliverable catalog + required/approval/compliance status + due_date + rejection state? *Tradeoff:* unblock completeness rate, overdue/rejected worklists — but large document-domain modeling.
13. **Capacity/resource/defect entities (G24):** Model Work-Center/Resource/Capacity/Utilization and Punch-list/Defect? *Tradeoff:* unblock utilization, forward-load, weeks-of-work-on-hand, punch-list aging — but large new domain entities.
14. **RAG banding policy (G16):** Define/persist RAG thresholds (e.g. Green CPI>1.0, Amber 0.95–1.0, Red<0.9) or compute transiently? *Tradeoff:* persisting enables "show only red" as a filter; transient ships faster but isn't filterable.
15. **Interim slippage proxy vs. full delay detection (G25):** Ship an SPI-based "at-risk" proxy now (feasible once G1+G4 exist) and defer true forecast-finish/milestone slippage? *Tradeoff:* immediate signal without domain modeling, but less accurate than gate/schedule-based detection.

---

## 11. Recommended Sequencing (one option, if POs choose to implement)

> Not a commitment. Phases are gated on PO decisions; each phase is independently valuable.

- **Phase 0 — Foundation (implement; must precede everything):**
  (a) Fix the stale `evm.py:311` docstring; (b) **close the RBAC scoping gap on the batch route (G2, S)** — a security fix, ships independently; (c) extend `FilterParser` with range operators on whitelisted numeric/date columns (G4, M); (d) add `organizational_unit_id` + `project_manager_id` + `customer_id` to `Project` (G6, M) — the highest-leverage data-model prerequisite. TCPI in `EVMMetricsResponse` (G12, S) and the portfolio margin endpoint (G18, S) ride along cheaply.

- **Phase 1 — Portfolio aggregation + global filter bar (implement; the keystone):**
  (a) `GET /api/v1/evm/portfolio` — per-project breakdown + rolled-up summary, resolving accessible projects server-side (G1, M); (b) global `FilterBar` + filter-context store + URL persistence + RBAC-scoped defaults on a new portfolio route (G3, L); (c) a CO-portfolio wrapper over `ChangeOrderReportingService` with hardened error handling (G17, M).
  *Makes treemaps, breach lists, RAG distribution, and exception ranking possible. Co-dependency: the endpoint and the filter bar should land together.*

- **Phase 2 — Functional roles + role-scoped landing dashboards (investigate; PO-gated):**
  Seed functional roles (G5, M) once the persona→permission matrix is defined and G6 lands; build role-scoped landing dashboards reusing the Phase-1 portfolio core. RAG banding (G16) can be computed transiently here before persisting. *Defer role work until Phase 1 proves the portfolio surface — roles without scoping can't express portfolio spans.*

- **Phase 3 — Deferrable domain-depth gaps (defer; decide per persona):**
  committed/PO/invoice + contingency (G8/G9/G10), milestone/gate + forecast finish (G14/G15), document compliance/review (G21), capacity/resource/defect (G24), portfolio EVM time-series (G20), currency normalization (G19), cost-registration data-quality (G23). Each is L–XL and belongs to a functional module — *prioritize by persona demand, don't bundle.*

**Minimum that solves the user's stated need** ("cost controller sees cost by cost element; PM director sees how many projects are delayed; current-year filtering"): **Phase 0 + Phase 1**, plus the G25 SPI<0.9 interim proxy for "delayed" until G14/G15 are funded. That is the smallest slice that delivers real cross-project functional dashboards with custom filtering.

---

## 12. References (selected)

**EVM / portfolio / PMO standards & vendor practice**
- PMI — Project portfolio EVM, treemaps & maturity — https://www.pmi.org/learning/library/project-portfolio-evm-treemaps-maturity-8341
- PMI — Organizational structure & cross-functional projects — https://www.pmi.org/learning/library/organizational-structure-project-cross-functional-3546
- Profit.co — EVM in project portfolio management — https://www.profit.co/blog/earned-value-management/project-success-with-earned-value-management-evm-in-project-portfolio-management-ppm/
- ILX — How to create a PMO dashboard that drives decisions — https://www.ilxgroup.com/usa/blog/how-to-create-a-pmo-dashboard-that-drives-decision-making
- FanRuan — Portfolio reporting for PMOs — https://www.fanruan.com/en/blog/portfolio-reporting-for-pmos
- Smartsheet — Project portfolio dashboards — https://www.smartsheet.com/content/project-portfolio-dashboards
- OpenText — Anatomy of an effective PPM dashboard — https://blogs.opentext.com/the-anatomy-of-an-effective-project-and-portfolio-management-dashboard/
- Oracle / ProjectManager — Primavera P6 — https://www.projectmanager.com/blog/what-is-primavera-p6
- AcuityPPM — PMO guide to portfolio charts (heatmap, bubble) — https://acuityppm.com/the-pmo-guide-to-portfolio-management-charts/
- Mastt — Project management dashboards for capital projects — https://www.mastt.com/blogs/project-management-dashboards-capital-projects

**Dashboard filter UX (the "avoid the full dataset" requirement)**
- Pencil & Paper — UX pattern analysis: enterprise filtering — https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-filtering
- Mokkup — Uses of filters in dashboards — https://www.mokkup.ai/blogs/uses-of-filters-in-dashboards/
- UXPilot — Dashboard design principles — https://uxpilot.ai/blogs/dashboard-design-principles
- Grow — Selecting date ranges — https://help.grow.com/hc/en-us/articles/23157408988173-Selecting-Date-Ranges
- Foundant — Adjusting for fiscal year in data visualization — https://support.foundant.com/hc/en-us/articles/40643382909975-Adjusting-for-Fiscal-Year-in-Data-Visualization
- Polaris (Shopify) — Date-range picker pattern — https://polaris-react.shopify.com/patterns/date-picking/date-range
- Tableau — Save dashboard filters / custom views — https://www.tableau.com/blog/save-dashboard-filters-custom-views-for-viewer-role-105941
- HubSpot community — Saved views / pre-set filters — https://community.hubspot.com/t/dashboards-should-have-saved-views-or-pre-set-filters/131029
- Microsoft — Power BI row-level security (role-aware defaults) — https://learn.microsoft.com/en-us/fabric/security/service-admin-row-level-security
- IBM Apptio — Security design patterns (RLS) — https://www.ibm.com/docs/en/apptio-gov/tbm-studio/saas?topic=practices-security-design-patterns

*(Full per-role source lists — ~50 URLs across the 7 research agents — are in the workflow transcript.)*

---

## Appendix A — Capability evidence (file:line)

- **Routes are project-scoped; no portfolio/reports/analytics/kpis routes:** `ls backend/app/api/routes/`; `grep` of `frontend/src/routes/index.tsx` for `/portfolio|/reports|/analytics|/kpis|/executive` → none.
- **`FilterParser` emits only eq/IN:** `backend/app/core/filtering.py:320–325` (`column == values[0]` / `column.in_(values)`); custom-field path also eq/IN only (`filtering.py:132–134`).
- **Batch EVM route lacks RBAC scoping:** `backend/app/api/routes/evm.py` (checks `evm-read` only); `rbac_unified.get_accessible_projects` at `backend/app/core/rbac_unified.py:467`.
- **Rollup math is correct (stale docstring):** `evm_service.aggregate_evm_metrics` (`backend/app/services/evm_service.py:~943`); `_calculate_project_evm_metrics` (`~853`); misleading "BAC-weighted average"/"not yet implemented" docstring at `evm.py:311`.
- **`Project` has no org_unit/PM/customer/risk:** `backend/app/models/domain/project.py:55–88` (fields: `project_id, name, code, budget(computed), contract_value, currency, status, start_date, end_date, description, custom_fields`).
- **Org units exist but only on ControlAccount/CostElementType:** `backend/app/models/domain/organizational_unit.py`; `control_account.py:56–61`.
- **Roles are 6 privilege tiers only:** `backend/app/core/rbac_unified.py` (`get_user_roles:375`); no `cost_controller`/`pmo_director`/etc. anywhere in `backend/app/`.
- **Widget dashboard is single-project:** `frontend/src/features/widgets/context/DashboardContextBus.tsx:40–44` (`projectId: string` required).
- **CO analytics mandatory project-scoped:** `backend/app/api/routes/change_orders.py:61–62` (`project_id: UUID = Query(...)`).
- **Home = single project spotlight:** `backend/app/api/routes/dashboard.py:54` ("project spotlight"); `frontend/src/pages/Home.tsx:44–74`.
- **"Cost Controller" template is a per-project layout:** `backend/app/services/dashboard_layout_service.py:147–187`.
- **Only "overdue/at_risk" logic is CO SLA:** `backend/app/models/domain/change_order.py:59` (`sla_status`); `ev_status` dashboard stub returns `on_track` if cost elements exist.
