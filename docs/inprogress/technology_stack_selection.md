# Technology Stack Selection: EVM Project Budget Management System

**Document:** DOC-004  
**Status:** ✅ Complete  
**Date:** 2024-12-19  
**Approved By:** TBD

---

## Executive Summary

This document provides the rationale and justification for technology stack selection for the EVM Project Budget Management System MVP. The recommended stack balances rapid development, maintainability, performance, and alignment with project requirements for complex financial calculations and reporting.

**Recommended Technology Stack:**
- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React 18+ with TypeScript
- **Database:** SQLite (initial MVP), PostgreSQL (production migration path)
- **ORM:** SQLAlchemy 2.0+
- **Authentication:** JWT with FastAPI-Users or similar
- **Testing:** pytest, Jest, React Testing Library
- **DevOps:** Docker, Docker Compose, GitHub Actions

---

## 1. Decision Criteria

### 1.1 Business Requirements

The system must:
- Support ~50 concurrent projects with complex hierarchies
- Generate EVM reports quickly on large datasets
- Be web-based, no client installation
- Scale to thousands of cost registrations
- Render reports under 5s

### 1.2 Technical Requirements

- Python backend
- Responsive UI
- PostgreSQL database
- REST API
- CI/CD
- Documentation and testing

### 1.3 Team Constraints

- 12-week MVP
- 2 full-stack developers
- Python expertise preferred
- Modern best practices

---

## 2. Backend Framework Selection

### 2.1 Options

#### **Option A: FastAPI** (RECOMMENDED)

**Pros:**
- High performance: async, fastest Python frameworks
- Type-safe: Pydantic, editor checks
- Auto-docs: OpenAPI/Swagger
- Production-ready ASGI
- Aligns with a 12-week MVP
- Maintainable, reliable, extensible

**Cons:**
- Smaller ecosystem than Django
- Fewer admin conveniences
- More explicit dependency wiring

**Complexity:** Low–medium  
**Risk:** Low  
**Learning curve:** Low  

---

#### **Option B: Django**

**Pros:**
- Mature ecosystem
- Admin UI
- Wide adoption
- Strong security defaults

**Cons:**
- Higher framework overhead
- More coupling
- Slower for compute-heavy APIs

**Complexity:** Medium  
**Risk:** Low  
**Learning curve:** Medium  

---

#### **Option C: Flask**

**Pros:**
- Minimal and flexible
- Easy to start

**Cons:**
- Less scaffolding
- Fewer reusable components
- Slower under load

**Complexity:** Medium–high  
**Risk:** Medium  
**Learning curve:** Low–medium  

---

### 2.2 Recommendation: FastAPI

Best fit for a fast, type-safe Python backend with complex calculations, fast dashboards, and clean APIs.

---

## 3. Frontend Framework Selection

### 3.1 Options

#### **Option A: React** (RECOMMENDED)

**Pros:**
- Strong ecosystem (React Query, Recharts, React Table, etc.)
- Wide adoption
- Component reuse
- Solid tooling
- Rich charting libraries

**Cons:**
- Some upfront complexity
- Choice overload
- Bundle size considerations

**Complexity:** Medium  
**Risk:** Low  
**Learning curve:** Medium  

---

#### **Option B: Vue**

**Pros:**
- Simpler learning curve
- Built-in reactivity

**Cons:**
- Smaller charting ecosystem
- Fewer enterprise examples
- Smaller community

**Complexity:** Medium  
**Risk:** Medium  
**Learning curve:** Low–medium  

---

### 3.2 Recommendation: React

Best fit for dashboards, large community, wide tooling, and team familiarity.

---

## 4. Database Selection

### 4.1 Recommendation: SQLite for MVP, PostgreSQL for Production

**For Initial MVP (SQLite):**
- Zero configuration — no separate server
- Portable, single-file
- ACID transactions
- Suitable for ~50 concurrent projects
- Embedded in Python

**For Production Migration (PostgreSQL):**
- High concurrency and scaling
- Advanced features (JSON, windowing, FTS)
- Rich indexing for hierarchies
- SQLAlchemy eases migration

