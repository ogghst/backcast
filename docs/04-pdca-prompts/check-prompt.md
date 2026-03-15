# CHECK Phase: Quality Assessment & Retrospective

## Purpose

Evaluate iteration outcomes against success criteria, perform root cause analysis on issues, and identify improvement options for the ACT phase.

**Prerequisite**: DO phase (`02-do.md`) must be completed with all tests passing.

---

## CHECK Phase Responsibility

This phase owns:

- **Verification**: Did we meet success criteria?
- **Measurement**: What are the metrics?
- **Architecture Quality**: Does implementation follow documented patterns?
- **Analysis**: What went well/wrong and why?
- **Options**: What improvements should ACT implement?

---

## 1. Acceptance Criteria Verification

Create verification matrix from PLAN success criteria:

| Acceptance Criterion | Test Coverage  | Status   | Evidence   | Notes     |
| -------------------- | -------------- | -------- | ---------- | --------- |
| [AC-1 from plan]     | test_x, test_y | ✅/⚠️/❌ | [evidence] | [details] |
| [AC-2 from plan]     | test_z         | ✅/⚠️/❌ | [evidence] | [details] |

**Status Key:**

- ✅ Fully met
- ⚠️ Partially met
- ❌ Not met

---

## 2. Test Quality Assessment

**Coverage Analysis:**

- Coverage percentage: X%
- Target: ≥80%
- Uncovered critical paths: [list if any]

**Test Quality Checklist:**

- [ ] Tests isolated and order-independent
- [ ] No slow tests (>1s for unit tests)
- [ ] Test names clearly communicate intent
- [ ] No brittle or flaky tests identified

---

## 3. Code Quality Metrics

Run quality gates and report:

| Metric                | Threshold | Actual | Status |
| --------------------- | --------- | ------ | ------ |
| Test Coverage         | ≥80%      | X%     | ✅/❌  |
| MyPy Errors           | 0         | X      | ✅/❌  |
| Ruff Errors           | 0         | X      | ✅/❌  |
| Type Hints            | 100%      | X%     | ✅/❌  |
| Cyclomatic Complexity | <10       | X      | ✅/❌  |

---

## 4. Architecture Consistency Audit

Verify implementation aligns with documented architecture:

**Primary Reference:** [Code Review Checklist](../../02-architecture/code-review-checklist.md)

### Pattern Compliance

**Backend EVCS Patterns:**
- [ ] Entity type correctly chosen (see [Entity Classification Guide](../../02-architecture/backend/contexts/evcs-core/entity-classification.md))
- [ ] TemporalBase used for versioned entities, SimpleBase for non-versioned
- [ ] Service layer patterns respected (no direct DB writes in services - see [Backend Coding Standards](../../02-architecture/backend/coding-standards.md))

**Frontend State Patterns:**
- [ ] TanStack Query used for server state (see [State & Data Context](../../02-architecture/frontend/contexts/02-state-data.md))
- [ ] Query Key Factory used for all query keys
- [ ] Context isolation applied for versioned entities (`branch`, `asOf` in query keys)

**API Conventions:**
- [ ] URL structure follows [API Conventions](../../02-architecture/cross-cutting/api-conventions.md)
- [ ] Pagination with `PaginatedResponse`
- [ ] Filtering with `FilterParser` and whitelisted fields

### Drift Detection

- [ ] Implementation matches PLAN phase approach
- [ ] No undocumented architectural decisions
- [ ] No shortcuts that violate documented standards
- [ ] Deviations logged with rationale

**Drift Found?** → Document in section 12 (Improvement Options) for ACT resolution.

---

## 5. Documentation Alignment

Ensure code and documentation stay synchronized:

| Document | Status | Action Needed |
|----------|--------|---------------|
| Architecture docs | ✅/⚠️/❌ | [update needed] |
| ADRs | ✅/⚠️/❌ | [create/update] |
| API spec (OpenAPI) | ✅/⚠️/❌ | [regenerate] |
| Lessons Learned | ✅/⚠️/❌ | [add entry] |

**Key Questions:**

- Did this iteration introduce patterns worth documenting?
- Are there ADRs needed for architectural decisions made?
- Is the Code Review Checklist still accurate?

**References:**
- [Lessons Learned Registry](../lessons-learned.md)
- [ADR Index](../../02-architecture/decisions/adr-index.md)

---

## 6. Design Pattern Audit

Review pattern application against [Code Review Checklist](../../02-architecture/code-review-checklist.md):

