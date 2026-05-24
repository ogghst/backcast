<p align="center">
  <img src="frontend/public/assets/images/backcast-logo.svg" alt="Backcast" width="360">
</p>

<p align="center">
  <strong>Run your projects through conversation.</strong><br>
  WBEs, work packages, cost elements, forecasts, schedules, change orders, cost of quality —<br>the vocabulary you already use, driven by AI that has the same access as any real user.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img src="https://github.com/ogghst/backcast/actions/workflows/ci.yml/badge.svg">
  <img src="https://img.shields.io/badge/docker-ready-blue.svg">
</p>

---

**Try it now — no install:** [app.backcast.duckdns.org](https://app.backcast.duckdns.org) &nbsp;·&nbsp; `admin@backcast.org` / `adminadmin`

---

Backcast won't replace your ERP. What it adds: a conversational layer where AI assistants can **do everything a human user can** — create WBEs and work packages, set up cost elements and schedules, register costs, manage change orders, run EVM analytics — while you watch, approve, or just ask questions.

```
"Create a project for ACME Corp, 12 WBEs, 3 cost elements each, 4.2M budget, March 2027."
"Register this invoice on the electrical engineering cost element for Machine 7."
"Open a change order to increase the mechanical work package budget by 15% and show me the EAC impact."
```

The AI acts. You decide how much it does on its own.

---

## What's inside

| | |
|---|---|
| 🤖 **AI Agents** | Multiple agents, each with its own LLM and permission scope — same RBAC as human users. Supports any OpenAI-compatible model: GPT-4o, Claude, Mistral, local models via Ollama, and more. Connects to external tools via MCP — web search, document repositories, corporate knowledge bases, or any MCP-compatible service. |
| ⏳ **Time Machine** | Navigate to any date in your project history. Every change to budgets, schedules, and forecasts is versioned — go back, explore forward, compare timelines. |
| 🔀 **Change Orders** | Branch your budget like a pull request. Modify work packages and cost elements in isolation, review the diff, merge when ready. Includes SLA tracking and approval workflows. |
| 📊 **EVM Analytics** | ANSI/EIA-748 compliant — CPI, SPI, EAC, ETC, TCPI, Cost of Quality — at cost element, WBE, and project level. |
| 🧩 **Dashboards** | 15+ drag-and-drop widgets. Share a live link instead of building a deck. |
| 🔌 **REST API** | Every feature accessible via API. Connect BI tools, sync from legacy ERPs, build automations. |

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

Python / FastAPI / PostgreSQL · React / TypeScript / Ant Design · LangGraph / LangChain · Docker

---

## Docs & contributing

[Documentation](docs/00-meta/README.md) &nbsp;·&nbsp; [EVM guide](docs/02-architecture/evm-calculation-guide.md) &nbsp;·&nbsp; [AI agents](docs/02-architecture/ai/agent-orchestration-guide.md) &nbsp;·&nbsp; [API reference](docs/02-architecture/evm-api-guide.md)

PRs welcome — bug fixes, features, or feedback from the project management trenches. See the [Onboarding Guide](docs/00-meta/onboarding.md) to get set up.

[MIT License](LICENSE)
