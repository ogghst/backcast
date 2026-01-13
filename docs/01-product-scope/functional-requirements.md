# Functional Requirements

**Last Updated:** 2025-01-13  
**Source:** Product Requirements Document (PRD)  
**Status:** Active

## 1. Executive Summary

This document defines the requirements for a Project Budget Management and Earned Value Management (EVM) application designed for end-of-line automation projects. The application will serve as a simulation and validation platform for new business rules and performance metrics, enabling comprehensive project financial tracking from initial budget definition through project completion.

The system will manage complex project structures comprising multiple Work Breakdown Elements (WBEs) representing individual machines, with granular cost tracking at the department level. The application will support complete project lifecycle financial management including budget forecasting, change order processing, quality event tracking, and baseline management while providing full EVM compliance and analytics capabilities.

## 2. Business Context and Objectives

The primary objective of this application is to provide the Project Management Directorate with a robust tool to model, test, and validate financial management processes before implementing them in production environments. The system must accurately simulate real-world scenarios encountered in end-of-line automation projects, where multiple machines are sold as part of integrated solutions, with each machine requiring independent budget tracking and performance measurement.

The application will enable the organization to refine business rules, test performance metrics under various scenarios, and establish best practices for project financial management. By providing comprehensive EVM capabilities, the system will support data-driven decision making and improve project delivery predictability.

## 3. System Overview and Core Capabilities

The application shall function as a comprehensive project financial management system built around EVM principles. At its foundation, the system will manage hierarchical project structures where each project contains multiple WBEs (representing individual machines or deliverables), and each WBE contains multiple cost elements representing departmental budgets and responsibilities.

The system must support the complete financial lifecycle of projects, from initial budget definition through final cost reconciliation. This includes establishing revenue and cost baselines, tracking actual expenditures, managing forecasts, processing change orders and quality events, and maintaining historical baselines at key project milestones. All financial data must be structured to support standard EVM calculations and reporting.

## 4. Project Structure Requirements

### 4.1 Project Creation and Configuration

The system shall allow users to create new projects with comprehensive metadata including project name, customer information, contract value, start date, planned completion date, and project manager assignment. Each project shall serve as the top-level container for all associated financial and structural data.

### 4.2 Work Breakdown Element (WBE) Management

Each project shall support the creation of multiple WBEs, where each WBE represents a distinct machine or major deliverable sold to the customer. For each WBE, the system must capture the machine type, serial number or identifier, contracted delivery date, and allocated revenue portion. WBEs shall function as the primary organizational unit for budget allocation and performance measurement.

The system must allow WBEs to be added, modified, and tracked independently while maintaining their relationship to the parent project. Each WBE must maintain its own performance metrics and baselines while contributing to aggregate project-level reporting.

WBEs are organized in hierarchical structure, where each WBE can have multiple sub-WBEs representing different components or deliverables. The system must support the creation, modification, and tracking of sub-WBEs while maintaining their relationship to the parent WBE.

### 4.3 Cost Element Structure

Within each WBE, the system shall support the creation of multiple cost elements, each representing a specific department or discipline responsible for delivering portions of the work. Cost elements must include a type, that is an hierarchical composition of controlling elements (such as Engineering, divided in Mechanical Engineering, Electrical Engineering), budget allocation, and planned value distribution over time. The system must allow cost elements to be added, modified, and tracked independently while maintaining their relationship to the parent WBE. The system can allow performance metrics to be captured at the cost element level, and these metrics can be used to calculate Earned Value (EV) and other EVM metrics. The system must allow performance metrics at cost element type level, to summarize and compare project or different projects at controlling level.

Cost elements shall serve as the most granular level of budget tracking and shall be the primary point for cost imputation and forecast updates. The system must maintain the hierarchical relationship between projects, WBEs, and cost elements throughout all operations.

## 5. Revenue Management Requirements

### 5.1 Revenue Allocation

The system shall enable users to assign total project revenue and distribute it across WBEs based on contracted values for each machine or deliverable. Revenue allocation must be captured at the WBE level and further distributed to cost elements based on the planned value of work assigned to each department.

### 5.2 Revenue Recognition Planning

For each cost element, the system must support the definition of planned revenue recognition schedules aligned with the planned completion of work. This shall form the basis for Planned Value (PV) calculations in the EVM framework. Users must be able to define time-phased revenue recognition based on planned work completion dates.

## 6. Cost Management Requirements

### 6.1 Budget Definition and Allocation

The system shall allow users to establish initial budgets at the cost element level, representing the Budget at Completion (BAC) for each department's scope of work. Budget allocation must be performed for each cost element within each WBE, with the ability to define time-phased budget consumption plans.

The system must maintain the integrity of budget allocations and provide warnings when total allocated budgets exceed available project budgets or when WBE budgets exceed allocated revenues.

### 6.1.1 Cost Element Schedule Baseline

For each cost element, the system shall support versioned, branchable schedule registrations that define the planned progression of work over time. Each registration must include a start date, end date, progression type, user-provided registration date, and optional description so that users can record the business context driving the change. Users must be able to perform full CRUD operations on schedule registrations while retaining historical entries.

The system shall support the following progression types: linear (even distribution over the duration), gaussian (normal distribution curve with peak at midpoint), and logarithmic (slow start with accelerating completion).

**Progression Type Formulas:**

For a cost element with Budget at Completion (BAC), start date (S), end date (E), and control date (t) where S ≤ t ≤ E:

**Linear Progression:**
Planned completion percentage increases uniformly over time.
```
% Planned(t) = (t - S) / (E - S)
PV(t) = BAC × % Planned(t)
```

**Gaussian Progression:**
Planned completion follows a normal distribution curve with peak at midpoint.
```
μ = (S + E) / 2                    # Midpoint (mean)
σ = (E - S) / 6                    # Standard deviation (99.7% within ±3σ)
z = (t - μ) / σ                    # Z-score
% Planned(t) = CDF(z)              # Cumulative distribution function
PV(t) = BAC × % Planned(t)
```
Where CDF is the standard normal cumulative distribution function. At the midpoint (t = μ), % Planned = 50%.

**Logarithmic Progression:**
Planned completion starts slow and accelerates toward end.
```
duration = E - S
elapsed = t - S
% Planned(t) = log(1 + elapsed) / log(1 + duration)
PV(t) = BAC × % Planned(t)
```
At 50% duration, logarithmic progression achieves ~30% planned completion (slower start).

