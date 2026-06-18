<p align="center">
  <img src="frontend/public/assets/images/backcast-logo.svg" alt="Backcast" width="360">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img src="https://github.com/ogghst/backcast/actions/workflows/ci.yml/badge.svg">
  <img src="https://img.shields.io/badge/docker-ready-blue.svg">
</p>

---

Backcast is the result of a personal journey to solve a universal frustration: the heavy tax of manual corporate data entry vs. the vital need for perfect project governance. What started as a weekend experiment with a "time-traveling" ledger revealed a deeper truth—that traditional tools burden teams instead of guiding them. Bridging this gap required capturing human intent without sacrificing structural safety. Backcast achieves this by pairing advanced, multi-agent AI coordination with rigid application guardrails. The result is an autonomous governance platform where specialized AI teams work alongside humans, executing complex project operations, managing costs, and interacting securely with legacy systems to turn project data from an administrative chore into a living, strategic asset.

## 1. The Narrative: From Time Travel to Autonomous Governance

### The Spark: A Time-Travelling Ledger

Backcast started as a weekend experiment born out of a simple, nagging question: *What if we could look at project data the way an archaeologist looks at layers of earth?*

Traditional project management tools only show you the world as it exists today—tracking the current delay, the active budget, and the immediate milestone. But they completely lose the context of *why*. I wanted a system with a "time-traveling" data ledger—a way to slide a drawer back in time and see exactly how a project was born, the exact moment a timeline shifted, and the forgotten context behind a critical decision.

When I built that temporal data model, the clarity was immediate. Being able to look back at the historical trajectory of a project completely changes how you handle reporting and governance. But it also exposed a massive roadblock.

### The Conflict: The Statistical Mirage vs. Deterministic Governance

Sophisticated project data models fail because they demand too much from the people using them. The cognitive load of understanding complex work breakdown structures (WBS), combined with the friction of meticulous data entry, turns project management tools into administrative burdens rather than strategic assets.

The obvious answer seemed to be Large Language Models (LLMs). LLMs are incredible at synthesizing concepts, drafting updates, and understanding human intent. However, applying them to complex corporate structures reveals a fundamental architectural mismatch: **the gap between the statistical, probabilistic nature of LLMs and the rigid, deterministic logic required to govern corporate data.**

Project governance demands flawless mathematical and procedural precision. An LLM operates on token probabilities; it does not inherently understand relational integrity, sequential constraints, or strict accounting rules. If you attempt to manage highly structured data—like parsing complex WBS hierarchies or calculating Earned Value Management (EVM) metrics like Schedule Variance (SV) and Cost Variance (CV)—using a purely text-based model, the system inevitably drifts into unpredictable behavior.

Moving from basic prompt engineering to reliable enterprise execution requires shifting away from massive upfront context dumps. Instead, systems must adopt a modular architecture that enforces **progressive disclosure** and strict environmental separation. Tool calling bridges the operational mechanics of reading and writing data, but it lacks semantic reasoning. It doesn't know *how* to build a logically sound hierarchy, map dependencies safely, or evaluate if a specific change order aligns with overarching corporate policies. To govern complexity, the statistical flexibility of the LLM must be tightly harnessed by a rigid, deterministic application layer.

### The Solution: Mirroring the Enterprise

The breakthrough came when I stopped treating AI as an isolated prompt-and-response engine and started looking at it through the lens of organizational design. In the real world, complex tasks are managed by structured teams. A single person rarely owns an entire process; instead, a task moves through individuals with distinct expertise, varying authorization levels, and specific functional roles—all bounded by strict corporate governance, compliance policies, and risk matrices.

Backcast implements this exact organizational hierarchy through a configurable multi-agent harness, applying core agentic design patterns—such as **Orchestrator-Workers** and **Reflection** models—directly to project controls.

```
                    [ Human / Agent Input ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
   [ Core Application API ]              [ External MCP Ecosystem ]
    (The Deterministic Guard)              (The Cognitive Sensors)
   ┌────────┴────────┐                    ┌───────┼───────┐
   ▼                 ▼                    ▼       ▼       ▼
[Data Validation] [RBAC & Policies]   [Web Search] [Legacy ERP] [Custom Skill]
   │                 │
   └────────┬────────┘
            ▼
   [(Time-Travel Ledger)]

```

#### Grounded Application Security

Unlike fragile sandboxes that grant AI raw database access, Backcast enforces strict boundary layers. **Agents interact with structured data using the exact same Application APIs as human users.**

Every single operation an agent attempts—whether creating a task, adjusting a baseline, or processing a financial metric—is intercepted and audited by the core application layer. It must pass through identical Role-Based Access Controls (RBAC), database constraints, and deterministic business logic. The LLM suggests the intent, but the application layer guarantees the structure.

#### Capability Expansion via MCP

While the core application layer acts as the deterministic guardrail, agents expand their cognitive reach using the **Model Context Protocol (MCP)**. MCP tools function as specialized skills extending beyond the core model:

* **Legacy & Web Integration:** Agents can use MCP to step outside the project sandbox—querying corporate legacy ERPs to validate material costs or scanning the web for real-time market shifts.
* **Autonomous Reflection & Collaboration:** Modeled after autonomous developer tools like *Claude Code*, Backcast agents don't just generate text; they hold distinct permission levels, execute specialized system prompts, and coordinate with real human users or other agents. They iteratively critique their own project plans before submittal, ensuring compliance with institutional policies before the API ever receives the data.

## 2. Technical Blueprint: Architecture & Use Cases

