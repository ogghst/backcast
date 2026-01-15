# ANALYSIS Phase: Requirements, Context Discovery & Solution Design

## Purpose

Analyze user requests by clarifying requirements, discovering context from documentation and codebase, and proposing 2-3 alternative solution approaches with clear trade-offs for human decision.

---

## Phase 1: Requirements Clarification

Before diving into solutions, ensure you understand:

1. **User Intent**: What problem are we solving? Who benefits?
2. **Functional Requirements**: What must the solution do?
3. **Non-Functional Requirements**: Performance, accessibility, maintainability?
4. **Constraints**: Technical, time, resource limitations

**Ask clarifying questions if any aspect is ambiguous.**

---

## Phase 2: Context Discovery

### 2.1 Documentation Review

Read and analyze relevant documentation:

**Product Scope** (`docs/01-product-scope/`):

- User stories related to the request
- Business requirements and priorities
- Domain concepts and terminology

**Architecture** (`docs/02-architecture/`):

- Bounded contexts involved
- Existing patterns and conventions
- **Coding Standards** (`coding-standards.md`): Core principles, type safety, quality requirements
- Architectural constraints and decisions
- Integration points

**Project Plan** (`docs/03-project-plan/`):

- Recently completed work (context awareness)
- Current iteration context
- Dependencies and blockers

### 2.2 Codebase Analysis

Analyze existing implementations:

**Backend**:

- Search for similar patterns, existing APIs, data models
- Identify reusable components and conventions
- Note technical debt or limitations

**Frontend**:

- Find comparable UI components, state management patterns, routing
- Identify established conventions
- Note technical debt or limitations

**Look for**:

- Reusable components and patterns
- Established conventions to follow
- Technical constraints or debt

---

## Phase 3: Solution Design

Propose **2-3 distinct solutions** with complete analysis for each:

### Solution Structure (for each option)

#### 1. Architecture & Design Patterns

- Component structure (frontend) or Layer design (backend)
- State management approach
- Data flow and API interactions
- Key design patterns applied

#### 2. User Experience Design

- User stories
- User interaction flow
- Visual hierarchy and layout
- Navigation patterns
- Accessibility considerations
- Edge cases and error states

#### 3. Technical Implementation

- Key files to create/modify
- Integration points with existing code
- Potential technical challenges
- Testing approach (high-level)

#### 4. Trade-offs Analysis

| Aspect          | Assessment                                |
| --------------- | ----------------------------------------- |
| Pros            | What this option excels at                |
| Cons            | Drawbacks and limitations                 |
| Complexity      | Implementation difficulty (Low/Med/High)  |
| Maintainability | Long-term sustainability (Good/Fair/Poor) |
| Performance     | Expected performance characteristics      |

---

## Phase 4: Recommendation & Decision

### Comparison Summary

Quick reference table comparing options:

| Criteria           | Option 1   | Option 2   | Option 3   |
| ------------------ | ---------- | ---------- | ---------- |
| Development Effort | [est.]     | [est.]     | [est.]     |
| UX Quality         | [rating]   | [rating]   | [rating]   |
| Flexibility        | [rating]   | [rating]   | [rating]   |
| Best For           | [use case] | [use case] | [use case] |

### Recommendation

**I recommend Option [X] because:** [clear rationale]

**Alternative consideration:** [when to choose another option]

### Questions for Decision

Specific questions to help the user choose:

1. [Specific question to help user choose]
2. [Another clarifying question]
3. [Priority/trade-off question]

> [!IMPORTANT] > **Human Decision Point**: Present options clearly and await explicit approval before proceeding to PLAN phase.

---

## Output Template