**Interpolation Rules:**
- For control dates between schedule registrations: Use weighted average of adjacent registrations
- For control dates before first registration: Extrapolate using earliest registration
- For control dates after last registration: Use last registration's values
- Partial periods: Calculate pro-rated values based on exact control date

The planned value engine shall always use the schedule registration with the most recent registration date (ties resolved by creation time) whose registration date is on or before the control date.

When a baseline is created, the system shall copy the latest schedule registration whose registration date is on or before the baseline date into a baseline schedule snapshot tied to the baseline log, preserving the registration date and description exactly as recorded. Once captured, baseline schedules remain immutable unless superseded through approved change orders or formal baseline revisions, maintaining the original baseline for historical comparison.

### 6.2 Cost Registration and Actual Cost Tracking

The system shall provide functionality to register actual costs incurred against specific cost elements. Each cost registration must capture the date of expenditure, amount, cost category (labor, materials, subcontracts, or other), invoice or reference number, and descriptive notes.

Cost registrations shall update the Actual Cost (AC) for the associated cost element and WBE, feeding directly into EVM calculations. The system must maintain a complete audit trail of all cost registrations with timestamps and user attribution.

### 6.3 Earned Value Recording

Users must be able to record the percentage of work completed for cost elements based on physical progress and deliverables achieved. Operational earned value entries remain editable until replaced, while baseline snapshots capture the latest values for historical comparison.

Each earned value entry shall capture the completion date and the percentage of work completed (percent complete) representing the physical completion of the work scope. The system shall calculate Earned Value (EV) using the formula $EV = BAC \times \%\ \text{di completamento fisico}$ where BAC is the Budget at Completion for the cost element. For example, if a cost element has $BAC = €100{,}000$ and is 30% physically complete, then $EV = 100{,}000 \times 0{,}30 = €30{,}000$.

Earned value entries may also capture specific deliverables achieved and descriptive notes. Whenever a baseline is created, the system shall snapshot the latest percent complete and earned value onto the corresponding Baseline Cost Element, enabling trend analysis without restricting subsequent operational updates.

## 7. Forecasting Requirements

### 7.1 Forecast Creation and Management

The system shall support the creation and maintenance of cost forecasts at the cost element level through a CRUD interface with dialog forms. Users must be able to create new forecasts at any point during project execution, with each forecast representing the Estimate at Completion (EAC) for the cost element based on current performance and anticipated future conditions.

Each forecast entry must include the forecast date (must be in the past, with alert if future), the revised estimate at completion (EAC - allows any positive value, shows warnings if EAC > BAC or EAC < AC), the estimate to complete (ETC - calculated as EAC - AC, not stored), forecast type (strict enum: bottom_up, performance_based, management_judgment), assumptions underlying the forecast, and the responsible estimator. The system shall maintain a complete history of all forecasts ordered by forecast_date descending to enable trend analysis and forecast accuracy assessment.

The system shall enforce a maximum of three forecast dates per cost element. When deleting a forecast, if the deleted forecast was the current forecast, the system shall automatically promote the previous forecast (by forecast_date) to become the current forecast.

### 7.2 Forecast Updates and Versioning

The system must allow forecasts to be updated periodically for each WBE and cost element as project conditions change. Each update shall create a new forecast version while preserving historical forecasts for comparison and analysis.

**Variance Thresholds:**

| Variance Level | Forecast Change from Previous | EAC vs BAC Variance | Alert Type | Action Required |
|----------------|-------------------------------|---------------------|------------|-----------------|
| Minor | ±5% | ±5% | Info | Log for trend analysis |
| Moderate | ±5-10% | ±5-10% | Warning | Notify project manager |
| Significant | ±10-15% | ±10-15% | Warning | Require explanation |
| Critical | >15% | >15% | Critical | Require director approval |

**Alert Behavior:**
- Minor variances: Logged in forecast history, visible in trends
- Moderate variances: In-app notification to project manager
- Significant variances: Email notification + require variance explanation
- Critical variances: Escalation to director + block EAC update without approval

**Trend Analysis:**
- Track forecast direction (increasing vs decreasing over time)
- Detect forecast volatility (frequent large changes)
- Compare forecast accuracy (actual EAC vs forecasted EAC at completion)
- Generate forecast accuracy report by project, WBE, and cost element

**Variance Explanation:**
When forecast variance exceeds ±10%, user must provide:
- Reason for significant change
- Specific factors affecting the estimate
- Mitigation actions being taken
- Confidence level in new forecast (Low/Medium/High)

**Forecast Stability Metric:**
Calculate forecast stability as the standard deviation of EAC changes over time.
- Stable: <5% standard deviation
- Moderate: 5-10% standard deviation
- Volatile: >10% standard deviation (requires review)

## 8. Change Order Management Requirements

### 8.1 Change Order Processing

The system shall provide comprehensive change order management capabilities to handle scope changes, contract modifications, and customer-requested additions. Each change order must be created with a unique identifier, description of the change, requesting party, justification, and proposed effective date. When a change order is created, the system shall automatically spawn a dedicated change order branch from the selected source branch (default: main). The branch name shall follow the pattern `co-{change_order_id}`.

Change orders must support modifications to both costs and revenues. When a change order is approved and implemented, the system shall update the affected WBE budgets, cost element allocations, and revenue assignments accordingly. The system must maintain the original baseline data while clearly tracking the impact of approved changes on current budgets and forecasts.

### 8.2 Change Order Impact Analysis

Before finalizing change orders, the system shall provide impact analysis showing the effect on project budgets, WBE allocations, cost element budgets, revenue recognition, schedule implications, and EVM performance indices. Users must be able to model change order impacts before formal approval.

### 8.3 Change Order Approval Workflow

The system shall track change order status through defined workflow states. Each status transition must be recorded with timestamp and responsible user information.

**Workflow States:**

1. **Draft** - Initial state when change order is created
   - Creator can edit all fields
   - Not visible to approvers
   - Can be deleted or submitted

2. **Submitted** - Change order submitted for approval
   - Read-only except for withdraw action
   - Assigned to approver based on impact level
   - Notification sent to approver

3. **Under Review** - Approver is actively reviewing
   - Approver can request clarification
   - Branch is locked for editing
   - Impact analysis generated

4. **Approved** - Change order approved for implementation
   - Branch is unlocked for implementation
   - Changes can be merged to main
   - Notification sent to stakeholders

