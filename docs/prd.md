# Product Requirements Document: Project Budget Management & EVM Analytics System

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

### 4.3 Cost Element Structure

Within each WBE, the system shall support the creation of multiple cost elements, each representing a specific department or discipline responsible for delivering portions of the work. Cost elements must include department identification (such as Mechanical Engineering, Electrical Engineering, Software Development, Procurement, Assembly, and Commissioning), budget allocation, resource assignments, and planned value distribution over time.

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

For each cost element, the system shall support versioned schedule registrations that define the planned progression of work over time. Each registration must include a start date, end date, progression type, user-provided registration date, and optional description so that users can record the business context driving the change. Users must be able to perform full CRUD operations on schedule registrations while retaining historical entries.

The system shall support the following progression types: linear (even distribution over the duration), gaussian (normal distribution curve with peak at midpoint), and logarithmic (slow start with accelerating completion). The planned value engine shall always use the schedule registration with the most recent registration date (ties resolved by creation time) whose registration date is on or before the control date.

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

The system shall support the creation and maintenance of cost forecasts at the cost element level. Users must be able to create new forecasts at any point during project execution, with each forecast representing the Estimate at Completion (EAC) for the cost element based on current performance and anticipated future conditions.

Each forecast entry must include the forecast date, the revised estimate at completion, the estimate to complete (ETC) from the current point, assumptions underlying the forecast, and the responsible estimator. The system shall maintain a complete history of all forecasts to enable trend analysis and forecast accuracy assessment.

### 7.2 Forecast Updates and Versioning

The system must allow forecasts to be updated periodically for each WBE and cost element as project conditions change. Each update shall create a new forecast version while preserving historical forecasts for comparison and analysis. The system shall track forecast variance trends over time and provide alerts when forecast changes exceed defined thresholds.

## 8. Change Order Management Requirements

### 8.1 Change Order Processing

The system shall provide comprehensive change order management capabilities to handle scope changes, contract modifications, and customer-requested additions. Each change order must be created with a unique identifier, description of the change, requesting party, justification, and proposed effective date.

Change orders must support modifications to both costs and revenues. When a change order is approved and implemented, the system shall update the affected WBE budgets, cost element allocations, and revenue assignments accordingly. The system must maintain the original baseline data while clearly tracking the impact of approved changes on current budgets and forecasts.

### 8.2 Change Order Impact Analysis

Before finalizing change orders, the system shall provide impact analysis showing the effect on project budgets, WBE allocations, cost element budgets, revenue recognition, schedule implications, and EVM performance indices. Users must be able to model change order impacts before formal approval.

### 8.3 Change Order Approval Workflow

The system shall track change order status through defined workflow states including draft, submitted for approval, under review, approved, rejected, and implemented. Each status transition must be recorded with timestamp and responsible user information.

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

The system shall support the creation of cost and schedule baselines at significant project milestones. Baseline events must be configurable but shall include at minimum the following standard milestones: project kickoff, bill of materials release, engineering completion, procurement completion, manufacturing start, shipment, site arrival, commissioning start, commissioning completion, and project closeout.

Each baseline creation event must capture the baseline date, event description, event classification (milestone type), responsible department or function, and a snapshot of all current budget, cost, revenue, earned value, percent complete, and forecast data for all WBEs and cost elements.

Baseline metadata (including owning department, `is_pmb` flag, cancellation status, and milestone classification) shall be stored directly on the **Baseline Log** record, which serves as the single source of truth for baseline identity. Detailed financial snapshots, including the latest physical percent complete and earned value for each cost element, remain in **Baseline Cost Element** records referencing the associated `baseline_id`.

### 10.2 Baseline Comparison and Variance Analysis

The system shall maintain all historical baselines and provide comparison capabilities to analyze changes between any two baselines or between any baseline and current actuals. Variance analysis must be available at project, WBE, and cost element levels, showing changes in budgets, costs, revenues, forecasts, and performance metrics between baseline periods.

Baseline comparisons shall leverage the consolidated Baseline Log data model (Baseline Log + Baseline Cost Elements) without reliance on a separate Baseline Snapshot table. Any historical reporting must read from these canonical sources.

### 10.3 Performance Measurement Baseline (PMB)

The system shall maintain a Performance Measurement Baseline in accordance with EVM principles. The PMB shall represent the time-phased budget plan against which performance is measured. The system must track changes to the PMB resulting from approved change orders while maintaining the original baseline for historical reference and variance analysis.

