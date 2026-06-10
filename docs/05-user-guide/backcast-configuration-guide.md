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

### 4.1 The Job Description Paradigm

Backcast's AI assistants are configured the same way you staff a professional services engagement: you define roles, assign responsibilities, and establish operating procedures. Each AI component has a job description that specifies its scope of authority, behavioral expectations, and the specialist skills it can draw upon. Administrators write these job descriptions to mirror the organization's own structure, terminology, and processes.

**The engagement model.** When a team member opens a chat session, they are assigned a primary contact -- the main assistant -- whose role is comparable to a department coordinator. This coordinator receives the request, determines what expertise is needed, and brings in the right subject-matter specialists. A planning coordinator breaks down complex requests into structured subtasks before any work begins. A team lead then manages the execution, handing each subtask to the appropriate specialist and monitoring progress. This mirrors how a well-run project office operates: a single point of contact for the client, clear work breakdown, and structured delegation to domain experts.

**The three tiers of job descriptions.**

The **main assistant** is the engagement lead -- the person the user interacts with directly. Three engagement leads ship with Backcast, each designed for a distinct organizational function:

| Main Assistant | Organizational Analogy | Scope of Authority |
|---|---|---|
| **Friendly Project Analyzer** | Read-only business analyst | View and explain project data, EVM metrics, budget performance. Cannot create, modify, or delete anything. |
| **Senior Project Manager** | Senior PM with full project delivery authority | Create and update projects, WBS elements, work packages, cost elements, change orders, forecasts, and progress entries. Cannot manage users or system configuration. |
| **System Manager** | IT system administrator | Manage user accounts, organizational units, cost element types, and system configuration. Operates with caution and a verification-first approach. |

Each main assistant's job description defines its communication style, its organizational terminology, and which specialist team members it can call upon. A Friendly Project Analyzer speaks in clear, explanatory language and has access only to read-only specialists. A Senior Project Manager communicates concisely and can delegate to the full range of project delivery specialists.

**Specialists** are the subject-matter experts the main assistant calls in for specific tasks. Each specialist has a detailed job description that defines their domain expertise, procedural rules, and exact tool inventory. Nine specialists are available:

| Specialist | Organizational Analogy | Domain |
|---|---|---|
| **Project Structure Coordinator** | Project setup specialist | Create and modify project hierarchies: projects, WBS elements, control accounts, work packages, and cost elements. Batch operations and ANSI-748 structure validation. |
| **EVM Analyst** | Earned value performance analyst | Calculate CPI, SPI, CV, SV, EAC, ETC, VAC, TCPI. Assess health trends. Read-only analysis with no data modification. |
| **Change Order Processing Specialist** | Change management coordinator | Full change order lifecycle: creation, AI-powered draft generation, impact analysis, approval workflows, and branch management for change isolation. |
| **Cost Accountant** | Cost registration clerk | Record actual costs and cost events, track Cost of Quality, create and update forecasts, retrieve project documents. |
| **Reporting and Visualization Analyst** | Management reporting specialist | Generate structural diagrams for project hierarchies, WBS trees, cost breakdowns, and workflow visualizations. Read-only access to source data. |
| **IT User Administrator** | User account manager | Create, update, and delete user accounts with security best-practices enforcement. |
| **Master Data Controller** | Configuration data steward | Manage cost element types, cost event types, and organizational units -- configuration shared across all projects. |
| **Records and Audit Clerk** | Temporal context specialist | Change the point-in-time viewing context, switch between branches and branch modes, explain the implications of temporal perspective changes. |
| **General Duty Officer** | General-purpose fallback | Handle tasks that do not fit a specific domain. Access to all available capabilities as a safety net for ambiguous or cross-cutting requests. |

**The planner and supervisor** share a third tier of job descriptions that govern how work is organized and executed internally. The planner functions like a project management office analyst: it receives the user's request, considers which specialists are available, and produces a structured work plan -- either a single step for straightforward requests ("show me the budget status") or a multi-step plan with dependencies for complex ones ("analyze EVM performance across all control accounts, then generate a structural diagram of the cost breakdown"). Plans are capped at five steps maximum, and the planner always falls back to a single-step general-purpose assignment if analysis fails, ensuring the system never deadlocks.

The supervisor functions like a team lead following your organization's standard operating procedures. It receives the plan, delegates each step to the assigned specialist, monitors progress, and ensures quality standards are met. The supervisor never performs domain work itself -- it manages the team. Each main assistant persona can have its own supervisor instructions, tailored to how that persona's engagement type should be managed. A Friendly Project Analyzer's supervisor might follow a simple, conversational delegation style, while a Senior Project Manager's supervisor follows a structured, action-oriented process.

