# ACT Phase: Standardization and Continuous Improvement

## Purpose

Decide actions based on learnings, standardize successful patterns, and implement improvements.

---

## 1. Prioritized Improvement Implementation

Based on CHECK phase decisions, execute improvements:

### Critical Issues (Implement Immediately)

Security vulnerabilities, data integrity issues, production blockers

**For each improvement:**

- Maintain test coverage throughout changes
- Run full test suite after each modification
- Document rationale for future maintainers
- Create follow-up tasks if needed

### High-Value Refactoring

Approved design improvements that enhance maintainability

### Technical Debt Items

Address or document for future sprints

---

## 2. Pattern Standardization

Identify patterns from this implementation that should be adopted codebase-wide:

| Pattern                 | Description | Benefits | Risks | Standardize? |
| ----------------------- | ----------- | -------- | ----- | ------------ |
| Error handling approach | Details     | Benefits | Risks | Yes/No/Pilot |
| Testing pattern         | Details     | Benefits | Risks | Yes/No/Pilot |
| Service structure       | Details     | Benefits | Risks | Yes/No/Pilot |
| Data access pattern     | Details     | Benefits | Risks | Yes/No/Pilot |

> [!IMPORTANT] > **Human Decision Point**: For patterns marked for standardization:
>
> **Option A**: Adopt immediately, update coding standards documentation  
> **Option B**: Pilot in one more feature before standardizing  
> **Option C**: Keep as local optimization, not for wider adoption
>
> **Ask**: "Which patterns should we standardize, and at what pace?"

### Actions if Standardizing

- [ ] Update `docs/02-architecture/cross-cutting/` with new pattern
- [ ] Update coding standards (`docs/02-architecture/coding-standards.md`)
- [ ] Create examples/templates
- [ ] Schedule training session (if complex)
- [ ] Add to code review checklist

---

## 3. Documentation Updates Required

Track what documentation needs updating:

| Document           | Update Needed     | Priority     | Assigned To | Completion Date |
| ------------------ | ----------------- | ------------ | ----------- | --------------- |
| Architecture doc X | Add pattern Y     | High/Med/Low | Name        | YYYY-MM-DD      |
| ADR-NNN            | Create new        | High/Med/Low | Name        | YYYY-MM-DD      |
| API Contracts      | Update endpoint Z | High/Med/Low | Name        | YYYY-MM-DD      |

**Specific Actions:**

- [ ] Update `docs/02-architecture/contexts/{name}/architecture.md`
- [ ] Create new ADR for decision X
- [ ] Update cross-cutting concern doc Y
- [ ] Deprecate obsolete pattern in doc Z

---

## 4. Technical Debt Ledger

### Debt Created This Iteration

| Item   | Description | Impact       | Estimated Effort to Fix | Target Date |
| ------ | ----------- | ------------ | ----------------------- | ----------- |
| TD-XXX | Description | High/Med/Low | X days                  | YYYY-MM-DD  |

### Debt Resolved This Iteration

| Item   | Resolution   | Time Spent |
| ------ | ------------ | ---------- |
| TD-YYY | How resolved | X hours    |

**Net Debt Change:** +/- X items, +/- Y effort days

**Action:** Update `docs/02-architecture/02-technical-debt.md`

---

## 5. Process Improvements

### Process Retrospective

**What Worked Well:**

- Effective TDD practices (specific examples)
- Successful design decisions
- Smooth integration points
- Helpful tools/workflows

**What Could Improve:**

- Testing gaps discovered late
- Design decisions requiring revision
- Tooling or process friction
- Communication breakdowns

**Prompt Engineering Refinements:**

- Which prompts yielded best results?
- Where did AI need more context/constraints?
- What architectural context was missing/unclear?

### Proposed Process Changes

| Change   | Rationale  | Implementation   | Owner |
| -------- | ---------- | ---------------- | ----- |
| Change X | Why needed | How to implement | Who   |

**Action:** Update project plan or team practices

---

## 6. Knowledge Gaps Identified

### Team Learning Needs

- What did team struggle with?
- What documentation is missing?
- What training might help?
- What expertise should we develop?

**Actions:**

- [ ] Create knowledge-sharing session on topic X
- [ ] Document pattern Y in architecture docs
- [ ] Schedule training on technology Z
- [ ] Pair programming on skill W

---

## 7. Metrics for Next PDCA Cycle

Define success metrics for monitoring:

| Metric              | Baseline (Pre-Change) | Target | Actual | Measurement Method |
| ------------------- | --------------------- | ------ | ------ | ------------------ |
| Bug rate in area    | X                     | Y      | Z      | Issue tracking     |
| Test coverage       | X%                    | Y%     | Z%     | Coverage tool      |
| Build time          | X min                 | Y min  | Z min  | CI metrics         |
| Response time (p95) | X ms                  | Y ms   | Z ms   | APM tool           |

---

## 8. Next Iteration Implications

**What This Iteration Unlocked:**

- New capabilities enabled
- Dependencies removed
- Risks mitigated

**New Priorities Emerged:**

- Unexpected opportunities
- Newly discovered requirements

**Assumptions Invalidated:**

- What we learned that changes plans
- Course corrections needed

**Action:** Input for next meta-prompt analysis

---

## 9. Knowledge Transfer Artifacts

Create assets for team learning:

- [ ] Code walkthrough document or video
- [ ] Key decision rationale summary
- [ ] Common pitfalls and how to avoid them
- [ ] Updated onboarding materials

---

## 10. Concrete Action Items

Specific, assignable tasks with owners and deadlines:

- [ ] Update `docs/02-architecture/contexts/auth/architecture.md` with new OAuth pattern (@dev1, by 2025-01-15)
- [ ] Create ADR-042 for database partitioning decision (@dev2, by 2025-01-10)
- [ ] Add technical debt item TD-099 for legacy API cleanup (@tech-lead, by 2025-01-05)
- [ ] Schedule code review session for new pattern (@team, 2025-01-12)
- [ ] Update coding standards with async/await guidelines (@dev3, by 2025-01-20)

---

## Success Metrics and Industry Benchmarks

Based on industry research:

| Metric                | Industry Average | Our Target with PDCA+TDD | Actual This Iteration |
| --------------------- | ---------------- | ------------------------ | --------------------- |
| Defect Rate Reduction | -                | 40-60% improvement       | X%                    |
| Code Review Cycles    | 3-4              | 1-2                      | X                     |
| Rework Rate           | 15-25%           | < 10%                    | X%                    |
| Time-to-Production    | Variable         | 20-30% faster            | X days                |

> [!NOTE] > **Success Story Reference**: Studies show PDCA-driven development reduces software defects by up to 61% when combined with TDD practices.

---

## Output Format

Create: `docs/03-project-plan/iterations/YYYY-MM-name/04-act.md`

Include:

- All sections above with decisions recorded
- Action item tracking with owners
- Metrics baseline and targets
- Links to updated documentation
- Date ACT phase completed
