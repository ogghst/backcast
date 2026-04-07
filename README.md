# Backcast

**Project Budget Management & Earned Value Management System** for end-of-line automation projects.

![Favicon](frontend/public/assets/images/backcast.png)

---

## Features

### Bitemporal Versioning & Time Travel

Every entity mutation is tracked with dual time dimensions — *valid time* (when the fact is true in business terms) and *transaction time* (when the system recorded it). A global **Time Machine** control lets you navigate to any point in history, query the database as it was on that date, and compare snapshots across branches.

### Branch Isolation & Change Orders

Change orders create dedicated Git-style branches (`BR-{code}`). Modifications to WBEs, cost elements, and budgets happen in isolation — the main timeline is untouched until the change order is **submitted, approved, and merged**. An **Impact Analysis** view provides side-by-side comparison of main vs. branch, hierarchical diffs, and KPI comparison cards. The full workflow includes SLA tracking, approval matrices, and audit trails.

### Earned Value Management (EVM)

Full ANSI/EIA-748-compliant EVM at every aggregation level — cost element, WBE, and project:

- **Performance Indices** — CPI, SPI with gauge visualizations
- **Variance Analysis** — Cost Variance (CV), Schedule Variance (SV), Variance at Completion (VAC)
- **Forecasting** — Estimate at Completion (EAC), Estimate to Complete (ETC), To-Complete Performance Index (TCPI)
- **Time-Series Charts** — PV/EV/AC progression with daily/weekly/monthly granularity
- **Batch Aggregation** — Server-side roll-up with weighted averages for parent entities

All EVM queries respect time-travel and branch context.

### AI Chat with Sub-Agents & Tools

A conversational AI assistant backed by LangGraph orchestration, with specialized tools for project data:

- **Natural Language Queries** — Ask about projects, WBEs, cost elements, and EVM metrics in plain English
- **AI Tools** — Purpose-built backend tools for CRUD operations, EVM calculations, change order drafts, and variance analysis
- **Sub-Agent Orchestration** — LangGraph agents with tool-calling, streaming responses, and context management
- **Execution Modes** — Safe (read-only), Standard (write with approval), Expert (full access) to control tool risk levels
- **WebSocket Streaming** — Real-time token streaming with execution lifecycle tracking

### Composable Widget Dashboard

Per-user, per-project customizable dashboards built on a plugin architecture:

- **15+ Widget Types** — Budget overview, EVM gauges, variance bars, Gantt chart, KPI cards, cost element tables, and more
- **Drag & Drop Layout** — `react-grid-layout` with 12-column responsive grid
- **Widget Registry** — Plugin-style registration; each widget self-registers on import
- **Context Bus** — Cross-widget communication via entity selection and Time Machine integration
- **Templates** — Pre-built dashboard templates (Project Overview, EVM Analysis) seeded on first use
- **Auto-Save** — Changes persist automatically with dirty-state tracking and navigation guards

### Project Explorer

A master-detail interface for navigating project hierarchies:

- **Card-Based Views** — Project, WBE, and Cost Element detail cards with inline charts
- **Interactive Project Tree** — Hierarchical tree with InfoPill labels (status, budget, EVM indices)
- **Allotment Split Panels** — Resizable tree + detail layout
- **Gantt Chart** — ECharts-based timeline with rich text labels, dual-grid layout, and branch/time-travel support

### Hierarchical Project Structure

- **Projects** — Top-level containers with contract value, customer info, and project manager
- **WBEs** (Work Breakdown Elements) — Machines or deliverables with hierarchical nesting (sub-WBEs)
- **Cost Elements** — Departmental budgets with type classification (Engineering, Electrical, etc.)
- **Schedule Baselines** — Versioned, branchable schedule registrations with linear, Gaussian, and logarithmic progression types
- **Revenue Allocation** — Revenue tracking at WBE level, distributed to cost elements via planned value

### Quality Events

Track quality issues with cost impact, severity classification, root cause tracking, and resolution status — all versioned within the EVCS framework.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Pydantic V2 |
| Frontend | React 18, TypeScript, Vite 7, Ant Design 5 |
| State | TanStack Query (server), Zustand (client) |
| Database | PostgreSQL 15+ with TSTZRANGE bitemporal ranges |
| AI | LangGraph, LangChain, WebSocket streaming |
| Quality | MyPy strict, Ruff, Vitest, 80%+ coverage |

---

## Installation & Deployment

- **[Development Setup](docs/00-meta/onboarding.md)** — Local dev environment setup
- **[Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md)** — Production deployment with Docker, Traefik, and Let's Encrypt SSL

---

## Documentation

Browse the full documentation starting from the **[Documentation Guide](docs/00-meta/README.md)**.

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

## License

[TBD]
