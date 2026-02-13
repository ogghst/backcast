# PLAN Phase: Work Decomposition & Success Criteria

## Purpose

Decompose the **approved approach from Analysis phase** into actionable tasks with measurable success criteria. This phase defines **WHAT** to test and implement, not **HOW** (that's the DO phase).

**Prerequisite**: Analysis phase (`00-analysis.md`) must be completed with an **approved option**.

---

## TDD Responsibility in PLAN Phase

PLAN defines the **test specifications** (what to test), while DO executes the **test implementation** (how to test).

| PLAN Phase Owns         | DO Phase Owns            |
| ----------------------- | ------------------------ |
| Acceptance criteria     | Actual test code         |
| Test case names/IDs     | RED-GREEN-REFACTOR cycle |
| Expected behaviors      | Implementation code      |
| Test-to-requirement map | Refactoring decisions    |

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

Reference the approved option from analysis:

- **Selected Option**: [Option X from analysis]
- **Architecture**: [Brief description]
- **Key Decisions**: [List critical decisions made]

### 1.2 Success Criteria (Measurable)

Define **testable acceptance criteria**:

**Functional Criteria:**

- [ ] [Specific feature behavior] VERIFIED BY: [test type]
- [ ] [Edge case handling] VERIFIED BY: [test type]
- [ ] [Error condition] VERIFIED BY: [test type]

**Technical Criteria:**

- [ ] Performance: [metric] VERIFIED BY: [measurement method]
- [ ] Security: [requirement] VERIFIED BY: [test type]
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline

**TDD Criteria:**

- [ ] All tests written **before** implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage ≥80%
- [ ] Tests follow Arrange-Act-Assert pattern

### 1.3 Scope Boundaries

**In Scope:**

- [Specific features/changes]
- [Components affected]
- [Testing requirements]
- [Documentation updates]

**Out of Scope:**

- [Explicitly list what's NOT done]
- [Items deferred to future iterations]

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

Break down work into **sequential, atomic tasks**:

| #   | Task          | Files  | Dependencies  | Success Criteria | Complexity   |
| --- | ------------- | ------ | ------------- | ---------------- | ------------ |
| 1   | [description] | [list] | [none/task X] | [verification]   | Low/Med/High |
| 2   | [description] | [list] | [task 1]      | [verification]   | Low/Med/High |

**Task Ordering Principles:**

1. Database/Models first (schema before logic)
2. Backend before Frontend (API before UI)
3. Tests defined alongside each task (DO phase writes them)
4. Incremental complexity (happy path → edge cases)

### 2.2 Test-to-Requirement Traceability

Map each acceptance criterion to test specifications:

| Acceptance Criterion | Test ID | Test File                   | Expected Behavior |
| -------------------- | ------- | --------------------------- | ----------------- |
| [AC1 from Phase 1]   | T-001   | tests/unit/[feature]        | [description]     |
| [AC2 from Phase 1]   | T-002   | tests/integration/[feature] | [description]     |

**Requirements:**

- Each acceptance criterion must have ≥1 test specification
- Test names follow: `test_{feature}_{scenario}_{expected_outcome}`
- Complex criteria require multiple tests (happy path, edge cases, errors)

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

Specify tests in this order (DO phase will implement):

```text
├── Unit Tests (tests/unit/)
│   ├── Happy path tests
│   ├── Edge cases and boundaries
│   └── Error handling
├── Integration Tests (tests/integration/)
│   ├── Database integration
│   └── Service layer integration
└── E2E Tests (if applicable - tests/e2e/)
    └── Critical user flows
```

### 3.2 Test Cases (First 3-5)

| Test ID | Test Name                                       | Criterion | Type | Expected Result |
| ------- | ----------------------------------------------- | --------- | ---- | --------------- |
| T-001   | test*[feature]\_happy_path_returns*[result]     | AC-1      | Unit | [expected]      |
| T-002   | test*[feature]\_with*[edge_case]                | AC-2      | Unit | [expected]      |
| T-003   | test*[feature]\_when*[error]_raises_[exception] | AC-3      | Unit | [expected]      |

### 3.3 Test Infrastructure Needs

- **Fixtures needed**: [list from conftest.py or new ones]
- **Mocks/stubs**: [external services, time-dependent logic]
- **Database state**: [seed data requirements]

---

## Phase 4: Risk Assessment

| Risk Type   | Description     | Probability  | Impact       | Mitigation |
| ----------- | --------------- | ------------ | ------------ | ---------- |
| Technical   | [specific risk] | Low/Med/High | Low/Med/High | [strategy] |
| Integration | [specific risk] | Low/Med/High | Low/Med/High | [strategy] |

---

## Phase 5: Prerequisites & Dependencies

### Technical Prerequisites

- [ ] Database migrations applied
- [ ] Dependencies installed
- [ ] Environment configured

### Documentation Prerequisites

- [x] Analysis phase approved
- [ ] Architecture docs reviewed
- [ ] Related ADRs understood

---

## Documentation References

See [`_references.md`](_references.md) for phase-specific documentation links.

---

## Output

**File**: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/01-plan.md`

**Template**: [`_templates/01-plan-template.md`](_templates/01-plan-template.md)

---

## Key Principles

1. **Define WHAT, not HOW**: Specify test cases, not test code
2. **Measurable**: Success criteria objectively verifiable
3. **Sequential**: Tasks ordered with clear dependencies
4. **Traceable**: Every requirement maps to test specifications
5. **Actionable**: Each task clear enough for DO phase execution

> [!NOTE]
> This plan drives the DO phase. Tests are **specified** here but **implemented** in DO following RED-GREEN-REFACTOR.
