# Glossary

**Last Updated:** 2026-03-02
**Purpose:** Define domain terms, acronyms, and naming conventions

> **This is the authoritative reference** for terminology in Backcast EVS.
> All documentation and code should follow these conventions.

---

## Naming Conventions

### Entity Names

| Context | Format | Example |
|---------|--------|---------|
| **UI/Documentation** | Title Case with space | "Cost Element", "Work Breakdown Element" |
| **Code (classes)** | PascalCase | `CostElement`, `WorkBreakdownElement` |
| **API/Database** | snake_case | `cost_element`, `work_breakdown_element` |
| **Variables** | snake_case | `cost_element_id`, `wbe_code` |

### Branch Mode Names

| Use | Correct | Incorrect |
|-----|---------|-----------|
| Code/Docs | `merge`, `strict` | `MERGE`, `STRICT`, `merged`, `isolated` |
| Display | "Merge mode", "Strict mode" | "Merged mode", "Isolated mode" |

### Temporal Parameter Names

| Parameter | Use Case | Description |
|-----------|----------|-------------|
| `as_of` | Read operations | Time-travel timestamp for queries |
| `control_date` | Write operations | Effective date for mutations |
| `valid_from` / `valid_to` | Data model | Temporal validity range |

> **Important:** Do NOT use `control_date` for read operations. Use `as_of` consistently.

---

## Standardized Terminology

The following terms shall be used consistently across all project documentation:

**Earned Value Management Terms:**

- "Percent Complete" (preferred) - Use instead of "Physical Completion" or "% di completamento"
- "Earned Value (EV)" - Use instead of "EV Calculation"
- "Gaussian Progression" (capitalized) - Use instead of "gaussian" (lowercase)
- "Cost Performance Index (CPI)" - Always use full term on first use in each section
- "Schedule Performance Index (SPI)" - Always use full term on first use in each section

**Quality Terms:**

- "Quality Event" (preferred) - Use instead of "Quality Incident"

**Branching Terms:**

- "Source Branch" - The branch from which a change order branch is forked
- "Target Branch" - The branch receiving merged changes (typically main)
- "Branch States: Active, Locked, Archived" - Use these exact terms (not "merged")

**Financial Terms:**

- "Budget at Completion (BAC)" - Always use full term on first use
- "Estimate at Completion (EAC)" - Always use full term on first use
- "Estimate to Complete (ETC)" - Always use full term on first use
- "Variance at Completion (VAC)" - Always use full term on first use

**Date/Time Terms:**

- "Control Date" - The temporal reference point for time machine queries
- "Registration Date" - When a record was created or took effect
- "Baseline Date" - The date a baseline snapshot was taken

---

## Project Structure Terms

**Project**  
Top-level container for all financial and structural data. Represents a complete customer order for end-of-line automation equipment.

**Work Breakdown Element (WBE)**  
Individual machine or major deliverable sold to customer within a project. Primary organizational unit for budget allocation and performance measurement.

**Cost Element**  
Represents a specific department or discipline responsible for delivering portions of work within a WBE. Most granular level of budget tracking and cost imputation.

**Branch**  
Isolated workspace for modifying project data. Types: main (production), BR-{id} (change orders).

**Control Date**  
Selected date determining what data is visible/calculable. Supports time-travel queries.

---

## Financial Terms

**BAC (Budget at Completion)**  
Total planned budget for work scope. Sum of all allocated budgets adjusted for approved changes.

**EAC (Estimate at Completion)**  
Expected total cost at project completion based on current performance and forecasts.

**ETC (Estimate to Complete)**  
Expected cost to finish remaining work. Calculated as `EAC - AC`.

**Baseline**  
Snapshot of project data at a specific milestone, used for variance tracking and performance measurement.

**Performance Measurement Baseline (PMB)**  
Time-phased budget plan against which performance is measured (EVM compliance).

---

## EVM Metrics

> **For detailed formulas and calculations**, see: [EVM Requirements](./evm-requirements.md)

**PV (Planned Value) / BCWS** - Authorized budget assigned to scheduled work.

**EV (Earned Value) / BCWP** - Budgeted cost of work actually performed.

**AC (Actual Cost) / ACWP** - Realized cost incurred for work performed.

**BAC (Budget at Completion)** - Total planned budget for work scope.

**EAC (Estimate at Completion)** - Expected total cost at project completion.

**CPI (Cost Performance Index)** - Cost efficiency: `EV / AC`. >1 = under budget, <1 = over budget.

**SPI (Schedule Performance Index)** - Schedule efficiency: `EV / PV`. >1 = ahead, <1 = behind.

