# PLAN Phase: Strategic Analysis and Iteration Planning

## Purpose

Structure iteration planning by analyzing requirements, architectural constraints, and generating implementation options for human decision.

---

## Phase 1: Context Analysis

### Documentation Review

Analyze existing documentation for alignment:

- **Documentation Guide** (`docs/00-meta/README.md`): How to read, write, and maintain documentation
- **Product Scope** (`docs/01-product-scope/`): product vision, functional requirements
- **Architecture** (`docs/02-architecture/`): Technical debt, constraints, system capabilities and gaps
  - **Coding Standards** (`docs/02-architecture/coding-standards.md`): Core principles, type safety, backend/frontend patterns, quality gates
- **Project Plan** (`docs/03-project-plan`): Epics, Sprints, User Stories, Recently completed work, current context, team velocity

### Codebase Analysis

Understand existing patterns:

- Current architectural patterns and conventions
- Existing test infrastructure and coverage patterns
- Dependencies and integration points
- Historical patterns for similar features

**Available MCP Tools for Analysis:**

- **`context7`**: Query library documentation and usage patterns

  - Access official documentation for Python/TypeScript libraries
  - Research best practices for frameworks (FastAPI, React, etc.)
  - Validate implementation approaches against library conventions

- **`postgres_evs`**: Direct database introspection
  - Query current schema, tables, columns, and constraints
  - Inspect existing data patterns and relationships
  - Validate migration strategies against actual database state
  - Test SQL queries before implementation

---

## Phase 2: Problem Definition

### 1. Problem Statement

- What specific problem are we solving?
- Why is it important now?
- What happens if we don't address it?
- What is the business value?

### 2. Success Criteria (Measurable)

Define **measurable acceptance criteria** verified through automated tests:

**Functional Criteria:**

- Features working as specified
- Edge cases handled
- Error conditions managed

**Technical Criteria:**

- Performance targets (response times, throughput)
- Security requirements
- Scalability needs

**Business Criteria:**

- Metrics to track
- User impact measurements

### 3. Scope Definition

**In Scope:**

- Specific features/changes
- Components affected
- Testing requirements
- Documentation updates

**Out of Scope:**

- Explicitly list what we're NOT doing
- Items deferred to future iterations
- Assumptions requiring stakeholder validation

---

## Phase 3: Implementation Options

Generate **2-3 distinct implementation approaches**:

| Aspect                   | Option A                | Option B                | Option C (optional)     |
| ------------------------ | ----------------------- | ----------------------- | ----------------------- |
| **Approach Summary**     | Brief description       | Brief description       | Brief description       |
| **Design Patterns**      | Patterns applied        | Patterns applied        | Patterns applied        |
| **Pros**                 | Key benefits            | Key benefits            | Key benefits            |
| **Cons**                 | Trade-offs              | Trade-offs              | Trade-offs              |
| **Test Strategy Impact** | How testing changes     | How testing changes     | How testing changes     |
| **Risk Level**           | Low/Medium/High         | Low/Medium/High         | Low/Medium/High         |
| **Estimated Complexity** | Simple/Moderate/Complex | Simple/Moderate/Complex | Simple/Moderate/Complex |

### Recommendation

Provide recommended option with justification based on:

- Alignment with existing codebase conventions
- Long-term maintainability and extensibility
- Test coverage feasibility
- Risk mitigation

> [!IMPORTANT] > **Human Decision Point**: Present options clearly and await explicit approval before proceeding.

---

## Phase 4: Technical Design

### TDD Test Blueprint

For the approved approach, outline test hierarchy:

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

Document the first 3-5 test cases, ordered simplest to most complex.

### Implementation Strategy

- High-level approach
- Key technologies/patterns to use
- Integration points with existing system
- Component breakdown

---

## Phase 5: Risk Assessment

### Risks and Mitigations

| Risk Type   | Description                       | Probability  | Impact       | Mitigation Strategy |
| ----------- | --------------------------------- | ------------ | ------------ | ------------------- |
| Technical   | e.g., API compatibility           | Low/Med/High | Low/Med/High | Specific mitigation |
| Schedule    | e.g., Dependency on external team | Low/Med/High | Low/Med/High | Specific mitigation |
| Integration | e.g., Breaking changes            | Low/Med/High | Low/Med/High | Specific mitigation |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Development:** X hours/days
- **Testing:** X hours/days
- **Documentation:** X hours/days
- **Review & Deployment:** X hours/days
- **Total Estimated Effort:** X days

### Prerequisites

- What must be done first?
- What documentation needs updating?
- What infrastructure is needed?

---

## Output Format

Create file: `docs/03-project-plan/iterations/YYYY-MM-name/01-plan.md`

Include:

- All sections above
- Date was created
- Links to related architecture docs
