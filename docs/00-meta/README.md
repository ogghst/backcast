# Backcast EVS Documentation

**Last Updated:** 2026-03-02
**Status:** Active Development - Sprint 2

## Quick Start

- **New to the project?** Start with [Onboarding Guide](onboarding.md) and [Vision](../01-product-scope/vision.md)
- **Need architecture overview?** Read [System Map](../02-architecture/00-system-map.md)
- **Working on current iteration?** Check [Sprint Backlog](../03-project-plan/sprint-backlog.md)
- **Looking for specific context?** See [Bounded Contexts](../02-architecture/01-bounded-contexts.md)
- **Maintaining documentation?** See [Documentation Ownership](DOCUMENTATION_OWNERSHIP.md)

## Philosophy

Our documentation follows a **bounded context** approach to minimize context rot. Instead of one massive architecture document, we separate concerns into focused, self-contained documents.

**Guiding Principles:**

1. **Clear Boundaries:** Product scope, architecture, and project tracking are separate
2. **Findability:** Use this guide to locate information quickly
3. **Staleness Indicators:** Each doc shows last-updated date
4. **Immutable Decisions:** ADRs capture decisions at a point in time
5. **Single Source of Truth:** Link to authoritative sources, don't duplicate

## Documentation Structure

This documentation follows a structure designed to minimize context rot through three clear pillars:

### Product Scope (The "What" and "Why")

[01-product-scope/](../01-product-scope/)

- Vision and business goals
- User stories and requirements
- Acceptance criteria templates

### Architecture (The "How")

[02-architecture/](../02-architecture/)

- System overview and bounded contexts
- Per-context documentation (auth, user-management, etc.)
- Cross-cutting concerns (database, API conventions, security)
- Architecture Decision Records (ADRs)
- Technical debt tracking

### Project Plan (The "When" and "Now")

[03-project-plan/](../03-project-plan/)

- Current iteration status
- Backlog and team capacity
- Historical PDCA iteration records

### PDCA Prompts (Process Automation)

[04-pdca-prompts/](../04-pdca-prompts/)

- Standardized prompts for AI collaboration
- Meta-prompt for iteration planning
- Plan/Do/Check/Act templates

## Documentation Maintenance

- **Before Each Iteration:** Update `sprint-backlog.md` with new plans
- **During Work:** Log decisions in `iterations/{YYYY-MM-DD}-{name}/02-do.md`
- **After Completion:** Record learnings in CHECK and ACT documents
- **Quarterly:** Full documentation audit (see `last-audit.md`)

## Writing Guidelines

### Document Title Format

```markdown
# Document Title

**Last Updated:** YYYY-MM-DD  
**Status:** Active | Deprecated | Superseded by [link]  
**Owner:** Team or role name
```

### Link to Code

Use file:// links for code references:

```markdown
See [`app/services/user.py`](file:///absolute/path/to/file.py)
```

### Keep It Concise

- One page per concern when possible
- Link to details rather than duplicating
- Use diagrams for complex relationships

### Date All Decisions

ADRs and significant changes must include dates to provide historical context.

---

## Documentation Debt

Like technical debt, documentation debt accumulates. Track it in:

- `02-architecture/technical-debt.md` (code-related)
- `00-meta/documentation-debt.md` (docs needing updates)

---

## Questions?

If you can't find what you need:

1. Check the [System Map](../02-architecture/00-system-map.md)
2. Search for keywords in all markdown files
3. Ask in team chat or create an issue

**Maintain this guide:** Update when you add new documentation patterns or structures.

## Recent Changes

See [changelog-architecture.md](changelog-architecture.md) for architectural evolution timeline.