## 11. Event Data Model Requirements

All events in the system (cost registrations, forecast updates, change orders, quality events, and baseline creation events) shall adhere to a consistent data model including the following attributes:

Each event must have a unique system-generated identifier, a user-defined event date representing when the event occurred or was effective, a detailed description of the event providing context and rationale, a classification or category appropriate to the event type, and an assigned department or organizational unit responsible for or associated with the event.

Additional attributes may include the user who created or registered the event, creation timestamp, last modification timestamp, approval status where applicable, attached supporting documentation or references, and links to related events or project artifacts.

The system shall maintain complete event history with no ability to delete events, supporting full audit trail requirements. Events may be modified or cancelled, but all changes must be tracked with version history.

## 12. Earned Value Management Requirements

### 12.1 EVM Terminology and Compliance

The system shall fully implement Earned Value Management principles using standard EVM terminology as defined by industry standards including the ANSI/EIA-748 standard. All calculations, reports, and user interfaces shall use proper EVM terminology consistently.

### 12.2 Core EVM Metrics

The system must calculate and maintain the following core EVM metrics for each cost element, WBE, and at the project level:

Planned Value (PV), also known as Budgeted Cost of Work Scheduled (BCWS), represents the authorized budget assigned to scheduled work and shall be calculated from the cost element schedule baseline. The system shall calculate PV using the formula $PV = BAC \times \%\ \text{di completamento pianificato}$, where BAC is the Budget at Completion of the cost element and the planned completion percentage is determined from the schedule baseline (start date, end date, and progression type) at the control date. For example, if $BAC = €100{,}000$ and at month 2 the planned completion is 40%, then $PV = 100{,}000 \times 0{,}40 = €40{,}000$. The progression type (linear, gaussian, logarithmic) determines how the planned completion percentage is calculated between the start and end dates.

Earned Value (EV), also known as Budgeted Cost of Work Performed (BCWP), represents the budgeted cost of work actually performed at the control date and shall be calculated from the baselined percentage of work completed. The system shall calculate EV using the formula $EV = BAC \times \%\ \text{di completamento fisico}$, where the physical completion percentage is based on recorded earned value entries. For example, if a cost element has $BAC = €100{,}000$ and is 30% physically complete, then $EV = 100{,}000 \times 0{,}30 = €30{,}000$. At the project level, the same formula applies using the aggregated budget and completion percentage.

Actual Cost (AC) represents the realized cost incurred for work performed and shall be calculated from all registered costs including quality event costs.

Budget at Completion (BAC) represents the total planned budget for the work scope and shall be maintained as the sum of all allocated budgets adjusted for approved changes. Estimate at Completion (EAC) represents the expected total cost at project completion and shall be calculated using current forecasts. Estimate to Complete (ETC) represents the expected cost to finish remaining work and shall be calculated as EAC minus AC.

### 12.3 EVM Performance Indices

The system shall calculate the following performance indices:

Cost Performance Index (CPI) shall be calculated as EV divided by AC, indicating cost efficiency. A CPI greater than one indicates under-budget performance, while less than one indicates over-budget conditions. Schedule Performance Index (SPI) shall be calculated as EV divided by PV, indicating schedule efficiency. An SPI greater than one indicates ahead-of-schedule performance, while less than one indicates behind-schedule conditions.

To Complete Performance Index (TCPI) shall be calculated to project the cost performance required on remaining work to meet budget goals. The system shall calculate TCPI based on BAC as (BAC minus EV) divided by (BAC minus AC), and also calculate TCPI based on EAC as (BAC minus EV) divided by (EAC minus AC).

### 12.4 EVM Variance Analysis

The system shall calculate and report the following variances:

Cost Variance (CV) shall be calculated as EV minus AC, with negative values indicating over-budget conditions and positive values indicating under-budget conditions. Schedule Variance (SV) shall be calculated as EV minus PV, with negative values indicating behind-schedule conditions and positive values indicating ahead-of-schedule conditions.

Variance at Completion (VAC) shall be calculated as BAC minus EAC, indicating the expected final cost variance at project completion. All variances must be calculable as both absolute values and percentages to support multiple reporting perspectives.

### 12.5 Additional EVM Metrics

The system shall support calculation of percent complete using multiple methods including percent of budget spent (AC divided by BAC), percent of work earned (EV divided by BAC), and percent of schedule complete (Current Date minus Start Date divided by Planned Duration).