```markdown
# Analysis: [Request Title]

**Created:** [Date]
**Request:** [User's original request]

---

## Clarified Requirements

[Restate requirements in your own words, highlighting any assumptions]

### Functional Requirements

- [List functional requirements]

### Non-Functional Requirements

- [List non-functional requirements]

### Constraints

- [List constraints]

---

## Context Discovery

### Product Scope

- Relevant user stories: [list with links]
- Business requirements: [summarize]

### Architecture Context

- Bounded contexts involved: [list]
- Existing patterns to follow: [describe]
- Architectural constraints: [list]

### Codebase Analysis

**Backend:**

- Existing related APIs: [list files with links]
- Data models: [list relevant models]
- Similar patterns: [describe with references]

**Frontend:**

- Comparable components: [list files with links]
- State management: [describe current approach]
- Routing structure: [relevant routes]

---

## Solution Options

### Option 1: [Descriptive Name]

**Architecture & Design:**
[Describe the approach]

**UX Design:**
[Describe user experience]

**Implementation:**
[Key technical details]

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | [list] |
| Cons | [list] |
| Complexity | [Low/Med/High] |
| Maintainability | [Good/Fair/Poor] |
| Performance | [expected characteristics] |

---

### Option 2: [Descriptive Name]

[Same structure as Option 1]

---

### Option 3: [Descriptive Name - if applicable]

[Same structure as Option 1]

---

## Comparison Summary

| Criteria           | Option 1   | Option 2   | Option 3   |
| ------------------ | ---------- | ---------- | ---------- |
| Development Effort | [est.]     | [est.]     | [est.]     |
| UX Quality         | [rating]   | [rating]   | [rating]   |
| Flexibility        | [rating]   | [rating]   | [rating]   |
| Best For           | [use case] | [use case] | [use case] |

---

## Recommendation

**I recommend Option [X] because:** [clear rationale]

**Alternative consideration:** [when to choose another option]

---

## Decision Questions

1. [Specific question to help user choose]
2. [Another clarifying question]
3. [Priority/trade-off question]

---

## References

- [Relevant architecture docs with links]
- [Related user stories with links]
```

---

## Output File

Create file: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/00-analysis.md`

Folder naming convention: `YYYY-MM-DD-{title}` (e.g., `2026-01-10-user-deletion-fix`)

---

## Key Principles

1. **Evidence-Based**: Base recommendations on actual codebase analysis, not assumptions
2. **Pattern Consistency**: Align with existing project conventions unless there's clear reason to diverge
3. **User-Centered**: UX decisions should prioritize user workflows and mental models
4. **Pragmatic**: Prefer simpler, maintainable solutions over clever but complex ones
5. **Iterative**: Design for incremental delivery when possible

---

## Common UX Patterns to Reference

When analyzing UX, consider these established patterns:

- **Master-Detail**: List selection → Detail view (e.g., project list → project details)
- **Wizard/Stepper**: Multi-step processes with progress indication
- **Drill-Down**: Hierarchical navigation (entity → sub-entity → sub-sub-entity)
- **Dashboard**: Overview with drill-down capabilities
- **Split View**: List + Detail side-by-side for rapid navigation
- **Breadcrumb**: Hierarchical navigation with clear path
- **Tabs/Chips**: Horizontal organization of related content
- **Modal/Drawer**: Contextual actions without losing place
- **Inline Actions**: Direct manipulation (edit-in-place, quick actions)

---

## Example Workflow

**User Request**: "Frontend shall implement hierarchical navigation between projects, WBEs, and cost elements. User shall select project, select its WBE, select its cost elements."

**Your Analysis Should**:

1. **Clarify**: Is this for viewing only? Editing? Creating? How do users navigate back?
2. **Discover**:
   - Check if similar navigation exists (e.g., department → users)
   - Review Project/WBE/CostElement domain models
   - Examine current routing and component structure
3. **Propose Options**:
   - Option 1: Drill-down with breadcrumbs (separate pages)
   - Option 2: Split view with expandable hierarchy
   - Option 3: Single page with nested tabs/panels
4. **Compare**: Effort, UX quality, scalability, mobile support
5. **Recommend**: Based on project conventions and user needs
6. **Await Decision**: User approves one option or requests modifications