**How job descriptions are assembled.** Every job description is stored in the Backcast system configuration and can be modified without code changes. When a chat session begins, the system assembles the full team dynamically: the main assistant's job description is loaded, its assigned specialists are compiled, and the planner and supervisor receive instructions that include the current specialist roster. This ensures that the planner always knows which specialists are available and the supervisor can always reach the specialists the planner assigns -- there is never a mismatch between planning and execution.

---

### 4.2 Delegation Levels -- Your Per-Session Choice

When you open a chat session, you decide how much authority to grant the AI team for that conversation. This is not a system setting locked by an administrator -- it is your choice, made fresh each session, reflecting your comfort level and the situation at hand.

Think of it this way: when you assign a task to a junior team member, you might ask them to confirm every action with you before proceeding. When you assign the same task to a trusted senior colleague, you might simply say "handle it" and review the results afterward. Backcast's delegation levels work the same way.

**Three delegation levels are available:**

**Supervised delegation (Safe mode).** The AI team operates in a read-only capacity. Specialists can view data, run calculations, and produce reports, but they cannot create, modify, or delete anything. This is equivalent to hiring an auditor for a review engagement -- the team observes, analyzes, and advises, but takes no action.

Choose supervised delegation when:
- You are learning the system and want to understand what the AI can do before granting it broader authority
- You are reviewing project status with stakeholders and want insights without any risk of data modification
- You are demonstrating Backcast to a new team member or during a presentation
- You are working in a sensitive period such as month-end closing or audit preparation and want to ensure no changes occur

**Guided delegation (Standard mode, the default).** The AI team can read data and perform standard project operations -- creating records, updating existing data, and running routine processes. Critical operations such as bulk deletions and sensitive administrative actions remain blocked. This is equivalent to engaging a full-service project team with normal approval gates: the team handles day-to-day work, but high-stakes decisions require elevated authority.

Choose guided delegation when:
- You are performing day-to-day project management and want the AI to handle data entry, calculations, and routine updates
- You want a safety net -- the AI can act, but within controlled boundaries
- You are working with a new or unfamiliar project and want assistance without exposing critical operations
- You are a project manager who wants to delegate routine work while retaining oversight of significant actions

**Autonomous delegation (Expert mode).** The AI team has full authority over all available operations, including critical-risk actions such as bulk deletions, administrative configuration changes, and sensitive operations. No additional approval gates apply at the individual action level. This is equivalent to granting power of attorney -- you trust the team to exercise judgment and act decisively.

Choose autonomous delegation when:
- You are an experienced user who understands the implications of AI-initiated actions and accepts responsibility for them
- You are performing time-critical operations where approval delays are unacceptable
- You are executing batch operations that would be impractical to confirm one by one
- You are working on a well-understood project and want maximum speed

**Delegation applies uniformly across the specialist team.** The delegation level you choose gates the entire tool pool before any specialist is compiled. A specialist configured with write capabilities will find those capabilities unavailable in supervised mode, just as a cost accountant would find their spending authority revoked during a read-only audit engagement. The delegation level works alongside the main assistant's access level -- even in autonomous mode, a read-only main assistant cannot perform write operations because its underlying role does not permit them.

**Choosing the right level.** The delegation level is a reflection of your relationship with the AI team in that moment, not a permanent categorization of your role. A senior project manager might use supervised delegation when exploring an unfamiliar project, guided delegation for routine management, and autonomous delegation during a time-critical change order implementation -- all in the same day. Choose the level that matches your comfort, the task's urgency, and the data's sensitivity.

---

### 4.3 Configuring Assistant Job Descriptions

Administrators customize AI assistants to reflect the organization's culture, processes, and terminology. Every configurable element is stored in Backcast's system configuration and can be adjusted without code changes.

**Main assistant behavioral guidelines.** Each main assistant has a job description that defines:

