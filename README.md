<p align="center">
  <img src="frontend/public/assets/images/backcast-logo.svg" alt="Backcast" width="360">
</p>

<p align="center">
  <strong>Your project. Your team. Your AI agents that actually get work done.
  </strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img src="https://github.com/ogghst/backcast/actions/workflows/ci.yml/badge.svg">
  <img src="https://img.shields.io/badge/docker-ready-blue.svg">
</p>

---
Backcast lets you manage complex projects by simply talking in natural language. AI agents create Work Breakdown Elements (WBE), work packages, cost elements, record actual costs, handle change orders, and calculate EVM metrics — all with real user permissions.

---

## Try it right now (no installation)

**[Live Demo →](https://app.backcast.duckdns.org)**

- **Email:** `admin@backcast.org`
- **Password:** `adminadmin`

Jump in, create things, open change orders, travel through time. The demo is built to be tested hard.

---

## How it works in real life

You talk naturally and the AI **takes action**:

- “Create the ‘Renovation HQ 2027’ project with a 3-level WBS, €8.4M budget, starting in March.”
- “Record the €142k invoice from supplier Alpha on the HVAC cost element of the Mechanical package.”
- “Open a change order to shift the Electrical package by 3 months and increase the Mechanical budget by 18%. Show me the impact on EAC and TCPI.”
- “Compare current status with the project state from 45 days ago using Time Machine.”

You control how autonomous each agent is — from “do it and notify me” to “always propose first.”

---

## Key Features

- **🤖 Smart AI Agents with real RBAC**  
  Each agent can use different models (GPT-4o, Claude, Mistral, local Ollama…) and has precise permissions. Agents can collaborate and use external tools via MCP.

- **⏳ Time Machine**  
  The most powerful feature in Backcast.  
  Every change to budget, schedule, forecast, work packages, and cost elements is **automatically versioned**. You can:
  - Travel to **any past date** in the project
  - See exactly how the project looked at that moment (budget, EVM metrics, forecast)
  - Compare any two dates (e.g. today vs 60 days ago)
  - Explore “what-if” scenarios without affecting real data
  - Understand exactly when and why numbers changed (full audit trail)

  It’s like having Git for your entire project — transparent, safe, and incredibly valuable during reviews, audits, or when justifying variances to clients or management.

- **🔀 Change Orders as branches**  
  Open a change order → work in isolation (just like a Git branch) → see full diff → approve and merge with proper workflow and SLA. Clean, traceable, and secure.

- **📊 Serious Granular EVM**  
  Fully ANSI/EIA-748 compliant. CPI, SPI, EAC, ETC, TCPI, and Cost of Quality calculated at cost element, work package, and project level.

- **🧩 Flexible Dashboards**  
  15+ drag & drop widgets. Build custom views and share live links.

- **🔌 Full API**  
  Everything is accessible via REST. Easy to integrate with your existing systems.


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
