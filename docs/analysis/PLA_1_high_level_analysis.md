# PLA-1 Time Machine High-Level Analysis

## User Story & Objective
As a project controller, I want to choose a “time machine” date so that every dashboard, report, and metric reflects the portfolio state as of that date (defaulting to today), allowing me to simulate historical or future control dates.

## Codebase Pattern Analysis
1. **Control-Date Driven Metrics** – The earned/planned value stacks already rely on explicit `control_date` inputs that travel from FastAPI query params through service helpers such as `calculate_planned_value()` and `_select_latest_entry_for_control_date()` to clamp data to a cutoff date (`backend/app/services/planned_value.py`, `backend/app/services/earned_value.py`; API routes in `backend/app/api/routes/earned_value.py`). These demonstrate how date parameters propagate through routers → services → SQLModel queries without mutating persistent state.
2. **Snapshot-Oriented Baselines** – The Baseline subsystem captures immutable snapshots keyed by `baseline_date` via `BaselineLog`/`BaselineCostElement` (`backend/app/models/baseline_log.py`), reinforcing an architectural preference for historical views that piggyback on stamped dates instead of duplicating live tables.
3. **Frontend Global Filters via React Query** – UI surfaces such as `BudgetTimeline` compose `react-query` keys from filter inputs and feed them into ChartJS datasets (`frontend/src/components/Projects/BudgetTimeline.tsx`). Local UI preferences live in hooks like `useTablePreferences` (localStorage-backed), while top-level chrome resides in `Navbar` with `UserMenu` controls. This shows an established pattern for shared UI state propagated via hooks + query keys, but there is no existing global date picker.

## Integration Touchpoints
- **Docs** – Add explicit requirements to `docs/prd.md`, `docs/plan.md`, and `docs/project_status.md` describing the time-machine UX, backend storage, and sprint tracking.
- **Frontend shell** – `Navbar.tsx` (and potentially a new `TimeMachineControl` component) must render the date picker next to `UserMenu`, persist selection, and broadcast it (context or global store) so every `react-query` request can include the chosen control date.
- **API client & hooks** – Generated schemas/services (`frontend/src/client`) and fetch hooks must accept the session control date (query param, header, or implicit server lookup) to keep caches scoped per date.
- **Backend session management** – Need a persistence layer for “session field” (new column/table keyed by user/session) plus FastAPI dependency/middleware that resolves the current time-machine date (default today) for every request.
- **Data filters** – Each route that returns mutable entities (projects, WBEs, cost elements, cost regs, earned value, baselines, forecasts, change orders, etc.) must respect the resolved time-machine date by filtering on `created_at`, `updated_at`, `registration_date`, or `baseline_date` before computing aggregates.
- **Testing** – Pytest suites covering services/routes plus frontend Vitest/Playwright specs need new cases for non-default dates.

## Abstraction Inventory
- **Dependency injection** – `SessionDep`/`get_current_user` (in `backend/app/api/deps.py`) centralize DB + auth injection; a similar dependency can expose `get_time_machine_date()`.
- **Service layer** – `app/services/planned_value.py` and `earned_value.py` already encapsulate date-based logic and can be extended/reused for the time machine cutoffs.
- **UI scaffolding** – Chakra-based navbar + custom menu primitives (`frontend/src/components/Common/Navbar.tsx`, `../ui/menu`) provide the placement for the new control, while hooks like `useTablePreferences` illustrate how to persist per-user UI settings locally if we need optimistic caching before the backend session writes succeed.
- **Docs & analysis framework** – Existing PLA/E3/E4 analysis/plans under `docs/analysis`/`docs/plans` show how to document phased delivery; the same template can be reused for this feature.

## Alternative Approaches
| Option | Summary | Pros | Cons / Risks | Alignment |
| --- | --- | --- | --- | --- |
| **A. Client-only control date (query param/localStorage)** | Store date in a React context + localStorage, append it to every API call. | Minimal backend change, leverages existing `react-query` patterns. | Violates requirement to “store in a session field”; backend can’t enforce filtering if callers omit the param. | Low (doesn’t meet spec). |
| **B. Server-side session preference** | Add `user_time_machine` table or extend `User` with `time_machine_date`, expose REST endpoints to update it, and inject it per request. | Meets requirement, single source of truth, backend can enforce filtering even for legacy clients. | Requires schema migration, auth-aware middleware, and audit of every route/service to honor the cutoff; large blast radius. | High (preferred). |
| **C. Hybrid header + cached session** | Frontend sends `X-Time-Machine-Date`; backend middleware persists last value in session store and uses header if present. | Flexible, opt-in per request, easier gradual adoption. | Still needs session persistence; header must be trusted and validated; more moving parts. | Medium (could satisfy spec if “session field” interpreted loosely). |

## Architectural Impact & Considerations
- **Cross-cutting concern** – Introducing a global “control date” effectively adds a new dimension to every query; missing one endpoint would yield inconsistent pages, so we likely need shared filters at repository/service layer or database views.
- **Authentication coupling** – Because the app uses stateless JWT auth (`useAuth` + bearer tokens), implementing “session fields” means either reintroducing server-side sessions or modelling the preference directly on the `User` entity. This impacts token invalidation strategy (e.g., updates should not require token refresh).
- **Performance & caching** – `react-query` cache keys must incorporate the date to avoid mixing data from different control dates. Backend queries may need composite indexes on `(created_at, updated_at)` to keep filters performant.
- **Testing footprint** – Need regression tests verifying that e.g., earned value endpoints now default to “today” but change behavior when the session date is rewound; also end-to-end tests to ensure the navbar control changes downstream pages.

## Risks & Unknowns
1. **Scope of filtering** – Requirement says “show only data with creation, modification, registration date, baseline date prior to that,” but does this include budgets (which may have both creation and effective dates), forecasts, and change orders? Clarify which timestamp drives eligibility for each entity (created_at vs. event_date vs. effective_date).
2. **Session storage definition** – There is no existing server session infrastructure; need confirmation whether augmenting `User` (persist preference) is acceptable or if a dedicated session table / Redis cache is expected.
3. **Future-date semantics** – For future dates, should we project planned/forecasted values beyond recorded data (e.g., PV already handles future control dates) while still hiding cost registrations that haven’t occurred? Need explicit rules to avoid contradictory outputs.
4. **Write operations** – If the UI is rewound to the past, can users still create/edit records? If yes, should those writes respect the time machine (e.g., default dates) or always use real “today”? This impacts validation flows.
5. **Baseline vs. operational data precedence** – Baseline snapshots are immutable; when the control date predates the most recent baseline, should the UI show the latest available baseline ≤ control date or hide future baselines entirely?

## Next Steps
- Confirm how “session field” should be implemented (user column vs. dedicated table vs. cache) and which entity timestamps govern filtering per model.
- Once clarified, proceed with detailed planning (TDD phases, migrations, frontend context design) before implementation.