- **Communication style:** How the assistant speaks -- formal or conversational, detailed or concise, explanatory or action-oriented. For example, the Friendly Project Analyzer is instructed to explain EVM concepts in plain language and define acronyms on first use, while the Senior Project Manager provides concise, data-dense responses and does not define standard EVM terms.
- **Organizational terminology:** Industry-specific terms, project naming conventions, and reporting standards that the assistant should use. An organization that calls control accounts "budget accounts" can instruct the assistant to adopt that terminology.
- **Scope of authority:** Which specialist team members the main assistant can call upon (the allowed specialists list) and which tasks the assistant can handle directly without delegation (the direct tools list). A main assistant with no direct handling capabilities must delegate every operation to a specialist -- analogous to a policy requiring all technical work to go through qualified experts.
- **Operating boundaries:** Rules about what the assistant should and should not do, such as "always confirm before creating change orders" or "never delete data without explicit user instruction."

**Specialist availability and scope.** Administrators control which specialists are active and what each one can do:

- **Active roster:** Specialists can be activated or deactivated. An organization that does not use AI-assisted user management can deactivate the IT User Administrator specialist, removing it from the team entirely.
- **Capability assignments:** Each specialist's exact tool inventory is configurable. A Cost Accountant can be given forecast creation authority, or that capability can be removed. The General Duty Officer has access to all tools by default (a wildcard assignment), but this can be narrowed to a specific set if the organization prefers tighter control.
- **Domain descriptions:** Each specialist's area of expertise and procedural rules are defined in their job description. The EVM Analyst is instructed to use comprehensive analysis calculations and to explain what metrics mean, while the Change Order Processing Specialist is instructed to generate draft change orders for new requests and to switch to the appropriate branch context before querying branch-specific data.

**Supervisor operating procedures.** Each main assistant can have customized supervisor instructions that define:

- **Delegation rules:** How the supervisor routes work to specialists and when to ask the user clarifying questions before proceeding.
- **Plan management:** How multi-step execution plans are managed -- the supervisor walks through plans one step at a time, checking dependencies and marking steps complete before delegating the next.
- **Quality standards:** What the supervisor checks before reporting results back, and how findings are compiled into the briefing document that the user sees.
- **Delegation enforcement:** A global policy option (set by the administrator) can lock the supervisor out of all domain tools entirely, forcing pure delegation to specialists. This is analogous to a corporate policy requiring all technical work to go through qualified specialists rather than being handled informally by a coordinator.

**Planner approach.** Each main assistant can have customized planner instructions that define:

- **Complexity thresholds:** When the planner produces a single-step plan versus a multi-step plan with dependencies. A read-only analyst might default to simpler plans, while a senior PM's planner recognizes multi-domain workflows that require coordination across several specialists.
- **Step limits:** The maximum number of steps the planner will produce (capped at five). A conservative configuration might limit plans to three steps, keeping engagement simpler and more predictable.
- **Specialist assignment preferences:** Which specialist the planner prefers for common task types, ensuring consistent routing patterns that match the organization's workflow habits.

**RBAC alignment.** Each main assistant operates under an AI-specific Role-Based Access Control (RBAC) role that further constrains what the assistant and its specialists can do, independent of tool assignments and delegation level:

| Main Assistant | Access Level | What This Means |
|---|---|---|
| Friendly Project Analyzer | Read-only | The assistant and all its specialists can only read data, regardless of delegation level chosen. |
| Senior Project Manager | Full project delivery | The assistant and its specialists can create, update, and delete project delivery data, but cannot manage users or system configuration. |
| System Manager | System administration | The assistant has system management capabilities including user accounts and organizational configuration. |

The main assistant's RBAC role should never exceed the human user's own role. A Viewer interacting with the System Manager would find the assistant's write operations blocked by the user's own permission boundaries.

---

### 4.4 Scenarios -- AI Assistants Adapted to Organizational Culture

#### Scenario 1: Formal Engineering Company -- Risk-Averse Culture with Hierarchical Approval

**Company profile.** A 35-person automation integrator serving the pharmaceutical industry. Projects are regulated, audits are frequent, and the Change Control Board meets weekly. The organizational culture values thorough documentation, clear accountability, and conservative decision-making. Every action must be traceable to an authorized individual.

**Main assistant configuration.**

The organization uses all three main assistants but configures them with conservative behavioral guidelines:

**Friendly Project Analyzer** -- Job description customized with: "Communicate formally. Cite data sources for every claim. Use PMBOK terminology consistently. When presenting variances, always include the threshold value and whether the current value is within contractual tolerance. Never use informal language or analogies." The specialist roster is limited to the EVM Analyst and the Reporting and Visualization Analyst -- no write-capable specialists are available even if the delegation level is raised.

