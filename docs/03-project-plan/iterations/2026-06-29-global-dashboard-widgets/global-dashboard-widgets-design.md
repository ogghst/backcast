# Global Dashboard Widgets — Design & Phased Plan

**Initiative:** Widget-ize the global (portfolio/functional) dashboards with role-gated widgets.
**Status:** Design (doc-first, awaiting sign-off). No implementation yet.
**Date:** 2026-06-29
**Builds on:** the functional-dashboards initiative (`…/2026-06-28-functional-dashboards/`) and the existing per-project widget dashboard system.

> Source: produced by a 9-agent design workflow (4 design areas → adversarial verification of each → synthesis). The adversarial pass refuted several first-pass claims; those corrections are folded in below and the refutations are summarized in the appendix. Every file:line citation has been re-read against the codebase.

---

## 1. TL;DR

Today there are **two disconnected dashboard worlds**:

- **Project dashboards** (`/projects/:id/dashboard`) — a mature composable **widget grid** (react-grid-layout), a widget registry of 21 widgets, a palette, per-user persisted layouts, admin templates, undo/redo. Read-only/personalized for any authenticated user.
- **Global/portfolio dashboards** (`/portfolio`) — a single **fixed page** (`PortfolioPage.tsx`) of hard-coded components (KPI tiles, a StandardTable, the CO pipeline, at-risk/cost-distress lists) with role-curation baked into page code (`roleLayout.ts`).

This initiative **unifies them on the widget system**: `/portfolio` becomes a widget grid whose widgets are **gated by permission** (so each role sees/picks only its allowed widgets), whose **default layout comes from role-tagged global templates**, and whose fixed components become **registered widgets**. The existing project-dashboard infrastructure (registry, grid, palette, persistence, templates) is reused almost wholesale.

The work decomposes into **10 phases**. The infrastructure is ~70% ready; the real work is a portfolio *scope* in the context bus, 4 new portfolio widgets, per-widget permission + scope gating, a backend RBAC route fix, and role-tagged global templates.

---

## 2. Locked decisions (user sign-off, 2026-06-29)

| | Decision | Detail |
|---|---|---|
| **D1** | **Replace** `/portfolio` fully | `/portfolio` becomes a widget-grid dashboard (`GlobalDashboardPage`). The page-level FilterBar becomes a **global-scope control carried in the dashboard context**. Role defaults become **role-tagged templates**, not page code. The fixed `PortfolioPage` + `roleLayout.ts` are **retired** (full tree). |
| **D2** | **Reuse domain read-perms** as widget gates | A widget's gate is the **existing** domain read-permission its data needs (e.g. portfolio KPI → `portfolio-read`, CO pipeline → `change-order-read`, EVM widgets → `evm-read`). **Zero new permission strings.** `WidgetDefinition.requiredPermission` gates both the palette (pick) and the grid (render). |
| **D3** | **Role-tagged default templates** | Seed a global default template per role; first visit **clones** the user's role template into a personal global (`project_id=NULL`) layout they then customize. Replaces fixed `roleLayout.ts`. |
| **D4** | **Doc-first** | This document. Implementation proceeds phase-by-phase after sign-off (same loop used for functional-dashboards). |

### Decisions still needing sign-off (§9)

A small number of items genuinely require a human/product call before implementation — most notably the **viewer role** (it lacks `portfolio-read` by a *locked* decision, so a "viewer overview" template is unreachable as written) and the **multi-permission widget** field shape.

---

## 3. Current-state map (verified)

