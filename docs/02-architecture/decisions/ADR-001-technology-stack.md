# ADR-001: Technology Stack Selection

## Status
✅ Accepted (2025-12-27)

## Context

We needed to choose a technology stack for building the Backcast EVS backend, a Project Budget Management and EVM application with Git-style versioning capabilities. The system requires:

- High-performance API endpoints
- Async database operations
- Complex versioning logic with time-travel queries
- Type safety for large codebase maintainability
- Strong ORM with modern async support

## Decision

We chose the following stack:

- **Python 3.12+** as the runtime
- **FastAPI** as the web framework
- **SQLAlchemy 2.0** as the ORM
- **PostgreSQL 15+** as the database
- **Pydantic V2** for data validation
- **asyncpg** as the database driver

## Consequences

### Positive

- **FastAPI:** Native async support, automatic OpenAPI docs, excellent DX
- **SQLAlchemy 2.0:** Modern typed ORM with `Mapped[]` annotations, async-native
- **Python 3.12:** Latest type hinting features (`TypeAlias`, improved generics)
- **PostgreSQL:** Strong support for composite PKs, JSONB, recursive CTEs
- **Pydantic V2:** Rust-powered validation, 5-50x performance improvement
- **Ecosystem:** Large community, extensive libraries, mature testing tools

### Negative

- Python slower than compiled languages (acceptable for our use case)
- Async requires careful management of connection pools
- Learning curve for SQLAlchemy 2.0's new API style

## Alternatives Considered

### Alternative 1: Django + DRF
- **Pros:** Batteries-included, excellent admin panel, mature
- **Cons:** Heavier framework, Django ORM limited for complex versioning, less async-native
- **Rejected:** Too opinionated, ORM limitations for our versioning needs

### Alternative 2: FastAPI + Django ORM
- **Pros:** FastAPI performance, Django ORM familiarity
- **Cons:** Awkward integration, Django ORM not async-native
- **Rejected:** Poor async support in Django ORM

### Alternative 3: Node.js + TypeScript
- **Pros:** True async, TypeScript type safety, fast runtime
- **Cons:** Team less experienced, weaker type system than Python 3.12+
- **Rejected:** Team expertise in Python, MyPy strict mode comparable to TypeScript

## Notes

This decision established the foundation for all subsequent architecture choices. The emphasis on async performance and type safety has proven valuable as the codebase grows.

**Review Date:** 2026-01-01 (reassess after 1 year of production use)