Backcast separates cognitive execution from deterministic state tracking. The system is split into a **Core Application Layer** handling the project engine and a **Multi-Agent Orchestration Layer** handling semantics and automation.

### Core Architecture Components

* **The Temporal Ledger:** Built on a historical event-sourcing or version-state database schema. Every change to a task, baseline, or financial assignment is tracked as a historical delta, allowing full project state reconstruction at any specific point in time.
* **Deterministic API Gateway:** A unified API exposing endpoints for WBS modifications, cost logging, change orders, and baseline revisions. This layer handles validation, preventing structural logical corruption (e.g., circular dependencies or unallocated budget inflation).
* **Configurable Agent Harness:** A declarative runtime where agent teams are defined using structured manifests. Profiles declare roles, specialized prompts, RBAC tokens, and targeted tool permission mappings.

### Primary Enterprise Use Cases

* **Autonomous Work Breakdown (WBS) Generation:** Real users input high-level statements of work. The agent team interprets the human intent, reviews historical project baselines, interacts via API to check resource parameters, and drafts a complete structured tree of nested tasks and milestones.
* **Intelligent Change Order Management:** When a project deviation occurs, an agent analyzes the downstream impacts. It checks the temporal ledger for the baseline trajectory, computes impact analysis, builds a compliant change order request through the application API, and alerts human stakeholders for approval.
* **Semantic EVM Tracking & Status Merging:** Instead of basic numerical dashboards, Backcast agents continuously evaluate Earned Value Management metrics alongside qualitative project updates, translating formulas into natural language strategic readouts.

## 3. Developer Notes & Implementation

Backcast is built for extensibility, making extensive use of modular APIs and open integration standards.

### Technology Stack

* **Backend Core:** Developed with Python using **FastAPI** for high-performance async API routing, paired with **SQLAlchemy** for deterministic database interaction and state management.
* **Agentic Frameworks:** Modeled around structured tool-calling loops and orchestration architectures (inspired by LangGraph and modern multi-agent coordination environments).
* **Extensibility Protocol:** Full native support for the **Model Context Protocol (MCP)**, allowing decoupled development of external system connectors.

### Extending Capabilities via MCP

To add custom capabilities to Backcast agents (such as connecting to a proprietary corporate ERP, an internal knowledge base, or a specific issue tracker), you can deploy an independent MCP server. Agents discover these capabilities dynamically based on their manifest configuration.

*Note: For detailed endpoint definitions, schema documentation, and custom agent team manifest syntax, refer to the OpenAPI spec (`/docs`) and the documentation linked below.*

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

---

## Get started

### Docker (recommended)

```bash
git clone https://github.com/ogghst/backcast.git && cd backcast
docker network create traefik-public
cd deploy && cp .env.production.example .env.production
# edit .env.production: domain, passwords, secret key, LLM API keys
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production run --rm alembic upgrade head
```

Full guide including SSL and Apache integration: [Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md)

### Ollama (local & cloud LLMs)

Both dev and deploy stacks ship an **[Ollama](https://ollama.com)** service — an OpenAI-compatible LLM endpoint preconfigured with **`gemma4:31b-cloud`** (cloud-hosted Gemma 4 31B). It runs on the non-standard host port **`11435`** (configurable via `OLLAMA_HOST_PORT`) so it never collides with a default Ollama install on `:11434`.

- **Cloud models** (tags ending in `-cloud`, e.g. `gemma4:31b-cloud`) run on Ollama's hosted cloud — **no GPU required**, but the local server must be signed in to an ollama.com account. Run once (the session persists in the Ollama volume):

  ```bash
  docker compose exec ollama ollama signin     # approve the printed ollama.com/connect link in your browser
  ```

- **Local models** (e.g. `gemma4:31b`, `gemma4:12b`) run on your own hardware and need a GPU. Add them to the pull list and enable GPU — see the [deploy guide](docs/05-user-guide/docker-deployment-guide.md#ollama) for the NVIDIA block.

> An **API key** (`OLLAMA_API_KEY`) is a separate, *optional* mechanism for **direct** `ollama.com` access (provider `base_url` `https://ollama.com/v1`) — it is **not** used by the local server, which authenticates cloud models via the `ollama signin` session.

```bash
# Pull additional models (idempotent)
docker compose exec ollama ollama pull gemma4:12b
docker compose exec ollama ollama list          # verify
```

**Connect Backcast to Ollama** in the AI Config UI: add an `ollama` provider with `base_url` `http://ollama:11434/v1` (in-container) or `http://localhost:11435/v1` (local backend), any dummy `api_key` (e.g. `ollama`), and model `gemma4:31b-cloud`.

Full setup, GPU, and troubleshooting: [Ollama section of the Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md#ollama).

### Local development

[Onboarding Guide](docs/00-meta/onboarding.md) — environment setup, coding standards, and local dev workflow (`uv` for the backend, Vite for the frontend).

---

## Documentation

- [Full documentation](docs/00-meta/README.md)
- [EVM calculation guide](docs/02-architecture/evm-calculation-guide.md) — how every metric is computed
- [Change order workflow](docs/05-user-guide/change-order-business-guide.md) — business user guide
- [AI agent orchestration](docs/02-architecture/ai/supervisor-orchestrator.md) — how agents collaborate
- [Human-AI collaboration](docs/05-user-guide/human-ai-collaboration-guide.md) — delegation, safety tiers, personas
- [Configuration guide](docs/05-user-guide/backcast-configuration-guide.md) — adapting Backcast to your organization

PRs welcome — bug fixes, features, or feedback from the project management trenches. See the [Onboarding Guide](docs/00-meta/onboarding.md) to get set up.

---

[MIT License](LICENSE)