### Widget system (frontend)
- **Registry** — `frontend/src/features/widgets/registry.ts` (`registerWidget`, `getWidgetDefinition`, `getAllWidgetDefinitions`). `WidgetDefinition` in `types.ts:137-160`: `typeId, displayName, description, category, icon, sizeConstraints, component, defaultConfig, configFormComponent?, requiresProjectContext?`. **No permission field.**
- **21 widgets** registered via `definitions/registerAll.ts` (side-effect imports). **All project-scoped** — they call hooks like `useEVMMetrics(projectId)`. Only `budget-settings` sets `requiresProjectContext:true`.
- **`WidgetInstance`** (`types.ts`) — `{instanceId, typeId, title?, config, layout{x,y,w,h}}`.
- **`DashboardContextBus`** (`context/DashboardContextBus.tsx:11-44,58-100`) — **requires** `projectId`; exposes `{projectId, wbsElementId, costElementId, branch, asOf, mode, isHistorical, invalidateQueries, setWbeId, setCostElementId}`. Composes `TimeMachineContext` (lines 62-64).
- **`useDashboardCompositionStore`** (Zustand+immer) — `isEditing, activeDashboard, isDirty, backendId, projectId, paletteOpen`, undo/redo (max 20), actions `addWidget/removeWidget/loadFromBackend/...`.
- **`DashboardGrid`** (`components/DashboardGrid.tsx`) — react-grid-layout `Responsive`, 12-col, `ROW_HEIGHT=80`. **Three render paths**: desktop `Responsive` map (~411-477), mobile stacked map (~308-337), and `WidgetFullscreenModal` (~499-506). Has a `WidgetErrorBoundary` (38-77, Result styling 56-74).
- **`WidgetPalette`** (`components/WidgetPalette.tsx`) — enumerates **all** widgets; filters by **text search + category only**. `getAllWidgetDefinitions()` called **outside** `useMemo` (line 53) — registry returns a fresh array each call.
- **Project dashboard page** — `pages/DashboardPage.tsx`, route `/projects/:projectId/dashboard`; `useParams` → `<DashboardContextBus projectId><DashboardGrid onSave={save}/>`; persistence via `useDashboardPersistence(projectId, dashboardName?)`.
- **`useDashboardPersistence`** (`api/useDashboardPersistence.ts`) — load: `layoutApi.list(projectId)`; named dashboard → find-by-name else auto-clone from template; unnamed → prefer `is_default` else first. Save: create (`project_id=pid`) or update by `backendId`. 500ms debounced autosave. Navigation guards (`beforeunload` + `useBlocker`).

### Templates + backend
- **`DashboardLayout`** model (`backend/app/models/domain/dashboard_layout.py`) — `name, description, user_id, project_id` (**nullable**), `is_template, is_default, widgets(JSONB)`. **`project_id=NULL` already = "global"** (documented + handled).
- **`DashboardLayoutService`** (`services/dashboard_layout_service.py`) — `_TEMPLATES` (4 templates: *Project Overview, EVM Analysis, Cost Controller, COQ Analysis*) seeded `project_id=None, is_template=True`, owned by admin. `get_templates()` returns **all** (no scope/role filter). `get_for_user_project(user_id, project_id=None)` — `None` → global-only; **but with a project_id it returns project-scoped ∪ global** (`| .is_(None)` union, lines 279-281 — the G5 pollution source). `clone_template` (line 454) **hardcodes `is_default=False`** (line 488) and builds the row directly (`session.add`), **bypassing `create()`** so `_clear_default_for_user_project` (line 496) never runs. Seeded at startup in `main.py` lifespan.
- **API routes** (`api/routes/dashboard_layouts.py`) — `GET ""` / `GET /templates` / `GET /{id}` / `POST ""` / `DELETE` / `POST /{id}/clone` are **all** `RoleChecker("project-read")` (lines 39,55,70,97,143,167). `PUT /{id}` has **no** role check (ownership in service). `PUT /templates/{id}` is `dashboard-template-update` (admin). **No "promote layout → template" endpoint.**
- **Schema** — `models/schemas/dashboard_layout.py:14` `project_id: UUID | None = Field(None, ...)` (JSON `null`→None; JSON `""`→422 UUID-parse).
- **FE hooks** — `api/useDashboardLayouts.ts` (`useDashboardLayouts(projectId?)`, `useDashboardLayoutTemplates`, mutations). `layoutApi.templates()` takes **no args** today.
- **Query keys** — `api/queryKeys.ts:425` `list(projectId?)` → `['dashboard-layouts','list',undefined]` for global vs `['…','list',<uuid>]` for project. **`list('')` ≠ `list(undefined)`** — different cache keys.

### RBAC
- **`Permission`** union (`frontend/src/types/auth.ts:16-107`) — ~100 perms incl. `portfolio-read`, `change-order-read`, `forecast-read`, `schedule-baseline-read`, `dashboard-template-update`. **`evm-read` is MISSING** (latent drift from the authoritative catalog `features/admin/rbac/permissions.ts:129`), even though `evm-read` is a live backend permission (`RoleChecker("evm-read")` on `evm.py:121/310/378`).
- **`<Can permission role requireAll fallback>`** (`components/auth/Can.tsx`) + **`usePermission()`** (`hooks/usePermission.ts`).
- **`UserPublic`** has **both** `role: string` **and** `permissions: string[]`. **`/auth/me` already returns the full `permissions[]`** (`UserPublic.from_user_async`). `useAuthStore` exposes `permissions[], hasPermission, hasAnyPermission, hasAllPermissions, hasRole`.
- **`hasPermission`** is typed `(Permission | string) => boolean` (`useAuthStore.ts:45`) — so a missing-from-union perm string still works at runtime (G1 is a type-safety gap, not a build-breaker).
- **`Role` union** — `"admin" | "manager" | "viewer" | "cost-controller" | "pmo-director"` (ai-* roles exist on the backend but not in the FE union).
- **Seed facts that matter** — `viewer` has `project-read` but **NOT** `portfolio-read` (locked decision, `seed_users_rbac.py:329-331`) and **NOT** `evm-read` (only write-roles + `ai-viewer` get it). `display_role = roles[0] if roles else 'viewer'` (`user.py:151`); `get_user_roles` (`rbac_unified.py:405-420`) has **no `ORDER BY`** → multi-role users get a non-deterministic `roles[0]`.

