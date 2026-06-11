<p align="center">
  <img src="frontend/public/assets/images/backcast-logo.svg" alt="Backcast" width="360">
</p>

<p align="center">
  <strong>AI assistants that understand your project management world —<br>version-controlled budgets, earned value management, and change governance<br>for industrial automation teams.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img src="https://github.com/ogghst/backcast/actions/workflows/ci.yml/badge.svg">
  <img src="https://img.shields.io/badge/docker-ready-blue.svg">
</p>

---

Your team knows how to deliver industrial automation projects. Backcast gives them AI assistants that speak their language — assistants that understand your data, your procedures, and your governance policies. When a project controller needs to know what a CPI of 0.89 means for the change order they are preparing, the AI already knows your approval thresholds, your contractual requirements, and how to present the findings to your Change Control Board.

---

**Backcast** is a project budget management and earned value platform built for capital project organizations delivering end-of-line automation. It gives your PMO AI assistants that are tailored to how you work — combined with a single source of truth for scope, cost, and schedule, Git-style versioning that makes every financial decision auditable, every change order reversible, and every EVM metric defensible.

Three things set Backcast apart:

1. **AI assistants configured like team members** — the AI knows which information is needed for a change order, what a low CPI means for your project, and how to present it to your CCB. Configured like a job description, not a feature toggle.

2. **Bitemporal versioning** — every change to budgets, forecasts, work packages, and cost elements is automatically versioned. You can reconstruct the exact state of any project at any past date, compare two points in time, and trace exactly when and why a number changed.

3. **Branch-isolated change orders** — change orders work like Git branches. Your team experiments in an isolated sandbox, sees the full diff before merging, and nothing touches the live project baseline until an approver explicitly says yes.

The AI drafts, calculates, and recommends, but it can never approve, reject, sign off baselines, commit forecasts, or authorize budget transfers. Accountability always rests with a named human role.

---

## See it in action

