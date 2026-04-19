<p align="center">
  <img src="frontend/public/assets/images/backcast-logo.svg" alt="Backcast" width="400">
</p>

<p align="center">
  <strong>Develop projects together with AI-powered team experts</strong><br>
Change Control, Earned Value Management, Chat with data. Navigate project timeline. Understand decision impacts simulating events across time. 
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT">
  <img src="https://github.com/ogghst/backcast/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome">
  <img src="https://img.shields.io/badge/docker-ready-blue.svg" alt="Docker Ready">
</p>

---

## Screenshots

<p align="center">
  <em>Dashboard &mdash; AI Chat &mdash; Time Travel &mdash; Project Explorer</em>
</p>

<!-- TODO: Add screenshots from a running instance -->
<!--
<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard" width="45%">
  <img src="docs/screenshots/ai-chat.png" alt="AI Chat" width="45%">
</p>
<p align="center">
  <img src="docs/screenshots/time-travel.png" alt="Time Travel" width="45%">
  <img src="docs/screenshots/explorer.png" alt="Project Explorer" width="45%">
</p>
-->

---

Traditional project management tools force you into rigid forms and fixed workflows. Pure AI assistants are conversational but lack the structure for professional-grade budget tracking, EVM compliance, and audit trails. Backcast bridges both: a full-featured project management platform where you can work through structured dashboards and forms **or** talk to your data through AI assistants &mdash; moving seamlessly between the two as the task demands.

---

## Why Backcast?

If you manage projects with complex budgets, you know the pain:

- **Spreadsheet hell** &mdash; budgets live in Excel, no audit trail, no history
- **No what-if analysis** &mdash; you can't test a budget change without breaking the real numbers
- **Black-box EVM** &mdash; earned value metrics in proprietary tools you can't inspect or extend
- **No AI assistance** &mdash; you spend hours building reports instead of asking questions

Backcast solves this with a Git-inspired approach to project data:

| You're used to... | Backcast gives you... |
|---|---|
| Manually computing EVM metrics | **AI assistant** &mdash; *"What's the CPI of Project Alpha?"* |
| Overwriting budgets with no history | **Time Machine** &mdash; navigate to any date, past or future, and explore what-if scenarios |
| Guessing the impact of a change order | **Change Orders** &mdash; test budget changes in a branch, review the diff, then merge |
| Copy-pasting charts into PowerPoint | **Custom Dashboards** &mdash; 15+ drag-and-drop widgets, auto-refreshing |
| Paying per seat for EVM compliance | **Open source** &mdash; ANSI/EIA-748 compliant, self-hosted, free forever |

---

## Use Cases

### Starting a project from scratch

A project manager wins a contract for a new production line with 12 machines. No structure exists yet &mdash; just a contract and a deadline.

They start by creating a **Planner agent** configured with a cost-focused LLM and write access to project structure. Then they open a chat:

> *"I have a new production line project for ACME Corp, contract value 4.2M, delivering 12 assembly machines by March 2027. Each machine has mechanical, electrical, and software engineering departments. Build the project structure with WBEs and cost elements."*

The agent creates the full hierarchy &mdash; project, 12 WBEs, cost elements per machine &mdash; in seconds. The PM reviews it in the Project Explorer, adjusts a few budgets, and the project is ready to track.

Later, they add a **Cost Controller agent** with write access limited to cost registrations, so the accounting team can log invoices without touching the project structure.

### Catching a budget overrun early

Three months in, the PM opens the dashboard and notices the electrical engineering CPI dipping below 0.85 on Machine 7. Instead of digging through spreadsheets, they ask:

> *"Why is Machine 7 electrical engineering underperforming? Show me cost registrations for the last 60 days."*

The AI surfaces a cluster of unexpected rework costs. The PM opens a change order, increases the budget by 8%, and uses Impact Analysis to show the effect on the overall project EAC before sending it for approval.

### Exploring a what-if scenario

A supplier offers to deliver critical components two months early &mdash; at a 5% premium. The PM sets the control date back to when the original order was placed, creates a branch, and modifies the procurement cost element with the new price and timeline. They compare both timelines side by side: the premium is real, but the earlier delivery pulls the schedule variance back into positive territory across three downstream machines. They take the deal.

### Month-end review without the report

The PM's director wants a status update. Instead of building a deck, the PM shares a link to the project dashboard with pre-configured EVM widgets. The director can see CPI, SPI, variance trends, and the Gantt chart &mdash; all live, all self-updating. Questions that used to require a follow-up email now get answered on the spot.