---

## 4. Gap register (G1–G19)

Each gap was surfaced by design + adversarial review; the **resolution** is what the plan implements.

| ID | Area | Gap | Resolution |
|---|---|---|---|
| **G1** | RBAC/Types | `evm-read` missing from the FE `Permission` union (live on backend). 9 widgets gate on it. | Add `\| "evm-read" \| "evm-create" \| "evm-update" \| "evm-delete"` to the union. Make `permissions.ts` the canonical source; follow-up to generate `auth.ts` from `rbac.json`. |
| **G2** | Context bus | Naively widening `projectId` to `string \| undefined` **fails TS strict** at ~13 project-widget call sites that pass it into typed `string` hooks (e.g. `ChangeOrdersListWidget.tsx:54` `useChangeOrders({projectId})` before the `:139` guard). | **Keep `projectId: string`**; add a **`scope`** discriminator (`"project"\|"portfolio"`) + `portfolioFilter?`. Runtime-assert `scope==='project' ⟹ projectId` present; portfolio host passes `projectId=""`. The existing `entityId ?? ""` pattern (`useWidgetEVMData.ts:74`) tolerates empty-string — all project widgets compile unchanged. |
| **G3** | Render gating | The render-time permission placeholder must cover **all 3** `DashboardGrid` paths (desktop, mobile, fullscreen) — not "DashboardGrid" generically. | Factor `isWidgetPermitted(def)` + `<WidgetPermissionPlaceholder/>` (antd Result 403-style, **no** `onFullscreen`) used in all 3 paths. Locked instances **keep their RGL cell** (placeholder inside the existing wrapper) so the grid never reflows and saved x/y/w/h stay stable. |
| **G4** | Backend RBAC | **All** dashboard-layout routes are `project-read`, but `/portfolio` is `portfolio-read`. A portfolio-only role (the layered model) renders the page but gets **403** on list/create/clone/delete. Persistence silently broken. | Change route guards to **requireAny `['project-read','portfolio-read']`** (verify `RoleChecker` supports any-of; add a variant if not). The one mandatory backend RBAC touch (still zero new perm strings). |
| **G5** | Persistence | **Global→project layout pollution**: `get_for_user_project` returns project ∪ global rows, so a user's `/portfolio` dashboard appears in **every** project's layout list and can be auto-selected as the project default. | Add a strict-scope path (or `get_global_for_user`) so the global page loads **only** `project_id IS NULL`; reconsider the project query's global-union; at minimum gate the project default-pick to `is_default AND matching scope`. |
| **G6** | Persistence | **Cache-key split**: `list('')` ≠ `list(undefined)`. `useCloneTemplate` invalidates `list(undefined)`; if the global page passes `''`, the clone is invisible until manual refetch. | **Pin the global sentinel to `undefined`, never `''`.** Global page calls `useDashboardPersistence(undefined)`. |
| **G7** | Persistence | **Empty-string 422**: `saveDashboard` sends `project_id: pid`; for the global page `pid=''`; `DashboardLayoutCreate.project_id: UUID\|None` rejects `''`. First autosave fails silently → edits lost on refresh. | In `saveDashboard` send `project_id: pid ?? null`. Regression test: `null` round-trips, `''` 422s. |
| **G8** | Persistence/D3 | `clone_template` hardcodes `is_default=False` and bypasses `create()` → `_clear_default_for_user_project` never runs → two re-firing first-visit clones can leave **two** `is_default` global layouts. | Add `is_default` kwarg to `clone_template`; when `True`, call `_clear_default_for_user_project` first. Add `CloneTemplateRequest.is_default: bool = False`. |
| **G9** | D3 role-match | `get_user_roles` has no `ORDER BY`; `display_role = roles[0]` flaps for multi-role users (exactly the platform+functional layered model) → first-visit clone non-reproducible. | Add `.order_by(RBACRole.name)` (or a declared precedence preferring the most-specific functional role) before shipping D3. |
| **G10** | D3 seed | Contradiction: "Portfolio Overview" tagged `role='manager'` **and** claimed as the `role IS NULL` fallback — impossible in one row (admin → empty grid). Also viewer "read-only" template is **dead seed** (viewer lacks `portfolio-read`). | Make **"Portfolio Overview" `role=NULL`** (generic fallback for admin/manager); add `role=cost-controller` ("Cost Controlling") + `role=pmo-director` ("PMO Schedule"). Viewer template: **dropped** ✓ (sign-off 2026-06-29) — do **not** grant `portfolio-read` to viewer (locked decision). |
| **G11** | Retirement | Deletion list incomplete: `usePortfolioFilterStore.ts`/`usePortfolioFilterUrlSync.ts` live in `src/stores/` (with tests); the full portfolio tree (8 source + 8 test files) must all go together or lint/typecheck fails on orphaned imports. | Enumerate the full tree (§8 Phase 10); update the grep verify to cover every retired symbol. |
| **G12** | Retirement | `roleLayout.ts` is the **single source** for D3 seed content (titles, leadMetrics, sort, section order, `cpiCostDistress:69`); deleting it orphans D3. The `MetricMetadata` blocks live in the doomed `PortfolioPage.tsx:64-114`. | **Extract** all reusable pieces (MetricMetadata, `cpiCostDistress`, rag helpers) to a shared module **before** deletion. Hard sequencing: extract (Phase 3) ⟹ delete (Phase 10). |
| **G13** | Scope filter | `get_templates()` returns all templates unfiltered by scope/role → project picker shows "Portfolio Overview" and vice-versa. An admin could also drop project widgets into a global template (→ crash on the global page). | Add `scope` query to `GET /templates` (`global`/`project`/all). **Thread scope through** `layoutApi.templates()` **and** `useDashboardLayoutTemplates` **and** `queryKeys.dashboardLayouts.templates(scope)` or the two scopes alias in cache. |
| **G14** | Perm mapping | Three mappings were **wrong** (would invert the lock for `viewer`): `forecast` claimed `forecast-read` but `ForecastWidget.tsx:32`+`ForecastComparisonCard.tsx:8,28,33` are all `evm-read` (BAC discarded); `cost-history` claimed `cost-event-read` but `CostHistoryChart.tsx:61` is `useEVMTimeSeries` (evm-read); typeId `wbs-tree` doesn't exist (it's `wbe-tree`). | **Remap** `forecast`→`evm-read`, `cost-history`→`evm-read`, `wbs-tree`→`wbe-tree`. |
| **G15** | Perm mapping | `requiredPermission` is singular, but some widgets have **dual** deps (`CostRegistrationsWidget` needs `project-read` *and* `cost-registration-read`). | **Array form** `Permission \| Permission[]` gated via `hasAllPermissions` ✓ (chosen at sign-off 2026-06-29). |
| **G16** | Cross-scope state | `TimeMachineContext.branch/mode` is **global** app state. Sourcing `ctx.branch/mode` into portfolio widgets would couple the portfolio dashboard to whatever branch the user last picked on a *project* dashboard (state leak). | **Freeze** `branch:'main', branchMode:'merged'` in portfolio widgets (port the hardcoded values from `PortfolioPage.tsx:390-391`). Do **not** pass `ctx.branch/mode` into `usePortfolioEVM`/`usePortfolioCO`. |
| **G17** | Behavior change | `usePortfolioCO` is called with **no `asOf`** today (`PortfolioPage.tsx:395-397`) — the CO pipeline ignores the controlDate filter (latent gap). | Wire `controlDate` into `usePortfolioCO` as `asOf` (positive fix). Document as a behavioral change + release note; verify against test data. |
| **G18** | Citations | Inaccurate cites that would mislead implementers: hooks live in `features/portfolio/api/` (no `hooks/` dir); `cpiCostDistress` is `roleLayout.ts:69` (not `rag.ts:38`); `rag.ts` exports are `RED_BAND_THRESHOLD:25` + `ragBand:53`; canonical undefined-ID pattern is `useWidgetEVMData.ts:74`; `registerAll.ts` is a side-effect import (re-runs per import with a console.warn). | Correct all cites in this doc (done). Flag the registration warn; add a module-level `alreadyRegistered` guard if it bothers. |
| **G19** | Perf | `WidgetPalette` calls `getAllWidgetDefinitions()` outside `useMemo` (fresh array each render); adding a perm `.filter` on top runs every render. | Move `getAllWidgetDefinitions()` + the perm/scope filter **inside** the existing `useMemo` chain as one pass. |

