# DO Phase: TDD Implementation

## Purpose

Execute the test specifications from PLAN phase using strict **RED-GREEN-REFACTOR** methodology. This phase owns **HOW** to implement—the actual test code and production code.

**Prerequisite**: Plan phase (`01-plan.md`) must be completed with test specifications.

---

## TDD Responsibility in DO Phase

| DO Phase Owns            | From PLAN Phase     |
| ------------------------ | ------------------- |
| Test implementation code | Test specifications |
| RED-GREEN-REFACTOR cycle | Acceptance criteria |
| Production code          | Expected behaviors  |
| Refactoring decisions    | Task breakdown      |

---

## RED-GREEN-REFACTOR Cycle

### 🔴 RED: Write a Failing Test

1. Take the **next test specification** from `01-plan.md`
2. Write the test following AAA pattern:

   ```python
   def test_[feature]_[scenario]_[expected_outcome]():
       # Arrange: Set up preconditions
       # Act: Execute the behavior under test
       # Assert: Verify the expected outcome
   ```

3. Run the test—confirm it **fails for the expected reason**
4. Log the failure reason in the DO document

### 🟢 GREEN: Minimal Passing Implementation

1. Write the **minimum code** to make the test pass
2. Resist adding functionality beyond the test scope
3. "Ugly" code is acceptable—we refactor next
4. Run all tests—confirm new test passes, no regressions

### 🔵 REFACTOR: Improve Design While Staying Green

1. Improve code quality:
   - Extract methods for readability
   - Rename for clarity
   - Apply patterns (Service, Repository, Command)
   - Ensure SOLID principles
2. Run tests after **each small change**
3. Document significant refactoring decisions

---

## Implementation Workflow

For each task from `01-plan.md`:

```text
1. Locate test specification (Test ID, expected behavior)
         ↓
2. Write failing test (RED)
         ↓
3. Verify test fails for expected reason
         ↓
4. Implement minimal code (GREEN)
         ↓
5. Verify all tests pass
         ↓
6. Refactor if needed (BLUE)
         ↓
7. Log progress in 02-do.md
         ↓
8. Repeat for next test
```

---

## Human Review Checkpoints

After completing each logical component (3-5 test cycles):

> [!IMPORTANT] > **Pause and present:**
>
> - Tests written and their purpose
> - Code coverage of current increment
> - Design decisions or trade-offs made
> - Concerns or alternatives discovered
>
> **Ask**: "Should I continue with current approach, or adjust direction?"

---

## Coding Standards Compliance

Follow project standards throughout (see `_references.md`):

**Backend:**

- MyPy strict mode (`uv run mypy app --strict`)
- Ruff linting (`uv run ruff check .`)
- Existing patterns from architecture docs

**Frontend:**

- ESLint (`npm run lint`)
- TypeScript strict (`npm run typecheck`)
- Component patterns from existing features

---

## Incremental Complexity Strategy

1. Start with core happy path
2. Add error handling and validation
3. Integrate with existing services/repositories
4. Add edge cases and boundary conditions
5. Implement cross-cutting concerns (logging, metrics)

---

## Daily Log Structure

Track progress continuously in the DO document:

### Entry Format

```markdown
### YYYY-MM-DD

**TDD Cycles Completed:**

| #   | Test Name    | RED Reason       | GREEN Implementation | REFACTOR Notes |
| --- | ------------ | ---------------- | -------------------- | -------------- |
| 1   | test\_[name] | [failure reason] | [code added]         | [improvements] |

**Files Changed:**

- `path/to/file.py` - [description]

**Decisions Made:**

- [Decision]: [Reasoning] → [Impact]

**Blockers:**

- [Issue] → [Resolution needed]

**Next Session:**

- [ ] Next test to implement
```

---

## Documentation References

See [`_references.md`](_references.md) for phase-specific documentation links.

---

## Output

**File**: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/02-do.md`

**Template**: [`_templates/02-do-template.md`](_templates/02-do-template.md)

Update continuously with daily entries. Track running totals:

- Tests written: X
- Tests passing: Y
- Files modified: Z
- Coverage delta: +W%

---

## Key Principles

1. **Test First**: Never write production code without a failing test
2. **Minimal Implementation**: Only code needed to pass the current test
3. **Continuous Refactoring**: Improve design while tests stay green
4. **Document Progress**: Log every cycle for traceability
5. **Quality Gates**: Pass mypy/ruff/eslint before CHECK phase