5. **Implemented** - Changes have been merged to main branch
   - Change order is closed
   - Final impact analysis captured
   - Read-only historical record

6. **Rejected** - Change order not approved
   - Reason for rejection recorded
   - Branch archived but not deleted
   - Can be resubmitted with modifications

7. **Archived** - Change order closed without implementation
   - Withdrawn by creator
   - Superseded by another change
   - No longer relevant

**Approval Matrix:**

| Impact Level | Financial Impact | Approver | Approval SLA | Branch Behavior |
|--------------|------------------|----------|--------------|-----------------|
| Low          | < €10K           | Project Manager   | 2 business days | No locking during review |
| Medium       | €10K - €50K      | Department Head   | 5 business days | Locked during review |
| High         | > €50K           | Director          | 10 business days| Locked during review |
| Critical     | > €100K          | Executive Committee| 15 business days| Locked, requires sign-off |

**Notification Mechanisms:**

- Email notifications for state transitions
- In-app notifications for assigned actions
- Daily digest for pending approvals
- Escalation notifications when SLA approaching

**Rollback Procedures:**

- Approved changes can be rolled back within 24 hours
- Rollback creates new change order automatically
- Requires justification and approval
- Full audit trail maintained

### 8.4 Branching and Versioning System

The system shall implement a comprehensive branching and versioning architecture to support isolated work on change orders and maintain complete entity history. This system enables safe experimentation with change order modifications before merging them into the main project data.

#### 8.4.1 Entity Versioning

All entities in the system shall support branching and versioning through a unified mechanism described in [Branching Requirements](branching-requirements.md).

#### 8.4.2 Branch-Enabled Entities

Project, WBE, and CostElement entities shall support branching and versioning.

#### 8.4.9 Version History and Time Machine

The system shall provide robust Time Machine capabilities to view the state of the project at any past point in time.

- **Scenarios Supported**:
  - **T1 (Active History)**: Viewing the active state of an entity at a past date.
  - **T2 (Deleted Head)**: Viewing an entity at a past date when it was active, even if currently deleted.
  - **T3 (Deleted Past)**: Correctly showing "no data" for dates when the entity was effectively deleted.
  - **T4 (Cross-Branch)**: Viewing the history of a specific change order branch, independent of the main branch.
  - **T5 (Reactivation Gap)**: Correctly handling gaps in history where an entity was deleted and later restored.

#### 8.4.10 Entity Lifecycle Operations

The system shall support the following entity lifecycle operations with proper versioning:

- **Create**: Creates a new entity with version=1 and status="active"
- **Update**: Creates a new version of the entity with updated data, preserving the previous version
- **Soft Delete**: Creates a new version with status="deleted", preserving all previous versions for recovery
- **Restore**: Creates a new version with status="active" based on the most recent deleted version
- **Hard Delete**: Permanently removes all versions of an entity (only for soft-deleted entities, requires administrative privileges)

All lifecycle operations must maintain version sequence integrity and preserve complete audit trails.

#### 8.4.11 Query Filtering and Default Behavior

The system shall implement automatic query filtering to ensure users only see relevant entity versions:

- **Active Status Filtering**: By default, queries shall return only entities with status="active"
- **Latest Version Filtering**: When multiple versions exist, queries shall return only the latest version for each entity_id
- **Branch Filtering**: For branch-enabled entities, queries shall automatically filter by the current branch context
- **Combined Filtering**: All filters must work together to ensure queries return the correct active, latest version in the selected branch

The system must provide override capabilities for administrative and reporting operations that require access to deleted entities, historical versions, or cross-branch data.

#### 8.4.12 Merged View Service

The system shall provide a merged view service that displays entities from both main and branch branches in a unified view, enabling users to understand the complete impact of branch changes before merging.

**Merged View Computation:**

The merged view is computed as follows:
1. Start with all entities from the source branch (typically main)
2. Overlay entities from the change order branch
3. For entities existing in both branches, the branch version takes precedence
4. For entities deleted in branch, mark as "Deleted in Branch"
5. For entities created in branch, mark as "Created in Branch"
6. For entities modified in branch, mark as "Modified in Branch" and show both versions

**Entity Change Status:**

The merged view shall indicate the change status of each entity:
- **Unchanged**: Entity exists in both branches with identical data
- **Created**: Entity exists only in the branch (new entity)
- **Updated**: Entity modified in the branch (shows branch version)
- **Deleted**: Entity exists in main but is deleted in the branch

**Performance Requirements:**
- Standard merged view query: <500ms for projects with <20 WBEs
- Large merged view query: <2 seconds for projects with ≥20 WBEs
- Caching strategy: 5-minute TTL for merged view results
- Incremental updates: Refresh only changed entities on re-query

**Conflict Resolution:**
- Same entity modified in both branches (rare): Branch version wins
- Child deleted in branch but parent modified: Preserve parent, mark child deleted
- Circular dependencies: Prevent merge, require user intervention

**Supported Entities:**
- Project (top-level merged view)
- WBE (hierarchical merged view)
- CostElement (leaf-level merged view)

**UI Display:**
- Color coding: Green (Created), Yellow (Modified), Red (Deleted), Gray (Unchanged)
- Side-by-side comparison for modified entities
- Diff view showing specific field changes
- Filterable by change status
- Export merged view to CSV/Excel for review

## 9. Quality Event Management Requirements

### 9.1 Quality Event Recording

The system shall support the registration of quality events that result in additional costs without corresponding revenue increases. Quality events represent rework, defect correction, warranty work, or other quality-related expenditures that impact project profitability.

Each quality event must capture the event date, detailed description of the issue, root cause classification, responsible department, estimated cost impact, actual cost incurred, corrective actions taken, and preventive measures implemented. Quality events must be linked to specific cost elements where the additional costs will be recorded.

### 9.2 Quality Event Cost Tracking

When quality events result in actual expenditures, these costs shall be registered in the system and attributed to the appropriate cost elements. The system must clearly distinguish quality event costs from planned work costs in reporting and analytics. Quality event costs shall be included in Actual Cost (AC) calculations but shall be tracked separately to enable quality cost analysis.

### 9.3 Quality Event Impact on EVM Metrics

The system must account for quality event costs in EVM calculations without adjusting revenue or planned value. This will result in cost variances and performance index degradation, providing visibility into quality impacts on project performance. Quality event costs must be separately reportable to support root cause analysis and process improvement initiatives.

## 10. Baseline Management Requirements