**Senior Project Manager** -- Job description customized with: "Before creating or modifying any entity, summarize the intended action and its downstream impact. Use full entity names (never abbreviations). When creating change orders, always include impact analysis across all four dimensions (budget, schedule, revenue, EVM). Flag any action that would affect a control account currently under audit." The allowed specialists include the Project Structure Coordinator, EVM Analyst, Change Order Processing Specialist, Cost Accountant, and Reporting and Visualization Analyst. The supervisor has no direct handling capabilities -- every operation is delegated to a specialist, mirroring the company's policy that all technical work goes through qualified personnel.

**System Manager** -- Job description customized with: "Before any destructive action (deletion, bulk modification), present the full list of affected entities and request explicit confirmation. Never perform administrative changes during the first or last business day of the month (closing periods). Maintain a conservative posture: when uncertain, ask rather than act." The allowed specialists are the IT User Administrator and Master Data Controller only.

**Delegation enforcement.** The global delegation enforcement policy is enabled, ensuring the supervisor never handles domain work directly. This mirrors the company's standard operating procedure: the department coordinator routes work to specialists but never performs technical tasks themselves.

**Planner configuration.** The planner is configured with a three-step maximum (below the five-step system cap) to keep plans simple and auditable. The planner's instructions emphasize: "Prefer sequential over parallel steps. Each step should have a single, clear deliverable. If a request could be interpreted multiple ways, produce a single-step plan that asks the user for clarification rather than assuming."

**Team member delegation patterns.** Project managers typically use guided delegation (Standard mode) even after months of experience, reflecting the company's cautious culture. Only the PMO director uses autonomous delegation (Expert mode), and only for batch operations during controlled maintenance windows. All other team members use supervised delegation (Safe mode). The delegation level is a conscious choice each session -- the PM might use supervised delegation when reviewing a project they are unfamiliar with, even though they are authorized for guided delegation.

**Result.** The AI assistants operate as a structured, hierarchical team that mirrors the company's existing processes. Every action passes through a specialist, every plan is simple and auditable, and the delegation level reflects the organization's risk tolerance. The CCB sees the same rigor in AI-assisted operations that they expect from human team members.

---

#### Scenario 2: Agile System Integrator -- Fast-Moving Culture with Flat Hierarchy

**Company profile.** A 12-person system integrator that designs and installs packaging lines. The team is experienced, communication is informal, and decisions are made quickly. The company runs three to five concurrent projects, each managed by a senior PM who has full authority over their project. There is no formal CCB -- the PM handles change management directly, escalating to the director only for budget overruns above 15 percent.

**Main assistant configuration.**

The organization uses two main assistants, configured for speed and directness:

**Friendly Project Analyzer** -- Job description customized with: "Be brief. Lead with the number, then provide context if asked. Use the team's shorthand: 'WP' for work package, 'CA' for control account, 'CO' for change order. Skip explanations of standard EVM metrics unless the user explicitly asks." The specialist roster includes the EVM Analyst, Reporting and Visualization Analyst, and Records and Audit Clerk -- giving even the read-only assistant access to temporal navigation for quick date-based comparisons.

**Senior Project Manager** -- Job description customized with: "Act first, explain if asked. When the user requests an operation, execute it immediately and report what was done. Do not ask for confirmation on routine creates and updates. Ask before deletions and before any operation that affects more than five entities. Use the project's own naming conventions found in the project context." The allowed specialists include the full project delivery roster: Project Structure Coordinator, EVM Analyst, Change Order Processing Specialist, Cost Accountant, and Reporting and Visualization Analyst. The supervisor has direct handling capabilities for quick lookups -- it can pull up project data, budget status, and structure information without delegating to a specialist, keeping routine queries fast.

**System Manager** -- Used only by the IT lead. Configured with default behavioral guidelines.

**Delegation enforcement.** The global delegation enforcement policy is disabled. The supervisor can handle quick lookups directly without routing through a specialist, reducing turnaround time on simple requests.

**Planner configuration.** The planner uses the full five-step maximum to handle complex multi-domain requests efficiently. The planner's instructions emphasize: "Recognize common multi-step patterns: EVM analysis followed by visualization, structure creation followed by budget allocation, cost recording followed by performance analysis. Produce multi-step plans for these patterns proactively. Only fall back to single-step for truly simple queries."

**Team member delegation patterns.** All three PMs use autonomous delegation (Expert mode) as their standard choice. They are experienced, they trust the AI team, and they want speed. The cost engineer uses guided delegation (Standard mode) with the Friendly Project Analyzer -- they occasionally need to ask the AI to create forecasts on their behalf, but they want the safety net of confirmation. Discipline engineers use supervised delegation (Safe mode) for read-only queries during design reviews.

