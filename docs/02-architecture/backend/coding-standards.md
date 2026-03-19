# Backend Coding Standards (Python/FastAPI)

**Scope:** Backend, Database, EVCS Core

---

## Type Safety (Non-Negotiable)

- **MyPy strict mode** with `disallow_any_explicit = True`
- Never use `Any` - always define explicit types
- Use `Mapped[]` for SQLAlchemy columns
- Use `typing.Annotated` for dependency injection

---

## Docstring Standard (LLM-Optimized)

**All public functions MUST have docstrings that explain intent and context.**

```python
async def calculate_earned_value(
    project_id: UUID,
    as_of: datetime,
    branch: str = "main",
) -> Decimal:
    """Calculate earned value for a project at a point in time.

    Context: Part of EVM calculations. Used by reporting and dashboard.

    Args:
        project_id: Project to calculate EV for
        as_of: Timestamp for time-travel query (bitemporal)
        branch: Version control branch (default: main)

    Returns:
        Earned value as Decimal (sum of completed work * planned rates)

    Raises:
        ValueError: Project not found or no valid data at as_of
    """
```

**Required elements:**

1. **One-line summary** - what it does
2. **Context** - why it exists, what calls it
3. **Args** - with business meaning, not just types
4. **Returns** - what the value represents
5. **Raises** - when and why

---

## Architecture Patterns

### Service Layer

- Services orchestrate business logic
- Raise `ValueError` for business errors (routes convert to `HTTPException`)
- Always pass `actor_id` for audit trail

### EVCS (Entity Version Control)

- **Bitemporal:** Track `valid_time` and `transaction_time`
- **Immutable:** Append-only, never overwrite
- **Branched:** Support branch isolation

**ADRs:** [Bitemporal](../decisions/ADR-005-bitemporal-versioning.md), [Command Pattern](../decisions/ADR-003-command-pattern.md)

#### Foreign Key Constraints for Temporal Entities

**Pattern:** Temporal entities (using `VersionableMixin`) should **NOT** use database-level FK constraints to other temporal entities' root IDs (e.g., `project_id`, `user_id`, `wbe_id`).

**Rationale:**
- Root IDs are **NOT UNIQUE** in bitemporal tables (multiple versions share the same root ID)
- PostgreSQL FK constraints require UNIQUE target columns
- Referential integrity must be enforced at the **application/service layer**

**Implementation:**
- Use explicit comments: `# NOTE: No database-level ForeignKey constraint because [field] is a root ID`
- Service layer validates existence before setting FK fields
- When FK is unavoidable (e.g., to non-temporal entities like `users.user_id`), document the decision

**Examples:**
```python
# Correct - Bitemporal to Bitemporal (no FK)
project_id: Mapped[UUID] = mapped_column(
    PG_UUID, nullable=False, index=True
)
# NOTE: No database-level ForeignKey constraint because project_id is a root ID.
# Referential integrity enforced at service layer.

# Correct - Bitemporal to non-temporal Business Key (FK allowed)
assigned_approver_id: Mapped[UUID | None] = mapped_column(
    PG_UUID, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
)
```

---

## API Routes

```python
@router.post("", response_model=ProjectPublic, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> Project:
    """Create a new project.

    Context: Entry point for project creation. Validates via Pydantic.
    """
    return await service.create_project(project_in, current_user.user_id)
```

- Use `PaginatedResponse` for list endpoints
- Use `FilterParser` with whitelisted fields
- Never concatenate raw SQL

---

## Common Pitfalls

| Issue           | Wrong                            | Right                                               |
| --------------- | -------------------------------- | --------------------------------------------------- |
| Expired objects | `wbe.wbe_id` after flush         | Capture ID immediately after creation               |
| Empty ranges    | `datetime.now()` called twice    | Generate timestamp once, reuse                      |
| Raw dicts       | `return results.scalars().all()` | Return `[Model.model_validate(r) for r in results]` |
| Naming          | `projectId`                      | `project_id` (snake_case)                           |

---

## Quality Gates

```bash
ruff check app tests --fix  # Linting
mypy app --strict           # Type check
pytest --cov=app            # Tests (≥80% coverage)
```