---

## 5. Target architecture

### 5.1 Widget scope + permission model
- `WidgetDefinition` gains two optional fields (`types.ts`, Phase 1):
  - `requiredPermission?: Permission | Permission[]` — the domain read-perm(s) its data needs (D2). Gated via `hasAllPermissions`.
  - `scope?: WidgetScope` where `type WidgetScope = "project" | "portfolio" | "any"` (default `"any"`) — which dashboards the widget is valid on.
- `DashboardContextBus` gains a **`scope`** discriminator + `portfolioFilter?` carrier; `projectId` stays `string` (portfolio passes `""`). Runtime-assert `scope==='project' ⟹ projectId` present (Phase 2, G2).

### 5.2 The 4 new portfolio widgets (Phase 4)
Each is `scope:"portfolio"`, self-registers in `registerAll.ts`, reuses the existing portfolio hooks (`usePortfolioEVM`, `usePortfolioCO`) with **frozen** `branch:'main', branchMode:'merged'` (G16) and reads `ctx.portfolioFilter` (not the store directly):

| typeId | Replaces | Permission | Notes |
|---|---|---|---|
| `portfolio-kpi` | `renderKpis` (KPI tiles + distress count) | `portfolio-read` | `defaultConfig.metrics` + `showDistressCount` encode the role's lead choice (replaces `roleLayout.leadMetrics/leadDistressCount`). |
| `portfolio-projects-table` | `renderTable` + client-side status/RAG filter | `portfolio-read` | `StandardTable<PortfolioProjectMetrics>`, identical columns; `defaultConfig.defaultSort` replaces `roleLayout.defaultSort` (URL sort still wins). |
| `portfolio-co-pipeline` | `ChangeOrderPipeline` | **`change-order-read`** | `usePortfolioCO` with `asOf=ctx.portfolioFilter.controlDate` (G17 behavioral change). The one portfolio widget whose gate differs from `portfolio-read`. |
| `portfolio-distress-list` | `DistressList` (at-risk + cost-distress) | `portfolio-read` | Parameterized `config.mode:"schedule"\|"cost"`; the **pagination (10/page) lives inside this widget**. |

