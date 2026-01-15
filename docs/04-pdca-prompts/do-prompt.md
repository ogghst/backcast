# DO Phase: TDD Implementation with Daily Tracking

## Purpose

Execute approved implementation using strict TDD methodology while logging progress, decisions, and deviations.

---

## Red-Green-Refactor Cycle Protocol

### 🔴 RED: Write a Failing Test

1. Write a **single, well-named test** capturing the simplest required behavior
2. Follow the Arrange-Act-Assert (AAA) pattern:
   ```python
   def test_[feature]_[scenario]_[expected_outcome](self):
       # Arrange: Set up preconditions
       # Act: Execute the behavior under test
       # Assert: Verify the expected outcome
   ```
3. Run the test to confirm it fails **for the expected reason**
4. Document why this test matters for acceptance criteria

### 🟢 GREEN: Minimal Passing Implementation

1. Write the **minimum code** necessary to make the test pass
2. Resist adding functionality not required by current tests
3. Keep implementation intentionally simple—even "ugly" code acceptable at this stage
4. Run all tests to confirm new test passes and no regressions

### 🔵 REFACTOR: Improve Design While Staying Green

1. Examine production code for improvements:
   - Extract methods for readability
   - Rename variables/functions for clarity
   - Apply design patterns (Strategy, Factory, Repository)
   - Ensure SOLID principles adherence
2. Run tests after **each small change** to maintain green status
3. Document significant refactoring decisions

---

## Implementation Checkpoints

After completing each logical component (3-5 test cycles):

> [!IMPORTANT] > **Human Review Checkpoint**: Pause and present:
>
> - Tests written and their purpose
> - Code coverage of current increment
> - Design decisions or trade-offs made
> - Identified concerns or alternatives discovered
>
> **Ask**: "Should I continue with current approach, or adjust direction?"

---

## Large Codebase Considerations

- **Follow architecture docs** (`docs/02-architecture/README.md`):

- **Follow coding standards** (`docs/02-architecture/coding-standards.md`):

- Maintain consistent patterns with existing code (naming, error handling, logging)
- Use existing utilities and helpers rather than creating duplicates
- Ensure new code integrates cleanly with dependency injection patterns
- Follow established module boundaries and layering

---

## Incremental Complexity Strategy

1. Start with core happy path
2. Add error handling and validation
3. Integrate with existing services/repositories
4. Add edge cases and boundary conditions
5. Implement cross-cutting concerns (logging, metrics, caching)

---

## Daily Implementation Log

### Date: YYYY-MM-DD

**Work Completed:**

- Specific changes made
- Files modified with brief descriptions
- Tests added (list test names)
- Coverage changes

**Technical Decisions Made:**

- Decision description
- Reasoning behind decision
- Alternatives considered
- Impact on architecture

**Deviations from Plan:**

- What changed from original plan?
- Why did it change?
- Impact on timeline/scope
- Approval obtained (if significant)

**Blockers and Challenges:**

- What's blocking progress?
- Attempted solutions
- Help needed
- Resolution timeline

**Tomorrow's Focus:**

- Next test to write
- Component to implement
- Preparations needed

**Integration Points:**

- Related PRs (link)
- Architecture decisions referenced (link to ADRs)
- Architecture docs needing updates

---

## Output Format

Continuously update: `docs/03-project-plan/iterations/YYYY-MM-name/02-do.md`

Append daily entries chronologically. Keep running totals of:

- Tests written: X
- Files modified: Y
- Coverage change: +/- Z%
