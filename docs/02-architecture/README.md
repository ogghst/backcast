# Architecture Docs - AI Agent Navigation Guide

Quick reference for AI agents to find relevant architecture documents.

## By Task Type

| I need to...                        | Read this file                                                                                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Understand the overall system       | [`00-system-map.md`](00-system-map.md)                                                                                                                  |
| Understand domain boundaries        | [`01-bounded-contexts.md`](01-bounded-contexts.md)                                                                                                      |
| Write code (backend or frontend)    | [`coding-standards.md`](coding-standards.md) - Core principles, type safety, patterns, quality gates                                                    |
| Work with versioning/branching      | [`backend/contexts/evcs-core/`](backend/contexts/evcs-core/)                                                                                            |
| Implement API endpoints             | [`cross-cutting/api-conventions.md`](cross-cutting/api-conventions.md)                                                                                  |
| Write database queries              | [`cross-cutting/database-strategy.md`](cross-cutting/database-strategy.md)                                                                              |
| Handle authentication/authorization | [`cross-cutting/security-practices.md`](cross-cutting/security-practices.md) + [`decisions/ADR-007-rbac-service.md`](decisions/ADR-007-rbac-service.md) |
| Understand a design decision        | [`decisions/adr-index.md`](decisions/adr-index.md)                                                                                                      |
| Implement feature X                 | Look in `backend/contexts/x-*/` or `frontend/contexts/`                                                                                                 |
| Understand technical debt           | [`02-technical-debt.md`](02-technical-debt.md)                                                                                                          |

## Folder Structure

```
02-architecture/
├── 00-system-map.md           # High-level architecture overview
├── 01-bounded-contexts.md     # Domain boundaries and context mapping
├── 02-technical-debt.md          # Technical debt tracking
├── backend/
│   └── contexts/              # Per-context backend architecture
├── frontend/
│   └── contexts/              # Per-context frontend architecture
├── cross-cutting/             # Cross-domain concerns (API, DB, security)
└── decisions/                 # Architecture Decision Records (ADRs)
```

## Key Concepts

- **EVCS**: Entity Versioning Control System - see [`backend/contexts/evcs-core/`](backend/contexts/evcs-core/)
- **Bitemporal Versioning**: See [`decisions/ADR-005-bitemporal-versioning.md`](decisions/ADR-005-bitemporal-versioning.md)
- **Command Pattern**: See [`decisions/ADR-003-command-pattern.md`](decisions/ADR-003-command-pattern.md)
- **RBAC**: See [`decisions/ADR-007-rbac-service.md`](decisions/ADR-007-rbac-service.md)
