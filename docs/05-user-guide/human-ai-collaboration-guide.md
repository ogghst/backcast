# Human-AI Collaboration in Industrial Automation Project Management

## A Backcast Platform Guide

**Version:** 1.0.0
**Last Updated:** 2026-06-09
**Target Audience:** Executives, PMO Directors, Project Managers, Department Heads, Project Controllers

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Organizational Roles and Responsibilities](#2-organizational-roles-and-responsibilities)
3. [The AI Assistant: Capabilities and Boundaries](#3-the-ai-assistant-capabilities-and-boundaries)
4. [Phase-by-Phase Collaboration Guide](#4-phase-by-phase-collaboration-guide)
   - 4.1 [Order Acquisition and Proposal](#41-order-acquisition-and-proposal)
   - 4.2 [Project Initiation and Planning](#42-project-initiation-and-planning)
   - 4.3 [Engineering and Design](#43-engineering-and-design)
   - 4.4 [Procurement and Supply Chain](#44-procurement-and-supply-chain)
   - 4.5 [Manufacturing and Assembly](#45-manufacturing-and-assembly)
   - 4.6 [Site Installation and Commissioning](#46-site-installation-and-commissioning)
   - 4.7 [Project Monitoring and Control (Cross-Cutting)](#47-project-monitoring-and-control-cross-cutting)
   - 4.8 [Project Closeout and Lessons Learned](#48-project-closeout-and-lessons-learned)
5. [Change Management and Governance](#5-change-management-and-governance)
6. [Earned Value Management Integration](#6-earned-value-management-integration)
7. [Integration with Corporate Tool Landscape](#7-integration-with-corporate-tool-landscape)
8. [Best Practices for Human-AI Collaboration](#8-best-practices-for-human-ai-collaboration)
9. [Appendix A: Glossary of PMI Terms](#appendix-a-glossary-of-pmi-terms)
10. [Appendix B: RACI Matrix Template](#appendix-b-raci-matrix-template)

---

## 1. Executive Summary

Industrial automation projects for end-of-line manufacturing systems are among the most complex capital undertakings in modern industry. They span multiple engineering disciplines, involve long procurement lead times, require precise coordination between factories and installation sites, and carry significant financial exposure from the moment a proposal is submitted through final commissioning and handover.

Backcast is a collaborative project budget management and Earned Value Management (EVM) platform purpose-built for this domain. It provides your team with AI assistants that understand your project management world — ANSI/EIA-748-compliant cost control, a structured Work Breakdown Structure (WBS), formal change management with branch isolation, and complete audit trails for every financial decision. The AI assistant knows your terminology, your approval thresholds, and your reporting standards.

This guide describes how human project team members collaborate with AI assistants that are tailored to how they work. The AI assistant is configured like a team member's job description — it knows which information is needed for a change order, what a low CPI means for your project, and how to present findings to your Change Control Board. It accelerates data preparation, identifies risks, generates forecasts, and produces analyses that humans review, validate, and act upon. Every significant decision remains firmly in human hands.

The collaborative model follows three principles:

- **Human-in-the-loop for all approvals.** The AI can draft, calculate, and recommend. Only authorized humans can approve, reject, or commit.
- **Transparency through complete audit trails.** Every action -- whether performed by a human or by the AI at a human's request -- is recorded with who did what, when, and why.
- **Role-based access control (RBAC).** Access is scoped to each person's organizational role and project responsibilities. The AI operates within the same permission boundaries as the human user who initiated the request.

---

## 2. Organizational Roles and Responsibilities

Backcast defines five organizational roles that map directly to standard PMI project governance structures. Each role carries specific responsibilities aligned with PMBOK knowledge areas.

### 2.1 Role Definitions

| Role | PMI Equivalent | Primary Responsibilities |
|------|---------------|------------------------|
| **System Administrator** | IT Operations / System Owner | System configuration, user management, organizational unit management, cost element type definitions, change order workflow configuration, data integrity, branch recovery |
| **Project Manager** | Project Manager | Project creation and planning, WBS structure definition, budget allocation, schedule baseline management, change order submission, forecast approval, progress reporting, stakeholder communication |
| **Department Manager** | Functional Manager | Department-specific cost element oversight, approval of change orders up to defined thresholds, resource allocation within department, technical review of cost estimates |
| **Project Controller** | Project Controller / Cost Engineer | Read-only analysis, EVM performance reporting, variance analysis, forecast review, trend monitoring, quality cost reporting |
| **Executive Viewer** | Sponsor / Steering Committee | Read-only access to dashboards, summary reports, and project health indicators. Approval authority for critical-tier change orders |

### 2.2 Organizational Structure

The organizational hierarchy in Backcast mirrors the typical industrial automation company structure:

| Department | Sub-Units |
|---|---|
| **Engineering** | Mechanical Engineering (Design Team, Analysis Team), Electrical Engineering |
| **Project Management** | — |
| **Quality Assurance** | Incoming Inspection, Final Inspection |
| **Procurement** | Supplier Management |

Each Control Account in the WBS represents the intersection of a Work Breakdown Element (what is being delivered) and an Organizational Unit (who is responsible). This alignment with ANSI/EIA-748 ensures that budget authority and technical responsibility are always paired.

### 2.3 The AI Assistant's Role

The AI assistant is not an additional organizational role — it is a team member configured to support existing role-holders. Three assistant personas are available, each understanding the responsibilities and boundaries of the organizational role it supports:

| Assistant Persona | Aligned Role | Access Level | Purpose |
|---|---|---|---|
| **Friendly Project Analyzer** | Project Controller, Executive Viewer | Read-only | Analysis, EVM reporting, trend visualization, plain-language explanations |
| **Senior Project Manager** | Project Manager, Department Manager | Read-write | All project operations including create/update workflows, change orders, forecasts, and progress tracking |
| **System Manager** | System Administrator | Administrative | User management, organizational unit configuration, master data setup |

The assistant persona determines what the AI can do on behalf of the user. A Project Controller working with the Friendly Project Analyzer cannot accidentally modify budget data, because that persona has no write access.

---

## 3. The AI Assistant: Capabilities and Boundaries

### 3.1 What the AI Can Do

The AI assistant provides the following capabilities through a natural-language conversational interface. It already understands your project structure, your EVM methodology, and your change governance procedures — so you can focus on the decision, not the data gathering:

**Analysis and Reporting**
- Calculate and explain all EVM metrics (Cost Performance Index, Schedule Performance Index, Cost Variance, Schedule Variance, Estimate at Completion, Variance at Completion, To Complete Performance Index)
- Generate variance analysis reports at project, WBS, Control Account, Work Package, and Cost Element levels
- Produce trend analyses and performance predictions
- Compare baseline performance across different milestone snapshots
- Generate visual diagrams of project structures, cost breakdowns, and hierarchies

**Data Management**
- Create, update, and search all project entities (Projects, WBS Elements, Control Accounts, Work Packages, Cost Elements)
- Record cost registrations, cost events, and progress entries
- Create and update forecasts with supporting justification
- Manage change orders from draft through approval workflow
- Perform batch operations for efficient data entry

**Change Management Support**
- Generate change order drafts from natural-language descriptions
- Perform impact analysis on proposed changes (budget, schedule, EVM)
- Compare branch states to show exactly what a change order would modify
- Draft justification text based on impact analysis findings

**Temporal Analysis**
- View project data as of any historical date ("show me the budget as of March 15")
- Switch between the main project branch and change order branches
- Toggle between isolated view (only changed entities) and merged view (composite future state)

**Document and Quality Management**
- Search and retrieve project documents
- Track Cost of Quality (COQ) across quality events
- Generate quality cost summaries and root cause reports

### 3.2 What the AI Cannot Do

The AI understands where its authority ends. The following actions are reserved exclusively for human decision-makers — the AI will always defer to the accountable person:

| Restricted Action | Reason |
|---|---|
| Approve or reject change orders | Requires human judgment on commercial, technical, and relational factors |
| Sign off baselines | Baselines represent contractual commitments |
| Commit to forecasts | Financial commitments require accountable human authority |
| Authorize budget transfers | Cross-functional resource decisions require management consensus |
| Override approval workflows | Governance controls exist to protect organizational interests |
| Make commitments to clients or suppliers | Commercial commitments require human authority |
| Delete data without human confirmation | All destructive operations require explicit human approval |

### 3.3 Human-in-the-Loop Principles

Every write operation performed by the AI follows a confirmation protocol:

1. **Preview.** The AI presents the proposed change with full context -- what will change, the previous values, and the new values.
2. **Confirm.** The user must explicitly approve the action. For destructive operations (deletions, high-risk changes), a separate confirmation dialog is required.
3. **Audit.** The completed action is recorded in the immutable audit trail with the human user identified as the responsible party, along with the AI assistant's role.

The AI also supports three delegation levels — chosen by the user at the start of each chat session, not locked by an administrator (see the *Configuration Guide*, Section 4.2 for the full description):

| Delegation Level | Behavior | When to Choose |
|---|---|---|
| **Supervised** | The AI can analyze and report but cannot modify any project data. | Executive reviews, stakeholder demonstrations, external audits, learning the system |
| **Guided** | The AI can create and update data, with confirmation required for all changes and additional approval for high-impact operations. | Day-to-day project management, routine data entry |
| **Autonomous** | The AI can perform all operations including batch changes, with confirmation required for each action. Experienced users who accept direct responsibility for outcomes. | Bulk data entry, time-critical operations, well-understood projects |

---

## 4. Phase-by-Phase Collaboration Guide

### 4.1 Order Acquisition and Proposal

**Objectives:** Respond to customer requests for quotation, estimate project costs, define preliminary scope, and secure contract award.

**Human Responsibilities:**
- Define the project scope based on customer requirements and site specifications
- Establish the preliminary Work Breakdown Structure aligned with deliverables (individual machines, integration packages, commissioning phases)
- Set the contract value, payment milestones, and revenue allocation
- Approve the proposal and negotiate commercial terms
- Authorize project creation in Backcast upon contract award

**AI Contributions:**
- Retrieve historical data from comparable past projects to support estimation ("show me budget breakdowns for similar assembly line projects")
- Generate draft WBS structures based on project type and machine configuration
- Calculate preliminary Planned Value distributions using Linear, Gaussian, or Logarithmic progression curves
- Provide cost benchmarking by comparing proposed budgets against historical performance data

**Corporate Tool Coordination:**
- Reference the ERP quotation module for customer master data, contract terms, and preliminary cost estimates
- Reference preliminary machine layouts and BOM data from engineering tools for scope definition
- Attach the customer specification, proposal documents, and technical data sheets to the project record in the document management system

**Example Scenario:** A Project Manager receives a request to automate a new automotive final assembly line. They ask the AI assistant: "Show me the WBS and budget allocation for our last three similar assembly line projects, broken down by Mechanical Engineering, Electrical Engineering, and Software Engineering." The AI retrieves the historical data and presents a comparative table. The Project Manager uses this to develop the proposal budget, then asks the AI to create a draft project structure. The PM reviews, adjusts based on commercial judgment, and approves the structure.

---

### 4.2 Project Initiation and Planning

**Objectives:** Formally establish the project in Backcast, define the complete WBS hierarchy, allocate budgets to Control Accounts and Work Packages, set the Performance Measurement Baseline (PMB), and establish schedule baselines.

**Human Responsibilities:**
- Create the formal Project Charter in Backcast with complete metadata (project name, customer, contract value, start and end dates, Project Manager assignment)
- Define the WBS hierarchy: Project > WBS Elements (machines/major deliverables) > Control Accounts (WBS Element x Organizational Unit intersections) > Work Packages > Cost Elements
- Allocate revenue across WBS Elements
- Define budgets at the Cost Element level (the single source of truth for financial planning)
- Approve the Project Kickoff baseline
- Set schedule baselines with appropriate progression types (Linear, Gaussian, Logarithmic) for each cost element

**AI Contributions:**
- Create the complete WBS hierarchy through natural-language instructions ("create a new WBS element called Robot Cell A under project LINE-ALPHA with Control Accounts for Mechanical Engineering and Electrical Engineering")
- Batch-create Control Accounts and Work Packages based on template structures
- Calculate Planned Value curves for each schedule baseline based on the selected progression type
- Generate the initial forecast (Estimate at Completion) for each cost element
- Validate budget completeness by checking that all WBS Elements have allocated revenue and all Work Packages have cost elements
- Produce a visual diagram of the complete project structure for review

**Corporate Tool Coordination:**
- Reference the scheduling tool (Primavera P6, MS Project) for activity lists, durations, and dependencies to align the WBS
- Reference the ERP for cost center codes, vendor master data, and chart of accounts mappings
- Reference engineering BOM data for initial material cost estimation

**Example Scenario:** A Project Manager is setting up Project LINE-ALPHA, a EUR 500,000 end-of-line automation system. They instruct the AI: "Create the full project structure for LINE-ALPHA with five WBS Elements: Assembly Station 1, Assembly Station 2, Robot Cell A, Conveyor System, and System Integration. Each station needs Control Accounts for Mechanical Engineering and Electrical Engineering, with Work Packages containing cost elements for Labor, Material, and Equipment." The AI generates the complete hierarchy. The PM reviews each element, adjusts budgets based on detailed engineering estimates, and approves the Project Kickoff baseline. The system captures an immutable snapshot of the initial project state.

---

### 4.3 Engineering and Design

**Objectives:** Complete detailed engineering, release bill of materials, finalize cost element budgets, establish the BOM Release and Engineering Complete milestone baselines.

**Human Responsibilities:**
- Review and approve detailed engineering designs
- Finalize material take-offs and update Cost Element budgets accordingly
- Approve the BOM Release baseline
- Manage engineering change requests through the formal change order process
- Approve the Engineering Complete milestone baseline
- Begin procurement activities based on released BOM

**AI Contributions:**
- Update Cost Element budgets as engineering estimates mature ("increase the Material cost element for Robot Cell A from EUR 40,000 to EUR 48,000 based on updated BOM")
- Calculate the impact of engineering changes on the overall budget and EVM metrics
- Generate the BOM Release baseline snapshot, capturing the state of all budgets at this milestone
- Create forecasts comparing bottom-up estimates against performance-based projections
- Identify budget variances between initial estimates and engineering-detail estimates
- Produce Cost of Quality tracking for any rework identified during design reviews

**Corporate Tool Coordination:**
- Reference released engineering drawings and BOM data from CAD/CAE tools for material cost verification
- Store and link engineering drawings, calculation reports, and design review minutes to the relevant WBS Elements in the document management system
- Coordinate with the ERP procurement module for vendor sourcing based on released BOM data

**Example Scenario:** The Mechanical Engineering Department Head completes the final design for Robot Cell A. The updated BOM shows material costs 12% above the initial estimate. The Project Manager asks the AI: "Analyze the impact of increasing Robot Cell A material costs from EUR 40,000 to EUR 48,000 on the overall project CPI and EAC." The AI calculates the revised metrics and shows that the project CPI would drop from 1.02 to 0.97. The PM decides to create a change order to formally document the budget revision and submits it for department head approval.

---

### 4.4 Procurement and Supply Chain

**Objectives:** Source materials and subcomponents, manage supplier contracts, track procurement commitments against budgets, establish the Procurement Complete milestone baseline.

**Human Responsibilities:**
- Issue purchase orders and manage supplier negotiations
- Approve supplier quotations and commit procurement budgets
- Record procurement commitments as Cost Registrations against the relevant Cost Elements
- Approve the Procurement Complete baseline
- Manage supply chain risks and escalate delays

**AI Contributions:**
- Register committed costs against Cost Elements as purchase orders are placed ("register a EUR 35,000 material cost for the Robot Cell A Electrical Installation work package")
- Compare procurement commitments against budgeted amounts and flag variances
- Generate the Procurement Complete baseline snapshot
- Calculate the impact of procurement overruns or savings on the Estimate at Completion
- Track Cost of Quality for incoming inspection failures and supplier nonconformities

**Corporate Tool Coordination:**
- Reference purchase order data, goods receipts, and vendor invoice information from the ERP procurement module for cost registration
- Reference delivery schedules and quality certificates from supplier management portals
- Link incoming inspection results from the quality management system to Cost Events for COQ tracking

**Example Scenario:** The Procurement Department completes sourcing for all major components. The Project Manager asks the AI: "Compare our committed procurement costs against the budgeted amounts for each Work Package in LINE-ALPHA." The AI produces a table showing that three Cost Elements are within budget, one is 8% over (mechanical components for Assembly Station 2), and two have savings. The PM requests a detailed breakdown of the overrun and asks the AI to calculate the revised EAC incorporating the procurement data.

---

### 4.5 Manufacturing and Assembly

**Objectives:** Execute manufacturing and assembly work, track labor and material consumption, record progress, establish Manufacturing Start and Shipment milestone baselines.

**Human Responsibilities:**
- Record actual costs (labor hours, material consumption, subcontractor invoices) as Cost Registrations
- Update Percent Complete for each Work Package based on physical progress
- Manage manufacturing quality events (nonconformities, rework, weld repairs)
- Approve Manufacturing Start and Shipment milestone baselines
- Update forecasts based on actual manufacturing performance

**AI Contributions:**
- Batch-register costs from time sheets and material consumption reports ("register EUR 12,000 in labor costs across the three active Work Packages for this period")
- Calculate real-time EVM metrics (CPI, SPI, CV, SV) at every level of the WBS
- Identify Work Packages trending over budget or behind schedule
- Record quality events and attribute costs to Cost of Quality categories
- Generate updated forecasts using performance-based methods (applying current CPI to remaining work)
- Produce S-curve visualizations comparing Planned Value, Earned Value, and Actual Cost

**Corporate Tool Coordination:**
- Reference labor hours from time tracking, material consumption from warehouse management, and subcontractor invoices from accounts payable (typically via the ERP)
- Reference production progress data from manufacturing execution systems for Percent Complete updates
- Reference nonconformity reports from the quality management system for COQ tracking
- Reference equipment test data for commissioning readiness assessment

**Example Scenario:** The manufacturing phase is 60% complete. The AI proactively alerts the Project Manager: "Robot Cell A shows a Cost Performance Index of 0.89 and a Schedule Performance Index of 0.94. At current performance, the Estimate at Completion is EUR 155,000 against a Budget at Completion of EUR 150,000, resulting in an unfavorable Variance at Completion of EUR 5,000. The primary cost driver is electrical installation labor, which is 22% over the planned budget." The PM investigates, identifies that complex cable routing was underestimated, and creates a forecast documenting the expected overrun with mitigation actions.

---

### 4.6 Site Installation and Commissioning

**Objectives:** Deliver and install equipment on site, complete commissioning, achieve final acceptance, establish Site Arrival, Commissioning Start, and Commissioning Complete milestone baselines.

**Human Responsibilities:**
- Record site installation costs (travel, per diem, subcontracted installation labor)
- Track installation progress against the schedule baseline
- Manage site-level quality events and punch list items
- Approve Site Arrival, Commissioning Start, and Commissioning Complete baselines
- Conduct and document final acceptance tests
- Resolve any remaining change orders

**AI Contributions:**
- Register site costs and travel expenses against the appropriate Cost Elements
- Update Earned Value as installation milestones are achieved
- Calculate the financial impact of commissioning delays on the project completion date and budget
- Track quality costs from site-identified issues (alignment problems, integration failures)
- Compare actual site costs against the budget to identify scope creep or installation efficiency gains
- Generate the Commissioning Complete baseline with final performance metrics

**Corporate Tool Coordination:**
- Reference commissioning test results and equipment performance data for acceptance documentation
- Store and link site inspection reports, test certificates, and punch list documentation in the document management system
- Reference travel expense reports and site subcontractor invoices for cost registration
- Update activity completion dates and remaining duration estimates in the scheduling tool

**Example Scenario:** During commissioning of Assembly Station 1, a site inspection identifies that the conveyor alignment requires adjustment, generating a quality event. The Quality Manager asks the AI: "Create a quality event for the conveyor alignment issue at Assembly Station 1. Assign it to the Incoming Inspection category and register the estimated rework cost of EUR 3,200 against the Mechanical Installation cost element." The AI creates the quality event and cost registration. The PM reviews the updated COQ report, which now shows quality costs at 4.2% of total project cost, and decides whether this warrants a formal root cause analysis.

---

### 4.7 Project Monitoring and Control (Cross-Cutting)

**Objectives:** Continuously monitor project performance against baselines, analyze variances, manage forecasts, and take corrective action. This phase operates concurrently with all execution phases.

**Human Responsibilities:**
- Review EVM dashboards and variance reports at regular intervals
- Investigate significant variances and determine root causes
- Approve or reject forecast updates
- Authorize corrective actions and budget reallocations
- Chair the Change Control Board meetings
- Report project status to sponsors and steering committees
- Approve manual baselines when significant milestone events occur

**AI Contributions:**
- Calculate all EVM metrics in real time across every level of the WBS hierarchy
- Generate project health assessments with executive summaries, risk factors, and recommendations
- Monitor forecast stability by tracking standard deviation of EAC changes over time
- Detect variance threshold breaches and flag them for management attention (Minor: +/-5%, Moderate: +/-5-10%, Significant: +/-10-15%, Critical: >15%)
- Produce trend analyses showing how CPI and SPI have evolved since project start
- Generate visual S-curves comparing Planned Value, Earned Value, and Actual Cost
- Provide time-travel analysis: "Show me the project performance as of March 1 compared to today"
- Support cross-project benchmarking (anonymized) to contextualize performance

**Corporate Tool Coordination:**
- Reference updated activity progress from the scheduling tool for Earned Value calculation
- Reference actual cost data from the ERP for Cost Variance tracking
- Distribute variance alerts and approval notifications through corporate communication channels
- Use EVM data from Backcast alongside corporate reporting and BI tools for stakeholder reporting

**Example Scenario:** During a monthly project review, the PMO Director asks the AI: "Give me a full project health assessment for LINE-ALPHA as of today." The AI compiles a briefing document with the following sections: Executive Summary (project is 35% complete, CPI of 0.97, SPI of 0.94), Budget Analysis (EUR 53,000 in actual costs against EUR 54,640 in earned value, a Cost Variance of EUR -1,640), Schedule Analysis (project is tracking 6% behind the planned curve), Risk Factors (electrical installation labor continues to trend over budget), and Recommendations (consider reallocation from under-spending Work Packages, escalate forecast variance to department head). The PMO Director reviews the briefing, validates the findings against their own judgment, and directs the PM to prepare a corrective action plan.

---

### 4.8 Project Closeout and Lessons Learned

**Objectives:** Complete all remaining work, reconcile final costs, close change order branches, generate the Project Closeout baseline, document lessons learned.

**Human Responsibilities:**
- Verify that all work is complete and all deliverables have been accepted
- Reconcile final actual costs against the budget
- Approve the Project Closeout baseline
- Review the final Cost of Quality report
- Archive all change order branches
- Document lessons learned and process improvements
- Approve final project financial closure

**AI Contributions:**
- Generate the final Variance at Completion analysis across all WBS Elements and Cost Elements
- Compile the Cost of Quality summary showing total quality costs, root cause breakdown, and trend across the project lifecycle
- Produce the Project Closeout baseline capturing the final immutable state
- Archive all change order branches after verification that changes have been implemented
- Generate a comprehensive project summary report suitable for lessons-learned workshops
- Compare final performance against initial baselines to quantify estimation accuracy

**Corporate Tool Coordination:**
- Reconcile final cost data with the ERP for financial closure and revenue recognition
- Archive all project documents, test certificates, and acceptance records in the document management system
- Contribute project metrics to the organizational lessons-learned database and BI platform

**Example Scenario:** Project LINE-ALPHA reaches final acceptance. The Project Manager asks the AI: "Generate the final project closeout summary for LINE-ALPHA, including final EVM metrics, cost variance analysis by Work Package, Cost of Quality report, and a comparison of actual performance against the original kickoff baseline." The AI produces a comprehensive report. The PM reviews it, confirms the figures match the ERP financial records, and approves the Project Closeout baseline. The report is filed in the document management system and shared with the PMO for inclusion in the quarterly lessons-learned review.

---

## 5. Change Management and Governance

### 5.1 Change Control Board Process

Backcast digitizes the Change Control Board (CCB) function in accordance with PMI's Perform Integrated Change Control process. Every modification to a project's budget, WBS structure, or schedule flows through a formal, auditable workflow.

**Workflow States:**

```
Draft --> Submitted for Approval --> Under Review --> Approved --> Implemented
              |                      |                           |
              |                      +-> Rejected               |
              |                           |                     |
              +---------------------------+                     |
              |   (resubmit or revise)    |                     |
              +---------------------------+                     Changes Applied
```

| State | Description | Who Can Act |
|-------|-------------|-------------|
| **Draft** | Change order is being scoped in an isolated workspace. Only the creator can see it. | Project Manager |
| **Submitted for Approval** | Workspace is locked. No further edits. Routed to the appropriate approver based on impact level. | Project Manager |
| **Under Review** | Designated approver evaluates impact analysis and makes a decision. | Approver (varies by impact level) |
| **Approved** | Change is authorized. Workspace changes can be applied to the main project. | Approver |
| **Rejected** | Change is denied. Creator may revise and resubmit as a new Draft, or resubmit directly. | Approver |
| **Implemented** | Workspace changes have been applied to the main project. Baselines updated. | Project Manager |

### 5.2 Tiered Approval Authority

The approval routing is determined by the financial impact of the proposed change, calculated using a weighted score across four dimensions: budget impact (40%), schedule impact (30%), revenue impact (20%), and EVM degradation (10%). *These weights and thresholds are configurable per organization; the values shown represent system defaults.*

| Impact Level | Financial Threshold | Required Approver | SLA Deadline |
|---|---|---|---|
| **Low** | Under EUR 10,000 | Project Manager | 10 business days |
| **Medium** | EUR 10,000 -- EUR 50,000 | Department Head | 7 business days |
| **High** | EUR 50,000 -- EUR 100,000 | Director | 5 business days |
| **Critical** | Over EUR 100,000 | Executive Committee / Admin | 3 business days |

### 5.3 AI-Assisted Impact Analysis

When a change order is created, the AI performs automated impact analysis:

1. **Budget Impact:** Compares the proposed changes against the current budget, calculating the net change for each affected Cost Element, Work Package, and Control Account.
2. **Schedule Impact:** Assesses whether the changes affect critical-path activities and estimates the schedule variance impact.
3. **Revenue Impact:** Evaluates whether the changes affect the revenue allocation across WBS Elements.
4. **EVM Impact:** Calculates the projected effect on CPI, SPI, and EAC, quantifying performance degradation.

The AI presents the impact analysis in plain language with supporting metrics, enabling the Change Control Board to make informed decisions quickly.

### 5.4 Isolated Workspaces for Change Orders

Every change order operates within an isolated workspace — a parallel version of the project data where modifications can be evaluated without affecting the live project. This enables safe what-if analysis:

- **Change-Only View:** Shows only the entities affected by the change order, making it easy to see what would change.
- **Composite Preview:** Shows how the full project would look if the change order were approved and applied.
- **Workspace Locking:** Once a change order is submitted for approval, the workspace is locked to prevent further modifications during the review period.
- **Coordinated Application:** When approved, all changes are applied to the main project in a single coordinated update. If any inconsistency is detected, the application is held for manual resolution.

### 5.5 Baseline Management

Baselines are immutable snapshots of project data captured at significant milestones. Backcast supports standard milestone baselines aligned with the typical industrial automation project lifecycle. The following milestones are available by default:

| Milestone | Phase | Trigger |
|---|---|---|
| Project Kickoff | Initiation | Project creation |
| BOM Release | Engineering | Bill of materials released |
| Engineering Complete | Engineering | Design finalized |
| Procurement Complete | Procurement | All purchase orders placed |
| Manufacturing Start | Manufacturing | Production begins |
| Shipment | Manufacturing | Equipment shipped |
| Site Arrival | Installation | Equipment received on site |
| Commissioning Start | Commissioning | Commissioning activities begin |
| Commissioning Complete | Commissioning | All tests passed |
| Project Closeout | Closeout | Final acceptance |

Standard milestone baselines are captured automatically. Manual baselines may be created at any time, with approval requirements based on their financial impact.

---

## 6. Earned Value Management Integration

### 6.1 How AI Supports EVM Calculations and Forecasting

Backcast provides full ANSI/EIA-748-compliant Earned Value Management. The AI assistant supports EVM in three ways:

**Automated Calculation**

The AI calculates all standard EVM metrics at every level of the WBS hierarchy (Project, WBS Element, Control Account, Work Package, Cost Element):

| Metric | Formula | Interpretation |
|---|---|---|
| Planned Value (PV) | Sum of time-phased budgets through the control date | What should have been earned by now |
| Earned Value (EV) | Budget at Completion x Percent Complete | What has been earned for work performed |
| Actual Cost (AC) | Sum of all Cost Registrations through the control date | What has actually been spent |
| Cost Variance (CV) | EV - AC | Negative = over budget |
| Schedule Variance (SV) | EV - PV | Negative = behind schedule |
| Cost Performance Index (CPI) | EV / AC | Below 1.0 = over budget |
| Schedule Performance Index (SPI) | EV / PV | Below 1.0 = behind schedule |
| Estimate at Completion (EAC) | BAC / CPI (performance-based)¹ | Projected total cost |
| Estimate to Complete (ETC) | EAC - AC | Cost to complete remaining work |
| Variance at Completion (VAC) | BAC - EAC | Projected final variance |
| To Complete Performance Index (TCPI) | (BAC - EV) / (BAC - AC) | Required future performance |

¹ *The EAC formula shown (BAC / CPI) is the performance-based projection used by default. PMI recognizes additional EAC formulas depending on project conditions, including EAC = AC + ETC (bottom-up re-estimate) and EAC = AC + [(BAC − EV) / (CPI × SPI)] (composite performance). The appropriate formula is selected based on the forecasting methodology.*

**Forecasting Support**

The AI supports three forecast methodologies, and can apply them comparatively:

- **Bottom-Up:** Detailed re-estimation of remaining work from the work-face level up
- **Performance-Based:** Mathematical projection using current CPI and SPI trends
- **Management Judgment:** Expert opinion incorporating factors not captured in the data (known scope changes, market conditions, resource availability)

Up to three forecasts can be maintained per Cost Element, enabling the team to track forecast convergence and stability.

**Plain-Language Explanation**

The AI translates EVM metrics into business language that non-specialists can understand. For example, instead of merely reporting "CPI = 0.89," the AI explains: "For every euro spent on electrical installation, the project has earned only 89 cents of value. At this rate, the final cost is projected to exceed the budget by approximately EUR 5,000."

### 6.2 Human Interpretation and Decision-Making

While the AI performs calculations with mathematical precision, the human project team is responsible for interpretation and action:

| AI Provides | Human Decides |
|---|---|
| CPI trending below 1.0 for three consecutive periods | Whether this indicates a systemic problem or a timing anomaly |
| EAC exceeds BAC by 8% | Whether to authorize a budget increase, reallocate from other Work Packages, or accept the overrun |
| SPI indicates schedule delay | Whether to add resources, negotiate a deadline extension, or accept revised delivery dates |
| Variance exceeds threshold | Whether escalation is warranted or if corrective action at the Work Package level is sufficient |
| Three forecasts diverge significantly | Which forecast methodology is most reliable given current project conditions |

### 6.3 Reporting to Stakeholders

The AI generates reports tailored to each audience:

- **Executive Steering Committee:** One-page project health summary with CPI, SPI, EAC, key risks, and traffic-light status indicators
- **PMO:** Detailed variance analysis with trend charts, forecast comparison, and change order status
- **Department Heads:** Department-specific cost performance, quality costs, and resource utilization
- **Project Team:** Work Package level detail with progress percentages, remaining budget, and upcoming milestones

Report data is accessible through the platform and can be used alongside corporate reporting tools. Contact your Backcast representative for current export format availability.

---

## 7. Integration with the Corporate Tool Landscape

Backcast is designed to operate within a broader ecosystem of enterprise tools commonly found in industrial automation companies. While the specific integrations available depend on your deployment configuration, this section describes the intended data flows between Backcast and the corporate tool landscape.

> **Note:** The integration architecture described below represents the planned integration roadmap. Availability of specific connectors depends on your deployment version and configuration. Contact your Backcast account representative for current integration status and roadmap details.

### 7.1 Enterprise Resource Planning (ERP)

In most industrial automation companies, the ERP system (e.g., SAP, Oracle, Microsoft Dynamics) serves as the authoritative source for financial master data. Backcast complements the ERP by providing project-specific EVM and budget control that ERP systems typically lack.

| Integration Point | Direction | Description |
|---|---|---|
| Cost data synchronization | ERP → Backcast | Actual costs from accounts payable, time tracking, and material consumption feed into Cost Registrations |
| Project master data | ERP → Backcast | Customer data, contract values, cost center codes, and vendor master data during project setup |
| Budget reconciliation | Backcast → ERP | Final cost summaries and variance reports for financial period-close and revenue recognition |
| Commitment tracking | ERP → Backcast | Purchase order commitments tracked against Cost Element budgets |

**Typical workflow:** The project team enters cost registrations in Backcast based on ERP reports, or imports them through bulk data entry. At period-close, Backcast EVM summaries are reconciled against ERP financial records.

### 7.2 Engineering Design Tools

Engineering departments typically use CAD/CAE platforms (e.g., EPLAN, AutoCAD Electrical, SolidWorks) for detailed design and bill of materials management. Backcast tracks the cost implications of engineering outputs without replacing these tools.

| Integration Point | Direction | Description |
|---|---|---|
| BOM cost verification | Engineering → Backcast | Released bill of materials quantities and specifications inform material cost budget updates |
| Engineering change notices | Engineering → Backcast | Design changes that affect cost are captured as Change Orders in Backcast |
| Document cross-references | Backcast → Document Management | Cost Elements and WBS Elements reference engineering drawing numbers and document IDs |

**Typical workflow:** After a BOM release, the cost engineer reviews material quantities from the engineering tool and updates the corresponding Cost Element budgets in Backcast. The AI assistant can batch-update multiple cost elements based on the revised BOM data.

### 7.3 Project Scheduling Tools

Project schedules are typically maintained in specialized scheduling software (e.g., Primavera P6, Microsoft Project). Backcast focuses on cost and earned value management, while the scheduling tool manages activity sequencing, resource leveling, and critical path analysis.

| Integration Point | Direction | Description |
|---|---|---|
| Activity structure alignment | Schedule → Backcast | Activity IDs and work package boundaries are aligned so that Backcast WBS elements correspond to schedule activities |
| Progress updates | Schedule → Backcast | Physical percent complete data from the schedule feeds into Earned Value calculations |
| Milestone and baseline tracking | Backcast → Schedule | Backcast milestone baselines and EAC forecasts inform schedule risk assessments |

**Typical workflow:** The Project Manager maintains the detailed schedule in the scheduling tool and transfers progress percentages to Backcast for EVM calculation. The AI assistant can apply these percentages and immediately calculate the resulting EVM metrics.

### 7.4 Document Management Systems

Project documentation — drawings, specifications, test certificates, approval records — is stored in the organization's document management system (e.g., SharePoint, OpenText, or an engineering-specific platform).

| Integration Point | Direction | Description |
|---|---|---|
| Document linking | Backcast ↔ DMS | WBS Elements, Control Accounts, and Change Orders reference document IDs stored in the DMS |
| Attachments and evidence | DMS → Backcast | Supporting documents (drawings, calculation reports, approval records) can be attached to Backcast entities for audit trail completeness |

**Typical workflow:** When creating a Change Order in Backcast, the Project Manager references the relevant engineering change notice document stored in the DMS. The AI assistant can search and retrieve attached documents for contextual analysis.

### 7.5 Manufacturing and Site Systems

During manufacturing and commissioning, data from shop floor systems provides real-world inputs for progress tracking and quality cost management.

| Integration Point | Direction | Description |
|---|---|---|
| Production output data | MES → Backcast | Manufacturing output data informs physical percent complete estimates |
| Commissioning test results | SCADA → Backcast | Equipment test data supports commissioning milestone verification and acceptance documentation |
| Quality and nonconformity data | QMS → Backcast | Nonconformity reports and inspection results feed into Cost of Quality tracking |

**Typical workflow:** Quality events identified during incoming inspection or final testing are manually registered in Backcast by the quality team, or batch-entered from quality system reports. The AI assistant attributes quality costs to the appropriate Cost Elements and generates COQ summaries.

### 7.6 Data Exchange Approach

Backcast supports data exchange through structured interfaces accessible to IT teams for custom integrations with the corporate tool landscape:

| Approach | Use Case |
|---|---|
| Programmatic API access | Custom integrations with ERP, scheduling, and document management systems, typically developed by the customer's IT team |
| Bulk data entry | Efficient batch operations for cost registrations, progress entries, and budget updates — supported natively by the AI assistant |
| Report generation | EVM and project data accessible through the platform for use in corporate reporting tools and BI dashboards |

Contact your Backcast account representative for technical integration specifications and connector availability.

---

## 8. Best Practices for Human-AI Collaboration

Your AI assistant is most effective when you work with it the way you would work with a skilled team member. These practices help you get the most from the collaboration:

### 8.1 Start with Clear Context

Always scope your AI conversation to the relevant project, WBS Element, or Work Package. The AI operates within the boundaries you set. An ambiguous request like "show me the budget" is less effective than "show me the budget for Robot Cell A in LINE-ALPHA as of today."

### 8.2 Use the Right Assistant for the Task

Select the Friendly Project Analyzer for analysis and reporting, the Senior Project Manager for operational data management, and the System Manager for administrative tasks. Using the read-only persona for analysis eliminates the risk of accidental modifications.

### 8.3 Review Before You Approve

Every AI-proposed action is presented for your review before execution. Read the preview carefully. The AI shows exactly what will change, including previous and new values. This is your opportunity to catch errors or reconsider.

### 8.4 Leverage Batch Operations for Efficiency

When entering multiple cost registrations, creating several WBS Elements, or updating multiple forecasts, use batch instructions. The AI can process multiple operations in a single request, reducing data entry time and minimizing the risk of partial updates.

### 8.5 Use Time-Travel for Root Cause Analysis

When performance deviates from plan, use the temporal analysis capability to identify when the deviation began. "Show me the CPI trend for this project by month since kickoff" is more diagnostic than a single-point metric.

### 8.6 Document the "Why," Not Just the "What"

When creating change orders or updating forecasts, include the reasoning in the description. The AI can draft justification text, but the commercial and technical rationale must come from human judgment. Future reviewers and auditors will need to understand why decisions were made.

### 8.7 Maintain Forecast Discipline

Limit forecasts to the three most recent per Cost Element. Discard superseded forecasts rather than accumulating them. Use the forecast stability metric (standard deviation of EAC changes) to assess whether estimates are converging or diverging.

### 8.8 Use Isolated Workspaces for What-If Scenarios

Before proposing a change order, use the isolated workspace feature to model the change in a sandbox environment. The AI can switch between change-only and composite preview views so you can evaluate the impact without committing to the live project.

### 8.9 Validate AI Outputs Against Your Expertise

The AI assistant knows your data, your procedures, and your policies — but it cannot know factors outside the system: a key supplier's financial instability, a client relationship consideration, or a strategic decision to accept a short-term loss. Always validate AI recommendations against your professional judgment and organizational context. Think of it as reviewing the work of a capable analyst who lacks your institutional knowledge.

### 8.10 Close the Loop on Variance Alerts

When the AI flags a variance threshold breach, respond formally. Either update the forecast to reflect the new reality, create a change order to adjust the budget, or document why the variance is expected to self-correct. Leaving variance alerts unaddressed undermines the value of the monitoring system.

---

## Appendix A: Glossary of PMI Terms

| Term | Definition |
|---|---|
| **Actual Cost (AC)** | The realized cost incurred for work performed during a specific time period. Also known as ACWP. |
| **Budget at Completion (BAC)** | The total authorized budget for the project, representing the sum of all budgets established for the work to be performed. |
| **Change Control Board (CCB)** | A formally constituted group of stakeholders responsible for reviewing, evaluating, and approving or rejecting change requests. |
| **Control Account** | A management control point where scope, budget, and schedule are integrated and compared to actual results for performance measurement. Defined as the intersection of a WBS Element and an Organizational Unit per ANSI/EIA-748. |
| **Cost Performance Index (CPI)** | A measure of cost efficiency on a project. Calculated as Earned Value divided by Actual Cost (CPI = EV / AC). A CPI below 1.0 indicates cost overrun. |
| **Cost Variance (CV)** | The difference between Earned Value and Actual Cost (CV = EV - AC). A negative CV indicates the project is over budget. |
| **Earned Value (EV)** | The measure of work performed expressed in terms of the budget authorized for that work. Also known as BCWP. |
| **Earned Value Management (EVM)** | A project management methodology that integrates scope, schedule, and cost to measure project performance and progress. Compliant with ANSI/EIA-748. |
| **Estimate at Completion (EAC)** | The expected total cost of completing all work expressed as the sum of Actual Cost to date and the estimated cost to complete remaining work. |
| **Estimate to Complete (ETC)** | The expected cost to finish all remaining project work. Calculated as EAC minus AC. |
| **Gaussian Progression** | A Backcast-specific scheduling model for Planned Value distribution where work accelerates through the middle of the schedule period and decelerates near the end, following a bell-curve shape. Produces a symmetric S-curve. |
| **Linear Progression** | A Backcast-specific scheduling model that distributes Planned Value evenly across the schedule period, where work progresses at a constant rate. |
| **Logarithmic Progression** | A Backcast-specific scheduling model where Planned Value accumulates slowly at the start and accelerates toward the end of the schedule period. Produces an asymmetric front-loaded curve. |
| **Milestone Baseline** | An immutable snapshot of project data captured at a significant project event, used for variance tracking and performance comparison. |
| **Percent Complete** | The physical progress of work expressed as a percentage of the total scope. The primary input for Earned Value calculation. |
| **Performance Measurement Baseline (PMB)** | An approved, time-phased budget plan against which project performance is measured. Includes all authorized work and approved changes. |
| **Planned Value (PV)** | The authorized budget assigned to scheduled work. Also known as BCWS. |
| **Perform Integrated Change Control** | The PMI process for reviewing all change requests, approving changes, and managing changes to deliverables, organizational process assets, project documents, and the project management plan. |
| **Project Charter** | A document issued by the project initiator or sponsor that formally authorizes the existence of a project and provides the Project Manager with authority to apply organizational resources. |
| **Schedule Performance Index (SPI)** | A measure of schedule efficiency expressed as Earned Value divided by Planned Value (SPI = EV / PV). An SPI below 1.0 indicates the project is behind schedule. |
| **Schedule Variance (SV)** | The difference between Earned Value and Planned Value (SV = EV - PV). A negative SV indicates the project is behind schedule. |
| **S-Curve** | A graphic display of cumulative costs, labor hours, or other quantities plotted against time, showing the characteristic S-shape of project progress. |
| **To Complete Performance Index (TCPI)** | The cost performance that must be achieved on the remaining work to meet a specified financial goal (typically BAC or EAC). |
| **Variance at Completion (VAC)** | The projected difference between the Budget at Completion and the Estimate at Completion (VAC = BAC - EAC). A negative VAC indicates an expected cost overrun. |
| **Work Breakdown Structure (WBS)** | A hierarchical decomposition of the total scope of work to be carried out by the project team to accomplish project objectives and create the required deliverables. |
| **Work Package** | The lowest level of the WBS for which cost and duration can be estimated and managed. In Backcast, the primary budget holder for EVM calculations. |

---

## Appendix B: RACI Matrix Template

The following RACI matrix defines responsibility assignments across the project lifecycle phases. **R** = Responsible, **A** = Accountable, **C** = Consulted, **I** = Informed.

| Activity | Project Manager | Department Head | Project Controller | System Administrator | Executive Viewer | AI Assistant |
|---|---|---|---|---|---|---|
| **Project Creation and Setup** | A/R | C | I | C | I | C (drafts structure) |
| **WBS Definition** | A/R | C | R (validate) | I | I | R (creates elements) |
| **Budget Allocation** | A | R (per department) | R (verifies) | I | I | R (registers values) |
| **Schedule Baseline** | A/R | C | R (analyzes) | I | I | R (calculates curves) |
| **Cost Registration** | A | R (per department) | R (verifies) | I | I | R (records costs) |
| **Progress Reporting** | A/R | C | R (compiles) | I | I | R (calculates EV) |
| **Forecast Creation** | A/R | C | R (challenges) | I | I | R (generates options) |
| **Change Order Draft** | A | C | C | I | I | R (drafts and analyzes) |
| **Change Order Approval** | R (Low) | A (Medium) | C | A (Critical) | I | I (tracks SLA) |
| **Baseline Approval** | A (standard) | C | R (verifies) | A (manual >= 10K) | I | I (captures snapshot) |
| **Variance Analysis** | A | C | R | I | I | R (calculates metrics) |
| **Project Closeout** | A/R | C | R (reconciles) | I | I | R (generates reports) |

**Key Principles:**

- The AI is always **Responsible** (R) for data processing, calculation, and draft generation. It is never **Accountable** (A) for decisions.
- Accountability always rests with a named human role, even when the AI performs the execution work.
- The Project Controller provides independent verification of all financial data, serving as a check on both human and AI inputs.
- The Executive Viewer is **Informed** (I) throughout the project lifecycle, with escalation to **Consulted** (C) or **Accountable** (A) for critical change orders and project-level decisions.

---

*This guide is intended for distribution to client organizations evaluating or deploying Backcast. For technical implementation details, system architecture documentation, and administrator guides, contact your Backcast account representative.*

**Standards References:**

- PMI, *A Guide to the Project Management Body of Knowledge (PMBOK Guide)*, 7th Edition
- PMI, *Practice Standard for Earned Value Management*
- ANSI/EIA-748, *Standard for Earned Value Management Systems*
- ISO 21500, *Guidance on Project Management*