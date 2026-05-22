# Work Packages User Guide

**Version:** 2.0
**Last Updated:** 2026-05-21
**Target Audience:** Project Managers, Cost Engineers, Quality Managers

---

## Table of Contents

1. [Introduction](#introduction)
2. [Work Package Types](#work-package-types)
3. [How Work Packages Work in Backcast](#how-work-packages-work-in-backcast)
4. [Creating and Managing Work Packages](#creating-and-managing-work-packages)
5. [Cost of Quality (COQ) for Quality-Typed Packages](#cost-of-quality-coq-for-quality-typed-packages)
6. [COQ Metrics](#coq-metrics)
7. [COQ Integration with EVM](#coq-integration-with-evm)
8. [Summary Card](#summary-card)
9. [Standards References](#standards-references)

---

## Introduction

### What are Work Packages?

Work Packages are a project-scoped grouping mechanism for cost registrations. Inspired by SAP internal orders and service orders, they allow project managers to organize actual costs by scope, activity, or event type -- beyond the default cost element breakdown.

Every cost registration may optionally be linked to exactly one work package. This provides a secondary axis for analyzing project costs: alongside the *what* (which cost element was charged), you can now track the *why* (which package of work drove the cost).

### Why Work Packages Matter

In capital projects, costs often need to be grouped in ways that don't map cleanly to the WBS or cost element structure:

- **Site visits** incur travel, labor, and material costs across multiple cost elements
- **Production phases** accumulate costs that need phase-level tracking
- **Quality events** carry prevention, appraisal, and failure costs that must be measured
- **Warranty batches** group post-delivery costs for claim processing
- **Commissioning phases** track costs during handover and acceptance

Without a grouping mechanism, these costs are scattered across the general ledger with no way to answer:

- How much did that site visit actually cost?
- What is the total financial impact of quality failures?
- Are commissioning costs within budget?

Backcast answers these questions by making work packages part of the project's unified financial system.

### From Quality Impacts to Work Packages

Quality Impacts were the first implementation of this concept -- a way to track the financial impact of quality events. Work Packages generalize this: quality impacts become one *type* of work package, alongside site visits, production phases, and other groupings.

The existing COQ (Cost of Quality) metrics pipeline continues to work unchanged, filtering work packages by type.

---

## Work Package Types

Backcast uses a closed set of work package types, each serving a distinct purpose:

| Type | Purpose | Example |
|---|---|---|
| **Quality Impact** | Track costs from quality events (NCRs, audits, rework) | `NCR-2026-0042` -- nonconformance report with rework costs |
| **Site Visit** | Group costs from on-site activities | `SV-2026-March` -- March site inspection trip |
| **Production Phase** | Track costs per manufacturing or assembly phase | `Phase 3 - Assembly` -- final assembly and testing |
| **Warranty Batch** | Group post-delivery warranty claim costs | `WB-2026-Q1` -- Q1 warranty claims batch |
| **Commissioning** | Track handover and acceptance costs | `Commissioning Line A` -- production line A commissioning |

Each type shares the same base fields (name, description, status, dates, cost impact) but may have type-specific fields. Quality-typed packages, for example, carry additional COQ fields.

### Status Lifecycle

Work packages have a simple two-state lifecycle:

- **Open** -- Costs can be posted and allocations added. The package is actively tracking costs.
- **Closed** -- Read-only. No further cost postings. Used for completed packages.

This simplified lifecycle avoids SAP-level complexity (CRTD → REL → TECO → CLSD) while covering Backcast's needs. The status can be extended via migration if more granular states are required.

---

## How Work Packages Work in Backcast

### Key Architectural Concept: Work Packages Are Flagged Cost Registrations

Work packages do not maintain a separate cost ledger. Instead, cost registrations are *linked* to a work package via a `work_package_id` flag. This means:

- Work package costs automatically flow into EVM Actual Cost calculations
- CPI and SPI naturally reflect work package costs (per PMI best practice)
- The financial impact of any package is traceable to specific WBS elements and cost elements
- No separate cost ledger is required -- work packages are part of the unified project financial system
- Metrics are computed by filtering cost registrations by the work package flag

### Data Model

```
WorkPackage (event header, renamed from QualityImpact)
  |-- work_package_id       --> Root ID (stable identity across versions)
  |-- project_id             --> Root ID of the affected Backcast project
  |-- name                   --> Human-readable label (required)
  |-- package_type           --> Closed enum: quality_impact, site_visit, etc.
  |-- description            --> Optional details about the package
  |-- status                 --> "open" or "closed"
  |-- event_date             --> When the event or activity occurred
  |-- cost_impact            --> Declared/estimated total financial impact
  |   ... quality-specific fields (see COQ section below)
  +-- [versioned]            --> Full EVCS bitemporal versioning support

CostRegistration (with work_package_id flag, when set = grouped cost)
  |-- cost_registration_id   --> Root ID
  |-- cost_element_id        --> Which cost element is affected
  |-- amount                 --> The actual cost incurred
  |-- work_package_id        --> Links to the work package (NULL = ungrouped)
  |-- [versioned, not branchable]
```

When a cost registration has `work_package_id` set, it belongs to that work package. The `cost_impact` on the WorkPackage represents the declared/estimated total, while actual costs are computed from the sum of linked cost registrations.

### Versioning and Branching

Work Packages use the EVCS versioning system with these characteristics:

- **Versionable**: Every change creates a new version. Full history is preserved. Time-travel queries are supported.
- **NOT branchable**: Work packages are financial facts that exist globally across all branches. A site visit cost is a fact regardless of which change order branch you are viewing.

This distinction is important: while scope elements (WBEs, Cost Elements) can be branched for change order what-if analysis, work package costs are objective financial facts that affect all branches equally.

---

## Creating and Managing Work Packages

### Step-by-Step Guide

1. **Navigate to the project**: Open the project you want to add a work package to.

2. **Open the Work Packages tab**: Select the "Work Packages" tab in the project view.

3. **Review the summary card**: The summary card at the top shows key metrics. When filtering by quality packages, the COQ summary card appears with quality-specific metrics.

4. **Click "Add Package"**: This opens the Work Package creation form.

5. **Fill in the required fields**:

   | Field | Description | Required | Example |
   |---|---|---|---|
   | Name | Human-readable label for the package | Yes | `NCR-2026-0042 Rework` |
   | Package Type | The type of work package | Yes | `Quality Impact` |
   | Description | Optional details | No | `Rework on column base plates after NCR` |
   | Event Date | When the event/activity occurred | No (defaults to today) | `2026-03-15` |
   | Cost Impact | Estimated total financial impact | Yes | `EUR 12,500.00` |
   | Status | Open or Closed (defaults to Open) | No | `Open` |

6. **Fill in type-specific fields**: Depending on the selected package type, additional fields may appear:

   **For Quality Impact packages:**

   | Field | Description | Required | Example |
   |---|---|---|---|
   | External Event ID | QMS identifier from the corporate system | Yes | `NCR-2026-0042` |
   | COQ Category | Conformance or Nonconformance | Yes | `Nonconformance` |
   | Schedule Impact Days | Days of schedule delay | No | `5` |

7. **Optionally add Cost Allocations**: Expand the "Cost Breakdown (optional)" section to allocate the cost impact to specific Cost Elements. For each allocation row:
   - Select a **Cost Element** from the dropdown
   - Enter the **amount** to allocate to that cost element
   - Click "Add Row" to add more allocations

   Each allocation creates a **Cost Registration entry** with the `work_package_id` flag set, meaning it automatically flows into EVM Actual Cost calculations. The form displays the **unallocated** remainder so you can see how much of the total cost impact remains at the project level.

8. **Click "Create"**: The work package is saved and immediately reflected in the summary card and package list.

### Filtering by Type

The Work Packages tab includes a type filter (chips/tabs for each type). This allows you to:

- View all work packages across types
- Filter to a specific type (e.g., show only quality impacts)
- Switch between views to compare cost distributions

When filtering to quality impact packages, the COQ summary card appears with quality-specific metrics (see [COQ Metrics](#coq-metrics) section).

### Editing Work Packages

To edit an existing work package:

1. Click the edit icon (pencil) on the package row in the table.
2. Modify any field in the modal form.
3. Click "Save" to create a new version. The previous version is preserved in history.

### Changing Status

To open or close a work package:

1. Click the status toggle on the package row.
2. Closing a package makes it read-only -- no further cost postings can be linked to it.

### Viewing Version History

Work Packages support full bitemporal versioning. To view the history of changes:

1. Click the history icon (clock) on the package row.
2. The Version History drawer opens, showing all versions with timestamps and field changes.

### Deleting Work Packages

Deletion is a soft-delete operation. The work package is marked as deleted but preserved in the history for audit purposes. To delete:

1. Click the delete icon (trash) on the package row.
2. Confirm the deletion in the pop-up dialog.

### Viewing Breakdowns

To view the cost breakdown allocations for a work package:

1. Click "View" in the Breakdowns column.
2. The Breakdown drawer opens, showing the allocated amounts per WBE/Cost Element along with the unallocated remainder.

### Permissions

Work Package operations require the following RBAC permissions:

| Operation | Required Permission |
|---|---|
| View work packages | `work-package-read` |
| Create work packages | `work-package-create` |
| Edit work packages | `work-package-update` |
| Delete work packages | `work-package-delete` |

---

## Cost of Quality (COQ) for Quality-Typed Packages

When a work package has `package_type = "quality_impact"`, it carries additional fields for Cost of Quality tracking. This section describes the COQ framework and how it applies to quality-typed packages.

### The P-A-F Model

The Prevention-Appraisal-Failure (P-A-F) model, formalized in ASQ TR 2:2018, classifies quality costs into four categories:

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

Backcast classifies quality-typed work packages as either **conformance** or **nonconformance** via the `coq_category` field, reflecting this two-part structure. When more granular breakdown is needed, the external QMS (referenced by External Event ID) typically provides the sub-category detail.

### Quality-Specific Data Model Fields

When `package_type = "quality_impact"`, the following additional fields are populated:

```
WorkPackage (quality-specific fields)
  |-- external_event_id      --> Link to corporate QMS (e.g., "NCR-2026-0042")
  |-- coq_category           --> "conformance" or "nonconformance"
  |-- schedule_impact_days   --> Schedule delay in days
```

These fields are nullable on all work packages and are only meaningful for quality-typed packages.

---

## COQ Metrics

Backcast provides the following COQ metrics for quality-typed work packages, drawing on the EVMq framework (Ahmed & Afifi, CSCE 2018) which integrates quality measures into earned value management.

All COQ metrics are computed by filtering work packages where `package_type = 'quality_impact'`.

### Metric Definitions

| Metric | Formula | Meaning |
|---|---|---|
| **Total COQ** | Sum of all quality-flagged cost registrations | Total quality spend across both conformance and nonconformance |
| **CPQ** (Cost of Poor Quality) | Sum of nonconformance cost registrations | Failure costs only |
| **CCQ** (Cost of Conformance Quality) | Sum of conformance cost registrations | Prevention and appraisal costs only |
| **CPQ%** | `CPQ / Total AC * 100` | Quality failure share of total project spend |
| **CPIq** | `CPQ / AC` | Quality's share of cost variance -- how much of the total cost overrun is quality-related |
| **COQ Ratio** | `Total COQ / Project Budget * 100` | Quality cost burden relative to project budget |
| **QPI** (Quality Performance Index) | Normalized from CPQ% | Single quality health score |

These metrics are available via the `GET /api/v1/work-packages/project/{id}/coq-metrics` endpoint and are computed from actual cost registration data, ensuring alignment with EVM calculations.

### Quality Performance Index (QPI)

The QPI, based on the scoring methodology by Nassar (2009), translates CPQ% into a single index value that is comparable across projects:

| CPQ% Range | QPI Value | Rating | Interpretation |
|---|---|---|---|
| <= 0.5% | > 1.15 | Outstanding | Quality costs are negligible relative to project spend |
| 0.5% -- 1.0% | 1.05 -- 1.15 | Exceeds Target | Quality management is highly effective |
| 1.0% -- 2.0% | 0.95 -- 1.05 | Within Target | Quality performance is acceptable |
| 2.0% -- 4.0% | 0.85 -- 0.95 | Below Target | Quality failures are eroding project margins |
| > 4.0% | <= 0.85 | Poor Performance | Urgent corrective action required |

### Using These Metrics

**For project managers:**

- Monitor **CPQ%** weekly. A rising trend indicates accumulating quality failures.
- Use **CPIq** to quantify quality's contribution to cost variance. If CPIq = 8.3%, then 8.3% of your total actual cost is quality failure cost.
- Track the **COQ Ratio** to benchmark against industry norms (15--20% for mature organizations, 30--40% for immature).
- Use **QPI** for cross-project comparison and portfolio-level quality reporting.

**For quality managers:**

- Compare conformance vs. nonconformance costs. A healthy ratio shows more investment in prevention/appraisal than in failures.
- Use External Event IDs to trace Backcast quality costs back to the QMS for root cause analysis.
- Review the breakdown allocations to identify which cost elements are most affected by quality events.

---

## COQ Integration with EVM

### How Quality Costs Flow Into Earned Value

Per the PMI Practice Standard for EMA (Earned Value Management), quality costs are a legitimate component of Actual Cost (AC). Backcast follows this principle:

1. Quality costs are recorded as financial impacts with optional cost element allocations.
2. These costs contribute to the project's total actual expenditure.
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

The Work Packages tab displays a summary card at the top of the page. The card content adapts based on the active type filter.

### General Summary Card

When viewing all work packages or non-quality types, the summary card shows:

| Metric | Description |
|---|---|
| **Total Packages** | Count of work packages (filtered by active type). |
| **Total Cost Impact** | Sum of all work package `cost_impact` values. Displayed in project currency. |
| **Open Packages** | Count of packages still accepting cost postings. |
| **Total Allocated** | Sum of all linked cost registrations across packages. |

### COQ Summary Card (Quality Filter Active)

When filtering by quality impact packages, the summary card switches to the COQ view:

| Metric | Description |
|---|---|
| **Total COQ** | Sum of all quality package cost_impact values. Displayed in project currency. Color-coded: red if nonzero, green if zero (no quality costs). |
| **Conformance** | Total conformance (prevention + appraisal) costs. Displayed with percentage of total COQ. Color-coded green. |
| **Nonconformance** | Total nonconformance (internal + external failure) costs. Displayed with percentage of total COQ. Color-coded red. |
| **Schedule Impact** | Total schedule delay in days across all quality packages. Color-coded red if nonzero. |

Below the four metrics, the **COQ Ratio** is displayed as a percentage: `(Total COQ / Project Budget) * 100`. This provides immediate context for whether the quality cost level is within acceptable range.

### Interpreting the COQ Summary Card

- **Low Total COQ with high nonconformance%**: Quality investment is insufficient. Consider increasing prevention and appraisal activities.
- **High Total COQ with high conformance%**: Quality investment is substantial. Monitor whether failure costs decrease over time.
- **High COQ Ratio** (above 20%): The project is spending a disproportionate amount on quality. Investigate root causes.
- **Schedule Impact > 0 days**: Quality events are causing schedule delays. This affects SPI and may trigger contractual penalties.

---

## Standards References

### Primary Standards

- **PMI PMBOK 7th Edition** -- Quality Performance Domain, Measurement Performance Domain. Defines quality management as a core performance domain and establishes the relationship between quality metrics and project outcomes.

- **ISO 10014:2021** -- Quality management systems -- Guidance for realizing financial and economic benefits. Provides guidance on managing the financial and economic impacts of quality, including COQ measurement frameworks.

- **ASQ TR 2:2018** -- Cost of Quality: Guidelines for Development, Implementation and Monitoring. The definitive guide to COQ program implementation, including the P-A-F classification model, data collection methods, and reporting frameworks.

### Academic and Industry References

- **Ahmed & Afifi (2018)** -- "Integrating Quality into Earned Value Management." CSCE Annual Conference. Introduces the EVMq framework that extends traditional EVM with quality-adjusted metrics (CPIq, QPI).

- **Solomon & Young (2007)** -- "Performance-Based Earned Value." Wiley. Establishes the theoretical foundation for integrating non-cost performance measures (including quality) into earned value analysis.

- **Nassar (2009)** -- QPI scoring methodology. Provides the empirical basis for the CPQ%-to-QPI mapping used in Backcast's quality performance scoring.

### ERP Integration References

- **SAP Internal Orders (CO-OM-OPA)** -- The work package entity maps naturally to SAP's internal order concept. The `external_event_id` field can reference SAP order numbers for future ERP integration.

### Related Backcast Documentation

- [EVCS User Guide](./evcs-wbe-user-guide.md) -- Understanding versioning and time-travel for work packages
- [Change Order Business Guide](./change-order-business-guide.md) -- How change orders interact with work package costs
