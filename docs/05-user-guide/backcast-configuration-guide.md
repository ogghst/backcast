# Configuring Backcast for Your Organization

## Adaptation Guide: Roles, Workflows, AI Assistance, and Team Structure

---

## 1. Introduction

This guide is a companion to the *Human-AI Collaboration Guide* and addresses the decisions that administrators and PMO directors face when deploying Backcast across an organization. While the Collaboration Guide describes how people and AI assistants work together day to day, this guide explains how to configure Backcast so that it reflects your organizational structure, authority model, and change management culture.

**Configuration philosophy.** Backcast adapts to your organization, not the other way around. The system provides a granular permission model spanning project delivery, change management, EVM reporting, AI interaction, and system administration. A fully configurable change order workflow, adjustable impact scoring, and customizable AI personas give administrators precise control over governance, delegation, and automation. Every configuration choice described in this guide can be adjusted at the global level and, where it matters most, overridden at the individual project level.

**Who should read this guide.** System administrators responsible for the initial Backcast deployment, PMO directors defining governance policies, IT leads managing user accounts and security, and project managers who will serve as project-level administrators.

---

## 2. Organizational Role Configuration

### 2.1 Understanding the Permission Model

Backcast controls access through a role-based access control (RBAC) system built on granular permissions organized by functional category. Each permission follows a consistent pattern: an entity name paired with an action. For example, the project-read permission grants viewing access to projects, while project-create authorizes the creation of new projects.

**Permission categories.** The permissions span the full range of Backcast capabilities:

- **Project delivery:** Project, WBS Element, Control Account, Work Package, Cost Element, Cost Event, Cost Registration, Progress Entry, Schedule Baseline, Forecast
- **Earned Value Management:** EVM metrics, analysis, and reporting
- **Change management:** Change Order (including specialized actions for submit, approve, implement, recover, and escalate)
- **Administrative:** User Management, Organizational Unit, Cost Element Type, Cost Event Type, AI Configuration, MCP Server, Dashboard Templates, Project Budget Settings, Change Order Workflow Configuration, Temporal and System operations
- **Documents:** Project Documents (read, write, delete)

**How roles bundle permissions.** Roles are named collections of permissions. Backcast ships with six predefined roles, each designed for a specific type of user or AI agent:

| Role | Scope | Intended User |
|------|:---:|---|
| **Admin** | Full system | System administrator with unrestricted access |
| **Manager** | Project delivery | Project manager with full project delivery permissions |
| **Viewer** | Read-only | Read-only stakeholder with change order approval capability |
| **AI Viewer** | Read-only | AI assistant operating in read-only mode |
| **AI Manager** | Project delivery | AI assistant with full project delivery permissions |
| **AI Agent (Admin)** | System management | AI assistant with system management capabilities |

Administrators can create custom roles by selecting any combination of available permissions. The predefined roles serve as starting templates: copy a role, adjust its permission set, and assign it to users as needed. System roles cannot be deleted, but their permission sets can be modified.

**Scoped role assignments.** A single user can hold different roles at different scopes:

- **Global scope** applies across all projects and system functions.
- **Project scope** applies to a specific project only, overriding the global role for that project's context.
- **Change Order scope** applies to a specific change order, enabling temporary authority grants for approval or review.

This scoping model supports matrix organizations where a person might be a viewer on one project and a manager on another, or where a department head receives temporary approval authority for a specific change order.

---

### 2.2 Adapting to Different Delegation Styles

#### Example 1: Centralized Control — Small Team (5-8 People)

A small automation integrator has a single project manager who directly manages all project delivery. The team includes two cost engineers, a scheduler, and three discipline leads. Decision-making is fast because the PM handles most approvals personally.

**Role setup:**

- **1 Admin:** The IT lead or company owner. Manages user accounts, system configuration, and AI settings. Holds all permissions.
- **1 Manager:** The project manager. Has full project delivery permissions including change order creation, submission, and implementation. Notably, the Manager role lacks AI configuration access, so the PM cannot accidentally modify AI behavior.
- **5 Viewers:** Cost engineers, the scheduler, and discipline leads. Each has read-only access to all project data plus the ability to approve change orders. This allows discipline leads to sign off on changes affecting their scope while preventing unintended data modifications.

