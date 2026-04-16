# Architecture Documentation

Quick reference for finding architecture documents. Start here when working on the Backcast system.

## Quick Links by Common Task

| I need to... | Read this |
| ------------ | --------- |
| **Understand the system** | [`00-system-map.md`](00-system-map.md) - High-level overview |
| **Understand domain boundaries** | [`01-bounded-contexts.md`](01-bounded-contexts.md) - Context mapping |
| **Write backend code** | [`backend/coding-standards.md`](backend/coding-standards.md) - Type safety, patterns, quality gates |
| **Write frontend code** | [`frontend/coding-standards.md`](frontend/coding-standards.md) - React patterns, state management |
| **Format dates & times** | [`frontend/date-formatting-guide.md`](frontend/date-formatting-guide.md) - Temporal formatting |
| **Work with EVCS/versioning** | [`backend/contexts/evcs-core/`](backend/contexts/evcs-core/) - Entity versioning framework |
| **Implement API endpoints** | [`cross-cutting/api-conventions.md`](cross-cutting/api-conventions.md) - REST patterns, RBAC |
| **Write database queries** | [`cross-cutting/database-strategy.md`](cross-cutting/database-strategy.md) - PostgreSQL, bitemporal |
| **Handle authentication** | [`cross-cutting/security-practices.md`](cross-cutting/security-practices.md) - JWT, RBAC |
| **Write tests** | [`testing/test-strategy-guide.md`](testing/test-strategy-guide.md) - Testing patterns |
| **Run tests** | [`testing/test-execution-runbook.md`](testing/test-execution-runbook.md) - How to execute tests |
| **Build EVM features** | [`evm-calculation-guide.md`](evm-calculation-guide.md) - Earned Value Management |
| **Build dashboard widgets** | [`how-to-create-a-widget.md`](how-to-create-a-widget.md) - Widget creation guide |
| **Build dashboard features** | [`dashboard-developer-guide.md`](dashboard-developer-guide.md) - Dashboard architecture |
| **Build AI chat features** | [`ai-chat-developer-guide.md`](ai-chat-developer-guide.md) - AI chat architecture |
| **Build branching features** | [`backend/contexts/branching/architecture.md`](backend/contexts/branching/architecture.md) - Branch context |
| **Build progression features** | [`backend/contexts/progression/architecture.md`](backend/contexts/progression/architecture.md) - Progression context |
| **Work with AI tools** | [`backend/api/ai-tools.md`](backend/api/ai-tools.md) - AI tool development |

## Folder Structure

```
02-architecture/
├── 00-system-map.md              # System overview
├── 01-bounded-contexts.md        # Domain boundaries
├── README.md                     # This file - navigation index
│
├── Root-Level Guides
│   ├── api-endpoints.md                  # API endpoint reference
│   ├── configuration.md                  # Configuration reference
│   ├── error-codes.md                    # Error code catalog
│   ├── migration-troubleshooting.md      # Migration issues & solutions
│   ├── testing-patterns.md               # Testing patterns reference
│   ├── code-review-checklist.md          # Code review guidelines
│   │
│   ├── EVM Guides
│   │   ├── evm-calculation-guide.md      # EVM calculations
│   │   ├── evm-api-guide.md              # EVM API reference
│   │   ├── evm-components-guide.md       # EVM React components
│   │   └── evm-time-travel-semantics.md  # EVM time-travel behavior
│   │
│   ├── Dashboard Guides
│   │   ├── dashboard-developer-guide.md   # Dashboard architecture for devs
│   │   ├── dashboard-user-guide.md        # Dashboard docs for users
│   │   ├── how-to-create-a-widget.md      # Widget creation tutorial
│   │   └── widget-lifecycle-walkthrough.md # Widget lifecycle explanation
│   │
│   └── AI Guides
│       └── ai-chat-developer-guide.md     # AI chat system architecture
│
├── backend/                      # Backend architecture
│   ├── coding-standards.md       # Python/FastAPI standards
│   ├── seed-data-strategy.md     # Seed data approach
│   ├── api/                      # Backend API docs
│   │   └── ai-tools.md           # AI tool development patterns
│   └── contexts/                 # Per-context backend docs
│       ├── evcs-core/            # EVCS (Entity Versioning Control System)
│       │   ├── architecture.md           # EVCS architecture overview
│       │   ├── entity-classification.md   # Versionable vs non-versionable
│       │   ├── evcs-implementation-guide.md # EVCS implementation patterns
│       │   └── code-locations.md          # Where EVCS code lives
│       ├── auth/                 # Authentication & authorization
│       │   └── architecture.md
│       ├── user-management/      # User domain
│       │   └── architecture.md
│       ├── branching/            # Branch context (change orders)
│       │   └── architecture.md
│       ├── progression/          # Progression context
│       │   └── architecture.md
│       └── project-management/   # Project management context
│           └── architecture.md
│
├── frontend/                     # Frontend architecture
│   ├── coding-standards.md       # React/TypeScript standards
│   ├── ui-patterns.md            # UI component patterns
│   ├── date-formatting-guide.md  # Date & temporal formatting
│   └── contexts/                 # Per-context frontend docs
│       ├── 01-core-architecture.md   # Frontend architecture overview
│       ├── 02-state-data.md          # State management patterns
│       ├── 03-ui-ux.md               # UI/UX guidelines
│       ├── 04-quality-testing.md     # Frontend testing
│       ├── 05-i18n.md                # Internationalization
│       └── 06-authentication.md      # Frontend auth patterns
│
├── cross-cutting/               # Cross-domain concerns
│   ├── api-conventions.md             # REST API patterns
│   ├── api-response-patterns.md       # API response standards
│   ├── automated-filter-types-migration.md # Filter types migration
│   ├── database-strategy.md           # PostgreSQL, migrations
│   ├── security-practices.md          # Auth, RBAC
│   └── temporal-query-reference.md    # Bitemporal query patterns
│
├── testing/                     # Testing documentation
│   ├── test-strategy-guide.md         # Testing philosophy & patterns
│   └── test-execution-runbook.md      # How to run tests
│
├── ai/                          # AI/Chat system documentation
│   ├── agent-orchestration-guide.md   # LangGraph agent patterns
│   ├── api-reference.md               # AI API reference
│   ├── project-context-patterns.md    # Project context injection
│   ├── temporal-context-patterns.md   # Temporal context in AI
│   ├── tool-development-guide.md      # AI tool development
│   └── troubleshooting.md             # AI system troubleshooting
│
├── decisions/                   # Architecture Decision Records (ADRs)
│   ├── adr-index.md                  # ADR index & template
│   ├── ADR-001-technology-stack.md
│   ├── ADR-003-command-pattern.md
│   ├── ADR-003-phase3e-session-context.md
│   ├── ADR-004-quality-standards.md
│   ├── ADR-005-bitemporal-versioning.md
│   ├── ADR-006-protocol-based-type-system.md
│   ├── ADR-007-rbac-service.md
│   ├── ADR-008-server-side-filtering.md
│   ├── ADR-009-schedule-baseline-1to1-relationship.md
│   ├── ADR-010-query-key-factory.md
│   ├── ADR-011-generic-evm-metric-system.md
│   ├── ADR-012-evm-time-series-data-strategy.md
│   ├── ADR-013-computed-budget-attribute.md
│   └── 009-langgraph-rewrite.md
│
├── decision-records/            # Legacy decision records
│   └── 004-test-coverage-strategy.md
│
└── archive/                     # Archived documentation
    ├── agent-library-alternatives-analysis.md
    ├── agent-library-compatibility-guide.md
    └── ai-tools-migration-guide.md
```