### Connecting the corporate stack

A company runs SAP for procurement, a legacy ERP for cost accounting, and Power BI for executive reporting. Backcast's REST API and open data model fit right in. The IT team writes a sync pipeline that pushes approved invoices from the ERP into Backcast every night, so cost registrations are always current. Executives browse live EVM dashboards in Backcast &mdash; or connect Power BI directly to the PostgreSQL database and build their own views. No data silos, no manual exports.

---

## Features

### AI Assistants

Ask questions in **your preferred language** &mdash; not just English. The AI uses purpose-built tools to query budgets, calculate EVM metrics, draft change orders, and run variance analysis &mdash; all with real-time streaming responses. It can also **create and update project data** directly: attach invoices, add cost elements, modify schedules, and more.

Configure **multiple AI agents**, each with its own LLM, personality, and tool set. Build a team that fits your workflow: a cost-focused agent with write access to financials, a reporting agent that only reads EVM data, a change-order specialist. You choose the model, the tools, and the style &mdash; and each agent sticks to its lane.

*"Show me all projects where CPI is below 0.9"*
*"Add the attached invoice to the electrical engineering cost element"*
*"Update the construction plan by adding a new building, starting next year"*
*"Draft a change order to increase the mechanical engineering budget by 15%"*

### Time Machine

Set a control date to any point in your project's timeline &mdash; past, present, or future. Every change to budgets, cost elements, and schedules is tracked with full audit trails, so you can see how the project looked on a given date or how it's forecasted to look ahead.

Because you can modify project data at any control date, Time Machine opens up **what-if scenario analysis**: *What if I had increased the engineering budget a month ago? How would that have rippled through cost and schedule variance?* Make the change in a branch, compare against the real timeline, and decide with data instead of guesswork.

### Change Orders

Like pull requests for your project budget. Create a change order to work in an isolated branch &mdash; modify budgets, add cost elements, adjust schedules &mdash; then use the **Impact Analysis** view to see a side-by-side diff before merging to the main timeline. Includes SLA tracking, approval workflows, and full audit trails.

### Financial Tracking

The foundation everything else builds on. Distribute contract revenue across machines (WBEs) and down to department-level cost elements. Register actual costs by category &mdash; labor, materials, subcontracts, other &mdash; with invoice tracking and full audit trails. Budget enforcement blocks cost registrations that would exceed the allocated budget, so overruns get caught at the point of entry.

### Schedule Baselines

Define how work progresses over time for each cost element &mdash; linear (even spread), Gaussian (bell curve peaking at midpoint), or logarithmic (slow start, accelerating finish). Baselines drive Planned Value calculations and can be versioned and branched like everything else, so you can compare the original plan against reality at any point.

### EVM Analytics

Full ANSI/EIA-748-compliant Earned Value Management at every level &mdash; cost element, machine (WBE), and project:

- **Performance Indices** &mdash; CPI, SPI with gauge visualizations
- **Variance Analysis** &mdash; Cost Variance, Schedule Variance, Variance at Completion
- **Forecasting** &mdash; Estimate at Completion, Estimate to Complete, TCPI
- **Multi-Method Forecasting** &mdash; choose between Bottom-Up (re-estimate from scratch), Performance-Based (extrapolate from CPI/SPI trends), or Management Judgment (manual override) depending on where you are in the project lifecycle
- **Variance Alerts** &mdash; configurable thresholds (minor, moderate, significant, critical) that flag metrics drifting outside acceptable ranges
- **Time-Series Charts** &mdash; PV/EV/AC progression with daily/weekly/monthly granularity

All metrics respect time-travel and branch context.

### Custom Dashboards

Per-user, per-project dashboards built on a drag-and-drop widget system:

- 15+ widget types &mdash; budget overview, EVM gauges, variance bars, Gantt chart, KPI cards
- Responsive 12-column grid with auto-save
- Cross-widget communication &mdash; select an entity in one widget, others update
- Pre-built templates for Project Overview and EVM Analysis

### Project Explorer

Navigate your project hierarchy visually &mdash; projects, machines (WBEs), and department budgets (cost elements) in an interactive tree with inline status badges, progress bars, and a Gantt timeline.

### Quality Tracking

Track quality issues with cost impact, severity classification, root cause analysis, and resolution status &mdash; all versioned within the change order framework.