**Result.** The AI team operates like an extension of the company's flat, fast-moving structure. There is no unnecessary process overhead. The PM says "update the forecast for mechanical installation to reflect the three-week delay" and the AI handles it. The briefing document compiles results concisely, the PM reviews, and moves on. The configuration reflects trust in experienced professionals.

---

#### Scenario 3: Multi-Site Organization with Varying Maturity -- Corporate Template, Regional Adaptation

**Company profile.** A multinational OEM with 200 employees across headquarters (Europe) and three regional offices (North America, Middle East, Asia-Pacific). The PMO at headquarters defines standards, but each region operates with significant autonomy. Project maturity varies: the European office has used EVM for a decade, the North American office adopted it two years ago, and the Middle East and Asia-Pacific offices are new to formal earned value management.

**Corporate template configuration.**

Headquarters defines a standard set of AI assistant job descriptions that all regions start from:

**Friendly Project Analyzer (corporate template)** -- "Communicate clearly and professionally. Define all EVM acronyms on first use in each conversation. Use PMBOK 7th Edition terminology. When presenting variances, include both the numeric value and its significance (favorable/unfavorable, trending direction)." The specialist roster includes the EVM Analyst, Reporting and Visualization Analyst, and Records and Audit Clerk.

**Senior Project Manager (corporate template)** -- "Follow a structured approach: confirm understanding of the request, outline the planned actions, execute, and summarize results. Use full entity names. When creating or modifying control accounts, verify that the organizational unit assignment matches the project's responsibility assignment matrix." The allowed specialists include the full project delivery roster. The supervisor has no direct handling capabilities (delegation enforcement enabled at corporate level).

**Regional adaptation -- Europe (mature EVM practice).** The European office customizes the Senior Project Manager's job description: "The team is experienced with EVM. Do not define standard acronyms (CPI, SPI, EAC, ETC, VAC, TCPI). Provide concise, data-dense responses. Prioritize action items over descriptions. When analyzing performance, benchmark against the project's contractual thresholds automatically." The planner is configured to allow five-step plans and recognize complex multi-domain workflows. PMs use autonomous delegation (Expert mode) as standard practice.

**Regional adaptation -- North America (intermediate EVM practice).** The North American office keeps the corporate template largely unchanged but adds: "When the user asks about performance metrics, provide both the calculation and a brief explanation of what the metric indicates about project health. Highlight metrics that fall outside the typical range (CPI below 0.90 or above 1.10, SPI below 0.95)." The planner is limited to three-step plans to keep interactions manageable while the team builds familiarity. PMs use guided delegation (Standard mode) as their standard choice, with the option to switch to autonomous when they are confident.

**Regional adaptation -- Middle East and Asia-Pacific (new to EVM).** These offices enhance the Friendly Project Analyzer's job description significantly: "This team is learning earned value management. Explain every metric the first time it appears in a conversation. Use analogies from construction and manufacturing operations. When the user asks 'how is the project doing,' provide a narrative summary before presenting numbers. Always explain whether a variance is good or bad and why." The specialist roster is expanded to include all read-only specialists. The Senior Project Manager is initially restricted to the Project Structure Coordinator and Cost Accountant specialists only -- change order management is handled manually until the teams complete EVM training. All team members use supervised delegation (Safe mode) for the first three months, transitioning to guided delegation as they build confidence. The planner is configured with a two-step maximum to keep interactions simple and educational.

**Result.** The corporate template ensures consistency -- every region uses the same specialist definitions, the same RBAC role assignments, and the same organizational terminology. But each region tailors the behavioral guidelines, specialist access, planner complexity, and recommended delegation levels to match their team's maturity and culture. A PM transferring from the European office to the Middle East office would find the same underlying structure but a communication style and delegation pattern adapted to the local team's needs.

---

### 4.5 Customization Quick Reference

The table below summarizes what administrators can configure for each AI team component and what is fixed by the system.

