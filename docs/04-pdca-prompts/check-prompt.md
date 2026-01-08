# CHECK Phase: Comprehensive Quality Assessment

## Purpose

Evaluate iteration outcomes against success criteria through multi-dimensional quality review and metrics analysis.

---

## 1. Acceptance Criteria Verification

Create verification matrix:

| Acceptance Criterion | Test Coverage  | Status   | Evidence          | Notes   |
| -------------------- | -------------- | -------- | ----------------- | ------- |
| Criterion 1          | test_x, test_y | ✅/⚠️/❌ | Specific evidence | Details |
| Criterion 2          | test_z         | ✅/⚠️/❌ | Specific evidence | Details |

**Status Key:**

- ✅ Fully met
- ⚠️ Partially met
- ❌ Not met

---

## 2. Test Quality Assessment

Evaluate the test suite:

**Coverage Analysis:**

- Execute coverage report and identify gaps
- Coverage percentage: X%
- Uncovered critical paths
- Recommended coverage improvements

**Test Quality:**

- **Isolation:** Tests independent and can run in any order? (Yes/No + examples)
- **Speed:** Identify slow tests (> 1s) that may hinder CI/CD
- **Clarity:** Test names communicate intent clearly? (Yes/No + examples)
- **Maintainability:** Test code duplication or brittleness issues

---

## 3. Code Quality Metrics

Analyze against established standards (`docs/02-architecture/coding-standards.md`):

| Metric                | Threshold  | Actual | Status   | Details             |
| --------------------- | ---------- | ------ | -------- | ------------------- |
| Cyclomatic Complexity | < 10       | X      | ✅/⚠️/❌ | Functions exceeding |
| Function Length       | < 50 lines | X      | ✅/⚠️/❌ | Long functions      |
| Test Coverage         | > 80%      | X%     | ✅/⚠️/❌ | Gap areas           |
| Type Hints Coverage   | 100%       | X%     | ✅/⚠️/❌ | Missing hints       |
| No `Any`/`any` Types  | 0          | X      | ✅/⚠️/❌ | Violations found    |
| Linting Errors        | 0          | X      | ✅/⚠️/❌ | Error types         |

---

## 4. Design Pattern Audit

Review pattern application:

- Are patterns applied correctly and providing intended benefits?
- Are there anti-patterns or code smells introduced?
- Does code follow existing architectural conventions?
- Is there unnecessary complexity or over-engineering?

**Findings:**

- Pattern used: [Name]
- Application: Correct/Incorrect/Mixed
- Benefits realized: [List]
- Issues identified: [List]

---

## 5. Security and Performance Review

**Security Checks:**

- Input validation and sanitization implemented?
- SQL injection / injection attack prevention verified?
- Proper error handling without information leakage?
- Authentication/authorization correctly applied?

**Performance Analysis:**

- Performance bottlenecks identified (N+1 queries, unnecessary loops)?
- Database query optimization needed?
- Response time measurements (p50, p95, p99)
- Memory usage patterns

---

## 6. Integration Compatibility

- Verify consistency with existing API contracts
- Check database migration compatibility
- Confirm no breaking changes to public interfaces
- Review dependency updates and implications
- Backward compatibility maintained?

---

## 7. Quantitative Assessment

| Metric            | Before | After | Change    | Target Met? |
| ----------------- | ------ | ----- | --------- | ----------- |
| Performance (p95) | X ms   | Y ms  | +/- Z ms  | ✅/❌       |
| Code Coverage     | X%     | Y%    | +/- Z%    | ✅/❌       |
| Bug Count         | X      | Y     | +/- Z     | ✅/❌       |
| Build Time        | X min  | Y min | +/- Z min | ✅/❌       |

---

## 8. Qualitative Assessment

**Code Maintainability:**

- Easy to understand and modify?
- Well-documented?
- Follows project conventions?

**Developer Experience:**

- Was development smooth?
- Were tools adequate?
- Documentation helpful?

**Integration Smoothness:**

- Easy to integrate with existing code?
- Dependencies manageable?

---

## 9. What Went Well

- Effective approaches
- Good decisions
- Smooth processes
- Positive surprises
- Successful patterns

---

## 10. What Went Wrong

- Ineffective approaches
- Poor decisions in hindsight
- Process bottlenecks
- Negative surprises
- Failed assumptions

---

## 11. Root Cause Analysis

For each major problem:

| Problem | Root Cause | Preventable? | Signals Missed | Prevention Strategy |
| ------- | ---------- | ------------ | -------------- | ------------------- |
| Issue 1 | Cause      | Yes/No       | Signals        | Strategy            |

---

## 12. Stakeholder Feedback

- Developer feedback
- Code reviewer observations
- User feedback (if applicable)
- Team retrospective insights

---

## 13. Improvement Options

> [!IMPORTANT] > **Human Decision Point**: If issues found, present **2-3 improvement options**:

| Issue             | Option A (Quick Fix) | Option B (Thorough)        | Option C (Defer)    |
| ----------------- | -------------------- | -------------------------- | ------------------- |
| Issue description | Minimal fix approach | Complete refactor approach | Document for later  |
| Impact            | Impact assessment    | Impact assessment          | Impact assessment   |
| Effort            | Low/Med/High         | Low/Med/High               | Low/Med/High        |
| Recommendation    | [⭐ if recommended]  | [⭐ if recommended]        | [⭐ if recommended] |

**Ask**: "Which improvement approach should we take for each identified issue?"

---

## Output Format

Create: `docs/03-project-plan/iterations/YYYY-MM-name/03-check.md`

Include:

- All sections above with data filled in
- Screenshots of coverage reports
- Links to specific test failures or issues
- Date check was performed