### 10.1 Baseline Creation at Project Events

The system shall support the creation of cost and schedule baselines at significant project milestones through both automatic and manual triggers.

**Standard Milestones (Automatic Baseline Creation):**

| Milestone | Trigger Event | Typical Project Phase | Optional? |
|-----------|---------------|----------------------|-----------|
| Project Kickoff | Project creation date | Initiation | No |
| BOM Release | Bill of Materials approved | Engineering | No |
| Engineering Complete | Engineering sign-off | Engineering | No |
| Procurement Complete | All materials ordered | Procurement | No |
| Manufacturing Start | Production begins | Manufacturing | No |
| Shipment | Equipment leaves factory | Manufacturing | No |
| Site Arrival | Equipment received at site | Installation | No |
| Commissioning Start | Installation complete, testing begins | Commissioning | No |
| Commissioning Complete | Acceptance testing passed | Commissioning | No |
| Project Closeout | Final acceptance signed | Closeout | No |

**Automatic Baseline Creation:**
- System detects milestone completion (based on project status or date)
- Creates baseline automatically with milestone name and date
- Captures snapshot of all current data
- Notification sent to project manager
- Can be suppressed if milestone not applicable

**Manual Baseline Creation:**
- User can create baseline at any time
- Requires baseline name, date, and justification
- Useful for ad-hoc checkpoints, pre-change-order snapshots, etc.
- Subject to same data capture as automatic baselines

**Baseline Approval Requirements:**

| Baseline Type | Approval Required | Approver |
|---------------|-------------------|----------|
| Standard milestone | No | Automatic |
| Manual baseline < €10K impact | No | Project manager discretion |
| Manual baseline ≥ €10K impact | Yes | Project manager |
| Pre-change-order baseline | Yes | Project manager |
| Post-change-order baseline | Yes | Change order approver |

**Baseline Data Capture:**
Each baseline creation event must capture:
- Baseline metadata (date, event description, milestone type, responsible department)
- Budget snapshots for all WBEs and cost elements
- Cost snapshots (actual costs incurred to date)
- Revenue snapshots (recognized and planned revenue)
- Earned value snapshots (current percent complete and EV)
- Forecast snapshots (current EAC, ETC)
- Schedule registration snapshots (latest schedule per cost element)

**Baseline Creation Workflow:**
1. User or system initiates baseline creation
2. System validates baseline date (must be in past or today)
3. For manual baselines, capture justification
4. For significant baselines, route for approval
5. Upon approval, capture all snapshots atomically
6. Create BaselineLog record with metadata
7. Create BaselineCostElement records for each cost element
8. Notification sent to stakeholders
9. Baseline becomes available for reporting and comparison

**Historical Baseline Access:**
- All baselines retained permanently (no deletion)
- Read-only access for reporting and comparison
- Can view baseline state at any past point in time
- Baseline comparison report between any two baselines
- Baseline vs actuals comparison for performance analysis

### 10.2 Baseline Comparison and Variance Analysis

The system shall maintain all historical baselines and provide comparison capabilities to analyze changes between any two baselines or between any baseline and current actuals. Variance analysis must be available at project, WBE, and cost element levels, showing changes in budgets, costs, revenues, forecasts, and performance metrics between baseline periods.

Baseline comparisons shall leverage the consolidated Baseline Log data model (Baseline Log + Baseline Cost Elements) without reliance on a separate Baseline Snapshot table. Any historical reporting must read from these canonical sources.

### 10.3 Performance Measurement Baseline (PMB)

The system shall maintain a Performance Measurement Baseline in accordance with EVM principles. The PMB shall represent the time-phased budget plan against which performance is measured. The system must track changes to the PMB resulting from approved change orders while maintaining the original baseline for historical reference and variance analysis.

## 11. Non-Functional Requirements

### 11.1 Performance Requirements

The system shall meet the following performance targets:

- **Response Times:**
  - Standard API requests: <200ms (95th percentile)
  - Complex EVM calculations: <500ms
  - Standard report generation: <5 seconds
  - Complex analytical reports: <15 seconds
  - Branch comparison operations: <500ms
  - Merged view queries: <500ms

- **Throughput:**
  - Support 100 concurrent users
  - Handle 50 concurrent projects with full data load
  - Process 1,000 cost registrations per minute
  - Generate 10 reports simultaneously without degradation

- **Scalability:**
  - Horizontal scaling for API servers
  - Database connection pooling for 200+ concurrent connections
  - Caching layer for frequently accessed data

### 11.2 Reliability and Availability

- **Uptime Target:** 99.5% availability during business hours
- **Data Durability:** 99.999% (atomic writes, WAL enabled)
- **Backup Frequency:** Daily automated backups, retained for 30 days
- **Disaster Recovery:** RTO <4 hours, RPO <1 hour

### 11.3 Security Requirements

**Beyond Section 16, the system shall provide:**

- **Authentication:**
  - JWT-based authentication with 15-minute token expiration
  - Refresh token rotation with 30-day validity
  - Multi-factor authentication support (optional)

- **Authorization:**
  - Role-based access control (RBAC) with 5 defined roles
  - Project-level permission isolation
  - Field-level data access control

- **Data Protection:**
  - TLS 1.3 for all client-server communications
  - Encrypted data at rest (AES-256)
  - PII data masking in logs
  - Audit logging for all data modifications

- **Session Management:**
  - Persist time machine date per user session
  - Persist branch selection per user session
  - Session timeout after 30 minutes of inactivity
  - Concurrent session limits (max 3 per user)

### 11.4 Maintainability

- **Code Quality:**
  - TypeScript strict mode for frontend
  - Python MyPy strict mode for backend
  - Minimum 80% test coverage
  - Zero linting errors (Ruff, ESLint)

- **Documentation:**
  - API documentation auto-generated from OpenAPI spec
  - Architectural Decision Records (ADRs) for major decisions
  - Inline code documentation for complex algorithms
  - User documentation with screenshots

- **Monitoring:**
  - Application performance monitoring (APM)
  - Error tracking with stack traces
  - Database query performance monitoring
  - API endpoint response time tracking

### 11.5 Interoperability

- **Data Import/Export:**
  - CSV export for all tabular data
  - Excel export with formatting for reports
  - PDF export for formal reports
  - JSON API for programmatic access

- **Integration Points:**
  - OpenAPI 3.0 specification at `/openapi.json`
  - Webhook support for event notifications (future)
  - RESTful API with HATEOAS links
  - GraphQL endpoint (future enhancement)

