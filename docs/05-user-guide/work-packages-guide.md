# Work Packages User Guide

**Version:** 3.0
**Last Updated:** 2026-05-30
**Target Audience:** Project Managers, Cost Engineers, Control Account Managers

---

## Table of Contents

1. [Introduction](#introduction)
2. [How Work Packages Work in Backcast](#how-work-packages-work-in-backcast)
3. [Creating and Managing Work Packages](#creating-and-managing-work-packages)
4. [Work Package Sub-Resources](#work-package-sub-resources)
5. [Cost Events and Cost of Quality (COQ)](#cost-events-and-cost-of-quality-coq)
6. [EVM Integration](#evm-integration)
7. [Summary Card](#summary-card)
8. [Standards References](#standards-references)

---

## Introduction

### What are Work Packages?

Work Packages are the lowest-level budget holders in Backcast's ANSI-748 Work Breakdown Structure. Each Work Package sits under a Control Account and holds an allocated budget (`budget_amount`). Every Work Package is created with a linked **Schedule Baseline** (planned-value curve) and a **Forecast** (Estimate at Complete); the creation parameters set their values, and sensible defaults are applied when they are omitted. Work Packages contain Cost Elements, against which actual costs (Cost Registrations) are tracked.

The hierarchy is:

```
Project > WBSElement > ControlAccount > WorkPackage > CostElement > CostRegistration
```

Control Accounts represent the intersection of *what* (WBS Element) and *who* (Organizational Unit). Work Packages decompose each Control Account into manageable budget units for earned value management.

### Why Work Packages Matter

In ANSI-748/EVM systems, the Work Package is the fundamental unit of planning and control:

- **Budget allocation**: Each Work Package holds a specific budget amount, enabling granular cost control
- **Schedule baseline**: Every Work Package has a Schedule Baseline defining the planned value curve (linear, Gaussian, or logarithmic progression) — created automatically with the work package
- **Forecasting**: Every Work Package has a Forecast (Estimate at Complete) for projected final cost — created automatically with the work package
- **EVM computation**: Cost Performance Index (CPI) and Schedule Performance Index (SPI) are computed at the Work Package level from its Cost Elements and their Cost Registrations
- **Progress tracking**: Progress Entries record physical percent complete against Work Packages

### Relationship to Cost Events

Cost Events are a separate entity that tracks quality and cost events at the project level (e.g., NCRs, site visits, warranty claims). Cost Events have their own COQ (Cost of Quality) tracking. Cost Registrations optionally link to a Cost Event via `cost_event_id` for event-based cost grouping. See the [Cost Events and Cost of Quality (COQ)](#cost-events-and-cost-of-quality-coq) section below.

### From Quality Impacts to the Current Model

Quality Impacts were the original quality event tracking entity. They were refactored into Cost Events with configurable Cost Event Types. Work Packages are a separate ANSI-748 concept representing budget holders under Control Accounts, not a generalization of Quality Impact.

---

## How Work Packages Work in Backcast

### Key Architectural Concept: Work Packages Are Budget Holders

Work Packages hold budget (`budget_amount`) and contain Cost Elements. Cost Registrations track actual costs against Cost Elements. EVM metrics (CPI, SPI) are computed at the Work Package level from its Cost Elements and their Cost Registrations.

- Work Package costs automatically flow into EVM Actual Cost calculations via their child Cost Elements
- CPI and SPI reflect the combined performance of all Cost Elements within the Work Package
- The financial status of any Work Package is traceable to specific Cost Elements and their Cost Registrations
- Separately, Cost Events provide event-based cost grouping via `cost_event_id` on Cost Registration

### Data Model

```
WorkPackage [Tier 3: Branchable] (ANSI-748 budget holder under ControlAccount)
  |-- work_package_id         --> Root ID (stable identity across versions and branches)
  |-- control_account_id      --> Parent Control Account root ID (required)
  |-- name                    --> Human-readable label (required)
  |-- code                    --> Work Package code (required, max 50 chars)
  |-- budget_amount           --> Allocated budget (DECIMAL 15,2, required, default 0)
  |-- description             --> Optional details about the package
  |-- status                  --> Lifecycle state, default "open"
  |-- schedule_baseline_id    --> 1:1 reference to schedule baseline (always linked)
  |-- forecast_id             --> 1:1 reference to forecast (always linked)
  +-- [branchable]            --> Full EVCS bitemporal versioning with change order branching

CostElement [Tier 2: Versionable] (child of WorkPackage)
  |-- cost_element_id         --> Root ID
  |-- work_package_id         --> Parent Work Package root ID (required)
  |-- cost_element_type_id    --> Cost Element Type root ID (required)
  |-- amount                  --> Allocated amount (DECIMAL 15,2)
  +-- [versioned]

CostRegistration [Tier 2: Versionable] (actual cost against a CostElement)
  |-- cost_registration_id    --> Root ID
  |-- cost_element_id         --> Cost Element root ID (required)
  |-- cost_event_id           --> Optional CostEvent root ID (NULL = not event-linked)
  |-- amount                  --> The actual cost incurred
  |-- registration_date       --> Business date incurred
  +-- [versioned, not branchable]

CostEvent [Tier 2: Versionable] (project-scoped quality/cost event tracker)
  |-- cost_event_id           --> Root ID
  |-- project_id              --> Parent project root ID (required)
  |-- cost_event_type_id      --> CostEventType root ID (required)
  |-- name                    --> Event label (required)
  |-- external_event_id       --> External reference ID (e.g., QMS ID, PO number)
  |-- event_date              --> When the event occurred
  |-- coq_category            --> COQ category: prevention, appraisal, internal_failure, external_failure
  |-- estimated_impact        --> Estimated financial impact (DECIMAL 15,2, default 0)
  |-- schedule_impact_days    --> Schedule delay in days
  +-- [versioned, not branchable]
```

The cost flow is: WorkPackage (budget) -> CostElement (budget line) -> CostRegistration (actual cost). Event-based grouping uses CostEvent -> CostRegistration (via `cost_event_id`).

### Versioning and Branching

Work Packages are **Branchable (Tier 3)**: They support full change order branching alongside versioning. Work Packages can be modified in change order branches for what-if analysis of budget reallocation. When a change order is merged, Work Package changes are merged back to the main branch.

Note: Cost Events and Cost Registrations are Versionable (Tier 2) but NOT Branchable. They are financial facts that exist globally across all branches.

### Status Lifecycle

Work packages have a simple two-state lifecycle:

- **Open** -- Costs can be posted and the package is actively tracking. Budget can be adjusted.
- **Closed** -- Read-only. No further cost postings. Used for completed packages.

The status field (`String(20)`, default `open`) can be extended via migration if more granular states are required.

---

## Creating and Managing Work Packages

### Step-by-Step Guide

1. **Navigate to the Control Account**: Open the Control Account under which you want to create a Work Package.

2. **Click "Add Work Package"**: This opens the Work Package creation form.

3. **Fill in the required fields**:

   | Field | Description | Required | Example |
   |---|---|---|---|
   | Name | Human-readable label for the work package | Yes | `Column Base Plate Assembly` |
   | Code | Work Package code (unique within the Control Account) | Yes | `WP-1.2.3.01` |
   | Budget Amount | Allocated budget for this work package | Yes | `EUR 25,000.00` |
   | Description | Optional details | No | `Final assembly and testing of column base plates` |
   | Status | Open or Closed (defaults to Open) | No | `Open` |

4. **Click "Create"**: The work package is saved and immediately reflected in the Control Account's budget summary.

5. **Add Cost Elements**: After creation, add Cost Elements to break down the budget by cost type (labor, material, subcontract, etc.). Each Cost Element references a Cost Element Type and has an allocated amount.

6. **Schedule Baseline (created automatically)**: A schedule baseline is created with the work package and defines the planned value curve (start/end dates and progression type: linear, Gaussian, or logarithmic). Provide start/end dates at creation to control it; defaults (control date as start, start + 90 days as end) are used otherwise.

7. **Forecast (created automatically)**: A forecast is created with the work package and defines the Estimate at Complete (EAC) with a basis of estimate. Provide `eac_amount` at creation to control it; it defaults to the work package's `budget_amount` otherwise.

### Editing Work Packages

To edit an existing work package:

1. Click the edit icon (pencil) on the package row in the table.
2. Modify any field in the modal form.
3. Click "Save" to create a new version. The previous version is preserved in history.

### Changing Status

To open or close a work package:

1. Click the status toggle on the package row.
2. Closing a package makes it read-only -- no further cost postings can be linked to its Cost Elements.

### Viewing Version History

Work Packages support full bitemporal versioning with branch support. To view the history of changes:

1. Click the history icon (clock) on the package row.
2. The Version History drawer opens, showing all versions with timestamps and field changes.

### Deleting Work Packages

Deletion is a soft-delete operation. The work package is marked as deleted but preserved in the history for audit purposes. To delete:

1. Click the delete icon (trash) on the package row.
2. Confirm the deletion in the pop-up dialog.

### Viewing the Breadcrumb

To see the full hierarchy path of a Work Package:

- The breadcrumb endpoint returns the path from Project through WBS Element and Control Account to the Work Package.

### Permissions

Work Package operations require the following RBAC permissions:

| Operation | Required Permission |
|---|---|
| View work packages | `work-package-read` |
| Create work packages | `work-package-create` |
| Edit work packages | `work-package-update` |
| Delete work packages | `work-package-delete` |

---

## Work Package Sub-Resources

### Schedule Baseline

Each Work Package can have one Schedule Baseline that defines the planned value curve:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/work-packages/{work_package_id}/schedule-baseline` | GET | Get the current schedule baseline |
| `/api/v1/work-packages/{work_package_id}/schedule-baseline` | POST | Create a new schedule baseline |
| `/api/v1/work-packages/{work_package_id}/schedule-baseline/{baseline_id}` | PUT | Update a schedule baseline |
| `/api/v1/work-packages/{work_package_id}/schedule-baseline/{baseline_id}` | DELETE | Delete a schedule baseline |

Schedule Baseline fields: `name`, `start_date`, `end_date`, `progression_type` (LINEAR, GAUSSIAN, or LOGARITHMIC), and optional `description`.

### Forecast

Each Work Package can have one Forecast (Estimate at Complete):

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/work-packages/{work_package_id}/forecast` | GET | Get the current forecast |
| `/api/v1/work-packages/{work_package_id}/forecast` | PUT | Update the forecast |
| `/api/v1/work-packages/{work_package_id}/forecast` | DELETE | Delete the forecast |

Forecast fields: `eac_amount` (Estimate at Complete), `basis_of_estimate`, `approved_date`, `approved_by`.

### EVM Metrics

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/work-packages/{work_package_id}/evm` | GET | Get EVM metrics (CPI, SPI, etc.) for this work package |

### Cost Elements

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/work-packages/{work_package_id}/cost-elements` | GET | List cost elements for this work package |
| `/api/v1/work-packages/{work_package_id}/cost-elements` | POST | Create a cost element under this work package |

### Budget Status

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/work-packages/{work_package_id}/budget-status` | GET | Get budget vs. actual status for this work package |

### Breadcrumb

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/work-packages/{work_package_id}/breadcrumb` | GET | Get the full hierarchy path |

---

## Cost Events and Cost of Quality (COQ)

Cost Events are a separate entity from Work Packages. They track quality and cost events at the project level with configurable Cost Event Types and COQ (Cost of Quality) fields.

### Cost Event Types

Cost Event Types are configurable admin reference data. Each type has:

| Field | Description | Example |
|---|---|---|
| Code | Type code | `ncr` |
| Name | Display name | `Nonconformance Report` |
| Color | Ant Design color name | `red` |
| Is Quality | Whether this type contributes to COQ metrics | `true` |
| Description | Optional details | `Quality-related nonconformance event` |

Types are configurable by admins via `/api/v1/cost-event-types` endpoints. The `is_quality` flag determines whether events of that type are included in COQ metric calculations.

### COQ Categories

Cost Events use four granular P-A-F (Prevention-Appraisal-Failure) values in the `coq_category` field:

| Category | P-A-F Group | Description |
|---|---|---|
| `prevention` | Conformance | Training, quality planning, process design, process control |
| `appraisal` | Conformance | Inspection, testing, audits, measurement equipment calibration |
| `internal_failure` | Nonconformance | Rework, scrap, retest, design changes (found before delivery) |
| `external_failure` | Nonconformance | Warranty claims, returns, field repairs, litigation (found after delivery) |

Prevention + Appraisal = conformance costs. Internal failure + External failure = nonconformance costs.

### The P-A-F Model

The Prevention-Appraisal-Failure (P-A-F) model, formalized in ASQ TR 2:2018, classifies quality costs into the four categories above:

```
Cost of Quality (COQ)
|
|-- Conformance Costs (cost of good quality)
|   |-- Prevention:  Training, quality planning, process design, process control
|   |-- Appraisal:   Inspection, testing, audits, measurement equipment calibration
|
|-- Nonconformance Costs (cost of poor quality)
    |-- Internal Failure: Rework, scrap, retest, design changes (found before delivery)
    |-- External Failure: Warranty claims, returns, field repairs, litigation (found after delivery)
```

#### Conformance Costs (Cost of Good Quality)

These are investments made to *prevent* defects from occurring and to *detect* them early:

- **Prevention costs** -- Activities that eliminate the root causes of potential defects. Examples: quality training programs, process design reviews, supplier qualification, statistical process control.
- **Appraisal costs** -- Activities that verify conformance to requirements. Examples: incoming inspection, in-process testing, final acceptance testing, quality audits.

Conformance costs are controllable investments. Increasing prevention spend typically reduces failure costs at a greater rate, yielding net savings.

#### Nonconformance Costs (Cost of Poor Quality)

These are the costs incurred when defects *do* occur:

- **Internal failure costs** -- Defects found before the product or deliverable reaches the customer. Examples: rework labor, scrapped material, retesting after corrective action, engineering change orders.
- **External failure costs** -- Defects found after delivery to the customer. Examples: warranty claims, field service calls, product returns, legal liability, reputational damage.

Nonconformance costs represent waste. They consume budget without producing value.

### The Optimal Quality Level

The COQ model reveals that total quality cost follows a U-shaped curve:

- At low quality investment: failure costs dominate (rework, scrap, warranty).
- At high quality investment: prevention/appraisal costs dominate.
- The optimal point lies where the marginal cost of prevention equals the marginal cost of failures avoided.

Industry benchmarks from ASQ suggest:

| Organization Maturity | COQ as % of Revenue | Typical Profile |
|---|---|---|
| Immature | 30 -- 40% | Failure costs dominate |
| Average | 20 -- 25% | Mixed |
| Mature (world-class) | 15 -- 20% | Prevention/appraisal dominate |

### Cost Event Quality-Specific Fields

When a CostEvent is associated with a CostEventType where `is_quality = True`, the following fields are populated:

| Field | Description | Required | Example |
|---|---|---|---|
| `coq_category` | One of: `prevention`, `appraisal`, `internal_failure`, `external_failure` | Required for quality events | `internal_failure` |
| `external_event_id` | External reference (e.g., QMS ID, PO number, work order) | No | `NCR-2026-0042` |
| `estimated_impact` | Estimated financial impact (DECIMAL 15,2) | Yes (default 0) | `EUR 12,500.00` |
| `schedule_impact_days` | Schedule delay in days | No | `5` |
| `event_date` | When the event occurred | No | `2026-03-15` |

### COQ Metrics

Backcast provides the following COQ metrics for Cost Events, drawing on the EVMq framework (Ahmed & Afifi, CSCE 2018) which integrates quality measures into earned value management.

All COQ metrics are computed by filtering Cost Events where the associated CostEventType has `is_quality = True`.

#### Metric Definitions

| Metric | Formula | Meaning |
|---|---|---|
| **Total COQ** | Sum of all quality Cost Event estimated impacts | Total quality spend across both conformance and nonconformance |
| **CPQ** (Cost of Poor Quality) | Sum of nonconformance Cost Event impacts | Failure costs only |
| **CCQ** (Cost of Conformance Quality) | Sum of conformance Cost Event impacts | Prevention and appraisal costs only |
| **CPQ%** | `CPQ / Total AC * 100` | Quality failure share of total project spend |
| **CPIq** | `CPQ / AC` | Quality's share of cost variance -- how much of the total cost overrun is quality-related |
| **COQ Ratio** | `Total COQ / Project Budget * 100` | Quality cost burden relative to project budget |
| **QPI** (Quality Performance Index) | Normalized from CPQ% | Single quality health score |

These metrics are available via the following endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/cost-events/project/{project_id}/coq-metrics` | GET | COQ metrics for the project |
| `/api/v1/cost-events/project/{project_id}/coq-trend` | GET | COQ metrics trend over time |
| `/api/v1/cost-events/project/{project_id}/summary` | GET | Cost Event summary for the project |

#### Quality Performance Index (QPI)

The QPI, based on the scoring methodology by Nassar (2009), translates CPQ% into a single index value that is comparable across projects:

| CPQ% Range | QPI Value | Rating | Interpretation |
|---|---|---|---|
| <= 0.5% | > 1.15 | Outstanding | Quality costs are negligible relative to project spend |
| 0.5% -- 1.0% | 1.05 -- 1.15 | Exceeds Target | Quality management is highly effective |
| 1.0% -- 2.0% | 0.95 -- 1.05 | Within Target | Quality performance is acceptable |
| 2.0% -- 4.0% | 0.85 -- 0.95 | Below Target | Quality failures are eroding project margins |
| > 4.0% | <= 0.85 | Poor Performance | Urgent corrective action required |

#### Using These Metrics

**For project managers:**

- Monitor **CPQ%** weekly. A rising trend indicates accumulating quality failures.
- Use **CPIq** to quantify quality's contribution to cost variance. If CPIq = 8.3%, then 8.3% of your total actual cost is quality failure cost.
- Track the **COQ Ratio** to benchmark against industry norms (15--20% for mature organizations, 30--40% for immature).
- Use **QPI** for cross-project comparison and portfolio-level quality reporting.

**For quality managers:**

- Compare conformance vs. nonconformance costs. A healthy ratio shows more investment in prevention/appraisal than in failures.
- Use External Event IDs to trace Backcast quality costs back to the QMS for root cause analysis.
- Review Cost Event allocations to identify which cost elements are most affected by quality events.

---

## EVM Integration

### How Quality Costs Flow Into Earned Value

Per the PMI Practice Standard for EMA (Earned Value Management), quality costs are a legitimate component of Actual Cost (AC). Backcast follows this principle:

1. Quality costs are recorded as Cost Events with estimated impacts and optional Cost Registration allocations.
2. These costs contribute to the project's total actual expenditure via Cost Registrations against Cost Elements.
3. CPI (Cost Performance Index) naturally reflects quality failures -- this is correct and intentional per PMI best practice.
4. CPIq isolates the quality-related portion of cost variance.

### The Project Health Triangle

Backcast presents three indices together to give a complete project health picture:

- **CPI** (Cost Performance Index): `EV / AC` -- overall cost efficiency
- **SPI** (Schedule Performance Index): `EV / PV` -- schedule efficiency
- **QPI** (Quality Performance Index): derived from CPQ% -- quality health

A project in good shape has all three indices near or above 1.0. A project with good CPI but poor QPI may be hitting budget targets by skipping quality activities -- a false economy.

### Worked Example

Consider a manufacturing automation project:

| Parameter | Value |
|---|---|
| Project Budget (BAC) | EUR 500,000 |
| Actual Cost (AC) | EUR 420,000 |
| Earned Value (EV) | EUR 380,000 |
| Quality costs (CPQ) | EUR 35,000 |

**Standard EVM calculation:**

```
CPI = EV / AC = 380,000 / 420,000 = 0.905
```

A CPI of 0.905 means the project is over budget -- every EUR 1.00 of budget is producing only EUR 0.91 of earned value.

**COQ analysis:**

```
CPIq = CPQ / AC = 35,000 / 420,000 = 0.083 (8.3%)
```

8.3% of the total actual cost is quality failure cost. To understand the project's cost performance *without* quality failures:

```
AC without quality failures = 420,000 - 35,000 = 385,000
CPI without quality failures = 380,000 / 385,000 = 0.987
```

This reveals that the project's underlying cost performance (CPI = 0.987) is nearly on target. The quality failures are responsible for most of the CPI degradation (from 0.987 to 0.905). The corrective action should focus on quality improvement rather than general cost reduction.

### Practical Implications

- **Do not try to remove quality costs from AC.** Per PMI standards, all quality costs belong in AC. Hiding them would produce misleading CPI values.
- **Use CPIq to prioritize.** When CPIq is high, fix quality. When CPIq is low and CPI is still poor, the problem is elsewhere (estimating, scope, productivity).
- **Track trends, not snapshots.** A single CPQ% measurement has limited value. The trend over time reveals whether quality improvement initiatives are working.

---

## Summary Card

### Work Package Budget Summary

The Work Package view displays a budget summary card showing:

| Metric | Description |
|---|---|
| **Budget Amount** | The allocated budget for the work package. |
| **Actual Spend** | Sum of all Cost Registrations against the work package's Cost Elements. |
| **Variance** | Budget Amount minus Actual Spend. Positive = under budget. |
| **EVM Metrics** | CPI (Cost Performance Index) and SPI (Schedule Performance Index) for the work package. |

### Cost Event Summary (COQ)

When viewing Cost Events with quality types (where `is_quality = True`), the COQ summary card shows:

| Metric | Description |
|---|---|
| **Total COQ** | Sum of all quality Cost Event estimated impacts. Color-coded: red if nonzero, green if zero. |
| **Conformance** | Total prevention + appraisal costs. Displayed with percentage of total COQ. Color-coded green. |
| **Nonconformance** | Total internal failure + external failure costs. Displayed with percentage of total COQ. Color-coded red. |
| **Schedule Impact** | Total schedule delay in days across all quality Cost Events. Color-coded red if nonzero. |

Below the four metrics, the **COQ Ratio** is displayed as a percentage: `(Total COQ / Project Budget) * 100`. This provides immediate context for whether the quality cost level is within acceptable range.

### Interpreting the COQ Summary Card

- **Low Total COQ with high nonconformance%**: Quality investment is insufficient. Consider increasing prevention and appraisal activities.
- **High Total COQ with high conformance%**: Quality investment is substantial. Monitor whether failure costs decrease over time.
- **High COQ Ratio** (above 20%): The project is spending a disproportionate amount on quality. Investigate root causes.
- **Schedule Impact > 0 days**: Quality events are causing schedule delays. This affects SPI and may trigger contractual penalties.

---

## Standards References

### Primary Standards

- **ANSI-748** -- Earned Value Management Systems. Defines the Work Package as the lowest-level planning and control unit in the WBS, with budget allocation, scheduling, and earned value measurement.

- **PMI PMBOK 7th Edition** -- Quality Performance Domain, Measurement Performance Domain. Defines quality management as a core performance domain and establishes the relationship between quality metrics and project outcomes.

- **ISO 10014:2021** -- Quality management systems -- Guidance for realizing financial and economic benefits. Provides guidance on managing the financial and economic impacts of quality, including COQ measurement frameworks.

- **ASQ TR 2:2018** -- Cost of Quality: Guidelines for Development, Implementation and Monitoring. The definitive guide to COQ program implementation, including the P-A-F classification model, data collection methods, and reporting frameworks.

### Academic and Industry References

- **Ahmed & Afifi (2018)** -- "Integrating Quality into Earned Value Management." CSCE Annual Conference. Introduces the EVMq framework that extends traditional EVM with quality-adjusted metrics (CPIq, QPI).

- **Solomon & Young (2007)** -- "Performance-Based Earned Value." Wiley. Establishes the theoretical foundation for integrating non-cost performance measures (including quality) into earned value analysis.

- **Nassar (2009)** -- QPI scoring methodology. Provides the empirical basis for the CPQ%-to-QPI mapping used in Backcast's quality performance scoring.

### ERP Integration References

- **SAP Internal Orders (CO-OM-OPA)** -- The Cost Event entity maps naturally to SAP's internal order concept. The `external_event_id` field on CostEvent can reference SAP order numbers for future ERP integration.

### Related Backcast Documentation

- [EVCS User Guide](./evcs-wbs-element-user-guide.md) -- Understanding versioning and time-travel for work packages
- [Change Order Business Guide](./change-order-business-guide.md) -- How change orders interact with work package budgets via branching
