# PDCA Prompt References

**Purpose:** Centralized documentation links for all PDCA phases. Read relevant sections before starting each phase.

**Navigation Strategy:** READMEs for directories (discovery), specific files for core stable docs (direct access).

---

## Core Documentation (Always Read)

| Document                      | Purpose                    | Path                                                |
| ----------------------------- | -------------------------- | --------------------------------------------------- |
| **Frontend Coding Standards** | Quality gates, type safety | `docs/02-architecture/frontend/coding-standards.md` |
| **Backend Coding Standards**  | Quality gates, type safety | `docs/02-architecture/backend/coding-standards.md`  |
| **System Map**                | Architecture overview      | `docs/02-architecture/00-system-map.md`             |

---

## Phase-Specific References

### Analysis Phase

| Document           | When to Read              | Path                                               |
| ------------------ | ------------------------- | -------------------------------------------------- |
| Product Scope      | Requirements overview     | `docs/01-product-scope/README.md`                  |
| Vision             | Business goals (core doc) | `docs/01-product-scope/vision.md`                  |
| Bounded Contexts   | System boundaries         | `docs/02-architecture/01-bounded-contexts.md`      |
| Architecture Index | Patterns & decisions      | `docs/02-architecture/README.md`                   |
| Temporal Query     | Access as-of data         | `docs/02-architecture/temporal-query-reference.md` |

### Plan Phase

| Document         | When to Read            | Path                                        |
| ---------------- | ----------------------- | ------------------------------------------- |
| ADR Index        | Architectural decisions | `docs/02-architecture/decisions/README.md`  |
| Test Fixtures    | Available test setup    | `backend/tests/conftest.py`                 |
| Technical Debt   | Existing debt items     | `docs/02-architecture/02-technical-debt.md` |
| Current Analysis | Analysis                | Current iteration's `01-analysis.md`        |

### Do Phase

| Document                  | When to Read           | Path                                                |
| ------------------------- | ---------------------- | --------------------------------------------------- |
| Frontend Coding Standards | Implementation quality | `docs/02-architecture/frontend/coding-standards.md` |
| Backend Coding Standards  | Implementation quality | `docs/02-architecture/backend/coding-standards.md`  |
| Architecture Index        | Patterns & decisions   | `docs/02-architecture/README.md`                    |
| Current Plan              | Task specifications    | Current iteration's `01-plan.md`                    |

### Check Phase

| Document       | When to Read         | Path                                        |
| -------------- | -------------------- | ------------------------------------------- |
| Plan Criteria  | Verification targets | Current iteration's `01-plan.md`            |
| Technical Debt | Log new items        | `docs/02-architecture/02-technical-debt.md` |

### Act Phase

| Document                  | When to Read             | Path                                                |
| ------------------------- | ------------------------ | --------------------------------------------------- |
| Cross-Cutting Index       | Pattern documentation    | `docs/02-architecture/cross-cutting/`               |
| Frontend Coding Standards | Update with new patterns | `docs/02-architecture/frontend/coding-standards.md` |
| Backend Coding Standards  | Update with new patterns | `docs/02-architecture/backend/coding-standards.md`  |
| Project Plan              | Update backlog           | `docs/03-project-plan/README.md`                    |

---

## Code Pattern References

### Backend Patterns

| Pattern            | Example Location                         |
| ------------------ | ---------------------------------------- |
| Branchable Service | `backend/app/services/wbe_service.py`    |
| Simple Service     | `backend/app/services/user_service.py`   |
| Repository Pattern | `backend/app/repositories/`              |
| Command Pattern    | `backend/app/core/branching/commands.py` |
| Unit Tests         | `backend/tests/unit/services/`           |
| Integration Tests  | `backend/tests/integration/`             |

### Frontend Patterns

| Pattern         | Example Location                  |
| --------------- | --------------------------------- |
| Feature Module  | `frontend/src/features/projects/` |
| CRUD Hook       | `frontend/src/hooks/useCrud.ts`   |
| API Service     | `frontend/src/api/`               |
| Component Tests | `frontend/src/**/*.test.tsx`      |

---

## Quality Gates

### Backend

```bash
# Must pass before CHECK phase
uv run mypy app --strict          # Type checking
uv run ruff check .               # Linting
uv run pytest --cov=app           # Tests + coverage (≥80%)
```

### Frontend

```bash
# Must pass before CHECK phase
npm run lint                      # ESLint
npm run typecheck                 # TypeScript strict
npm run test -- --coverage        # Tests + coverage (≥80%)
```

---

## Output File Locations

All iteration outputs go to:

```
docs/03-project-plan/iterations/YYYY-MM-DD-{title}/
├── 00-analysis.md    # Analysis phase output
├── 01-plan.md        # Plan phase output
├── 02-do.md          # Do phase log
├── 03-check.md       # Check phase output
└── 04-act.md         # Act phase output
```

**Naming Convention:** `YYYY-MM-DD-{kebab-case-title}` (e.g., `2026-01-15-budget-tracking`)