**Migration Path:**
- Start with SQLite
- Schema via SQLAlchemy + Alembic
- Tested migration path to PostgreSQL
- No ORM changes required

---

## 5. Supporting Technology Stack

### 5.1 Backend Components

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Web Framework** | FastAPI | 0.109+ | Fast, type-safe APIs |
| **Python Version** | Python | 3.11+ | Features and speed |
| **ORM** | SQLAlchemy | 2.0+ | SQL-first ORM |
| **Database Migrations** | Alembic | 2.13+ | SQLAlchemy migrations |
| **API Documentation** | OpenAPI/Swagger | Auto-generated | FastAPI integration |
| **Async HTTP Client** | httpx | 0.26+ | Async testing |
| **Validation** | Pydantic | 2.6+ | Type-safe schemas |
| **Authentication** | JWT + FastAPI-Users | Latest | RBAC, JWT |
| **Testing Framework** | pytest | 8.0+ | Standard for Python |
| **API Testing** | pytest-asyncio | 0.23+ | Async endpoint tests |
| **Mocking** | pytest-mock | 3.14+ | Unit mocks |
| **Coverage** | pytest-cov | 5.0+ | Coverage |
| **Code Quality** | Black, Ruff, mypy | Latest | Linting, types |
| **Environment Management** | pydantic-settings | 2.2+ | Config |

---

### 5.2 Frontend Components

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Framework** | React | 18.3+ | Component-based UI |
| **Language** | TypeScript | 5.3+ | Type safety |
| **Bundler** | Vite | 5.0+ | Fast build and HMR |
| **Routing** | React Router | 6.22+ | Client-side routing |
| **State Management** | Zustand / TanStack Query | Latest | Simple global state / server state |
| **API Client** | axios / fetch | Latest | REST calls |
| **Forms** | React Hook Form | 7.50+ | Form validation |
| **Validation** | Zod | 3.23+ | Schema validation |
| **UI Library** | Material-UI (MUI) / shadcn/ui | Latest | Production components |
| **Charts** | Recharts | 2.12+ | EVM visualizations |
| **Data Grid** | TanStack Table | 8.15+ | Reports |
| **Date Handling** | date-fns | 3.3+ | Dates |
| **Testing Framework** | Jest | 29.7+ | Unit tests |
| **Component Testing** | React Testing Library | 14.1+ | Component tests |
| **E2E Testing** | Playwright | 1.42+ | E2E flows |
| **Code Quality** | ESLint, Prettier | Latest | Linting, formatting |
| **Type Checking** | TypeScript | 5.3+ | Types |

---

### 5.3 Infrastructure & DevOps

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Containerization** | Docker | 24.0+ | Environments |
| **Container Orchestration** | Docker Compose | 2.24+ | Local multi-container (optional for MVP) |
| **CI/CD** | GitHub Actions | Latest | Automation |
| **Database Client** | DB Browser for SQLite / DBeaver | Latest | DB management |
| **API Testing** | Postman / Insomnia | Latest | REST testing |
| **Version Control** | Git | Latest | VCS |
| **Code Repository** | GitHub | Latest | Hosting |
| **Documentation** | MkDocs / Sphinx | Latest | Docs |
| **Logging** | Python logging / structlog | Latest | Structured logs |
| **Monitoring** | Prometheus + Grafana (future) | Latest | Monitoring |

---

## 6. Architecture Overview

### 6.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Browser (Chrome/Edge/Safari)        │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              React SPA (TypeScript)                    │  │
│  │  - Project Management UI                               │  │
│  │  - EVM Dashboards & Reports                            │  │
│  │  - Data Entry Forms                                    │  │
│  └──────────────────┬────────────────────────────────────┘  │
└───────────────────────┼───────────────────────────────────────┘
                        │ HTTPS/REST API
