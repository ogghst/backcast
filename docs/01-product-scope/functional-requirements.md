# Functional Requirements

**Last Updated:** 2025-12-29  
**Source:** Product Requirements Document (PRD)  
**Status:** Active

This document specifies the functional requirements for the Backcast EVS system, organized by feature domain.

---

## 1. Project Structure Management

### 1.1 Project Creation

- Users shall create projects with metadata: name, customer, contract value, start date, completion date, project manager
- Each project serves as top-level container for financial data

### 1.2 Work Breakdown Elements (WBEs)

- Projects contain multiple WBEs representing individual machines/deliverables
- Each WBE captures: machine type, serial number, delivery date, revenue allocation
- WBEs are independent organizational units for budget allocation and performance measurement
- Support CRUD operations on WBEs while maintaining parent project relationship

### 1.3 Cost Elements

- WBEs contain multiple cost elements representing departmental responsibilities
- Cost elements include: department ID, budget allocation, resource assignments, planned value distribution
- Cost elements are the most granular level of budget tracking and cost imputation

---

## 2. Revenue Management

### 2.1 Revenue Allocation

- Assign total project revenue and distribute across WBEs based on contracted values
- Revenue captured at WBE level, distributed to cost elements based on planned work value
  -Warnings when total allocated budgets exceed available project budgets or WBE budgets exceed allocated revenues

### 2.2 Revenue Recognition Planning

- Support time-phased revenue recognition schedules aligned with planned work completion
- Forms basis for Planned Value (PV) calculations in EVM framework

---

## 3. Cost Management

### 3.1 Budget Definition

- Establish initial budgets at cost element level (Budget at Completion - BAC)
- Support time-phased budget consumption plans
- Maintain budget allocation integrity with validation

### 3.2 Cost Element Schedule Baseline

- **Versioned schedule registrations** defining planned work progression
- Each registration: start date, end date, progression type (linear/gaussian/logarithmic), registration date, description
- Full CRUD on schedule registrations while retaining history
- System uses latest registration (by registration_date ≤ control_date) for planning calculations
- Baseline snapshots preserve schedule registrations immutably

### 3.3 Cost Registration

- Register actual costs: date, amount, category (labor/materials/subcontracts/other), invoice reference, notes
- Updates Actual Cost (AC) for cost elements and WBEs
- Complete audit trail with timestamps and user attribution

### 3.4 Earned Value Recording

- Record physical work completion percentage for cost elements
- Each entry: completion date, percent complete, deliverables, notes
- Calculate EV using: `EV = BAC × % physical completion`
- Baseline snapshots capture latest earned value for trend analysis

---

## 4. Forecasting

### 4.1 Forecast Creation and Management

- CRUD interface for cost forecasts at cost element level
- Forecasts represent Estimate at Completion (EAC)
- Required fields: forecast_date (past only), EAC value, ETC (calculated), forecast type (bottom_up/performance_based/management_judgment), assumptions, estimator
- Maximum 3 forecast dates per cost element
- Complete history ordered by forecast_date descending

### 4.2 Forecast Wizard

- Multi-step guided interface for complex forecast scenarios
- Steps: type selection, EAC entry with context, assumptions, review/confirmation

---

## 5. Change Order Management

### 5.1 Change Order Processing

- Create change orders: unique ID, description, requesting party, justification, effective date
- Support modifications to costs AND revenues
- Update affected WBE budgets, cost element allocations, revenue assignments upon approval
- Maintain original baseline while tracking impact

### 5.2 Change Order Impact Analysis

- Model impacts on: budgets, allocations, revenue recognition, schedule, EVM indices
- Available before formal approval

### 5.3 Change Order Approval Workflow

- Workflow states: draft → submitted → under review → approved/rejected → implemented
- Record each status transition with timestamp and responsible user

### 5.4 Branching and Versioning System

See [Branching Requirements](branching-requirements.md) for comprehensive details.

**Summary:**

- Composite PK versioning: `(id, branch)` or `(head_id, valid_from)`
- Branch types: main (production), co-{id} (change orders)
- Operations: branch creation (deep copy), comparison, merging, locking
- Time-travel queries for historical state reconstruction
- Entity lifecycle: create, update, soft delete, restore, hard delete
- Merged view service for impact visualization

---

## 6. Quality Event Management

### 6.1 Quality Event Recording

- Register quality events causing additional costs without revenue increase
- Types: rework, defect correction, warranty work
- Capture: event date, description, root cause, responsible department, estimated/actual cost, corrective actions, preventive measures
- Link to cost elements for cost attribution

### 6.2 Quality Event Cost Tracking

- Register quality costs separately from planned work costs
- Include in AC calculations
- Enable quality cost analysis and reporting

### 6.3 EVM Impact

- Quality costs affect cost variances and CPI without adjusting PV or revenue
- Provides visibility into quality impact on project performance