**CV (Cost Variance)** - Cost difference: `EV - AC`. Negative = over budget.

**SV (Schedule Variance)** - Schedule difference: `EV - PV`. Negative = behind schedule.

**VAC (Variance at Completion)** - Final variance: `BAC - EAC`.

**TCPI (To Complete Performance Index)** - Required performance on remaining work.

---

## Versioning Terms

> **For implementation details**, see: [Temporal Query Reference](../02-architecture/cross-cutting/temporal-query-reference.md)

**Valid Time** - When the fact was true in the real world (business perspective).

**Transaction Time** - When the fact was recorded in the database (audit perspective).

**Time Travel** - Query entity state at any historical point using `as_of` parameter.

**Branch Isolation** - Each branch maintains separate timelines (main vs BR-{id}).

**Merge** - Apply branch changes to main. Atomic operation (all-or-nothing).

---

## Change Order Terms

**Change Order**  
Formal request to modify project scope, budget, or schedule. Creates isolated branch for safe experimentation.

**Change Order Branch**  
Isolated workspace (`BR-{id}`) where change order modifications are made before merging to main.

**Branch Lock**  
Prevents modifications to a branch. Used when branch should be read-only (e.g., under review).

**Impact Analysis**  
Assessment of change order effects on budgets, schedules, and EVM metrics before approval.

**Merged View**  
Unified display showing entities from both main and branch with change status indicators (unchanged/created/updated/deleted).

---

## Quality Management Terms

**Quality Event**  
Incident requiring additional costs without corresponding revenue increase. Examples: rework, defect correction, warranty work.

**Cost of Quality**  
Total costs attributable to quality events as percentage of total project costs.

**Root Cause**  
Fundamental reason a quality event occurred. Used for analysis and process improvement.

---

## Event Terms

**Event**  
Any data change in the system: cost registration, forecast update, change order, quality event, baseline creation.

**Event Date**  
User-defined date when event occurred or became effective (distinct from creation timestamp).

**Audit Trail**  
Permanent record of all data changes: what, who, when, why. Immutable and non-deletable.

---

## Forecast Terms

**Forecast Type**  
Method used to create forecast:

- **Bottom-Up:** Detailed estimation from ground up
- **Performance-Based:** Using historical <|CURSOR_LOCATION|>performance trends (e.g., CPI)
- **Management Judgment:** Expert opinion/experience

**Forecast Date**  
Date when forecast was created. Must be in past. Maximum 3 per cost element.

---

## Schedule Terms

**Progression Type**  
How planned work is distributed over time:

- **Linear:** Even distribution
- **Gaussian:** Bell curve, peak at midpoint
- **Logarithmic:** Slow start, accelerating finish

**Schedule Baseline**  
Versioned record defining when work is planned. Determines PV calculations.

**Registration Date**  
Date when schedule registration was recorded. System uses latest registration ≤ control date.

---

## User Roles

**System Administrator**  
Full system access for configuration and maintenance.

**Project Manager**  
Full access to assigned projects.

**Department Manager**  
Access to department-specific cost elements.

**Project Controller**  
Read-only access for reporting and analysis.

**Executive Viewer**  
Access to summary dashboards and executive reports.

---

## Acronyms

| Acronym | Full Term |
|---------|-----------|
| AC | Actual Cost |
| ACWP | Actual Cost of Work Performed |
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| BAC | Budget at Completion |
| BCWP | Budgeted Cost of Work Performed |
| BCWS | Budgeted Cost of Work Scheduled |
| BOM | Bill of Materials |
| CPI | Cost Performance Index |
| CRUD | Create, Read, Update, Delete |
| CV | Cost Variance |
| EAC | Estimate at Completion |
| ETC | Estimate to Complete |
| EV | Earned Value |
| EVCS | Entity Version Control System |
| EVM | Earned Value Management |
| FK | Foreign Key |
| PDCA | Plan-Do-Check-Act |
| PII | Personal Identifiable Information |
| PK | Primary Key |
| PMB | Performance Measurement Baseline |
| PRD | Product Requirements Document |
| PV | Planned Value |
| RBAC | Role-Based Access Control |
| SPI | Schedule Performance Index |
| SV | Schedule Variance |
| TCPI | To Complete Performance Index |
| TDD | Test-Driven Development |
| VAC | Variance at Completion |
| WBE | Work Breakdown Element |

---

**See Also:**

- [Functional Requirements](functional-requirements.md) - Detailed system requirements
- [EVM Requirements](evm-requirements.md) - EVM calculations and formulas