### 5.3 Global dashboard page + FilterBar (Phase 8)
- New `GlobalDashboardPage.tsx` mirrors `DashboardPage`: `useDashboardPersistence(undefined)`; `<DashboardContextBus scope="portfolio" portfolioFilter={…}>`; same `DashboardGrid`, guards, skeleton.
- **FilterBar** (controlDate/status/RAG) is relocated to `features/widgets/components/PortfolioFilterBar.tsx` and rendered by `GlobalDashboardPage` **above the grid** (a host-level control, not a palette widget). It still reads/writes `usePortfolioFilterStore`; the host pushes the store value into `portfolioFilter` on the context. `usePortfolioFilterUrlSync` is mounted **once** in the host.
- `/portfolio` route (`routes/index.tsx:354-361`) keeps its path + `<Can permission="portfolio-read">` gate; only the lazy element swaps to `GlobalDashboardPage`.

### 5.4 Role-tagged templates + first-visit clone (Phases 7–8)
- Add a nullable indexed `role VARCHAR(64)` column to `DashboardLayout` (templates only); surface on `DashboardLayoutRead` (read-only — never on Create/Update).
- Seed (`_TEMPLATES`): **"Portfolio Overview" (`role=NULL`)** generic fallback (admin/manager), **"Cost Controlling" (`role=cost-controller`)**, **"PMO Schedule" (`role=pmo-director`)**. Each references the 4 new portfolio typeIds with per-role metric/sort config.
- `get_default_template_for_role(role)`: prefer `role==role`, else `role IS NULL`, else None. `get_user_roles` gets an `ORDER BY` (G9).
- First visit: no saved global layout → clone the user's role template with `project_id=NULL, is_default=true` (G8 fix). Subsequent loads find it via `is_default`.

### 5.5 Backend touches (Phases 6–7)
1. **Route RBAC** (G4): `requireAny ['project-read','portfolio-read']` on the 6 dashboard-layout routes.
2. **`clone_template(is_default=)`** (G8) + `CloneTemplateRequest.is_default`.
3. **`scope` query** on `GET /templates` (G13).
4. **Strict-scope** load (G5).
5. **`role` column + seed + `get_default_template_for_role` + deterministic role-match** (G9/G10).
6. *(Deferred)* "promote layout → template" endpoint — v1 = edit `_TEMPLATES` + idempotent reseed.

---

## 6. Corrected required-permission mapping (Phase 9 stamps these)

> Rule: gate on the permission the widget's **data hooks actually enforce** (the route's `RoleChecker`), not the feature-folder name. Verified against backend routes.

