# Check: [Request Title]

**Completed:** YYYY-MM-DD  
**Based on:** [Link to 02-do.md]

---

## 1. Acceptance Criteria Verification

| Acceptance Criterion | Test Coverage  | Status   | Evidence   | Notes     |
| -------------------- | -------------- | -------- | ---------- | --------- |
| [AC-1 from plan]     | test_x, test_y | ✅/⚠️/❌ | [evidence] | [details] |
| [AC-2 from plan]     | test_z         | ✅/⚠️/❌ | [evidence] | [details] |

**Status Key:** ✅ Fully met | ⚠️ Partially met | ❌ Not met

---

## 2. Test Quality Assessment

**Coverage:**

- Coverage percentage: X%
- Uncovered critical paths: [list if any]

**Quality Checklist:**

- [ ] Tests isolated and order-independent
- [ ] No slow tests (>1s)
- [ ] Test names communicate intent
- [ ] No brittle or flaky tests

---

## 3. Code Quality Metrics

| Metric                | Threshold | Actual | Status |
| --------------------- | --------- | ------ | ------ |
| Test Coverage         | >80%      | X%     | ✅/❌  |
| Type Hints            | 100%      | X%     | ✅/❌  |
| Linting Errors        | 0         | X      | ✅/❌  |
| Cyclomatic Complexity | <10       | X      | ✅/❌  |

---

## 4. Security & Performance

**Security:**

- [ ] Input validation implemented
- [ ] No injection vulnerabilities
- [ ] Proper error handling (no info leakage)
- [ ] Auth/authz correctly applied

**Performance:**

- Response time (p95): X ms
- Database queries optimized: Yes/No
- N+1 queries: None/Found

---

## 5. Integration Compatibility

- [ ] API contracts maintained
- [ ] Database migrations compatible
- [ ] No breaking changes
- [ ] Backward compatibility verified

---

## 6. Quantitative Summary

| Metric            | Before | After | Change | Target Met? |
| ----------------- | ------ | ----- | ------ | ----------- |
| Coverage          | X%     | Y%    | +Z%    | ✅/❌       |
| Performance (p95) | X ms   | Y ms  | -Z ms  | ✅/❌       |
| Build Time        | X min  | Y min | ±Z min | ✅/❌       |

---

## 7. Retrospective

### What Went Well

- [Effective approach 1]
- [Good decision 1]

### What Went Wrong

- [Issue 1]
- [Issue 2]

---

## 8. Root Cause Analysis

| Problem   | Root Cause | Preventable? | Prevention Strategy |
| --------- | ---------- | ------------ | ------------------- |
| [Issue 1] | [Cause]    | Yes/No       | [Strategy]          |

---

## 9. Improvement Options

| Issue   | Option A (Quick) | Option B (Thorough) | Option C (Defer) | Recommended |
| ------- | ---------------- | ------------------- | ---------------- | ----------- |
| [Issue] | [approach]       | [approach]          | [approach]       | ⭐ A/B/C    |

**Decision Required:** Which improvement approach for each issue?

---

## 10. Stakeholder Feedback

- Developer observations: [notes]
- Code reviewer feedback: [notes]
- User feedback (if any): [notes]