## Architecture Decision Records (ADRs)

Past technical decisions are recorded in [`decisions/`](decisions/).

| Topic | ADR |
| ----- | --- |
| Technology stack | [`ADR-001`](decisions/ADR-001-technology-stack.md) |
| Command pattern | [`ADR-003`](decisions/ADR-003-command-pattern.md) |
| Phase3E session context | [`ADR-003-phase3e`](decisions/ADR-003-phase3e-session-context.md) |
| Quality standards | [`ADR-004`](decisions/ADR-004-quality-standards.md) |
| Bitemporal versioning | [`ADR-005`](decisions/ADR-005-bitemporal-versioning.md) |
| Protocol-based type system | [`ADR-006`](decisions/ADR-006-protocol-based-type-system.md) |
| RBAC service | [`ADR-007`](decisions/ADR-007-rbac-service.md) |
| Server-side filtering | [`ADR-008`](decisions/ADR-008-server-side-filtering.md) |
| Schedule baseline 1:1 | [`ADR-009`](decisions/ADR-009-schedule-baseline-1to1-relationship.md) |
| Query key factory | [`ADR-010`](decisions/ADR-010-query-key-factory.md) |
| Generic EVM metrics | [`ADR-011`](decisions/ADR-011-generic-evm-metric-system.md) |
| EVM time-series data | [`ADR-012`](decisions/ADR-012-evm-time-series-data-strategy.md) |
| Computed budget attribute | [`ADR-013`](decisions/ADR-013-computed-budget-attribute.md) |
| LangGraph rewrite | [`009-langgraph`](decisions/009-langgraph-rewrite.md) |

For the full index, see [`decisions/adr-index.md`](decisions/adr-index.md).

## Key Concepts

- **EVCS** (Entity Versioning Control System): Git-style versioning for entities with bitemporal tracking. See [`backend/contexts/evcs-core/`](backend/contexts/evcs-core/)
- **Bounded Contexts**: Domain-driven design partitions. See [`01-bounded-contexts.md`](01-bounded-contexts.md)
- **Layered Architecture**: API → Services → Repositories → Models. See coding standards
- **TDD**: RED-GREEN-REFACTOR test-driven development enforced via PDCA process

## Reference Documentation

| Topic | File |
| ----- | ---- |
| API endpoints | [`api-endpoints.md`](api-endpoints.md) |
| Code review checklist | [`code-review-checklist.md`](code-review-checklist.md) |
| Error codes | [`error-codes.md`](error-codes.md) |
| Configuration | [`configuration.md`](configuration.md) |
| Migration troubleshooting | [`migration-troubleshooting.md`](migration-troubleshooting.md) |
| Testing patterns | [`testing-patterns.md`](testing-patterns.md) |
