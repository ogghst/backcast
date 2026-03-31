# Architecture Documentation

Quick reference for finding architecture documents. Start here when working on the Backcast system.

## Quick Links by Common Task

| I need to... | Read this |
| ------------ | --------- |
| **Understand the system** | [`00-system-map.md`](00-system-map.md) - High-level overview |
| **Understand domain boundaries** | [`01-bounded-contexts.md`](01-bounded-contexts.md) - Context mapping |
| **Write backend code** | [`backend/coding-standards.md`](backend/coding-standards.md) - Type safety, patterns, quality gates |
| **Write frontend code** | [`frontend/coding-standards.md`](frontend/coding-standards.md) - React patterns, state management |
| **Work with EVCS/versioning** | [`backend/contexts/evcs-core/`](backend/contexts/evcs-core/) - Entity versioning framework |
| **Implement API endpoints** | [`cross-cutting/api-conventions.md`](cross-cutting/api-conventions.md) - REST patterns, RBAC |
| **Write database queries** | [`cross-cutting/database-strategy.md`](cross-cutting/database-strategy.md) - PostgreSQL, bitemporal |
| **Handle authentication** | [`cross-cutting/security-practices.md`](cross-cutting/security-practices.md) - JWT, RBAC |
| **Write tests** | [`testing/test-strategy-guide.md`](testing/test-strategy-guide.md) - Testing patterns |
| **Run tests** | [`testing/test-execution-runbook.md`](testing/test-execution-runbook.md) - How to execute tests |
| **Build EVM features** | [`evm-calculation-guide.md`](evm-calculation-guide.md) - Earned Value Management |
| **Build AI chat features** | [`ai-chat-developer-guide.md`](ai-chat-developer-guide.md) - AI chat architecture |

## Folder Structure

```
02-architecture/
├── 00-system-map.md              # System overview
├── 01-bounded-contexts.md        # Domain boundaries
├── backend/                      # Backend architecture
│   ├── coding-standards.md       # Python/FastAPI standards
│   └── contexts/                 # Per-context backend docs
│       ├── evcs-core/            # EVCS (Entity Versioning Control System)
│       ├── auth/                 # Authentication & authorization
│       └── user-management/      # User domain
├── frontend/                     # Frontend architecture
│   ├── coding-standards.md       # React/TypeScript standards
│   └── contexts/                 # Per-context frontend docs
├── cross-cutting/               # Cross-domain concerns
│   ├── api-conventions.md        # REST API patterns
│   ├── database-strategy.md      # PostgreSQL, migrations
│   ├── security-practices.md     # Auth, RBAC
│   └── temporal-query-reference.md # Bitemporal queries
├── testing/                     # Testing documentation
│   ├── test-strategy-guide.md    # Testing patterns
│   └── test-execution-runbook.md # How to run tests
├── decisions/                   # Architecture Decision Records (ADRs)
├── evm-*.md                     # EVM (Earned Value Management) guides
└── ai-*.md                      # AI/Chat feature docs
```

## Architecture Decision Records (ADRs)

Past technical decisions are recorded in [`decisions/`](decisions/). Key ADRs:

| Topic | ADR |
| ----- | --- |
| Technology stack | [`ADR-001`](decisions/ADR-001-technology-stack.md) |
| Bitemporal versioning | [`ADR-005`](decisions/ADR-005-bitemporal-versioning.md) |
| Command pattern | [`ADR-003`](decisions/ADR-003-command-pattern.md) |
| RBAC service | [`ADR-007`](decisions/ADR-007-rbac-service.md) |
| Server-side filtering | [`ADR-008`](decisions/ADR-008-server-side-filtering.md) |
| Quality standards | [`ADR-004`](decisions/ADR-004-quality-standards.md) |
| Test coverage strategy | [`decision-records/004-test-coverage-strategy.md`](decision-records/004-test-coverage-strategy.md) |

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