**Delegation pattern.** The PM creates change orders, the relevant discipline lead reviews and approves (using the Viewer's approval permission), and the PM implements. For simple changes below the LOW threshold, the PM self-approves and proceeds.

**AI persona assignment.** The Friendly Project Analyzer (read-only AI persona) is available to all team members for ad-hoc queries about EVM metrics, budget status, and project performance. The PM additionally has access to the Senior Project Manager persona for creating and updating work packages, cost elements, and progress entries through conversational interaction.

---

#### Example 2: Balanced Delegation — Medium Team (15-25 People)

A mid-size system integrator runs multiple concurrent projects. Each project has its own PM, and department heads (Engineering, Procurement, Construction) provide oversight across projects. The organization uses a matrix structure where discipline engineers report to both their project PM and their department head.

**Role setup:**

- **1-2 Admins:** IT administration and the PMO director. Manage system-wide configuration, user accounts, and the change order workflow template.
- **3-5 Managers:** One per active project. Each PM is assigned the Manager role at the **project scope** for their specific project. A PM working on Project A has no write access to Project B unless explicitly assigned. Additionally, each PM has the Viewer role at global scope so they can read (but not modify) other projects for cross-project awareness.
- **3 Department Heads:** Viewer role at global scope, plus the Viewer role at the change order scope for changes exceeding the MEDIUM impact threshold. This ensures department heads see all projects but only intervene on significant changes.
- **10-15 Viewers:** Engineers, schedulers, cost controllers, and document controllers. Read access across all projects within their assignment scope.

**Delegation pattern.** Project managers handle day-to-day change orders up to the MEDIUM threshold. Changes classified as HIGH or CRITICAL route to department heads or directors for approval. The per-project workflow override allows each PM to adjust impact thresholds and SLA deadlines to match their contract requirements.

**AI persona assignment.** The Friendly Project Analyzer is available organization-wide. Each PM is assigned the Senior Project Manager persona at their project scope. Department heads receive the Friendly Project Analyzer only, since their role is oversight rather than data entry. This ensures that AI-assisted write operations are always scoped to the PM's area of authority.

---

#### Example 3: Fully Distributed Authority — Large Organization (50+ People)

A large OEM with regional offices runs ten or more concurrent projects. The PMO defines standards, but each region operates with significant autonomy. Multiple project managers, regional directors, and a corporate executive layer all participate in governance.

**Role setup:**

- **2-3 Admins:** Corporate IT and the PMO director. Control system configuration, AI providers, and the global change order workflow template. Regional IT contacts may receive a scoped Admin role for their region's projects.
- **8-12 Managers:** Multiple PMs, each assigned the Manager role at their specific project scope. Senior PMs overseeing a portfolio receive the Manager role at global scope with the understanding that they operate across projects.
- **5-8 Viewers with scoped approval authority:** Regional directors and department heads receive the Viewer role globally, with change order approval authority scoped to specific projects or specific impact levels. The approval authority configuration maps HIGH-impact changes to the director role and CRITICAL-impact changes to the admin role.
- **30+ Viewers:** Engineers, specialists, and support staff across regions and projects.
- **Custom roles as needed:** The organization may create a "Project Controller" role (Manager permissions minus change order approval) for cost controllers who manage budgets but should not approve their own changes, enforcing segregation of duties.

**Delegation pattern.** The three-tier approval model operates at scale. PMs approve LOW and MEDIUM changes within their project. Regional directors approve HIGH changes. Corporate executives (holding the Admin role) approve CRITICAL changes. The SLA escalation mechanism automatically routes overdue approvals upward. The per-project override capability allows each regional office to calibrate thresholds to local contract requirements while maintaining corporate governance standards.

**AI persona assignment.** All users have access to the Friendly Project Analyzer. PMs and senior PMs receive the Senior Project Manager persona. The IT team configures the System Manager persona for administrative use. Regional offices may receive project-specific AI assistants with localized behavioral guidelines reflecting local terminology, reporting standards, and contractual requirements.

---

### 2.3 Organizational Unit Design

Organizational units in Backcast represent the departments, disciplines, or teams that form the organizational axis of the ANSI-748 Work Breakdown Structure matrix. Each unit can own Cost Element Types and Control Accounts, creating the intersection between "what is being built" (WBS) and "who is building it" (organizational unit).

Organizational units support hierarchical nesting with no enforced depth limit. A flat structure might have a single level of departments, while a deep hierarchy might represent divisions, departments, teams, and sub-teams.

**Organizational units are versioned entities** — they support the same temporal versioning and change order branching as project delivery entities. This means reorganizing departments can be managed through the change order process, preserving a complete audit trail.

#### Example 1: Single-Discipline Automation House

A company specializing in packaging line automation has three departments:

```
AUTOMATION (root)
  ├── MECH — Mechanical Engineering
  ├── ELEC — Electrical Engineering
  └── SW    — Software & Controls
```

Each department owns its own Cost Element Types (for example, MECH owns "Structural Steel" and "Piping," ELEC owns "Cabling" and "Panel Fabrication"). Control Accounts are created at the intersection of WBS elements and these three departments. The flat hierarchy reflects the company's collaborative culture where department leads communicate directly.

#### Example 2: Multi-Discipline System Integrator

A company that designs and builds complete production lines across industries organizes by discipline and sub-discipline:

```
ENGINEERING (root)
  ├── PROC — Process Engineering
  │     ├── PIP — Piping Design
  │     └── VES — Vessel Design
  ├── AUT  — Automation
  │     ├── PLC — PLC Programming
  │     ├── DCS — DCS Configuration
  │     └── INS — Instrumentation
  ├── CIV  — Civil & Structural
  └── COM  — Commissioning
```

The two-level hierarchy allows the Engineering Director to see aggregated performance across all disciplines while enabling discipline-specific cost tracking. Control Accounts at the sub-discipline level provide the granularity needed for earned value analysis per specialty.

#### Example 3: Large OEM with Regional Offices

A multinational OEM structures organizational units by region, then by function:

```
CORPORATE (root)
  ├── EU — Europe Region
  │     ├── EU-ENG — European Engineering
  │     ├── EU-PM  — European Project Management
  │     └── EU-SRV — European Service
  ├── NA — North America Region
  │     ├── NA-ENG — North American Engineering
  │     ├── NA-PM  — North American Project Management
  │     └── NA-SRV — North American Service
  └── APAC — Asia-Pacific Region
        ├── APAC-ENG — APAC Engineering
        └── APAC-PM  — APAC Project Management
```

Each regional unit manages its own projects, cost element types, and control accounts. The three-level hierarchy enables corporate-level EVM consolidation while maintaining regional autonomy. The PMO at corporate can view aggregated performance across all regions using the Viewer role at global scope, while regional PMs operate within their regional unit's scope.

---

## 3. Change Management Configuration

### 3.1 Workflow Adaptability

Backcast's change order workflow is built on a configurable state machine. The system defines six workflow states and governs the transitions between them through a set of rules that administrators can customize.

**Fixed elements.** The six workflow states — Draft, Submitted for Approval, Under Review, Approved, Implemented, and Rejected — are fixed. Every change order follows this lifecycle. Segregation of duties is enforced: the person who creates a change order cannot approve it. These constraints ensure compliance with common project management standards.

**Configurable elements.** Administrators control which transitions are allowed between states, which statuses allow editing, and whether transitions lock or unlock the change order. The approval routing, impact scoring, SLA deadlines, and escalation behavior are all adjustable.

**Approval tiers.** Backcast classifies every change order into one of four impact levels — LOW, MEDIUM, HIGH, or CRITICAL — using two independent methods: a financial threshold (in EUR) and a weighted impact score. The higher classification of the two determines the required approval authority. The default tier structure is:

| Level | Financial Threshold | Score Range | Required Approver | SLA |
|-------|:---:|:---:|---|:---:|
| LOW | Under 10,000 EUR | 0 - 10 | Project Manager | 10 business days |
| MEDIUM | 10,000 - 50,000 EUR | 10.01 - 30 | Department Head | 7 business days |
| HIGH | 50,000 - 100,000 EUR | 30.01 - 50 | Director | 5 business days |
| CRITICAL | 100,000 EUR and above | 50.01+ | Executive / Admin | 3 business days |

Every element in this table — the threshold amounts, score boundaries, approver titles, and SLA deadlines — is configurable globally and can be overridden per project.

---

### 3.2 Adapting to Different Change Management Styles

#### Example 1: Lean Change Control — Small Integrator

A small automation integrator with 6 people needs fast decision cycles. Changes are typically minor scope adjustments or cost transfers. Formal CCB meetings would slow the team down without adding value.

**Impact tier configuration:**

| Level | Financial Threshold | Score Boundary | Approver | SLA |
|-------|:---:|:---:|---|:---:|
| LOW | Under 25,000 EUR | 0 - 20 | Project Manager | 15 business days |
| MEDIUM | 25,000 - 75,000 EUR | 20.01 - 40 | Project Manager | 10 business days |
| HIGH | 75,000 - 150,000 EUR | 40.01 - 60 | Director | 7 business days |
| CRITICAL | 150,000 EUR and above | 60.01+ | Director | 5 business days |

**Rationale.** The LOW and MEDIUM thresholds are raised significantly from defaults because the PM handles most changes directly. The HIGH and CRITICAL thresholds are also elevated to match the company's typical project size. SLA deadlines are generous for lower tiers (the team is small and communicates constantly) but tighten for significant changes. Only two approver roles are used because the organization has a flat hierarchy.

**Impact weights:** Budget 0.5, Schedule 0.3, Revenue 0.1, EVM 0.1. Budget is weighted most heavily because cost control is the primary concern for small projects with thin margins.

**Workflow simplification.** The Under Review state can be bypassed by configuring a direct transition from Submitted for Approval to Approved. This eliminates the intermediate review step for teams where the approver is also the reviewer.

---

#### Example 2: Formal Change Control Board — Mid-Size Company

A mid-size system integrator with 20 employees holds monthly Change Control Board (CCB) meetings attended by department heads. Changes above a modest threshold require documented impact analysis and CCB approval before implementation.

**Impact tier configuration:**

| Level | Financial Threshold | Score Boundary | Approver | SLA |
|-------|:---:|:---:|---|:---:|
| LOW | Under 5,000 EUR | 0 - 10 | Project Manager | 15 business days |
| MEDIUM | 5,000 - 25,000 EUR | 10.01 - 30 | Department Head | 10 business days |
| HIGH | 25,000 - 75,000 EUR | 30.01 - 50 | Director | 7 business days |
| CRITICAL | 75,000 EUR and above | 50.01+ | Director | 3 business days |

**Rationale.** Thresholds are tightened from defaults to ensure that even moderately sized changes receive proper scrutiny. The SLA for CRITICAL changes is aggressive at 3 business days, aligning with CCB meeting cycles. The Under Review state is actively used as the CCB review stage.

**Impact weights:** Budget 0.35, Schedule 0.35, Revenue 0.15, EVM 0.15. Budget and schedule receive equal weight because the company's fixed-price contracts make both cost overruns and schedule delays equally damaging.

**Workflow configuration.** The full state machine is enabled: Draft, Submitted for Approval, Under Review, Approved, Implemented, Rejected. Custom fields are configured to capture the CCB meeting date, CCB decision reference number, and implementation deadline. The escalation trigger is set at 60% of SLA time, so approvers receive warnings before the CCB meeting if a change order is approaching its deadline.

---

#### Example 3: Enterprise Change Governance — Large OEM with ANSI/EIA-748 Compliance

A large OEM delivering defense or regulated-industry projects must comply with ANSI/EIA-748 Earned Value Management standards. Change governance is contractual, segregation of duties is mandatory, and every decision requires an audit-grade trail.

**Impact tier configuration:**

| Level | Financial Threshold | Score Boundary | Approver | SLA |
|-------|:---:|:---:|---|:---:|
| LOW | Under 2,500 EUR | 0 - 5 | Control Account Manager | 10 business days |
| MEDIUM | 2,500 - 10,000 EUR | 5.01 - 20 | Program Manager | 7 business days |
| HIGH | 10,000 - 50,000 EUR | 20.01 - 40 | Program Director | 5 business days |
| CRITICAL | 50,000 EUR and above | 40.01+ | Executive Sponsor | 2 business days |

**Rationale.** Thresholds are significantly tightened from defaults, reflecting the contractual requirement to track and approve even small changes. Four distinct approver levels enforce the segregation of duties required by EVM standards. The SLA for CRITICAL changes is aggressive because contractual notification deadlines may be as short as 48 hours.

**Impact weights:** Budget 0.30, Schedule 0.25, Revenue 0.20, EVM 0.25. EVM receives a high weight because contract compliance depends on maintaining CPI and SPI within contractual thresholds. Revenue is weighted at 0.20 because changes that reduce margin have direct contractual implications.

**Workflow configuration.** The complete state machine is active with strict lock/unlock rules: change orders are locked upon submission and remain locked until implementation or rejection. The Rejected-to-Draft transition is allowed for rework, but Rejected-to-Submitted is disabled to force a full revision cycle. Custom fields capture the contractual change request reference, the customer notification date, the reason code (scope change, funding adjustment, schedule acceleration), and the variance analysis reference number.

**Holiday calendar.** The holiday country code is set to match the project's jurisdiction, ensuring SLA calculations count only business days. For projects spanning multiple countries, the PMO selects the most restrictive calendar.

**Per-project overrides.** Different contracts may specify different thresholds. A defense contract might require CRITICAL approval at 25,000 EUR, while a commercial contract uses the enterprise default of 50,000 EUR. Each project's workflow configuration is overridden to match its contractual requirements, while the global template provides the corporate standard.

---

### 3.3 Impact Scoring and Thresholds

The impact scoring system evaluates every change order across four dimensions: Budget impact, Schedule impact, Revenue impact, and EVM impact. Each dimension receives a configurable weight, and the weighted combination produces an impact score that maps to one of the four impact levels.

**Tuning impact weights.** Adjust the four weights based on your organization's priorities:

- **Budget-focused organizations** (cost-reimbursable contracts, tight margins): Increase the budget weight to 0.50 and reduce EVM to 0.05.
- **Schedule-critical organizations** (penalty clauses, fixed delivery dates): Increase the schedule weight to 0.45 and reduce revenue to 0.10.
- **EVM-compliant organizations** (ANSI/EIA-748 contracts): Set EVM to 0.25 or higher, reflecting the contractual significance of CPI and SPI thresholds.
- **Balanced organizations**: The defaults (Budget 0.40, Schedule 0.30, Revenue 0.20, EVM 0.10) provide reasonable sensitivity across all dimensions.

**Threshold calibration.** When setting financial thresholds, consider your typical project size. A 10,000 EUR threshold for LOW impact is appropriate for projects in the 500,000 - 2,000,000 EUR range. For larger projects (5,000,000+ EUR), multiply all thresholds by a factor of 5-10. For smaller projects, reduce thresholds proportionally.

**Per-project overrides.** As described in the Human-AI Collaboration Guide, the AI assistant uses the project's active configuration to determine impact scoring and approval routing at the time of submission. This configuration snapshot is captured immutably on the change order record, ensuring that later changes to the workflow template do not retroactively affect submitted change orders. Use per-project overrides when a specific contract mandates different thresholds than your corporate standard.

---

## 4. AI Assistant Configuration

### 4.1 Persona Selection and Customization

Backcast ships with three AI personas, each designed for a distinct purpose and matched to a specific access level:

**Friendly Project Analyzer** (access level: read-only). This persona explains project status, EVM metrics, budget performance, and schedule data in clear language. It cannot create, modify, or delete any data. Use this persona for stakeholders who need insights without write access, for team members new to EVM who benefit from explanatory interaction, and for executive reporting where the AI summarizes project health without risk of data modification.

**Senior Project Manager** (access level: full project delivery). This persona can create and update projects, WBS elements, control accounts, work packages, cost elements, change orders, forecasts, and progress entries. It cannot manage users, system configuration, or organizational structure. Use this persona for project managers who want to delegate data entry and routine calculations to the AI while retaining decision-making authority.

**System Manager** (access level: full system). This persona can manage user accounts, organizational units, cost element types, and system configuration. It operates with caution and verification-first behavior. Use this persona for IT administrators and PMO staff who manage the Backcast system itself.

**Persona access alignment.** The AI persona's access level should never exceed the human user's role. A Viewer should interact with the Friendly Project Analyzer, not the Senior Project Manager. This is enforced by Backcast's triple-layer access control: the persona's RBAC role, the execution mode selected at chat time, and the individual tool's permission requirements all filter independently. A read-only persona simply cannot invoke write tools regardless of execution mode.

**Customizing behavior.** Administrators can adjust several aspects of each persona:

- **Communication style and guidelines:** Defines the persona's personality, behavioral rules, and interaction patterns. Adjust this to match your organization's terminology, reporting standards, and communication culture.
- **Response precision:** Controls how deterministic or conversational the AI's responses are. Precision-oriented settings produce consistent, analytical answers suitable for financial work. Conversational settings allow more exploratory dialogue.
- **Response depth:** Controls how detailed the AI's responses are. Longer responses suit comprehensive reports and analyses; shorter responses keep interactions concise and action-oriented.
- **AI model selection:** Different personas can use different AI models to balance capability and cost. For example, the System Manager might use a cost-effective model for routine tasks, while the Senior Project Manager uses a more capable model for complex analysis.

---

### 4.2 Adapting AI Assistance to Team Maturity

#### Example 1: AI-Supported Onboarding — New Team Unfamiliar with EVM

A manufacturing company has adopted earned value management for the first time. The project team includes experienced engineers who understand the technical work but are unfamiliar with CPI, SPI, EAC, and variance analysis. The AI assistant serves as a tutor and guide during the transition.

**Phase 1 — Learning (Months 1-2):**
All team members receive the Friendly Project Analyzer persona in Safe execution mode. The AI can only read data and respond to questions. Team members learn to ask questions like "What does a CPI of 0.85 mean for this control account?" and "Why is the schedule variance negative on the electrical installation work package?" The AI explains metrics in plain language, building EVM literacy across the team.

**Phase 2 — Guided Practice (Months 3-4):**
Project managers are upgraded to the Senior Project Manager persona in Standard execution mode. The AI can now create and update data, but every write operation requires explicit user approval before execution. This safety net ensures that new PMs learn the correct data entry patterns without risk of accidental modifications.

**Phase 3 — Full Operation (Month 5+):**
Experienced PMs switch to Expert execution mode. The AI executes immediately without confirmation, reflecting the PM's growing confidence and competence. New team members continue at the Standard tier until they demonstrate proficiency.

**Persona customization.** The AI's behavioral guidelines are enhanced with instructions like "Explain EVM concepts when the user asks about metrics. Use analogies relevant to manufacturing operations. Always define acronyms on first use." This ensures the AI adapts its communication style to the team's learning curve.

---

#### Example 2: Experienced Team Augmentation — Seasoned PM Team

A project management team with decades of combined EVM experience uses AI to accelerate routine work, not to learn fundamentals. The team knows what CPI means and does not need explanations. They want the AI to handle data lookups, calculate forecasts, and populate routine entries so they can focus on judgment and stakeholder management.

**Configuration:**
- All PMs receive the Senior Project Manager persona in Expert execution mode from day one. No approval workflow, no training wheels. The AI executes immediately, reflecting the trust placed in experienced professionals.
- The AI's behavioral guidelines are customized to remove explanatory language: "Provide concise, data-dense responses. Do not define EVM acronyms. Present variances as numbers with trend direction. Prioritize action items over descriptions."
- Response precision is set to maximum for consistent, analytical output. The AI acts as a fast calculator and data retrieval engine rather than a tutor.
- Response depth is set to maximum to accommodate detailed cost breakdowns and comprehensive project analyses in a single response.
- Cost registration and forecast capabilities are enabled so PMs can delegate routine financial entries through conversational interaction.

**Result.** PMs describe what they want ("Update the forecast for the mechanical installation work package to reflect the 3-week delay") and the AI handles the data operations. The PM reviews the result and moves on to the next decision.

---

#### Example 3: Mixed Maturity Organization — Large Org with Varying Experience Levels

A large engineering firm has assembled a project team that mixes experienced PMs with junior engineers and functional specialists (cost controllers, schedulers, document controllers) who have varying familiarity with EVM and with AI tools.

**Tiered persona assignment:**

| Team Role | AI Persona | Execution Mode | Rationale |
|-----------|-----------|:---:|---|
| Senior PM | Senior Project Manager | Expert | Full capability, immediate execution |
| Junior PM | Senior Project Manager | Standard | Full capability with approval safety net |
| Cost Controller | Friendly Project Analyzer | Standard | Read-only insights; write operations via human PM |
| Discipline Engineer | Friendly Project Analyzer | Safe | Read-only, no risk of data modification |
| Executive Sponsor | Friendly Project Analyzer | Safe | Summaries and explanations only |
| IT Administrator | System Manager | Expert | Full system management capability |

**Delegation configuration.** The Senior PM's AI assistant is configured with a curated set of capabilities: WBS and work package operations, cost registrations and forecasts, performance analysis, change order lifecycle management, and diagram generation for project structure visualization. The temporal analysis capability is excluded to prevent accidental context shifts during critical reporting periods.

The Junior PM's main agent uses the same specialist set but with Standard execution mode providing the approval safety net. As the junior PM gains experience over several months, the execution mode is upgraded to Expert.

**Result.** Each team member receives AI assistance appropriate to their role and experience level. The experienced PM works at full speed, the junior PM learns with a safety net, and non-PM roles get read-only insights without risk. The AI adapts to the organization's skill distribution rather than forcing a one-size-fits-all approach.

---

### 4.3 Execution Safety Configuration

Backcast provides three execution safety tiers that control what actions the AI can perform and what safeguards are in place. The execution mode is selected by the user at the start of each conversation and applies for the duration of that session.

**Safe mode.** Only read operations are available. The AI can query projects, retrieve metrics, and display information, but cannot create, modify, or delete any data. Use Safe mode for demonstrations, for training sessions, for stakeholder reviews, and for any situation where you want AI insights without any risk of data modification.

**Standard mode (default).** Read and write operations are available, but critical operations (deletion, bulk operations) are blocked. Write operations require explicit user approval: the AI pauses and presents the proposed action for review and confirmation. Use Standard mode for day-to-day project management where the AI assists with routine data entry but the user retains control over every modification.

**Expert mode.** All operations are available, including deletion and bulk actions. No approval workflow is triggered; the AI executes immediately. Use Expert mode for experienced users who accept full responsibility for AI-initiated actions, for time-critical operations where approval delays are unacceptable, and for batch operations that would be impractical to approve one by one.

**Matching tiers to roles.** As a general guideline: assign Safe mode to Viewers and external stakeholders, assign Standard mode to new managers and anyone still building confidence with AI-assisted workflows, and assign Expert mode to experienced managers who understand the implications of AI-initiated write operations. Remember that the execution mode acts as a secondary filter on top of the persona's RBAC role — even in Expert mode, a read-only persona cannot write data because it lacks the underlying RBAC permissions.

---

## 5. Configuration by Team Size — Quick Reference

| Dimension | Solo PM (1-2) | Small Team (3-8) | Medium Team (10-25) | Large Team (25-50) | Enterprise (50+) |
|-----------|:---:|:---:|:---:|:---:|:---:|
| **Roles needed** | Admin + Manager | Admin + Manager + Viewer | Admin + Manager + Viewer + custom | Admin + Manager + Viewer + custom | Admin + Manager + Viewer + multiple custom |
| **Org unit depth** | Flat (1 level) | Flat (1-2 levels) | 2 levels | 2-3 levels | 3+ levels |
| **Approval tiers** | 2 tiers (PM + Director) | 2-3 tiers | 3-4 tiers (default) | 4 tiers (default) | 4 tiers (tightened thresholds) |
| **LOW threshold** | 25,000 EUR | 15,000 EUR | 10,000 EUR (default) | 5,000 EUR | 2,500 EUR |
| **CRITICAL threshold** | 150,000 EUR | 100,000 EUR (default) | 75,000 EUR | 50,000 EUR | 25,000 - 50,000 EUR |
| **Default SLA (LOW)** | 15 days | 10 days (default) | 10 days (default) | 10 days (default) | 10 days |
| **Default SLA (CRITICAL)** | 5 days | 3 days (default) | 3 days (default) | 3 days (default) | 2 days |
| **AI persona for PM** | Senior PM (Expert) | Senior PM (Standard) | Senior PM (Standard/Expert) | Senior PM (Standard/Expert) | Senior PM (Expert) |
| **AI persona for team** | Friendly Analyzer (Safe) | Friendly Analyzer (Safe) | Friendly Analyzer (Safe) | Mixed per role | Mixed per role |
| **Change management** | Lean | Lean-to-default | Default (CCB optional) | Formal (CCB recommended) | Enterprise governance |
| **Impact weight priority** | Budget-heavy | Budget-heavy | Balanced | Balanced-to-EVM | EVM-weighted |
| **Per-project overrides** | Rarely needed | Optional | Recommended for key projects | Standard practice | Required per contract |
| **Execution mode default** | Expert | Standard | Standard | Standard | Standard |

---

## 6. Configuration Checklist

Use this ordered checklist when deploying Backcast for the first time or onboarding a new project. Each step references the relevant section of this guide.

**Phase 1: Foundation (System Administrator)**

1. **Create user accounts** — Enter all team members with their names, emails, and initial passwords. Assign each user a global role (Admin, Manager, or Viewer). Refer to Section 2.1 for the permission model.
2. **Define organizational units** — Create the department or discipline hierarchy that reflects your company structure. Refer to Section 2.3 for organizational unit design examples.
3. **Create custom roles (if needed)** — If the three default human roles do not match your organizational model, create custom roles by selecting from the available permissions. Refer to Section 2.2 for delegation style examples.

**Phase 2: Change Management (PMO Director or Administrator)**

4. **Configure impact scoring weights** — Set the budget, schedule, revenue, and EVM weights to reflect your organization's priorities. Refer to Section 3.3 for weight tuning guidance.
5. **Set impact level thresholds** — Adjust the financial thresholds and score boundaries for each of the four impact levels based on your typical project size. Refer to Section 3.2 for tier configuration examples.
6. **Map approval authority** — Assign the required approver role for each impact level. Ensure segregation of duties (change creators cannot approve their own changes). Refer to Section 3.1 for the approval tier overview.
7. **Configure SLA rules** — Set business-day deadlines per impact level and the escalation trigger percentage. Select the appropriate holiday calendar. Refer to Section 3.2 for SLA examples.
8. **Customize the workflow (optional)** — Adjust state transitions, lock/unlock rules, and editable statuses. Add custom fields if your change orders require additional information. Refer to Section 3.1 for workflow adaptability.

**Phase 3: AI Configuration (System Administrator)**

9. **Configure AI providers** — Set up the connection to your chosen AI service. Refer to your Backcast deployment documentation for supported providers and connection instructions.
10. **Review AI persona assignments** — Confirm that each user's assigned AI persona matches their organizational role. The persona's access level should not exceed the user's RBAC role. Refer to Section 4.1 for persona descriptions.
11. **Customize AI behavior (optional)** — Adjust communication style, response precision, and response depth to match your organization's communication culture. Refer to Section 4.1 for customization options.
12. **Set default execution mode** — Determine whether Standard mode (the default) is appropriate for your team or whether specific users should start in Safe or Expert mode. Refer to Section 4.3 for execution safety guidance.

**Phase 4: Project Setup (Project Manager or Administrator)**

13. **Configure project budget settings** — Set the budget warning threshold percentage and decide whether to enforce budget limits for the project. Refer to your project settings page.
14. **Apply per-project workflow overrides (if needed)** — If a specific project requires different impact thresholds or approval tiers than the global configuration, create a project-level override. Refer to Section 3.3 for per-project override scenarios.
15. **Assign project-scoped roles** — For matrix organizations, assign users to project-specific roles. Refer to Section 2.2 for scoped role assignment examples.
16. **Verify the configuration** — Create a test change order and walk it through the full approval lifecycle to confirm that impact scoring, approval routing, and SLA tracking behave as expected.

---

*This guide is a companion to the Human-AI Collaboration Guide, which covers the operational aspects of working with AI assistants in Backcast. For questions about day-to-day AI interaction patterns, specialist routing, and conversational workflows, refer to the Human-AI Collaboration Guide.*