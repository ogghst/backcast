# Code Review Checklist

**Last Updated:** 2026-01-08

---

## 1. Core Implementation

- [ ] Does the code solve the problem described in the user request?
- [ ] Are edge cases handled (e.g., empty lists, null values, invalid IDs)?
- [ ] Is there any unnecessary complexity or over-engineering?
- [ ] Is the logic correct and free of obvious bugs?

## 2. Type Safety & Standards

- [ ] **Backend**: 100% type hint coverage (no `Any`)?
- [ ] **Backend**: Pydantic models used correctly?
- [ ] **Frontend**: 100% type safety?
- [ ] **Common**: No `Any` or `any` used?
- [ ] **Standards**: Does the code follow [Coding Standards](coding-standards.md)?

## 3. API & Data Patterns

- [ ] **Filtering**: Is [FilterParser](cross-cutting/api-response-patterns.md) used for list endpoints?
- [ ] **Security**: Are filter fields whitelisted?
- [ ] **Pagination**: Is `PaginatedResponse` used where appropriate?
- [ ] **Response Unwrapping**: Does the frontend correctly handle paginated responses?
- [ ] **SQL**: No raw SQL concatenation? (SQLAlchemy ORM/Expression language used)

## 4. Testing

- [ ] Are there unit tests for the new logic?
- [ ] Are critical paths (versioning, EVM) covered 100%?
- [ ] Do all tests pass?
- [ ] Is test isolation maintained?

## 5. Documentation & Metadata

- [ ] Are public functions/classes documented (Google-style)?
- [ ] Has an ADR been created for significant architecture decisions?
- [ ] Is the [Sprint Backlog](../03-project-plan/sprint-backlog.md) updated?
- [ ] Are [Technical Debt](../03-project-plan/technical-debt/) items documented?

## 6. Performance & Scalability

- [ ] Are database indexes added for frequently filtered/searched columns?
- [ ] Are N+1 query problems avoided (e.g., using `selectinload` or `joinedload`)?
- [ ] Is server-side processing used instead of client-side for large datasets?

---

**Note:** AI Agents should use this checklist to verify their own work before asking for user review.
