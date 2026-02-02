# ACT Phase: Standardization & Continuous Improvement

## Purpose

Execute approved improvements from CHECK phase, standardize successful patterns, update documentation, and close the iteration with actionable learnings.

**Prerequisite**: CHECK phase (`03-check.md`) must be completed with **approved improvement options**.

---

## ACT Phase Responsibility

This phase owns:

- **Implementation**: Execute the approved improvements
- **Standardization**: Document patterns for reuse
- **Documentation**: Update architecture and project docs
- **Closure**: Finalize iteration with lessons learned

> [!NOTE]
> Root cause analysis is done in CHECK phase. ACT executes the approved solutions.

---

## 1. Improvement Implementation

Based on CHECK phase decisions, execute improvements in priority order:

### Critical Issues (Implement Immediately)

Security vulnerabilities, data integrity issues, production blockers.

| Issue        | Approved Approach | Implementation | Verification     |
| ------------ | ----------------- | -------------- | ---------------- |
| [From CHECK] | [A/B/C]           | [How resolved] | [Tests/evidence] |

### High-Value Refactoring

Approved design improvements that enhance maintainability.

| Change   | Rationale | Files Affected | Verification |
| -------- | --------- | -------------- | ------------ |
| [Change] | [Why]     | [List]         | [Tests pass] |

### Deferred Items

Items marked for future iterations.

| Item   | Reason Deferred | Target Iteration | Tracking       |
| ------ | --------------- | ---------------- | -------------- |
| [Item] | [Why]           | [When]           | [Where logged] |

---

## 2. Pattern Standardization

Identify patterns from this implementation for codebase-wide adoption:

| Pattern             | Description | Benefits   | Risks   | Standardize? |
| ------------------- | ----------- | ---------- | ------- | ------------ |
| [Error handling]    | [Details]   | [Benefits] | [Risks] | Yes/No/Pilot |
| [Testing pattern]   | [Details]   | [Benefits] | [Risks] | Yes/No/Pilot |
| [Service structure] | [Details]   | [Benefits] | [Risks] | Yes/No/Pilot |

> [!IMPORTANT] > **Human Decision Point**: For patterns marked for standardization:
>
> - **Option A**: Adopt immediately, update coding standards
> - **Option B**: Pilot in one more feature before standardizing
> - **Option C**: Keep as local optimization, not for wider adoption
>
> **Ask**: "Which patterns should we standardize, and at what pace?"

### If Standardizing

For each pattern approved for adoption:

- [ ] Update `docs/02-architecture/cross-cutting/` with pattern documentation
- [ ] Update `docs/02-architecture/coding-standards.md` with guidelines
- [ ] Create examples/templates in codebase
- [ ] Add to code review checklist
- [ ] Schedule knowledge sharing (if complex)

---

## 3. Documentation Updates

Track all documentation requiring updates:

| Document           | Update Needed     | Priority     | Status   |
| ------------------ | ----------------- | ------------ | -------- |
| [Architecture doc] | [Add pattern Y]   | High/Med/Low | ✅/🔄/❌ |
| [ADR-XXX]          | [Create new]      | High/Med/Low | ✅/🔄/❌ |
| [API Contracts]    | [Update endpoint] | High/Med/Low | ✅/🔄/❌ |
| [Coding Standards] | [Add guideline]   | High/Med/Low | ✅/🔄/❌ |

### Specific Documentation Actions

- [ ] Update `docs/02-architecture/contexts/{name}/architecture.md`
- [ ] Create ADR for decision X (if architectural change)
- [ ] Update cross-cutting concern doc Y
- [ ] Deprecate obsolete pattern in doc Z

---

## 4. Technical Debt Ledger

### Debt Created This Iteration

| ID     | Description   | Impact       | Effort to Fix | Target Date |
| ------ | ------------- | ------------ | ------------- | ----------- |
| TD-XXX | [Description] | High/Med/Low | X days        | YYYY-MM-DD  |

### Debt Resolved This Iteration

| ID     | Resolution     | Time Spent |
| ------ | -------------- | ---------- |
| TD-YYY | [How resolved] | X hours    |

**Net Debt Change:** +/- X items, +/- Y effort days

**Action**: Update `docs/02-architecture/02-technical-debt.md`

