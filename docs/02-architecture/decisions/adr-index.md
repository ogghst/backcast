# ADR Index

**Last Updated:** 2026-01-02

## Creating New ADRs

### Template

Use this structure for new ADRs:

```markdown
# ADR-NNN: [Title]

## Status

[Proposed | Accepted | Superseded by ADR-XXX | Deprecated]

## Context

What is the issue we're facing that motivates this decision?

## Decision

What decision did we make?

## Consequences

What are the positive and negative consequences of this decision?

## Alternatives Considered

What other options were evaluated?

## Notes

Additional information, links, or future review dates
```

### Numbering

- Sequential: ADR-001, ADR-002, ADR-003...
- Never reuse numbers
- Gaps okay if ADRs deleted before acceptance

### Process

1. Draft ADR with "Proposed" status
2. Review with team
3. Update status to "Accepted" when consensus reached
4. Link from this index
