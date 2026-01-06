# Team Capacity

**Last Updated:** 2025-12-29  
**Review Frequency:** Monthly or when team changes

---

## Current Team Composition

### Core Team

**Backend Developer** (1 FTE)

- **Name:** Primary Developer
- **Role:** Full-stack backend development
- **Availability:** 40 hours/week
- **Skills:** Project Management, Task Priorization, System design, Object Oriented programming, Python, FastAPI, SQLAlchemy, PostgreSQL, async patterns
- **Focus Areas:** All features, architecture, quality

**AI Assistant** (Paired)

- **Role:** Pair programming, code generation, quality automation
- **Availability:** On-demand
- **Strengths:** Code generation, test creation, documentation, pattern application
- **Limitations:** Requires human review, context management

---

## Sprint Capacity

**2-Week Sprint:**

- **Available Hours:** ~80 hours (40 hours/week × 2 weeks)
- **Effective Development Hours:** ~60 hours (accounting for meetings, overhead)
- **Story Point Capacity:** 20-25 points per sprint

---

## Velocity History

| Sprint     | Points | Dates               | Status | Notes                              |
| ---------- | ------ | ------------------- | ------ | ---------------------------------- |
| Sprint 1   | 21     | 2025-12-20 to 27    | ✅     | Infrastructure setup                |
| Sprint 2   | 23     | 2025-12-27 to 01-05 | ✅     | User management, Epic 4 foundation  |
| Hybrid 2/3 | TBD    | 2026-01-05 to 06    | 🔄     | Project/WBE cleanup, audit gap fix  |

**Average Velocity:** 22.0 points
**Velocity Trend:** ➡️ Stable

**See [velocity-tracking.md](./velocity-tracking.md) for detailed metrics and forecasting.**

---

## Skills Matrix

| Skill Area         | Proficiency  | Notes                                       |
| ------------------ | ------------ | ------------------------------------------- |
| **Python 3.12+**   | Expert       | Type hints, async/await, generics           |
| **FastAPI**        | Advanced     | Dependency injection, async routes, OpenAPI |
| **SQLAlchemy 2.0** | Advanced     | Async ORM, Mapped types, migrations         |
| **PostgreSQL**     | Intermediate | Complex queries, indexing, JSONB            |
| **Testing**        | Advanced     | pytest, fixtures, async tests, coverage     |
| **Type Safety**    | Advanced     | MyPy strict mode, Protocols, generics       |
| **Git/GitHub**     | Advanced     | Branching, PR workflows, CI/CD              |
| **Docker**         | Intermediate | Containerization, docker-compose            |

**Growth Areas:**

- Advanced PostgreSQL optimization
- Performance profiling and tuning
- Load testing at scale

---

## Constraints

**Technical:**

- Development on local machine (Ubuntu 24.04)
- Database: PostgreSQL via Docker
- No cloud infrastructure provisioned yet

**Process:**

- Solo developer (no pair programming with other humans)
- All work reviewed via AI assistant
- Quality gates enforced via CI/CD

**Dependencies:**

- None external currently
- Self-contained backend development

---

## Capacity Planning Guidelines

**Story Point Estimates Based on Capacity:**

| Points | Effort   | Feasible in Sprint?        |
| ------ | -------- | -------------------------- |
| 1-3    | < 1 day  | Yes, multiple stories      |
| 5      | 1-2 days | Yes, 4-5 per sprint        |
| 8      | 2-4 days | Yes, 2-3 per sprint        |
| 13     | 4-6 days | Yes, 1-2 per sprint        |
| 21+    | > 1 week | Split into smaller stories |

**Risk Factors:**

- Unexpected complexity (buffer 10-15%)
- Learning curve for new patterns (first implementation -20%)
- Technical debt paydown (add 20-30% to estimates)

---

**Use During PLAN Phase:**
Reality-check iteration scope against available capacity before committing to work.