| typeId | Permission | Data route (perm) |
|---|---|---|
| `project-header` | `project-read` | `/projects/{id}` (project-read) |
| `quick-stats-bar` | `evm-read` | EVM metrics (evm.py:121) |
| `evm-summary` | `evm-read` | evm.py:121 |
| `evm-efficiency-gauges` | `evm-read` | evm.py:121 |
| `evm-trend-chart` | `evm-read` | evm.py:310 |
| `variance-chart` | `evm-read` | evm.py:121 |
| `budget-status` | `evm-read` | evm.py:121 (derived) |
| `health-summary` | `evm-read` | evm.py:121 |
| `forecast` | `evm-read` ⚠️ *(not forecast-read)* | `ForecastComparisonCard` uses `useEVMMetrics`+`useEVMTimeSeries` |
| `cost-history` | `evm-read` ⚠️ *(not cost-event-read)* | `CostHistoryChart.tsx:61` `useEVMTimeSeries` |
| `budget-settings` | `project-budget-settings-read` | `project_budget_settings.py:34` |
| `cost-registrations` | `cost-registration-read` **+ `project-read`** (G15 dual) | `cost_registrations.py:68` + `useProjectCurrency` |
| `change-order-analytics` | `change-order-read` | `change_orders.py:119` (project-scoped) |
| `change-orders-list` | `change-order-read` | `change_orders.py:119` |
| `wbe-tree` ⚠️ *(not wbs-tree)* | `wbs-element-read` | `wbs_elements.py:36` (audience gate; widget makes no call) |
| `mini-gantt` | `cost-element-read` ⚠️ *(not schedule-baseline-read)* | `gantt.py:29` enforces cost-element-read |
| `progress-tracker` | `progress-entry-read` | `progress_entries.py:35` |
| `coq-summary` | `cost-event-read` | `cost_events.py:53` |
| `coq-trend-chart` | `cost-event-read` | `cost_events.py:53` |
| `coq-category-breakdown` | `cost-event-read` | `cost_events.py:53` |
| `coq-work-packages` | `cost-event-read` | `cost_events.py:53` |
| `portfolio-kpi` *(new)* | `portfolio-read` | `/evm/portfolio` (evm.py:46) |
| `portfolio-projects-table` *(new)* | `portfolio-read` | evm.py:46 |
| `portfolio-co-pipeline` *(new)* | **`change-order-read`** | `/change-orders/portfolio-stats` |
| `portfolio-distress-list` *(new)* | `portfolio-read` | evm.py:46 (derived) |

**Consequence:** `viewer` lacks `evm-read` → 9 widgets (`quick-stats-bar, evm-summary, evm-efficiency-gauges, evm-trend-chart, variance-chart, budget-status, health-summary, forecast, cost-history`) lock for it. Any viewer-accessible template must exclude them or show locked placeholders.

---

## 7. Phased implementation plan

Each phase is independently shippable with its own verify. Dependencies noted. *(Backend phases delegate to `backend-developer`; frontend to `frontend-developer` per project policy.)*

| Phase | Goal | Key steps | Verify | Deps |
|---|---|---|---|---|
| **1. Type foundation** | Type layer; no behavior change. | Add `evm-*` to `Permission` (G1); add `requiredPermission?` + `scope?` to `WidgetDefinition` (G15). | `typecheck` clean; project dashboard renders identically; no widget file touched. | — |
| **2. Context-bus scope** | Portfolio-aware bus without breaking 21 project widgets. | Widen props `{projectId?, scope?, portfolioFilter?}`; assert `project ⟹ projectId`; keep `projectId:string` (G2). | `typecheck`; project dashboard identical; `<DashboardContextBus scope="portfolio">` harness exposes scope+filter with `projectId=""`. | 1 |
| **3. Extract shared pieces** *(gate before deletion)* | Move reusables out of the doomed files. | `portfolioWidgetShared.ts`: `MetricMetadata` blocks, `cpiCostDistress` (from `roleLayout.ts:69`), rag helpers (`RED_BAND_THRESHOLD:25`, `ragBand:53`). | `PortfolioPage` still works (transient); shared-module unit tests green. | 2 |
| **4. Build 4 portfolio widgets** | Materialize the typeIds Phases 7/8 depend on. | `PortfolioKpiWidget`, `PortfolioProjectsTableWidget`, `PortfolioChangeOrderPipelineWidget`, `PortfolioDistressListWidget`; register in `registerAll.ts`; **frozen** branch main/merged (G16); widgets read `ctx.portfolioFilter` only. | 25 widgets registered; each renders in a portfolio-scope harness with mocked hooks; pagination lives in the distress widget. | 3 |
| **5. Palette + grid gating (3 paths)** | D2 both halves. | Palette filters by `requiredPermission` + `scope` inside the `useMemo` (G19) + empty-state; `isWidgetPermitted` + `<WidgetPermissionPlaceholder/>` in **all 3** render paths (G3); locked cells keep their slot. | Project palette shows project-scope+permitted only; portfolio palette shows portfolio+permitted only; force-stripped instance → placeholder in-slot, no fetch, no reflow; mobile + fullscreen gated. | 1, 4 |
| **6. Backend persistence correctness** | Global layouts persist for portfolio-read roles; clone-default correct; no scope pollution. | Route guards → requireAny (G4); `clone_template(is_default=)` + clear-default (G8); `scope` query on `/templates` threaded through FE cache key (G13); strict-scope load (G5). | `pytest`: portfolio-only role GET/POST/clone (no 403); `is_default=true` clone clears prior; `?scope=global` returns only global; global layout not in project list. | — |
| **7. D3 backend seed + role column + deterministic role-match** | Role-tagged templates resolvable per user. | `role` column (Alembic) + `DashboardLayoutRead.role`; `get_user_roles` `ORDER BY` (G9); `get_default_template_for_role`; seed 3 templates (G10: Portfolio Overview `role=NULL`, Cost Controlling, PMO Schedule); viewer template dropped/dormant. | `alembic upgrade head`; role-match deterministic; `get_default_template_for_role('cost-controller')` → Cost Controlling; admin/manager → role=NULL; ruff/mypy clean; idempotent reseed. | 4, 6 |
| **8. FE global path + page + FilterBar** | `/portfolio` renders the widget grid. | `useDashboardPersistence(undefined)` (G6) + `project_id: pid ?? null` (G7); first-visit role-default clone; `GlobalDashboardPage`; relocate `FilterBar`→`PortfolioFilterBar`; route swap. | controller@ `/portfolio` first-visit → one `/clone`, `is_default=true`, Cost Controlling widgets; reload → no re-clone; filter flows via context; save persists `project_id=NULL` (key `undefined`); guard prompts. | 5, 6, 7 |
| **9. Stamp mappings** | Per-widget gate on all 25. | Stamp the corrected §6 mapping; `scope:portfolio` on the 4 new widgets. | Cross-check each gate vs the route `RoleChecker`; per-role palette subset correct; viewer locks the 9 evm-read widgets (confirms G1). | 1, 4, 5 |
| **10. Retirement + regression** | Delete the fixed page; full test suite. | Delete the **full** portfolio tree (8 source + 8 test files, G11); add regression tests (G3/G5/G6/G7/G8); grep-verify zero hits on retired symbols. | `lint`+`typecheck` clean; grep zero hits; `/projects/:id/dashboard` still works; `test:coverage` + `pytest` green. | 8, 9 |