**[Live Demo →](https://app.backcast.duckdns.org)**

- **Email:** `admin@backcast.org`
- **Password:** `adminadmin`

Jump in, create projects, open change orders, travel through time. The demo is built to be tested hard.

Your AI assistant already knows your WBS naming conventions, your approval thresholds, and your reporting standards. Here is what that looks like in practice:

Imagine opening a chat and saying:

> "Create the 'Renovation HQ 2027' project with a 3-level WBS, €8.4M budget, starting in March."

The AI builds the entire project structure — work breakdown elements, control accounts, work packages, cost elements — and you review before anything is committed.

> "Record the €142k invoice from supplier Alpha on the HVAC cost element of the Mechanical package."

Actual costs are booked against the right cost element, EVM metrics recalculate instantly, and the audit trail captures who recorded what, when, and why.

> "Open a change order to shift the Electrical package by 3 months and increase the Mechanical budget by 18%. Show me the impact on EAC and TCPI."

A branch is created. The AI runs a four-dimension impact analysis — budget, schedule, revenue, EVM — and presents findings in plain language so the Change Control Board can decide faster.

> "Compare current status with the project state from 45 days ago."

Time Machine reconstructs the project as it existed 45 days ago. You see CPI, SPI, EAC, and every other metric at that point in time, with full variance context explained.

You control how autonomous each agent is — from "act and notify me" to "always propose first." Three delegation levels let you match the autonomy to the situation: supervised (read-only) for executive reviews, guided (confirmation-gated) for daily management, and autonomous (full delegation) for experienced users during bulk data entry. You choose your delegation level when you open each chat session — it is your decision, not a system setting.

---

## Built for how your team actually works

Backcast adapts to your organization, not the other way around. The AI assistant is configured like a team member's job description — it knows your terminology, your approval thresholds, your reporting standards. A solo project manager on a single automation line and a 200-person OEM delivering across three regions use the same system, with AI assistants tailored to each team's maturity and governance model.

| Dimension | Solo PM or Small Team | 25-Person Program | Enterprise OEM (50+) |
|---|---|---|---|
| **Team size** | 1-8 people, 2-3 roles | 10-25 people, custom roles | 50+ with segregation of duties |
| **Change control** | Lean: elevated thresholds, 2 approvers, optional review state | Balanced: full 6-state workflow, optional CCB | Formal CCB: tightened thresholds, 4 approval levels, per-contract overrides |
| **EVM maturity** | AI explains every metric, guided delegation, limited planner steps | AI highlights out-of-range values, balanced autonomy | Data-dense responses, benchmarking against contractual thresholds, full planner |
| **Organization** | Flat, single site | 2-level org units, per-project overrides | 3+ level hierarchy, corporate template with regional adaptation |
| **AI delegation** | Autonomous for the PM | Guided with escalation option | Per-role delegation, supervised for new teams |

### Your change control, your rules

Whether you run a formal Change Control Board with four-tier approval routing, or a lean process where the PM self-approves below a threshold and discipline leads review the rest — Backcast configures to your governance model. The state machine is fixed (Draft → Submitted → Under Review → Approved/Rejected → Implemented), but thresholds, approver levels, SLA deadlines, and field requirements are all adjustable per project or per contract.

### EVM expertise is not a prerequisite

Your AI assistant meets your team where they are. Your team in the Middle East office is new to earned value. Your European team has been running EVM for a decade. Backcast adapts. For beginners, the AI explains every metric on first use with manufacturing analogies: "For every euro spent, the project earned only 89 cents of value." For veterans, it skips the definitions and benchmarks against your contractual CPI thresholds automatically.

---

## Core capabilities

### AI agents that respect your authority

Each AI persona understands its role in your organization. The Analyzer speaks the language of executive review — concise, data-backed, read-only. The Senior PM handles operational conversations — creating work packages, preparing change orders, running impact analysis — the way your best project controller would. The System Manager handles administration carefully, with a verification-first approach.

Every persona inherits the requesting user's permissions. The AI can never exceed the human's authorization boundary. It drafts change orders, performs impact analysis, and generates stakeholder-specific reports. But it never approves, rejects, commits forecasts, or authorizes budget transfers.

Three delegation levels let you dial autonomy to match context: read-only for audits and executive reviews, confirmation-gated for daily project management, and full delegation for experienced users during bulk operations. RACI enforcement means the AI is always Responsible for data processing but never Accountable for decisions.

Agents can use different AI models from multiple providers, including local and self-hosted options — your data stays in your infrastructure.

### Version-controlled project data

Every change to budget, schedule, forecast, work packages, and cost elements is automatically versioned. This is not a changelog. It is a full bitemporal model: the system records both when a change occurred in the real world and when it was recorded in the system.

You can travel to any past date and see exactly how the project looked at that moment — not just the numbers, but the complete hierarchy, EVM metrics, and forecast state. Switch between the main project and any change order branch to evaluate proposed changes against the current baseline.

During audits, client reviews, or variance justification, this is the difference between "I believe the number was X" and "here is exactly what the project looked like on March 15, and here is the change that altered it two days later."

### Change orders with real governance

Change orders operate in isolated branches — sandbox copies of the project where your team can experiment freely. Nothing touches the live project baseline until the change order is approved and merged.

The workflow follows PMI's Perform Integrated Change Control: Draft → Submitted → Under Review → Approved or Rejected → Implemented. Approval routing is automatic, based on a configurable composite impact score across budget (40%), schedule (30%), revenue (20%), and EVM degradation (10%). SLA deadlines tighten as the impact level rises. Segregation of duties is enforced: the person who creates a change order cannot approve it.

Reviewers see both change-only and composite preview views before approving. The complete audit trail captures every state transition with timestamps, actors, and justification.

### ANSI/EIA-748 compliant EVM

Full Earned Value Management calculated at every level of the WBS hierarchy — cost element, work package, control account, and project. The metric suite covers Planned Value, Earned Value, Actual Cost, BAC, EAC, ETC, CPI, SPI, TCPI, CV, SV, and VAC.

Control Accounts sit at the intersection of WBS Element and Organizational Unit, pairing budget authority with technical responsibility as the standard requires. The Performance Measurement Baseline is an approved, time-phased budget plan against which all performance is measured, with immutable milestone baselines captured at each significant lifecycle event.

Forecasting supports three concurrent methodologies per cost element — bottom-up re-estimate, performance-based (BAC/CPI), and management judgment — with stability tracking via EAC standard deviation to measure forecast convergence over time. Cost of Quality is tracked from incoming inspection through site commissioning with root-cause attribution.

### Tailored to your organization's way of working

Role definitions, approval thresholds, impact score weights, SLA durations, org unit hierarchies, WBS templates, and AI behavior are all configured the way you would write a team member's job description — not through code changes, but through system settings that capture how your organization actually operates. Settings can be overridden per project or per contract, because a defense contract and a commercial line installation don't follow the same rules.

Five defined roles (Administrator, Project Manager, Department Manager, Project Controller, Executive Viewer) map to PMI governance structures. Custom roles can be added. Permissions scope at three levels: global, project, and change-order — so a single user can hold different roles in different contexts, supporting matrix organizations.

### Dashboards that tell the story

15+ drag-and-drop widgets build custom views for different audiences: executive one-pagers with traffic-light indicators, detailed PMO variance analyses, department-specific performance breakdowns, and work-package-level team detail — all generated from the same underlying data, ensuring consistency across the organization. Save dashboard layouts and switch between views tailored to each stakeholder group.

---

## From order to commissioning

Backcast supports the full lifecycle of an end-of-line automation project:

**Proposal and award.** AI retrieves comparable past-project data to support estimation. Budgets are validated against historical benchmarks. The initial WBS is structured from domain-specific templates.

**Engineering and design.** The Performance Measurement Baseline is established. Work packages are defined with time-phased budget plans. Progression curves (linear, Gaussian, logarithmic) model how budget is consumed across the project timeline.

**Procurement and manufacturing.** Actual costs are recorded against cost elements as invoices arrive. CPI and SPI are calculated in real time. Variance threshold monitoring triggers alerts when trends deteriorate.

**Site installation and commissioning.** Milestone baselines capture project state at BOM Release, Shipment, and Commissioning Complete. Quality events are tracked with root-cause classification and cost attribution.

**Closeout and lessons learned.** The complete audit trail is available for post-project review. Historical data feeds back into estimation benchmarks for future proposals.

---

## How organizations configure it

The AI assistant is not one-size-fits-all. It is configured to match how each organization works:

**A formal defense contractor (35 people, risk-averse).** Conservative AI behavioral guidelines — the system cites data sources for every claim. All work routes through specialists. Planner is capped at three sequential steps. Guided delegation is standard, even for experienced PMs. Approval thresholds are tight: CRITICAL at €50K, four distinct approver levels, holiday-aware SLA calculations.

**An agile packaging-line integrator (12 people).** AI is configured for speed: act first, explain if asked. Full five-step planner for multi-domain patterns. All PMs use autonomous delegation. Discipline engineers use supervised delegation for read-only queries. Approval thresholds are elevated: LOW under €25K, only two approver roles.

**A multi-site OEM (200 people across HQ and three regions).** Corporate defines standard specialist definitions, RBAC roles, and terminology. Regions customize behavioral guidelines, specialist access, planner complexity, and delegation levels to match local EVM maturity. A PM transferring between regions finds the same structure but adapted interaction patterns. Per-contract workflow overrides handle differing client requirements.

---

## Get started

### Docker (recommended)

```bash
git clone https://github.com/ogghst/backcast.git && cd backcast
docker network create traefik-public
cd deploy && cp .env.production.example .env.production
nano .env.production   # domain, passwords, secret key, LLM API keys
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production run --rm alembic upgrade head
```

Full guide including SSL and Apache integration: [Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md)

### Local development

[Onboarding Guide](docs/00-meta/onboarding.md) — environment setup, coding standards, local dev workflow.

---

## Stack

Python / FastAPI / PostgreSQL · React / TypeScript / Ant Design · Docker

---

## Documentation and community

- [Full documentation](docs/00-meta/README.md)
- [EVM calculation guide](docs/02-architecture/evm-calculation-guide.md) — how every metric is computed
- [Change order workflow](docs/05-user-guide/change-order-business-guide.md) — business user guide
- [AI agent orchestration](docs/02-architecture/ai/supervisor-orchestrator.md) — how agents collaborate
- [Human-AI collaboration](docs/05-user-guide/human-ai-collaboration-guide.md) — delegation, safety tiers, personas
- [Configuration guide](docs/05-user-guide/backcast-configuration-guide.md) — adapting Backcast to your organization
- [EVM API reference](docs/02-architecture/evm-api-guide.md)

PRs welcome — bug fixes, features, or feedback from the project management trenches. See the [Onboarding Guide](docs/00-meta/onboarding.md) to get set up.

---

[MIT License](LICENSE)
