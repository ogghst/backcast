# Documentation Ownership & Maintenance

**Last Updated:** 2026-03-02
**Status:** Active

This document establishes the maintenance schedule and review tracking for Backcast EVS documentation.

---

## Team Structure

| Role | Responsibility |
|------|----------------|
| **Human Architect** | Strategic decisions, ADR approval, business requirements |
| **AI Agent Team** | Implementation, documentation updates, consistency checks |

---

## Update Triggers

Documentation MUST be updated when:

### Code Changes
1. **New Entity Created** → Update `01-bounded-contexts.md`, `glossary.md`
2. **New API Endpoint** → Update `api-endpoints.md`
3. **New Error Code** → Update `error-codes.md`
4. **New Configuration Option** → Update `configuration.md`
5. **New Frontend Feature** → Update `frontend-features.md`

### Architecture Changes
1. **New ADR Created** → Link from relevant bounded context
2. **Database Schema Change** → Update `database-strategy.md`
3. **API Pattern Change** → Update `api-conventions.md`
4. **Temporal Query Change** → Update `temporal-query-reference.md`

### Business Changes
1. **New Workflow** → Update `functional-requirements.md`
2. **New EVM Metric** → Update `evm-requirements.md`, `glossary.md`
3. **New User Story** → Update `functional-requirements.md`

---

## Review Schedule

| Frequency | Scope | Command |
|-----------|-------|---------|
| **Per Iteration** | Docs touched by changes | Automatic with `/pm update` |
| **Monthly** | Full documentation audit | `/pm doc-review` |
| **Quarterly** | ADRs and architecture docs | `/pm doc-review --quarterly` |

---

## Review History

| Date | Scope | Reviewer | Notes |
|------|-------|----------|-------|
| 2026-03-02 | Full audit | AI Agent | Initial consistency review; fixed duplications, created missing docs |

---

## Documentation Quality Checklist

Before marking any document as complete:

### Content Quality
- [ ] Single source of truth identified
- [ ] Links to authoritative sources instead of duplicating
- [ ] No conflicting information with other documents
- [ ] Consistent terminology (see `glossary.md`)

### Structure
- [ ] Clear purpose statement
- [ ] Last Updated date present
- [ ] Related documents linked

### Navigation
- [ ] Listed in parent directory README
- [ ] Cross-referenced from related docs

---

## Duplication Prevention Rules

### Rule 1: Link, Don't Copy
When a topic is covered in another document:
- ✅ **DO:** Add a link with brief context
- ❌ **DON'T:** Copy the content

Example:
```markdown
> **For EVM formulas**, see the authoritative source: [EVM Requirements](../01-product-scope/evm-requirements.md)
```

### Rule 2: One Document, One Purpose
| Document Type | Content | NOT Content |
|---------------|---------|-------------|
| Product Scope | WHAT and WHY | HOW (implementation) |
| Architecture | HOW | WHY (business rationale) |
| User Guide | How to use | Implementation details |

### Rule 3: Authoritative Sources
| Topic | Authoritative Source | Documents that LINK |
|-------|---------------------|-------------------|
| EVM Formulas | `evm-requirements.md` | `glossary.md`, `evm-*.md` |
| API Parameters | `api-conventions.md` | `evm-api-guide.md`, endpoint docs |
| Temporal Queries | `temporal-query-reference.md` | `database-strategy.md`, ADR-005 |
| Change Workflow | `change-management-user-stories.md` | `functional-requirements.md` |
| Budget Allocation | `ADR-013` | `evm-requirements.md`, `01-bounded-contexts.md` |

---

## Related Documentation

- [Documentation Guide](./README.md) - How to write documentation
- [Glossary](../01-product-scope/glossary.md) - Terminology standards
- [ADR Index](../02-architecture/decisions/adr-index.md) - Architecture decisions