---

## 8. Files touched (summary)

**Frontend — modify:** `types/auth.ts` (G1), `features/widgets/types.ts` (D2 fields), `context/DashboardContextBus.tsx` (scope), `components/WidgetPalette.tsx` (gating), `components/DashboardGrid.tsx` (3-path gating), `api/useDashboardPersistence.ts` (global path + null), `api/useDashboardLayouts.ts` (scope), `api/queryKeys.ts` (cache key), `routes/index.tsx` (route swap).
**Frontend — create:** `features/widgets/definitions/{PortfolioKpiWidget,PortfolioProjectsTableWidget,PortfolioChangeOrderPipelineWidget,PortfolioDistressListWidget}.tsx`; `features/widgets/components/PortfolioFilterBar.tsx`; `features/widgets/pages/GlobalDashboardPage.tsx`; `features/portfolio/components/portfolioWidgetShared.ts`.
**Frontend — delete (full tree):** `features/portfolio/{roleLayout.ts, pages/PortfolioPage.tsx, components/FilterBar.tsx, components/PortfolioDateRangePicker.tsx, utils/rag.ts, api/usePortfolioEVM.ts, api/usePortfolioCO.ts}` + `stores/{usePortfolioFilterStore,usePortfolioFilterUrlSync}.ts` + **all** their `__tests__/`.
**Backend — modify:** `api/routes/dashboard_layouts.py` (RBAC + scope query), `services/dashboard_layout_service.py` (`clone_template(is_default=)`, `get_default_template_for_role`, strict-scope, seed), `models/domain/dashboard_layout.py` (`role` column), `models/schemas/dashboard_layout.py` (`role` on Read, `is_default` on Clone), `core/rbac_unified.py` (`get_user_roles` ORDER BY), `db/seed_users_rbac.py` (no change — viewer policy is a decision, not a seed edit).
**Backend — create:** one Alembic revision (`role` column).
**No change:** the 21 project widgets' bodies (the scope/permission additions are registry metadata), `DashboardGrid` layout logic, react-grid-layout config, the registry itself, `/auth/me`.

---

## 9. Resolved decisions (sign-off 2026-06-29)

All items below were open during design; the user signed off on 2026-06-29. The chosen resolution is marked **✓**. Recommendations that were *not* objected to are also marked **✓ (no objection)**.