---

## 7. Baseline Management

### 7.1 Baseline Creation

- Create baselines at project milestones: kickoff, BOM release, engineering completion, procurement completion, manufacturing start, shipment, site arrival, commissioning start/completion, closeout
- Capture: date, description, event classification, responsible department/function
- Snapshot all budget, cost, revenue, earned value, percent complete, forecast data
- Baseline Log as single source of truth for baseline metadata

### 7.2 Baseline Comparison

- Maintain all historical baselines
- Compare any two baselines or baseline vs. current actuals
- Variance analysis at project/WBE/cost element levels
- Changes in: budgets, costs, revenues, forecasts, performance metrics

### 7.3 Performance Measurement Baseline (PMB)

- Time-phased budget plan for performance measurement (EVM compliance)
- Track PMB changes from approved change orders
- Maintain original baseline for historical reference

---

## 8. Event Data Model

All events (cost registrations, forecasts, change orders, quality events, baselines) share common attributes:

- Unique system-generated ID
- User-defined event date (when occurred/effective)
- Detailed description (context, rationale)
- Classification/category
- Assigned department/organizational unit
- Creator, creation timestamp, last modified timestamp
- Approval status (where applicable)
- Supporting documentation/references
- Links to related events/artifacts

**Immutability:** Events cannot be deleted (may be modified/cancelled with full version history)

---

## 9. User Interface

### 9.1 Navigation and Workflow

- Intuitive hierarchical navigation (Project → WBE → Cost Element)
- Quick navigation between projects, WBEs, cost elements
- Support workflows: project setup, budget allocation, baseline creation, cost/EV recording, forecast updates, change orders, quality events, reporting

### 9.2 Time Machine Control

- Persistent date selector in application header (left of user menu)
- Defaults to current date
- Determines control date for all views and calculations
- Displays only records with date ≤ selected control date
- Persisted per user session (backend)

### 9.3 Branch Selection Control

- Persistent branch selector in header (near time machine)
- Default: "main"
- Dropdown lists all branches (main + active change order branches)
- All views filter by selected branch
- Branch status indicators (active/locked/merged)
- Locked branches: read-only, visually distinguished
- Seamless branch switching
- Persisted per user session

### 9.4 Data Entry and Validation

- Clear field labels, contextual help, immediate feedback
- Default values, required field indicators
- Meaningful error messages
- Numeric: precision, formatting, currency conversion, calculation assistance
- Currency: All monetary values shall be displayed in Euros (€) using the symbol "€"
- Dates: calendar pickers, format preferences

### 9.5 Dashboards

- Project/portfolio level summaries
- KPIs, status indicators (schedule/cost performance)
- Alerts for items requiring attention
- Quick access to recent activities
- Color coding (green/yellow/red), progress bars, trend indicators

---

## 10. Data Management

### 10.1 Data Validation Rules

- Total WBE budgets ≤ project budgets
- Total cost element budgets per WBE ≤ WBE allocation
- Revenue allocations reconcile to total contract value
- Actual costs not recorded before cost element start dates
- Earned value not exceeding planned value (without authorization)

### 10.2 Audit Trail

- Track: what changed, previous/new values, who, when, why (if applicable)
- Permanent, non-deletable
- Versioning system provides immutable version history
- Branch context included for branch-enabled entities

### 10.3 Backup and Recovery

- On-demand and scheduled backups
- Capture complete system state
- Full restoration capability

---

## 11. Security and Access Control

### 11.1 Role-Based Access Control (RBAC)

- **System Administrator:** Full system access
- **Project Manager:** Full access to assigned projects
- **Department Manager:** Access to department cost elements
- **Project Controller:** Read-only for reporting/analysis
- **Executive Viewer:** Summary dashboards and executive reports

### 11.2 Project-Level Configuration

- Configurable access per project based on roles and responsibilities

---

## 12. Performance and Scalability

### 12.1 Capacity

- Support ≥ 50 concurrent projects
- Each project: up to 20 WBEs
- Each WBE: up to 15 cost elements
- Handle thousands of cost registrations, forecast updates, events

### 12.2 Response Time Targets

- Standard reports: < 5 seconds
- Complex analytical reports: < 15 seconds
- Maintain performance with large data volumes

---

## 13. Technical Considerations

### 13.1 Platform

- Web-based application
- Modern web browsers (no client-side software installation)
- Responsive: desktop computers and tablets
- Field access support for project managers/site personnel

### 13.2 Data Persistence

- Reliable preservation of all entered information
- Client and server-side validation
- Data quality and consistency enforcement

---

**See Also:**

- [EVM Requirements](evm-requirements.md) - Detailed EVM calculations and reporting
- [Branching Requirements](branching-requirements.md) - Complete versioning/branching specification
- [Glossary](glossary.md) - Term definitions and acronyms
