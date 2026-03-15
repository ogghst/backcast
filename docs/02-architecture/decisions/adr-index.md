# ADR Index

**Last Updated:** 2026-01-23

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

---

## Active ADRs

| ID                                                        | Title                                        | Status   | Date       |
| --------------------------------------------------------- | -------------------------------------------- | -------- | ---------- |
| [ADR-001](ADR-001-technology-stack.md)                    | Technology Stack                             | Accepted | 2026-01-01 |
| [ADR-003](ADR-003-command-pattern.md)                     | Command Pattern                              | Accepted | 2026-01-02 |
| [ADR-004](ADR-004-quality-standards.md)                   | Quality Standards                            | Accepted | 2026-01-02 |
| [ADR-005](ADR-005-bitemporal-versioning.md)               | Bitemporal Versioning                        | Accepted | 2026-01-03 |
| [ADR-006](ADR-006-protocol-based-type-system.md)          | Protocol-based Type System                   | Accepted | 2026-01-04 |
| [ADR-007](ADR-007-rbac-service.md)                        | RBAC Service                                 | Accepted | 2026-01-05 |
| [ADR-008](ADR-008-server-side-filtering.md)               | Server-Side Filtering, Search, and Sorting   | Accepted | 2026-01-08 |
| [ADR-009](ADR-009-schedule-baseline-1to1-relationship.md) | Schedule Baseline 1:1 Relationship Inversion | Rejected | 2026-01-18 |
| [ADR-010](ADR-010-query-key-factory.md)                   | Query Key Factory                            | Accepted | 2026-01-19 |
| [ADR-011](ADR-011-generic-evm-metric-system.md)          | Generic EVM Metric System                     | Accepted | 2026-01-22 |
| [ADR-012](ADR-012-evm-time-series-data-strategy.md)      | EVM Time-Series Data Strategy                 | Accepted | 2026-01-22 |
| [ADR-013](ADR-013-computed-budget-attribute.md)         | Computed Budget Attribute Pattern             | Accepted | 2026-02-28 |