1. **Viewer role (G10).** `viewer` lacks `portfolio-read` (locked decision) **and** `evm-read`. The D3 "viewer read-only overview" template is unreachable as written. Options: **(a)** *recommended* — drop the viewer template; the `role=NULL` "Portfolio Overview" is served to anyone with `portfolio-read` but no matching role (so viewer simply never reaches `/portfolio`, unchanged from today); **(b)** seed it dormant for forward-compat; **(c)** grant `portfolio-read` to viewer — **contradicts the locked decision, do not do silently**.
2. **Multi-permission widget field (G15).** `requiredPermission: Permission` (single; secondary 403 handled by `WidgetErrorBoundary`) **vs** `Permission | Permission[]` (gate via `hasAllPermissions`). *Recommend the array form* — `CostRegistrationsWidget` genuinely needs both `project-read` and `cost-registration-read`.
3. **"Promote layout → template" interpretation.** The user's words "transform existing layouts into global dashboard templates." *Recommend v1 = edit `_TEMPLATES` + idempotent reseed* (admin/engineer task); defer a runtime `POST /templates` (`dashboard-template-update`) to v2. Confirm this satisfies the ask, or if a runtime promote flow is required for v1.
4. **Locked-placeholder UX (G3).** When a user clones a richer template than their role allows, show locked 403 cards **in-place** (layout stable) — *recommended* — or add a "hide all locked widgets" toggle (out of scope v1). Confirm the in-place default is acceptable.
5. **FilterBar placement.** Host-level control rendered by `GlobalDashboardPage` above the grid (*recommended*, matches D1 "carried in the context") **vs** a pinned always-rendered widget. (Affects whether FilterBar is palette-addable.)

Items I'll resolve as engineering calls (noted for transparency): MiniGantt gates on `cost-element-read` (the route's actual perm, `gantt.py:29`); the FE role→template lookup uses the `role` field already on the templates payload (server-side deterministic, no extra round-trip).

### Sign-off resolutions (2026-06-29)

1. **Viewer role → drop the viewer template ✓.** No `role=viewer` template is seeded. The `role=NULL` "Portfolio Overview" is served to any user with `portfolio-read` but no matching role; viewers still never reach `/portfolio` (respects the locked decision). (G10)
2. **Multi-permission gate → array form ✓.** `requiredPermission?: Permission | Permission[]`, gated via `hasAllPermissions`. `CostRegistrationsWidget` (and any future multi-perm widget) lists both perms. (G15)
3. **"Promote layout → template" → edit `_TEMPLATES` + idempotent reseed ✓ (v1).** No runtime admin endpoint. A future `POST /templates` (`dashboard-template-update`) is deferred to v2. (§9.3)
4. **Locked-placeholder UX → in-place 403 cards ✓ (no objection).** Locked widgets keep their grid cell; a "hide locked widgets" toggle is out of scope for v1. (G3)
5. **FilterBar → host-level control ✓ (no objection).** Rendered by `GlobalDashboardPage` above the grid; not palette-addable. (§9.5)

**All design decisions are now locked. Implementation may proceed phase-by-phase from Phase 1.**

---

## 10. Out of scope / deferred

- A runtime **"promote layout → template"** admin endpoint (v2).
- The **other 3 functional roles** (executive/backoffice/production) and their templates.
- A user-facing **"hide locked widgets"** toggle.
- Auto-generating `auth.ts` `Permission` from `rbac.json` (G1 follow-up).
- Org-unit scoping of the portfolio (carried over from the functional-dashboards deferred list).

---

## Appendix A — Adversarial refutations applied

The verify pass refuted these first-pass design claims; all are folded into the gap register above:

- **"evm-read seeded for every role"** — false; `viewer` lacks it (and `portfolio-read`).
- **"forecast → forecast-read"** / **"cost-history → cost-event-read"** — false; both are `evm-read` (G14).
- **"widen `projectId` to `string|undefined`, rely on guards"** — would break ~13 typed call sites (G2).
- **"no backend changes for persistence"** — false; route RBAC split (G4) + clone-default bug (G8).
- **"`projectId:''` works as the global sentinel"** — self-contradictory; `''` 422s (G7) and splits the cache key (G6). Must be `undefined`.
- **"seed returns 3 rows"** while seeding 4; and "Portfolio Overview is both `role='manager'` and the `role=NULL` fallback" — contradictions (G10).
- **"`clone_template` clears prior default via `create()`"** — false; it bypasses `create()` (G8).
- **"`roles[0]` is safe for multi-role users"** — non-deterministic (G9).
- **"schema file could not be located"** — it exists at `schemas/dashboard_layout.py:14` (G7).
- **Mobile + fullscreen render paths** for gating were missed (G3); **`getAllWidgetDefinitions` outside `useMemo`** perf (G19); **global→project layout pollution** (G5); **TimeMachine cross-scope leak** (G16); **full retirement tree** (G11/G12) — all surfaced by verification.