---

## 5. Process Improvements

### Effective Practices to Continue

- [Process 1]: [Why it worked]
- [Process 2]: [Why it worked]

### Process Changes for Future

| Change   | Rationale    | Implementation     | Owner |
| -------- | ------------ | ------------------ | ----- |
| [Change] | [Why needed] | [How to implement] | [Who] |

### Prompt Engineering Refinements

Capture learnings for improving AI collaboration:

- Which prompts yielded best results?
- Where did AI need more context/constraints?
- What architectural context was missing/unclear?

---

## 6. Knowledge Gaps Identified

### Learning Needs Discovered

- What did team struggle with?
- What documentation is missing?
- What training might help?

### Actions

- [ ] Create knowledge-sharing session on [topic]
- [ ] Document [pattern] in architecture docs
- [ ] Schedule training on [technology]
- [ ] Pair programming on [skill]

---

## 7. Knowledge Transfer Artifacts

Create assets for team learning:

- [ ] Code walkthrough document or video
- [ ] Key decision rationale summary
- [ ] Common pitfalls and how to avoid them
- [ ] Updated onboarding materials (if needed)

---

## 8. Metrics for Monitoring

Define success metrics for ongoing monitoring:

| Metric              | Baseline | Target | Measurement Method |
| ------------------- | -------- | ------ | ------------------ |
| Bug rate in area    | X        | Y      | Issue tracking     |
| Test coverage       | X%       | Y%     | Coverage tool      |
| Response time (p95) | X ms     | Y ms   | APM tool           |

---

## 9. Next Iteration Implications

### Unlocked Capabilities

- New capabilities enabled by this iteration
- Dependencies removed
- Risks mitigated

### Emerged Priorities

- Unexpected opportunities discovered
- Newly discovered requirements
- Technical insights affecting roadmap

### Invalidated Assumptions

- What we learned that changes future plans
- Course corrections needed

**Action**: Input these findings into next iteration's Analysis phase

---

## 10. Concrete Action Items

Specific, assignable tasks with owners and deadlines:

- [ ] [Action 1] - @owner - by YYYY-MM-DD
- [ ] [Action 2] - @owner - by YYYY-MM-DD
- [ ] [Action 3] - @owner - by YYYY-MM-DD
- [ ] [Action 4] - @owner - by YYYY-MM-DD
- [ ] [Action 5] - @owner - by YYYY-MM-DD

---

## 11. Iteration Closure

### Final Status

- [ ] All success criteria from PLAN phase verified
- [ ] All approved improvements from CHECK implemented
- [ ] Code passes quality gates (MyPy, Ruff/ESLint, tests)
- [ ] Documentation updated (including ADRs if architectural)
- [ ] Sprint backlog updated
- [ ] Technical debt ledger updated
- [ ] Lessons learned documented

**Iteration Status:** ✅ Complete | ⚠️ Partial | ❌ Incomplete

**Success Criteria Met:** X of Y

### Lessons Learned Summary

1. [Key lesson 1]
2. [Key lesson 2]
3. [Key lesson 3]

**Iteration Closed:** YYYY-MM-DD

---

## Industry Benchmarks

Reference for evaluating iteration success:

| Metric                | Industry Average | Target with PDCA+TDD | Actual |
| --------------------- | ---------------- | -------------------- | ------ |
| Defect Rate Reduction | -                | 40-60% improvement   | X%     |
| Code Review Cycles    | 3-4              | 1-2                  | X      |
| Rework Rate           | 15-25%           | <10%                 | X%     |
| Time-to-Production    | Variable         | 20-30% faster        | X days |

---

## Documentation References

See [`_references.md`](_references.md) for phase-specific documentation links.

---

## Output

**File**: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/04-act.md`

**Template**: [`_templates/04-act-template.md`](_templates/04-act-template.md)

Include:

- All sections above with decisions recorded
- Action item tracking with owners
- Links to updated documentation
- Date ACT phase completed

---

## Key Principles

1. **Execute Decisions**: Implement what CHECK phase decided
2. **Standardize Success**: Document patterns for reuse
3. **Update Everything**: No stale documentation
4. **Close Cleanly**: Clear status and lessons learned
5. **Feed Forward**: Findings inform next iteration