| Component | Configurable by Administrators | Fixed by System |
|---|---|---|
| **Main Assistant** | Communication style and behavioral guidelines; organizational terminology and reporting standards; specialist roster (which experts are available); direct handling capabilities (what the coordinator can do without delegation); supervisor instructions; planner instructions; RBAC role assignment; AI model selection; response precision and depth | The internal coordination workflow (planning before delegation, delegation before reporting); specialist findings are always compiled into a shared briefing for the user |
| **Specialists** | Activation or deactivation of each specialist; domain description and procedural rules; exact capability inventory (which tools each specialist can use); specialist RBAC role; AI model selection; response precision and depth | Maximum plan size (five steps); automatic fallback to the General Duty Officer for requests that do not match a specific domain; capability availability is automatically adjusted based on the delegation level chosen for the session |
| **Supervisor** | Delegation rules and quality standards; plan management approach; per-assistant supervisor instructions; whether the supervisor can handle tasks directly or must always delegate (delegation enforcement policy) | Sequential plan execution (steps are completed in order with dependency checks); specialist work is isolated and findings are compiled into a single briefing |
| **Planner** | Complexity thresholds (when to produce multi-step plans); step limits (up to five); specialist assignment preferences; per-assistant planner instructions | Maximum plan size (five steps); automatic fallback to single-step assignment on analysis failure; plan structure always includes specialist assignment, task description, and dependencies |
| **Delegation Level** | Not administrator-configured — chosen by the user at the start of each chat session | Three levels (Supervised, Guided, Autonomous); risk classification of each capability; delegation level applies uniformly across all specialists; delegation level works alongside (never overrides) the main assistant's RBAC role |

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
| **Main assistant for PM** | Senior PM | Senior PM | Senior PM | Senior PM | Senior PM |
| **Main assistant for team** | Friendly Analyzer | Friendly Analyzer | Friendly Analyzer | Mixed per role | Mixed per role |
| **Typical PM delegation** | Autonomous | Guided | Guided / Autonomous | Guided / Autonomous | Autonomous |
| **Typical team delegation** | Supervised | Supervised | Supervised | Mixed per role | Mixed per role |
| **Change management** | Lean | Lean-to-default | Default (CCB optional) | Formal (CCB recommended) | Enterprise governance |
| **Impact weight priority** | Budget-heavy | Budget-heavy | Balanced | Balanced-to-EVM | EVM-weighted |
| **Per-project overrides** | Rarely needed | Optional | Recommended for key projects | Standard practice | Required per contract |
| **Planner step limit** | 5 (full) | 3-5 | 3-5 | 3-5 | 3-5 (corporate standard) |

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

**Phase 3: AI Assistant Configuration (System Administrator)**

9. **Configure AI providers** — Set up the connection to your chosen AI service. Refer to your Backcast deployment documentation for supported providers and connection instructions.
10. **Review main assistant job descriptions** — Confirm that each main assistant's job description — communication style, specialist roster, direct handling capabilities, and access level — matches the organizational role it serves. The assistant's access level should never exceed the user's own role. Refer to Section 4.1 for the job description paradigm and Section 4.3 for configuration details.
11. **Customize assistant behavior** — Adjust each main assistant's behavioral guidelines, specialist roster, supervisor operating procedures, and planner approach to reflect your organization's processes and communication culture. Refer to Section 4.3 for all customization options.
12. **Configure supervisor and planner (optional)** — Decide whether delegation enforcement is enabled (supervisor must always route to specialists), set planner step limits, and define specialist assignment preferences. Refer to Section 4.3 for supervisor and planner configuration.
13. **Document delegation level recommendations** — Prepare guidance for your team on which delegation level (Supervised, Guided, or Autonomous) to choose for common scenarios. Delegation level is each user's per-session choice — administrators provide recommendations, not restrictions. Refer to Section 4.2 for delegation level descriptions.

**Phase 4: Project Setup (Project Manager or Administrator)**

14. **Configure project budget settings** — Set the budget warning threshold percentage and decide whether to enforce budget limits for the project. Refer to your project settings page.
15. **Apply per-project workflow overrides (if needed)** — If a specific project requires different impact thresholds or approval tiers than the global configuration, create a project-level override. Refer to Section 3.3 for per-project override scenarios.
16. **Assign project-scoped roles** — For matrix organizations, assign users to project-specific roles. Refer to Section 2.2 for scoped role assignment examples.
17. **Verify the configuration** — Create a test change order and walk it through the full approval lifecycle to confirm that impact scoring, approval routing, and SLA tracking behave as expected. Open a chat session and test each delegation level to confirm the AI team responds as configured.

---

*This guide is a companion to the Human-AI Collaboration Guide, which covers the operational aspects of working with AI assistants in Backcast. For questions about day-to-day AI interaction patterns, specialist routing, and conversational workflows, refer to the Human-AI Collaboration Guide.*