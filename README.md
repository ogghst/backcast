<p align="center">
  <img src="frontend/public/assets/images/backcast-logo.svg" alt="Backcast" width="400">
</p>

<p align="center">
  <strong>Open-source project budget management with AI-powered Earned Value Analysis</strong><br>
  Git-style versioning for your project data. Ask questions in plain English. Travel back in time.
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

## Features

### AI Assistant

Ask questions about your projects in plain English. The AI uses purpose-built tools to query budgets, calculate EVM metrics, draft change orders, and run variance analysis &mdash; all with real-time streaming responses.

*"Show me all projects where CPI is below 0.9"*
*"What's the cost variance for the Alpha project's electrical engineering department?"*
*"Draft a change order to increase the mechanical engineering budget by 15%"*

### Time Machine

Set a control date to any point in your project's timeline &mdash; past, present, or future. Every change to budgets, cost elements, and schedules is tracked with full audit trails, so you can see how the project looked on a given date or how it's forecasted to look ahead.

Because you can modify project data at any control date, Time Machine opens up **what-if scenario analysis**: *What if I had increased the engineering budget a month ago? How would that have rippled through cost and schedule variance?* Make the change in a branch, compare against the real timeline, and decide with data instead of guesswork.

### Change Orders

Like pull requests for your project budget. Create a change order to work in an isolated branch &mdash; modify budgets, add cost elements, adjust schedules &mdash; then use the **Impact Analysis** view to see a side-by-side diff before merging to the main timeline. Includes SLA tracking, approval workflows, and full audit trails.

### EVM Analytics

Full ANSI/EIA-748-compliant Earned Value Management at every level &mdash; cost element, machine (WBE), and project:

- **Performance Indices** &mdash; CPI, SPI with gauge visualizations
- **Variance Analysis** &mdash; Cost Variance, Schedule Variance, Variance at Completion
- **Forecasting** &mdash; Estimate at Completion, Estimate to Complete, TCPI
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

---

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/ogghst/backcast.git
cd backcast
cp backend/.env.example backend/.env  # Configure your environment
docker compose up -d postgres  # Start the database
```

Then start the backend and frontend separately for development:

```bash
# Backend
cd backend && source .venv/bin/activate
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8020

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and start managing projects.

For **production deployment** with Traefik, SSL, and automated migrations, see the [Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md).

### Developer Setup

Full development environment setup, architecture walkthrough, and coding standards:

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