┌───────────────────────┼───────────────────────────────────────┐
│                       ▼                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            FastAPI Backend (Python)                    │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  API Layer (REST Endpoints)                      │  │  │
│  │  ├─────────────────────────────────────────────────┤  │  │
│  │  │  Business Logic Layer                            │  │  │
│  │  │  - EVM Calculations                              │  │  │
│  │  │  - Budget Reconciliation                         │  │  │
│  │  │  - Report Generation                             │  │  │
│  │  ├─────────────────────────────────────────────────┤  │  │
│  │  │  Data Access Layer (SQLAlchemy ORM)              │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └──────────────────┬────────────────────────────────────┘  │
└───────────────────────┼───────────────────────────────────────┘
                        │
┌───────────────────────┼───────────────────────────────────────┐
│                       ▼                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │       SQLite Database (MVP) / PostgreSQL (Prod)       │  │
│  │  - Project/WBE/Cost Element Data                      │  │
│  │  - Transactions & Audit Logs                          │  │
│  │  - Calculated Metrics (optional materialized views)    │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

### 6.2 Layered Architecture

- API: REST, request validation, auth, error handling
- Business Logic: EVM, budget reconciliation, baselines
- Data Access: SQLAlchemy, migrations, rollups
- Database: PostgreSQL (schema, indexes, constraints)

Separation of concerns supports testing, scalability, and maintenance.

---

## 7. Development Approach

### 7.1 Project Structure

```
E80_pm_mockup/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes and endpoints
│   │   ├── core/             # Configuration, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── repositories/     # Data access layer
│   │   ├── calculations/     # EVM calculation engine
│   │   └── main.py           # FastAPI application
│   ├── tests/                # pytest test suite
│   ├── alembic/              # Database migrations
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API client functions
│   │   ├── store/            # State management
│   │   ├── types/            # TypeScript types
│   │   ├── utils/            # Helper functions
│   │   └── App.tsx           # Main App component
│   ├── public/               # Static assets
│   ├── tests/                # Jest test suite
│   ├── package.json          # Node dependencies
│   └── Dockerfile
├── docs/                     # Project documentation
├── docker-compose.yml        # Local development environment
└── README.md
```

---

### 7.2 Development Workflow

1. Environment: Docker Compose for local development
2. API-first: define contracts
3. TDD: unit → integration → E2E
4. Version control: Git, small commits
5. Code reviews: all PRs reviewed
6. CI/CD: automated tests, lint, type checks
7. Documentation: updating as you go

---

## 8. Risk Assessment

### 8.1 Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| FastAPI learning curve | Medium | Low | Solid docs, active community |
| React complexity | Medium | Low | Existing experience |
| EVM accuracy | High | Medium | Early spikes, manual checks |
| PostgreSQL performance | Medium | Low | Indexing plan, benchmarks |
| Integration | Medium | Medium | E2E coverage |
| Scope creep | High | Medium | Clear MVP scope |

### 8.2 Risk Mitigation

1. FastAPI: small API → build patterns
2. React: component-based, UI libraries
3. EVM: isolated tests, manual reviews
4. Performance: indexes, queries, caching if needed
5. Integration: E2E tests, CI/CD

---

## 9. Success Criteria

Stack is successful if:
- MVP shipped in 12 weeks
- Reports < 5s for large datasets
- Tests > 80% coverage
- Type safety where possible
- Onboarding in days, not weeks
- Deployment is straightforward

---

## 10. Alternative Considered

### Django (not selected)
Better fit if admin UI was critical. For an API-first, calculation-heavy MVP, FastAPI is better aligned.

---

## 11. Next Steps

1. Create project structure
2. FastAPI skeleton
3. SQLite database schema and migrations (Alembic)
4. React SPA with routing
5. Docker Compose (optional for MVP, SQLite simplifies local dev)
6. CI/CD
7. Begin Sprint 1

---

## Appendix A: Technology Comparison Matrix

| Criteria | FastAPI | Django | Flask |
|----------|---------|--------|-------|
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Type Safety | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Auto Documentation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| Learning Curve | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Ecosystem | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Async Support | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| MVP Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| API-First Design | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Appendix B: References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [EVM Guidelines](https://www.pmi.org/learning/library/earned-value-management-project-success-11022)

---

**Document Owner:** Development Team  
**Review Date:** Before Sprint 1 Implementation  
**Approval Required:** Yes, before proceeding to DOC-005