The system must calculate Estimate to Complete (ETC) using multiple methods including bottom-up detailed estimates from forecasts, ETC calculated as (BAC minus EV) divided by CPI for performance-based projections, and ETC calculated using management judgment factors when appropriate.

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

The interface shall include a persistent “time machine” date selector in the application header, positioned to the left of the user menu. The control defaults to the current date, supports selection of past and future dates, and determines the control date for every view and calculation. When a user adjusts the time machine date, the system must only display or aggregate records whose creation, modification, registration, or baseline date is on or before the selected control date. The selected value must be persisted per user session on the backend so that subsequent requests automatically honor the chosen date without requiring clients to restate it.

### 14.2 Data Entry and Validation

All data entry screens shall provide clear field labels, contextual help text, input validation with immediate feedback, default values where appropriate, and required field indicators. The system must prevent invalid data entry and provide meaningful error messages guiding users to correct input.

For numeric fields, the system shall support appropriate precision and formatting, currency conversion where needed, and calculation assistance for derived values. Date fields must provide calendar pickers and support multiple date format preferences.

### 14.3 Dashboard and Summary Views

The system shall provide summary dashboards at project and portfolio levels showing key performance indicators, status indicators for schedule and cost performance, alerts for items requiring attention, quick access to recent activities, and links to detailed information.

Visual indicators such as color coding for performance thresholds (green for on-track, yellow for at-risk, red for critical), progress bars for completion percentages, and trend indicators (up, down, stable arrows) shall enhance information comprehension.

## 15. Data Management and Integrity Requirements

### 15.1 Data Validation Rules

The system shall enforce data integrity through validation rules including total WBE budgets not exceeding project budgets, total cost element budgets within each WBE not exceeding WBE allocation, revenue allocations reconciling to total project contract value, actual costs not being recorded before cost element start dates, and earned value not exceeding planned value for cost elements without proper authorization.

### 15.2 Audit Trail and History

The system must maintain complete audit trails for all data changes including what data was changed, previous and new values, who made the change, when the change occurred, and the reason for change where applicable. Audit trails must be permanent and cannot be deleted or modified by users.

### 15.3 Data Backup and Recovery

The system shall support data backup capabilities ensuring all project, budget, cost, forecast, and event data can be backed up on demand or on scheduled intervals. The backup process must capture complete system state allowing full restoration if needed.

## 16. Security and Access Control Requirements

The system shall implement role-based access control with defined user roles including system administrator with full system access, project manager with full access to assigned projects, department manager with access to department-specific cost elements, project controller with read-only access for reporting and analysis, and executive viewer with access to summary dashboards and executive reports.

Access controls must be configurable at the project level allowing different users to have appropriate access to specific projects based on their roles and responsibilities.

## 17. Performance and Scalability Requirements

The system shall support management of at least fifty concurrent projects with each project containing up to twenty WBEs and each WBE containing up to fifteen cost elements. The system must handle thousands of cost registrations, forecast updates, and events while maintaining responsive performance.

Report generation and dashboard rendering must complete within acceptable timeframes (typically under five seconds for standard reports, under fifteen seconds for complex analytical reports) even with large data volumes.

## 18. Technical Considerations

The system shall be developed as a web-based application accessible through modern web browsers without requiring client-side software installation. The application must be responsive and functional on desktop computers and tablets to support field access by project managers and site personnel.

Data persistence must ensure that all entered information is preserved reliably. The system should implement appropriate data validation on both client and server sides to ensure data quality and consistency.

## 19. Future Enhancement Considerations

While not required for the initial implementation, the system architecture should accommodate future enhancements including integration with enterprise resource planning systems for automated cost data import, integration with project scheduling tools for automated earned value calculations based on schedule progress, multi-currency support for international projects, resource management capabilities tracking labor hours and material quantities, risk management integration linking identified risks to cost and schedule contingencies, and portfolio-level analytics aggregating performance across multiple projects.

## 20. Success Criteria

The application will be considered successful when it enables the Project Management Directorate to accurately simulate complex project scenarios, validate proposed business rules and performance metrics under various conditions, identify potential issues in financial management processes before production implementation, generate accurate EVM calculations and reports matching manual calculation results, support training of project personnel on EVM principles and organizational financial management processes, and provide a foundation for continuous improvement of project financial management practices.

The system must be intuitive enough that project managers and department leaders can use it effectively with minimal training while providing sufficient depth and analytical capability to support sophisticated financial analysis and decision making.