### 11.6 Usability

- **User Interface:**
  - Responsive design for desktop and tablet
  - Keyboard navigation support
  - WCAG 2.1 AA accessibility compliance
  - Contextual help and tooltips
  - Undo functionality for destructive operations

- **User Experience:**
  - Maximum 3 clicks to reach any feature from dashboard
  - Inline validation with immediate feedback
  - Loading indicators for operations >500ms
  - Optimistic updates for better perceived performance

## 12. Earned Value Management Requirements

### 12.1 EVM Terminology and Compliance

The system shall fully implement Earned Value Management principles using standard EVM terminology as defined by industry standards including the ANSI/EIA-748 standard. All calculations, reports, and user interfaces shall use proper EVM terminology consistently.

### 12.2 Core EVM Metrics

The system must calculate and maintain the following core EVM metrics for each cost element, WBE, and at the project level:

Planned Value (PV), also known as Budgeted Cost of Work Scheduled (BCWS), represents the authorized budget assigned to scheduled work and shall be calculated from the cost element schedule baseline. The system shall calculate PV using the formula $PV = BAC \times \%\ \text{di completamento pianificato}$, where BAC is the Budget at Completion of the cost element and the planned completion percentage is determined from the schedule baseline (start date, end date, and progression type) at the control date. For example, if $BAC = €100{,}000$ and at month 2 the planned completion is 40%, then $PV = 100{,}000 \times 0{,}40 = €40{,}000$. The progression type (linear, gaussian, logarithmic) determines how the planned completion percentage is calculated between the start and end dates.

Earned Value (EV), also known as Budgeted Cost of Work Performed (BCWP), represents the budgeted cost of work actually performed at the control date. The EV calculation uses the latest recorded earned value entry (percent complete) as the source of truth. The formula is EV = BAC × % complete, where the percent complete is based on the most recent earned value entry recorded for the cost element. For example, if a cost element has $BAC = €100{,}000$ and is 30% physically complete, then $EV = 100{,}000 \times 0{,}30 = €30{,}000$. At the project level, the same formula applies using the aggregated budget and completion percentage. Baseline snapshots preserve historical EV values for comparison but do not affect current EV calculations.

Actual Cost (AC) represents the realized cost incurred for work performed and shall be calculated from all registered costs including quality event costs.

Budget at Completion (BAC) represents the total planned budget for the work scope and shall be maintained as the sum of all allocated budgets adjusted for approved changes. Estimate at Completion (EAC) represents the expected total cost at project completion and shall be calculated using current forecasts. Estimate to Complete (ETC) represents the expected cost to finish remaining work and shall be calculated as EAC minus AC.

### 12.3 EVM Performance Indices

The system shall calculate the following performance indices:

Cost Performance Index (CPI) shall be calculated as EV divided by AC, indicating cost efficiency. A CPI greater than one indicates under-budget performance, while less than one indicates over-budget conditions. Schedule Performance Index (SPI) shall be calculated as EV divided by PV, indicating schedule efficiency. An SPI greater than one indicates ahead-of-schedule performance, while less than one indicates behind-schedule conditions.

To Complete Performance Index (TCPI) shall be calculated to project the cost performance required on remaining work to meet budget goals. The system shall calculate both TCPI variants:

**TCPI based on BAC:**
The TCPI based on Budget at Completion represents the efficiency needed to complete the project within the original budget.
```
TCPI(BAC) = (BAC - EV) / (BAC - AC)
```
Use this when the project must complete within the original BAC. A TCPI > 1.0 indicates improved performance is needed. TCPI > 1.5 is typically difficult to achieve.

**TCPI based on EAC:**
The TCPI based on Estimate at Completion represents the efficiency needed to complete the project based on current forecast.
```
TCPI(EAC) = (BAC - EV) / (EAC - AC)
```
Use this when the EAC is accepted as the new target. TCPI(EAC) should be close to the current CPI if the forecast is realistic.

**Interpretation:**
- TCPI < 1.0: Current performance is sufficient to meet target
- TCPI = 1.0: Maintain current performance to meet target
- TCPI > 1.0: Improved performance needed to meet target
- TCPI > 1.5: Target likely unachievable without significant changes

### 12.4 EVM Variance Analysis

The system shall calculate and report the following variances:

Cost Variance (CV) shall be calculated as EV minus AC, with negative values indicating over-budget conditions and positive values indicating under-budget conditions. Schedule Variance (SV) shall be calculated as EV minus PV, with negative values indicating behind-schedule conditions and positive values indicating ahead-of-schedule conditions.

Variance at Completion (VAC) shall be calculated as BAC minus EAC, indicating the expected final cost variance at project completion. All variances must be calculable as both absolute values and percentages to support multiple reporting perspectives.

### 12.4A EVM Calculation Validation

The system shall validate all EVM calculations to ensure data integrity and alert users to potential anomalies:

**Metric Bounds Checking:**

- CPI (Cost Performance Index): Valid range 0-5.0, typical range 0.5-2.0
  - Warning if CPI < 0.8 (significant cost overrun)
  - Critical if CPI < 0.5 (severe cost overrun)
  - Info if CPI > 1.5 (under-budget performance)

- SPI (Schedule Performance Index): Valid range 0-5.0, typical range 0.5-2.0
  - Warning if SPI < 0.8 (significant schedule delay)
  - Critical if SPI < 0.5 (severe schedule delay)
  - Info if SPI > 1.5 (ahead-of-schedule performance)

- TCPI (To Complete Performance Index): Valid range 0-10.0
  - Warning if TCPI > 1.5 (difficult to achieve)
  - Critical if TCPI > 2.0 (likely unachievable)

**Relationship Validation:**

- BAC ≥ EV ≥ 0: Budget at Completion must be ≥ Earned Value
- EAC ≥ AC: Estimate at Completion must be ≥ Actual Cost
- EAC ≥ EV: Estimate at Completion must be ≥ Earned Value
- ETC = EAC - AC: Estimate to Complete must equal difference

**Time-Phased Data Consistency:**

- PV at control date must not exceed BAC
- EV at control date must not exceed PV (unless ahead of schedule)
- AC accumulation must be monotonic (never decrease)
- Percent complete must be between 0-100%

**Validation Actions:**

- Prevent saving data that violates hard constraints
- Warn users for soft constraint violations
- Require explanation for out-of-bounds values
- Log all validation failures for audit trail