### Role-Based Access Control

Fine-grained permissions let you control exactly who can do what in each project. Assign roles per project with read or write capabilities across every feature &mdash; project structure, cost registration, AI assistant, dashboards, and change orders. An accountant can register costs but not modify the project hierarchy; a controller gets read-only EVM analytics; the project manager holds the keys.

### REST API & Open Data Model

Every feature in Backcast is accessible through a versioned REST API (`/api/v1`) with full OpenAPI documentation. Built on a proven open-source stack &mdash; FastAPI, PostgreSQL, React &mdash; Backcast integrates cleanly into existing corporate infrastructure: sync data from legacy ERPs, feed business intelligence tools directly from the database, or build custom automations on top of the API. No vendor lock-in, no proprietary formats.

---

## Quick Start

### Deploy with Docker

The fastest way to get Backcast running &mdash; backend, frontend, database, SSL, and automated migrations, all in one stack.

**Prerequisites:** Docker 24.0+, Docker Compose 2.20+, a domain pointing to your server.

```bash
git clone https://github.com/ogghst/backcast.git
cd backcast

# Create the Traefik network
docker network create traefik-public

# Configure your environment
cd deploy
cp .env.production.example .env.production
nano .env.production   # Set domain, passwords, secret key, email

# Build and launch
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d

# Run database migrations
docker compose --env-file .env.production run --rm alembic upgrade head
```

Open `https://app.yourdomain.com` and start managing projects.

For the full guide including SSL troubleshooting, Apache integration, and security hardening, see the [Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md).

### Local Development

For contributing or running locally without Docker:

**[Onboarding Guide](docs/00-meta/onboarding.md)**

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Pydantic V2 |
| Frontend | React 18, TypeScript, Vite, Ant Design |
| State | TanStack Query (server), Zustand (client) |
| Database | PostgreSQL 15+ with bitemporal range indexing |
| AI | LangGraph, LangChain, WebSocket streaming |
| Quality | MyPy strict, Ruff, Vitest |

---

## Documentation

### Architecture & Design

| Document | Description |
|----------|-------------|
| [System Map](docs/02-architecture/00-system-map.md) | Architecture overview |
| [EVCS Implementation Guide](docs/02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md) | Entity Versioning Control System internals |
| [EVM Calculation Guide](docs/02-architecture/evm-calculation-guide.md) | Formulas and interpretation |
| [EVM API Guide](docs/02-architecture/evm-api-guide.md) | API endpoint reference |
| [EVM Time-Travel Semantics](docs/02-architecture/evm-time-travel-semantics.md) | How time-travel interacts with EVM queries |
| [AI Agent Orchestration](docs/02-architecture/ai/agent-orchestration-guide.md) | LangGraph agent architecture |
| [AI Tool Development](docs/02-architecture/ai/tool-development-guide.md) | Building AI tools with `@ai_tool` |
| [Widget Dashboard Guide](docs/02-architecture/widget-dashboard-guide.md) | Dashboard and widget developer reference |
| [ADR Index](docs/02-architecture/decisions/adr-index.md) | Architecture Decision Records |

### User Guides

| Guide | Audience |
|-------|----------|
| [Dashboard & Widgets](docs/02-architecture/dashboard-user-guide.md) | All users |
| [AI Chat](docs/05-user-guide/ai-chat-user-guide.md) | All users |
| [AI Execution Modes](docs/05-user-guide/ai-execution-modes.md) | All users |
| [Change Order Workflow](docs/05-user-guide/change-order-workflow-guide.md) | Developers, admins |
| [EVCS & WBE Operations](docs/05-user-guide/evcs-wbe-user-guide.md) | Backend developers |

### Project Planning

| Document | Description |
|----------|-------------|
| [Product Vision](docs/01-product-scope/vision.md) | Business goals and scope |
| [Functional Requirements](docs/01-product-scope/functional-requirements.md) | Detailed feature requirements |
| [Product Backlog](docs/03-project-plan/product-backlog.md) | Current backlog |

Browse the full documentation starting from the **[Documentation Guide](docs/00-meta/README.md)**.

---

## Contributing

Contributions are welcome! Whether it's a bug fix, new feature, documentation improvement, or feedback from the project management trenches.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a Pull Request

See the [Onboarding Guide](docs/00-meta/onboarding.md) for development setup and coding standards.

---

## License

[MIT](LICENSE)
