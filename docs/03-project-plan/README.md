# Project Plan

**Quick Start for AI Agents:**

| Need                                  | Read This                                                                          |
| ------------------------------------- | ---------------------------------------------------------------------------------- |
| **What to work on RIGHT NOW**         | [`sprint-backlog.md`](sprint-backlog.md) - Active sprint tasks                     |
| **All pending work**                  | [`product-backlog.md`](product-backlog.md) - Prioritized items with estimates       |
| **Product features to build**         | [`../01-product-scope/`](../01-product-scope/) - Requirements                      |
| **All planned work**                  | [`epics.md`](epics.md) - Epic breakdown with dependencies                         |
| **Team availability**                 | [`team-capacity.md`](team-capacity.md) - Capacity & velocity history               |
| **Velocity tracking**                 | [`velocity-tracking.md`](velocity-tracking.md) - Sprint metrics & forecasting      |
| **Technical debt**                    | [`technical-debt-register.md`](technical-debt-register.md) - Consolidated debt log  |
| **Past iterations**                   | [`iterations/`](iterations/) - PDCA history (01-plan → 02-do → 03-check → 04-act)   |
| **Sprint archive**                    | [`sprints/`](sprints/) - Historical sprint documentation                           |

---

## Key Concepts

### Workflow: Epics → Backlog → Iteration → PDCA

```
1. Define Epics (epics.md)
   ↓
2. Break down into User Stories with estimates
   ↓
3. Add to Product Backlog (product-backlog.md) with priorities
   ↓
4. Pull into Sprint Backlog (sprint-backlog.md) based on velocity & capacity
   ↓
5. Execute with PDCA cycle:
   - 01-plan.md: Strategic analysis, TDD blueprint
   - 02-do.md: TDD implementation with daily logs
   - 03-check.md: Quality assessment & metrics
   - 04-act.md: Standardization & improvements
```

### PDCA Cycle

- **PDCA**: Each iteration uses Plan → Do → Check → Act structure documented in [`../04-pdca-prompts/`](../04-pdca-prompts/)
- **Current Work**: Always check [`sprint-backlog.md`](sprint-backlog.md) first
- **Implementation**: Use `project-plan-implementer` agent for product scope features

---

## Directory Structure

```
docs/03-project-plan/
├── README.md                      # This file - navigation hub
├── sprint-backlog.md              # Active sprint backlog (current iteration)
├── product-backlog.md             # Product backlog (all pending work)
├── epics.md                       # Epic breakdown with dependencies
├── team-capacity.md               # Team skills & velocity history
├── velocity-tracking.md           # Sprint metrics & forecasting
├── technical-debt-register.md     # Consolidated debt tracking
├── sprints/                       # Historical sprint archive
│   ├── sprint-01.md
│   ├── sprint-02.md
│   └── ...
└── iterations/                    # PDCA iteration folders
    ├── YYYY-MM-DD-name/
    │   ├── 01-plan.md
    │   ├── 02-do.md
    │   ├── 03-check.md
    │   └── 04-act.md
    └── ...
```

### Note: sprints/ vs iterations/

- **`sprints/`**: Historical sprint documentation (Sprint 1, 2, etc.)
- **`iterations/`**: Active PDCA iterations with detailed phase documents

---

## Planning Process

### 1. Sprint Planning

1. Review [`velocity-tracking.md`](velocity-tracking.md) for capacity
2. Review [`product-backlog.md`](product-backlog.md) for prioritized, ready items
3. Select items totaling 20-25 points (80% capacity, 20% buffer)
4. Update [`sprint-backlog.md`](sprint-backlog.md) with selected stories
5. Create iteration folder: `iterations/YYYY-MM-DD-name/`
6. Copy PDCA templates from [`../04-pdca-prompts/`](../04-pdca-prompts/)

### 2. Iteration Execution

Follow PDCA cycle:
- **PLAN**: Analyze requirements, design approach, estimate effort
- **DO**: TDD implementation with red-green-refactor cycles
- **CHECK**: Verify acceptance criteria, measure quality
- **ACT**: Standardize patterns, document technical debt

### 3. Iteration Review

1. Update [`velocity-tracking.md`](velocity-tracking.md) with actual points
2. Move technical debt to [`technical-debt-register.md`](technical-debt-register.md)
3. Update [`product-backlog.md`](product-backlog.md) with completed items
4. Retrospective: What went well? What needs improvement?

---

## Metrics & Tracking

### Story Points

- **Fibonacci sequence**: 1, 2, 3, 5, 8, 13, 21
- **Team capacity**: 20-25 points per sprint
- **Target velocity**: 25 ± 3 points
- **Items > 13 points**: Must be split

### Velocity

- **Current average**: 22.0 points/sprint
- **Trend**: Stable
- **Forecast**: 23-25 points for next 3 sprints

See [`velocity-tracking.md`](velocity-tracking.md) for details.

### Technical Debt

- **Active items**: 2 high severity
- **Total effort**: 10 hours
- **Paydown target**: 2026-01-10

See [`technical-debt-register.md`](technical-debt-register.md) for details.

---

## Related Documentation

- [Product Scope](../01-product-scope/) - Requirements and features
- [System Architecture](../02-architecture/) - Technical design and decisions
- [PDCA Prompts](../04-pdca-prompts/) - Iteration guidance templates
