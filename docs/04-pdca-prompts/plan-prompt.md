# PLAN Phase: Work Decomposition & Success Criteria

## Purpose

Decompose the **approved approach from Analysis phase** into actionable tasks with measurable success criteria, documentation references, and test specifications.

**Prerequisite**: Analysis phase (00-analysis.md) must be completed with an **approved option**.

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

- [Specific feature behavior] VERIFIED BY: [test type]
- [Edge case handling] VERIFIED BY: [test type]
- [Error condition] VERIFIED BY: [test type]

**Technical Criteria:**

- Performance: [metric] VERIFIED BY: [measurement method]
- Security: [requirement] VERIFIED BY: [test type]
- Code Quality: [standard] VERIFIED BY: [quality gate]

**Business Criteria:**

- [User outcome] VERIFIED BY: [measurement method]
- [Business metric] VERIFIED BY: [measurement method]

### 1.3 Scope Boundaries

**In Scope:**

- [Specific features/changes]
- [Components affected]
- [Testing requirements]
- [Documentation updates]

**Out of Scope:**

- [Explicitly list what's NOT done]
- [Items deferred to future iterations]
- [Assumptions requiring validation]

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

Break down the work into **sequential, atomic tasks**:

```
├── Task 1: [Description]
│   ├── Files: [list files to create/modify]
│   ├── Dependencies: [what must be done first]
│   ├── Success: [how to verify completion]
│   └── Estimated: [complexity: Low/Med/High]
├── Task 2: [Description]
│   └── [same structure]
└── Task N: [Description]
    └── [same structure]
```

**Task Ordering Principles:**

1. **Database/Models First**: Schema changes before API/services
2. **Backend Before Frontend**: API ready before UI consumes it
3. **Tests Parallel**: Write tests alongside implementation (TDD)
4. **Incremental**: Each task adds verifiable value

### 2.2 File Change List

List all files to be created or modified:

| File Path           | Action | Purpose                |
| ------------------- | ------ | ---------------------- |
| `path/to/file.ext`  | Create | [Brief description]    |
| `path/to/other.ext` | Modify | [What changes and why] |

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

```
├── Unit Tests (isolated component behavior)
│   ├── Happy path scenarios
│   ├── Edge cases and boundaries
│   └── Error handling
├── Integration Tests (component interactions)
│   ├── Database/repository integration
│   └── Service layer integration
└── End-to-End Tests (if applicable)
    └── Critical user flows
```

### 3.2 Test Cases (First 3-5)

Document specific test cases, ordered simplest to most complex:

| Test ID | Description              | Type         | Verification      |
| ------- | ------------------------ | ------------ | ----------------- |
| T-001   | [Brief test description] | Unit/Int/E2E | [Expected result] |
| T-002   | [Brief test description] | Unit/Int/E2E | [Expected result] |
| T-003   | [Brief test description] | Unit/Int/E2E | [Expected result] |

### 3.3 Test Infrastructure

- **Test Framework**: [e.g., pytest, vitest]
- **Fixtures Needed**: [list shared test fixtures]
- **Mock/Stub Requirements**: [external dependencies to mock]

---

## Phase 4: Risk Assessment

### 4.1 Risks and Mitigations

| Risk Type   | Description     | Probability  | Impact       | Mitigation Strategy   |
| ----------- | --------------- | ------------ | ------------ | --------------------- |
| Technical   | [specific risk] | Low/Med/High | Low/Med/High | [concrete mitigation] |
| Integration | [specific risk] | Low/Med/High | Low/Med/High | [concrete mitigation] |
| Schedule    | [specific risk] | Low/Med/High | Low/Med/High | [concrete mitigation] |

---

## Phase 5: Documentation References

### 5.1 Required Documentation

Link to relevant docs for implementation:

**Architecture & Standards:**

- Coding Standards: `docs/02-architecture/coding-standards.md`
- [Relevant ADRs]: `docs/02-architecture/decisions/...`
- [Bounded Context]: `docs/02-architecture/01-bounded-contexts.md`

**Domain & Requirements:**

- [User Stories]: `docs/01-product-scope/...`
- [Functional Specs]: `docs/01-product-scope/...`

**Project Context:**

- Current Iteration: `docs/03-project-plan/current-iteration.md`
- Related Iterations: [links]

### 5.2 Code References

**Existing Patterns to Follow:**

- Backend: [link to similar implementation]
- Frontend: [link to similar component]
- Tests: [link to test pattern reference]

**Database Schema:**

- Relevant tables: [table names]
- Relationships: [describe]
- Indexes: [list if needed]

---

## Phase 6: Prerequisites & Dependencies

### 6.1 Technical Prerequisites

- [ ] Database migrations applied
- [ ] Dependencies installed
- [ ] Environment configured
- [ ] External services available

### 6.2 Documentation Prerequisites

- [ ] Analysis phase approved
- [ ] Architecture docs reviewed
- [ ] Related ADRs understood

---

## Output Template

```markdown
# Plan: [Request Title]

**Created:** [Date]
**Based on:** [Link to 00-analysis.md]
**Approved Option:** [Option X]

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: [Option X from analysis]
- **Architecture**: [Brief description]
- **Key Decisions**: [List critical decisions made]

### Success Criteria

**Functional Criteria:**

- [Specific feature behavior] VERIFIED BY: [test type]
- [Edge case handling] VERIFIED BY: [test type]
- [Error condition] VERIFIED BY: [test type]

**Technical Criteria:**

- Performance: [metric] VERIFIED BY: [measurement method]
- Security: [requirement] VERIFIED BY: [test type]
- Code Quality: [standard] VERIFIED BY: [quality gate]

**Business Criteria:**

- [User outcome] VERIFIED BY: [measurement method]

### Scope Boundaries

**In Scope:**

- [List]

**Out of Scope:**

- [List]

---

## Work Decomposition

### Task Breakdown

| Task | Description | Files  | Dependencies  | Success  | Est. Complexity |
| ---- | ----------- | ------ | ------------- | -------- | --------------- |
| 1    | [desc]      | [list] | [none/task X] | [verify] | Low/Med/High    |
| 2    | [desc]      | [list] | [task 1]      | [verify] | Low/Med/High    |
| 3    | [desc]      | [list] | [task 2]      | [verify] | Low/Med/High    |

---

## Test Specification

### Test Hierarchy
```

├── Unit Tests
│ ├── [test areas]
├── Integration Tests
│ ├── [test areas]
└── E2E Tests (if applicable)
└── [critical flows]

```

### Test Cases

| Test ID | Description | Type | Verification |
| ------- | ----------- | ---- | ------------ |
| T-001   | [desc]      | Unit | [expected]   |
| T-002   | [desc]      | Int  | [expected]   |
| T-003   | [desc]      | Unit | [expected]   |

### Test Infrastructure

- **Test Framework**: [framework]
- **Fixtures Needed**: [list]
- **Mock Requirements**: [list]

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| Technical | [desc]      | Low/Med/High| Low/Med/High| [strategy] |
| Integration| [desc]     | Low/Med/High| Low/Med/High| [strategy] |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**
- Coding Standards: `docs/02-architecture/coding-standards.md`
- [Relevant ADR]: `docs/02-architecture/decisions/...`

**Domain & Requirements:**
- [User Story]: `docs/01-product-scope/...`

**Project Context:**
- Current Iteration: `docs/03-project-plan/current-iteration.md`

### Code References

**Existing Patterns:**
- Backend: [link to similar implementation]
- Frontend: [link to similar component]

**Database Schema:**
- Tables: [list]
- Relationships: [describe]

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [ ] [Prerequisite 1]
- [ ] [Prerequisite 2]

### Documentation Prerequisites

- [x] Analysis phase approved

```

---

## Output File

Create file: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/01-plan.md`

**Location**: Same folder as `00-analysis.md`

---

## Key Principles

1. **Actionable**: Each task must be clear and executable
2. **Measurable**: Success criteria must be objectively verifiable
3. **Sequential**: Tasks ordered with clear dependencies
4. **Test-Driven**: Tests specified alongside implementation
5. **Reference-Rich**: Link to existing patterns and documentation