### 12.5 Additional EVM Metrics

The system shall support multiple methods for calculating and displaying percent complete, each serving different analytical purposes:

**Percent of Budget Spent (PBS):**
Indicates what portion of the budget has been consumed.
```
PBS = AC / BAC
```
Use for: Cash flow analysis, budget utilization tracking. Values >100% indicate cost overrun.

**Percent of Work Earned (PWE):**
Indicates what portion of the work has been physically completed.
```
PWE = EV / BAC
```
Use for: Performance assessment, progress measurement. This is the primary "percent complete" metric for EVM.

**Percent of Schedule Complete (PSC):**
Indicates what portion of the planned time has elapsed.
```
PSC = (Current Date - Start Date) / Planned Duration
```
Use for: Schedule assessment, time-based progress tracking. Values >100% indicate schedule overrun.

**Comparison and Analysis:**
The system shall enable comparison of these three methods:
- PWE > PBS: Performing well (earning more than spending)
- PWE < PBS: Performing poorly (spending more than earning)
- PWE > PSC: Ahead of schedule
- PWE < PSC: Behind schedule

**Primary Metric:**
For all EVM calculations and reports, "percent complete" shall refer to Percent of Work Earned (PWE) unless otherwise specified.

### 12.5A Estimate to Complete (ETC) Calculation Methods

The system shall support multiple methods for calculating Estimate to Complete (ETC), representing the expected cost to finish remaining work:

**Bottom-Up ETC:**
Sum of detailed estimates for remaining work packages.
```
ETC = Σ(Estimated cost of each uncompleted work package)
```
Use for: Most accurate method when detailed estimates exist. Requires user input through forecast creation.

**Performance-Based ETC:**
Extrapolates based on current cost performance efficiency.
```
ETC = (BAC - EV) / CPI
```
Use for: Quick projection when performance is stable. Assumes future performance matches past CPI.

**Management Judgment ETC:**
Expert opinion-based estimate incorporating known factors.
```
ETC = Manager's estimated cost to complete
```
Use for: When significant changes are expected that historical performance doesn't reflect.

**EAC Relationship:**
All ETC methods feed into EAC calculation:
```
EAC = AC + ETC
```

**System Behavior:**
- Default ETC calculation: Performance-based (uses current CPI)
- User can override with bottom-up forecast (Section 7.1)
- System tracks which method was used for audit trail
- Historical ETC values preserved for trend analysis

### 12.6 AI-Powered Project Assessment