- [ ] Patterns applied correctly with intended benefits
- [ ] No anti-patterns or code smells introduced
- [ ] Code follows existing architectural conventions
- [ ] No unnecessary complexity or over-engineering
- [ ] Parallel development concerns addressed (contract alignment, integration tests)

**Findings:**

| Pattern        | Application       | Issues   |
| -------------- | ----------------- | -------- |
| [Pattern name] | Correct/Incorrect | [if any] |

---

## 7. Security & Performance Review

**Security Checks:**

- [ ] Input validation and sanitization implemented
- [ ] SQL injection prevention verified
- [ ] Proper error handling (no info leakage)
- [ ] Authentication/authorization correctly applied (see [Security Practices](../../02-architecture/cross-cutting/security-practices.md))

**Performance Analysis:**

- Response time (p95): X ms (target: <200ms)
- Database queries optimized (no N+1, see [Database Strategy](../../02-architecture/cross-cutting/database-strategy.md))
- Memory usage acceptable

---

## 8. Integration Compatibility

- [ ] API contracts maintained (see [API Conventions](../../02-architecture/cross-cutting/api-conventions.md))
- [ ] Database migrations compatible
- [ ] No breaking changes to public interfaces
- [ ] Backward compatibility verified

---

## 9. Quantitative Summary

| Metric            | Before | After | Change | Target Met? |
| ----------------- | ------ | ----- | ------ | ----------- |
| Coverage          | X%     | Y%    | +Z%    | ✅/❌       |
| Performance (p95) | X ms   | Y ms  | ±Z ms  | ✅/❌       |
| Build Time        | X min  | Y min | ±Z min | ✅/❌       |

---

## 10. Retrospective

### What Went Well

- [Effective approach 1]
- [Good decision 1]
- [Smooth process 1]

### What Went Wrong

- [Issue 1]
- [Issue 2]
- [Unexpected problem]

---

## 11. Root Cause Analysis

For each major issue identified:

| Problem   | Root Cause | Preventable? | Signals Missed | Prevention Strategy |
| --------- | ---------- | ------------ | -------------- | ------------------- |
| [Issue 1] | [Cause]    | Yes/No       | [Signals]      | [Strategy]          |
| [Issue 2] | [Cause]    | Yes/No       | [Signals]      | [Strategy]          |

**5 Whys Template** (for complex issues):

1. Why did [problem] occur? → [Answer 1]
2. Why [Answer 1]? → [Answer 2]
3. Why [Answer 2]? → [Answer 3]
4. Why [Answer 3]? → [Answer 4]
5. Why [Answer 4]? → **Root Cause**

---

## 12. Improvement Options

> [!IMPORTANT] > **Human Decision Point**: Present improvement options for ACT phase.

For each issue identified:

| Issue      | Option A (Quick Fix) | Option B (Thorough) | Option C (Defer) | Recommended |
| ---------- | -------------------- | ------------------- | ---------------- | ----------- |
| [Issue]    | [approach]           | [approach]          | [approach]       | ⭐ A/B/C    |
| **Effort** | Low                  | Med/High            | None             |             |
| **Impact** | [assessment]         | [assessment]        | [assessment]     |             |

### Documentation Debt

| Doc Type | Gap | Priority | Effort |
|----------|-----|----------|--------|
| [ADR needed] | [topic] | High/Med/Low | X hours |
| [Pattern doc] | [topic] | High/Med/Low | X hours |
| [Lessons entry] | [topic] | High/Med/Low | 15 min |

**Ask**: "Which improvement approach should we take for each identified issue?"

---

## 13. Stakeholder Feedback

- Developer observations: [notes]
- Code reviewer feedback: [notes]
- User feedback (if applicable): [notes]

---

## Documentation References

See [`_references.md`](_references.md) for phase-specific documentation links.

---

## Output

**File**: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/03-check.md`

**Template**: [`_templates/03-check-template.md`](_templates/03-check-template.md)

Include:

- All sections above with data filled in
- Screenshots of coverage reports (if applicable)
- Links to specific test failures or issues
- Date check was performed

---

## Key Principles

1. **Objective Verification**: Use tests and metrics, not opinions
2. **Complete Analysis**: Don't skip root cause for quick fixes
3. **Actionable Options**: Every issue gets improvement options
4. **Human Decision**: ACT phase waits for user approval on approach
5. **Learning Focus**: Problems are opportunities for improvement