The system shall be able to collect all project metrics at a control date or from a baseline and generate a comprehensive assessment using an AI endpoint. This capability is provided by the AI/ML Integration bounded context (see [Architecture: Bounded Contexts](../../02-architecture/01-bounded-contexts.md#10-aiml-integration)).

**Assessment Content:**
The AI-generated assessment shall include:
- Executive summary of project status
- Key risk factors and concerns
- Performance trend analysis
- Recommendations for improvement
- Comparison to similar projects (anonymized)

**Usage:**
- Triggered on-demand by authorized users
- Requires explicit user confirmation before generation
- Results stored for historical reference
- No write access to project data (read-only analysis)

**Privacy and Security:**
- Project data anonymized before sending to external AI services
- No PII sent to external services
- AI usage audit logged
- Users can opt-out of AI features per organizational policy

## 13. Reporting and Analytics Requirements

### 13.1 Standard EVM Reports

The system shall provide standard EVM reports including Cost Performance Report showing cumulative and period performance with all key EVM metrics, Variance Analysis Report showing cost and schedule variances with trend analysis, Forecast Report showing current EAC compared to BAC with variance explanations, and Baseline Comparison Report showing performance against original and current baselines.

All reports must be available at project, WBE, and cost element levels with drill-down capabilities to access supporting detail.

### 13.2 Trend Analysis and Dashboards

The system shall provide visual dashboards displaying performance trends over time including CPI and SPI trending, forecast EAC trending, earned value versus planned value versus actual cost curves, variance trends, and quality cost trends.

Dashboards must be configurable to display data for selected projects, WBEs, departments, or time periods. Visual representations should include line graphs for trend analysis, bar charts for period comparisons, and gauge displays for current performance indices.

### 13.3 Custom Reporting and Data Export

The system shall support custom report generation allowing users to select specific data elements, define filters and groupings, specify calculation methods, and determine output formats. All data must be exportable to common formats including CSV, Excel, and PDF for further analysis or presentation.

### 13.4 Quality Cost Analysis

The system shall provide specialized reporting for quality event analysis including total quality costs by project, WBE, and department, quality cost trends over time, root cause analysis summaries, cost of quality as a percentage of total project costs, and comparison of quality costs across projects for benchmarking.

## 14. User Interface Requirements

### 14.1 Navigation and Workflow

The system shall provide intuitive navigation supporting the hierarchical project structure with clear visual representation of the project-WBE-cost element relationships. Users must be able to quickly navigate between different projects, access specific WBEs, drill down to cost element detail, and move laterally between related information.

The interface shall support common workflows including project setup and configuration, budget allocation and baseline creation, regular cost and earned value recording, periodic forecast updates, change order processing, quality event registration, and report generation and analysis.

#### 14.1.1 Time Machine Control

The interface shall include a persistent "time machine" date selector in the application header, positioned to the left of the user menu. The control defaults to the current date, supports selection of past and future dates, and determines the control date for every view and calculation. When a user adjusts the time machine date, the system must only display or aggregate records whose creation, modification, registration, or baseline date is on or before the selected control date. The selected value must be persisted per user session on the backend so that subsequent requests automatically honor the chosen date without requiring clients to restate it.

#### 14.1.2 Branch Selection Control

The interface shall include a persistent branch selector in the application header, positioned near the time machine control. The selector shall display the currently selected branch (defaulting to "main") and provide a dropdown menu listing all available branches for the current project, including the main branch and all active change order branches. When a user selects a branch:

- All views, tables, and data displays shall automatically filter to show only data from the selected branch
- The branch name shall be prominently displayed to indicate the current context
- Branch status indicators (Active, Locked, Archived) shall be visible in the selector
- Locked branches shall be visually distinguished and prevent modification operations
- The selected branch must be persisted per user session on the backend so that subsequent requests automatically honor the chosen branch without requiring clients to restate it

The branch selector must support switching between branches seamlessly, allowing users to compare different change order scenarios or return to the main branch view at any time.

### 14.2 Data Entry and Validation

All data entry screens shall provide clear field labels, contextual help text, input validation with immediate feedback, default values where appropriate, and required field indicators. The system must prevent invalid data entry and provide meaningful error messages guiding users to correct input.

For numeric fields, the system shall support appropriate precision and formatting, currency conversion where needed, and calculation assistance for derived values. Date fields must provide calendar pickers and support multiple date format preferences.

### 14.3 Dashboard and Summary Views

The system shall provide summary dashboards at project and portfolio levels showing key performance indicators, status indicators for schedule and cost performance, alerts for items requiring attention, quick access to recent activities, and links to detailed information.

Visual indicators such as color coding for performance thresholds (green for on-track, yellow for at-risk, red for critical), progress bars for completion percentages, and trend indicators (up, down, stable arrows) shall enhance information comprehension.

## 15. Data Management and Integrity Requirements

### 15.1 Data Validation Rules

The system shall enforce data integrity through comprehensive validation rules:

**Budget Allocation Validation:**
- Total WBE budgets ≤ Project budget (warning at 90%, error at 100%)
- Total cost element budgets ≤ WBE budget (warning at 90%, error at 100%)
- Revenue allocations = Total project contract value (exact match required)
- Budget values > 0 (positive values only)

**Cost Registration Validation:**
- Cost date must be within cost element start/end date range
- Cost amount must be > 0 (positive values only)
- Invoice/reference number required for costs > €1,000
- Cost category required (labor, materials, subcontracts, other)

**Date Validation:**
- Start date < End date for all time ranges
- Project start date ≤ WBE start date
- WBE start date ≤ Cost element start date
- Baseline date must be in the past (no future baselines)
- Forecast date must be in the past (warning if future)

**Hierarchical Consistency:**
- Child WBE budgets ≤ Parent WBE budget
- Cannot delete parent WBE without deleting or reassigning child WBEs
- WBE must belong to exactly one project
- Cost element must belong to exactly one WBE

**Financial Validation:**
- Currency values rounded to 2 decimal places using banker's rounding
- All monetary values in project's base currency (no multi-currency mixing)
- EAC must be ≥ AC
- EAC must be ≥ EV
- BAC must be ≥ EV
- BAC must be ≥ 0

**Cross-Currency Validation (Future):**
- When multi-currency support is added:
  - All currencies must have valid ISO 4217 codes
  - Exchange rates must be > 0
  - Conversion required for aggregation
  - Store both original and converted values

**Time Zone Validation:**
- All datetime fields include timezone (UTC storage)
- Display in user's local timezone
- Date comparisons use UTC to avoid DST issues
- Validate timezone is valid IANA timezone identifier

**EVM Metric Validation:**
(See Section 12.4A for detailed EVM validation rules)

**Validation Feedback:**
- Immediate inline validation for form fields
- Warning messages for soft constraints (allow override with explanation)
- Error messages for hard constraints (prevent save)
- Validation summary before committing changes

### 15.2 Audit Trail and History

The system must maintain complete audit trails for all data changes including what data was changed, previous and new values, who made the change, when the change occurred, and the reason for change where applicable.

The versioning system provides an integral component of the audit trail by preserving immutable version history for all entities. Each version record captures the complete state of an entity at a point in time, enabling reconstruction of entity evolution and supporting forensic analysis of data changes. For branch-enabled entities, the audit trail includes branch context, allowing tracking of changes within specific change order branches before they are merged into the main branch.

### 15.3 Data Backup and Recovery

The system shall support data backup capabilities ensuring all project, budget, cost, forecast, and event data can be backed up on demand or on scheduled intervals. The backup process must capture complete system state allowing full restoration if needed.

## 16. Security and Access Control Requirements

The system shall implement role-based access control with defined user roles including system administrator with full system access, project manager with full access to assigned projects, department manager with access to department-specific cost elements, project controller with read-only access for reporting and analysis, and executive viewer with access to summary dashboards and executive reports.

Access controls must be configurable at the project level allowing different users to have appropriate access to specific projects based on their roles and responsibilities.

## 17. Performance and Scalability Requirements

The system shall support management of at least fifty concurrent projects with each project containing up to twenty WBEs and each WBE containing up to fifteen cost elements. The system must handle thousands of cost registrations, forecast updates, and events while maintaining responsive performance.

Report generation and dashboard rendering must complete within acceptable timeframes (typically under five seconds for standard reports, under fifteen seconds for complex analytical reports) even with large data volumes.

### 17.1 System Capacity Limits

The system shall support the following capacity constraints:

**Concurrent Usage:**
- Maximum 100 concurrent users
- Maximum 50 concurrent active projects
- Maximum 20 WBEs per project
- Maximum 15 cost elements per WBE
- Maximum 3 active branches per project

**Data Volume:**
- Maximum 10,000 cost registrations per project
- Maximum 1,000 forecasts per project
- Maximum 100 change orders per project
- Maximum 50 baselines per project

**Data Retention:**
- Active project data: Permanent retention
- Completed project data: 5 years post-completion
- Audit trail data: 7 years minimum
- Branch data: Archived 1 year after merge
- Temporary session data: 30 days

### 17.2 Technical Constraints

**Database:**
- PostgreSQL 15+ with TSTZRANGE support for bitemporal queries
- Maximum database size: 500 GB per project
- Connection pool: 200 concurrent connections
- Query timeout: 30 seconds for complex queries

**Application:**
- Memory per API instance: 512 MB minimum, 2 GB recommended
- CPU: 2 cores minimum, 8 cores recommended for production
- Storage: SSD with >1000 IOPS for database
- Network: 1 Gbps for inter-service communication

**Time Zone Handling:**
- All datetime fields include timezone information (UTC storage)
- Display in user's local timezone
- Support for international projects with multiple timezones
- Daylight saving time automatically handled

**Concurrency Model:**
- All database operations use async/await patterns
- API endpoints support concurrent request handling
- Optimistic concurrency control for entity updates
- Pessimistic locking for branch merge operations

## 18. Technical Considerations

The system shall be developed as a web-based application accessible through modern web browsers without requiring client-side software installation. The application must be responsive and functional on desktop computers and tablets to support field access by project managers and site personnel.

Data persistence must ensure that all entered information is preserved reliably. The system should implement appropriate data validation on both client and server sides to ensure data quality and consistency.

### 18.1 Technology Stack

The system shall be built using the following technology stack:

**Backend:**
- Language: Python 3.12+
- Framework: FastAPI
- Database: PostgreSQL 15+ with TSTZRANGE support
- ORM: SQLAlchemy 2.0 with async support
- Migrations: Alembic
- Authentication: JWT with Pydantic validation

**Frontend:**
- Language: TypeScript 5+ (strict mode)
- Framework: React 18
- Build Tool: Vite
- State Management: TanStack Query (server), Zustand (client)
- Routing: React Router v6
- Component Library: Custom components with Material Design guidelines

**Infrastructure:**
- Containerization: Docker
- Reverse Proxy: Nginx
- Process Manager: Gunicorn (production), Uvicorn (development)
- Monitoring: Application Performance Monitoring (APM) solution
- Logging: Structured JSON logs

### 18.2 Integration Points

**External Integrations (Future):**
- ERP systems for cost data import (REST API)
- Project scheduling tools for schedule integration (CSV/API)
- Document management systems (WebDAV)
- Email services for notifications (SMTP)

**Internal Integrations:**
- OpenAPI specification auto-generated at `/docs` and `/openapi.json`
- WebSocket support for real-time updates (future)
- Webhook support for event notifications (future)

## 19. Future Enhancement Considerations

While not required for the initial implementation, the system architecture should accommodate future enhancements including integration with enterprise resource planning systems for automated cost data import, integration with project scheduling tools for automated earned value calculations based on schedule progress, multi-currency support for international projects, resource management capabilities tracking labor hours and material quantities, risk management integration linking identified risks to cost and schedule contingencies, and portfolio-level analytics aggregating performance across multiple projects.

### Enhanced Forecast Wizard Interface

As a future enhancement, the system may provide a multi-step forecast wizard to guide users through complex forecast creation. The wizard would include:
- Step 1: Forecast type selection with recommendations
- Step 2: EAC entry with contextual information (BAC, AC, EV, current CPI/SPI)
- Step 3: Assumptions documentation with template prompts
- Step 4: Review and confirmation with variance analysis

This enhancement would improve user experience for complex forecast scenarios while maintaining the core CRUD interface as the primary method for forecast management.

## 20. Success Criteria

The application will be considered successful when it meets the following measurable criteria:

### 20.1 Functional Success Metrics

**EVM Calculation Accuracy:**
- EVM calculations match manual calculations within ±0.1%
- All EVM metrics validated against test cases
- Zero calculation errors in production for 30 days

**Simulation Capabilities:**
- Successfully simulate 50 concurrent projects
- Handle project structures with 20 WBEs × 15 cost elements
- Process 1,000 cost registrations per minute without degradation

**Reporting Performance:**
- Standard reports generated in <5 seconds (95th percentile)
- Complex reports generated in <15 seconds (95th percentile)
- Zero report generation failures

### 20.2 User Adoption Metrics

**Adoption Targets:**
- 80% of project managers using system within 3 months of launch
- 60% of department leads using system within 6 months
- Average 10 sessions per active user per week
- <5% user-reported critical bugs per month

**User Satisfaction:**
- Net Promoter Score (NPS) ≥ 40 after 6 months
- User satisfaction survey score ≥ 4.0/5.0
- Average task completion time <2 minutes
- <10% user error rate for data entry

### 20.3 Business Impact Metrics

**Process Improvements:**
- 50% reduction in time spent on manual EVM calculations
- 75% reduction in spreadsheet-based tracking
- 90% of projects using baselines for performance tracking
- 100% of change orders tracked in system

**Decision Support:**
- 80% of project reviews using system-generated reports
- 60% improvement in early issue identification
- 30% reduction in project cost overruns (measured after 12 months)
- 25% improvement in schedule performance (measured after 12 months)

### 20.4 Technical Success Metrics

**System Reliability:**
- 99.5% uptime during business hours
- <1% data error rate
- <5 second average response time for API calls
- Zero data loss incidents

**Code Quality:**
- 80%+ test coverage maintained
- Zero critical security vulnerabilities
- All linting and type checking passing (zero errors)
- Code review approval rate >95%

### 20.5 Training Success Metrics

**Training Effectiveness:**
- 90% of users complete onboarding training
- Average training time <4 hours per user
- <10% of users require follow-up training
- Training satisfaction score ≥ 4.0/5.0

**Knowledge Transfer:**
- 100% of project managers pass EVM principles assessment
- 75% of users can navigate system without assistance after training
- <20% support ticket rate per user in first 90 days

## 21. Business Constraints

### 21.1 Financial Constraints

**Currency Handling:**
- Base currency: Euro (EUR) for all projects
- Currency display: Use € symbol with 2 decimal places (€1,234.56)
- Rounding: Banker's rounding (round half to even) for all calculations
- Negative values: Display in parentheses (€(1,234.56))

**Approval Authority:**
- Project managers: Approve changes up to €10K
- Department heads: Approve changes €10K-€50K
- Directors: Approve changes €50K-€100K
- Executive committee: Approve changes >€100K

**Budget Constraints:**
- Hard budget cap: Cannot exceed allocated budget without formal change order
- Contingency: 10% contingency budget recommended
- Reserve: 5% management reserve for executive authorization

### 21.2 Organizational Constraints

**User Roles and Permissions:**
(See Section 16 for detailed role definitions)

**Working Hours and SLAs:**
- Business days: Monday-Friday excluding holidays
- Business hours: 08:00-18:00 CET
- Approval SLAs: As defined in Section 8.3 approval matrix
- Support response: <4 hours for critical issues, <24 hours for non-critical

**Geographic Constraints:**
- Primary timezone: Central European Time (CET/CEST)
- Supported languages: English (primary), Italian (secondary)
- Multi-site support: System must support projects across multiple timezones

### 21.3 Compliance Constraints

**Data Retention:**
- Financial records: 7 years minimum (legal requirement)
- Audit trails: 7 years minimum
- Project data: 5 years post-completion
- User data: GDPR compliant (30 days after account deletion)

**Accessibility:**
- WCAG 2.1 AA compliance required
- Screen reader compatible
- Keyboard navigation support
- Color blind friendly palette

### 21.4 Contractual Constraints

**Customer Deliverables:**
- Monthly progress reports (EVM metrics)
- Quarterly executive summaries
- Final project report with variance analysis
- Baseline comparison reports on request

**Intellectual Property:**
- All project data owned by customer
- No customer data used for AI training without explicit consent
- Benchmarking data anonymized before cross-project comparison
